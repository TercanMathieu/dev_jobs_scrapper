import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website
from urllib.parse import unquote

class JobTeaser(Website):

    def __init__(self):
        super().__init__(
            'Job Teaser',
            'https://www.jobteaser.com/fr/job-offers?p={}&contract=cdd,cdi&position_category_uuid=ddc0460c-ce0b-4d98-bc5d-d8829ff9cf11&location=France%3A%3A%C3%8Ele-de-France..%C3%8Ele-de-France%20(France)&locale=en,fr',
            'JOB TEASER JOBS',
            'https://d1guu6n8gz71j.cloudfront.net/system/asset/logos/27460/logo_mobile.png',
            False
            )

    def _click_agree_button(self):
        """Click the cookie consent button if present"""
        try:
            # Attendre un peu que la bannière apparaisse
            time.sleep(2)
            agree_button = self.driver.find_element(By.XPATH,'//*[@id="didomi-notice-agree-button"]')
            agree_button.click()
            print("Clicked on cookie consent button.")
            time.sleep(1)  # Attendre que la page se mette à jour
        except Exception:
            # Le bouton n'est pas toujours présent, c'est OK
            print("No cookie button found, continuing...")

    def _wait_for_jobs_to_load(self):
        """Wait for job cards to be loaded"""
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="jobad-card"]'))
            )
            print("Job cards loaded successfully")
            return True
        except Exception as e:
            print(f"Timeout waiting for job cards: {e}")
            return False

    def scrap(self):
        page = 0
        total_jobs_found = 0
        
        while True:
            print(f"\n{'='*50}")
            print(f"Job Teaser - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading URL: {self.page_url}")
            
            self._init_driver(self.page_url)
            
            # Handle cookie banner
            self._click_agree_button()
            
            # Wait for jobs to load
            if not self._wait_for_jobs_to_load():
                print("No jobs found on this page, stopping.")
                break
            
            # Get page data
            page_data = self._get_chrome_page_data()
            
            # Debug: save HTML for inspection
            if page == 0:
                with open('/tmp/jobteaser_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/jobteaser_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # Try multiple selectors for job container
            job_ads_wrapper = page_soup.find('ul', {'data-testid': 'job-ads-wrapper'})
            if job_ads_wrapper is None:
                # Try alternative selectors
                job_ads_wrapper = page_soup.find('ul', {'data-testid': 'search-results-list'})
            
            if job_ads_wrapper is None:
                print("Job Teaser's page #{} has no job ads wrapper.".format(page))
                # Debug: print what we found
                all_uls = page_soup.find_all('ul')
                print(f"Found {len(all_uls)} ul elements")
                for i, ul in enumerate(all_uls[:3]):
                    print(f"  UL {i}: {ul.get('data-testid', 'no-testid')}")
                break
       
            # Find all jobs
            all_jobs_raw = job_ads_wrapper.find_all('div', {'data-testid': 'jobad-card'})
            
            if len(all_jobs_raw) == 0:
                print("No job cards found in wrapper")
                break
                
            if page >= 3:  # Limit to 3 pages
                print("Reached page limit, stopping.")
                break
                
            print(f"\nProcessing {len(all_jobs_raw)} jobs...")
            
            for i, jobs in enumerate(all_jobs_raw):
                try:
                    print(f"\n--- Job {i+1}/{len(all_jobs_raw)} ---")
                    
                    # Find company name - try multiple selectors
                    job_company = self._extract_company(jobs)
                    if not job_company:
                        print('Could not find company name, skipping job')
                        continue
                    print(f'Company: {job_company}')

                    # Find job title - try multiple selectors
                    job_name, job_link = self._extract_job_title_and_link(jobs)
                    if not job_name or not job_link:
                        print('Could not find job title/link, skipping job')
                        continue
                    print(f'Job: {job_name}')
                    print(f'Link: {job_link}')

                    # Find thumbnail
                    job_thumbnail = self._extract_thumbnail(jobs)

                    # Check and save
                    if not is_url_in_database(job_link):
                        print(f"✓ New job found!")
                        add_url_in_database(job_link)
                        embed = create_embed(job_name, job_company, 'Paris', job_link, job_thumbnail)
                        description = f"{job_name} {job_company}"
                        send_embed(embed, self, job_name, job_company, 'Paris', job_link, job_thumbnail, description)
                        total_jobs_found += 1
                        time.sleep(4)
                    else:
                        print(f"✗ Job already in database")
                        
                except Exception as e:
                    print(f"Error processing job: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f'\nJob Teaser page #{page} finished - Total jobs this run: {total_jobs_found}')
            page += 1
            
        print(f"\n{'='*50}")
        print(f"Job Teaser scraping complete. Total new jobs: {total_jobs_found}")
        print(f"{'='*50}")

    def _is_valid_company_name(self, text):
        """Check if text is a valid company name (not a phrase or generic text)"""
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
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
        
        text_lower = text.lower()
        for pattern in invalid_patterns:
            if pattern in text_lower:
                return False
        
        if text.isupper() and len(text) > 10:
            return False
            
        digit_count = sum(c.isdigit() for c in text)
        if digit_count > 3:
            return False
        
        return True

    def _extract_company(self, job_element):
        """Extract company name with fallback selectors and validation"""
        # Try specific testid first
        company_elem = job_element.find('p', {'data-testid': 'jobad-card-company-name'})
        if company_elem:
            text = company_elem.get_text(strip=True)
            if self._is_valid_company_name(text):
                return text
        
        # Try other selectors
        selectors = [
            ('span', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('div', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('span', {'class': lambda x: x and 'name' in x.lower() if x else False}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text):
                    return text
        
        # Fallback: look for short text in the card
        for elem in job_element.find_all(['span', 'p', 'div']):
            text = elem.get_text(strip=True)
            if (2 < len(text) < 35 and 
                len(text.split()) <= 4 and
                text[0].isupper() and
                self._is_valid_company_name(text)):
                return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title_and_link(self, job_element):
        """Extract job title and link with fallback selectors"""
        # Try different link selectors
        selectors = [
            ('a', {'class': lambda x: x and 'JobAdCard_link' in x if x else False}),
            ('a', {'data-testid': 'jobad-card-title'}),
            ('a', {'href': True}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem and elem.get('href'):
                title = elem.text.strip()
                href = elem['href']
                if href.startswith('/'):
                    href = 'https://www.jobteaser.com' + href
                return title, href
        
        return None, None

    def _extract_thumbnail(self, job_element):
        """Extract thumbnail with fallback selectors"""
        selectors = [
            ('img', {'data-testid': 'jobad-card-company-logo'}),
            ('img', {'class': lambda x: x and 'logo' in x.lower() if x else False}),
            ('img', {}),
        ]
        
        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem and elem.get('src'):
                thumbnail_url = elem['src']
                if 'url=' in thumbnail_url:
                    return unquote(thumbnail_url.split("url=")[1].split("&")[0])
                return thumbnail_url
        
        return ''
