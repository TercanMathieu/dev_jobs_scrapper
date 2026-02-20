import os
from dotenv import load_dotenv

load_dotenv()

"""
Here are all the constants we use in the program.
They are loaded from a .env file.
"""

MONGO_URL = os.getenv('MONGO_URL')
DISCORD_WEBHOOK = os.getenv("WEBHOOK_URL")
DISCORD_LOG_WEBHOOK = os.getenv("LOG_WEBHOOK_URL")  # Webhook pour les logs
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
GOOGLE_CHROME_BIN = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/chromium")

# Proxy configuration for scraping
# Format: http://user:pass@host:port or http://host:port
PROXY_URL = os.getenv("PROXY_URL", "")  # Pour tous les sites
PROXY_LINKEDIN = os.getenv("PROXY_LINKEDIN", "")  # Proxy spécifique LinkedIn
PROXY_INDEED = os.getenv("PROXY_INDEED", "")  # Proxy spécifique Indeed

# ScrapingBee API (alternative aux proxies)
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")
