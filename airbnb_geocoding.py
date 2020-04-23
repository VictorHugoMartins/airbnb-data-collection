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
import os

FORMAT_STRING = "%(asctime)-15s %(levelname)-8s%(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT_STRING)
LOGGER = logging.getLogger()
STRING_NA = "N/A"

# Suppress informational logging from requests module
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class Location():

    def __init__(self, lat_round, lng_round):
        self.id = None
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


    def insert_in_table_location(self, config):
        """
        Insert or update a location with the required address information
        """
        try:
            logging.info("Adding location to database")
            conn = config.connect()
            cur = conn.cursor()
            
            # check if it exists
            cur.execute("""
                select location_id from location where sublocality = %s
            """, (self.sublocality,))
            ( self.id ) = cur.fetchone()
            
            if cur.fetchone() is not None:
                print("Location {} already exists".format(self.id))
                return self.id

            sql = """
            SELECT max(location_id) from location limit 1"""
            cur.execute(sql)
            result = cur.fetchall()
            self.id = result[0][0]

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
            update_args = (self.id,
                           self.neighborhood,
                           self.sublocality,
                           self.locality,
                           self.level2,
                           self.level1,
                           self.country,
                           self.lat_round,
                           self.lng_round,
                          )
            print("DDDDDDDDDDDD")
            LOGGER.debug(update_args)
            cur.execute(sql, update_args)
            cur.close()
            conn.commit()
            print("Location ", self.id, " inserted")
            
            return self.id
        except:
            LOGGER.exception("Exception in update_location")
            raise


    def reverse_geocode(self, config):
        """
        Return address information from the Google API as a Location object for a given lat lng
        """
        gmaps = googlemaps.Client(key=config.GOOGLE_API_KEY)
        # Look up an address with reverse geocoding
        # lat = 41.782
        # lng = -72.693

        results = gmaps.reverse_geocode((self.lat_round, self.lng_round))

        # Parsing the result is described at
        # https://developers.google.com/maps/documentation/geocoding/web-service-best-practices#ParsingJSON

        json_file = open("geocode.json", mode="w", encoding="utf-8")
        json_file.write(json.dumps(results, indent=4, sort_keys=True))
        json_file.close()
        #  In practice, you may wish to only return the first result (results[0])

        if (len(results)) > 0:
            for result in results:
                if (self.neighborhood != STRING_NA and
                        self.sublocality != STRING_NA and
                        self.locality != STRING_NA and
                        self.level2 != STRING_NA and
                        self.level1 != STRING_NA and
                        self.country != STRING_NA):
                    break
                address_components = result['address_components']
                for address_component in address_components:
                    if (self.neighborhood == STRING_NA
                        and "neighborhood" in address_component["types"]):
                        self.neighborhood = address_component["long_name"]
                    elif (self.sublocality == STRING_NA
                          and "sublocality" in address_component["types"]):
                        self.sublocality = address_component["long_name"]
                    elif (self.locality == STRING_NA
                          and "locality" in address_component["types"]):
                        self.locality = address_component["long_name"]
                    elif (self.level2 == STRING_NA
                          and "administrative_area_level_2" in
                          address_component["types"]):
                        self.level2 = address_component["long_name"]
                    elif (self.level1 == STRING_NA
                          and "administrative_area_level_1" in
                          address_component["types"]):
                        self.level1 = address_component["long_name"]
                    elif (self.country == STRING_NA
                          and "country" in address_component["types"]):
                        self.country = address_component["long_name"]


        os.remove('geocode.json')

        print(self.neighborhood)
        print(self.sublocality)
        print(self.locality)
        print(self.level2)
        print(self.level1)
        print(self.country)


    def insert_in_search_area(self, config):
        country_id = insert_country(self, config)
        level1_id = insert_level1(config, self.level1, country_id, self.country)
        level2_id = insert_level2(config, self.level2, level1_id, self.level1)
        insert_sublocality(config, self.sublocality, level2_id, self.level2)
        print("Room inserted")


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
            print(results)
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


    def add_search_area(self, config, search_area):
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
                print("Area already exists: {}".format(search_area))
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
                self.bb_n_lat,
                self.bb_e_lng,
                self.bb_s_lat,
                self.bb_w_lng))
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


