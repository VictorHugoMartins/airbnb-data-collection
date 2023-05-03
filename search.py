#!/usr/bin/python3
# ============================================================================
# Airbnb web site scraper, for analysis of Airbnb listings
# Tom Slee, 2013--2015.
# Victor Martins, 2020.
#
# function naming conventions:
#   ws_get = get from web site
#   db_get = get from database
#   db_add = add to the database
#
# function name conventions:
#   add = add to database
#   display = open a browser and show
#   list = get from database and print
#   print = get from web site and print
# ============================================================================
import logging
import requests
import argparse
import sys
import time
import webbrowser
from lxml import html
import psycopg2
import psycopg2.errorcodes
from general_config import ABConfig
from airbnb_survey import ABSurveyByBoundingBox
from airbnb_listing import ABListing
from airbnb_geocoding import BoundingBox
from airbnb_geocoding import Location
from airbnb_geocoding import identify_and_insert_locations
import airbnb_ws
from airbnb_score import airbnb_score_search
from booking import search_booking_rooms
from utils import select_command

SCRIPT_VERSION_NUMBER = "5.0"

def db_ping(config):
		"""
		Test database connectivity, and print success or failure.
		"""
		try:
				conn = config.connect()
				if conn is not None:
						print("Connection test succeeded: {db_name}@{db_host}"
									.format(db_name=config.DB_NAME, db_host=config.DB_HOST))
				else:
						print("Connection test failed")
		except Exception:
				logging.exception("Connection test failed")


def db_add_survey(config, search_area):
		"""
		Add a survey entry to the database, so the survey can be run.
		Also returns the survey_id, in case it is to be used..
		"""

		# POSTGRESQL
		try:
				conn = config.connect()
				cur = conn.cursor()
				# Add an entry into the survey table, and get the survey_id
				sql = """
				insert into survey (survey_description, search_area_id)
				select (name || ' (' || current_date || ')') as survey_description,
				search_area_id
				from search_area
				where name = %s
				returning survey_id"""
				cur.execute(sql, (search_area,))
				survey_id = cur.fetchone()[0]

				# Get and print the survey entry
				cur.execute("""select survey_id, survey_date,
				survey_description, search_area_id
				from survey where survey_id = %s""", (survey_id,))
				(survey_id,
				 survey_date,
				 survey_description,
				 search_area_id) = cur.fetchone()
				conn.commit()
				cur.close()
				print("\nSurvey added:\n"
							+ "\n\tsurvey_id=" + str(survey_id)
							+ "\n\tsurvey_date=" + str(survey_date)
							+ "\n\tsurvey_description=" + survey_description
							+ "\n\tsearch_area_id=" + str(search_area_id))
				return survey_id
		except Exception:
				logging.error("Failed to add survey for %s", search_area)
				raise


def db_add_search_area(config, search_area, flag):  # version of tom slee
		"""
		Add a search_area to the database.
		"""
		try:
				logging.info("Adding search_area to database as new search area")
				# Add the search_area to the database anyway
				conn = config.connect()
				cur = conn.cursor()
				# check if it exists
				sql = """
				select name
				from search_area
				where name = %s"""
				cur.execute(sql, (search_area,))
				if cur.fetchone() is not None:
						print("City already exists: {}".format(search_area))
						return True
				# Compute an abbreviation, which is optional and can be used
				# as a suffix for search_area views (based on a shapefile)
				# The abbreviation is lower case, has no whitespace, is 10 characters
				# or less, and does not end with a whitespace character
				# (translated as an underscore)
				abbreviation = search_area.lower()[:10].replace(" ", "_")
				while abbreviation[-1] == "_":
						abbreviation = abbreviation[:-1]

				# Insert the search_area into the table
				sql = """insert into search_area (name, abbreviation)
				values (%s, %s)"""
				cur.execute(sql, (search_area, abbreviation,))
				sql = """select
				currval('search_area_search_area_id_seq')
				"""
				cur.execute(sql, ())
				search_area_id = cur.fetchone()[0]
				# city_id = cur.lastrowid
				cur.close()
				conn.commit()
				print("Search area {} added: search_area_id = {}"
							.format(search_area, search_area_id))
				print("Before searching, update the row to add a bounding box, using SQL.")
				print(
						"I use coordinates from http://www.mapdevelopers.com/geocode_bounding_box.php.")
				print("The update statement to use is:")
				print("\n\tUPDATE search_area")
				print("\tSET bb_n_lat = ?, bb_s_lat = ?, bb_e_lng = ?, bb_w_lng = ?")
				print("\tWHERE search_area_id = {}".format(search_area_id))
				print("\nThis program does not provide a way to do this update automatically.")

		except Exception:
				print("Error adding search area to database")
				raise


