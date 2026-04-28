import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class WTTJ(Website):
    """Scraper pour Welcome to the Jungle - Nouvelle interface 2025
    
    WTTJ a changé son interface. Les jobs sont maintenant listés sur des pages thématiques
    par métier avec pagination classique.
    """

    def __init__(self):
        super().__init__(
            'Welcome to the Jungle',
            'https://www.welcometothejungle.com/fr/pages/emploi-developpeur?page={}',
            'WTTJ JOBS',
            'https://www.startupbegins.com/wp-content/uploads/2018/05/Logo-Welcome-to-the-Jungle.jpg',
            True,
        )
        self.page_load_timeout = 45

    def _wait_for_content(self):
        """Attendre que le DOM contienne des jobs (pas de sélecteurs stricts)"""
        for attempt in range(25):
            try:
                # Vérifier qu'il y a du contenu significatif
                body_text = self.driver.execute_script("return document.body.innerText.length")
                # Vérifier aussi qu'on a des éléments de job
                has_jobs = self.driver.execute_script(
                    "return document.querySelectorAll('[data-testid=\"jobs-results-list-list-item-wrapper\"]').length"
                )
                if body_text > 5000 and has_jobs > 0:
                    print(f"Page loaded: {body_text} chars, {has_jobs} job elements")
                    return True
                elif has_jobs > 0:
                    print(f"Jobs found but page still loading... ({has_jobs} elements)")
                    return True
            except Exception:
                pass
            time.sleep(1)
        print("Warning: minimal content, continuing anyway...")
        return True

    def _scroll_and_wait(self):
        """Scrolle pour charger tout le contenu lazy-loaded"""
        print("Scrolling to trigger lazy loading...")
        for _ in range(80):
            self.driver.execute_script("window.scrollTo(0, window.scrollY + 400)")
            time.sleep(0.15)
        # Scroll back to top then down again
        self.driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(2)
        for _ in range(40):
            self.driver.execute_script("window.scrollTo(0, window.scrollY + 500)")
            time.sleep(0.25)
        time.sleep(5)
        print("Scrolling complete")

    def _get_page_data(self):
        """Get page data with extended waits for SPA"""
        self._wait_for_content()
        self._scroll_and_wait()
        page_data = self.driver.page_source
        self.driver.quit()
        return page_data

    def _extract_job_title(self, job_element):
        """Extract job title from h2 in the job link"""
        link = job_element.find('a', href=re.compile(r'/fr/companies/.+/jobs/'))
        if link:
            h2 = link.find('h2')
            if h2:
                return h2.get_text(strip=True)
            # Fallback: text of the link itself
            text = link.get_text(strip=True)
            if text and len(text) > 5:
                return text
        return "Unknown Position"

    def _extract_company_name(self, job_element):
        """Extract company name - try logo alt first, then span text"""
        # Method 1: logo image alt text (data-testid pattern)
        logo_img = job_element.find('img', {'data-testid': re.compile(r'job-thumb-logo-')})
        if logo_img and logo_img.get('alt'):
            alt = logo_img['alt'].strip()
            if alt and len(alt) > 1 and alt.lower() not in ['logo', 'image']:
                return alt

        # Method 2: find span with company name (usually near logo)
        logo_container = job_element.find('div', {'data-testid': re.compile(r'job-thumb-logo-')})
        if logo_container:
            parent = logo_container.find_parent('div')
            if parent:
                for span in parent.find_all('span', {'class': re.compile(r'wui-text')}):
                    text = span.get_text(strip=True)
                    if text and 2 < len(text) < 50 and not any(kw in text.lower() for kw in ['développeur', 'developer', 'engineer']):
                        return text

        # Method 3: any span that looks like a company name
        for span in job_element.find_all('span', {'class': re.compile(r'wui-text')}):
            text = span.get_text(strip=True)
            if (2 < len(text) < 50 and
                text[0].isupper() and
                not any(kw in text.lower() for kw in ['développeur', 'developer', 'engineer', 'cdi', 'cdd', 'stage', 'alternance'])):
                return text

        return "Entreprise non spécifiée"

    def _extract_job_link(self, job_element):
        """Extract full job URL"""
        link = job_element.find('a', href=re.compile(r'/fr/companies/.+/jobs/'))
        if link and link.get('href'):
            href = link['href']
            if href.startswith('http'):
                return href
            return 'https://www.welcometothejungle.com' + href
        return None

    def _extract_location(self, job_element):
        """Extract location from the job card"""
        # Look for span with location class pattern
        for span in job_element.find_all('span', {'class': re.compile(r'ldnNiw')}):
            text = span.get_text(strip=True)
            if text and len(text) > 1:
                return text

        # Fallback: look for text after location icon
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            if re.search(r'(Paris|Lyon|Bordeaux|Marseille|Nantes|Toulouse|Lille|Remote|Télétravail)', text, re.IGNORECASE):
                match = re.search(r'(Paris|Lyon|Bordeaux|Marseille|Nantes|Toulouse|Lille|Remote|Télétravail)[^,]*', text, re.IGNORECASE)
                if match:
                    return match.group(0)
        return "Paris"

    def _extract_contract(self, job_element):
        """Extract contract type (CDI, CDD, Stage, etc.)"""
        # Look for text near contract icon
        contract_patterns = ['CDI', 'CDD', 'Stage', 'Alternance', 'Freelance', 'Apprentissage', 'Temps plein']
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            for pattern in contract_patterns:
                if pattern in text:
                    return pattern
        return "CDI"

    def _extract_thumbnail(self, job_element):
        """Extract company logo or cover image URL"""
        # Try cover image first (larger)
        cover = job_element.find('img', {'data-testid': re.compile(r'job-thumb-cover-')})
        if cover and cover.get('src'):
            return cover['src']

        # Fallback to logo
        logo = job_element.find('img', {'data-testid': re.compile(r'job-thumb-logo-')})
        if logo and logo.get('src'):
            return logo['src']

        return ''

    def _extract_description(self, job_element):
        """Extract short description if available"""
        for p in job_element.find_all('p', {'class': re.compile(r'wui-text')}):
            text = p.get_text(strip=True)
            if text and len(text) > 20 and len(text) < 300:
                return text
        return ""

    def scrap(self):
        page = 1
        jobs_found_this_run = 0
        max_pages = 5  # Limit to avoid too long runs

        while page <= max_pages:
            print(f"\n{'='*50}")
            print(f"WTTJ - Page {page}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")

            try:
                self._init_driver(self.page_url)
                page_data = self._get_page_data()
            except Exception as e:
                print(f"Error loading page: {e}")
                break

            # Save debug HTML on first page
            if page == 1:
                with open('/tmp/wttj_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/wttj_debug.html")

            page_soup = BeautifulSoup(page_data, 'html.parser')

            # Find all job listing items
            job_items = page_soup.find_all('li', {'data-testid': 'jobs-results-list-list-item-wrapper'})

            if not job_items:
                print("No jobs found on this page")
                break

            print(f"Found {len(job_items)} jobs on page {page}")

            for i, job in enumerate(job_items):
                try:
                    print(f"\n--- Job {i+1}/{len(job_items)} ---")

                    job_name = self._extract_job_title(job)
                    print(f"Job: {job_name}")

                    job_company = self._extract_company_name(job)
                    print(f"Company: {job_company}")

                    job_link = self._extract_job_link(job)
                    if not job_link:
                        print("No link found, skipping")
                        continue
                    print(f"Link: {job_link}")

                    job_location = self._extract_location(job)
                    print(f"Location: {job_location}")

                    job_contract = self._extract_contract(job)
                    print(f"Contract: {job_contract}")

                    job_thumbnail = self._extract_thumbnail(job)

                    job_description = self._extract_description(job)
                    if job_description:
                        print(f"Description: {job_description[:80]}...")

                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)

                        embed = create_embed(job_name, job_company, job_location, job_link, job_thumbnail)
                        description = f"{job_name} - {job_company} - {job_contract}"
                        if job_description:
                            description += f" | {job_description[:100]}"

                        success = send_embed(embed, self, job_name, job_company, job_location, job_link, job_thumbnail, description)

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

            # Check if there's a next page by looking for pagination
            pagination = page_soup.find('nav', {'aria-label': 'jobs-pagination'})
            has_next = False
            if pagination:
                next_link = pagination.find('a', href=re.compile(rf'page={page + 1}'))
                if next_link:
                    has_next = True

            print(f'WTTJ page #{page} finished - New jobs this run: {jobs_found_this_run}')
            
            if not has_next:
                print("No more pages")
                break
                
            page += 1

        print(f"\n{'='*50}")
        print(f"WTTJ complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
