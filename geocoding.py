#! /usr/bin/python3
"""
Reverse geocoding
"""

import googlemaps
import argparse
import json
from airbnb_config import ABConfig
import sys
import logging

FORMAT_STRING = "%(asctime)-15s %(levelname)-8s%(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT_STRING)
LOGGER = logging.getLogger()
STRING_NA = "N/A"

# Suppress informational logging from requests module
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class Location():

    def __init__(self, lat_round, lng_round):
        self.lat_round = lat_round
        self.lng_round = lng_round
        self.neighborhood = STRING_NA
        self.sublocality = STRING_NA
        self.locality = STRING_NA
        self.level2 = STRING_NA
        self.level1 = STRING_NA
        self.country = STRING_NA

    @classmethod
    def from_db(cls, lat_round, lng_round):
        """
        Get a location (address etc) by reading from the database
        """
        return cls(lat_round, lng_round)


class BoundingBox():
    """
    Get max and min lat and long for a search area
    """

    def __init__(self, bounding_box):
        (self.bb_s_lat,
         self.bb_n_lat,
         self.bb_w_lng,
         self.bb_e_lng) = bounding_box

    @classmethod
    def from_db(cls, config, search_area):
        """
        Get a bounding box from the database by reading the search_area.name
        """
        try:
            cls.search_area = search_area
            conn = config.connect()
            cur = conn.cursor()
            sql = """
            SELECT bb_s_lat, bb_n_lat, bb_w_lng, bb_e_lng
            FROM search_area
            WHERE name = %s
            """
            cur.execute(sql, (search_area,))
            bounding_box = cur.fetchone()
            cur.close()
            return cls(bounding_box)
        except:
            LOGGER.exception("Exception in BoundingBox_from_db: exiting")
            sys.exit()

    @classmethod
    def from_google(cls, config, search_area):
        """
        Get a bounding box from Google
        """
        try:
            gmaps = googlemaps.Client(key=config.GOOGLE_API_KEY)
            results = gmaps.geocode((search_area))
            bounds = results[0]["geometry"]["bounds"]
            bounding_box = (bounds["southwest"]["lat"],
                            bounds["northeast"]["lat"],
                            bounds["southwest"]["lng"],
                            bounds["northeast"]["lng"],)
            return cls(bounding_box)
        except:
            LOGGER.exception("Exception in BoundingBox_from_google: exiting")
            sys.exit()

    @classmethod
    def from_args(cls, config, args):
        """
        Get a bounding box from the command line
        """
        try:
            bounding_box = (args.bb_s_lat, args.bb_n_lat,
                            args.bb_w_lng, args.bb_e_lng)
            return cls(bounding_box)
        except:
            LOGGER.exception("Exception in BoundingBox_from_args: exiting")
            sys.exit()


def select_country(config, country):
    """ Update a room in the database. Raise an error if it fails.
    Return number of rows affected."""
    try:
        rowcount = 0
        conn = config.connect()
        cur = conn.cursor()
        LOGGER.debug("Selecting...")
        cur.execute("""
                select *
                from location where country=%s limit 1
                """, (country,))
        rowcount = cur.rowcount
        if rowcount > 0:
            return True
        else:
            return False
    except:
        # may want to handle connection close errors
        LOGGER.warning("Exception in select: raising")
        raise


