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
from airbnb_config import ABConfig
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from booking_reviews import BReview
from geopy import distance


SCRIPT_VERSION_NUMBER = "4.0"
DOMAIN =  'https://www.booking.com'
logger = logging.getLogger()

class BListing():
	"""
	# BListing represents an Airbnb room_id, as captured at a moment in time.
	# room_id, survey_id is the primary key.
	"""
	def __init__(self, config, driver, url):
		self.config = config

		time.sleep(5)
		try:
			self.hotel_id = self.get_hotel_id(driver)
		except:
			self.hotel_id = None
		self.property_type = self.get_property_type(driver)
		self.name = self.get_name(driver)
		self.address = self.get_address(driver)
		self.popular_facilities = self.get_popular_facilities(driver)
		self.overall_satisfaction = self.get_overall_satisfaction(driver)
		self.reviews = self.get_reviews(driver)
		self.images = self.get_images(driver)

		(self.latitude, self.longitude) = self.get_lat_lng(driver)
		(self.city, self.state, self.country, self.currency) = self.get_address_elements(url)

		self.room_id = None
		self.room_name = None
		self.bed_type = None
		self.adults_accommodates = None
		self.children_accommodates = None
		self.comodities = None
		self.price = None

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
			return driver.find_element_by_xpath('/html/body/div[5]/div/div[3]/div[2]/div[2]/div[13]/div[1]/a/div/div[1]').text.\
					replace(',','.')
		except:
			try:
				return driver.find_element_by_class_name(
					'bui-review-score--end').find_element_by_class_name(
					'bui-review-score__badge').text.replace(',','.')
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
			return int(driver.find_element_by_xpath('//*[@id="hprt-form"]/input[1]').\
							get_attribute("value"))
		except:
			return int(driver.find_elements_by_xpath('//*[@id="hp_facilities_box"]/div[6]/div[1]/input')[0].\
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

		''''for i in x:
			if 'city_name:' in i:
				city = i.split("city_name: '")[1].split("'")[0]
				state = i.split("state_name: '")[1].split("'")[0]
				country = i.split("country_name: '")[1].split("'")[0]
				currency = i.split("currency: '")[1].split("'")[0]
				break'''

		return (city, state, country, currency)

	def get_popular_facilities(self, driver):
		try:
			x = []
			# Get the most popular facilities

			facilities = driver.find_element_by_class_name('hp_desc_important_facilities')

			for facility in facilities.find_elements_by_class_name('important_facility'):
				x.append(facility.text)
			return x
		except:
			return None

	def get_rooms_id(self, driver): # unused
		rooms_id = []
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/td[@class="ftd roomType"]/div')
		n_rows = len(x)
		
		logger.debug("len de rooms id", n_rows)

		if ( n_rows == 0 ): # in case of search with checkin-checkout date
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

	def get_facilities(self, driver): # unused
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
   
	def get_beds_type(self, driver): # unused
		room_name = []
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr'\
					'td[@class="ftd roomType"]/div/div[@class="room-info"]/a')
		n_rows = len(x)

		i = 0
		if ( n_rows == 0 ):
			x = driver.find_elements_by_xpath('//*[@class="bedroom_bed_type"]/span')
			n_rows = len(x)
			for j in range(n_rows):
				logger.debug(j, "ta no j")
				try:
					room_name.append(x[j].text)
				except:
					print("Bed type not finded")
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

	def get_room_name(self, driver): # unused
		beds_type = []
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/'\
					'td[@class="ftd roomType"]/div/div[@class="room-info"]/div/'\
					'/ul/li/span')
		n_rows = len(x)

		if ( n_rows == 0 ):
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
		x = driver.find_elements_by_xpath('//*[@class="bui-price-display__value prco-text-nowrap-helper prco-font16-helper"]')
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
		if ( n_rows == 0 ):
			x = driver.find_elements_by_xpath('//*[@id="hprt-table"]/tbody/tr/td[2]')
			n_rows = len(x)
			for elem in x:
				try:
					accommodates.append(elem.find_element_by_class_name('bui-u-sr-only').text.split('Máx. pessoas: ')[1])
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

	def get_children_accommodates(self, driver): # unused
		# Get the rooms person capacity
		x = driver.find_elements_by_xpath('//*[@id="maxotel_rooms"]/tbody/tr/td')
		
		n_rows = len(x)
		accommodates = []

		if ( n_rows == 0 ):
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
			x = driver.find_element_by_xpath('//*[@id="hotel_surroundings"]')
			l = x.get_attribute("data-atlas-latlng").split(',')
			latitude = l[0]
			longitude = l[1]
			return (latitude, longitude)
		except:
			return (None, None)

	def get_images(self, driver):
		m_images = []
		images = driver.find_elements_by_xpath('//div[@class="b_nha_hotel_small_images hp_thumbgallery_with_counter"]/a')
		tamanho = len(images)
		for elem in images:
			linha = []
			linha.append(elem.get_attribute("href"))
			linha.append(elem.get_attribute("aria-label"))
			m_images.append(linha)
		return m_images

	def get_reviews_text(self, driver):
		try:

			driver.find_element_by_xpath('//*[@id="show_reviews_tab"]').click()
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
						review_pages.append(p.text.split('\n')[0]) # append(p.text.split(\n)[0]) ??? ai tem q verificar se vai 1 vez em cada 1
						new_page = True
						p.click()
						time.sleep(5)
						reviews = driver.find_elements_by_class_name('review_list_new_item_block')
						for review in reviews: # get the reviews
							r = BReview(self.config, review, self.hotel_id)
							r.save(self.config.FLAGS_INSERT_REPLACE)
							n_review = n_review + 1
						break
		except selenium.common.exceptions.StaleElementReferenceException:
			print("Unable to find all reviews. Last page visited: ", n_page)

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
			
			'''if insert_replace_flag == self.config.FLAGS_INSERT_REPLACE:
				rowcount = self.__update()'''
			if (rowcount == 0 or
					insert_replace_flag == self.config.FLAGS_INSERT_NO_REPLACE):
				try:
					# self.get_address()
					self.__insert()
					return True
				except psycopg2.IntegrityError:
					logger.debug("Room " + str(self.name) + ": already collected")
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
		try:
			logger.debug("Values: ")
			logger.debug("\troom: {}".format(self.room_id))
			conn = self.config.connect()
			cur = conn.cursor()
			sql = """
				insert into booking_room (
					room_id, hotel_id, name, room_name, address, popular_facilities,
					overall_satisfaction, reviews, property_type, bed_type, accommodates, children_accommodates,
					price, latitude, longitude, city, state, country, currency, comodities, images
					)
				values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
			insert_args = (
				self.room_id, self.hotel_id, self.name, self.room_name, self.address, self.popular_facilities,
				self.overall_satisfaction, self.reviews, self.property_type, self.bed_type, self.adults_accommodates,
				self.children_accommodates, self.price, self.latitude, self.longitude,
				self.city, self.state, self.country, self.currency, self.comodities, self.images
				)
			cur.execute(sql, insert_args)
			cur.close()
			conn.commit()
			logger.debug("Room " + str(self.name) + ": inserted")
			logger.debug("(lat, long) = (%s, %s)".format(lat=self.latitude, lng=self.longitude))
		except psycopg2.IntegrityError:
			logger.info("Room " + str(self.name) + ": insert failed")
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
	driver = webdriver.Firefox(firefox_binary=binary, executable_path=r'C:\\geckodriver.exe', options=options)
	driver.get(url)
	wait = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
		(By.ID, 'ss')))
	return driver

def fill_form(driver, config, search_argument, tomorrow_rooms):
	'''Finds all the input tags in form and makes a POST requests.'''
	try:
		search_field = driver.find_element_by_id('ss')
		search_field.send_keys(search_argument)

		#if config.SEARCH_WITH_DATE:
		driver.find_element_by_xpath('/html/body/div[5]/div/div/div[2]/form/div[1]/div[2]/'\
											'div[1]/div[2]/div/div/div/div/span').click()
		
		if tomorrow_rooms:
			try: # select the first selectionable day in calendar (in pratice, tomorrow)
				print("tomorrow in this month")
				driver.find_element_by_xpath('/html/body/div[5]/div/div/div[2]/form/div[1]/div[2]/'\
					'div[2]/div/div/div[3]/div[1]/table/tbody/tr/td[@class="bui-calendar__date"]').click()
			except: # in case of "tomorrow" in the other month
				print("Tomorrow in next month")
				driver.find_element_by_xpath('/html/body/div[5]/div/div/div[2]/form/div[1]/div[2]/div[2]'\
					'/div/div/div[3]/div[2]/table/tbody/tr[1]/td[@class="bui-calendar__date"]').click()
		else: # search for rooms in the first day of next month
			print("next month")
			driver.find_element_by_xpath('/html/body/div[5]/div/div/div[2]/form/div[1]/div[2]/div[2]'\
					'/div/div/div[3]/div[2]/table/tbody/tr[1]/td[@class="bui-calendar__date"]').click()
		
		# We look for the search button and click it
		driver.find_element_by_class_name('sb-searchbox__button')\
			.click()
		
		wait = WebDriverWait(driver, timeout=10).until(
			EC.presence_of_all_elements_located(
				(By.CLASS_NAME, 'sr-hotel__title')))
		return True
	except:
		return False

def scrape_results(config, driver, n_results):
	'''Returns the data from n_results amount of results.'''
	#try:
	accommodations_urls = list()

	for accomodation_title in driver.find_elements_by_class_name('sr-hotel__title'):
		accommodations_urls.append(accomodation_title.find_element_by_class_name(
			'hotel_name_link').get_attribute('href'))

	k = 0
	for url in range(0, n_results):
		'''try:
		if url == n_results:
			print("End of page results")
			break'''
		try:
			scrape_accommodation_data(config, driver, accommodations_urls[url], url)
			k = k + 1
		except IndexError:
			break

	return k

def scrape_accommodation_data(config, driver, accommodation_url, n_page):
	'''Visits an accommodation page and extracts the data.'''
	#try:
	if driver == None:
		driver = prepare_driver(accommodation_url)

	driver.get(accommodation_url)
	time.sleep(12)

	accommodation = BListing(config, driver, accommodation_url)
	print(accommodation.name)

	x = driver.find_elements_by_xpath('//table[@id="hprt-table"]/tbody/tr')
	id_anterior = None
	bed_anterior = []
	room_anterior = None
	linha_anterior = []
	i = 1
	for elem in x:
		accommodation.bed_type = []
		print("Room: ", i," from page ", n_page)
		try:
			accommodation.room_id = elem.find_element_by_class_name('hprt-roomtype-link').get_attribute("data-room-id")
			id_anterior = accommodation.room_id
		except:
			accommodation.room_id = id_anterior # room id anterior
		try:
			accommodation.room_name = elem.find_element_by_class_name('hprt-roomtype-link').get_attribute("data-room-name")
			room_anterior = accommodation.room_name
		except:
			accommodation.room_name = room_anterior
		try:
			beds_type = elem.find_elements_by_class_name("rt-bed-type")
			for k in beds_type:
				accommodation.bed_type.append(k.text)
			if accommodation.bed_type == []:
				beds_type = elem.find_elements_by_class_name("bedroom_bed_type")
				for k in beds_type:
					accommodation.bed_type.append(k.text)
			bed_anterior = accommodation.bed_type
				# linha_anterior = [] ??????
		except:
			accommodation.bed_type = bed_anterior 
			accommodation.adults_accommodates = elem.find_element_by_class_name('bui-u-sr-only').text.split('Máx. pessoas: ')[1]
		try:
			accommodation.price = elem.find_element_by_xpath('//tr[' + str(i) + ']/td[3]/div/div[2]/div[1]').text.split('R$ ')[1]
		except:
			accommodation.price = elem.find_element_by_xpath('//tr[' + str(i) + ']/td[2]/div/div[2]/div[1]').text.split('R$ ')[1]
		try:
			y = elem.find_elements_by_xpath('//tr[' + str(i) + ']/td[1]/div/div[4]/div/div/span[@class="hprt-facilities-facility"]/span')
			n_rows = len(x)
			linha = []
			for j in y:
				linha.append(j.text)

			accommodation.comodities = linha + accommodation.popular_facilities
			linha_anterior = linha
		except:
			accommodation.comodities = linha_anterior 
		#print(accommodation.comodities)

		i = i + 1
	accommodation.save(config.FLAGS_INSERT_REPLACE)
	
	#if accommodation.reviews is not None:
	#    accommodation.get_reviews_text(driver)

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
		print(str(cur.rowcount) + " rooms to update")

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

			print(cur.rowcount, "room(s) ", room_id," updated for ", sublocality)
				
	except:
		raise

def is_inside(lat_center, lng_center, lat_test, lng_test):
	center_point = [{'lat': lat_center, 'lng': lng_center}]
	test_point = [{'lat': lat_test, 'lng': lng_test}]

	for radius in range(50):
		center_point_tuple = tuple(center_point[0].values()) # (-7.7940023, 110.3656535)
		test_point_tuple = tuple(test_point[0].values()) # (-7.79457, 110.36563)

		dis = distance.distance(center_point_tuple, test_point_tuple).km
		
		if dis <= radius:
			print("{} point is inside the {} km radius from {} coordinate".\
					format(test_point_tuple, radius/1000, center_point_tuple))
			return True
	return False

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
			print(str(cur.rowcount) + " routes to update")

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

					if is_inside(latitude, longitude, lat, lng):
						sql = """UPDATE booking_room set sublocality = %s where room_id = %s"""
						update_args = ( sublocality, r_id )
						cur.execute(sql, update_args)
						conn.commit()

						print("Room ", r_id," updated for ", sublocality)
						break
				
	except:
		raise

def search(config, area, tomorrow_rooms):
	for i in range(config.ATTEMPTS_TO_FIND_PAGE):
		print("Attempt ", i+1, " to find page")
		try:
			driver = prepare_driver(DOMAIN)
			fill_form(driver, config, area, tomorrow_rooms)
			break
		except selenium.common.exceptions.TimeoutException:
			continue

	if driver is None:
		return False

	urls = []
	for link in driver.find_elements_by_xpath('//*[@id="search_results_table"]/div[4]/nav/ul/li[2]/ul/li/a'):
		urls.append(link.get_attribute('href'))
	driver.quit()

	i = 1
	n_rooms = 0
	for url in urls:
		page = prepare_driver(url)
		logger.debug("Page ", i, " of ", len(urls))
		n_rooms = n_rooms + scrape_results(config, page, 25)
		print(n_rooms, " room(s) inserted")
		page.quit()
		i = i + 1
	return True

def update_routes_geolocation(config):
	try:
		conn = config.connect()
		cur = conn.cursor()

		sql = """UPDATE booking_room T1 
				SET
				 route = T2.name
				FROM route T2
				WHERE 
				  strpos(address, T2.name) <> 0;
				 
				UPDATE booking_room T1 
				SET
				 sublocality = T2.sublocality
				FROM room T2
				WHERE 
				  T1.route = T2.route""" # nenhum dos 2 é nulo
		
		cur.execute(sql)
		rowcount = cur.rowcount
		print(rowcount, " hotels updated")
		conn.commit()
	except:
		raise

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
	parser.add_argument("-t", "--tomorrow_rooms",
						default=False,
						help="""search rooms in the imediatly next day""") # para implementar
	parser.add_argument("-or", "--only_reviews",
						default=False,
						help="""search only for reviews""") # para implementar
	parser.add_argument('-sc', '--city',
					   metavar='city_name', type=str,
					   help="""search by a city
					   """) 
	
	# Only one argument!
	group = parser.add_mutually_exclusive_group()
	group.add_argument('-ur', '--update_routes',
					   metavar='city_name', type=str,
					   help="""update routes from rooms""") # by victor

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
		if args.city:
			search(config, args.city, args.tomorrow_rooms)
		elif args.update_routes:
			update_cities(config, args.update_routes)
			update_routes(config, args.update_routes)
	except (SystemExit, KeyboardInterrupt):
		logger.debug("Interrupted execution")
		exit(0)
	except Exception:
		logging.exception("Top level exception handler: quitting.")
		exit(0)

if __name__ == "__main__":
	main()