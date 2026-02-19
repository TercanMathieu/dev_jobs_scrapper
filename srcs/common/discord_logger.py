from discord_webhook import DiscordWebhook
from common.constants import DISCORD_LOG_WEBHOOK
from common.database import log_to_db
import datetime


def send_log(message, level="INFO"):
    """
    Envoie un log vers le channel Discord dédié ET vers MongoDB.
    
    Args:
        message: Le message à logger
        level: Niveau de log (INFO, SUCCESS, WARNING, ERROR)
    """
    
    # Log to MongoDB
    log_to_db(level, message)
    
    if not DISCORD_LOG_WEBHOOK:
        print(f"[LOG - {level}] {message}")
        return
    
    # Emoji selon le niveau
    emojis = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "SCRAP_START": "🔍",
        "SCRAP_END": "📊",
        "JOB_FOUND": "🎯"
    }
    
    emoji = emojis.get(level, "📝")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Couleur selon le niveau
    colors = {
        "INFO": "0x3498db",      # Bleu
        "SUCCESS": "0x2ecc71",   # Vert
        "WARNING": "0xf39c12",   # Orange
        "ERROR": "0xe74c3c",     # Rouge
        "SCRAP_START": "0x9b59b6", # Violet
        "SCRAP_END": "0x1abc9c",   # Turquoise
        "JOB_FOUND": "0xe91e63"    # Rose
    }
    
    color = colors.get(level, "0x95a5a6")
    
    # Créer le webhook
    webhook = DiscordWebhook(
        url=DISCORD_LOG_WEBHOOK,
        username="Job Scrapper Logger",
        avatar_url="https://cdn-icons-png.flaticon.com/512/2922/2922506.png"
    )
    
    # Créer l'embed
    from discord_webhook import DiscordEmbed
    embed = DiscordEmbed(
        title=f"{emoji} {level}",
        description=message,
        color=color
    )
    embed.set_timestamp()
    embed.set_footer(text=f"Dev Jobs Scrapper • {timestamp}")
    
    webhook.add_embed(embed)
    
    try:
        response = webhook.execute()
        if response.status_code != 200:
            print(f"Erreur envoi log Discord: {response.status_code}")
    except Exception as e:
        print(f"Exception envoi log: {e}")


def log_scrap_start(website_name):
    """Log le début d'un scraping"""
    send_log(f"Démarrage du scraping de **{website_name}**", "SCRAP_START")


def log_scrap_end(website_name, jobs_found=0):
    """Log la fin d'un scraping"""
    send_log(f"Scraping de **{website_name}** terminé • {jobs_found} job(s) trouvé(s)", "SCRAP_END")


def log_job_sent(job_name, job_company, website_name):
    """Log quand un job est envoyé sur Discord"""
    send_log(f"Nouveau job envoyé: **{job_name}** chez **{job_company}** (via {website_name})", "JOB_FOUND")


def log_error(website_name, error_message):
    """Log une erreur"""
    send_log(f"Erreur lors du scraping de **{website_name}**:\n```{error_message}```", "ERROR")


def log_iteration_start():
    """Log le début d'une itération"""
    send_log("🚀 Nouvelle itération de scraping lancée", "INFO")


def log_warning(message):
    """Log un avertissement"""
    send_log(message, "WARNING")
