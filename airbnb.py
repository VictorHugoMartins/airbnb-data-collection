#!/usr/bin/python3
# ============================================================================
# Airbnb web site scraper, for analysis of Airbnb listings
# Tom Slee, 2013--2015.
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
import argparse
import sys
import time
import webbrowser
from lxml import html
import psycopg2
import psycopg2.errorcodes
from airbnb_config import ABConfig
from airbnb_survey import ABSurveyByBoundingBox
from airbnb_survey import ABSurveyByNeighborhood, ABSurveyByZipcode
from airbnb_listing import ABListing
from airbnb_geocoding import BoundingBox
from airbnb_geocoding import Location
import airbnb_ws
from geopy import distance

# ============================================================================
# CONSTANTS
# ============================================================================

# Script version
# 4.0 April 2020: Beginning of Victor Hugo's code changes, adapting the previously
# developed work for UFOP research
# 3.6 May 2019: Fixed problem where pagination was wrong because of a change in 
# the Airbnb web site.
# 3.5 July 2018: Added column to room table for rounded-off latitude and
# longitude, and additional location table for Google reverse geocode addresses
# 3.4 June 2018: Minor tweaks, but now know that Airbnb searches do not return
#                listings for which there are no available dates.
# 3.3 April 2018: Changed to use /api/ for -sb if key provided in config file
# 3.2 April 2018: fix for modified Airbnb site. Avoided loops over room types
#                 in -sb
# 3.1 provides more efficient "-sb" searches, avoiding loops over guests and
# prices. See example.config for details, and set a large max_zoom (eg 12).
# 3.0 modified -sb searches to reflect new Airbnb web site design (Jan 2018)
# 2.9 adds resume for bounding box searches. Requires new schema
# 2.8 makes different searches subclasses of ABSurvey
# 2.7 factors the Survey and Listing objects into their own modules
# 2.6 adds a bounding box search
# 2.5 is a bit of a rewrite: classes for ABListing and ABSurvey, and requests lib
# 2.3 released Jan 12, 2015, to handle a web site update
SCRIPT_VERSION_NUMBER = "4.0"
# logging = logging.getLogger()

def list_search_area_info(config, search_area):
    """
    Print a list of the search areas in the database to stdout.
    """
    try:
        conn = config.connect()
        cur = conn.cursor()
        cur.execute("""
                select search_area_id
                from search_area where name=%s
                """, (search_area,))
        result_set = cur.fetchall()
        cur.close()
        count = len(result_set)
        if count == 1:
            print("\nThere is one search area called",
                  str(search_area),
                  "in the database.")
        elif count > 1:
            print("\nThere are", str(count),
                  "cities called", str(search_area),
                  "in the database.")
        elif count < 1:
            print("\nThere are no cities called",
                  str(search_area),
                  "in the database.")
            sys.exit()
        sql_neighborhood = """select count(*) from neighborhood
        where search_area_id = %s"""
        sql_search_area = """select count(*) from search_area
        where search_area_id = %s"""
        for result in result_set:
            search_area_id = result[0]
            cur = conn.cursor()
            cur.execute(sql_neighborhood, (search_area_id,))
            count = cur.fetchone()[0]
            cur.close()
            print("\t" + str(count) + " neighborhoods.")
            cur = conn.cursor()
            cur.execute(sql_search_area, (search_area_id,))
            count = cur.fetchone()[0]
            cur.close()
            print("\t" + str(count) + " Airbnb cities.")
    except psycopg2.Error as pge:
        logging.error(pge.pgerror)
        logging.error("Error code %s", pge.pgcode)
        logging.error("Diagnostics %s", pge.diag.message_primary)
        cur.close()
        conn.rollback()
        raise
    except Exception:
        logging.error("Failed to list search area info")
        raise


def list_surveys(config):
    """
    Print a list of the surveys in the database to stdout.
    """
    try:
        conn = config.connect()
        cur = conn.cursor()
        cur.execute("""
            select survey_id, to_char(survey_date, 'YYYY-Mon-DD'),
                    survey_description, search_area_id, status
            from survey
            where survey_date is not null
            and status is not null
            and survey_description is not null
            order by survey_id asc""")
        result_set = cur.fetchall()
        if result_set:
            template = "| {0:3} | {1:>12} | {2:>50} | {3:3} | {4:3} |"
            print (template.format("ID", "Date", "Description", "SA", "status"))
            for survey in result_set:
                (survey_id, survey_date, desc, sa_id, status) = survey
                print(template.format(survey_id, survey_date, desc, sa_id, status))
    except Exception:
        logging.error("Cannot list surveys.")
        raise


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


