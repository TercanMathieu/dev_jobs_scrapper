import time
import re
from urllib.parse import quote
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class Indeed(Website):
    """Scraper for Indeed France"""

    def __init__(self):
        super().__init__(
            'Indeed France',
            'https://fr.indeed.com/jobs?q=developpeur+software&l=Paris&sort=date&start={}',
            'INDEED JOBS',
            'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Indeed_logo.svg/1200px-Indeed_logo.svg.png',
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
            'paris', 'lyon', 'marseille', 'bordeaux', 'lille',
            'france', 'europe', 'salaire', 'salary',
        ]
        
        job_keywords = [
            'développeur', 'developpeur', 'developer', 'dev ',
            'ingénieur', 'ingenieur', 'engineer',
            'frontend', 'backend', 'fullstack', 'full-stack',
            'software', 'web', 'mobile', 'cloud',
            'data', 'machine learning', 'ia ', 'ai ',
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
        """Extract company name from Indeed job element"""
        
        # Indeed specific: company name is usually in a span with specific class
        selectors = [
            ('span', {'data-testid': 'company-name'}),
            ('span', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('span', {'class': lambda x: x and 'css-1cxc9zk' in x if x else False}),  # Indeed class pattern
            ('div', {'data-testid': 'company-name'}),
            ('span', {'class': lambda x: x and 'css-' in str(x) and 'company' in str(x).lower()}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Look for company in aria-label
        for elem in job_element.find_all(attrs={'aria-label': True}):
            aria = elem['aria-label'].lower()
            if 'company' in aria or 'entreprise' in aria:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Fallback: look for company-like text in spans/divs
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
        """Extract job title from Indeed"""
        selectors = [
            ('h2', {'class': lambda x: x and 'title' in str(x).lower()}),
            ('a', {'class': lambda x: x and 'jcs-JobTitle' in str(x)}),
            ('span', {'id': lambda x: x and 'jobTitle' in str(x)}),
            ('h2', {}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                # Get title from aria-label or text
                if elem.get('aria-label'):
                    text = elem['aria-label'].strip()
                else:
                    text = elem.get_text(strip=True)
                
                # Clean up Indeed title format
                text = re.sub(r'^nouveau\s+', '', text, flags=re.IGNORECASE)
                if len(text) > 3:
                    return text
        
        return "Unknown Position"

    def _extract_location(self, job_element):
        """Extract job location"""
        selectors = [
            ('div', {'data-testid': 'job-location'}),
            ('span', {'data-testid': 'job-location'}),
            ('div', {'class': lambda x: x and 'location' in str(x).lower()}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                return elem.get_text(strip=True)
        
        return "Paris"

    def _extract_job_link(self, job_element):
        """Extract job link"""
        # Find the main job link
        link_elem = job_element.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('/'):
                return 'https://fr.indeed.com' + href
            elif href.startswith('http'):
                return href
        return None

    def _extract_salary(self, job_element):
        """Extract salary if available"""
        salary_elem = job_element.find('div', {'class': lambda x: x and 'salary' in str(x).lower()})
        if salary_elem:
            return salary_elem.get_text(strip=True)
        
        # Look for salary in metadata
        for elem in job_element.find_all('span'):
            text = elem.get_text(strip=True)
            if '€' in text or 'euro' in text.lower() or 'k' in text.lower():
                if any(char.isdigit() for char in text):
                    return text
        return None

    def scrap(self):
        page = 0  # Indeed uses 0, 10, 20, 30...
        jobs_found_this_run = 0

        while True:
            print(f"\n{'='*50}")
            print(f"INDEED - Page {page//10 + 1}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            self._init_driver(self.page_url)
            page_data = self._get_chrome_page_data()
            
            # Save debug HTML on first page
            if page == 0:
                with open('/tmp/indeed_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/indeed_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # Indeed job cards
            job_listings = []
            
            # Try multiple selectors for Indeed job cards
            selectors_to_try = [
                ('div', {'class': lambda x: x and 'job_seen_beacon' in x}),
                ('div', {'data-testid': 'job-title'}),
                ('div', {'class': lambda x: x and 'slider_container' in str(x)}),
                ('div', {'class': lambda x: x and 'slider' in str(x) and 'item' in str(x)}),
                ('li', {'class': lambda x: x and 'css-5lfssm' in str(x)}),
            ]
            
            for tag, attrs in selectors_to_try:
                job_listings = page_soup.find_all(tag, attrs)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs with selector: {tag}, {attrs}")
                    break
            
            # Alternative: look for any element containing job data
            if not job_listings:
                job_listings = page_soup.find_all('div', {'class': lambda x: x and 'job' in str(x).lower()})
            
            if not job_listings or page >= 30:  # Limit to 3 pages
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
                    
                    # Extract salary if available
                    salary = self._extract_salary(job)
                    if salary:
                        print(f"Salary: {salary}")
                    
                    # Check database
                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
                        # Build description
                        description = f"{job_name} - {job_company} - {job_location}"
                        if salary:
                            description += f" - {salary}"
                        
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

            print(f'Indeed page finished - New jobs this page: {jobs_found_this_run}')
            page += 10  # Indeed pagination is 0, 10, 20, 30...
            
        print(f"\n{'='*50}")
        print(f"Indeed complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
