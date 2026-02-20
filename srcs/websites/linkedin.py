import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class LinkedIn(Website):
    """Scraper for LinkedIn Jobs - Note: LinkedIn requires login for most content"""

    def __init__(self):
        super().__init__(
            'LinkedIn',
            'https://www.linkedin.com/jobs/search?keywords=D%C3%A9veloppeur%20Software&location=Paris%2C%20France&geoId=105015875&f_TPR=r86400&start={}',
            'LINKEDIN JOBS',
            'https://content.linkedin.com/content/dam/me/business/en-us/amp/brand-site/v2/bg/LI-Logo.svg.original.svg',
            True,
        )
        # Add extra Chrome options
        self.extra_chrome_options = [
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--accept-lang=fr-FR,fr',
        ]

    def _is_valid_company_name(self, text, job_title=None):
        """Check if text is a valid company name"""
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        if job_title:
            text_norm = text.lower().strip()
            title_norm = job_title.lower().strip()
            if text_norm == title_norm:
                return False
            if text_norm in title_norm and len(text_norm) > 8:
                return False
        
        invalid_patterns = [
            'recrutement', 'recrute', 'recruiting', 'hiring',
            'publié', 'published', 'posté', 'posted',
            'il y a', 'ago', 'days', 'jours',
            ' CDI', ' CDD', ' stage', ' alternance',
        ]
        
        job_keywords = [
            'développeur', 'developpeur', 'developer', 'dev ',
            'ingénieur', 'ingenieur', 'engineer',
            'frontend', 'backend', 'fullstack', 'full-stack',
            'software', 'web', 'mobile', 'cloud',
        ]
        
        text_lower = text.lower()
        for pattern in invalid_patterns + job_keywords:
            if pattern in text_lower:
                return False
        
        if text.isupper() and len(text) > 10:
            return False
            
        return True

    def _extract_company_name(self, job_element, job_title=None):
        """Extract company name from LinkedIn job element"""
        
        # LinkedIn often has company in specific classes
        selectors = [
            ('span', {'class': lambda x: x and 'company' in str(x).lower()}),
            ('a', {'class': lambda x: x and 'company' in str(x).lower()}),
            ('h4', {'class': lambda x: x and 'company' in str(x).lower()}),
            ('span', {'class': 'base-search-card__subtitle'}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Fallback: look for text that looks like a company name
        for elem in job_element.find_all(['span', 'a', 'h4']):
            text = elem.get_text(strip=True)
            if (2 < len(text) < 40 and 
                len(text.split()) <= 4 and
                not text.isupper() and
                text[0].isupper() and
                self._is_valid_company_name(text, job_title)):
                return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_element):
        """Extract job title from LinkedIn"""
        selectors = [
            ('h3', {'class': lambda x: x and 'title' in str(x).lower()}),
            ('span', {'class': lambda x: x and 'job-card-container__link' in str(x)}),
            ('h3', {'class': 'base-search-card__title'}),
            ('h3', {}),
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
            ('span', {'class': 'job-card-container__metadata-item'}),
            ('span', {'class': 'base-search-card__metadata'}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                return elem.get_text(strip=True)
        
        return "Paris"

    def _extract_job_link(self, job_element):
        """Extract job link"""
        for link in job_element.find_all('a', href=True):
            href = link['href']
            if '/jobs/view/' in href:
                if href.startswith('/'):
                    return 'https://www.linkedin.com' + href
                return href
        return None

    def _extract_thumbnail(self, job_element):
        """Extract company logo/thumbnail from LinkedIn job element"""
        # LinkedIn company logos are typically in img tags
        img_selectors = [
            ('img', {'class': lambda x: x and 'company' in str(x).lower() and 'logo' in str(x).lower()}),
            ('img', {'class': lambda x: x and 'entity-image' in str(x)}),
            ('img', {'class': lambda x: x and 'artdeco-entity-image' in str(x)}),
            ('img', {'src': lambda x: x and 'company-logo' in str(x)}),
        ]
        
        for tag, attrs in img_selectors:
            img = job_element.find(tag, attrs)
            if img and img.get('src'):
                src = img['src']
                # LinkedIn logos often have different sizes, get the best one
                if 'shrink' in src or 'logo' in src.lower():
                    return src
        
        # Try data-src lazy loaded images
        for img in job_element.find_all('img'):
            src = img.get('data-src') or img.get('src', '')
            if src and ('company' in src.lower() or 'logo' in src.lower()):
                return src
        
        return ''

    def scrap(self):
        page = 0
        jobs_found_this_run = 0

        while True:
            print(f"\n{'='*50}")
            print(f"LINKEDIN - Page {page//25 + 1}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            try:
                self._init_driver(self.page_url)
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error loading page: {e}")
                break
            
            # Check if we need to login (LinkedIn blocks without login)
            if 'sign in' in page_data.lower() and 'join now' in page_data.lower():
                print("WARNING: LinkedIn requires login - cannot scrape without authentication")
                with open('/tmp/linkedin_blocked.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                break
            
            # Save debug HTML on first page
            if page == 0:
                with open('/tmp/linkedin_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/linkedin_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # LinkedIn job cards
            job_listings = []
            
            selectors_to_try = [
                ('div', {'class': lambda x: x and 'job-card-container' in str(x)}),
                ('li', {'class': lambda x: x and 'jobs-search-results__list-item' in str(x)}),
                ('div', {'class': lambda x: x and 'base-card' in str(x)}),
                ('div', {'data-job-id': True}),
                ('div', {'class': lambda x: x and 'job-search-card' in str(x)}),
            ]
            
            for tag, attrs in selectors_to_try:
                job_listings = page_soup.find_all(tag, attrs)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs with selector: {tag}")
                    break
            
            # Alternative: find by job links
            if not job_listings:
                job_links = page_soup.find_all('a', href=re.compile(r'/jobs/view/'))
                job_listings = [link.find_parent(['div', 'li', 'article']) for link in job_links if link.find_parent()]
                job_listings = [j for j in job_listings if j]
                if job_listings:
                    print(f"Found {len(job_listings)} jobs via link search")
            
            if not job_listings or page >= 25:  # Limit to ~1 page
                print("No more jobs found or page limit reached")
                break

            print(f"Processing {len(job_listings)} jobs...")
            
            for i, job in enumerate(job_listings):
                try:
                    print(f"\n--- Job {i+1}/{len(job_listings)} ---")
                    
                    # Extract job title first
                    job_name = self._extract_job_title(job)
                    if job_name == "Unknown Position":
                        print("Could not extract job title, skipping")
                        continue
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
                    
                    # Extract thumbnail
                    job_thumbnail = self._extract_thumbnail(job)
                    if job_thumbnail:
                        print(f"Thumbnail: {job_thumbnail[:80]}...")
                    
                    # Check database
                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
                        description = f"{job_name} - {job_company} - {job_location}"
                        
                        embed = create_embed(job_name, job_company, job_location, job_link, job_thumbnail)
                        
                        success = send_embed(embed, self, job_name, job_company, job_location, job_link, job_thumbnail, description)
                        
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

            print(f'LinkedIn page finished - Total new jobs: {jobs_found_this_run}')
            page += 25
            
        print(f"\n{'='*50}")
        print(f"LinkedIn complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
