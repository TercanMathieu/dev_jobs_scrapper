import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class StationF(Website):

    def __init__(self):
        super().__init__(
            'Station F',
            'https://jobs.stationf.co/search?query=dev{}&departments%5B0%5D=Tech&departments%5B1%5D=Tech%20%26%20Dev&departments%5B2%5D=Tech%2FDev&departments%5B3%5D=Dev&contract_types%5B0%5D=Full-Time&contract_types%5B1%5D=Freelance&contract_types%5B2%5D=Temporary',
            'STATION F JOBS',
            'https://mbem.fr/wp-content/uploads/2018/06/station-f-logo-copie.png',
            False
        )

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

    def _extract_company_name(self, job_element):
        """Extract company name with validation"""
        # Try the specific class first
        job_company_li = job_element.find('li', attrs={'class': 'job-company'})
        if job_company_li:
            text = job_company_li.get_text(strip=True)
            if self._is_valid_company_name(text):
                return text

        # Try alternative selectors
        selectors = [
            ('span', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('div', {'class': lambda x: x and 'company' in x.lower() if x else False}),
            ('p', {'class': lambda x: x and 'company' in x.lower() if x else False}),
        ]

        for tag, attrs in selectors:
            elem = job_element.find(tag, attrs)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text):
                    return text

        # Fallback: look for short text
        for elem in job_element.find_all(['span', 'li', 'div']):
            text = elem.get_text(strip=True)
            if (2 < len(text) < 35 and
                    len(text.split()) <= 4 and
                    text[0].isupper() and
                    self._is_valid_company_name(text)):
                return text

        return "Entreprise non spécifiée"

    def scrap(self):
        page = 1
        total_jobs_found = 0

        while True:
            print(f"\n{'='*50}")
            print(f"Station F - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(
                '&page={}'.format(page) if page != 1 else '')
            self._init_driver(self.page_url)
            page_data = self._get_chrome_page_data()
            page_soup = BeautifulSoup(page_data, 'html.parser')
            all_jobs_raw = page_soup.find_all(
                'li', attrs={'class': 'ais-Hits-item'})

            if len(all_jobs_raw) == 0 or page >= 2:  # Scrap finished
                print("No more jobs found")
                break

            print(f"\nStation F found {len(all_jobs_raw)} jobs")
            for i, jobs in enumerate(all_jobs_raw):
                try:
                    print(f"\n--- Job {i+1}/{len(all_jobs_raw)} ---")

                    # Find job title
                    job_title_h4 = jobs.find('h4', attrs={'class': 'job-title'})
                    if not job_title_h4:
                        print('Could not find job title, skipping job')
                        continue
                    job_name = job_title_h4.text.strip()
                    print('Job : ' + job_name)

                    # Find company name with validation
                    job_company = self._extract_company_name(jobs)
                    print('Company : ' + job_company)

                    # Find location
                    job_location_li = jobs.find(
                        'li', attrs={'class': 'job-office'})
                    if not job_location_li:
                        print('Could not find location, using default')
                        job_location = 'Paris'
                    else:
                        job_location = job_location_li.text.strip()
                    print('Location : ' + job_location)

                    # Find job link
                    job_link_a = jobs.find(
                        'a', attrs={'class': 'jobs-item-link'}, href=True)
                    if not job_link_a:
                        print('Could not find job link, skipping job')
                        continue
                    job_link = 'https://jobs.stationf.co' + job_link_a['href']
                    print(f'Link : {job_link}')

                    # Find thumbnail
                    job_thumbnail = ''
                    company_logo_div = jobs.find(
                        'div', attrs={'class': 'company-logo'})
                    if company_logo_div and 'style' in company_logo_div.attrs:
                        thumbnail_match = re.search(
                            "(?P<url>https?://[^\s]+)", company_logo_div['style'])
                        if thumbnail_match:
                            job_thumbnail = thumbnail_match.group("url")[:-2]

                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        embed = create_embed(
                            job_name, job_company, job_location, job_link, job_thumbnail)

                        description = f"{job_name} {job_company} {job_location}"
                        send_embed(embed, self, job_name, job_company,
                                   job_location, job_link, job_thumbnail, description)
                        total_jobs_found += 1
                        time.sleep(4)
                    else:
                        print("✗ Already in database")

                except Exception as e:
                    print(f"Error processing job: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            print(f'Station F page #{page} finished - New jobs this page: {total_jobs_found}')
            page += 1

        print(f"\n{'='*50}")
        print(f"Station F complete. Total new jobs: {total_jobs_found}")
        print(f"{'='*50}")

