import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class Cadremploi(Website):
    """Scraper pour Cadremploi - Updated 2025"""

    def __init__(self):
        super().__init__(
            'Cadremploi',
            'https://www.cadremploi.fr/emploi/developpeur_logiciel_paris_{}',
            'CADREEMPLOI',
            'https://www.cadremploi.fr/assets/images/logo-cadremploi.svg',
            True,
        )
        # Options Chrome anti-détection
        self.extra_chrome_options = [
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            '--accept-lang=fr-FR,fr;q=0.9',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-web-security',
            '--window-size=1920,1080',
            '--disable-infobars',
            '--disable-extensions',
        ]

    def _is_valid_company_name(self, text, job_title=None):
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        if job_title and text.lower() == job_title.lower():
            return False
        
        invalid = ['recrutement', 'recrute', 'hiring', 'il y a', 'publié', 'cdi', 'cdd', 'salaire', 'postuler']
        for pattern in invalid:
            if pattern in text.lower():
                return False
        
        job_words = ['developpeur', 'developer', 'engineer', 'ingénieur', 'manager', 'lead', 'software']
        for word in job_words:
            if word in text.lower():
                return False
        
        return True

    def _extract_company_name(self, job_element, job_title=None):
        # Sélecteurs Cadremploi 2025
        selectors = [
            'span.company-name',
            'span.entreprise',
            'div.company',
            'span[class*="company"]',
            'div[class*="entreprise"]',
            'a[href*="/entreprise/"]',
        ]
        
        for selector in selectors:
            elem = job_element.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Fallback: chercher texte capitalisé
        for elem in job_element.find_all(['span', 'div', 'a']):
            text = elem.get_text(strip=True)
            if (2 < len(text) < 40 and 
                text[0].isupper() and 
                not text.isupper() and
                self._is_valid_company_name(text, job_title)):
                return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_element):
        # Sélecteurs 2025
        selectors = [
            'h2.job-title',
            'h3.job-title',
            'h2.title a',
            'h3.title a',
            'a.job-title',
            'h2 a',
            'h3 a',
        ]
        
        for selector in selectors:
            elem = job_element.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 5:
                    return text
        
        # Fallback
        link = job_element.find('a', href=True)
        if link:
            text = link.get_text(strip=True)
            if len(text) > 5:
                return text
        
        return "Unknown Position"

    def _extract_location(self, job_element):
        selectors = [
            'span.location',
            'span.city',
            'div.location',
            'span[class*="location"]',
        ]
        
        for selector in selectors:
            elem = job_element.select_one(selector)
            if elem:
                return elem.get_text(strip=True)
        
        # Pattern regex
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            if re.search(r'(Paris|Lyon|Bordeaux|Marseille|Nantes|Toulouse)\s*\(?\d{2,5}\)?', text, re.IGNORECASE):
                return text
            if re.search(r'\b\d{5}\b', text):
                return text
        return "Paris"

    def _extract_job_link(self, job_element):
        # Chercher lien d'offre
        link = job_element.find('a', href=re.compile(r'/offre/|/emploi/|/job/'))
        if link:
            href = link['href']
            if href.startswith('/'):
                return 'https://www.cadremploi.fr' + href
            return href
        
        # Fallback: premier lien
        link = job_element.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('/'):
                return 'https://www.cadremploi.fr' + href
            return href
        return None

    def _extract_thumbnail(self, job_element):
        img = job_element.find('img', {'src': True})
        if img:
            return img.get('src', '')
        return ''

    def _init_driver(self, url):
        """Override avec anti-détection"""
        super()._init_driver(url)
        
        # Masquer Selenium
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = { runtime: {} };
        """)
        
        time.sleep(2)

    def scrap(self):
        page = 1
        jobs_found = 0
        max_pages = 3

        while page <= max_pages:
            print(f"\n{'='*50}")
            print(f"CADREEMPLOI - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            try:
                self._init_driver(self.page_url)
                time.sleep(3)  # Attendre chargement
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error: {e}")
                break

            if page == 1:
                with open('/tmp/cadremploi_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML")

            soup = BeautifulSoup(page_data, 'html.parser')
            
            # Chercher les offres avec sélecteurs 2025
            jobs = []
            selectors_to_try = [
                'article.job-card',
                'div.job-card',
                'article.offer-card',
                'div.offer-card',
                'article[data-offer-id]',
                'div[class*="job"]',
                'div[class*="offer"]',
            ]
            
            for selector in selectors_to_try:
                jobs = soup.select(selector)
                if jobs:
                    print(f"Found {len(jobs)} jobs with selector: {selector}")
                    break

            # Fallback: recherche par liens
            if not jobs:
                job_links = soup.find_all('a', href=re.compile(r'/offre/'))
                jobs = []
                for link in job_links:
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent and parent not in jobs:
                        jobs.append(parent)
                if jobs:
                    print(f"Found {len(jobs)} jobs via link search")

            if not jobs:
                print("No jobs found")
                break

            for i, job in enumerate(jobs[:20]):
                try:
                    print(f"\n--- Job {i+1} ---")
                    
                    job_name = self._extract_job_title(job)
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
                    
                    job_thumbnail = self._extract_thumbnail(job)

                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
                        embed = create_embed(job_name, job_company, job_location, job_link, job_thumbnail)
                        desc = f"{job_name} - {job_company}"
                        
                        if send_embed(embed, self, job_name, job_company, job_location, job_link, job_thumbnail, desc):
                            jobs_found += 1
                        time.sleep(3)
                    else:
                        print("✗ Already in database")
                        
                except Exception as e:
                    print(f"Error: {e}")
                    continue

            print(f"Page {page} done - Total new: {jobs_found}")
            page += 1

        print(f"\nCadremploi complete: {jobs_found} jobs")
