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
import airbnb_ws
import utils
from airbnb_score import search as fill_search

SCRIPT_VERSION_NUMBER = "4.0"
# logging = logging.getLogger()


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


def search_sublocalities_by_bounding_box(config, city):
    try:
        rowcount = -1
        logging.info("Initializing search by sublocalities")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT name from search_area, sublocality, level2 where
            level2.level2_name = %s and level2.level2_id = sublocality.level2_id
            and sublocality.sublocality_name = search_area.name order by sublocality_name"""

        cur.execute(sql, (city,))
        rowcount = cur.rowcount

        if rowcount > 0:
            results = cur.fetchall()
            logging.info("Sublocalities: %s", results)
            # create new super_survey
            sql = """INSERT into super_survey(city, date) values (%s, current_date) returning ss_id"""
            cur.execute(sql, (city,))
            ss_id = cur.fetchone()[0]

            for result in results:
                logging.info("Search by %s", result[0])
                survey_id = db_add_survey(config,
                                          result[0])
                # update inserting super_survey_id
                sql = """UPDATE survey set ss_id = %s where survey_id = %s"""
                cur.execute(sql, (ss_id, survey_id))

                survey = ABSurveyByBoundingBox(config, survey_id)
                survey.search(config.FLAGS_ADD)

    except Exception:
        logging.error("Failed to search from sublocalities")
        raise


def update_routes(config, city):
    (lat_max, lat_min, lng_max, lng_min) = utils.get_area_coordinates_from_db(config, city)
    try:
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(room_id), latitude, longitude from room
                where latitude <= %s and latitude >= %s
                and longitude <= %s and longitude >= %s
                order by room_id"""  # os q precisa atualizar
        select_args = (lat_max, lat_min, lng_max, lng_min,)
        cur.execute(sql, select_args)
        routes = cur.fetchall()
        print(str(cur.rowcount) + " routes to update")

        sql = """SELECT distinct(room_id), latitude, longitude, sublocality from room
                where route is not null and ( sublocality is not null and sublocality <> '')
                and latitude <= %s and latitude >= %s
                and longitude <= %s and longitude >= %s
                order by sublocality desc"""  # nenhum dos 2 é nulo
        select_args = (lat_max, lat_min, lng_max, lng_min,)
        cur.execute(sql, select_args)
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
                    sql = """UPDATE room set sublocality = %s where room_id = %s"""
                    update_args = (sublocality, r_id)
                    cur.execute(sql, update_args)
                    conn.commit()

                    print("Room ", r_id, " updated for ", sublocality)
                    break

    except:
        raise


def update_routes_geolocation(config, city):
    (lat_max, lat_min, lng_max, lng_min) = utils.get_area_coordinates_from_db(config, city)

    conn = config.connect()
    cur = conn.cursor()

    sql = """SELECT distinct(room_id), latitude, longitude
            from room
            where latitude <= %s and latitude >= %s
            and longitude <= %s and longitude >= %s
            order by room_id"""  # nenhum dos 2 é nulo
    select_args = (lat_max, lat_min, lng_max, lng_min,)
    cur.execute(sql, select_args)
    results = cur.fetchall()
    print(str(cur.rowcount) + " routes")

    for result in results:
        print(result)
        
        room_id = result[0]
        lat = result[1]
        lng = result[2]

        print(str(lat), str(lng))
        location = Location(str(lat), str(lng)) 
        location.reverse_geocode(config)
        
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

        sql = """UPDATE room set route = %s, sublocality = %s,
                        city = %s, country = %s, neighborhood = %s
                where room_id = %s"""
        update_args = (
            route, sublocality, city, country, neighborhood, room_id
        )
        cur.execute(sql, update_args)
        rowcount = cur.rowcount
        print("Room ", room_id, " updated for ", route)
        conn.commit()

    add_routes_area_by_bounding_box(config, city)


