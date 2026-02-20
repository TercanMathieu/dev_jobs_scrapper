import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class WTTJ(Website):

    def __init__(self):
        super().__init__(
            'Welcome to the Jungle',
            'https://www.welcometothejungle.com/fr/jobs?page={}&aroundLatLng=48.85717%2C2.3414&aroundRadius=20&aroundQuery=Paris%2C%20France&sortBy=mostRecent&refinementList%5Bprofession.sub_category_reference%5D%5B%5D=software-web-development-iMzA4',
            'WTTJ JOBS',
            'https://www.startupbegins.com/wp-content/uploads/2018/05/Logo-Welcome-to-the-Jungle.jpg',
            True,
        )

    def _is_valid_company_name(self, text, job_title=None):
        """Check if text is a valid company name (not a phrase or generic text)"""
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        # If we have a job title, make sure the text is not the same or similar
        if job_title:
            # Normalize for comparison
            text_norm = text.lower().strip()
            title_norm = job_title.lower().strip()
            if text_norm == title_norm:
                return False
            # Also reject if text is contained in job title (common substring)
            if text_norm in title_norm and len(text_norm) > 8:
                return False
        
        # List of invalid patterns/phrases that are NOT company names
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
            'france', 'europe',
        ]
        
        # Job title keywords that should NOT be in company names
        job_title_keywords = [
            'développeur', 'developpeur', 'developer', 'dev ',
            'ingénieur', 'ingenieur', 'engineer',
            'frontend', 'backend', 'fullstack', 'full-stack',
            'software', 'web', 'mobile', 'cloud',
            'data', 'machine learning', 'ia ', 'ai ',
            'product owner', 'scrum master', 'tech lead',
            'architect', 'architecte', 'lead ', 'senior', 'junior',
            'stage', 'alternance', 'apprenti',
            'h/f', 'f/h', '(h/f)', '(f/h)',
            'php', 'python', 'javascript', 'react', 'node',
            'java', 'go ', 'rust', 'ruby', 'scala',
        ]
        
        text_lower = text.lower()
        for pattern in invalid_patterns:
            if pattern in text_lower:
                return False
        
        for keyword in job_title_keywords:
            if keyword in text_lower:
                return False
        
        # Check if it's all uppercase (often job titles or labels)
        if text.isupper() and len(text) > 10:
            return False
            
        # Check if it contains too many numbers (dates, codes)
        digit_count = sum(c.isdigit() for c in text)
        if digit_count > 3:
            return False
        
        return True

    def _extract_company_name(self, job_element, job_title=None):
        """Extract company name with multiple fallback selectors and validation"""
        
        # First try: Look for specific company attributes
        company_elem = job_element.find(attrs={'data-testid': lambda x: x and 'company' in str(x).lower()})
        if company_elem:
            text = company_elem.get_text(strip=True)
            if self._is_valid_company_name(text, job_title):
                return text
        
        # Second try: Look for aria-label containing company info
        for elem in job_element.find_all(attrs={'aria-label': True}):
            aria = elem['aria-label']
            if 'chez' in aria.lower() or 'at' in aria.lower():
                # Extract company name from aria-label like "Développeur chez Company"
                parts = aria.split('chez') if 'chez' in aria else aria.split('at')
                if len(parts) > 1:
                    company = parts[-1].strip()
                    if self._is_valid_company_name(company, job_title):
                        return company
        
        # Third try: Look for specific CSS patterns
        company_patterns = [
            'sc-izXThL',  # Common WTTJ class pattern
            'wui-text',
            'company',
            'employer',
        ]
        
        for pattern in company_patterns:
            elems = job_element.find_all(class_=lambda x: x and pattern in str(x))
            for elem in elems:
                text = elem.get_text(strip=True)
                # Company names on WTTJ are typically:
                # - Short (2-40 chars)
                # - Title case or mixed case (not all caps)
                # - Not containing job-related keywords
                if self._is_valid_company_name(text, job_title):
                    # Additional check: should be shorter than typical job titles
                    if len(text) < 35 and len(text.split()) <= 5:
                        return text
        
        # Fourth try: Look for any span or div with short text that could be company
        # This is the fallback - be extra strict here
        for tag in ['span', 'div', 'p']:
            elems = job_element.find_all(tag)
            for elem in elems:
                text = elem.get_text(strip=True)
                # Very strict validation for fallback
                # Company names should be SHORT (2-25 chars ideally)
                # and NOT match job title at all
                if (2 < len(text) < 25 and 
                    len(text.split()) <= 3 and
                    text[0].isupper() and
                    not text.isupper() and  # Not all caps
                    self._is_valid_company_name(text, job_title)):
                    return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_element):
        """Extract job title with multiple fallback selectors"""
        selectors = [
            ('h2', {}),
            ('h3', {}),
            ('h1', {}),
            ('a', {'data-testid': lambda x: 'title' in x.lower() if x else False}),
            ('span', {'class': lambda x: x and 'title' in x.lower() if x else False}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.text.strip()
                if len(text) > 5:  # Job titles are usually longer
                    return text
        
        return "Unknown Position"

    def _extract_job_link(self, job_element):
        """Extract job link"""
        # Find any link that contains job details
        links = job_element.find_all('a', href=True)
        for link in links:
            href = link['href']
            # Look for job links
            if '/jobs/' in href or '/companies/' in href:
                if href.startswith('http'):
                    return href
                else:
                    return 'https://welcometothejungle.com' + href
        return None

    def scrap(self):
        page = 1
        jobs_found_this_run = 0

        while True:
            print(f"\n{'='*50}")
            print(f"WTTJ - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            self._init_driver(self.page_url)
            page_data = self._get_chrome_page_data()
            
            # Save debug HTML on first page
            if page == 1:
                with open('/tmp/wttj_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/wttj_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # Try multiple selectors for job listings
            all_jobs_raw = page_soup.find_all('li', attrs={'data-testid': 'search-results-list-item-wrapper'})
            
            if not all_jobs_raw:
                # Try alternative selectors
                all_jobs_raw = page_soup.find_all('article')
            if not all_jobs_raw:
                all_jobs_raw = page_soup.find_all('div', {'class': lambda x: x and 'job' in x.lower() if x else False})
            
            print(f"Found {len(all_jobs_raw)} job elements")
            
            if len(all_jobs_raw) == 0 or page >= 4:
                print("No more jobs found or page limit reached")
                break

            for i, job in enumerate(all_jobs_raw):
                try:
                    print(f"\n--- Job {i+1}/{len(all_jobs_raw)} ---")
                    
                    # Extract job title FIRST
                    job_name = self._extract_job_title(job)
                    print(f"Job: {job_name}")

                    # Extract company - pass job title to avoid collision
                    job_company = self._extract_company_name(job, job_title=job_name)
                    print(f"Company: {job_company}")

                    # Extract link
                    job_link = self._extract_job_link(job)
                    if not job_link:
                        print("No link found, skipping")
                        continue
                    print(f"Link: {job_link}")

                    # Extract thumbnail
                    job_thumbnail = ''
                    img = job.find('img')
                    if img and img.get('src'):
                        job_thumbnail = img['src']

                    # Check if already in DB
                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
                        embed = create_embed(job_name, job_company, 'Paris', job_link, job_thumbnail)
                        description = f"{job_name} {job_company}"
                        
                        success = send_embed(embed, self, job_name, job_company, 'Paris', job_link, job_thumbnail, description)
                        
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

            print(f'WTTJ page #{page} finished - New jobs this page: {jobs_found_this_run}')
            page += 1
            
        print(f"\n{'='*50}")
        print(f"WTTJ complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
