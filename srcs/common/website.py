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
    
    def _get_Driver(self):
        return self.driver
    
        """
        Open the given url and returns the data on the page.
        """
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
        
        # Anti-bot detection options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Add any extra options from subclasses
        for opt in self.extra_chrome_options:
            options.add_argument(opt)

        self.driver = webdriver.Chrome(
            options=options, service=service)
        
        # Remove webdriver property to avoid detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver.get(url)


       #-------------------- #### diviser la fonction en deux -----------------------



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
