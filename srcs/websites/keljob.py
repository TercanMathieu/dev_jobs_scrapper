import time
import re
from bs4 import BeautifulSoup

from common.webhook import create_embed, send_embed
from common.database import is_url_in_database, add_url_in_database
from common.website import Website


class Keljob(Website):
    """Scraper pour Keljob - Site fermé, redirigé vers Le Figaro Emploi"""

    def __init__(self):
        super().__init__(
            'Keljob',
            'https://www.keljob.com/emploi/recherche.html?motscles=developpeur&lieux=75P&page={}',
            'KELJOB',
            'https://www.keljob.com/assets/images/logo-keljob.svg',
            True,
        )
        self.page_load_timeout = 20

    def scrap(self):
        print("\n" + "="*50)
        print("KELJOB - Site fermé depuis 2024")
        print("Keljob a été racheté par Le Figaro Emploi.")
        print("Le scraper ne retournera plus d'offres.")
        print("="*50 + "\n")
        return 0