def update_cities(config, city):
    (lat_max, lat_min, lng_max, lng_min) = utils.get_area_coordinates_from_db(config, city)

    try:
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(room_id), route, sublocality, city, country from room
                where latitude <= %s and latitude >= %s
                and longitude <= %s and longitude >= %s
                and route is not null
                group by room_id, route, sublocality, city, country
                order by room_id"""  # os q precisa atualizar
        select_args = (lat_max, lat_min, lng_max, lng_min,)
        cur.execute(sql, select_args)
        results = cur.fetchall()
        print(str(cur.rowcount) + " rooms to update")

        i = 0
        for result in results:
            room_id = result[0]
            route = result[1]
            sublocality = result[2]
            city = result[3]
            country = result[4]

            sql = """UPDATE room set route = %s,
                    sublocality = %s,
                    city = %s, country = %s
                    where room_id = %s"""
            update_args = (route, sublocality, city, country, room_id)
            cur.execute(sql, update_args)
            conn.commit()

            print(cur.rowcount, "room(s) ", room_id,
                  " updated for ", sublocality)

    except:
        raise


def add_routes_area_by_bounding_box(config, city):
    try:
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(route) from room
                where city = %s"""  # os q precisa atualizar
        select_args = (city,)
        cur.execute(sql, select_args)
        results = cur.fetchall()
        print(str(cur.rowcount) + " rooms finded")

        for result in results:
            route_name = str(result[0]) + ', ' + city
            bounding_box = BoundingBox.from_geopy(config, route_name)
            if bounding_box != None:
                bounding_box.add_search_area(config, route_name)
    except:
        raise


def search_routes_by_bounding_box(config, city):
    try:
        rowcount = -1
        logging.info("Initializing search by routes")
        conn = config.connect()
        cur = conn.cursor()

        print(city)
        sql = """SELECT distinct(name)
                from search_area
                where strpos(name, %s) != 0
                order by name
            """
        select_args = (', ' + city,)
        cur.execute(sql, select_args)
        rowcount = cur.rowcount

        if rowcount > 0:
            results = cur.fetchall()
            logging.info("Routes: %s", results)
            # create new super_survey
            sql = """INSERT into super_survey(city, date) values (%s, current_date) returning ss_id"""
            cur.execute(sql, (city,))
            ss_id = cur.fetchone()[0]

            for result in results:
                name = result[0]
                logging.info("Search by %s", name)
                survey_id = db_add_survey(config, name)
                # update inserting super_survey_id
                sql = """UPDATE survey set ss_id = %s where survey_id = %s"""
                cur.execute(sql, (ss_id, survey_id))

                survey = ABSurveyByBoundingBox(config, survey_id)
                survey.search(config.FLAGS_ADD)

    except Exception:
        logging.error("Failed to search routes")
        raise


def search_reviews(config, survey_id):
    try:
        rowcount = -1
        logging.info("Initializing search by host reviews")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT room_id, survey_id, host_id from room where reviews > 0 order by host_id desc"""

        cur.execute(sql, (survey_id,))
        rowcount = cur.rowcount
        logging.info(str(rowcount) + " rooms founded.")

        if rowcount > 0:
            results = cur.fetchall()

            for result in results:
                room_id = result[0]
                survey_id = result[1]
                host_id = result[2]
                listing = ABListing(config, room_id, survey_id)

                response = requests.get(
                    'https://www.airbnb.com.br/users/show/' + str(host_id))
                if response is not None:
                    print(response.status_code)

                    ''' The page must obey a certain structure to return the comment data,
                    I defined the limit of attempts to find that page "complete" before moving on to the next room '''
                    for i in range(10):
                        logging.info(
                            "Attempt {i}: searching for room {r}".format(i=i+1, r=host_id))
                        if listing.get_comments(host_id, response):
                            print("Comments finded")
                            break
        else:
            print("No rooms in this super survey")

    except Exception:
        logging.error("Failed to search reviews")
        raise


def get_comments(self):
    """ Get the reviews properties from the web site """
    try:
        # initialization
        logger.info("-" * 70)
        logger.info("Host " + str(host_id) +
                    ": getting from Airbnb web site")
        room_url = "airbnb.com.br/users/show/" + str(host_id)
        response = airbnb_ws.ws_request_with_repeats(self.config, room_url)
        if response is not None:
            page = response.text
            tree = html.fromstring(page)
            print(page)
            exit(0)
            if self.__get_reviews(tree) == False:
                return False
            elif self.reviews == 0:
                print("No reviews to find")
                return True
            else:
                return self.__get_reviews_text(tree)
        else:
            logger.info("Room %s: not found", self.room_id)
            return False
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as ex:
        logger.exception("Room " + str(self.host_id) +
                         ": failed to retrieve from web site.")
        logger.error("Exception: " + str(type(ex)))
        raise


def restart_super_survey(config, super_survey_id):
    try:
        rowcount = -1
        logging.info("Restarting super survey")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(survey_id) from survey
                 where ss_id = %s
                 order by survey_id"""

        cur.execute(sql, (super_survey_id,))
        rowcount = cur.rowcount

        if rowcount > 0:
            results = cur.fetchall()

            for result in results:
                survey_id = result[0]

                survey = ABSurveyByBoundingBox(config, survey_id)
                survey.search(config.FLAGS_ADD)

    except Exception:
        logging.error("Failed to restart super survey")
        raise


