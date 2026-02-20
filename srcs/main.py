from time import sleep

from websites.stationf import StationF
from websites.wttj import WTTJ
from websites.jobteaser import JobTeaser
from websites.indeed import Indeed  # Enabled with proxy
from websites.linkedin import LinkedIn  # Enabled with proxy
from websites.apec import APEC
from websites.lesjeudis import LesJeudis
from websites.cadremploi import Cadremploi
from websites.keljob import Keljob
from common.discord_logger import (
    log_iteration_start, log_scrap_start,
    log_scrap_end, log_error
)

SLEEP_TIME = 900
WEBSITES_TO_SCRAP = [
    WTTJ(),
    JobTeaser(),
    StationF(),
    APEC(),
    LesJeudis(),
    Cadremploi(),
    Keljob(),
]

# Add Indeed and LinkedIn only if proxies are configured
from common.constants import PROXY_INDEED, PROXY_LINKEDIN
if PROXY_INDEED:
    WEBSITES_TO_SCRAP.append(Indeed())
    print("✅ Indeed enabled with proxy")
else:
    print("⚠️  Indeed disabled - no proxy configured (PROXY_INDEED)")

if PROXY_LINKEDIN:
    WEBSITES_TO_SCRAP.append(LinkedIn())
    print("✅ LinkedIn enabled with proxy")
else:
    print("⚠️  LinkedIn disabled - no proxy configured (PROXY_LINKEDIN)")


def main():
    """
    Main function of the program.
    Looping every $SLEEP_TIME seconds on the websites to scrap, and send notifications on Discord
    when a new job is found.
    """

    print("Starting Developer Job Scrapper..")

    while True:

        print("Running another iteration..")
        log_iteration_start()
        
        for website in WEBSITES_TO_SCRAP:
            try:
                log_scrap_start(website.name)
                print("== SCRAPING {} ===".format(website.name))
                website.scrap()
                log_scrap_end(website.name)
                print("SCRAP OF {} FINISHED!\n".format(website.name))
            except Exception as e:
                error_msg = str(e)
                log_error(website.name, error_msg)
                print("Unable to scrap {}:".format(website.name))
                print(e)

        sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()
