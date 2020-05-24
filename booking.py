from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
import selenium
import json
import time
import re
import string
import requests
import bs4
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from airbnb_config import ABConfig
import argparse
import logging

SCRIPT_VERSION_NUMBER = "4.0"
domain =  'https://www.booking.com'

logger = logging.getLogger()

class BListing():
    """
    # ABListing represents an Airbnb room_id, as captured at a moment in time.
    # room_id, survey_id is the primary key.
    # Occasionally, a survey_id = None will happen, but for retrieving data
    # straight from the web site, and not stored in the database.
    """
    def __init__(self, config, driver):
        print("hmm")
        self.config = config
        self.get_hotel_id(driver)
        print(self.hotel_id)
        self.get_property_type(driver)
        print(self.property_type)
        self.get_name(driver)
        print(self.name)
        self.get_location(driver)
        print(self.location)
        self.get_popular_facilities(driver)
        print(self.popular_facilities)
        self.get_score(driver)
        print(self.score)
        self.get_reviews(driver)
        print(self.reviews)
        
        self.room_id = None
        self.bed_type = None
        self.accommodates = None
        self.price = None
        
        self.latitude = None
        self.longitude = None

    def get_location(self, driver):
        # Get the accommodation location
        try:
            self.location = driver.find_element_by_id('showMap2')\
            .find_element_by_class_name('hp_address_subtitle').text
        except:
            self.location = None

    def get_score(self, driver):
        # Get the accommodation score
        try:
            self.score = driver.find_element_by_class_name(
            'bui-review-score--end').find_element_by_class_name(
            'bui-review-score__badge').text
        except:
            self.score = None
    
    def get_property_type(self, driver):
        # Get the accommodation type
        try:
            self.property_type = driver.find_elements_by_xpath('//*[@id="hp_hotel_name"]/span')[0].text
        except:
            self.property_type = None

    def get_name(self, driver):    
        try:
            self.name = driver.find_element_by_id('hp_hotel_name')\
            .text.strip(str(self.property_type))
        except:
            self.name = None

        print(self.name)

    def get_hotel_id(self, driver):
        try:
            self.hotel_id = driver.find_elements_by_xpath('//*[@id="hp_facilities_box"]/div[6]/div[1]/input')[0].\
                                    get_attribute("value")
        except:
            self.hotel_id = None

    def get_reviews(self, driver):
        # Get the accommodation reviews count
        try:
            x = driver.find_elements_by_xpath('//*[@id="show_reviews_tab"]/span')
            try:
                self.reviews = x[0].text.split('(')[1].split(')')[0]
            except:
                self.reviews = 0
        except:
            self.reviews = None

    def get_popular_facilities(self, driver):
        try:
            # Get the most popular facilities
            facilities = driver.find_element_by_class_name('hp_desc_important_facilities')

            for facility in facilities.find_elements_by_class_name('important_facility'):
                self.popular_facilities.append(facility.text)
        except:
            self.popular_facilities = None

    def get_rooms_id(self, driver):
        rooms_id = []
        x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/td[@class="ftd roomType"]/div')
        n_rows = len(x)
        print(n_rows)
        for j in range(n_rows):
            try:
                rooms_id.append(x[j].get_attribute("id"))
                print("acc: ", x[j].get_attribute("id")," iter ", j)
            except:
                print("Rooms not finded")

        print("O TAMANHO CONTINUOU O MESMO???", n_rows == len(rooms_id))
        return rooms_id

    def get_accommodates(self, driver):
        # Get the rooms person capacity
        x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/td')
        print("linha 320")
        
        n_rows = len(x)
        print(n_rows)
        print("vai entrar no for agora:")

        accommodates = []

        for j in range(0, n_rows, 4): 
            try:
                accommodates.append(x[j].find_element_by_class_name('bui-u-sr-only').text.split('Máx. adultos: ')[1])
                print("acc: ", x[j].find_element_by_class_name('bui-u-sr-only').text.split('Máx. adultos: ')[1]," iter ", j)
            except:
                print("Accomodates not finded")

        return accommodates

    def save(self, insert_replace_flag):
        """
        Save a listing in the database. Delegates to lower-level methods
        to do the actual database operations.
        Return values:
            True: listing is saved in the database
            False: listing already existed
        """
        try:
            rowcount = -1
            print("save 51")
            
            if insert_replace_flag == self.config.FLAGS_INSERT_REPLACE:
                print("save aqui")
                rowcount = self.__update()
                print(rowcount)
                print("< - rowcount")
            if (rowcount == 0 or
                    insert_replace_flag == self.config.FLAGS_INSERT_NO_REPLACE):
                print("save esse outro")
                    
                try:
                    # self.get_location()
                    self.__insert()
                    return True
                except psycopg2.IntegrityError:
                    #logger.debug("Room " + str(self.name) + ": already collected")
                    return False
        except psycopg2.OperationalError:
            # connection closed
            #logger.error("Operational error (connection closed): resuming")
            del(self.config.connection)
        except psycopg2.DatabaseError as de:
            self.config.connection.conn.rollback()
            #logger.erro(psycopg2.errorcodes.lookup(de.pgcode[:2]))
            #logger.error("Database error: resuming")
            del(self.config.connection)
        except psycopg2.InterfaceError:
            # connection closed
            #logger.error("Interface error: resuming")
            del(self.config.connection)
        except psycopg2.Error as pge:
            # database error: rollback operations and resume
            self.config.connection.conn.rollback()
            #logger.error("Database error: " + str(self.room_id))
            #logger.error("Diagnostics " + pge.diag.message_primary)
            del(self.config.connection)
        except (KeyboardInterrupt, SystemExit):
            raise
        except UnicodeEncodeError as uee:
            print("Unicode")
            #logger.error("UnicodeEncodeError Exception at " +
                         #str(uee.object[uee.start:uee.end]))
            raise
        except ValueError:
            print("value")
            #logger.error("ValueError for room_id = " + str(self.room_id))
        except AttributeError:
            print("Atribute")
            #logger.error("AttributeError")
            raise
        except Exception:
            self.config.connection.rollback()
            #logger.error("Exception saving room")
            raise

    def __insert(self):
        """ Insert a room into the database. Raise an error if it fails """
        try:
            print("AQUI")
            #logger.debug("Values: ")
            #logger.debug("\troom: {}".format(self.name))
            conn = self.config.connect()
            cur = conn.cursor()
            sql = """
                insert into booking_room (
                    hotel_id, name, location, popular_facilities,
                    score, reviews, type)
                values (%s, %s, %s, %s, %s, %s, %s)"""
            insert_args = (
                self.hotel_id, self.name, self.location, self.popular_facilities,
                self.score, self.reviews, self.property_type,
                )
            cur.execute(sql, insert_args)
            cur.close()
            conn.commit()
            print("Room " + str(self.name) + ": inserted")
            #logger.debug("Room " + str(self.name) + ": inserted")
            #logger.debug("(lat, long) = ({lat:+.5f}, {lng:+.5f})".format(lat=self.latitude, lng=self.longitude))
        except psycopg2.IntegrityError:
            #logger.info("Room " + str(self.name) + ": insert failed")
            print("Insert failed")
            conn.rollback()
            cur.close()
            raise
        except:
            conn.rollback()
            raise

    def __update(self):
        """ Update a room in the database. Raise an error if it fails.
        Return number of rows affected."""
        try:
            print("Updating... 139")
            rowcount = 0
            conn = self.config.connect()
            print("144")
            cur = conn.cursor()
            #logger.debug("Updating...")
            print("147")
            print(self.score)
            print(self.location)
            print(self.popular_facilities)
            print(self.name)
            sql = """
                update booking_room
                name = %s,
                set score = %s,
                location = %s,
                popular_facilities = %s,
                reviews = %s,
                type = %s,
                last_modified = now()::timestamp
                where hotel_id = %s"""
            update_args = (
                self.name, self.score, self.location,
                self.popular_facilities,
                self.hotel_id, self.property_type,
                )
            #logger.debug("Executing...")
            cur.execute(sql, update_args)
            rowcount = cur.rowcount
            print("Hm aii")
            #logger.debug("Closing...")
            cur.close()
            conn.commit()
            #logger.info("Room " + str(self.name) +
                        #": updated (" + str(rowcount) + ")")
            print("sla 160")
            
            return rowcount
        except:
            # may want to handle connection close errors
            print("Exception in updating")
            #logger.warning("Exception in __update: raising")
            raise


