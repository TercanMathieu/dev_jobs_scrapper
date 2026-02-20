import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class LesJeudis(Website):
    """Scraper pour LesJeudis - Updated 2025 avec anti-détection Cloudflare"""

    def __init__(self):
        super().__init__(
            'LesJeudis',
            'https://www.lesjeudis.com/recherche?f=1&q=developpeur&l=Paris&p={}',
            'LES JEUDIS',
            'https://www.lesjeudis.com/assets/images/logo-lesjeudis.svg',
            True,
        )
        # Options Chrome avancées pour contourner Cloudflare
        self.extra_chrome_options = [
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            '--accept-lang=fr-FR,fr;q=0.9,en;q=0.8',
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--window-size=1920,1080',
            '--start-maximized',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-gpu',
            '--hide-scrollbars',
            '--dns-prefetch-disable',
        ]
        self.page_load_timeout = 30

    def _is_valid_company_name(self, text, job_title=None):
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        if job_title and text.lower() == job_title.lower():
            return False
        
        invalid = ['recrutement', 'recrute', 'hiring', 'il y a', 'publié', 'salaire', 'cdi', 'cdd', 'postuler']
        for pattern in invalid:
            if pattern in text.lower():
                return False
        
        job_words = ['developpeur', 'developer', 'engineer', 'ingénieur', 'frontend', 'backend', 'fullstack']
        for word in job_words:
            if word in text.lower():
                return False
        
        return True

    def _extract_company_name(self, job_element, job_title=None):
        # LesJeudis 2025 - nouveaux sélecteurs
        selectors = [
            'span.company-name',
            'span.job-company',
            'div.company',
            'span[class*="company"]',
            'div[class*="company"]',
        ]
        
        for selector in selectors:
            elem = job_element.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Fallback: chercher après le titre
        for elem in job_element.find_all('span'):
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
            'h2.job-title a',
            'h3.job-title a',
            'a.job-title',
            'h2 a[data-testid]',
            'h3 a[data-testid]',
            'h2.title',
            'h3.title',
        ]
        
        for selector in selectors:
            elem = job_element.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 5:
                    return text
        
        # Fallback: premier lien avec texte significatif
        for link in job_element.find_all('a'):
            text = link.get_text(strip=True)
            if len(text) > 10 and len(text) < 100:
                return text
        
        return "Unknown Position"

    def _extract_location(self, job_element):
        selectors = [
            'span.location',
            'span.job-location',
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
            if re.search(r'(Paris|Lyon|Bordeaux|Nantes|Lille|Toulouse)\s*\(?\d{2,5}\)?', text, re.IGNORECASE):
                return text
            if re.search(r'\b\d{5}\b', text):
                return text
        return "Paris"

    def _extract_job_link(self, job_element):
        # Chercher lien d'offre
        link = job_element.find('a', href=re.compile(r'/job/|/offre/|/emploi/'))
        if link:
            href = link['href']
            if href.startswith('/'):
                return 'https://www.lesjeudis.com' + href
            return href
        
        # Fallback: premier lien
        link = job_element.find('a', href=True)
        if link:
            href = link['href']
            if href.startswith('/'):
                return 'https://www.lesjeudis.com' + href
            return href
        return None

    def _extract_thumbnail(self, job_element):
        img = job_element.find('img', {'src': True})
        if img:
            return img.get('src', '')
        return ''

    def _init_driver(self, url):
        """Override pour ajouter des scripts anti-détection"""
        super()._init_driver(url)
        
        # Exécuter script pour masquer Selenium
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
        time.sleep(3)  # Attendre que Cloudflare valide

    def scrap(self):
        page = 1
        jobs_found = 0
        max_pages = 3

        while page <= max_pages:
            print(f"\n{'='*50}")
            print(f"LES JEUDIS - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            try:
                self._init_driver(self.page_url)
                
                # Attendre que la page charge complètement
                time.sleep(5)
                
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error: {e}")
                break

            if page == 1:
                with open('/tmp/lesjeudis_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML")

            soup = BeautifulSoup(page_data, 'html.parser')
            
            # Chercher les offres avec sélecteurs 2025
            jobs = []
            selectors_to_try = [
                'article.job-card',
                'div.job-card',
                'article[data-testid]',
                'div[data-testid*="job"]',
                'li.job-item',
                'article',
                'div[class*="job"]',
            ]
            
            for selector in selectors_to_try:
                jobs = soup.select(selector)
                if jobs:
                    print(f"Found {len(jobs)} jobs with selector: {selector}")
                    break

            if not jobs:
                # Vérifier si c'est une page de challenge Cloudflare
                if 'cf-browser-verification' in page_data or 'challenge' in page_data.lower():
                    print("⚠️ Cloudflare challenge detected - cannot bypass")
                else:
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

        print(f"\nLesJeudis complete: {jobs_found} jobs")