def select_sublocalities(config, city):
		return select_command(config,
						sql_script="""SELECT DISTINCT sublocality, locality from location where strpos(locality, %s) <> 0""",
						params=(city,),
						initial_message="Selecting sublocalities from city",
						failure_message="Failed to search from sublocalities")

def select_routes(config, sublocality):
		return select_command(config,
						sql_script="""SELECT distinct route, sublocality from location where strpos(sublocality, %s) <> 0""",
						params=(sublocality,),
						initial_message="Selecting routes from sublocality",
						failure_message="Failed to search from sublocalities")

def create_super_survey(config, city):
		try:
				ss_id = None
				rowcount = -1
				logging.info("Initializing search by routes")
				conn = config.connect()
				cur = conn.cursor()


				sql = """INSERT into super_survey(city, date) values (%s, current_date) returning ss_id"""
				cur.execute(sql, (city,))
				ss_id = cur.fetchone()[0]

				return ss_id
		except Exception:
				logging.error("Failed to search from sublocalities")
				raise
		finally:
				return ss_id

def update_survey_with_super_survey_id(config, super_survey_id, survey_id):
		try:
				rowcount = -1
				logging.info("Initializing update of survey with super survey id")
				conn = config.connect()
				cur = conn.cursor()


				sql = """UPDATE survey set ss_id = %s where survey_id = %s"""
				cur.execute(sql, (super_survey_id, survey_id))
		except Exception:
				logging.error("Failed to update survey with super survey id")
				raise

def execute_search(ab_config, platform="Airbnb", search_area_name='', fill_airbnb_with_selenium=False, start_date=None, finish_date=None, super_survey_id=None):
		#create/insert in database search area with coordinates
		bounding_box = BoundingBox.from_geopy(ab_config, search_area_name)
		bounding_box.add_search_area(ab_config, search_area_name)

		# initialize new survey
		survey_id = db_add_survey(ab_config, search_area_name)
		if (super_survey_id): update_survey_with_super_survey_id(ab_config, super_survey_id, survey_id)
		survey = ABSurveyByBoundingBox(ab_config, survey_id)

		# search for the listings
		if (platform == "Airbnb"):
				survey.search(ab_config.FLAGS_ADD)
		else:
				search_booking_rooms(ab_config, search_area_name, start_date, finish_date, survey_id)

		if (fill_airbnb_with_selenium):
				airbnb_score_search(ab_config, search_area_name, 252, None)

		return survey_id
		# update_routes_geolocation(ab_config, search_area_name)

def search_sublocalities(ab_config, super_survey_id, search_area_name='', fill_airbnb_with_selenium=True):
		sa_name = search_area_name.split(',')[0]
		city_sublocalities = select_sublocalities(ab_config, search_area_name)
		for city in city_sublocalities:
			if (city[0] is not None):
					city_name = city[0] + ', ' + city[1]
					survey_id = execute_search(ab_config, "Airbnb", city_name, fill_airbnb_with_selenium, super_survey_id=super_survey_id)
					identify_and_insert_locations(ab_config, platform, survey_id)

def search_routes(ab_config, search_area_name='', fill_airbnb_with_selenium=True, super_survey_id=None):
		sa_name = search_area_name.split(',')[0]
		sublocalities_routes = select_routes(ab_config, search_area_name)
		print(sublocalities_routes)
		for route in sublocalities_routes:
			if (route[0] is not None):
					route_name = route[0] + ', ' + route[1]
					execute_search(ab_config, "Airbnb", route_name, fill_airbnb_with_selenium, super_survey_id=super_survey_id)