def prepare_driver(url):
    '''Returns a Firefox Webdriver.'''
    options = Options()
    # options.add_argument('-headless')
    binary = FirefoxBinary('C:\\Program Files\\Mozilla Firefox\\firefox.exe')
    driver = webdriver.Firefox(firefox_binary=binary, executable_path=r'C:\\geckodriver.exe', options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.ID, 'ss')))
    return driver

def fill_form(driver, search_argument):
    '''Finds all the input tags in form and makes a POST requests.'''
    search_field = driver.find_element_by_id('ss')
    search_field.send_keys(search_argument)
    # We look for the search button and click it
    driver.find_element_by_class_name('sb-searchbox__button')\
        .click()
    wait = WebDriverWait(driver, timeout=10).until(
        EC.presence_of_all_elements_located(
            (By.CLASS_NAME, 'sr-hotel__title')))

def scrape_results(config, driver, n_results):
    '''Returns the data from n_results amount of results.'''
    try:
        accommodations_urls = list()
        accommodations_data = list()

        for accomodation_title in driver.find_elements_by_class_name('sr-hotel__title'):
            accommodations_urls.append(accomodation_title.find_element_by_class_name(
                'hotel_name_link').get_attribute('href'))

        for url in range(0, n_results):
            if url == n_results:
                break
            print("215")
            scrape_accommodation_data(config, driver, accommodations_urls[url])
            print("217")
            exit(0)
        
        return accommodations_data
    except IndexError:
        print("End of page")
        return accommodations_data