def insert_in_table_location(config, location):
    """
    Insert or update a location with the required address information
    """
    try:
        logging.info("Adding location to database")
        conn = config.connect()
        cur = conn.cursor()
        # check if it exists
        sql = """
        select lat_round, lng_round
        from location
        where lat_round = %s and lng_round = %s"""
        cur.execute(sql, (location.lat_round, location.lng_round,))
        if cur.fetchone() is not None:
            print("Location with latitude = {} and longitude = {} already exists".format(location.lat_round, location.lng_round))
            return True

        sql = """
        SELECT max(location_id) from location limit 1"""
        cur.execute(sql)
        result = cur.fetchall()

        location_id = result[0][0]

        sql = """
        INSERT into location(
        location_id,
        neighborhood,
        sublocality,
        locality,
        level2,
        level1,
        country,
        lat_round,
        lng_round)
        VALUES
        (%s+1, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        update_args = (location_id,
                       location.neighborhood,
                       location.sublocality,
                       location.locality,
                       location.level2,
                       location.level1,
                       location.country,
                       location.lat_round,
                       location.lng_round,
                      )
        LOGGER.debug(update_args)
        cur.execute(sql, update_args)
        cur.close()
        conn.commit()
        print("Location ", location_id, " inserted")
        
        return True
    except:
        LOGGER.exception("Exception in update_location")
        return False


def add_search_area(config, search_area, bounding_box):
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
        sql = """insert into search_area (name, abbreviation, bb_n_lat, bb_e_lng, bb_s_lat, bb_w_lng)
        values (%s, %s, %s, %s, %s, %s)"""
        cur.execute(sql, (search_area,
            abbreviation,
            bounding_box.bb_n_lat,
            bounding_box.bb_e_lng,
            bounding_box.bb_s_lat,
            bounding_box.bb_w_lng))
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
               
    except Exception:
        print("Error adding search area to database")
        raise


def reverse_geocode(config, location):
    """
    Return address information from the Google API as a Location object for a given lat lng
    """
    gmaps = googlemaps.Client(key=config.GOOGLE_API_KEY)
    # Look up an address with reverse geocoding
    # lat = 41.782
    # lng = -72.693

    results = gmaps.reverse_geocode((location.lat_round, location.lng_round))

    # Parsing the result is described at
    # https://developers.google.com/maps/documentation/geocoding/web-service-best-practices#ParsingJSON

    json_file = open("geocode.json", mode="w", encoding="utf-8")
    json_file.write(json.dumps(results, indent=4, sort_keys=True))
    json_file.close()
    #  In practice, you may wish to only return the first result (results[0])

    if (len(results)) > 0:
        for result in results:
            if (location.neighborhood != STRING_NA and
                    location.sublocality != STRING_NA and
                    location.locality != STRING_NA and
                    location.level2 != STRING_NA and
                    location.level1 != STRING_NA and
                    location.country != STRING_NA):
                break
            address_components = result['address_components']
            for address_component in address_components:
                if (location.neighborhood == STRING_NA
                    and "neighborhood" in address_component["types"]):
                    location.neighborhood = address_component["long_name"]
                elif (location.sublocality == STRING_NA
                      and "sublocality" in address_component["types"]):
                    location.sublocality = address_component["long_name"]
                elif (location.locality == STRING_NA
                      and "locality" in address_component["types"]):
                    location.locality = address_component["long_name"]
                elif (location.level2 == STRING_NA
                      and "administrative_area_level_2" in
                      address_component["types"]):
                    location.level2 = address_component["long_name"]
                elif (location.level1 == STRING_NA
                      and "administrative_area_level_1" in
                      address_component["types"]):
                    location.level1 = address_component["long_name"]
                elif (location.country == STRING_NA
                      and "country" in address_component["types"]):
                    location.country = address_component["long_name"]


    print(location.neighborhood)
    print(location.sublocality)
    print(location.locality)
    print(location.level2)
    print(location.level1)
    print(location.country)

    return location


def update_location_from_room(config, room_id, survey_id, location):
    """
    Insert or update a location with the required address information
    """

    try:
        conn = config.connect()
        cur = conn.cursor()
        sql = """
        SELECT max(location_id) from location limit 1"""
        cur.execute(sql)
        result = cur.fetchall()

        sql = """
        UPDATE room set
        country = %s,
        city = %s
        where room_id = %s and length(sublocality) < 4
        """ # survey_id condition desnecessary?
        update_args = (location.country,
                       location.level2,
                       room_id
                      )
        LOGGER.debug(update_args)
        cur.execute(sql, update_args)
        cur.close()
        conn.commit()
        print("Room ", room_id, " updated")
    except:
        LOGGER.exception("Exception in update_location")


def gambiarra(config):
    """
    Insert or update a location with the required address information
    """

    try:
        conn = config.connect()
        cur = conn.cursor()
        sql = """
        select lat_round, lng_round from location where length(sublocality) < 5"""
        cur.execute(sql)
        results = cur.fetchall()

        for r in results:
            location = Location(results[0][0], results[0][1]) # initialize a location with coordinates
            reverse_geocode(config, location)
            sql = """
            UPDATE room set
            country = %s,
            city = %s
            where latitude = %s and longitude = %s
            """ # survey_id condition desnecessary?
            update_args = (location.country,
                           location.level2,
                           location.lat_round,
                           location.lng_round
                          )
            cur.execute(sql, update_args)
            sql = """
            delete from location
            where lat_round = %s and lng_round = %s
            """ # survey_id condition desnecessary?
            update_args = (location.lat_round,
                           location.lng_round
                          )
            cur.execute(sql, update_args)
            insert_in_table_location(config, location)
        
        cur.close()
        conn.commit()
        print("feito")
    except:
        LOGGER.exception("Exception in update_location")


def select_rooms(config, survey_id):
    """ Update a room in the database. Raise an error if it fails.
    Return number of rows affected."""
    try:
        rowcount = 0
        conn = config.connect()
        cur = conn.cursor()
        LOGGER.debug("Selecting...")

        # pensar melhor
        cur.execute("""
                SELECT room_id, latitude, longitude
                from room where survey_id = %s
                and ( city is null
                or  country is null )
                and ( latitude is not null
                or  longitude is not null )
                """, (survey_id,))
        result_select = cur.fetchall()

        if (len(result_select)) > 0:
            for result in result_select: # for each room in database
                latitude = result[1]
                longitude = result[2]

                location = Location(latitude, longitude) # initialize a location with coordinates
                reverse_geocode(config, location) # find atributes for location with google api key
                insert_in_table_location(config, location)
                
                room_id = result[0]
                update_location_from_room(config, room_id, survey_id, location)
        else:
            print("No rooms ")        
    except:
        # may want to handle connection close errors
        LOGGER.warning("Exception in select: raising")
        raise


def main():
    """ Controlling routine that calls the others """
    
    config = ABConfig()
    parser = argparse.ArgumentParser(
        description='reverse geocode')
        # usage='%(prog)s [options]')
    # These arguments should be more carefully constructed. Right now there is
    # no defining what is required, and what is optional, and what contradicts
    # what.
    
    parser.add_argument("--sa",
                        metavar="search_area", type=str,
                        help="""search_area""")
    parser.add_argument("--lat",
                        metavar="lat", type=float,
                        help="""lat""")
    parser.add_argument("--lng",
                        metavar="lng", type=float,
                        help="""lng""")
    parser.add_argument("--bb_n_lat",
                        metavar="bb_n_lat", type=float,
                        help="""bb_n_lat""")
    parser.add_argument("--bb_s_lat",
                        metavar="bb_s_lat", type=float,
                        help="""bb_s_lat""")
    parser.add_argument("--bb_e_lng",
                        metavar="bb_e_lng", type=float,
                        help="""bb_e_lng""")
    parser.add_argument("--bb_w_lng",
                        metavar="bb_w_lng", type=float,
                        help="""bb_w_lng""")
    parser.add_argument("--count",
                        metavar="count", type=int,
                        help="""number_of_lookups""")
    parser.add_argument("--update",
                        metavar="update", type=int,
                        help="""update locations from search area""")
    parser.add_argument("--insert",
                        metavar="insert", type=str,
                        help="""update locations from search area""")
    args = parser.parse_args()

    if args.update:
        results = select_rooms(config, args.update)
    elif args.lat and args.lng:
        location = Location(args.lat, args.lng)
        reverse_geocode(config, location)
        exit(0)
        insert_in_table_location(config, location)
    elif args.insert:
        bounding_box = BoundingBox.from_google(config, args.insert)
        LOGGER.info("Bounding box for %s from Google = (%s, %s, %s, %s)",
                    args.insert,
                    bounding_box.bb_s_lat, bounding_box.bb_n_lat,
                    bounding_box.bb_w_lng, bounding_box.bb_e_lng)
        add_search_area(config, args.insert, bounding_box)
        #insert_in_table_location(config, location)

if __name__ == "__main__":
    main()