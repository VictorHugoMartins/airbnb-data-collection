import psycopg2 as pg
import pandas as pd
import argparse
import datetime as dt
import logging
from general_config import ABConfig
import os.path
import os
import csv

LOG_LEVEL = logging.INFO
# Set up logging
LOG_FORMAT = '%(levelname)-8s%(message)s'
logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
DEFAULT_START_DATE = '2020-03-03'

def export_airbnb_room(config, sql_command, city, project, format, start_date):
    try:
        rowcount = -1
        logging.info("Initializing export Airbnb'b rooms for " + city)
        conn = config.connect()
        cur = conn.cursor()
        cnxn = config.connect()
        cur.execute(sql_command)

        # create a directory for all the data for the city
        directory = ('files/').format(project=project)
        if not os.path.isdir(directory): # if directory don't exists, create
            os.mkdir(directory)

        today = today = dt.date.today().isoformat()
        directory = directory + 'airbnb_rooms_{city}_28_04_23.csv'.format(city=city)
        csv_path = directory

        # Busca os resultados da query e salva em um arquivo CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([d[0] for d in cur.description])
            for row in cur:
                writer.writerow(row)

        # Fecha a conexão com o banco de dados
        cur.close()
        conn.close()

        # pd.read_sql(sql,cnxn).to_excel(directory, sheet_name="Total Listings")

        # data = pd.read_excel(directory)
    
        # # update the file inserting the region

        # region = [ define_region(sub, lat, lng) for sub, lat, lng in zip(data['sublocality'], data['latitude'], data['longitude']) ]
        
        # #region = ['Centro' if x in centro else 'Entorno' if x in entorno else 'Distrito' if x in distrito else x for x in data['sublocality']]
        # data.insert(16, "region", region)
        # data = data.drop(columns=['Unnamed: 0']) #, 'host_id', 'room_type'
        # data.to_excel(directory, sheet_name="Total Listings")

        logging.info("Finishing export")

        return directory
    except PermissionError:
        print("Permission denied: ", directory, " is open")
    except Exception:
        logging.error("Failed to export")
        raise

def main():
    parser = \
        argparse.ArgumentParser(
            description="Create a spreadsheet of surveys from a city")
    parser.add_argument("-cfg", "--config_file",
                        metavar="config_file", action="store", default=None,
                        help="""explicitly set configuration file, instead of
                        using the default <username>.config""")
    parser.add_argument('-c', '--city',
                        metavar='city', action='store',
                        help="""set the city""")
    parser.add_argument('-la', '--listings_airbnb',
                        action='store_true', default=False,
                        help="export the listings from airbnb")
    parser.add_argument('-lb', '--listings_booking',
                        action='store_true', default=False,
                        help="export the listings from booking")
    parser.add_argument('-ra', '--reviews_airbnb',
                        action='store_true', default=False,
                        help="export the reviews from airbnb")
    parser.add_argument('-rb', '--reviews_booking',
                        action='store_true', default=False,
                        help="export the reviews from booking")
    parser.add_argument('-p', '--project',
                        metavar='project', action='store', default="public",
                        help="""the project determines the table or view: public
                        for room, gis for listing_city, default public""")
    parser.add_argument('-f', '--format',
                        metavar='format', action='store', default="csv",
                        help="""output format (xlsx or csv), default xlsx""")
    parser.add_argument('-s', '--summary',
                        action='store_true', default=False,
                        help="create a summary spreadsheet instead of raw data")
    parser.add_argument('-sd', '--start_date',
                        metavar="start_date", action='store',
                        default=DEFAULT_START_DATE,
                        help="create a summary spreadsheet instead of raw data")
    args = parser.parse_args()
    ab_config = ABConfig(args)
    export_airbnb_room(ab_config, """
      SELECT
        room_id,
        STRING_AGG(DISTINCT CAST(host_id AS varchar), 'JOIN ') AS host_id,
        STRING_AGG(DISTINCT name, 'JOIN ') AS names,
        STRING_AGG(DISTINCT property_type, 'JOIN ') AS property_types,
        STRING_AGG(DISTINCT room_type, 'JOIN ') AS room_types,
        AVG(price) AS avg_price,
        AVG(minstay) AS avg_minstay,
        AVG(reviews) AS avg_reviews,
        AVG(avg_rating) AS avg_rating,
        AVG(accommodates) AS avg_accommodates,
        AVG(bedrooms) AS avg_bedrooms,
        AVG(bathrooms) AS avg_bathrooms,
        STRING_AGG(DISTINCT bathroom, 'JOIN ') AS bathrooms,
        AVG(latitude) AS avg_latitude,
        AVG(longitude) AS avg_longitude,
        STRING_AGG(DISTINCT extra_host_languages, 'JOIN ') AS extra_host_languages,
        AVG(CAST(is_superhost AS int)) AS avg_is_superhost,
        STRING_AGG(DISTINCT comodities, 'JOIN ') AS comodities
      FROM
        room
      GROUP BY
        room_id;
    """, 'Ouro Preto', args.project.lower(), args.format, args.start_date)

if __name__ == "__main__":
    main()


# SELECT
#         room_id,
#         STRING_AGG(DISTINCT room_name, 'JOIN ') AS hotel_names,
# 		STRING_AGG(DISTINCT hotel_name, 'JOIN ') AS room_names,
#         STRING_AGG(DISTINCT property_type, 'JOIN ') AS property_types,
#         STRING_AGG(DISTINCT room_type, 'JOIN ') AS room_types,
#         AVG(price) AS avg_price,
#         AVG(reviews) AS avg_reviews,
#         AVG(overall_satisfaction) AS avg_rating,
#         AVG(accommodates) AS avg_accommodates,
#         AVG(bedrooms) AS avg_bedrooms,
#         AVG(bathrooms) AS avg_bathrooms,
#        	AVG(latitude) AS avg_latitude,
#         AVG(longitude) AS avg_longitude,
#         STRING_AGG(DISTINCT comodities, 'JOIN ') AS comodities,
# 		STRING_AGG(DISTINCT bed_type, 'JOIN ') AS room_types,
# 		STRING_AGG(DISTINCT checkin_date, 'JOIN ') AS checkin_date,
# 		STRING_AGG(DISTINCT checkout_date, 'JOIN ') AS checkout_dates
#       FROM
#         booking_room
#       GROUP BY
#         room_id;