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
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from geopy import distance
import datetime as dt

from airbnb import db_add_survey
from airbnb_geocoding import reverse_geocode_coordinates_and_insert
from general_config import ABConfig
import utils
from utils import prepare_driver

DOMAIN = 'https://www.booking.com'
logger = logging.getLogger()


class BListing():
	"""
	# BListing represents an Airbnb room_id, as captured at a moment in time.
	# room_id, survey_id is the primary key.
	"""

	def __init__(self, config, driver, url, survey_id, checkin_date, checkout_date):
		self.config = config

		self.room_id = None
		self.room_name = None
		self.accommodates = None
		self.price = None
		self.bedtype = None
		self.latitude = None
		self.longitude = None
		self.overall_satisfaction = None
		self.comodities = None
		self.hotel_name = None
		self.localized_address = None
		self.property_type = None
		self.reviews = None
		self.survey_id = survey_id
		self.checkin_date = checkin_date
		self.checkout_date = checkout_date

		self.start_date = None
		self.finish_date = None
		self.location_id = None

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
					if (self.config.FLAGS_INSERT_IN_LOCATION): self.location_id = reverse_geocode_coordinates_and_insert(self.config, self.latitude, self.longitude)
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
				insert into booking_room (
					room_id, room_name, hotel_name, address, comodities,
					overall_satisfaction, property_type, bed_type, accommodates,
					price, latitude, longitude, reviews, survey_id,
					checkin_date, checkout_date, location_id
					)
				values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
			insert_args = (
				self.room_id, self.hotel_name, self.room_name, self.localized_address, self.comodities,
				self.overall_satisfaction, self.property_type, self.bedtype, self.accomodates,
				self.price, self.latitude, self.longitude, self.reviews, self.survey_id, self.checkin_date, self.checkout_date,
				self.location_id
				)

			cur.execute(sql, insert_args)
			cur.close()
			conn.commit()
			logger.debug("Room " + str(self.room_name) + ": inserted")
			logger.debug("(lat, long) = (%s, %s)".format(
					lat=self.latitude, lng=self.longitude))
		except psycopg2.IntegrityError:
			logger.info("Room " + str(self.room_name) + ": insert failed")
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
				update booking_room set
				hotel_id = %s, name = %s, room_name = %s, overall_satisfaction = %s,
				address = %s, popular_facilities = %s, reviews = %s,
				property_type = %s, bed_type = %s, accommodates = %s,
				children_accommodates = %s, price = %s, latitude = %s,
				longitude = %s, city = %s, state = %s, country = %s,
				currency = %s, comodities = %s,
				images = %s,
				last_modified = now()::timestamp
				where room_id = %s"""
			update_args = (
				self.hotel_id, self.name, self.room_name, self.overall_satisfaction,
				self.address, self.popular_facilities, self.reviews,
				self.property_type, self.bed_type, self.adults_accommodates,
				self.children_accommodates, self.price,
				self.latitude, self.longitude,
				self.city, self.state, self.country, self.currency,
				self.comodities, self.room_id, self.images
				)
			logger.debug("Executing...")
			cur.execute(sql, update_args)
			rowcount = cur.rowcount
			logger.debug("Closing...")
			cur.close()
			conn.commit()
			if rowcount > 0:
				logger.debug("Room " + str(self.room_id) +
						": updated (" + str(rowcount) + ")")

			return rowcount
		except:
			# may want to handle connection close errors
			logger.debug("Exception in updating")
			logger.warning("Exception in __update: raising")
			raise

	# ENCONTRANDO DADOS NA NOVA VERSÃO
	def find_hotel_name(self, driver):
		try:
				element = driver.find_element(By.CSS_SELECTOR, '.pp-header__title')
				self.hotel_name = element.text
		except selenium.common.exceptions.NoSuchElementException:
				raise

	def find_localized_address(self, driver):
		try:
				element = driver.find_element(By.CSS_SELECTOR, '.js-hp_address_subtitle')
				self.localized_address = element.text
		except selenium.common.exceptions.NoSuchElementException:
				raise

	def find_room_informations(self, driver):
		try:
				table_rows = driver.find_elements(By.XPATH, "//*[@id='hprt-table']/tbody/tr")
				for row in table_rows:
					try:
						room_name = row.find_element(By.CLASS_NAME, 'hprt-roomtype-link')
						self.room_name = room_name.text
						self.room_id = room_name.get_attribute("data-room-id")

						bed_type = row.find_element(By.CSS_SELECTOR, '.hprt-roomtype-bed')
						self.bedtype = bed_type.text
					except selenium.common.exceptions.NoSuchElementException:
						pass
					
					accomodates = row.find_elements(By.CSS_SELECTOR, ".bicon-occupancy")
					self.accomodates = len(accomodates)

					# preco
					price = row.find_element(By.CSS_SELECTOR, '.bui-price-display__value')
					self.price = price.text.split('R$ ')[1]
		except selenium.common.exceptions.NoSuchElementException:
				raise

	def find_latlng(self, driver): # ok
		try:
				element = driver.find_element(By.ID, 'hotel_header')
				coordinates = element.get_attribute('data-atlas-latlng').split(',')
				self.latitude = coordinates[0]
				self.longitude = coordinates[1]
		except selenium.common.exceptions.NoSuchElementException:
				raise
	
	def find_property_type(self, driver):
		try:
				element = driver.find_element(By.XPATH, '//*[@data-testid="property-type-badge"]')
				self.property_type = element.text
		except selenium.common.exceptions.NoSuchElementException:
				raise
		
	def find_overall_classification(self, driver):
		try:
				element = driver.find_element(By.CSS_SELECTOR, 'div.b5cd09854e.d10a6220b4')
				if ',' in element.text:
					self.overall_satisfaction = float(element.text.replace(',', '.'))
				else:
					if len(element.text) > 0:
						self.overall_satisfaction = float(element.text)
		except selenium.common.exceptions.NoSuchElementException:
				raise
		except:
				raise

	def find_principal_comodities(self, driver):
		try:
				element = driver.find_elements(By.CSS_SELECTOR, 'div.a815ec762e.ab06168e66')
				comodities = []
				for comodity in element:
					comodities.append(comodity.text)

				self.comodities = comodities
		except selenium.common.exceptions.NoSuchElementException:
				raise

	def find_reviews_quantity(self, driver):
		try:
				element = driver.find_element(By.XPATH, '//*[@rel="reviews"]')
				if element.text is not None:
					r = element.text.split('Avaliações de hóspedes (')[1].split(')')[0]
					self.reviews = float(r)
		except selenium.common.exceptions.NoSuchElementException:
				raise
		except:
				raise

def fill_empty_routes(config):
	try:
		rowcount = 0
		conn = config.connect()
		cur = conn.cursor()
		logger.debug("Updating...")
		sql = """UPDATE booking_room set route = split_part(address, ',', 1)
				where route is null"""
		logger.debug("Executing...")
		cur.execute(sql)
		rowcount = cur.rowcount
		logger.debug("Closing...")
		cur.close()
		conn.commit()
		logger.debug(str(rowcount) + " rooms updated")

	except:
		# may want to handle connection close errors
		logger.debug("Exception in updating")
		logger.warning("Exception in __update: raising")
		raise

def update_cities(config, city):
	try:
		conn = config.connect()
		cur = conn.cursor()

		sql = """SELECT distinct(room_id), route, sublocality, city, state, country from booking_room
				where route is not null
				
				group by room_id, route, sublocality, city, state, country
				order by room_id""" # os q precisa atualizar
		cur.execute(sql)
		results = cur.fetchall()
		logger.debug(str(cur.rowcount) + " rooms to update")

		i = 0 
		for result in results:     
			room_id = result[0]
			route = result[1]
			sublocality = result[2]
			city = result[3]
			state=result[4]
			country = result[5]

			sql = """UPDATE booking_room set route = %s,
					sublocality = %s,
					city = %s, state=%s, country = %s
					where room_id = %s"""
			update_args = ( route, sublocality, city, state, country, room_id )
			cur.execute(sql, update_args)
			conn.commit()

			logger.debug(cur.rowcount, "room(s) ", room_id," updated for ", sublocality)
				
	except:
		raise

def update_routes(config, city):
	try:
		conn = config.connect()
		cur = conn.cursor()

		sql = """SELECT distinct(room_id), latitude, longitude from booking_room
				where route is null and
				( sublocality is null or sublocality = '1392' or
				sublocality = '162' or sublocality = '302'
				or sublocality = '')
				order by room_id""" # os q precisa atualizar
		cur.execute(sql)
		routes = cur.fetchall()
		logger.debug(str(cur.rowcount) + " routes to update")

		sql = """SELECT distinct(room_id), latitude, longitude, sublocality from booking_room
				where route is not null and ( sublocality is not null and sublocality <> '')
				and sublocality <> '1392' and sublocality <> '162' and sublocality <> '302'
				order by sublocality desc""" # nenhum dos 2 é nulo
		cur.execute(sql)
		results = cur.fetchall()
		
		for route in routes:
			r_id = route[0]
			latitude = route[1]
			longitude = route[2]

			for result in results: 
				room_id = result[0]
				lat = result[1]
				lng = result[2]
				sublocality = result[3]

				if utils.is_inside(latitude, longitude, lat, lng):
					sql = """UPDATE booking_room set sublocality = %s where room_id = %s"""
					update_args = ( sublocality, r_id )
					cur.execute(sql, update_args)
					conn.commit()

					logger.debug("Room ", r_id," updated for ", sublocality)
					break
				
	except:
		raise

def add_routes_area_by_bounding_box(config, city):
	try:
		conn = config.connect()
		cur = conn.cursor()

		sql = """SELECT distinct(route) from booking_room
				where city = %s""" # os q precisa atualizar
		select_args = (city,)
		cur.execute(sql, select_args)
		results = cur.fetchall()
		logger.debug(str(cur.rowcount) + " rooms finded")

		for result in results:     
			route_name = str(result[0]) + ', ' + city
			bounding_box = BoundingBox.from_google(config, route_name)
			if bounding_box != None:
				bounding_box.add_search_area(config, route_name)                
	except:
		raise

def search_booking_rooms(config, area, start_date, finish_date, survey_id, search_reviews=False):
	city = area.split(',')[0]

	checkin_date = start_date
	if checkin_date is None:
		checkin_date = dt.date.today() + dt.timedelta(days=15)

	checkout_date = finish_date
	if checkout_date is None:
		checkout_date = dt.date.today() + dt.timedelta(days=16)

	url = "https://www.booking.com/searchresults.pt-br.html?ss={}&ssne={}&ssne_untouched={}&checkin={}&checkout={}".format(
					city, city, city, checkin_date, checkout_date)
	driver = prepare_driver(url)

	wait = WebDriverWait(driver, timeout=10).until(
		EC.presence_of_all_elements_located(
			(By.XPATH, '//*[@data-testid="property-card"]')))
	# FIND ALL PAGES
	all_pages = driver.find_elements(By.CLASS_NAME, 'f32a99c8d1')
	for page in all_pages[1:len(all_pages):1]:
		for i in range(config.ATTEMPTS_TO_FIND_PAGE):
			try:
				logger.debug("Attempt " + str(i+1) + " to find page")
				property_cards = driver.find_elements(By.XPATH, '//*[@data-testid="property-card"]//*[@data-testid="title-link"]')
				urls = []
				for property_card in property_cards:
					urls.append(property_card.get_attribute("href"))

				for url in urls:
					hotel_page = prepare_driver(url)
					
					listing = BListing(config, driver, url, survey_id, checkin_date, checkout_date)
					
					listing.find_latlng(hotel_page)
					listing.find_principal_comodities(hotel_page)
					listing.find_hotel_name(hotel_page)
					listing.find_localized_address(hotel_page)
					listing.find_property_type(hotel_page)
					listing.find_reviews_quantity(hotel_page)
					listing.find_overall_classification(hotel_page)
					
					listing.find_room_informations(hotel_page) # needs to be the last call
					listing.save(listing.config.FLAGS_INSERT_REPLACE)
					
				page.click()
				break
			except selenium.common.exceptions.TimeoutException:
				continue

	driver.quit()
	

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
	parser.add_argument("-sr", "--search_reviews",
						action="store_true", default=False,
						help="""search only for reviews""") # para implementar
	parser.add_argument('-sc', '--city',
						 metavar='city_name', type=str,
						 help="""search by a city
						 """)
	parser.add_argument('-sd', '--start_date',
						 metavar='start_date', type=str,
						 help="""start date of travel
						 """)
	parser.add_argument('-fd', '--finish_date',
						 metavar='finish_date', type=str,
						 help="""finish date of travel
						 """)
	parser.add_argument("-urbb", "--update_routes_with_bounding_box",
												metavar="city_name", type=str,
												help="""update geolocation based on Google's API""")
	
	# Only one argument!
	group = parser.add_mutually_exclusive_group()
	group.add_argument('-ur', '--update_routes',
						 metavar='city_name', type=str,
						 help="""update routes from rooms""") # by victor

	args = parser.parse_args()
	return (parser, args)

def main():
	(parser, args) = parse_args()
	logging.basicConfig(format='%(levelname)-8s%(message)s')
	config = ABConfig(args)
	
	try:
		if args.city:
			# create/insert in database search area with coordinates
			bounding_box = BoundingBox.from_geopy(config, args.city)
			bounding_box.add_search_area(config, args.city)

			# initialize new survey
			survey_id = db_add_survey(config, args.city)

			search(config, args.city, args.start_date, args.finish_date,
					args.search_reviews, survey_id)
		elif args.update_routes_with_database:
			fill_empty_routes(config)
			update_cities(config, args.update_routes)
			update_routes(config, args.update_routes)
			logger.debug("Data updated")
	except (SystemExit, KeyboardInterrupt):
		logger.debug("Interrupted execution")
		exit(0)
	except Exception:
		logging.exception("Top level exception handler: quitting.")
		exit(0)

if __name__ == "__main__":
	main()