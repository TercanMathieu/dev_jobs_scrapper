import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import unquote

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class JobTeaser(Website):
    """Scraper pour JobTeaser - Approche robuste 2025"""

    def __init__(self):
        super().__init__(
            'Job Teaser',
            'https://www.jobteaser.com/fr/job-offers?p={}&contract=cdd,cdi&position_category_uuid=ddc0460c-ce0b-4d98-bc5d-d8829ff9cf11&location=France%3A%3A%C3%8Ele-de-France..%C3%8Ele-de-France%20(France)&locale=en,fr',
            'JOB TEASER JOBS',
            'https://d1guu6n8gz71j.cloudfront.net/system/asset/logos/27460/logo_mobile.png',
            False
        )
        self.page_load_timeout = 30

    def _click_agree_button(self):
        """Click the cookie consent button if present"""
        try:
            time.sleep(2)
            agree_button = self.driver.find_element(By.XPATH, '//*[@id="didomi-notice-agree-button"]')
            agree_button.click()
            print("Clicked on cookie consent button.")
            time.sleep(1)
        except Exception:
            print("No cookie button found, continuing...")

    def _wait_for_jobs_to_load(self):
        """Wait for job cards to be loaded"""
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="jobad-card"], article, .job-card, [class*="job"]'))
            )
            time.sleep(3)
            print("Job cards loaded successfully")
            return True
        except Exception as e:
            print(f"Timeout waiting for job cards: {e}")
            return False

    def _is_valid_company_name(self, text, job_title=None):
        """Check if text is a valid company name"""
        if not text or len(text) < 2 or len(text) > 60:
            return False

        text_lower = text.lower()

        if job_title and text_lower == job_title.lower():
            return False

        invalid_patterns = [
            'recrutement', 'recrute', 'recruiting', 'hiring',
            'publié', 'published', 'posté', 'posted',
            'il y a', 'ago', 'days', 'jours',
            ' CDI', ' CDD', ' stage', ' alternance',
            'temps plein', 'temps partiel', 'full time', 'part time',
            'télétravail', 'remote', 'hybride', 'hybrid',
            'france', 'europe', 'paris', 'lyon',
        ]

        for pattern in invalid_patterns:
            if pattern in text_lower:
                return False

        if text.isupper() and len(text) > 10:
            return False

        digit_count = sum(c.isdigit() for c in text)
        if digit_count > 3:
            return False

        return True

    def _extract_company(self, job_element, job_title=None):
        """Extract company name with fallback selectors and validation"""
        # Try specific testid first
        company_elem = job_element.find(attrs={'data-testid': lambda x: x and 'company' in str(x).lower()})
        if company_elem:
            text = company_elem.get_text(strip=True)
            if self._is_valid_company_name(text, job_title):
                return text

        # Try other selectors
        for tag in ['p', 'span', 'div', 'a']:
            for elem in job_element.find_all(tag):
                text = elem.get_text(strip=True)
                if (2 < len(text) < 35 and
                    len(text.split()) <= 4 and
                    text[0].isupper() and
                    self._is_valid_company_name(text, job_title)):
                    return text

        return "Entreprise non spécifiée"

    def _extract_job_title_and_link(self, job_element):
        """Extract job title and link with fallback selectors"""
        # Try links that look like job links
        for link in job_element.find_all('a', href=True):
            href = link['href']
            if '/job_offers/' in href or '/job-offer' in href or '/jobs/' in href:
                title = link.get_text(strip=True)
                if len(title) > 5:
                    if href.startswith('/'):
                        href = 'https://www.jobteaser.com' + href
                    return title, href

        # Fallback: any link with significant text
        for link in job_element.find_all('a', href=True):
            title = link.get_text(strip=True)
            if 10 < len(title) < 120 and any(kw in title.lower() for kw in ['développeur', 'developpeur', 'developer', 'engineer']):
                href = link['href']
                if href.startswith('/'):
                    href = 'https://www.jobteaser.com' + href
                return title, href

        return None, None

    def _extract_thumbnail(self, job_element):
        """Extract thumbnail with fallback selectors"""
        for elem in job_element.find_all('img'):
            if elem.get('src'):
                thumbnail_url = elem['src']
                if 'url=' in thumbnail_url:
                    return unquote(thumbnail_url.split("url=")[1].split("&")[0])
                return thumbnail_url
        return ''

    def scrap(self):
        page = 0
        total_jobs_found = 0
        max_pages = 3

        while page < max_pages:
            print(f"\n{'='*50}")
            print(f"Job Teaser - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading URL: {self.page_url}")

            try:
                self._init_driver(self.page_url)
                self._click_agree_button()
                self._wait_for_jobs_to_load()
            except Exception as e:
                print(f"Error initializing driver: {e}")
                break

            # Get page data
            try:
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error getting page data: {e}")
                break

            # Debug: save HTML for inspection
            if page == 0:
                with open('/tmp/jobteaser_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/jobteaser_debug.html")

            page_soup = BeautifulSoup(page_data, 'html.parser')

            # Try multiple selectors for job container
            job_ads_wrapper = None
            for selector in [
                {'data-testid': 'job-ads-wrapper'},
                {'data-testid': 'search-results-list'},
                {'class': lambda x: x and 'results' in str(x).lower()},
            ]:
                job_ads_wrapper = page_soup.find('ul', selector) or page_soup.find('div', selector)
                if job_ads_wrapper:
                    break

            # Find all jobs
            all_jobs_raw = []
            if job_ads_wrapper:
                all_jobs_raw = job_ads_wrapper.find_all(attrs={'data-testid': 'jobad-card'})
                if not all_jobs_raw:
                    all_jobs_raw = job_ads_wrapper.find_all('article')
                if not all_jobs_raw:
                    all_jobs_raw = job_ads_wrapper.find_all('li')

            # Fallback: search entire page for job links
            if not all_jobs_raw:
                job_links = page_soup.find_all('a', href=re.compile(r'/job_offers/|/job-offer'))
                seen_parents = set()
                for link in job_links:
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent and id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        all_jobs_raw.append(parent)

            if not all_jobs_raw:
                print("No job cards found")
                break

            print(f"\nProcessing {len(all_jobs_raw)} jobs...")

            for i, jobs in enumerate(all_jobs_raw):
                try:
                    print(f"\n--- Job {i+1}/{len(all_jobs_raw)} ---")

                    job_company = self._extract_company(jobs)
                    if not job_company:
                        print('Could not find company name, skipping job')
                        continue
                    print(f'Company: {job_company}')

                    job_name, job_link = self._extract_job_title_and_link(jobs)
                    if not job_name or not job_link:
                        print('Could not find job title/link, skipping job')
                        continue
                    print(f'Job: {job_name}')
                    print(f'Link: {job_link}')

                    job_thumbnail = self._extract_thumbnail(jobs)

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