def insert_country(location, config):
    """
    Insert or update a location with the required address information
    """
    try:
        logging.info("Adding country to database")
        conn = config.connect()
        cur = conn.cursor()
        # check if it exists
        sql = """ SELECT country_id from country where country_name = %s """
        cur.execute(sql, (location.country,))
        ( country_id ) = cur.fetchone()
        if cur.fetchone() is not None:
            print("Country {} already exists".format(country_id+1))
            return country_id

        sql = """ SELECT max(country_id) from country limit 1"""
        cur.execute(sql)
        result = cur.fetchall()

        country_id = result[0][0]

        if country_id is None:
            country_id = 0

        sql = """ INSERT into country(country_id, country_name) VALUES (%s+1, %s) """
        insert_args = (country_id, location.country)
        LOGGER.debug(insert_args)
        cur.execute(sql, insert_args)
        cur.close()
        conn.commit()
        print("Country ", country_id+1, " inserted")

        # insert sublocality in the list of search areas
        bounding_box = BoundingBox.from_google(config, location.country)
        bounding_box.add_search_area(config, location.country)
        
        return country_id
    except:
        LOGGER.exception("Exception in insert_country")
        raise


def insert_level1(config, level1, country_id, country):
    """
    Insert or update a location with the required address information
    """
    try:
        logging.info("Adding level1 to database")
        conn = config.connect()
        cur = conn.cursor()

        name = level1 + ", " + country

        # check if it exists
        sql = """ SELECT level1_id from level1 where level1_name = %s """
        cur.execute(sql, (name,))
        ( level1_id ) = cur.fetchone()
        if cur.fetchone() is not None:
            print("Level1 {} already exists".format(level1_id+1))
            return level1_id

        sql = """ SELECT max(level1_id) from level1 limit 1"""
        cur.execute(sql)
        result = cur.fetchall()

        level1_id = result[0][0]

        if level1_id is None:
            level1_id = 0

        sql = """ INSERT into level1(level1_id, level1_name, country_id) VALUES (%s+1, %s, %s) """
        insert_args = (level1_id, name, country_id)
        LOGGER.debug(insert_args)
        cur.execute(sql, insert_args)
        cur.close()
        conn.commit()
        print("Level1 ", level1_id+1, " inserted")

        # insert sublocality in the list of search areas
        bounding_box = BoundingBox.from_google(config, name)
        bounding_box.add_search_area(config, name) # for example, "Bauxita, Ouro Preto"
        
        return level1_id
    except:
        LOGGER.exception("Exception in insert_level1")
        raise


def insert_level2(config, level2, level1_id, level1):
    """
    Insert or update a location with the required address information
    """
    try:
        logging.info("Adding level2 to database")
        conn = config.connect()
        cur = conn.cursor()

        name = level2 + ", " + level1

        # check if it exists
        sql = """ SELECT level2_id from level2 where level2_name = %s """
        cur.execute(sql, (name,))
        ( level2_id ) = cur.fetchone()
        if cur.fetchone() is not None:
            print("Level2 {} already exists".format(level2_id+1))
            return level2_id

        sql = """ SELECT max(level2_id) from level2 limit 1"""
        cur.execute(sql)
        result = cur.fetchall()

        level2_id = result[0][0]

        if level2_id is None:
            level2_id = 0

        sql = """ INSERT into level2(level2_id, level2_name, level1_id) VALUES (%s+1, %s, %s) """
        insert_args = (level2_id, name, level1_id)
        LOGGER.debug(insert_args)
        cur.execute(sql, insert_args)
        cur.close()
        conn.commit()
        print("Level2 ", level2_id+1, " inserted")

        # insert sublocality in the list of search areas
        bounding_box = BoundingBox.from_google(config, name)
        bounding_box.add_search_area(config, name) # for example, "Bauxita, Ouro Preto"
        
        return level2_id
    except:
        LOGGER.exception("Exception in insert_level2")
        raise


