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

    def _extract_company_name(self, job_element):
        """Extract company name with multiple fallback selectors"""
        # Try different selectors for company name
        selectors = [
            ('span', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('span', {'data-testid': lambda x: 'company' in x.lower() if x else False}),
            ('p', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('div', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            # Look for any text that might be company name before job title
            ('span', {}),
        ]
        
        for tag, attrs in selectors:
            elements = job_element.find_all(tag, attrs)
            for elem in elements:
                text = elem.text.strip()
                # Company names are usually short (2-50 chars)
                if 2 < len(text) < 50 and text.isupper() == False:
                    # Avoid job titles which are usually longer
                    if len(text.split()) <= 6:
                        return text
        
        return "Unknown Company"

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
                    
                    # Extract company
                    job_company = self._extract_company_name(job)
                    print(f"Company: {job_company}")

                    # Extract job title
                    job_name = self._extract_job_title(job)
                    print(f"Job: {job_name}")

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