def db_delete_survey(config, survey_id):
    """
    Delete the listings and progress for a survey from the database.
    Set the survey to "incomplete" in the survey table.
    """
    question = "Are you sure you want to delete listings for survey {}? [y/N] ".format(survey_id)
    sys.stdout.write(question)
    choice = input().lower()
    if choice != "y":
        print("Cancelling the request.")
        return
    try:
        conn = config.connect()
        cur = conn.cursor()
        # Delete the listings from the room table
        sql = """
        delete from room where survey_id = %s
        """
        cur.execute(sql, (survey_id,))
        print("{} listings deleted from 'room' table".format(cur.rowcount))

        # Delete the entry from the progress log table
        sql = """
        delete from survey_progress_log_bb where survey_id = %s
        """
        cur.execute(sql, (survey_id,))
        # No need to report: it's just a log table

        # Update the survey entry
        sql = """
        update survey
        set status = 0, survey_date = NULL
        where survey_id = %s
        """
        cur.execute(sql, (survey_id,))
        if cur.rowcount == 1:
            print("Survey entry updated")
        else:
            print("Warning: {} survey entries updated".format(cur.rowcount))
        conn.commit()
        cur.close()
    except Exception:
        logging.error("Failed to delete survey for %s", survey_id)
        raise

    pass


def db_get_room_to_fill(config, survey_id):
    """
    For "fill" runs (loops over room pages), choose a random room that has
    not yet been visited in this "fill".
    """
    for attempt in range(config.MAX_CONNECTION_ATTEMPTS):
        try:
            conn = config.connect()
            cur = conn.cursor()
            if survey_id == 0:  # no survey specified
                sql = """
                    select room_id, survey_id
                    from room
                    where deleted is null
                    order by random()
                    limit 1
                    """
                cur.execute(sql)
            else:
                sql = """
                    select room_id, survey_id
                    from room
                    where deleted is null
                    and survey_id = %s
                    order by random()
                    limit 1
                    """
                cur.execute(sql, (survey_id,))
            (room_id, survey_id) = cur.fetchone()
            listing = ABListing(config, room_id, survey_id)
            cur.close()
            conn.commit()
            return listing
        except TypeError:
            logging.info("Finishing: no unfilled rooms in database --")
            conn.rollback()
            del config.connection
            return None
        except Exception:
            logging.exception("Error retrieving room to fill from db")
            conn.rollback()
            del config.connection
    return None


def db_add_search_area(config, search_area, flag): # version of tom slee
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
        print("I use coordinates from http://www.mapdevelopers.com/geocode_bounding_box.php.")
        print("The update statement to use is:")
        print("\n\tUPDATE search_area")
        print("\tSET bb_n_lat = ?, bb_s_lat = ?, bb_e_lng = ?, bb_w_lng = ?")
        print("\tWHERE search_area_id = {}".format(search_area_id))
        print("\nThis program does not provide a way to do this update automatically.")
               
    except Exception:
        print("Error adding search area to database")
        raise


def display_room(config, room_id):
    """
    Open a web browser and show the listing page for a room.
    """
    webbrowser.open(config.URL_ROOM_ROOT + str(room_id))


def display_host(config, host_id):
    """
    Open a web browser and show the user page for a host.
    """
    webbrowser.open(config.URL_HOST_ROOT + str(host_id))


def fill_loop_by_room(config, survey_id):
    """
    Master routine for looping over rooms (after a search)
    to fill in the properties.
    """
    room_count = 0
    while room_count < config.FILL_MAX_ROOM_COUNT:
        try:
            if not config.HTTP_PROXY_LIST:
                logging.info(
                    "No proxies left: re-initialize after %s seconds",
                    config.RE_INIT_SLEEP_TIME)
                time.sleep(config.RE_INIT_SLEEP_TIME)  # be nice
                config = ABConfig()
            room_count += 1
            listing = db_get_room_to_fill(config, survey_id)
            if listing is None:
                return None
            else:
                if listing.ws_get_room_info(config.FLAGS_ADD):
                    pass
                else:  # Airbnb now seems to return nothing if a room has gone
                    listing.save_as_deleted()
        except AttributeError:
            logging.error("Attribute error: marking room as deleted.")
            listing.save_as_deleted()
        except Exception as e:
            logging.error("Error in fill_loop_by_room: %s", str(type(e)))
            raise


def search_sublocaties_by_bounding_box(config, city):
    try:
        rowcount = -1
        logging.info("Initializing search by sublocalities")
        conn = config.connect()
        cur = conn.cursor()


        """SELECT distinct(search_area.name) from search_area, room
            where room.city = 'Ouro Preto' and search_area.name = concat(room.sublocality, ', ', room.city) 
            order by search_area.name"""

        """os q n existem SELECT distinct(sublocality) from search_area, room
        where room.city = 'Ouro Preto'
        and concat(room.sublocality, ', ', room.city) not in ( select name from search_area where strpos(name, 'Ouro Preto') <> 0 )
        order by sublocality"""
        ''' for result in results insere em search_area e faz a busca AAAAAAA NAO SEI'''
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