def insert_sublocality(config, sublocality, level2_id, level2):
    """
    Insert or update a location with the required address information
    """
    try:
        logging.info("Adding sublocality to database")
        conn = config.connect()
        cur = conn.cursor()

        name = sublocality + ", " + level2

        # check if it exists
        sql = """ SELECT sublocality_id from sublocality where sublocality_name = %s """
        cur.execute(sql, (name,))
        ( sublocality_id ) = cur.fetchone()
        if cur.fetchone() is not None:
            print("Sublocality {} already exists".format(sublocality_id+1))
            return sublocality_id

        sql = """ SELECT max(sublocality_id) from sublocality limit 1"""
        cur.execute(sql)
        result = cur.fetchall()

        sublocality_id = result[0][0]

        if sublocality_id is None:
            sublocality_id = 0

        sql = """ INSERT into sublocality(sublocality_id, sublocality_name, level2_id) VALUES (%s+1, %s, %s) """
        insert_args = (sublocality_id, name, level2_id)
        LOGGER.debug(insert_args)
        cur.execute(sql, insert_args)
        cur.close()
        conn.commit()
        print("Sublocality ", sublocality_id+1, " inserted")

        # insert sublocality in the list of search areas
        bounding_box = BoundingBox.from_google(config, name)
        bounding_box.add_search_area(config, name) # for example, "Bauxita, Ouro Preto"
        
        return sublocality_id
    except:
        LOGGER.exception("Exception in insert_sublocality")
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
                        help="""search_area""") # para implementar
    parser.add_argument("--lat",
                        metavar="lat", type=float,
                        help="""lat""")
    parser.add_argument("--lng",
                        metavar="lng", type=float,
                        help="""lng""")
    parser.add_argument("--bb_n_lat",
                        metavar="bb_n_lat", type=float,
                        help="""bb_n_lat""") # para implementar
    parser.add_argument("--bb_s_lat",
                        metavar="bb_s_lat", type=float,
                        help="""bb_s_lat""") # para implementar
    parser.add_argument("--bb_e_lng",
                        metavar="bb_e_lng", type=float,
                        help="""bb_e_lng""") # para implementar
    parser.add_argument("--bb_w_lng",
                        metavar="bb_w_lng", type=float,
                        help="""bb_w_lng""") # para implementar
    parser.add_argument("--count",
                        metavar="count", type=int,
                        help="""number_of_lookups""") # para implementar
    parser.add_argument("--update",
                        metavar="update", type=int,
                        help="""update locations from search area""")
    parser.add_argument("--insert",
                        metavar="insert", type=str,
                        help="""insert search area""")
    args = parser.parse_args()

    if args.update:
        results = select_rooms(config, args.update)
    elif args.lat and args.lng:
        location = Location(args.lat, args.lng)
        location.reverse_geocode(location)
        location.insert_in_table_location(config)
    elif args.insert:
        bounding_box = BoundingBox.from_google(config, args.insert)
        LOGGER.info("Bounding box for %s from Google = (%s, %s, %s, %s)",
                    args.insert,
                    bounding_box.bb_s_lat, bounding_box.bb_n_lat,
                    bounding_box.bb_w_lng, bounding_box.bb_e_lng)
        bounding_box.add_search_area(config, args.insert)
    '''elif args.sa:
        bounding_box = BoundingBox.from_google(config, args.sa)
        LOGGER.info("Bounding box for %s from Google = (%s, %s, %s, %s)",
                    args.sa,
                    bounding_box.bb_s_lat, bounding_box.bb_n_lat,
                    bounding_box.bb_w_lng, bounding_box.bb_e_lng)
        update_location(config, args.sa, bounding_box) '''

if __name__ == "__main__":
    main()

# notes by victor: add loggers