def full_process(ab_config, platform="Airbnb", search_area_name='', fill_airbnb_with_selenium=None, start_date=None, finish_date=None):
		fill_bnb_with_selenium = platform == 'Airbnb'
		
		super_survey_id = create_super_survey(ab_config, search_area_name)
		survey_id = execute_search(ab_config, platform, search_area_name, fill_bnb_with_selenium, start_date, finish_date, super_survey_id)
		# identify_and_insert_locations(ab_config, platform, survey_id) #not necessary since is inserting locations at the same time its inserting rooms
		search_sublocalities(ab_config, search_area_name)
		search_routes(ab_config, search_area_name)


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
		group.add_argument('-asa', '--addsearcharea',
											 metavar='search_area', action='store', default=False,
											 help="""add a search area to the database. A search area
											 is typically a city, but may be a bigger region.""")
		group.add_argument('-dbp', '--dbping',
											 action='store_true', default=False,
											 help='Test the database connection')
		group.add_argument('-dh', '--displayhost',
											 metavar='host_id', type=int,
											 help='display web page for host_id in browser')
		group.add_argument('-dr', '--displayroom',
											 metavar='room_id', type=int,
											 help='display web page for room_id in browser')
		group.add_argument('-dsv', '--delete_survey',
											 metavar='survey_id', type=int,
											 help="""delete a survey from the database, with its
											 listings""")
		group.add_argument('-f', '--fill', nargs='?',
											 metavar='survey_id', type=int, const=0,
											 help='fill details for rooms collected with -s')
		group.add_argument('-lsa', '--listsearcharea',
											 metavar='search_area', type=str,
											 help="""list information about this search area
											 from the database""")
		group.add_argument('-lr', '--listroom',
											 metavar='room_id', type=int,
											 help='list information about room_id from the database')
		group.add_argument('-ls', '--listsurveys',
											 action='store_true', default=False,
											 help='list the surveys in the database')
		group.add_argument('-sb', '--search',
											 metavar='survey_id', type=int,
											 help="""search for rooms using survey survey_id,
											 by bounding box
											 """)
		group.add_argument('-ur', '--update_routes',
											 metavar='city_name', type=str,
											 help="""update routes from rooms""")  # by victor
		group.add_argument('-sbs', '--search_sublocalities',
											 metavar='city_name', type=str,
											 help="""bounding box search from sublocalities""")
		group.add_argument('-sbr', '--search_routes',
											 metavar='city_name', type=str,
											 help="""bounding box search from routes""")
		group.add_argument('-rss', '--restart_super_survey',
											 metavar='super_survey_id', type=int,
											 help="""restart super survey""")
		group.add_argument('-css', '--continue_super_survey_by_sublocality',
											 metavar='super_survey_id', type=int,
											 help="""continue super survey by sublocality""")
		group.add_argument('-csr', '--continue_super_survey_by_route',
											 metavar='super_survey_id', type=int,
											 help="""continue super survey by route""")
		group.add_argument('-fs', '--full_survey',
											 metavar='full survey area', type=str,
											 help="""make a full survey ininterrumptly""")
		parser.add_argument('-pt', '--platform',
											 metavar='platform search', type=str,
											 help="""platform to search""")	
		group.add_argument('-V', '--version',
											 action='version',
											 version='%(prog)s, version ' +
											 str(SCRIPT_VERSION_NUMBER))
		group.add_argument('-?', action='help')

		args = parser.parse_args()
		return (parser, args)

def main():
		"""
		Main entry point for the program.
		"""
		(parser, args) = parse_args()
		logging.basicConfig(
				format='%(levelname)-8s%(message)s', level=logging.INFO)
		ab_config = ABConfig(args)
		
		try:
				if args.addsearcharea:
						bounding_box = BoundingBox.from_geopy(
								ab_config, args.addsearcharea)
						bounding_box.add_search_area(ab_config, args.addsearcharea)
						# db_add_search_area(ab_config, args.addsearcharea, ab_config.FLAGS_ADD) # tom slee version
				elif args.dbping:
						db_ping(ab_config)
				elif args.update_routes:
						update_routes_geolocation(ab_config, args.update_routes)
						# update_cities(ab_config, args.update_routes)
				elif args.search_sublocalities:
						search_sublocalities(ab_config, args.search_sublocalities, fill_airbnb_with_selenium=True)
				elif args.search_routes:
						search_routes(ab_config, args.search_routes, fill_airbnb_with_selenium=True)
				elif args.full_survey and args.platform:
						print(args.full_survey, args.platform)
						full_process(ab_config,args.platform, args.full_survey)
				else:
						parser.print_help()
		except (SystemExit, KeyboardInterrupt):
				sys.exit()
		except Exception:
				logging.exception("Top level exception handler: quitting.")
				sys.exit(0)


if __name__ == "__main__":
		main()
