"""
Module pour analyser les fiches de poste détaillées.
Scrape la page du job pour extraire les vraies informations.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def fetch_job_page(url, timeout=10):
    """
    Récupère le contenu HTML d'une fiche de poste.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching job page {url}: {e}")
        return None

def clean_company_name(name):
    """
    Nettoie le nom de l'entreprise en supprimant les phrases invalides.
    """
    if not name:
        return "Entreprise non spécifiée"
    
    invalid_patterns = [
        'recrutement', 'recrute', 'recruiting', 'hiring',
        'active', 'actif', 'en cours', 'in progress',
        'publié', 'published', 'posté', 'posted',
        'il y a', 'ago', 'days', 'jours',
        'voir', 'view', 'en savoir', 'more',
    ]
    
    name_lower = name.lower()
    for pattern in invalid_patterns:
        if pattern in name_lower:
            return "Entreprise non spécifiée"
    
    return name.strip()

def extract_experience_years(text):
    """
    Extrait les années d'expérience requises du texte.
    Retourne le nombre d'années ou None si non trouvé.
    """
    patterns = [
        # Patterns français
        r'(\d+)\+?\s*ans?\s+d\'?exp[eé]rience',
        r'exp[eé]rience\s*:?\s*(\d+)\+?\s*ans?',
        r'(?:minimum|min|au\s+moins)\s*:?\s*(\d+)\+?\s*ans?',
        r'(\d+)\s*à\s*\d+\s*ans?\s+d\'?exp[eé]rience',
        r'profil\s+\w+\s*:?\s*(\d+)\+?\s*ans?',
        
        # Patterns anglais
        r'(\d+)\+?\s*years?\s+of\s+experience',
        r'(\d+)\+?\s*years?\s+experience',
        r'experience\s*:?\s*(\d+)\+?\s*years?',
        r'(?:minimum|min|at\s+least)\s*:?\s*(\d+)\+?\s*years?',
        r'(\d+)\s*-\s*\d+\s*years?',
        
        # Patterns avec expérience
        r'exp[eé]rience\s+professionnelle\s*:?\s*(\d+)',
        r'dipl[oô]m[eé]\s+d[e\']?un\s+profil\s+\w+\s*:?\s*(\d+)',
    ]
    
    text_lower = text.lower()
    years_found = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                years = int(match)
                if 0 < years < 20:  # Filtre les valeurs aberrantes
                    years_found.append(years)
            except:
                continue
    
    if years_found:
        return min(years_found)  # Prend le minimum requis
    
    return None

def determine_seniority_from_years(years):
    """
    Détermine la seniorité basée sur les années d'expérience.
    """
    if years is None:
        return 'not_specified'
    
    if years < 2:
        return 'junior'
    elif 2 <= years <= 5:
        return 'mid'
    else:
        return 'senior'

def extract_seniority_from_text(text):
    """
    Extrait la seniorité du texte avec détection des années d'expérience.
    """
    # D'abord chercher les années d'expérience
    years = extract_experience_years(text)
    if years is not None:
        return determine_seniority_from_years(years)
    
    # Fallback sur les mots-clés
    text_lower = text.lower()
    
    # Lead/Expert (plus haut niveau)
    if any(word in text_lower for word in ['lead tech', 'tech lead', 'architect', 'staff engineer', 'principal engineer', 'expert']):
        return 'lead'
    
    # Senior
    if any(word in text_lower for word in ['senior', 'senior ', 'sr ', 'confirmé', 'confirme', 'expérimenté', 'experimente']):
        return 'senior'
    
    # Mid
    if any(word in text_lower for word in ['intermédiaire', 'intermediaire', 'mid', 'intermediate']):
        return 'mid'
    
    # Junior
    if any(word in text_lower for word in ['junior', 'jr ', 'débutant', 'debutant', 'first job', 'premier emploi', 'graduate', 'jeune diplômé']):
        return 'junior'
    
    return 'not_specified'

