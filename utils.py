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

logging = logging.getLogger()

def get_area_coordinates_from_db(config, area):
		conn = config.connect()
		cur = conn.cursor()

		sql = """SELECT bb_n_lat, bb_s_lat, bb_w_lng, bb_e_lng
						from search_area
						where name = %s
						limit 1""" # os q precisa atualizar
		cur.execute(sql, (area,))                
		result = cur.fetchall()

		lat_max = float(result[0][0])
		lat_min = float(result[0][1])
		lng_min = float(result[0][2])
		lng_max = float(result[0][3])

		return (lat_max, lat_min, lng_max, lng_min)

def is_inside(lat_center, lng_center, lat_test, lng_test, verbose=False):
		center_point = [{'lat': lat_center, 'lng': lng_center}]
		test_point = [{'lat': lat_test, 'lng': lng_test}]

		for radius in range(50):
				center_point_tuple = tuple(center_point[0].values()) # (-7.7940023, 110.3656535)
				test_point_tuple = tuple(test_point[0].values()) # (-7.79457, 110.36563)

				dis = distance.distance(center_point_tuple, test_point_tuple).km
				
				if dis <= radius:
						if ( verbose == True ):
								print("{} point is inside the {} km radius from {} coordinate".\
										format(test_point_tuple, radius/1000, center_point_tuple))
						return True
		return False

def select_command(config, sql_script, params, initial_message, failure_message):
		try:
				rowcount = -1
				logging.info(initial_message)
				conn = config.connect()
				cur = conn.cursor()

				sql = sql_script

				cur.execute(sql, (params))
				rowcount = cur.rowcount
				
				return cur.fetchall()
		except Exception:
				logging.error(failure_message)
				raise


def update_command(config, sql_script, params, initial_message, failure_message):
		try:
				id = None
				rowcount = -1
				logging.info(initial_message)
				conn = config.connect()
				cur = conn.cursor()
				
				cur.execute(sql_script, params)
				conn.commit()
		except Exception:
				logging.error(failure_message)
				raise
				
def prepare_driver(url):
		'''Returns a Firefox Webdriver.'''
		options = Options()
		# options.add_argument('-headless')
		binary = FirefoxBinary('C:\\Program Files\\Mozilla Firefox\\firefox.exe')
		driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
		driver.get(url)
		time.sleep(5)
		return driver