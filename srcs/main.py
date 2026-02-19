from time import sleep

from websites.stationf import StationF
from websites.wttj import WTTJ
from websites.jobteaser import JobTeaser
from common.discord_logger import (
    log_iteration_start, log_scrap_start, 
    log_scrap_end, log_error
)

SLEEP_TIME = 900
WEBSITES_TO_SCRAP = [WTTJ(), JobTeaser(), StationF()]


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