def continue_super_survey_by_sublocality(config, ss_id):
    try:
        rowcount = -1
        logging.info("Continue super survey")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(sublocality) from room where sublocality >
                ( select survey_description from survey where ss_id = 33
                  group by survey_id, survey_description
                  order by survey_id desc limit 1
                ) order by sublocality"""

        cur.execute(sql, (ss_id,))
        rowcount = cur.rowcount

        if rowcount > 0:
            results = cur.fetchall()

            for result in results:
                sublocality = result[0]
                logging.info("\nSearch by %s", sublocality)
                survey_id = db_add_survey(config, sublocality + ", Ouro Preto")
                # update inserting super_survey_id
                sql = """UPDATE survey set ss_id = %s where survey_id = %s"""
                cur.execute(sql, (ss_id, survey_id))

                survey = ABSurveyByBoundingBox(config, survey_id)
                survey.search(config.FLAGS_ADD)

    except Exception:
        logging.error("Failed to continue super survey")
        raise


def continue_super_survey_by_route(config, super_survey_id):
    try:
        rowcount = -1
        logging.info("Initializing survey by routes")
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(route) from room where city = 'Ouro Preto' and route >
                ( select survey_description from survey where ss_id = %s
                  group by survey_id, survey_description
                  order by survey_id desc limit 1
                ) order by route"""

        cur.execute(sql, (super_survey_id,))
        rowcount = cur.rowcount

        if ( True or (rowcount > 0)):
            # print(rowcount, " results")
            # results = cur.fetchall()
            # print(results)

            results = ['Centro, Ouro Preto', 'Cabeças, Ouro Preto']

            for result in results:
                route = result
                # print(route)
                logging.info("Search by %s", route)
                survey_id = db_add_survey(config,
                                          route)
                
                # update inserting super_survey_id
                sql = """UPDATE survey set ss_id = %s where survey_id = %s"""
                cur.execute(sql, (super_survey_id, survey_id))

                survey = ABSurveyByBoundingBox(config, survey_id)
                survey.search(config.FLAGS_ADD)

    except Exception:
        logging.error("Failed to continue super survey")
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


