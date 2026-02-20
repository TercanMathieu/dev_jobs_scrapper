import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class Indeed(Website):
    """Scraper for Indeed France - Note: Indeed has strong bot detection"""

    def __init__(self):
        super().__init__(
            'Indeed France',
            'https://fr.indeed.com/jobs?q=developpeur+software&l=Paris&sort=date&start={}',
            'INDEED JOBS',
            'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fc/Indeed_logo.svg/1200px-Indeed_logo.svg.png',
            True,
        )
        # Add extra Chrome options to avoid bot detection
        self.extra_chrome_options = [
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '--accept-lang=fr-FR,fr',
        ]

    def _is_valid_company_name(self, text, job_title=None):
        """Check if text is a valid company name"""
        if not text or len(text) < 2 or len(text) > 60:
            return False
        
        # Check against job title
        if job_title:
            text_norm = text.lower().strip()
            title_norm = job_title.lower().strip()
            if text_norm == title_norm:
                return False
            if text_norm in title_norm and len(text_norm) > 8:
                return False
        
        # Invalid patterns
        invalid_patterns = [
            'recrutement', 'recrute', 'recruiting', 'hiring',
            'publié', 'published', 'posté', 'posted',
            'il y a', 'ago', 'days', 'jours',
            ' CDI', ' CDD', ' stage', ' alternance',
            'temps plein', 'temps partiel', 'full time', 'part time',
            'télétravail', 'remote', 'hybride', 'hybrid',
            'paris', 'lyon', 'marseille', 'bordeaux', 'lille',
            'france', 'europe', 'salaire', 'salary',
        ]
        
        job_keywords = [
            'développeur', 'developpeur', 'developer', 'dev ',
            'ingénieur', 'ingenieur', 'engineer',
            'frontend', 'backend', 'fullstack', 'full-stack',
            'software', 'web', 'mobile', 'cloud',
            'data', 'machine learning', 'ia ', 'ai ',
        ]
        
        text_lower = text.lower()
        for pattern in invalid_patterns + job_keywords:
            if pattern in text_lower:
                return False
        
        if text.isupper() and len(text) > 10:
            return False
            
        digit_count = sum(c.isdigit() for c in text)
        if digit_count > 3:
            return False
        
        return True

    def _extract_company_name(self, job_element, job_title=None):
        """Extract company name from Indeed job element"""
        
        # Try data-testid first (modern Indeed)
        company_elem = job_element.find(attrs={'data-testid': 'company-name'})
        if company_elem:
            text = company_elem.get_text(strip=True)
            if self._is_valid_company_name(text, job_title):
                return text
        
        # Try aria-label containing company
        for elem in job_element.find_all(attrs={'aria-label': True}):
            aria = elem['aria-label']
            if 'company' in aria.lower() or 'employeur' in aria.lower():
                text = elem.get_text(strip=True)
                if self._is_valid_company_name(text, job_title):
                    return text
        
        # Try to find company in spans/divs that are not the title
        # On Indeed, company often appears in specific positions
        title_elem = job_element.find(['h2', 'a', 'span'], attrs={'data-testid': 'job-title'})
        if title_elem:
            # Look for next sibling that might be company
            for sibling in title_elem.find_all_next(['span', 'div'], limit=3):
                text = sibling.get_text(strip=True)
                if (2 < len(text) < 40 and 
                    not text.isupper() and
                    text[0].isupper() and
                    len(text.split()) <= 4 and
                    self._is_valid_company_name(text, job_title)):
                    return text
        
        # Generic fallback
        for elem in job_element.find_all(['span', 'div']):
            # Skip if it's likely the title
            if elem.find(['h2', 'h3']) or elem.get('data-testid') == 'job-title':
                continue
                
            text = elem.get_text(strip=True)
            if (2 < len(text) < 35 and 
                not text.isupper() and
                text[0].isupper() and
                len(text.split()) <= 3 and
                self._is_valid_company_name(text, job_title)):
                return text
        
        return "Entreprise non spécifiée"

    def _extract_job_title(self, job_element):
        """Extract job title from Indeed"""
        # Modern Indeed uses data-testid
        title_elem = job_element.find(attrs={'data-testid': 'job-title'})
        if title_elem:
            text = title_elem.get_text(strip=True)
            if len(text) > 3:
                return text
        
        # Try aria-label
        for elem in job_element.find_all(attrs={'aria-label': True}):
            aria = elem['aria-label']
            if len(aria) > 5 and len(aria) < 150:
                # Clean up
                text = re.sub(r'^nouveau\s+', '', aria, flags=re.IGNORECASE)
                return text.strip()
        
        # Try h2 (often contains job title on Indeed)
        h2 = job_element.find('h2')
        if h2:
            text = h2.get_text(strip=True)
            # Remove "nouveau" prefix if present
            text = re.sub(r'^nouveau\s+', '', text, flags=re.IGNORECASE)
            if len(text) > 3:
                return text
        
        return "Unknown Position"

    def _extract_location(self, job_element):
        """Extract job location"""
        # Modern Indeed
        loc_elem = job_element.find(attrs={'data-testid': 'job-location'})
        if loc_elem:
            return loc_elem.get_text(strip=True)
        
        # Try to find location by looking for city names
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            # Location patterns - cities followed by department/postal code
            if re.search(r'(Paris|Lyon|Marseille|Bordeaux|Nantes|Lille|Toulouse|Nice|Strasbourg)\s*\(?\d{2,5}\)?', text, re.IGNORECASE):
                if len(text) < 60:
                    return text
            # Or just postal code pattern
            if re.search(r'\b\d{5}\b', text):
                if len(text) < 60 and len(text) > 3:
                    return text
        
        return "Paris"

    def _extract_job_link(self, job_element):
        """Extract job link"""
        # Find any link
        for link in job_element.find_all('a', href=True):
            href = link['href']
            if '/rc/clk' in href or '/pagead/' in href or '/viewjob' in href or '/jobs/view' in href:
                if href.startswith('/'):
                    return 'https://fr.indeed.com' + href
                elif href.startswith('http'):
                    return href
        return None

    def _extract_thumbnail(self, job_element):
        """Extract company logo/thumbnail"""
        # Try to find company logo image
        img = job_element.find('img', {'src': True})
        if img and img.get('src'):
            src = img['src']
            # Filter for actual company logos, not icons
            if 'indeed' not in src.lower() and len(src) > 10:
                return src
        # Try data-src for lazy loaded images
        img = job_element.find('img', {'data-src': True})
        if img and img.get('data-src'):
            src = img['data-src']
            if 'indeed' not in src.lower() and len(src) > 10:
                return src
        return ''

    def _extract_technologies_from_snippet(self, job_element):
        """Try to extract technologies from job snippet on results page"""
        # Find description/snippet
        text = job_element.get_text(separator=' ', strip=True).lower()
        
        # Look for common tech keywords
        techs = []
        
        tech_keywords = {
            'python': 'python',
            'javascript': 'javascript', 'js': 'javascript',
            'typescript': 'typescript', 'ts': 'typescript',
            'react': 'react', 'angular': 'angular', 'vue': 'vue.js',
            'node': 'node.js', 'nodejs': 'node.js',
            'php': 'php', 'java': 'java', 'go ': 'go',
            'docker': 'docker', 'kubernetes': 'kubernetes', 'k8s': 'kubernetes',
            'aws': 'aws', 'azure': 'azure', 'gcp': 'gcp', 'google cloud': 'gcp',
            'sql': 'sql', 'postgresql': 'postgresql', 'mysql': 'mysql', 'mongo': 'mongodb',
            'git': 'git', 'ci/cd': 'ci/cd', 'jenkins': 'jenkins',
            'html': 'html', 'css': 'css', 'sass': 'sass', 'scss': 'scss',
            'spring': 'spring', 'symfony': 'symfony', 'laravel': 'laravel',
            'django': 'django', 'flask': 'flask', 'fastapi': 'fastapi',
            'tensorflow': 'tensorflow', 'pytorch': 'pytorch',
        }
        
        for keyword, tech in tech_keywords.items():
            if keyword in text and tech not in techs:
                techs.append(tech)
        
        return techs

    def _extract_salary(self, job_element):
        """Extract salary if available"""
        for elem in job_element.find_all(['span', 'div']):
            text = elem.get_text(strip=True)
            if '€' in text or 'euro' in text.lower():
                if any(char.isdigit() for char in text):
                    return text
        return None

    def scrap(self):
        page = 0
        jobs_found_this_run = 0

        while True:
            print(f"\n{'='*50}")
            print(f"INDEED - Page {page//10 + 1}")
            print(f"{'='*50}")

            self.page_url = self.url.format(page)
            print(f"Loading: {self.page_url}")
            
            try:
                self._init_driver(self.page_url)
                page_data = self._get_chrome_page_data()
            except Exception as e:
                print(f"Error loading page: {e}")
                break
            
            # Check if we got blocked
            if 'cf-browser-verification' in page_data.lower() or 'ray id' in page_data.lower():
                print("WARNING: Cloudflare detected - Indeed is blocking the bot")
                with open('/tmp/indeed_blocked.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                break
            
            # Save debug HTML on first page
            if page == 0:
                with open('/tmp/indeed_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_data)
                print("Saved debug HTML to /tmp/indeed_debug.html")
            
            page_soup = BeautifulSoup(page_data, 'html.parser')
            
            # Indeed job cards - be very flexible with selectors
            job_listings = []
            
            # Try many different selectors
            selectors_to_try = [
                ('div', {'data-testid': 'job-title'}),  # Modern Indeed
                ('div', {'class': lambda x: x and 'job_seen_beacon' in str(x)}),
                ('div', {'class': lambda x: x and 'slider_container' in str(x)}),
                ('div', {'class': lambda x: x and 'slider' in str(x) and 'item' in str(x)}),
                ('div', {'class': lambda x: x and 'tapItem' in str(x)}),
                ('a', {'class': lambda x: x and 'tapItem' in str(x)}),
                ('li', {'class': lambda x: x and 'css-5lfssm' in str(x)}),
                ('div', {'class': lambda x: x and 'jobTitle' in str(x)}),
            ]
            
            for tag, attrs in selectors_to_try:
                job_listings = page_soup.find_all(tag, attrs)
                if job_listings:
                    print(f"Found {len(job_listings)} jobs with selector: {tag}")
                    break
            
            # Alternative: look for any element containing job data
            if not job_listings:
                job_listings = page_soup.find_all('div', {'class': lambda x: x and 'job' in str(x).lower()})
            
            if not job_listings or page >= 20:  # Limit to 2 pages
                print("No more jobs found or page limit reached")
                break

            print(f"Processing {len(job_listings)} jobs...")
            
            for i, job in enumerate(job_listings):
                try:
                    print(f"\n--- Job {i+1}/{len(job_listings)} ---")
                    
                    # Extract job title first
                    job_name = self._extract_job_title(job)
                    if job_name == "Unknown Position":
                        print("Could not extract job title, skipping")
                        continue
                    print(f"Job: {job_name}")
                    
                    # Extract company
                    job_company = self._extract_company_name(job, job_title=job_name)
                    print(f"Company: {job_company}")
                    
                    # Extract location
                    job_location = self._extract_location(job)
                    print(f"Location: {job_location}")
                    
                    # Extract link
                    job_link = self._extract_job_link(job)
                    if not job_link:
                        print("No link found, skipping")
                        continue
                    print(f"Link: {job_link}")
                    
                    # Extract thumbnail
                    job_thumbnail = self._extract_thumbnail(job)
                    if job_thumbnail:
                        print(f"Thumbnail found: {job_thumbnail[:60]}...")
                    
                    # Extract technologies from snippet (since Indeed blocks page analysis)
                    techs = self._extract_technologies_from_snippet(job)
                    if techs:
                        print(f"Technologies detected from snippet: {', '.join(techs)}")
                    
                    # Extract salary if available
                    salary = self._extract_salary(job)
                    if salary:
                        print(f"Salary: {salary}")
                    
                    # Check database
                    if not is_url_in_database(job_link):
                        print("✓ New job!")
                        add_url_in_database(job_link)
                        
                        # Build description
                        description = f"{job_name} - {job_company} - {job_location}"
                        if salary:
                            description += f" - {salary}"
                        
                        embed = create_embed(job_name, job_company, job_location, job_link, job_thumbnail)
                        
                        # Pass technologies to be saved
                        success = send_embed(embed, self, job_name, job_company, job_location, job_link, job_thumbnail, description)
                        
                        if success and techs:
                            # Update the job with technologies we found
                            from common.database import jobs_collection
                            jobs_collection.update_one(
                                {'url': job_link},
                                {'$set': {'technologies': techs}}
                            )
                        
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

            print(f'Indeed page finished - Total new jobs: {jobs_found_this_run}')
            page += 10
            
        print(f"\n{'='*50}")
        print(f"Indeed complete. Total new jobs: {jobs_found_this_run}")
        print(f"{'='*50}")