def extract_technologies_from_text(text):
    """
    Extrait les technologies du texte avec une liste complète.
    """
    tech_keywords = {
        # Frontend
        'javascript': ['javascript', 'js', 'es6', 'es2015', 'vanilla js'],
        'typescript': ['typescript', 'ts', '.ts'],
        'react': ['react', 'reactjs', 'react.js', 'react native', 'next.js', 'nextjs', 'gatsby'],
        'angular': ['angular', 'angularjs', 'angular.js'],
        'vue': ['vue', 'vuejs', 'vue.js', 'nuxt', 'nuxt.js'],
        'svelte': ['svelte', 'sveltekit'],
        'solidjs': ['solidjs', 'solid.js'],
        'jquery': ['jquery'],
        
        # CSS/Frameworks UI
        'html': ['html', 'html5'],
        'css': ['css', 'css3'],
        'sass': ['sass', 'scss'],
        'tailwind': ['tailwind', 'tailwindcss', 'tailwind css'],
        'bootstrap': ['bootstrap'],
        'material-ui': ['material-ui', 'material ui', 'mui'],
        'styled-components': ['styled-components', 'styled components'],
        
        # Backend
        'node': ['nodejs', 'node.js', 'node js', 'express', 'fastify', 'nest.js', 'nestjs'],
        'python': ['python', 'django', 'flask', 'fastapi', 'tornado', 'pyramid'],
        'php': ['php', 'laravel', 'symfony', 'codeigniter', 'zend'],
        'java': ['java', 'spring', 'springboot', 'spring boot', 'jakarta ee', 'jee'],
        'kotlin': ['kotlin'],
        'scala': ['scala', 'akka', 'play framework'],
        'go': ['golang', 'go ', 'go.'],
        'rust': ['rust', 'actix', 'rocket'],
        'ruby': ['ruby', 'rails', 'sinatra'],
        'c++': ['c++', 'cpp', 'cplusplus'],
        'c#': ['c#', 'csharp', '.net', 'dotnet', 'asp.net', 'aspnetcore'],
        
        # Mobile
        'swift': ['swift', 'ios', 'iphone'],
        'kotlin-android': ['kotlin', 'android', 'jetpack compose'],
        'flutter': ['flutter', 'dart'],
        'react-native': ['react native', 'react-native'],
        
        # Bases de données
        'postgresql': ['postgresql', 'postgres', 'psql'],
        'mysql': ['mysql', 'mariadb'],
        'mongodb': ['mongodb', 'mongo', 'mongoose'],
        'redis': ['redis'],
        'elasticsearch': ['elasticsearch', 'elastic search'],
        'cassandra': ['cassandra'],
        'dynamodb': ['dynamodb', 'dynamo db'],
        'firebase': ['firebase', 'firestore'],
        'sqlite': ['sqlite'],
        'sql': ['sql', 'pl/sql', 'tsql'],
        
        # DevOps/Cloud
        'docker': ['docker', 'containerization', 'containers'],
        'kubernetes': ['kubernetes', 'k8s', 'helm'],
        'aws': ['aws', 'amazon web services', 'ec2', 's3', 'lambda', 'cloudfront'],
        'azure': ['azure', 'microsoft azure', 'azure devops'],
        'gcp': ['gcp', 'google cloud', 'google cloud platform'],
        'terraform': ['terraform', 'infrastructure as code', 'iac'],
        'ansible': ['ansible'],
        'jenkins': ['jenkins', 'ci/cd', 'cicd', 'pipeline'],
        'github-actions': ['github actions', 'gitlab ci'],
        'circleci': ['circleci', 'circle ci'],
        'travisci': ['travisci', 'travis ci'],
        
        # Outils
        'git': ['git', 'github', 'gitlab', 'bitbucket'],
        'jira': ['jira'],
        'confluence': ['confluence'],
        'figma': ['figma'],
        'sketch': ['sketch'],
        'adobe-xd': ['adobe xd', 'xd'],
        
        # API/Protocols
        'graphql': ['graphql', 'apollo'],
        'rest': ['rest', 'restful', 'rest api', 'api rest'],
        'grpc': ['grpc', 'grpc-web'],
        'websocket': ['websocket', 'websockets', 'socket.io', 'socketio'],
        'oauth': ['oauth', 'oauth2', 'openid', 'jwt'],
        
        # Testing
        'jest': ['jest'],
        'cypress': ['cypress'],
        'selenium': ['selenium'],
        'playwright': ['playwright'],
        'mocha': ['mocha'],
        'jasmine': ['jasmine'],
        'pytest': ['pytest'],
        'junit': ['junit'],
        'cucumber': ['cucumber', 'gherkin'],
        
        # State Management
        'redux': ['redux', '@redux'],
        'mobx': ['mobx'],
        'zustand': ['zustand'],
        'recoil': ['recoil'],
        
        # Build Tools
        'webpack': ['webpack'],
        'vite': ['vite'],
        'parcel': ['parcel'],
        'rollup': ['rollup'],
        'esbuild': ['esbuild'],
        'babel': ['babel'],
        
        # Data Science/ML
        'pandas': ['pandas'],
        'numpy': ['numpy'],
        'scikit-learn': ['scikit-learn', 'sklearn'],
        'tensorflow': ['tensorflow'],
        'pytorch': ['pytorch'],
        'keras': ['keras'],
        
        # CMS
        'wordpress': ['wordpress'],
        'drupal': ['drupal'],
        'shopify': ['shopify'],
        'prestashop': ['prestashop'],
        'magento': ['magento'],
        
        # Methodologies
        'agile': ['agile', 'scrum', 'kanban'],
        'tdd': ['tdd', 'test driven', 'test-driven'],
        'ddd': ['ddd', 'domain driven', 'domain-driven'],
    }
    
    text_lower = text.lower()
    found_techs = []
    found_set = set()
    
    for tech, keywords in tech_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                if tech not in found_set:
                    found_techs.append(tech)
                    found_set.add(tech)
                break
    
    return sorted(found_techs)

