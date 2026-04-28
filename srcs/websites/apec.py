import time
import re
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class APEC(Website):
    """Scraper for APEC - Approche robuste 2025"""

    def __init__(self):
        super().__init__(
            'APEC',
            'https://www.apec.fr/candidat/recherche-emploi.html/emploi?lieux=91&motsCles=developpeur&page={}',
            'APEC JOBS',
            'https://www.apec.fr/fileadmin/user_upload/Logos/Apec-Logo.svg',
            True,
        )
        self.page_load_timeout = 30

    def _is_valid_company_name(self, text, job_title=None):
        """Check if text is a valid company name"""
        if not text or len(text) < 2 or len(text) > 60:
            return False

        if job_title:
            text_norm = text.lower().strip()
            title_norm = job_title.lower().strip()
            if text_norm == title_norm:
                return False

        invalid_patterns = [
            'recrutement', 'recrute', 'recruiting', 'hiring',
            'publié', 'published', 'posté', 'posted',
            'il y a', 'ago', 'days', 'jours',
            ' CDI', ' CDD', ' stage', ' alternance',
            'télétravail', 'remote', 'hybride', 'hybrid',
            'france', 'europe',
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

        return True

    def _extract_company_name(self, job_card, job_title=None):
        """Extract company name from APEC job card"""
        # Try specific APEC selectors
        selectors = [
            'span.card-offer__company-name',
            'span.company-name',
            'div.offer-card__company',
            '.nomEntreprise',
            '[data-cy="company-name"]',
            'span[class*="company"]',
            'div[class*="company"]',
        ]

        for selector in selectors:
            elem = job_card.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text

        # Fallback: look for capitalized short text
        for elem in job_card.find_all(['span', 'div', 'p', 'a']):
            text = elem.get_text(strip=True)
            if (2 < len(text) < 35 and
                not text.isupper() and
                text[0].isupper() and
                self._is_valid_company_name(text, job_title)):
                return text

        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_card):
        """Extract job title from APEC"""
        selectors = [
            'h2.card-offer__title',
            'h3.card-offer__title',
            'a[data-cy="offer-title"]',
            'span.intitulePoste',
            '.offer-title',
            'h2 a',
            'h3 a',
            'h2',
            'h3',
        ]

        for selector in selectors:
            elem = job_card.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 3:
                    return text

        # Fallback: look for links with job-like text
        for link in job_card.find_all('a', href=True):
            text = link.get_text(strip=True)
            if len(text) > 5 and any(kw in text.lower() for kw in ['développeur', 'developpeur', 'developer', 'engineer']):
                return text

        return "Unknown Position"

    def _extract_location(self, job_card):
        """Extract job location"""
        selectors = [
            'span.card-offer__location',
            'span.location',
            'div.location',
            '[data-cy="location"]',
            '.lieu',
        ]

        for selector in selectors:
            elem = job_card.select_one(selector)
            if elem:
                return elem.get_text(strip=True)

        return "Paris"

    def _extract_job_link(self, job_card):
        """Extract job link"""
        for link in job_card.find_all('a', href=True):
            href = link['href']
            if '/offre-emploi/' in href or '/emploi/' in href:
                if href.startswith('/'):
                    return 'https://www.apec.fr' + href
                return href

        # Fallback: first link
        link = job_card.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('/'):
                return 'https://www.apec.fr' + href
            return href

        return None

    def _wait_for_jobs_to_load(self):
        """Wait for job cards to appear (SPA)"""
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    'article.card-offer, div.card-offer, div[data-cy="offer-card"], article, .offer'
                ))
            )
            time.sleep(3)
            return True
        except:
            return False

    def scrap(self):
        page = 0
        jobs_found_this_run = 0
        max_pages = 3

        while page < max_pages:
            print(f"\n{'='*50}")
            print(f"APEC - Page {page + 1}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")

            try:
                self._init_driver(self.page_url)
                self._wait_for_jobs_to_load()
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error loading page: {e}")
                break

            # Debug: save HTML
            if page == 0:
                with open('/tmp/apec_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/apec_debug.html")

            page_soup = BeautifulSoup(page_data, 'html.parser')

            # Try multiple selectors
            job_listings = []
            selectors_to_try = [
                'article.card-offer',
                'div.card-offer',
                'div[data-cy="offer-card"]',
                'article[data-cy="offer"]',
                'div.offer-card',
                'article.offer',
                'article',
                'div[class*="offer"]',
            ]

            for selector in selectors_to_try:
                job_listings = page_soup.select(selector)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs with selector: {selector}")
                    break

            # Fallback: search by job links
            if not job_listings:
                job_links = page_soup.find_all('a', href=re.compile(r'/offre-emploi/'))
                seen_parents = set()
                for link in job_links:
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent and id(parent) not in seen_parents:
                        seen_parents.add(id(parent))
                        job_listings.append(parent)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs via link search")

            if not job_listings:
                print("No jobs found on this page")
                break

            print(f"Processing {len(job_listings)} jobs...")

            for i, job in enumerate(job_listings[:20]):
                try:
                    print(f"\n--- Job {i+1}/{len(job_listings)} ---")

                    job_name = self._extract_job_title(job)
                    if job_name == "Unknown Position":
                        print("Could not extract job title, skipping")
                        continue
                    print(f"Job: {job_name}")

                    job_company = self._extract_company_name(job, job_title=job_name)
                    print(f"Company: {job_company}")

                    job_location = self._extract_location(job)
                    print(f"Location: {job_location}")

                    job_link = self._extract_job_link(job)
                    if not job_link:
                        print("No link found, skipping")
                        continue
                    print(f"Link: {job_link}")

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

            print(f'APEC page finished - Total new jobs: {jobs_found_this_run}')
            page += 1

        print(f"\n{'='*50}")
        print(f"APEC complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
