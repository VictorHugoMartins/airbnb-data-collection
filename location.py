import re
import bs4
import time
import json
import string
import logging
import requests
import argparse
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import selenium
import psycopg2
from airbnb_geocoding import Location
from airbnb_geocoding import BoundingBox
from lxml import html
from selenium import webdriver
from general_config import ABConfig
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from geopy import distance
import datetime as dt
from utils import select_command
from airbnb import db_add_survey

class Localization():
	"""
	# BListing represents an Airbnb room_id, as captured at a moment in time.
	# room_id, survey_id is the primary key.
	"""

	def __init__(self, config):
		self.config = config

		self.route = None 
		self.sublocality = None 
		self.city = None
		self.state = None
		self.country = None

	def save(self, insert_replace_flag):
		"""
		Save a listing in the database. Delegates to lower-level methods
		to do the actual database operations.
		Return values:
			True: listing is saved in the database
			False: listing already existed
		"""
		self.__insert()
		try:
			rowcount = -1

			'''if insert_replace_flag == self.config.FLAGS_INSERT_REPLACE:
				rowcount = self.__update()'''
			if (rowcount == 0 or
					insert_replace_flag == self.config.FLAGS_INSERT_NO_REPLACE):
				try:
					# self.get_address()
					self.__insert()
					return True
				except psycopg2.IntegrityError:
					logger.debug("Room " + str(self.room_name) + ": already collected")
					return False
		except psycopg2.OperationalError:
			# connection closed
			logger.error("Operational error (connection closed): resuming")
			del (self.config.connection)
		except psycopg2.DatabaseError as de:
			self.config.connection.conn.rollback()
			logger.erro(psycopg2.errorcodes.lookup(de.pgcode[:2]))
			logger.error("Database error: resuming")
			del (self.config.connection)
		except psycopg2.InterfaceError:
			# connection closed
			logger.error("Interface error: resuming")
			del (self.config.connection)
		except psycopg2.Error as pge:
			# database error: rollback operations and resume
			self.config.connection.conn.rollback()
			logger.error("Database error: " + str(self.room_id))
			logger.error("Diagnostics " + pge.diag.message_primary)
			del (self.config.connection)
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
		try:
			logger.debug("Values: ")
			logger.debug("\troom: {}".format(self.room_id))
			conn = self.config.connect()
			cur = conn.cursor()
			sql = """
				insert into location (
					route, sublocality, city, state, country
					)
				values (%s, %s, %s, %s, %s)"""
			insert_args = (
				self.route, self.sublocality, self.city, self.state, self.country
				)

			cur.execute(sql, insert_args)
			cur.close()
			conn.commit()
			logger.debug("Location %s, %s inserted".format(
					lat=self.route, lng=self.sublocality))
		except psycopg2.IntegrityError:
			logger.info("Location %s, %s: insert failed".format(
					lat=self.route, lng=self.sublocality))
			conn.rollback()
			cur.close()
			raise
		except:
			conn.rollback()
			raise

def get_coordinates_list(config, platform="Airbnb", survey_id=1):
		return select_command(config,
						sql_script="""SELECT DISTINCT latitude, longitude from room where survey_id >= %s""" if platform == "Airbnb" else """SELECT DISTINCT latitude, longitude from booking_room where survey_id >= %s""",
						params=((survey_id,)),
						initial_message="Selecting coordinates list from " + platform,
						failure_message="Failed to search coordinates list")
		
def identify_and_insert_locations(config, platform, survey_id):
	coordinates_list = get_coordinates_list(config, platform, survey_id)
	for coordinate in coordinates_list:
			lat = coordinate[0]
			lng = coordinate[1]
			if ( lat is not None) and (lng is not None):
					location = Location(config, str(lat), str(lng)) 
					location.reverse_geocode(config)
					location.insert()

def parse_args():
	"""
	Read and parse command-line arguments
	"""
	parser = argparse.ArgumentParser(
		description='Manage a database of Booking listings.',
		usage='%(prog)s [options]')
	parser.add_argument("-v", "--verbose",
						action="store_true", default=False,
						help="""write verbose (debug) output to the log file""")
	parser.add_argument("-c", "--config_file",
						metavar="config_file", action="store", default=None,
						help="""explicitly set configuration file, instead of
						using the default <username>.config""")
	parser.add_argument('-pt', '--platform',
						 metavar='platform', type=str,
						 help="""search upon a platform
						 """)

	args = parser.parse_args()
	return (parser, args)

def main():
	(parser, args) = parse_args()
	logging.basicConfig(format='%(levelname)-8s%(message)s')
	config = ABConfig(args)
	if (args.platform):
		identify_and_insert_locations(config, args.platform, 1)


if __name__ == "__main__":
	main()