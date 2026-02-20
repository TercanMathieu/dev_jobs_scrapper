import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class APEC(Website):
    """Scraper for APEC (Association Pour l'Emploi des Cadres)"""

    def __init__(self):
        super().__init__(
            'APEC',
            'https://www.apec.fr/candidat/recherche-emploi.html/emploi?lieux=91&motsCles=developpeur&page={}',
            'APEC JOBS',
            'https://www.apec.fr/fileadmin/user_upload/Logos/Apec-Logo.svg',
            True,
        )

    def _is_valid_company_name(self, text, job_title=None):
        """Check if text is a valid company name"""
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        # Check against job title
        if job_title:
            text_norm = text.lower().strip()
            title_norm = job_title.lower().strip()
            if text_norm == title_norm:
                return False
            if text_norm in title_norm and len(text_norm) > 8:
                return False
        
        # Invalid patterns
        invalid_patterns = [
            'recrutement', 'recrute', 'recruiting', 'hiring',
            'active', 'actif', 'en cours', 'in progress',
            'publié', 'published', 'posté', 'posted',
            'il y a', 'ago', 'days', 'jours',
            'voir', 'view', 'en savoir', 'more',
            ' CDI', ' CDD', ' stage', ' alternance',
            'temps plein', 'temps partiel', 'full time', 'part time',
            'télétravail', 'remote', 'hybride', 'hybrid',
        ]
        
        job_keywords = [
            'développeur', 'developpeur', 'developer', 'dev ',
            'ingénieur', 'ingenieur', 'engineer',
            'frontend', 'backend', 'fullstack', 'full-stack',
            'software', 'web', 'mobile', 'cloud',
            'data', 'machine learning', 'ia ', 'ai ',
            'cadre', 'manager', 'directeur',
        ]
        
        text_lower = text.lower()
        for pattern in invalid_patterns + job_keywords:
            if pattern in text_lower:
                return False
        
        if text.isupper() and len(text) > 10:
            return False
            
        digit_count = sum(c.isdigit() for c in text)
        if digit_count > 3:
            return False
        
        return True

    def _extract_company_name(self, job_element, job_title=None):
        """Extract company name from APEC job element"""
        
        # APEC specific selectors
        selectors = [
            ('span', {'class': lambda x: x and 'company' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'company' in str(x).lower()}),
            ('span', {'class': lambda x: x and 'card-offer__company' in str(x)}),
            ('div', {'class': lambda x: x and 'offer-card__company' in str(x)}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # APEC often has company in specific data attributes
        for elem in job_element.find_all(attrs={'data-company': True}):
            text = elem['data-company'].strip()
            if self._is_valid_company_name(text, job_title):
                return text
        
        # Fallback
        for tag in ['span', 'div']:
            for elem in job_element.find_all(tag):
                text = elem.get_text(strip=True)
                if (2 < len(text) < 35 and 
                    len(text.split()) <= 4 and
                    text[0].isupper() and
                    self._is_valid_company_name(text, job_title)):
                    return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_element):
        """Extract job title from APEC"""
        selectors = [
            ('h2', {'class': lambda x: x and 'title' in str(x).lower()}),
            ('h3', {'class': lambda x: x and 'title' in str(x).lower()}),
            ('span', {'class': lambda x: x and 'card-offer__title' in str(x)}),
            ('a', {'class': lambda x: x and 'offer-title' in str(x).lower()}),
            ('h2', {}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 3:
                    return text
        
        return "Unknown Position"

    def _extract_location(self, job_element):
        """Extract job location"""
        selectors = [
            ('span', {'class': lambda x: x and 'location' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'location' in str(x).lower()}),
            ('span', {'class': lambda x: x and 'card-offer__location' in str(x)}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                return elem.get_text(strip=True)
        
        return "Paris"

    def _extract_job_link(self, job_element):
        """Extract job link"""
        # Look for links to job details
        link_selectors = [
            ('a', {'href': lambda x: x and '/offre-emploi/' in str(x)}),
            ('a', {'class': lambda x: x and 'offer-link' in str(x).lower()}),
            ('a', {'data-link': True}),
        ]
        
        for tag, attrs in link_selectors:
            link_elem = job_element.find(tag, attrs)
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('/'):
                    return 'https://www.apec.fr' + href
                return href
        
        # Fallback: any link
        link_elem = job_element.find('a', href=True)
        if link_elem and link_elem.get('href'):
            href = link_elem['href']
            if '/offre-emploi/' in href:
                if href.startswith('/'):
                    return 'https://www.apec.fr' + href
                return href
        
        return None

    def scrap(self):
        page = 0
        jobs_found_this_run = 0

        while True:
            print(f"\n{'='*50}")
            print(f"APEC - Page {page + 1}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            self._init_driver(self.page_url)
            page_data = self._get_chrome_page_data()
            
            # Save debug HTML on first page
            if page == 0:
                with open('/tmp/apec_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/apec_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # APEC job cards
            job_listings = []
            
            selectors_to_try = [
                ('div', {'class': lambda x: x and 'offer-card' in str(x).lower()}),
                ('div', {'class': lambda x: x and 'card-offer' in str(x).lower()}),
                ('li', {'class': lambda x: x and 'offer' in str(x).lower()}),
                ('article', {}),
            ]
            
            for tag, attrs in selectors_to_try:
                job_listings = page_soup.find_all(tag, attrs)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs with selector: {tag}, {attrs}")
                    break
            
            if not job_listings or page >= 3:  # Limit to 3 pages
                print("No more jobs found or page limit reached")
                break

            print(f"Processing {len(job_listings)} jobs...")
            
            for i, job in enumerate(job_listings):
                try:
                    print(f"\n--- Job {i+1}/{len(job_listings)} ---")
                    
                    # Extract job title first
                    job_name = self._extract_job_title(job)
                    print(f"Job: {job_name}")
                    
                    # Extract company
                    job_company = self._extract_company_name(job, job_title=job_name)
                    print(f"Company: {job_company}")
                    
                    # Extract location
                    job_location = self._extract_location(job)
                    print(f"Location: {job_location}")
                    
                    # Extract link
                    job_link = self._extract_job_link(job)
                    if not job_link:
                        print("No link found, skipping")
                        continue
                    print(f"Link: {job_link}")
                    
                    # Check database
                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
                        description = f"{job_name} - {job_company} - {job_location}"
                        
                        embed = create_embed(job_name, job_company, job_location, job_link, '')
                        
                        success = send_embed(embed, self, job_name, job_company, job_location, job_link, '', description)
                        
                        if success:
                            jobs_found_this_run += 1
                        time.sleep(4)
                    else:
                        print("✗ Already in database")
                        
                except Exception as e:
                    print(f"Error processing job: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f'APEC page finished - New jobs this page: {jobs_found_this_run}')
            page += 1
            
        print(f"\n{'='*50}")
        print(f"APEC complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
