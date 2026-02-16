import os
from dotenv import load_dotenv

load_dotenv()

"""
Here are all the constants we use in the program.
They are loaded from a .env file.
"""

MONGO_URL = os.getenv('MONGO_URL')
DISCORD_WEBHOOK = os.getenv("WEBHOOK_URL")
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
GOOGLE_CHROME_BIN = os.getenv("GOOGLE_CHROME_BIN", "/usr/bin/chromium")
