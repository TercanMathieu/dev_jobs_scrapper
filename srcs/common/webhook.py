from discord_webhook import DiscordWebhook, DiscordEmbed
from common.constants import DISCORD_WEBHOOK
from common.discord_logger import log_job_sent
from common.database import save_job

def create_embed(job_name, job_company, job_location, job_link, job_thumbnail):
    """Create a discord embed object from the data of a Station F job listing."""
    embed = DiscordEmbed(title='🛎 NEW JOB FOUND ! 🛎')
    embed.set_description(job_name)
    embed.set_url(job_link)
    embed.add_embed_field(name='Company', value='🏢 {}'.format(job_company))
    embed.add_embed_field(name='Location', value='📍 {}'.format(job_location))
    embed.set_thumbnail(url=job_thumbnail)
    return embed

def extract_technologies(text):
    """Extract technologies from job text"""
    tech_keywords = {
        'javascript': ['javascript', 'js'],
        'typescript': ['typescript', 'ts'],
        'react': ['react', 'reactjs', 'react.js'],
        'angular': ['angular'],
        'vue': ['vue', 'vuejs', 'vue.js'],
        'svelte': ['svelte'],
        'nextjs': ['nextjs', 'next.js', 'next'],
        'node': ['nodejs', 'node.js', 'node'],
        'python': ['python'],
        'django': ['django'],
        'flask': ['flask'],
        'fastapi': ['fastapi'],
        'php': ['php'],
        'laravel': ['laravel'],
        'symfony': ['symfony'],
        'java': ['java'],
        'spring': ['spring', 'springboot'],
        'kotlin': ['kotlin'],
        'go': ['golang', 'go'],
        'rust': ['rust'],
        'ruby': ['ruby', 'rails'],
        'c++': ['c++', 'cpp'],
        'c#': ['c#', 'csharp', '.net'],
        'sql': ['sql', 'mysql', 'postgresql', 'mongodb'],
        'docker': ['docker', 'kubernetes', 'k8s'],
        'aws': ['aws', 'amazon web services'],
        'azure': ['azure', 'microsoft azure'],
        'gcp': ['gcp', 'google cloud'],
        'terraform': ['terraform'],
        'jenkins': ['jenkins', 'ci/cd'],
        'git': ['git', 'github', 'gitlab'],
        'graphql': ['graphql'],
        'rest': ['rest', 'restful', 'api'],
        'html': ['html', 'html5'],
        'css': ['css', 'css3', 'scss', 'sass'],
        'tailwind': ['tailwind', 'tailwindcss'],
        'bootstrap': ['bootstrap'],
    }
    
    text_lower = text.lower()
    found_techs = []
    
    for tech, keywords in tech_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                found_techs.append(tech)
                break
    
    return found_techs

def extract_seniority(text):
    """Extract seniority level from job text"""
    text_lower = text.lower()
    
    seniority_patterns = [
        (['lead', 'architect', 'staff', 'principal', 'expert'], 'lead'),
        (['senior', 'senior ', 'sr ', 'confirmé', 'confirme'], 'senior'),
        (['intermédiaire', 'intermediaire', 'mid ', 'intermediate'], 'mid'),
        (['junior', 'jr ', 'débutant', 'debutant', 'graduate', 'intern', 'alternance', 'apprenticeship'], 'junior'),
    ]
    
    for patterns, level in seniority_patterns:
        for pattern in patterns:
            if pattern in text_lower:
                return level
    
    return 'not_specified'

def extract_contract_type(text):
    """Extract contract type from job text"""
    text_lower = text.lower()
    
    if any(x in text_lower for x in ['cdi', 'permanent', 'unlimited']):
        return 'cdi'
    elif any(x in text_lower for x in ['cdd', 'fixed-term', 'temporary']):
        return 'cdd'
    elif any(x in text_lower for x in ['freelance', 'consultant', 'contractor']):
        return 'freelance'
    elif any(x in text_lower for x in ['stage', 'internship', 'intern']):
        return 'internship'
    elif any(x in text_lower for x in ['alternance', 'apprenticeship']):
        return 'apprenticeship'
    
    return 'not_specified'

def is_remote(text):
    """Check if job is remote-friendly"""
    text_lower = text.lower()
    remote_keywords = ['remote', 'télétravail', 'teletravail', 'full remote', 'hybride', 'hybrid', 'distanciel']
    return any(kw in text_lower for kw in remote_keywords)

def send_embed(embed, website, job_name="", job_company="", job_location="", job_link="", job_thumbnail="", description=""):
    """Send an embed to Discord and save to database."""
    webhook = DiscordWebhook(url=DISCORD_WEBHOOK, username=website.discord_username,
                             avatar_url=website.discord_avatar_url)
    webhook.add_embed(embed)
    response = webhook.execute()
    
    if response.status_code == 404:
        print('Couldn\'t send the embed to the webhook ' + DISCORD_WEBHOOK)
        return False
    
    # Log the job sent
    if job_name and job_company:
        log_job_sent(job_name, job_company, website.name)
    
    # Save to database with enriched data
    full_text = f"{job_name} {job_company} {description}"
    job_data = {
        'url': job_link,
        'name': job_name,
        'company': job_company,
        'location': job_location,
        'thumbnail': job_thumbnail,
        'source': website.name,
        'technologies': extract_technologies(full_text),
        'seniority': extract_seniority(full_text),
        'contract_type': extract_contract_type(full_text),
        'remote': is_remote(full_text),
        'description': description[:1000] if description else '',  # Truncate for storage
    }
    save_job(job_data)
    
    return True
