#!/usr/bin/python3
# ============================================================================
# Tom Slee, 2013--2017.
#
# An ABListing represents and individual Airbnb listing
# ============================================================================
import logging
import re
from lxml import html
import psycopg2
import json
import airbnb_ws
import sys
import random
import time
from datetime import date
from bs4 import BeautifulSoup
import json

import airbnb_ws

from airbnb_geocoding import Location
from airbnb_geocoding import reverse_geocode_coordinates_and_insert

logger = logging.getLogger()


class ABListing():
    """
    # ABListing represents an Airbnb room_id, as captured at a moment in time.
    # room_id, survey_id is the primary key.
    # Occasionally, a survey_id = None will happen, but for retrieving data
    # straight from the web site, and not stored in the database.
    """
    def __init__(self, config, room_id, survey_id):
        self.config = config
        self.room_id = room_id
        self.host_id = None
        self.room_type = None
        self.country = None
        self.city = None
        self.neighborhood = None
        self.address = None
        self.reviews = None
        self.reviews_text = False
        self.overall_satisfaction = None
        self.accommodates = None
        self.bedrooms = None
        self.bathrooms = None
        self.price = None
        self.deleted = None
        self.minstay = None
        self.latitude = None
        self.longitude = None
        self.survey_id = survey_id
        #  extra fields added from search json:
        # coworker_hosted (bool)
        self.coworker_hosted = None
        # extra_host_languages (list)
        self.extra_host_languages = None
        # name (str)
        self.name = None
        # property_type (str)
        self.property_type = None
        # currency (str)
        self.currency = None
        # rate_type (str) - "nightly" or other?
        self.rate_type = None
        self.sublocality = None
        self.route = None
        self.is_superhost = None
        self.max_nights = None
        self.avg_rating = None
        self.person_capacity = None
        self.pictures = None
        self.bathroom = None
        self.location_id = None

        logger.setLevel(config.log_level)

    def status_check(self):
        # if sufficient of the values are None or don't exist, the room 
        # entry was not properly parsed and we may as well throw the whole
        # thing away.
        status = True  # OK
        unassigned_values = {key: value
                             for key, value in vars(self).items()
                             if not key.startswith('__') and
                             not callable(key) and
                             value is None
                             }
        if len(unassigned_values) > 9:  # just a value indicating deleted
            logger.info("Room " + str(self.room_id) + ": marked deleted")
            status = False  # probably deleted
            self.deleted = 1
        else:
            for key, val in unassigned_values.items():
                if (key == "overall_satisfaction" and "reviews" not in
                        unassigned_values):
                    if val is None and self.reviews > 2:
                        logger.debug("Room " + str(self.room_id) + ": No value for " + key)
                elif val is None:
                    logger.debug("Room " + str(self.room_id) + ": No value for " + key)
        return status

    def get_columns(self):
        """
        Hack: callable(attr) includes methods with (self) as argument.
        Need to find a way to avoid these.
        This hack does also provide the proper order, which matters
        """
        # columns = [attr for attr in dir(self) if not
        # callable(attr) and not attr.startswith("__")]
        columns = ("room_id", "host_id", "room_type", "country",
                   "city", "neighborhood", "address", "reviews",
                   "overall_satisfaction", "accommodates", "bedrooms",
                   "bathrooms", "price", "deleted", "minstay",
                   "latitude", "longitude", "survey_id", "last_modified",)
        return columns

    def save_as_deleted(self):
        try:
            logger.debug("Marking room deleted: " + str(self.room_id))
            if self.survey_id is None:
                return
            conn = self.config.connect()
            sql = """
                update room
                set deleted = 1, last_modified = now()::timestamp
                where room_id = %s
                and survey_id = %s
            """
            cur = conn.cursor()
            cur.execute(sql, (self.room_id, self.survey_id))
            cur.close()
            conn.commit()
        except Exception:
            logger.error("Failed to save room as deleted")
            raise

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
            if self.deleted == 1:
                self.save_as_deleted()
            else:
                '''if insert_replace_flag == self.config.FLAGS_INSERT_REPLACE:
                    rowcount = self.__update()
                '''
                if (rowcount == 0 or
                        insert_replace_flag == self.config.FLAGS_INSERT_NO_REPLACE):
                    try:
                        if (self.config.FLAGS_INSERT_IN_LOCATION): self.location_id = reverse_geocode_coordinates_and_insert(self.config, self.latitude, self.longitude)
                        self.__insert()
                        return True
                    except psycopg2.IntegrityError:
                        logger.debug("Room " + str(self.room_id) + ": already collected")
                        return False
        except psycopg2.OperationalError:
            # connection closed
            logger.error("Operational error (connection closed): resuming")
            del(self.config.connection)
        except psycopg2.DatabaseError as de:
            self.config.connection.conn.rollback()
            logger.erro(psycopg2.errorcodes.lookup(de.pgcode[:2]))
            logger.error("Database error: resuming")
            del(self.config.connection)
        except psycopg2.InterfaceError:
            # connection closed
            logger.error("Interface error: resuming")
            del(self.config.connection)
        except psycopg2.Error as pge:
            # database error: rollback operations and resume
            self.config.connection.conn.rollback()
            logger.error("Database error: " + str(self.room_id))
            logger.error("Diagnostics " + pge.diag.message_primary)
            del(self.config.connection)
        except (KeyboardInterrupt, SystemExit):
            raise
        except UnicodeEncodeError as uee:
            logger.error("UnicodeEncodeError Exception at " +
                         str(uee.object[uee.start:uee.end]))
            raise
        except ValueError:
            logger.error("ValueError for room_id = " + str(self.room_id))
        except AttributeError:
            logger.error("AttributeError")
            raise
        except Exception:
            self.config.connection.rollback()
            logger.error("Exception saving room")
            raise

    def __insert(self):
        """ Insert a room into the database. Raise an error if it fails """
        print("o location id do quarto: ", self.location_id)
        try:
            logger.debug("Values: ")
            logger.debug("\troom_id: {}".format(self.room_id))
            logger.debug("\thost_id: {}".format(self.host_id))
            conn = self.config.connect()
            cur = conn.cursor()
            sql = """
                insert into room (
                    room_id, host_id, room_type, country, city,
                    neighborhood, address, reviews, overall_satisfaction,
                    accommodates, bedrooms, bathrooms, price, deleted,
                    minstay, latitude, longitude, survey_id,
                    coworker_hosted, extra_host_languages, name,
                    property_type, currency, rate_type,
                    sublocality, route, avg_rating,
                    is_superhost, max_nights, pictures, bathroom, location_id)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )"""
            insert_args = (
                self.room_id, self.host_id, self.room_type, self.country,
                self.city, self.neighborhood, self.address, self.reviews,
                self.overall_satisfaction, self.accommodates, self.bedrooms,
                self.bathrooms, self.price, self.deleted, self.minstay,
                self.latitude, self.longitude, self.survey_id,
                self.coworker_hosted, self.extra_host_languages, self.name,
                self.property_type, self.currency, self.rate_type,
                self.sublocality, self.route, self.avg_rating,
                 self.is_superhost,
                self.max_nights, self.pictures, self.bathroom,
                self.location_id
                )
            cur.execute(sql, insert_args)
            cur.close()
            conn.commit()
            logger.debug("Room " + str(self.room_id) + ": inserted")
            logger.debug("(lat, long) = ({lat:+.5f}, {lng:+.5f})".format(lat=self.latitude, lng=self.longitude))
        except psycopg2.IntegrityError:
            # logger.info("Room " + str(self.room_id) + ": insert failed")
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
                update room
                set host_id = %s, room_type = %s,
                    country = %s, city = %s, neighborhood = %s,
                    address = %s, reviews = %s, overall_satisfaction = %s,
                    accommodates = %s, bedrooms = %s, bathrooms = %s,
                    price = %s, deleted = %s, last_modified = now()::timestamp,
                    minstay = %s, latitude = %s, longitude = %s,
                    coworker_hosted = %s, extra_host_languages = %s, name = %s,
                    property_type = %s, currency = %s, rate_type = %s, pictures = %s
                where room_id = %s
                and survey_id = %s"""
            update_args = (
                self.host_id, self.room_type,
                self.country, self.city, self.neighborhood,
                self.address, self.reviews, self.overall_satisfaction,
                self.accommodates, self.bedrooms, self.bathrooms,
                self.price, self.deleted,
                self.minstay, self.latitude,
                self.longitude,
                self.coworker_hosted, self.extra_host_languages, self.name,
                self.property_type, self.currency, self.rate_type, self.pictures,
                self.room_id,
                self.survey_id,
                )
            logger.debug("Executing...")
            cur.execute(sql, update_args)
            rowcount = cur.rowcount
            logger.debug("Closing...")
            cur.close()
            conn.commit()
            logger.info("Room " + str(self.room_id) +
                        ": updated (" + str(rowcount) + ")")
            return rowcount
        except:
            # may want to handle connection close errors
            logger.warning("Exception in __update: raising")
            raise

    def __get_reviews(self, tree):
        try:
            # 2020-05-09
            x = tree.xpath("//*[@id='reviews']/div/div/section/div[1]/div/div[2]/div[1]/div/div/div/div/div/div[3]/span[1]/text()")
            if x is not None:
                self.reviews = x[0]
                return True

            # 2016-04-10
            s = tree.xpath("//meta[@id='_bootstrap-listing']/@content")
            # 2015-10-02
            temp2 = tree.xpath(
                "//div[@class='___iso-state___p3summarybundlejs']"
                "/@data-state"
                )
            if s is not None:
                j = json.loads(s[0])
                self.reviews = \
                    j["listing"]["review_details_interface"]["review_count"]
            elif len(temp2) == 1:
                summary = json.loads(temp2[0])
                self.reviews = summary["visibleReviewCount"]
            elif len(temp2) == 0:
                temp = tree.xpath(
                    "//div[@id='room']/div[@id='reviews']//h4/text()")
                if len(temp) > 0:
                    self.reviews = temp[0].strip()
                    self.reviews = str(self.reviews).split('+')[0]
                    self.reviews = str(self.reviews).split(' ')[0].strip()
                if self.reviews == "No":
                    self.reviews = 0
            else:
                # try old page match
                temp = tree.xpath(
                    "//span[@itemprop='reviewCount']/text()"
                    )
                if len(temp) > 0:
                    self.reviews = temp[0]
            if self.reviews is not None:
                self.reviews = int(self.reviews)
        except IndexError:
            return
        except Exception as e:
            logger.exception(e)
            self.reviews = None

    def get_location(self):
        location = Location(self.latitude, self.longitude) # initialize a location with coordinates
        location.reverse_geocode(self.config) # find atributes for location with google api key
        
        if location.get_country() != "N/A":
            self.country = location.get_country()
        if location.get_level2() != "N/A":
            self.city = location.get_level2()
        if location.get_neighborhood() != "N/A":
            self.neighborhood = location.get_neighborhood()
        if location.get_sublocality() != "N/A":
            self.sublocality = location.get_sublocality()
        if location.get_route() != "N/A":
            self.route = location.get_route()

        location.insert_in_search_area(self.config)

    def get_comments(self):
        """ Get the reviews properties from the web site """
        try:
            # initialization
            logger.info("-" * 70)
            logger.info("Room " + str(self.room_id) +
                        ": getting from Airbnb web site")
            room_url = self.config.URL_ROOM_ROOT + str(self.room_id)
            response = airbnb_ws.ws_request_with_repeats(self.config, room_url)
            if response is not None:
                page = response.text
                tree = html.fromstring(page)
                if self.__get_reviews(tree) == False:
                    return False
                elif self.reviews == 0:
                    logger.info("No reviews to find")
                    return True
            else:
                logger.info("Room %s: not found", self.room_id)
                return False
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            logger.exception("Room " + str(self.room_id) +
                             ": failed to retrieve from web site.")
            logger.error("Exception: " + str(type(ex)))
            raise

    def get_comments(self, host_id, response):
        """ Get the reviews properties from the web site """
        try:
            # initialization
            logger.info("-" * 70)
            logger.info("Host " + str(host_id) +
                        ": getting from Airbnb web site")
            room_url = "airbnb.com.br/users/show/" + str(host_id)
            
            if response is not None:
                page = response.text
                tree = html.fromstring(page)
                if self.__get_reviews(tree) == False:
                    return False
                elif self.reviews == 0:
                    logger.info("No reviews to find")
                    return True
                else:
                    return self.__get_reviews_text(tree)
            else:
                logger.info("Room %s: not found", self.room_id)
                return False
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            logger.exception("Room " + str(self.room_id) +
                             ": failed to retrieve from web site.")
            logger.error("Exception: " + str(type(ex)))
            raise