def scrape_accommodation_data(config, driver, accommodation_url):
    print("aaa")
    '''Visits an accommodation page and extracts the data.'''

    if driver == None:
        driver = prepare_driver(accommodation_url)

    driver.get(accommodation_url)
    time.sleep(12) # previously 12

    accommodation = BListing(config, driver)

    list_accommodates = []
    list_rooms_id = []

    list_accommodates = accommodation.get_accommodates(driver)
    list_rooms_id = accommodation.get_rooms_id(driver)

    print("igual?",len(list_accommodates) == len(list_rooms_id))

    n_rooms = len(list_rooms_id)
    print(n_rooms, "<- n_rooms")

    for i in range(n_rooms):
        accommodation.room_id = list_rooms_id[i]
        accommodation.accommodates = list_accommodates[i]
        print(accommodation.room_id, "<- rid")
        print(accommodation.accommodates, "<- acc")
        print("277")
        #accommodation.save(config.FLAGS_INSERT_REPLACE)
        #print("279 IMPORTANTISSIME")

    driver.quit()
    exit(0)

def search(config, area):
    driver = prepare_driver(domain)
    fill_form(driver, area)
    
    accommodations_data = list()
    
    urls = []
    for link in driver.find_elements_by_xpath('//*[@id="search_results_table"]/div[4]/nav/ul/li[2]/ul/li/a'):
        urls.append(link.get_attribute('href'))

    driver.quit()

    i = 1
    for url in urls:
        
        page = prepare_driver(url)
        print("Page ", i, " of ", len(urls))
        accommodations_data.append(scrape_results(config, page, 1))
        print("agora aqui")
        i = i + 1
        if i == 2:
            break
        
    '''accommodations_data = json.dumps(accommodations_data, indent=4)
    with open('booking_data.json', 'w') as f:
        print("escrevendo no arquivo")
        f.write(accommodations_data)'''

    page.quit()

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
    # Only one argument!
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-sb', '--search_by_bounding_box',
                       metavar='survey_id', type=int,
                       help="""search for rooms using survey survey_id,
                       by bounding box
                       """)
    group.add_argument('-sc', '--search_city',
                       metavar='city_name', type=str,
                       help="""search by a city
                       """)    

    args = parser.parse_args()
    return (parser, args)

def main():
    """
    Main entry point for the program.
    """

    (parser, args) = parse_args()
    logging.basicConfig(format='%(levelname)-8s%(message)s')
    config = ABConfig(args)

    search(config, args.search_city)
    exit(0)


    try:
        if args.search_by_bounding_box:
            search_city(config, config.FLAGS_ADD)
        elif args.printsearch_by_bounding_box:
            survey = ABSurveyByBoundingBox(config, args.printsearch_by_bounding_box)
            survey.search(config.FLAGS_PRINT)
        elif args.search_sublocalities:
            search_sublocalities(config, args.search_sublocalities)
        elif args.search_routes:
            search_routes(config, args.search_routes)
    except (SystemExit, KeyboardInterrupt):
        sys.exit()
    except Exception:
        logging.exception("Top level exception handler: quitting.")
        sys.exit(0)

if __name__ == "__main__":
    main()