#!/usr/bin/python3
# ============================================================================
# Airbnb web site scraper, for analysis of Airbnb listings
# Tom Slee, 2013--2015.
# Victor Martins, 2020-2023.
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
import airbnb_ws
import utils

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


def delete_room_repeats(config, super_survey_id):
		try:
				logging.info("Deleting repeats from super survey")
				conn = config.connect()
				cur = conn.cursor()

				sql = """DELETE from room
								where room_id in
										(select room_id from room
										group by room_id
										having Count(room_id)>1)
								and not last_modified in
										(select max(last_modified) from room
										group by room_id
										 having Count(room_id)>1)
								"""

				cur.execute(sql, (super_survey_id,))
				rowcount = cur.rowcount

				if rowcount > 0:
						print(rowcount + " rooms deleted")
				else:
						print("No rooms deleted")
		except Exception:
				logging.error("Failed to continue super survey")
				raise


def verify_existent_search_area(config, area):
		# POSTGRESQL
		try:
				rowcount = -1
				conn = config.connect()
				cur = conn.cursor()
				sql = """
						SELECT name
						from search_area
						where name = %s
						limit 1
						"""
				cur.execute(sql, (survey_id,))
				rowcount = cur.rowcount
		except:
				logging.info("Error to verify preexistence of search area")
		return (rowcount > 0)

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
		group.add_argument('-lr', '--listroom',
											 metavar='room_id', type=int,
											 help='list information about room_id from the database')
		group.add_argument('-ls', '--listsurveys',
											 action='store_true', default=False,
											 help='list the surveys in the database')
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
		select_routes(ab_config, 'Bauxita')
		exit(0)
		
		try:
				if args.search_by_bounding_box:
						survey = ABSurveyByBoundingBox(
								ab_config, args.search_by_bounding_box)
						survey.search(ab_config.FLAGS_ADD)
				elif args.add_and_search_by_bounding_box:
						survey_id = db_add_survey(ab_config,
																			args.add_and_search_by_bounding_box)
						survey = ABSurveyByBoundingBox(ab_config, survey_id)
						survey.search(ab_config.FLAGS_ADD)
				elif args.addsearcharea:
						bounding_box = BoundingBox.from_geopy(
								ab_config, args.addsearcharea)
						bounding_box.add_search_area(ab_config, args.addsearcharea)
				else:
						parser.print_help()
		except (SystemExit, KeyboardInterrupt):
				sys.exit()
		except Exception:
				logging.exception("Top level exception handler: quitting.")
				sys.exit(0)


if __name__ == "__main__":
		main()