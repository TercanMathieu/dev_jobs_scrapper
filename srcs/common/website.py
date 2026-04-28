from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from time import sleep
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from common.constants import CHROMEDRIVER_PATH, GOOGLE_CHROME_BIN


class Website:

    def __init__(self, name, url, discord_username, discord_avatar_url, should_scroll_page):
        self.name = name
        self.url = url
        self.discord_username = discord_username
        self.discord_avatar_url = discord_avatar_url
        self.should_scroll_page = should_scroll_page
        self.driver = None
        self.extra_chrome_options = []
        self.page_load_timeout = 15

    def _get_Driver(self):
        return self.driver

    def _init_driver(self, url):
        service = Service(executable_path=CHROMEDRIVER_PATH) if CHROMEDRIVER_PATH else Service()
        options = Options()
        options.headless = True
        options.binary_location = GOOGLE_CHROME_BIN
        options.add_argument("--window-size=1920,1200")
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")

        # Advanced anti-bot detection options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Additional anti-detection (applied to all scrapers)
        base_extra_options = [
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            '--accept-lang=fr-FR,fr;q=0.9,en;q=0.8',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--start-maximized',
            '--hide-scrollbars',
            '--dns-prefetch-disable',
        ]

        for opt in base_extra_options:
            options.add_argument(opt)

        # Add any extra options from subclasses
        for opt in self.extra_chrome_options:
            options.add_argument(opt)

        self.driver = webdriver.Chrome(options=options, service=service)
        self.driver.set_page_load_timeout(self.page_load_timeout)

        # Remove webdriver property to avoid detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Advanced stealth scripts
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', {
                get: () => ['fr-FR', 'fr', 'en-US', 'en']
            });
        """)

        self.driver.get(url)
        sleep(3)  # Let JS frameworks initialize

    def _get_chrome_page_data(self):
        if self.should_scroll_page:
            for _ in range(100):
                self.driver.execute_script(
                    "window.scrollTo(0, window.scrollY + 200)")
                sleep(0.1)
        sleep(8)
        page_data = self.driver.page_source
        self.driver.quit()
        return page_data

    def scrap(self):
        print("Scrap function is not implemented in website '{}'!".format(self.name))
