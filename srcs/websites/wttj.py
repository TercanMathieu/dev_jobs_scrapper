import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class WTTJ(Website):
    """Scraper pour Welcome to the Jungle - Approche robuste 2025"""

    def __init__(self):
        super().__init__(
            'Welcome to the Jungle',
            'https://www.welcometothejungle.com/fr/jobs?page={}&aroundLatLng=48.85717%2C2.3414&aroundRadius=20&aroundQuery=Paris%2C%20France&sortBy=mostRecent&refinementList%5Bprofession.sub_category_reference%5D%5B%5D=software-web-development-iMzA4',
            'WTTJ JOBS',
            'https://www.startupbegins.com/wp-content/uploads/2018/05/Logo-Welcome-to-the-Jungle.jpg',
            True,
        )
        self.page_load_timeout = 30

    def _wait_for_jobs(self):
        """Attendre que les offres se chargent dans le DOM"""
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="search-results-list-item-wrapper"], article, [class*="job"], [class*="offer"]'))
            )
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Wait timeout or no jobs found: {e}")
            return False

    def _extract_job_title(self, job_element):
        """Extract job title with multiple fallback selectors"""
        # Try semantic tags first
        for tag in ['h2', 'h3', 'h4', 'h1']:
            elem = job_element.find(tag)
            if elem:
                text = elem.get_text(strip=True)
                if 10 < len(text) < 120:
                    return text

        # Try links with job-like text
        for link in job_element.find_all('a', href=True):
            text = link.get_text(strip=True)
            if 10 < len(text) < 120 and any(kw in text.lower() for kw in ['développeur', 'developpeur', 'developer', 'engineer', 'ingénieur', 'lead', 'architect']):
                return text

        # Fallback: any significant text
        for elem in job_element.find_all(['span', 'div', 'p']):
            text = elem.get_text(strip=True)
            if 10 < len(text) < 120 and any(kw in text.lower() for kw in ['développeur', 'developpeur', 'developer', 'engineer']):
                return text

        return "Unknown Position"

    def _extract_company_name(self, job_element, job_title=None):
        """Extract company name with robust validation"""
        job_title_lower = job_title.lower() if job_title else ""

        # Try specific patterns
        for elem in job_element.find_all(['span', 'div', 'p', 'a']):
            text = elem.get_text(strip=True)
            text_lower = text.lower()

            # Skip if same as job title
            if job_title and text_lower == job_title_lower:
                continue

            # Skip if contains job keywords
            job_keywords = ['développeur', 'developpeur', 'developer', 'engineer', 'ingénieur',
                          'frontend', 'backend', 'fullstack', 'software', 'web', 'lead', 'senior', 'junior']
            if any(kw in text_lower for kw in job_keywords):
                continue

            # Skip if contains invalid patterns
            invalid = ['recrutement', 'recrute', 'hiring', 'il y a', 'publié', 'posté', 'cdi', 'cdd',
                      'temps plein', 'temps partiel', 'télétravail', 'remote', 'hybride',
                      'france', 'paris', 'europe', 'voir', 'en savoir']
            if any(inv in text_lower for inv in invalid):
                continue

            # Valid company name criteria
            if (2 < len(text) < 45 and
                len(text.split()) <= 6 and
                not text.isupper() and
                text[0].isupper() and
                sum(c.isdigit() for c in text) <= 2):
                return text

        return "Entreprise non spécifiée"

    def _extract_job_link(self, job_element):
        """Extract job link - look for WTTJ job URLs"""
        for link in job_element.find_all('a', href=True):
            href = link['href']
            if '/jobs/' in href or '/companies/' in href:
                if href.startswith('http'):
                    return href
                return 'https://welcometothejungle.com' + href
        return None

    def scrap(self):
        page = 1
        jobs_found_this_run = 0
        max_pages = 3

        while page <= max_pages:
            print(f"\n{'='*50}")
            print(f"WTTJ - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")

            try:
                self._init_driver(self.page_url)
                self._wait_for_jobs()
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error loading page: {e}")
                break

            # Save debug HTML on first page
            if page == 1:
                with open('/tmp/wttj_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/wttj_debug.html")

            page_soup = BeautifulSoup(page_data, 'html.parser')

            # Try multiple strategies to find job listings
            all_jobs_raw = []

            # Strategy 1: data-testid
            all_jobs_raw = page_soup.find_all('li', attrs={'data-testid': 'search-results-list-item-wrapper'})

            # Strategy 2: articles
            if not all_jobs_raw:
                all_jobs_raw = page_soup.find_all('article')

            # Strategy 3: divs with job/offer in class
            if not all_jobs_raw:
                all_jobs_raw = page_soup.find_all('div', {'class': lambda x: x and any(kw in str(x).lower() for kw in ['job', 'offer', 'card', 'result'])})

            # Strategy 4: look for WTTJ job links and group by parent
            if not all_jobs_raw:
                job_links = page_soup.find_all('a', href=re.compile(r'/fr/companies/.+/jobs/'))
                seen_parents = set()
                for link in job_links:
                    parent = link.find_parent(['article', 'li', 'div'])
                    if parent and id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        all_jobs_raw.append(parent)

            print(f"Found {len(all_jobs_raw)} job elements")

            if len(all_jobs_raw) == 0:
                print("No more jobs found")
                break

            for i, job in enumerate(all_jobs_raw):
                try:
                    print(f"\n--- Job {i+1}/{len(all_jobs_raw)} ---")

                    job_name = self._extract_job_title(job)
                    print(f"Job: {job_name}")

                    job_company = self._extract_company_name(job, job_title=job_name)
                    print(f"Company: {job_company}")

                    job_link = self._extract_job_link(job)
                    if not job_link:
                        print("No link found, skipping")
                        continue
                    print(f"Link: {job_link}")

                    job_thumbnail = ''
                    img = job.find('img')
                    if img and img.get('src'):
                        job_thumbnail = img['src']

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
