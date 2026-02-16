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
        try:
            agree_button = self.driver.find_element(By.XPATH,'//*[@id="didomi-notice-agree-button"]')
            agree_button.click()
            print("Clicked on 'Good for me!' button.")
        except Exception as e:
            print("Error clicking 'Good for me!' button:", str(e))


    def scrap(self):
        page = 0
        while True:

            print("Looking for another Job Teaser\'s page..")

            self.page_url = self.url.format(page)
            self._init_driver(self.page_url)
    
            # Click the "Good for me!" button if it appears
            self._click_agree_button()
            page_data = self._get_chrome_page_data()
            # Use Selenium to handle the dynamic content and click the button

            page_soup = BeautifulSoup(page_data, 'html.parser')
            job_ads_wrapper = page_soup.find('ul', {'data-testid': 'job-ads-wrapper'})
            if job_ads_wrapper is None:
                print("Job Teaser's page #{} has no job ads.".format(page))
                return
       
            # Find all jobs within the <ul> element
            all_jobs_raw = job_ads_wrapper.find_all('div', {'data-testid': 'jobad-card'})
            if len(all_jobs_raw) == 0 or page >= 2:  # Scrap finished
                return
            print("\nJob Teaser\'s found jobs ({}) :".format(len(all_jobs_raw)))
            for jobs in all_jobs_raw:
                try:
                    # Find company name - first p tag with testid
                    company_p = jobs.find('p', {'data-testid': 'jobad-card-company-name'})
                    if not company_p:
                        print('Could not find company name, skipping job')
                        continue
                    job_company = company_p.text.strip()
                    print('Company : ' + job_company)

                    # Find job title - link with class JobAdCard_link__LMtBN
                    job_link_a = jobs.find('a', class_='JobAdCard_link__LMtBN')
                    if not job_link_a:
                        print('Could not find job link, skipping job')
                        continue
                    job_name = job_link_a.text.strip()
                    print('Job : ' + job_name)
                    job_link = 'https://www.jobteaser.com' + job_link_a['href']

                    # Find thumbnail
                    job_thumbnail = ''
                    img_tag = jobs.find('img', {'data-testid': 'jobad-card-company-logo'})
                    if img_tag and 'src' in img_tag.attrs:
                        thumbnail_url = img_tag['src']
                        if 'url=' in thumbnail_url:
                            job_thumbnail = unquote(thumbnail_url.split("url=")[1].split("&")[0])
                        else:
                            job_thumbnail = thumbnail_url

                    if not is_url_in_database(job_name + job_company):
                        print("Found new job: {}".format(job_link))
                        add_url_in_database(job_name + job_company)
                        embed = create_embed(
                            job_name, job_company, 'Paris', job_link, job_thumbnail)
                        send_embed(embed, self)
                        time.sleep(4)
                except Exception as e:
                    print(f"Error processing job: {e}")
                    continue

            print('Job Teaser\'s page #{} finished'.format(page))
            page += 1