def update_routes(config):
    try:
            conn = config.connect()
            cur = conn.cursor()

            sql = """SELECT room_id, latitude, longitude from room
                    where route is not null and sublocality is  null and city = 'Ouro Preto'
                    order by route""" # os q precisa atualizar
            cur.execute(sql)
            routes = cur.fetchall()

            sql = """SELECT room_id, latitude, longitude, sublocality from room
                    where route is not null and sublocality is not null and city = 'Ouro Preto'
                    order by route""" # nenhum dos 2 é nulo
            cur.execute(sql)
            results = cur.fetchall()
            print(str(cur.rowcount) + "routes")

            for result in results:
                room_id = result[0]
                lat = result[1]
                lng = result[2]
                sublocality = result[3]

                for route in routes:
                    room_id = route[0]
                    latitude = route[1]
                    longitude = route[2]
                    if is_inside(latitude, longitude, lat, lng):
                        sql = """UPDATE room set sublocality = %s
                                where room_id = %s"""
                        update_args = (
                            sublocality, room_id
                            )
                        cur.execute(sql, update_args)
                        rowcount = cur.rowcount
                        conn.commit()
                        break
                
            exit(0)
    except:
        raise


def is_inside(lat_center, lng_center, lat_test, lng_test):
    center_point = [{'lat': lat_center, 'lng': lng_center}]
    test_point = [{'lat': lat_test, 'lng': lng_test}]

    for radius in range(100):
        center_point_tuple = tuple(center_point[0].values()) # (-7.7940023, 110.3656535)
        test_point_tuple = tuple(test_point[0].values()) # (-7.79457, 110.36563)

        dis = distance.distance(center_point_tuple, test_point_tuple).km
        
        if dis <= radius:
            print("{} point is inside the {} km radius from {} coordinate".format(test_point_tuple, radius/1000, center_point_tuple))
            return True
    return False


def search_routes_by_bounding_box(config, city):
    try:
        rowcount = -1
        logging.info("Initializing search by routes")
        conn = config.connect()
        cur = conn.cursor()


        sql = """SELECT distinct(search_area.name) from search_area, route
                where search_area.name = concat(route.name, ', ', city)
                and city = %s
                and bb_n_lat <> -20.3699597
                and bb_e_lng <> -43.4719237
                and bb_s_lat <> -20.4126148
                and bb_w_lng <> -43.5313676
                order by search_area.name asc"""

        cur.execute(sql, (city,))
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
                sql = """UPDATE survey set ss_id = 22 where survey_id = %s"""
                cur.execute(sql, ( survey_id,))

                survey = ABSurveyByBoundingBox(config, survey_id)
                survey.search(config.FLAGS_ADD)

                if name == "Rua Grupiara, Ouro Preto":
                    exit(0)

    except Exception:
        logging.error("Failed to search from sublocalities")
        raise


def search_reviews(config, survey_id):
    try:
        rowcount = -1
        logging.info("Initializing search by reviews")
        conn = config.connect()
        cur = conn.cursor()


        sql = """select room_id, survey_id from room where survey_id  in ( select survey_id from survey where ss_id = %s ) order by room_id"""

        cur.execute(sql, (survey_id,))
        rowcount = cur.rowcount

        if rowcount > 0:
            results = cur.fetchall()
            
            for result in results:
                room_id = result[0]
                listing = ABListing(config, room_id, survey_id)

                ''' The page must obey a certain structure to return the comment data,
                I defined the limit of attempts to find that page "complete" before moving on to the next room '''
                for i in range(config.MAX_CONNECTION_ATTEMPTS):
                    logging.info("Attempt {i}: searching for room {r}".format(i=i+1, r=room_id)) 
                    if listing.get_comments():
                        break

    except Exception:
        logging.error("Failed to search reviews")
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


        sql = """SELECT distinct(sublocality) from room where city = 'Ouro Preto' and sublocality >
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
                ( select survey_description from survey where ss_id = 33
                  group by survey_id, survey_description
                  order by survey_id desc limit 1
                ) order by route"""

        cur.execute(sql, (super_survey_id,))
        rowcount = cur.rowcount

        if rowcount > 0:
            results = cur.fetchall()
            
            for result in results:
                route = result[0]
                logging.info("Search by %s", route)
                survey_id = db_add_survey(config,
                                          route)
                # update inserting super_survey_id
                sql = """UPDATE survey set ss_id = %s where survey_id = %s"""
                cur.execute(sql, (ss_id, survey_id))

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

