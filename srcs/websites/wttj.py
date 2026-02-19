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

    def scrap(self):
        page = 1

        while True:

            print("Looking for another WTTJ\'s page..")

            self.page_url = self.url.format(page)
            print('test0')
            self._init_driver(self.page_url)
            print('test2 - Driver initialized')
            page_data = self._get_chrome_page_data()
            print(f'test3 - Page data retrieved, length: {len(page_data)} chars')
            print('Creating BeautifulSoup object...')
            page_soup = BeautifulSoup(page_data, 'html.parser')
            print('test1 - BeautifulSoup created successfully')
            all_jobs_raw = page_soup.find_all(
                'li', attrs={'data-testid': 'search-results-list-item-wrapper'})
            print(f"Found {len(all_jobs_raw)} jobs")
            if len(all_jobs_raw) == 0 or page >= 4:  # Scrap finished
                return

            print("\nWTTJ\'s found jobs ({}) :".format(len(all_jobs_raw)))
            for jobs in all_jobs_raw:
                try:
                    # Find company name - look for span with company name class
                    company_span = jobs.find('span', class_='sc-izXThL fFdRYJ sc-jkYWRr ewxOXb wui-text')
                    if not company_span:
                        print('Could not find company name, skipping job')
                        continue
                    job_company = company_span.text.strip()

                    # Find job name - look for h2 title
                    job_title_h2 = jobs.find('h2', class_='sc-izXThL fnsHVh wui-text')
                    if not job_title_h2:
                        print('Could not find job title, skipping job')
                        continue
                    job_name = job_title_h2.text.strip()

                    # Find job link
                    job_link_a = jobs.find('a', href=True)
                    if not job_link_a:
                        print('Could not find job link, skipping job')
                        continue
                    job_link = 'https://welcometothejungle.com' + job_link_a['href']

                    # Find thumbnail - first img tag
                    job_thumbnail_img = jobs.find('img')
                    job_thumbnail = job_thumbnail_img['src'] if job_thumbnail_img else ''

                    print('Job : ' + job_name)
                    print('Company : ' + job_company)
                    print(job_link)
                    print('\n')

                    if not is_url_in_database(job_name + job_company):
                        print("Found new job: {}".format(job_link))
                        add_url_in_database(job_name + job_company)
                        embed = create_embed(
                            job_name, job_company, 'Paris', job_link, job_thumbnail)
                        send_embed(embed, self, job_name, job_company)
                        time.sleep(4)
                except Exception as e:
                    print(f"Error processing job: {e}")
                    continue

            print('WTTJ\'s page #{} finished'.format(page))
            page += 1
