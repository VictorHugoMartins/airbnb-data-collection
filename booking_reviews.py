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

class BReview():
    """
    # ABListing represents an Airbnb hotel_id, as captured at a moment in time.
    # hotel_id, survey_id is the primary key.
    """
    def __init__(self, config, driver, hotel_id):
        self.config = config
        self.hotel_id = hotel_id
        self.review_url = self.get_review_url(driver)
        self.reviewer = self.get_reviewer(driver) #
        self.country = self.get_country(driver) #
        self.date = self.get_date(driver)
        self.review_title = self.get_review_title(driver)
        self.review_body = self.get_review_body(driver) #
        self.room = self.get_room_name(driver) #
        self.stay_date = self.get_stay_date(driver) # ta errado???
        self.rating = self.get_rating(driver) #
        self.response = self.get_response(driver)

    def get_reviewer(self, driver):
        try:
            return driver.find_element_by_class_name('bui-avatar-block__title').text
        except:
            return None

    def get_review_url(self, driver):
        try:
            return driver.get_attribute('data-review-url')
        except:
            return None

    def get_country(self, driver):
        try:
            return driver.find_element_by_class_name('bui-avatar-block__subtitle').text
        except:
            return None
    
    def get_review_body(self, driver):
        try:
            return driver.find_element_by_class_name('c-review__body').text # maybe elements
        except:
            return None

    def get_room_name(self, driver):
        try:
            return driver.find_element_by_class_name('room_info_heading').text.split('Ficou em: ')[1]
        except:
            return None
    
    def get_stay_date(self, driver):
        try:
            return driver.find_element_by_xpath('//div[@class="c-review-block__room-info__name"]/div[2]').text
        except:
            return None

    def get_rating(self, driver):
        try:
            return driver.find_element_by_class_name('bui-review-score__badge').text
        except:
            return None
    
    def get_review_title(self, driver):
        try:
            return driver.find_element_by_xpath('//div[@class="c-review-block__row"]/h3').text
        except:
            return None
                
    def get_date(self, driver):
        try:
            return driver.find_element_by_class_name('c-review-block__date').text.split('Avaliação: ')[1]
        except:
            return None

    def get_response(self, driver):
        try: # try to click for see more
            return driver.find_element_by_class_name('c-review-block__response__body').text
        except:
            return None

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
            
            if insert_replace_flag == self.config.FLAGS_INSERT_REPLACE:
                rowcount = self.__update()
            if (rowcount == 0 or
                    insert_replace_flag == self.config.FLAGS_INSERT_NO_REPLACE):
                try:
                    self.__insert()
                    return True
                except psycopg2.IntegrityError:
                    logger.debug("Room " + str(self.hotel_id) + ": already collected")
                    return False
        except psycopg2.OperationalError:
            # connection closed
            logger.error("Operational error (connection closed): resuming")
            del(self.config.connection)
        except psycopg2.DatabaseError as de:
            self.config.connection.conn.rollback()
            logger.error(psycopg2.errorcodes.lookup(de.pgcode[:2]))
            logger.error("Database error: resuming")
            del(self.config.connection)
        except psycopg2.InterfaceError:
            # connection closed
            logger.error("Interface error: resuming")
            del(self.config.connection)
        except psycopg2.Error as pge:
            # database error: rollback operations and resume
            self.config.connection.conn.rollback()
            logger.error("Database error: " + str(self.hotel_id))
            logger.error("Diagnostics " + pge.diag.message_primary)
            del(self.config.connection)
        except (KeyboardInterrupt, SystemExit):
            raise
        except UnicodeEncodeError as uee:
            logger.error("UnicodeEncodeError Exception at " +
                         str(uee.object[uee.start:uee.end]))
            raise
        except ValueError:
            logger.error("ValueError for hotel_id = " + str(self.hotel_id))
        except AttributeError:
            logger.error("AttributeError")
            raise
        except Exception:
            self.config.connection.rollback()
            logger.error("Exception saving room")
            raise

    def __insert(self):
        """ Insert a room into the database. Raise an error if it fails """
        try:
            logger.debug("Values: ")
            logger.debug("\treview: {}".format(self.review_url))
            conn = self.config.connect()
            cur = conn.cursor()
            sql = """
                insert into booking_reviews (
                    review_url, hotel_id, reviewer_name, country, date,
                    review_title, review_body, response, room, stay_date,
                    rating
                    )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            insert_args = (
                self.review_url, self.hotel_id, self.reviewer,
                self.country, self.date, self.review_title, self.review_body,
                self.response, self.room, self.stay_date, self.rating)
            cur.execute(sql, insert_args)
            cur.close()
            conn.commit()
            logger.debug("Review " + str(self.review_url) + ": inserted")

        except psycopg2.IntegrityError:
            logger.info("Review " + str(self.review_url) + ": insert failed")
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
            rowcount = 0
            conn = self.config.connect()
            cur = conn.cursor()
            logger.debug("Updating...")
            sql = """
                update booking_reviews set
                hotel_id = %s,
                reviewer_name = %s,
                country = %s,
                date = %s,
                review_title = %s,
                review_body = %s,
                response = %s,
                room = %s,
                stay_date = %s,
                rating = %s
                where review_url = %s 
                """
            update_args = (
                self.hotel_id, self.reviewer,
                self.country, self.date, self.review_title, self.review_body,
                self.response, self.room, self.stay_date, self.rating, self.review_url
                )
            logger.debug("Executing...")
            cur.execute(sql, update_args)
            rowcount = cur.rowcount
            logger.debug("Closing...")
            cur.close()
            conn.commit()
            if rowcount > 0:
                logger.debug("Room " + str(self.hotel_id) +
                        ": updated (" + str(rowcount) + ")")
            
            return rowcount
        except:
            # may want to handle connection close errors
            logger.debug("Exception in updating")
            logger.warning("Exception in __update: raising")
            raise