def extract_remote_days(text):
    """
    Extrait le nombre de jours de télétravail autorisés.
    Retourne: None (pas de remote), 'full' (100%), 'hybrid' (partiel), ou un nombre de jours (1-4)
    """
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Full remote patterns
    full_remote_patterns = [
        'full remote', '100% remote', 'remote 100%', 'fullremote',
        'full télétravail', '100% télétravail', 'télétravail 100%',
        'full teletravail', '100% teletravail',
        'remote first', 'remote-first', 'fully remote',
        'no office', 'pas de bureau', 'à domicile', 'à distance',
    ]
    
    for pattern in full_remote_patterns:
        if pattern in text_lower:
            return 'full'
    
    # Hybrid patterns with days
    hybrid_patterns = [
        r'(\d+)\s*(?:days?|jours?)?\s*(?:per\s*week|par\s*semaine)?\s*(?:remote|télétravail|teletravail)',
        r'remote\s*(?:\s*-\s*)?(\d+)\s*(?:days?|jours?)',
        r'télétravail\s*(?:\s*-\s*)?(\d+)\s*(?:jours?|days?)',
        r'(\d+)\s*(?:jours?|days?)?\s*(?:de\s*)?(?:télétravail|teletravail|remote)',
        r'(\d+)j?\s*/\s*\d+',
        r'télétravail\s*:\s*(\d+)\s*jours?',
        r'remote\s*:\s*(\d+)\s*(?:days?|jours?)',
        r'(\d+)\s*(?:jours?|days?)\s*(?:par\s*semaine|per\s*week)?\s*(?:en\s*)?(?:télétravail|teletravail|remote)',
    ]
    
    for pattern in hybrid_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                days = int(match)
                if 1 <= days <= 4:
                    return days
            except:
                continue
    
    # Hybrid générique
    hybrid_keywords = ['hybride', 'hybrid', 'flexible', 'partiel', 'partial', 
                       'télétravail possible', 'remote possible', 'télétravail ouvert',
                       'remote friendly', 'remote-friendly', 'télétravail occasionnel']
    
    for kw in hybrid_keywords:
        if kw in text_lower:
            return 'hybrid'
    
    return None

