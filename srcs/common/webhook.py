from discord_webhook import DiscordWebhook, DiscordEmbed
from common.constants import DISCORD_WEBHOOK
from common.discord_logger import log_job_sent
from common.database import save_job
from common.job_analyzer import analyze_job_page

def create_embed(job_name, job_company, job_location, job_link, job_thumbnail):
    """Create a discord embed object from the data of a Station F job listing."""
    embed = DiscordEmbed(title='🛎 NEW JOB FOUND ! 🛎')
    embed.set_description(job_name)
    embed.set_url(job_link)
    embed.add_embed_field(name='Company', value='🏢 {}'.format(job_company))
    embed.add_embed_field(name='Location', value='📍 {}'.format(job_location))
    embed.set_thumbnail(url=job_thumbnail)
    return embed

def send_embed(embed, website, job_name="", job_company="", job_location="", job_link="", job_thumbnail="", description=""):
    """Send an embed to Discord and save to database with detailed analysis."""
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
    
    # Analyze the job page for detailed information
    print(f"🔍 Analyzing job page: {job_link}")
    basic_info = {
        'name': job_name,
        'company': job_company,
        'location': job_location,
        'thumbnail': job_thumbnail,
    }
    
    # Scrape the full job page for better data
    job_data = analyze_job_page(job_link, basic_info)
    
    # Override with basic info if analysis failed
    if not job_data['name']:
        job_data['name'] = job_name
    if not job_data['company']:
        job_data['company'] = job_company
    if not job_data['location']:
        job_data['location'] = job_location
    if not job_data['thumbnail']:
        job_data['thumbnail'] = job_thumbnail
    
    # Save to database
    save_job(job_data)
    
    # Print summary
    print(f"✓ Job saved:")
    print(f"  - Name: {job_data['name']}")
    print(f"  - Company: {job_data['company']}")
    print(f"  - Seniority: {job_data['seniority']} ({job_data['years_experience']} years)")
    print(f"  - Technologies: {', '.join(job_data['technologies'][:5])}")
    print(f"  - Contract: {job_data['contract_type']}")
    print(f"  - Remote: {job_data['remote']}")
    
    return True
