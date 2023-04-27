import re
import bs4
import time
import json
import string
import logging
import requests
import argparse
import selenium
import psycopg2
from lxml import html
from selenium import webdriver
from general_config import ABConfig
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

logger = logging.getLogger()
DOMAIN = 'https://www.airbnb.com.br/rooms/'


def prepare_driver(url):
    '''Returns a Firefox Webdriver.'''
    options = Options()
    # options.add_argument('-headless')
    binary = FirefoxBinary('C:\\Program Files\\Mozilla Firefox\\firefox.exe')
    driver = webdriver.Firefox(
        firefox_binary=binary, executable_path=r'C:\\geckodriver.exe', options=options)
    driver.get(url)
    time.sleep(5)
    return driver


def save_as_deleted(config, room_id):
    try:
        logger.debug("Marking room deleted: " + str(room_id))
        conn = config.connect()
        sql = """
			update room
			set deleted = 1, last_modified = now()::timestamp
			where room_id = %s
		"""
        cur = conn.cursor()
        cur.execute(sql, (room_id,))
        cur.close()
        conn.commit()
    except Exception:
        logger.error("Failed to save room as deleted")
        raise


def update_comodities(config, driver, city, room_id, survey_id):
    try:
        comodities = []
        comodidades = driver.find_elements(By.CLASS_NAME, 'iikjzje')
        for c in comodidades:
            if (('Indisponível' not in c.text) and ('\n' not in c.text)):
                comodities.append(c.text)
        rowcount = -1
        logging.info("Searching for comodities")
        conn = config.connect()
        cur = conn.cursor()

        sql = """UPDATE room set comodities = %s
				where room_id = %s and survey_id = %s comodities is null"""
        update_args = (comodities, room_id, survey_id)
        cur.execute(sql, update_args)
        conn.commit()

        print("Comodities of room ", room_id, " updated for ", comodities)
        return True
    except selenium.common.exceptions.NoSuchElementException:
        print("Unable to find comodities")
        raise


def update_overall_satisfaction(config, driver, city, room_id):
    try:
        try:
            overall_satisfaction = driver.find_element(By.XPATH, '//*[@id="site-content"]'
                                                       '/div/div[1]/div/div/div/section/div[1]/div[2]/span[1]/span[2]/button/span[1]')
            score = overall_satisfaction.text.replace(',', '.')
        except selenium.common.exceptions.NoSuchElementException:
            print("This room don't have a classification yet.")
            return

        rowcount = -1
        logging.info("Searching for overall satisfaction")
        conn = config.connect()
        cur = conn.cursor()

        sql = """UPDATE room set overall_satisfaction = %s
			where room_id = %s and overall_satisfaction is null"""
        update_args = (score, room_id)
        cur.execute(sql, update_args)
        conn.commit()

        print("Overall satisfaction of room ", room_id, " updated for ", score)
        return True
    except selenium.common.exceptions.NoSuchElementException:
        print("Unable to find overall satisfaction")
        raise


def update_bathroom(config, driver, city, room_id, survey_id):
    try:
        # try:
        x = driver.find_element(
            By.XPATH, '//*[@id="site-content"]/div/div/div[3]/div[1]/div/div[1]/div/div/div/div/div[1]/div[2]/span[7]')
        bathroom = x.text
        '''except selenium.common.exceptions.NoSuchElementException:
			print("This room don't have bathroom specifications.")
			return'''

        rowcount = -1
        logging.info("Searching for price")
        conn = config.connect()
        cur = conn.cursor()

        sql = """UPDATE room set bathroom = %s
			where room_id = %s and survey_id = %s"""
        update_args = (bathroom, room_id, survey_id)
        cur.execute(sql, update_args)
        conn.commit()

        print("Bathroom of room ", room_id, " updated for ", bathroom)
        return True
    except selenium.common.exceptions.NoSuchElementException:
        print("Unable to find element")
        raise


def update_price(config, driver, city, room_id):
    try:
        try:
            x = driver.find_element(
                By.XPATH, '//*[@class="_ymq6as"]/span/span[@class="_pgfqnw"]')
            price = x.text.replace('.', '').replace(',', '.').split('R$')[1]
        except selenium.common.exceptions.NoSuchElementException:
            print("This room don't have a price yet.")
            return

        rowcount = -1
        logging.info("Searching for price")
        conn = config.connect()
        cur = conn.cursor()

        sql = """UPDATE room set price = %s, currency = 'RS'
			where room_id = %s"""
        update_args = (price, room_id)
        cur.execute(sql, update_args)
        conn.commit()

        print("Price of room ", room_id, " updated for ", price)
        return True
    except selenium.common.exceptions.NoSuchElementException:
        print("Unable to find element")
        raise