def full_survey(ab_config, area, areaJaExistente, buscaIsolada):
    # areaJaExistente = False
    # buscaIsolada = False
    # if not verify_existent_search_area(ab_config, area):
    #     bounding_box = BoundingBox.from_geopy(ab_config, area)
    #     bounding_box.add_search_area(ab_config, area)

    # survey_id = db_add_survey(ab_config,
    #                           area)

    # buscaIsolada = True
    # print("sid", survey_id)
    # if buscaIsolada:  # sb
    #     survey = ABSurveyByBoundingBox(ab_config, survey_id)
    #     print("fazendo survey")
    #     print(survey.bounding_box)
    #     survey.search(ab_config.FLAGS_ADD)
    # else:  # sbr
    #     search_routes_by_bounding_box(ab_config, area)

    fill_search(ab_config, area, None)
    # update_routes_geolocation(ab_config, area)
    # logging.info("Pronto! Pesquisa finalizada!")


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
    group.add_argument('-asv', '--add_survey',
                       metavar='search_area', type=str,
                       help="""add a survey entry to the database,
                       for search_area""")
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
    group.add_argument('-psa', '--printsearcharea',
                       metavar='search_area', action='store', default=False,
                       help="""print the name and neighborhoods for
                       search area (city) from the Airbnb web site""")
    group.add_argument('-pr', '--printroom',
                       metavar='room_id', type=int,
                       help="""print room_id information
                       from the Airbnb web site""")
    group.add_argument('-ps', '--printsearch',
                       metavar='survey_id', type=int,
                       help="""print first page of search information
                       for survey from the Airbnb web site""")
    group.add_argument('-psn', '--printsearch_by_neighborhood',
                       metavar='survey_id', type=int,
                       help="""print first page of search information
                       for survey from the Airbnb web site,
                       by neighborhood""")
    group.add_argument('-psz', '--printsearch_by_zipcode',
                       metavar='survey_id', type=int,
                       help="""print first page of search information
                       for survey from the Airbnb web site,
                       by zipcode""")
    group.add_argument('-psb', '--printsearch_by_bounding_box',
                       metavar='survey_id', type=int,
                       help="""print first page of search information
                       for survey from the Airbnb web site,
                       by bounding_box""")
    group.add_argument('-s', '--search',
                       metavar='survey_id', type=int,
                       help="""search for rooms using survey survey_id (NO
                       LONGER SUPPORTED)""")
    group.add_argument('-sb', '--search_by_bounding_box',
                       metavar='survey_id', type=int,
                       help="""search for rooms using survey survey_id,
                       by bounding box
                       """)
    group.add_argument('-asb', '--add_and_search_by_bounding_box',
                       metavar='search_area', type=str,
                       help="""add a survey for search_area and search ,
                       by bounding box
                       """)
    group.add_argument('-ur', '--update_routes',
                       metavar='city_name', type=str,
                       help="""update routes from rooms""")  # by victor
    group.add_argument('-sbs', '--search_sublocalities_by_bounding_box',
                       metavar='city_name', type=str,
                       help="""bounding box search from sublocalities""")
    group.add_argument('-sbr', '--search_routes_by_bounding_box',
                       metavar='city_name', type=str,
                       help="""bounding box search from routes""")
    group.add_argument('-sr', '--search_reviews',
                       metavar='survey_id', type=int,
                       help="""search reviews from a survey""")
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
    group.add_argument('-V', '--version',
                       action='version',
                       version='%(prog)s, version ' +
                       str(SCRIPT_VERSION_NUMBER))
    group.add_argument('-?', action='help')

    args = parser.parse_args()
    return (parser, args)


def full_process(ab_config, search_area_name):
    # create/insert in database search area with coordinates
    bounding_box = BoundingBox.from_geopy(ab_config, search_area_name)
    bounding_box.add_search_area(ab_config, search_area_name)

    # initialize new survey
    survey_id = db_add_survey(ab_config, search_area_name)
    survey = ABSurveyByBoundingBox(ab_config, survey_id)

    # search for the listings
    survey.search(ab_config.FLAGS_ADD)

    fill_search(ab_config, search_area_name, None)
    update_routes_geolocation(ab_config, search_area_name)

def main():
    """
    Main entry point for the program.
    """
    (parser, args) = parse_args()
    logging.basicConfig(
        format='%(levelname)-8s%(message)s', level=logging.INFO)
    ab_config = ABConfig(args)
    
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
            # db_add_search_area(ab_config, args.addsearcharea, ab_config.FLAGS_ADD) # tom slee version
        elif args.add_survey:
            db_add_survey(ab_config, args.add_survey)
        elif args.dbping:
            db_ping(ab_config)
        elif args.update_routes:
            update_routes_geolocation(ab_config, args.update_routes)
            # update_cities(ab_config, args.update_routes)
        elif args.search_sublocalities_by_bounding_box:
            search_sublocalities_by_bounding_box(
                ab_config, args.search_sublocalities_by_bounding_box)
        elif args.search_routes_by_bounding_box:
            search_routes_by_bounding_box(
                ab_config, args.search_routes_by_bounding_box)
        elif args.search_reviews:
            search_reviews(ab_config, args.search_reviews)
        elif args.restart_super_survey:
            restart_super_survey(ab_config, args.restart_super_survey)
        elif args.continue_super_survey_by_route:
            continue_super_survey_by_route(
                ab_config, args.continue_super_survey_by_route)
        elif args.continue_super_survey_by_sublocality:
            continue_super_survey_by_sublocality(
                ab_config, args.continue_super_survey_by_sublocality)
        elif args.full_survey:
            full_process(ab_config, args.full_survey)
        else:
            parser.print_help()
    except (SystemExit, KeyboardInterrupt):
        sys.exit()
    except Exception:
        logging.exception("Top level exception handler: quitting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
