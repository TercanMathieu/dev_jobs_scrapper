import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class Indeed(Website):
    """Scraper for Indeed France - Note: Indeed has strong bot detection"""

    def __init__(self):
        super().__init__(
            'Indeed France',
            'https://fr.indeed.com/jobs?q=developpeur+software&l=Paris&sort=date&start={}',
            'INDEED JOBS',
            'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Indeed_logo.svg/1200px-Indeed_logo.svg.png',
            True,
        )
        # Add extra Chrome options to avoid bot detection
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
            'télétravail', 'remote', 'hybride', 'hybrid',
            'paris', 'lyon', 'marseille', 'bordeaux', 'lille',
            'france', 'salaire', 'salary',
        ]
        
        job_keywords = [
            'développeur', 'developpeur', 'developer', 'dev ',
            'ingénieur', 'ingenieur', 'engineer',
            'frontend', 'backend', 'fullstack', 'full-stack',
            'software', 'web', 'mobile',
        ]
        
        text_lower = text.lower()
        for pattern in invalid_patterns + job_keywords:
            if pattern in text_lower:
                return False
        
        if text.isupper() and len(text) > 10:
            return False
            
        return True

    def _extract_company_name(self, job_element, job_title=None):
        """Extract company name from Indeed job element"""
        
        # Try data-testid first (modern Indeed)
        company_elem = job_element.find(attrs={'data-testid': 'company-name'})
        if company_elem:
            text = company_elem.get_text(strip=True)
            if self._is_valid_company_name(text, job_title):
                return text
        
        # Try aria-label containing company
        for elem in job_element.find_all(attrs={'aria-label': True}):
            aria = elem['aria-label']
            if 'company' in aria.lower() or 'employeur' in aria.lower():
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Try to find company in spans/divs that are not the title
        # Company names on Indeed are typically short and near the title
        for elem in job_element.find_all(['span', 'div']):
            # Skip if it's likely the title
            if elem.find(['h2', 'h3']) or elem.get('data-testid') == 'job-title':
                continue
                
            text = elem.get_text(strip=True)
            # Company names are typically:
            # - Between 2 and 40 chars
            # - Not all uppercase  
            # - Start with uppercase
            if (2 < len(text) < 40 and 
                not text.isupper() and
                text[0].isupper() and
                len(text.split()) <= 5 and
                self._is_valid_company_name(text, job_title)):
                return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_element):
        """Extract job title from Indeed"""
        # Modern Indeed uses data-testid
        title_elem = job_element.find(attrs={'data-testid': 'job-title'})
        if title_elem:
            text = title_elem.get_text(strip=True)
            if len(text) > 3:
                return text
        
        # Try aria-label
        for elem in job_element.find_all(attrs={'aria-label': True}):
            aria = elem['aria-label']
            if len(aria) > 5 and len(aria) < 150:
                # Clean up
                text = re.sub(r'^nouveau\s+', '', aria, flags=re.IGNORECASE)
                return text.strip()
        
        # Try h2 (often contains job title on Indeed)
        h2 = job_element.find('h2')
        if h2:
            text = h2.get_text(strip=True)
            # Remove "nouveau" prefix if present
            text = re.sub(r'^nouveau\s+', '', text, flags=re.IGNORECASE)
            if len(text) > 3:
                return text
        
        return "Unknown Position"

    def _extract_location(self, job_element):
        """Extract job location"""
        # Modern Indeed
        loc_elem = job_element.find(attrs={'data-testid': 'job-location'})
        if loc_elem:
            return loc_elem.get_text(strip=True)
        
        # Try to find location pattern
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            # Location often contains these patterns
            if any(city in text.lower() for city in ['paris', 'lyon', 'marseille', 'bordeaux', 'lille', 'france']):
                if len(text) < 60:
                    return text
        
        return "Paris"

    def _extract_job_link(self, job_element):
        """Extract job link"""
        # Find any link
        for link in job_element.find_all('a', href=True):
            href = link['href']
            if '/rc/clk' in href or '/pagead/' in href or '/viewjob' in href:
                if href.startswith('/'):
                    return 'https://fr.indeed.com' + href
                return href
        return None

    def _extract_salary(self, job_element):
        """Extract salary if available"""
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            if '€' in text or 'euro' in text.lower():
                if any(char.isdigit() for char in text):
                    return text
        return None

    def scrap(self):
        page = 0
        jobs_found_this_run = 0

        while True:
            print(f"\n{'='*50}")
            print(f"INDEED - Page {page//10 + 1}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            try:
                self._init_driver(self.page_url)
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error loading page: {e}")
                break
            
            # Check if we got blocked
            if 'cf-browser-verification' in page_data.lower() or 'ray id' in page_data.lower():
                print("WARNING: Cloudflare detected - Indeed is blocking the bot")
                # Save debug to see what we got
                with open('/tmp/indeed_blocked.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                break
            
            # Save debug HTML on first page
            if page == 0:
                with open('/tmp/indeed_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/indeed_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # Indeed job cards - be very flexible with selectors
            job_listings = []
            
            # Try many different selectors
            selectors_to_try = [
                ('div', {'data-testid': 'job-title'}),  # Modern Indeed
                ('div', {'class': lambda x: x and 'job_seen_beacon' in str(x)}),
                ('div', {'class': lambda x: x and 'slider_container' in str(x)}),
                ('div', {'class': lambda x: x and 'slider' in str(x) and 'item' in str(x)}),
                ('div', {'class': lambda x: x and 'tapItem' in str(x)}),
                ('a', {'class': lambda x: x and 'tapItem' in str(x)}),
            ]
            
            for tag, attrs in selectors_to_try:
                job_listings = page_soup.find_all(tag, attrs)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs with selector: {tag}")
                    break
            
            # If still nothing, try to find any job-like structure
            if not job_listings:
                # Look for elements containing job-related text
                potential_jobs = []
                for elem in page_soup.find_all(['div', 'a']):
                    text = elem.get_text(strip=True).lower()
                    if any(word in text for word in ['développeur', 'developer', 'engineer', 'software']):
                        if elem.find('a') or elem.get('href'):
                            potential_jobs.append(elem)
                
                if potential_jobs:
                    print(f"Found {len(potential_jobs)} potential jobs via text search")
                    job_listings = potential_jobs
            
            if not job_listings:
                print("No job listings found on this page")
                # Save the page for debugging
                with open(f'/tmp/indeed_page_{page}.html', 'w', encoding='utf-8') as f:
                    f.write(page_data[:50000])  # First 50KB
                
            if not job_listings or page >= 20:  # Limit to 2 pages
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
                    
                    # Extract salary if available
                    salary = self._extract_salary(job)
                    if salary:
                        print(f"Salary: {salary}")
                    
                    # Check database
                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
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

            print(f'Indeed page finished - Total new jobs: {jobs_found_this_run}')
            page += 10
            
        print(f"\n{'='*50}")
        print(f"Indeed complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