def update_with_preexistent_comodities(config, city, args):
    try:
        rowcount = -1
        logging.info("Initialing search by overall satisfactions")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(room_id), comodities from room where city = %s
				and comodities is not null
				order by room_id"""  # and comodities is null
        # and price is null
        # and overall_satisfaction is null

        cur.execute(sql, (city,))
        rowcount = cur.rowcount
        print(rowcount, " results")

        if rowcount > 0:
            results = cur.fetchall()
            for result in results:
                room_id = result[0]
                comodities = result[1]
                rowcount = -1
                sql = """UPDATE room set comodities = %s
						where room_id = %s and comodities is null"""
                update_args = (comodities, room_id)
                cur.execute(sql, update_args)
                rowcount = cur.rowcount
                conn.commit()

                print(rowcount, " comodities updated")
        return True
    except Exception:
        logger.error("Failed to update comodities")
        raise


def search(config, city, survey_id, args):
    try:
        driver = None
        rowcount = -1
        logging.info("Initialing search by overall satisfactions")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(room_id) from room, search_area
				where survey_id = %s"""  # and comodities is null
        # and price is null
        # and overall_satisfaction is null

        cur.execute(sql, (city,))
        rowcount = cur.rowcount
        print(rowcount, " results")

        if rowcount > 0:
            results = cur.fetchall()
            for result in results:
                room_id = result[0]
                url = DOMAIN + str(result[0])
                for i in range(config.ATTEMPTS_TO_FIND_PAGE):
                    try:
                        print("Attempt ", i+1, " to find room ", room_id)
                        driver = prepare_driver(url)

                        if url not in driver.current_url:
                            print("Room ", room_id, " has been removed")
                            save_as_deleted(config, room_id)
                            driver.quit()
                            break
                        print("chegou aqui depois de preparar o driver")
                        time.sleep(3)
                        # try to identify a plugin with cookie's preference blocking the screen
                        try:
                            driver.find_element(
                                By.XPATH, '/html/body/div[1]/div[2]/div[4]/div[2]/div/button').click()
                        except (selenium.common.exceptions.NoSuchElementException,
                                selenium.common.exceptions.ElementNotInteractableException):
                            try:
                                driver.find_element(
                                    By.XPATH, '/html/body/div[6]/div/div/div[1]/section/footer/div[2]').click()
                            except:
                                try:
                                    driver.find_element(
                                        By.XPATH, '/html/body/div[6]/div/div/div[1]/section/footer/div[2]/button').click()
                                except:
                                    print("No cookies privacy")
                        time.sleep(3)
                        try:
                            update_bathroom(config, driver, city, room_id, survey_id)
                        except:
                            print("No bathroom finded")
                        update_comodities(config, driver, city, room_id, survey_id)
                        
                        driver.quit()
                        print("Data collected")
                        break
                    except selenium.common.exceptions.TimeoutException:
                        print("TimeOutException")
                        if driver is not None:
                            driver.quit()
                        continue
                    except (SystemExit, KeyboardInterrupt):
                        print("Interrupted execution")
                        if driver is not None:
                            driver.quit()
                        exit(0)
    except selenium.common.exceptions.WebDriverException:
        logger.error("WebDriverException")
    except Exception:
        logger.error("Failed to search overall satisfactions")
        raise

def parse_args():
    """
    Read and parse command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='Manage a database of Airbnb listings.',
        usage='%(prog)s [options]')
    parser.add_argument("-v", "--verbose",
                        action="store_true", default=False,
                        help="""write verbose (debug) output to the log file""")
    parser.add_argument("-c", "--config_file",
                        metavar="config_file", action="store", default=None,
                        help="""explicitly set configuration file, instead of
						using the default <username>.config""")
    parser.add_argument("-cd", "--check_date",
                        action="store_true", default=True,
                        help="""search using a checkin-checkout date""")  # para implementar
    parser.add_argument("-p", "--price",
                        action="store_true", default=True,
                        help="""update price""")  # para implementar
    parser.add_argument("-os", "--overall_satisfaction",
                        action="store_true", default=True,
                        help="""update overall_satisfaction""")  # para implementar
    parser.add_argument("-co", "--comodities",
                        action="store_true", default=True,
                        help="""update comodities""")  # para implementar
    parser.add_argument("-cm", "--comments",
                        action="store_true", default=True,
                        help="""update review's comment""")  # para implementar
    parser.add_argument("-upc", "--update_preexistent_comodities",
                        action="store_true", default=False,
                        help="""update comodities with values preexistents""")  # para implementar
    parser.add_argument('-sc', '--search_city',
                        metavar='city_name', type=str,
                        help="""search by a city
					   """)

    # Only one argument!
    group = parser.add_mutually_exclusive_group()

    args = parser.parse_args()
    return (parser, args)


def main():
    """
    Main entry point for the program.
    """
    (parser, args) = parse_args()
    logging.basicConfig(format='%(levelname)-8s%(message)s')
    config = ABConfig(args)

    try:
        if args.search_city:
            if args.update_preexistent_comodities:
                update_with_preexistent_comodities(
                    config, args.search_city, args)
            else:
                search(config, args.search_city, args)
    except (SystemExit, KeyboardInterrupt):
        logger.debug("Interrupted execution")
        exit(0)
    except Exception:
        logging.exception("Top level exception handler: quitting.")
        exit(0)


if __name__ == "__main__":
    main()


# .iikjzje.i10xc1ab.dir.dir-ltr
