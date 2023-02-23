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
from airbnb_config import ABConfig
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from booking_reviews import BReview
from geopy import distance
import datetime as dt
import utils


SCRIPT_VERSION_NUMBER = "4.0"
DOMAIN = 'https://www.booking.com'
logger = logging.getLogger()


class BListing():
	"""
	# BListing represents an Airbnb room_id, as captured at a moment in time.
	# room_id, survey_id is the primary key.
	"""

	def __init__(self, config, driver, url):
		self.config = config

		room_id = None
		room_name = None
		accommodates = None
		price = None
		bedtype = None
		lat = None
		lng = None
		overall_satisfaction = None
		comodities = None
		hotel_name = None
		localized_address = None
		property_type = None

		# time.sleep(5)
		# try:
		# 	self.hotel_id = self.get_hotel_id(driver)
		# except selenium.common.exceptions.NoSuchElementException:
		# 	self.hotel_id = None
		# self.popular_facilities = self.get_popular_facilities(driver)
		# self.reviews = self.get_reviews(driver)
		# self.images = self.get_images(driver)

		# (self.latitude, self.longitude) = self.get_lat_lng(driver)
		# (self.city, self.state, self.country,
		#  self.currency) = self.get_address_elements(url)

		# self.qtd_rooms = None
		# self.bed_type = None
		# self.adults_accommodates = None
		# self.children_accommodates = None
		# self.bedroom_type = None

		self.start_date = None
		self.finish_date = None

	def get_address(self, driver):
		# Get the accommodation address
		try:
			return driver.find_element_by_id('showMap2')\
			.find_element_by_class_name('hp_address_subtitle').text
		except:
			return None

	def get_overall_satisfaction(self, driver):
		# Get the accommodation overall_satisfaction
		try:
			return driver.find_element(By.XPATH, '/html/body/div[5]/div/div[3]/div[2]/div[2]/div[13]/div[1]/a/div/div[1]').text.\
					replace(',', '.')
		except:
			try:
				return driver.find_element_by_class_name(
					'bui-review-score--end').find_element_by_class_name(
					'bui-review-score__badge').text.replace(',', '.')
			except:
				return None

	def get_property_type(self, driver):
		# Get the accommodation type
		try:
			return driver.find_elements_by_xpath('//*[@id="hp_hotel_name"]/span')[0].text
		except:
			return None

	def get_name(self, driver):
		try:
			return driver.find_element_by_id('hp_hotel_name')\
			.text.strip(str(self.property_type))
		except:
			return None

	def get_hotel_id(self, driver):
		try:
			return int(driver.find_element(By.XPATH, '//*[@id="hprt-form"]/input[1]').
							get_attribute("value"))
		except:
			return int(driver.find_elements_by_xpath('//*[@id="hp_facilities_box"]/div[6]/div[1]/input')[0].
							get_attribute("value"))

	def get_reviews(self, driver):
		# Get the accommodation reviews count
		try:
			x = driver.find_elements_by_xpath('//*[@id="show_reviews_tab"]/span')
			try:
				return int(x[0].text.split('(')[1].split(')')[0])
			except:
				return driver.find_elements_by_xpath('//*[@id="left"]/div[11]/div[1]/a/div/div[2]/div[2]').split(' comentários')[0]
		except:
			return None

	def get_address_elements(self, accommodation_url):
		response = requests.get(accommodation_url)
		page = response.text
		tree = html.fromstring(page)
		x = tree.xpath('//*[@id="b2hotelPage"]/script[1]/text()')

		try:
			self.name = x[0].split("hotel_name: '")[1].split("'")[0]
			city = x[0].split("city_name: '")[1].split("'")[0]
			state = x[0].split("region_name: '")[1].split("'")[0]
			country = x[0].split("country_name: '")[1].split("'")[0]
			currency = x[0].split("currency: '")[1].split("'")[0]

			return (city, state, country, currency)
		except:
			return (None, None, None, None)

		return (city, state, country, currency)

	def get_popular_facilities(self, driver):
		try:
			x = []
			# Get the most popular facilities

			facilities = driver.find_element_by_class_name(
					'hp_desc_important_facilities')

			for facility in facilities.find_elements_by_class_name('important_facility'):
				x.append(facility.text)
			return x
		except:
			return None

	def get_rooms_id(self, driver):  # unused
		rooms_id = []
		x = driver.find_elements_by_xpath(
				'//*[@id="maxotel_rooms"]/tbody/tr/td[@class="ftd roomType"]/div')
		n_rows = len(x)

		logger.debug("len de rooms id", n_rows)

		if (n_rows == 0):  # in case of search with checkin-checkout date
			x = driver.find_elements_by_xpath('//*[@class="hprt-roomtype-link"]')
			n_rows = len(x)

			for j in range(n_rows):
				try:
					rooms_id.append(x[j].get_attribute("id").split('room_type_id_')[1])
				except:
					logger.debug("Room id not finded")
					rooms_id.append(None)
		else:
			for j in range(n_rows):
				try:
					rooms_id.append(x[j].get_attribute("id"))
				except:
					logger.debug("Room id not finded")

		return rooms_id

	def get_facilities(self, driver):  # unused
		facilities = []
		y = driver.find_elements_by_class_name('hprt-facilities-block')
		tamanho = len(y)
		for x in y:
			x = x.find_elements_by_class_name('hprt-facilities-facility')
			n_rows = len(x)
			linha = []
			for j in range(n_rows):
				try:
					linha.append(x[j].get_attribute("data-name-en"))
				except:
					linha.append(None)
			facilities.append(linha)

		return facilities

	def get_beds_type(self, driver):  # unused
		room_name = []
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr'
					'td[@class="ftd roomType"]/div/div[@class="room-info"]/a')
		n_rows = len(x)

		i = 0
		if (n_rows == 0):
			x = driver.find_elements_by_xpath('//*[@class="bedroom_bed_type"]/span')
			n_rows = len(x)
			for j in range(n_rows):
				try:
					room_name.append(x[j].text)
				except:
					logger.debug("Bed type not finded")
					room_name.append(None)
		else:
			for j in range(n_rows):
				logger.debug(j, "veio no else")
				try:
					room_name.append(x[j].get_attribute("data-room-name-en"))
				except:
					logger.debug("Bed type not finded")
					room_name.append(None)
		return room_name

	def get_room_name(self, driver):  # unused
		beds_type = []
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/'
					'td[@class="ftd roomType"]/div/div[@class="room-info"]/div/'
					'/ul/li/span')
		n_rows = len(x)

		if (n_rows == 0):
			y = driver.find_elements_by_xpath('//*[@class="hprt-roomtype-icon-link "]')
			n_rows = len(y)
			for j in range(n_rows):
				try:
					beds_type.append(y[j].text)
				except:
					beds_type.append(None)
					logger.debug("Bed not finded")
		else:
			for j in range(n_rows):
				try:
					beds_type.append(x[j].text)
				except:
					logger.debug("Bed not finded")
		return beds_type

	def get_price(self, driver):  # unused
		prices = []
		x = driver.find_elements_by_xpath(
				'//*[@class="bui-price-display__value prco-text-nowrap-helper prco-font16-helper"]')
		n_rows = len(x)

		for elem in x:
			try:
				prices.append(elem.text.split('R$ ')[1])
			except:
				prices.append(None)
				logger.debug("Price not finded")

		return prices

	def get_accommodates(self, driver):  # unused
		# Get the rooms person capacity
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/td')
		n_rows = len(x)
		accommodates = []
		if (n_rows == 0):
			x = driver.find_elements_by_xpath('//*[@id="hprt-table"]/tbody/tr/td[2]')
			n_rows = len(x)
			for elem in x:
				try:
					accommodates.append(elem.find_element_by_class_name(
							'bui-u-sr-only').text.split('Máx. pessoas: ')[1])
				except:
					accommodates.append(None)
		else:
			for j in range(0, n_rows, 4):
				try:
					s = x[j].find_element_by_class_name('bui-u-sr-only').text.split(': ')
					if len(s) == 3:
						accommodates.append(int(s[1].split('.')[0]))
					else:
						accommodates.append(int(s[1]))
				except:
					accommodates.append(None)

		return accommodates

	def get_children_accommodates(self, driver):  # unused
		# Get the rooms person capacity
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/td')

		n_rows = len(x)
		accommodates = []

		if (n_rows == 0):
			return None
		for j in range(0, n_rows, 4):
			try:
				s = x[j].find_element_by_class_name('bui-u-sr-only').text.split(': ')
				if len(s) == 3:
					accommodates.append(s[2])
				else:
					accommodates.append('0')
			except:
				logger.debug("Accomodate not finded")

		return accommodates

	def get_lat_lng(self, driver):
		try:
			x = driver.find_element(By.XPATH, '//*[@id="hotel_surroundings"]')
			l = x.get_attribute("data-atlas-latlng").split(',')
			latitude = l[0]
			longitude = l[1]
			return (latitude, longitude)
		except:
			return (None, None)

	def get_images(self, driver):
		m_images = []
		images = driver.find_elements_by_xpath(
				'//div[@class="b_nha_hotel_small_images hp_thumbgallery_with_counter"]/a')
		tamanho = len(images)
		for elem in images:
			linha = []
			linha.append(elem.get_attribute("href"))
			linha.append(elem.get_attribute("aria-label"))
			m_images.append(linha)
		return m_images

	def get_reviews_text(self, driver):
		try:

			driver.find_element(By.XPATH, '//*[@id="show_reviews_tab"]').click()
			time.sleep(5)

			reviews = driver.find_elements_by_class_name('review_list_new_item_block')
			size = len(reviews)
			if size == 0:
				logger.debug("Unable to find reviews")

			n_review = 1
			n_page = 1

			new_page = True
			review_pages = []
			while new_page:
				next_page = driver.find_elements_by_class_name('bui-pagination__link')
				new_page = False
				for p in next_page:
					if p.text.split('\n')[0] not in review_pages:
						n_page = n_page + 1
						# append(p.text.split(\n)[0]) ??? ai tem q verificar se vai 1 vez em cada 1
						review_pages.append(p.text.split('\n')[0])
						new_page = True
						p.click()
						time.sleep(5)
						reviews = driver.find_elements_by_class_name(
								'review_list_new_item_block')
						for review in reviews:  # get the reviews
							r = BReview(self.config, review, self.hotel_id)
							r.save(self.config.FLAGS_INSERT_REPLACE)
							n_review = n_review + 1
						break
		except selenium.common.exceptions.StaleElementReferenceException:
			logger.debug("Unable to find all reviews. Last page visited: ", n_page)

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
			# sql = """
			# 	insert into booking_room (
			# 		room_id, hotel_id, name, room_name, address, popular_facilities,
			# 		overall_satisfaction, reviews, property_type, bed_type, accommodates, children_accommodates,
			# 		price, latitude, longitude, city, state, country, currency, comodities,
			# 		images, bedroom_type, qtd_rooms
			# 		)
			# 	values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
			# insert_args = (
			# 	self.room_id, self.hotel_id, self.name, self.room_name, self.address, self.popular_facilities,
			# 	self.overall_satisfaction, self.reviews, self.property_type, self.bed_type, self.adults_accommodates,
			# 	self.children_accommodates, self.price, self.latitude, self.longitude,
			# 	self.city, self.state, self.country, self.currency, self.comodities,
			# 	self.images, self.bedroom_type, self.qtd_rooms
			# 	)
			sql = """
				insert into booking_room (
					room_id, room_name, hotel_name, address, comodities,
					overall_satisfaction, property_type, bed_type, accommodates,
					price, latitude, longitude, reviews
					)
				values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
			insert_args = (
				self.room_id, self.hotel_name, self.room_name, self.localized_address, self.comodities,
				self.overall_satisfaction, self.property_type, self.bedtype, self.accomodates,
				self.price, self.lat, self.lng, self.reviews
				)

			cur.execute(sql, insert_args)
			cur.close()
			conn.commit()
			logger.debug("Room " + str(self.room_name) + ": inserted")
			logger.debug("(lat, long) = (%s, %s)".format(
					lat=self.lat, lng=self.lng))
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


def prepare_driver(url):
	'''Returns a Firefox Webdriver.'''
	options = Options()
	# options.add_argument('-headless')
	binary = FirefoxBinary('C:\\Program Files\\Mozilla Firefox\\firefox.exe')
	driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
	driver.get(url)
	# wait = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
	# 	(By.NAME, 'ss')))
	return driver


def fill_form(driver, config, search_argument, start_date, finish_date):
	# preenche o campo de área de busca
	# search_field = driver.find_element(By.NAME, 'ss')
	# search_field.send_keys(search_argument)

	# # tenta clicar em "checkin/checkout" para exibir calendário com datas disponíveis
	# driver.find_element(By.CSS_SELECTOR, '.fe211c0731').click()
	# sd_div = None
	# if start_date:
	# 	actual_month = int(dt.date.today().isoformat().split("-")[1])
	# 	search_month = int(start_date.split("-")[1])
	# 	while ( search_month > actual_month ):
	# 		actual_month = actual_month + 1
	# 		driver.find_element(By.XPATH, "/html/body/div[5]/div/div/div[2]/"
	# 									+ "form/div[1]/div[2]/div[2]/div/div/div[2]").click()
			
	# 	try: # in case start date is in the actual month
	# 		driver.find_element(By.XPATH, '//*[@data-date="' + start_date + '"]').click()
	# 	except: # in case is in the next
	# 		driver.find_element(By.XPATH, '//*[@data-date="' + start_date + '"]').click()
	# else: # look for the first date in next month
	# 	sd_div = driver.find_element(By.XPATH, '/html/body/div[5]/div/div/div[2]/form/div[1]/div[2]/div[2]'\
	# 				'/div/div/div[3]/div[2]/table/tbody/tr[1]/td[@class="bui-calendar__date"]')
	# 	sd_div.click()
	# 	start_date = sd_div.get_attribute("data-date")
	
	# if finish_date: # if not, the default is the next day to the next to the start
	# 	try:
	# 		driver.find_element(By.XPATH, '//*[@data-date="' + finish_date + '"]').click()
	# 	except:
	# 		driver.find_element(By.XPATH, '//*[@data-date="' + finish_date + '"]').click()
		
	# # We look for the search button and click it
	# driver.find_element_by_class_name('sb-searchbox__button')\
	# 	.click()

	wait = WebDriverWait(driver, timeout=10).until(
		EC.presence_of_all_elements_located(
			(By.XPATH, '//*[@data-testid="property-card"]')))

	return (start_date, finish_date)

def get_price(driver):  # unused
	prices = []
	x = driver.find_elements_by_xpath('//*[@class="bui-price-display__value prco-inline-block-maker-helper prco-font16-helper"]')
	n_rows = len(x)

	for elem in x:
		try:
			prices.append(elem.text.split('R$ ')[1])
		except:
			prices.append(None)
			logger.debug("Price not finded")

	return prices

def get_room_options(driver):
	rooms_options = driver.find_elements_by_xpath("//td[contains(@class, ' hprt-table-cell hprt-table-room-select')]")
	ro = []
	for t in rooms_options:
		ro.append(t.text)
	return ro

def get_room_name(elem, valor_anterior):
	try:
		rn = elem.find_element_by_class_name('hprt-roomtype-link').get_attribute("data-room-name")
		if rn == "":
			rn = elem.find_element_by_class_name('hprt-roomtype-link').text
		rn = rn
	except (TypeError, selenium.common.exceptions.NoSuchElementException):
		return valor_anterior

def get_room_id(elem, valor_anterior):
	try:
		return elem.find_element_by_class_name('hprt-roomtype-link').get_attribute("data-room-id")
	except (TypeError, selenium.common.exceptions.NoSuchElementException):
		return valor_anterior # room id anterior

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

# ENCONTRANDO DADOS NA NOVA VERSÃO
def find_hotel_name(driver, listing):
	element = driver.find_element(By.CSS_SELECTOR, '.pp-header__title')
	listing.hotel_name = element.text

def find_localized_address(driver, listing):
	element = driver.find_element(By.CSS_SELECTOR, '.js-hp_address_subtitle')
	listing.localized_address = element.text

def find_room_informations(driver, listing):
	table_rows = driver.find_elements(By.XPATH, "//*[@id='hprt-table']/tbody/tr")
	for row in table_rows:
		try:
			room_name = row.find_element(By.CLASS_NAME, 'hprt-roomtype-link')
			listing.room_name = room_name.text
			listing.room_id = room_name.get_attribute("data-room-id")

			bed_type = row.find_element(By.CSS_SELECTOR, '.hprt-roomtype-bed')
			listing.bedtype = bed_type.text
		except selenium.common.exceptions.NoSuchElementException:
			pass
		
		accomodates = row.find_elements(By.CSS_SELECTOR, ".bicon-occupancy")
		listing.accomodates = len(accomodates)

		# preco
		price = row.find_element(By.CSS_SELECTOR, '.bui-price-display__value')
		listing.price = price.text.split('R$ ')[1]		

		listing.save(listing.config.FLAGS_INSERT_REPLACE)

def find_latlng(driver, listing): # ok
	element = driver.find_element(By.ID, 'hotel_header')
	coordinates = element.get_attribute('data-atlas-latlng').split(',')
	listing.lat = coordinates[0]
	listing.lng = coordinates[1]

def find_property_type(driver, listing):
	element = driver.find_element(By.XPATH, '//*[@data-testid="property-type-badge"]')
	listing.property_type = element.text
	
def find_overall_classification(driver, listing):
	element = driver.find_element(By.CSS_SELECTOR, 'div.b5cd09854e.d10a6220b4')
	if ',' in element.text:
		listing.overall_satisfaction = float(element.text.replace(',', '.'))
	else:
		listing.overall_satisfaction = float(element.text)

def find_principal_comodities(driver, listing):
	element = driver.find_elements(By.CSS_SELECTOR, 'div.a815ec762e.ab06168e66')
	comodities = []
	for comodity in element:
		comodities.append(comodity.text)

	listing.comodities = comodities

def find_reviews_quantity(driver, listing):
	element = driver.find_element(By.CSS_SELECTOR, '.b5cd09854e.c90c0a70d3.db63693c62')
	listing.reviews = element.text.split(' ')[0]
	print(listing.reviews)

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

def search(config, area, start_date, finish_date, search_reviews):
	driver = prepare_driver('https://www.booking.com/searchresults.pt-br.html?ss=Ouro+Preto&ssne=Ouro+Preto&ssne_untouched=Ouro+Preto&checkin=2023-02-24&checkout=2023-02-25')
	
	wait = WebDriverWait(driver, timeout=10).until(
		EC.presence_of_all_elements_located(
			(By.XPATH, '//*[@data-testid="property-card"]')))
	# FIND ALL PAGES
	all_pages = driver.find_elements(By.CLASS_NAME, 'f32a99c8d1')
	for page in all_pages[1:len(all_pages):1]:
		for i in range(config.ATTEMPTS_TO_FIND_PAGE):
			try:
				logger.debug("Attempt ", i+1, " to find page")
				property_cards = driver.find_elements(By.XPATH, '//*[@data-testid="property-card"]//*[@data-testid="title-link"]')
				urls = []
				for property_card in property_cards:
					urls.append(property_card.get_attribute("href"))

				for url in urls:
					hotel_page = prepare_driver(url)
					
					listing = BListing(config, driver, url)
					
					find_latlng(hotel_page, listing)
					find_overall_classification(hotel_page, listing)
					find_principal_comodities(hotel_page, listing)
					find_hotel_name(hotel_page, listing)
					find_localized_address(hotel_page, listing)
					find_property_type(hotel_page, listing)
					find_room_informations(hotel_page, listing)
				
				page.click()
				break
			except selenium.common.exceptions.TimeoutException:
				continue

	driver.quit()
	
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

def update_routes_geolocation(config, city):
	(lat_max, lat_min, lng_max, lng_min) = utils.get_area_coordinates_from_db(config, city)
	
	conn = config.connect()
	cur = conn.cursor()

	sql = """SELECT distinct(hotel_id), latitude, longitude
		from booking_room
		where route is null
		order by hotel_id""" # nenhum dos 2 é nulo
	'''where latitude <= %s and latitude >= %s and longitude <= %s and longitude >= %s
	'''
	select_args = (lat_max, lat_min, lng_max, lng_min,)
	cur.execute(sql, select_args)
	results = cur.fetchall()
	logger.debug(str(cur.rowcount) + "routes")

	
	for result in results:
		hotel_id = result[0]
		lat = result[1]
		lng = result[2]

		if lat is None or lng is None:
			continue

		location = Location(lat, lng) # initialize a location with coordinates
		location.reverse_geocode(config) # find atributes for location with google api key
		
		if location.get_country() != "N/A":
			country = location.get_country()
		else:
			country = None
		if location.get_level2() != "N/A":
			city = location.get_level2()
		else:
			city = None
		if location.get_neighborhood() != "N/A":
			neighborhood = location.get_neighborhood()
		else:
			neighborhood = None
		if location.get_sublocality() != "N/A":
			sublocality = location.get_sublocality()
		else:
			sublocality = None
		if location.get_route() != "N/A":
			route = location.get_route()
		else:
			route = None

		location.insert_in_table_location(config)
		
		sql = """UPDATE booking_room set route = %s, sublocality = %s
				where hotel_id = %s"""
		update_args = (
			route, sublocality, hotel_id,
			)
		cur.execute(sql, update_args)
		rowcount = cur.rowcount
		logger.debug("Room ", hotel_id, " updated for ", route)
		conn.commit()

	add_routes_area_by_bounding_box(config, city)

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
	parser.add_argument("-urdb", "--update_routes_with_database",
												metavar="city_name", type=str,
												help="""update geolocation based on already existent data""")
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
			search(config, args.city, args.start_date, args.finish_date,
					args.search_reviews)
		elif args.update_routes_with_database:
			fill_empty_routes(config)
			update_cities(config, args.update_routes)
			update_routes(config, args.update_routes)
			logger.debug("Data updated")
		elif args.update_routes_with_bounding_box:
			update_routes_geolocation(config, args.update_routes_with_bounding_box)
	except (SystemExit, KeyboardInterrupt):
		logger.debug("Interrupted execution")
		exit(0)
	except Exception:
		logging.exception("Top level exception handler: quitting.")
		exit(0)

if __name__ == "__main__":
	main()

# preço?????