def analyze_job_page(url, basic_info=None):
    """
    Analyse complète d'une fiche de poste.
    """
    # Récupérer le contenu de la page
    html_content = fetch_job_page(url)
    
    # Nettoyer le nom de l'entreprise
    company_name = clean_company_name(basic_info.get('company', '') if basic_info else '')
    
    if html_content is None:
        # Si on ne peut pas scraper, utiliser les infos de base nettoyées
        return {
            'url': url,
            'name': basic_info.get('name', '') if basic_info else '',
            'company': company_name,
            'location': basic_info.get('location', 'Paris') if basic_info else 'Paris',
            'thumbnail': basic_info.get('thumbnail', '') if basic_info else '',
            'technologies': [],
            'seniority': 'not_specified',
            'years_experience': None,
            'contract_type': 'not_specified',
            'remote': False,
            'remote_days': None,
            'description': '',
            'salary': None,
        }
    
    # Parser le HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Check if we got a Cloudflare/verification page
    page_text = soup.get_text().lower()
    if any(x in page_text for x in ['cf-browser-verification', 'ray id', 'checking your browser', 'please wait', 'cloudflare']):
        print(f"⚠️ Cloudflare/verification page detected for {url}, using basic info only")
        return {
            'url': url,
            'name': basic_info.get('name', '') if basic_info else '',
            'company': company_name,
            'location': basic_info.get('location', 'Paris') if basic_info else 'Paris',
            'thumbnail': basic_info.get('thumbnail', '') if basic_info else '',
            'technologies': [],
            'seniority': 'not_specified',
            'years_experience': None,
            'contract_type': 'not_specified',
            'remote': False,
            'remote_days': None,
            'description': '',
            'full_content': '',
        }
    
    # Extraire tout le texte visible
    for script in soup(['script', 'style', 'nav', 'footer', 'header']):
        script.decompose()
    
    # Récupérer le texte
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    
    # Extraire les informations
    years_exp = extract_experience_years(text)
    seniority = extract_seniority_from_text(text) if years_exp is None else determine_seniority_from_years(years_exp)
    technologies = extract_technologies_from_text(text)
    
    # Extraire le type de contrat
    contract_type = 'not_specified'
    text_lower = text.lower()
    if any(x in text_lower for x in ['cdi', 'permanent']):
        contract_type = 'cdi'
    elif any(x in text_lower for x in ['cdd', 'fixed-term']):
        contract_type = 'cdd'
    elif any(x in text_lower for x in ['freelance', 'consultant']):
        contract_type = 'freelance'
    elif any(x in text_lower for x in ['stage', 'internship']):
        contract_type = 'internship'
    elif any(x in text_lower for x in ['alternance', 'apprenticeship']):
        contract_type = 'apprenticeship'
    
    # Extraire le thumbnail/logo si pas déjà présent
    thumbnail = basic_info.get('thumbnail', '') if basic_info else ''
    if not thumbnail:
        # Try to find company logo image
        # LinkedIn specific selectors
        img_selectors = [
            ('img', {'class': lambda x: x and 'company' in str(x).lower() and 'logo' in str(x).lower()}),
            ('img', {'data-test-id': 'company-logo'}),
            ('img', {'src': lambda x: x and 'company-logo' in str(x)}),
            ('img', {'alt': lambda x: x and 'logo' in str(x).lower()}),
        ]
        
        for tag, attrs in img_selectors:
            img = soup.find(tag, attrs)
            if img and img.get('src'):
                thumbnail = img['src']
                break
        
        # If still no thumbnail, try to find any image with company name
        if not thumbnail and company_name and company_name != "Entreprise non spécifiée":
            for img in soup.find_all('img'):
                alt = img.get('alt', '')
                if company_name.lower() in alt.lower() or 'logo' in alt.lower():
                    if img.get('src'):
                        thumbnail = img['src']
                        break
    
    # Make sure thumbnail is absolute URL
    if thumbnail and thumbnail.startswith('/'):
        thumbnail = urljoin(url, thumbnail)
    
    # Remote avec nombre de jours
    remote_days = extract_remote_days(text)
    remote = remote_days is not None
    
    return {
        'url': url,
        'name': basic_info.get('name', '') if basic_info else '',
        'company': company_name,
        'location': basic_info.get('location', 'Paris') if basic_info else 'Paris',
        'thumbnail': thumbnail,
        'technologies': technologies,
        'seniority': seniority,
        'years_experience': years_exp,
        'contract_type': contract_type,
        'remote': remote,
        'remote_days': remote_days,
        'description': text[:2000],
        'full_content': text,
    }

# Test
if __name__ == '__main__':
    # Test d'extraction de remote
    test_texts = [
        "Poste en full remote",
        "Télétravail 2 jours par semaine",
        "3 jours de remote par semaine",
        "Mode hybride possible",
        "Pas de télétravail",
        "2-3 days remote per week",
        "Full remote 100%",
        "Télétravail 1 jour / 5",
    ]
    
    for text in test_texts:
        days = extract_remote_days(text)
        print(f"Text: {text[:50]}...")
        print(f"  Remote days: {days}")
        print()
