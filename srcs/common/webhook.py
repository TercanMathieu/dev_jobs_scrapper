from discord_webhook import DiscordWebhook, DiscordEmbed
from common.constants import DISCORD_WEBHOOK
from common.discord_logger import log_job_sent


def create_embed(job_name, job_company, job_location, job_link, job_thumbnail):
    """
    Create a discord embed object from the
    data of a Station F job listing.
    """

    embed = DiscordEmbed(title='🛎 NEW JOB FOUND ! 🛎')
    embed.set_description(job_name)
    embed.set_url(job_link)
    embed.add_embed_field(name='Company', value='🏢 {}'.format(job_company))
    embed.add_embed_field(name='Location', value='📍 {}'.format(job_location))
    embed.set_thumbnail(url=job_thumbnail)
    return embed


def send_embed(embed, website, job_name="", job_company=""):
    """
    Send an embed to the webhook specified in the .env file.
    Returns True if successful, False otherwise.
    """

    webhook = DiscordWebhook(url=DISCORD_WEBHOOK, username=website.discord_username,
                             avatar_url=website.discord_avatar_url)

    webhook.add_embed(embed)
    response = webhook.execute()
    if (response.status_code == 404):
        print('Couldn\'t send the embed to the webhook ' + DISCORD_WEBHOOK)
        return False
    
    # Log the job sent
    if job_name and job_company:
        log_job_sent(job_name, job_company, website.name)
    
    return True