def update_db_search_area():
    # sql distinct(city), state for result insere (MAS PRA FAZER ISSO TEM Q INSERIR ESTADO NO ROOM)
    # faz isso com sublocality, city e depois pra route, sublocality
    # if sublocality is not None and route is not None: insere
    return


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
    group.add_argument('-sn', '--search_by_neighborhood',
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
    group.add_argument('-sz', '--search_by_zipcode',
                       metavar='survey_id', type=int,
                       help="""search for rooms using survey_id,
                       by zipcode (NO LONGER SUPPORTED)""")
    group.add_argument('-uc', '--update_cities',
                       metavar='city_name', type=str,
                       help="""update cities from a room""") # by victor
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
    logging.basicConfig(format='%(levelname)-8s%(message)s')
    ab_config = ABConfig(args)

    try:
        if args.search:
            survey = ABSurveyByNeighborhood(ab_config, args.search)
            survey.search(ab_config.FLAGS_ADD)
        elif args.search_by_neighborhood:
            survey = ABSurveyByNeighborhood(ab_config, args.search_by_neighborhood)
            survey.search(ab_config.FLAGS_ADD)
        elif args.search_by_zipcode:
            survey = ABSurveyByZipcode(ab_config, args.search_by_zipcode)
            survey.search(ab_config.FLAGS_ADD)
        elif args.search_by_bounding_box:
            survey = ABSurveyByBoundingBox(ab_config, args.search_by_bounding_box)
            survey.search(ab_config.FLAGS_ADD)
        elif args.add_and_search_by_bounding_box:
            survey_id = db_add_survey(ab_config,
                                      args.add_and_search_by_bounding_box)
            survey = ABSurveyByBoundingBox(ab_config, survey_id)
            survey.search(ab_config.FLAGS_ADD)
        elif args.fill is not None:
            fill_loop_by_room(ab_config, args.fill)
        elif args.addsearcharea:
            bounding_box = BoundingBox.from_google(ab_config, args.addsearcharea)
            bounding_box.add_search_area(ab_config, args.addsearcharea)
            # db_add_search_area(ab_config, args.addsearcharea, ab_config.FLAGS_ADD) # tom slee version
        elif args.add_survey:
            db_add_survey(ab_config, args.add_survey)
        elif args.dbping:
            db_ping(ab_config)
        elif args.delete_survey:
            db_delete_survey(ab_config, args.delete_survey)
        elif args.displayhost:
            display_host(ab_config, args.displayhost)
        elif args.displayroom:
            display_room(ab_config, args.displayroom)
        elif args.listsearcharea:
            list_search_area_info(ab_config, args.listsearcharea)
        elif args.listroom:
            listing = ABListing(ab_config, args.listroom, None)
            listing.print_from_db()
        elif args.listsurveys:
            list_surveys(ab_config)
        elif args.printsearcharea:
            ws_get_city_info(ab_config, args.printsearcharea, ab_config.FLAGS_PRINT)
        elif args.printroom:
            listing = ABListing(ab_config, args.printroom, None)
            listing.get_room_info_from_web_site(ab_config.FLAGS_PRINT)
        elif args.printsearch:
            survey = ABSurveyByNeighborhood(ab_config, args.printsearch)
            survey.search(ab_config.FLAGS_PRINT)
        elif args.printsearch_by_neighborhood:
            survey = ABSurveyByNeighborhood(ab_config, args.printsearch_by_neighborhood)
            survey.search(ab_config.FLAGS_PRINT)
        elif args.printsearch_by_bounding_box:
            survey = ABSurveyByBoundingBox(ab_config, args.printsearch_by_bounding_box)
            survey.search(ab_config.FLAGS_PRINT)
        elif args.printsearch_by_zipcode:
            survey = ABSurveyByZipcode(ab_config, args.printsearch_by_zipcode)
            survey.search(ab_config.FLAGS_PRINT)
        elif args.update_cities:
            update_city(ab_config, args.update_cities)
        elif args.search_sublocalities_by_bounding_box:
            search_sublocaties_by_bounding_box(ab_config, args.search_sublocalities)
        elif args.search_routes_by_bounding_box:
            search_routes_by_bounding_box(ab_config, args.search_routes_by_bounding_box)
        elif args.search_reviews:
            search_reviews(ab_config, args.search_reviews)
        elif args.restart_super_survey:
            restart_super_survey(ab_config, args.restart_super_survey)
        elif args.continue_super_survey_by_route:
            continue_super_survey_by_route(ab_config, args.continue_super_survey_by_route)
        elif args.continue_super_survey_by_sublocality:
            continue_super_survey_by_sublocality(ab_config, args.continue_super_survey_by_sublocality)
        else:
            parser.print_help()
    except (SystemExit, KeyboardInterrupt):
        sys.exit()
    except Exception:
        logging.exception("Top level exception handler: quitting.")
        sys.exit(0)


if __name__ == "__main__":
    main()

# > sao tomé