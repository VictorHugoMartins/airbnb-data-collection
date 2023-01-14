#!/usr/bin/python3
# ============================================================================
# Victor Martins, 2020.
#
# An ABReview represents and individual Airbnb review
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

logger = logging.getLogger()


class ABReview():

    def __init__(self, config, review_id):
        self.config = config
        self.review_id = review_id

        self.room_id = None
        self.comment = None
        self.language = None
        self.create_at = None
        self.response = None
        self.localized_date = None
        self.reviewer_name = None
        self.reviewer_id = None
        self.rating = None
        self.deleted = None
        self.role = None
        logger.setLevel(config.log_level)

    def get_attributes(self, config, path, room_id):
        self.config = config
        self.room_id = room_id
        self.review_id = self.__get_review_id(path)
        self.comment = self.__get_comment(path)
        self.language = self.__get_language(path)
        self.create_at = self.__get_created_at(path)
        self.response = self.__get_response(path)
        self.localized_date = self.__get_localized_date(path)
        self.reviewer_name = self.__get_reviewer_name(path)
        self.reviewer_id = self.__get_reviewer_id(path)
        self.rating = self.__get_rating(path)
        self.deleted = self.__get_deleted(path)
        self.role = self.__get_role(path)

        logger.setLevel(config.log_level)

        self.save(self.config.FLAGS_INSERT_REPLACE)

    def save(self, insert_replace_flag):
        try:
            rowcount = 0
            
            if insert_replace_flag == self.config.FLAGS_INSERT_REPLACE:
                rowcount = self.__update()
            if (rowcount == 0 or
                    insert_replace_flag == self.config.FLAGS_INSERT_NO_REPLACE):
                try:
                    self.__insert()
                    return True
                except psycopg2.IntegrityError:
                    logger.debug("Review " + str(self.review_id) + ": already collected")
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
            logger.error("Database error: " + str(self.review_id))
            logger.error("Diagnostics " + pge.diag.message_primary)
            del(self.config.connection)
        except (KeyboardInterrupt, SystemExit):
            raise
        except UnicodeEncodeError as uee:
            logger.error("UnicodeEncodeError Exception at " +
                         str(uee.object[uee.start:uee.end]))
            raise
        except ValueError:
            logger.error("ValueError for review_id = " + str(self.review_id))
        except AttributeError:
            logger.error("AttributeError")
            raise
        except Exception:
            self.config.connection.rollback()
            logger.error("Exception saving review")
            raise

    def __insert(self):
        """ Insert a review into the database. Raise an error if it fails """
        try:
            logger.debug("Values: ")
            logger.debug("\treview_id: {}".format(self.review_id))
            logger.debug("\troom_id: {}".format(self.room_id))
            conn = self.config.connect()
            cur = conn.cursor()
            sql = """
                INSERT into reviews(id, room_id, comment, language,
                    create_at, response, localized_data,
                    reviewer_name, reviewer_id, rating, deleted,
                    role)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            insert_args = (
                self.review_id, self.room_id, self.comment, self.language,
                self.create_at, self.response, self.localized_date,
                self.reviewer_name, self.reviewer_id, self.rating, self.deleted,
                self.role
                )
            cur.execute(sql, insert_args)
            cur.close()
            conn.commit()
            logger.debug("Review " + str(self.review_id) + ": inserted")
        except psycopg2.IntegrityError:
            logger.info("Review " + str(self.review_id) + ": insert failed")
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
                update reviews
                set room_id = %s, comment = %s, language = %s,
                    create_at = %s, response = %s, localized_data = %s,
                    reviewer_name = %s, reviewer_id = %s, rating = %s, deleted = %s, role = %s,
                    last_modified = now()::timestamp
                where id = %s"""

            update_args = (
                self.room_id, self.comment, self.language,
                self.create_at, self.response, self.localized_date, self.reviewer_name,
                self.reviewer_id, self.rating, self.deleted, self.role, self.review_id
                )
            logger.debug("Executing...")
            cur.execute(sql, update_args)
            rowcount = cur.rowcount
            logger.debug("Closing...")
            cur.close()
            conn.commit()
            logger.info("Review " + str(self.review_id) +
                        ": updated (" + str(rowcount) + ")")
            return rowcount
        except:
            # may want to handle connection close errors
            logger.warning("Exception in __update: raising")
            raise

    def __get_comment(self, path):
        try:
            return str(path["comments"])
        except KeyError:
            return None

    def __get_language(self, path):
        try:
            return path["language"]
        except KeyError:
            return None

    def __get_review_id(self, path):
        try:
            return path["id"]
        except KeyError:
            return None

    def __get_created_at(self, path):
        try:
            return path["created_at"]
        except KeyError:
            return None

    def __get_deleted(self, path):
        try:
            return path["reviewee"]["deleted"]
        except KeyError:
            return None

    def __get_response(self, path):
        try:
            return path["response"]
        except KeyError:
            return None

    def __get_localized_date(self, path):
        try:
            return path["localized_date"]
        except KeyError:
            return None

    def __get_reviewer_name(self, path):
        try:
            return path["reviewer"]["first_name"]
        except KeyError:
            return None

    def __get_rating(self, path):
        try:
            return path["rating"]
        except KeyError:
            return None

    def __get_reviewer_id(self, path):
        try:
            return path["reviewer"]["id"]
        except KeyError:
            return None

    def __get_role(self, path):
        try:
            return path["role"]
        except KeyError:
            return 'guest'