import psycopg2 as pg
import pandas as pd
import argparse
import datetime as dt
import logging
from airbnb_config import ABConfig
import os.path
import os

LOG_LEVEL = logging.INFO
# Set up logging
LOG_FORMAT = '%(levelname)-8s%(message)s'
logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
DEFAULT_START_DATE = '2020-03-03'

centro = ['Agua Limpa', 'Água Limpa', 'Alto Cruz', 'Antonio Dias', 'Barra', 'Cabecas', \
         'Centro', 'Jardim Alvorada', 'Loteamento', 'Morro Da Queimada', 'Morro Sao Sebastiao', \
         'Nossa Senhora Das Dores', 'Nossa Senhora De Lourdes', 'Nossa Senhora Do Carmo', \
         'Nossa Senhora Do Pilar', 'Nossa Senhora Do Rosario', 'Ouro Preto', 'Padre Faria', \
         'Pilar', 'Pinheiros', 'Rosario', 'Sao Cristovao', 'Sao Francisco', 'Sao Sebastiao', \
         'Vila Pereira', 'Vila Sao Jose' ]
entorno = ['Bairro Da Lagoa', 'Bauxita', 'Morro Do Cruzeiro', 'Saramenha De Cima', 'Vila Aparecida', 'Vila Itacolomy']
distrito = ['Amarantina', 'Cachoeira Do Campo', 'Chapada', 'Glaura', 'Lavras Novas', \
            'Miguel Burnier', 'Santa Rita De Ouro Preto', 'Santo Antonio Do Leite', 'Santo Antônio do Leite', \
            'Sao Bartolomeu' ]

centro_coordenadas = [-43.547957, -20.415906, -43.451998, -20.348322]
entorno_coordenadas = [-43.534224, -20.43521, -43.490107, -20.395795]

def define_region(sub, lat, lng):
    for sublocality in centro:
        if sublocality == sub:
            return 'Centro'

    for sublocality in entorno:
        if sublocality == sub:
            return 'Entorno'

    for sublocality in distrito:
        if sublocality == sub:
            return 'Distrito'

    regiao = 'Distrito'

    if ( lat >= centro_coordenadas[1] and lat <= centro_coordenadas[3] and
        lng >= centro_coordenadas[0] and lng <= centro_coordenadas[2] ):
        regiao = 'Centro'
    if ( lat >= entorno_coordenadas[1] and lat <= entorno_coordenadas[3] and
        lng >= entorno_coordenadas[0] and lng <= entorno_coordenadas[2] ):
        regiao = 'Entorno'
    return regiao

def survey_df(ab_config, city, start_date):
    sql_survey_ids = """
        select survey_id, survey_date, comment
        from survey s, search_area sa
        where s.search_area_id = sa.search_area_id
        and sa.name = %(city)s
        and s.survey_date > '{start_date}'
        and s.status = 1
        order by survey_id
    """.format(start_date=start_date)
    conn = ab_config.connect()
    df = pd.read_sql(sql_survey_ids, conn,
                     params={"city": city})
    conn.close()
    return(df)

def super_survey_df(ab_config, city, start_date):
    sql_survey_ids = """
        select ss_id, date from super_survey
        where city = %(city)s
        and date > '{start_date}'
        order by ss_id
    """.format(start_date=start_date)
    conn = ab_config.connect()
    df = pd.read_sql(sql_survey_ids, conn,
                     params={"city": city})
    conn.close()
    return(df)

def city_view_name(ab_config, city):
    sql_abbrev = """
    select abbreviation from search_area
    where name = %s
    """
    conn = ab_config.connect()
    cur = conn.cursor()
    cur.execute(sql_abbrev, (city, ))
    city_view_name = 'listing_' + cur.fetchall()[0][0]
    cur.close()
    return city_view_name

def export_airbnb_room(config, city, project, format, start_date):
    try:
        rowcount = -1
        logging.info("Initializing export Airbnb'b rooms for " + city)
        conn = config.connect()
        cur = conn.cursor()
        cnxn = config.connect()
        sql = """SELECT room_id, host_id, reviews, price, overall_satisfaction,
                accommodates, bedrooms, bathrooms, bathroom, minstay, max_nights,
                latitude, longitude, avg_rating, is_superhost, room_type,
                rate_type, survey_id, currency, deleted,
                extra_host_languages, name, property_type,
                route, sublocality, city, country,
                address, comodities, last_modified as collected
                FROM room where city = '{city}'
                order by comodities, room_id, last_modified""".format(city=city)

        # create a directory for all the data for the city
        directory = ('files/').format(project=project)
        if not os.path.isdir(directory): # if directory don't exists, create
            os.mkdir(directory)

        today = today = dt.date.today().isoformat()
        directory = directory + 'airbnb_rooms_{city}_2020-12-05.xlsx'.format(city=city)
        pd.read_sql(sql,cnxn).to_excel(directory, sheet_name="Total Listings")

        data = pd.read_excel(directory)
    
        # update the file inserting the region

        region = [ define_region(sub, lat, lng) for sub, lat, lng in zip(data['sublocality'], data['latitude'], data['longitude']) ]
        
        #region = ['Centro' if x in centro else 'Entorno' if x in entorno else 'Distrito' if x in distrito else x for x in data['sublocality']]
        data.insert(16, "region", region)
        data = data.drop(columns=['Unnamed: 0']) #, 'host_id', 'room_type'
        data.to_excel(directory, sheet_name="Total Listings")

        logging.info("Finishing export")

        return directory
    except PermissionError:
        print("Permission denied: ", directory, " is open")
    except Exception:
        logging.error("Failed to export by sublocalities")
        raise


def export_all_cities(config, city, project, format, start_date):

    try:
        rowcount = -1
        logging.info("Initializing export for " + city)
        conn = config.connect()
        cur = conn.cursor()

        sql = """SELECT distinct(city) from room order by city""" # pensar melhor #
            # tratar problema do n/a

        cur.execute(sql, (city,))
        rowcount = cur.rowcount
        results = cur.fetchall()

        if rowcount > 0:
            for result in results:
                cnxn = config.connect()
                city = result[0]
                
                sql = """SELECT room_id, host_id, room_type, name,
                        route, neighborhood, sublocality, city, country
                        neighborhood, address, reviews, overall_satisfaction,
                        accommodates, bedrooms, bathrooms, price, currency, deleted,
                        minstay, max_nights, latitude, longitude, survey_id,
                        coworker_hosted, extra_host_languages,
                        property_type, rate_type, is_superhost,
                        avg_rating, last_modified as collected
                        FROM room where city = '{city}'
                        order by country, sublocality, sublocality, route, room_id, last_modified desc""".format(city=result[0])

                # create a directory for all the data for the city
                directory = ('files/').format(project=project)
                if not os.path.isdir(directory): # if directory don't exists, create
                    os.mkdir(directory)

                today = today = dt.date.today().isoformat()
                pd.read_sql(sql,cnxn).to_excel(directory + 'rooms_{city}_{today}.xlsx'.format(city=result[0], today=today), sheet_name="Total Listings")
    
                logging.info("Finishing export")
                break

    except PermissionError:
        print("Permission denied: ", directory, " is open")
    except Exception:
        logging.error("Failed to export by sublocalities")
        raise


def export_reviews(config, table, city, project, format):

    try:
        rowcount = -1
        logging.info("Initializing export " + table + "'s reviews for " + city)
        conn = config.connect()
        cur = conn.cursor()
   
        if table == 'airbnb':
            sql = """SELECT id, room_id, role, comment, response, language,
                create_at, localized_data, reviewer_name, reviewer_id,
                rating, deleted, last_modified as collected
                FROM reviews where room_id in ( select room_id from room where city = '{city}')
                order by role, room_id, id""".format(city=city)
        else:
            sql = """SELECT id, room_id, role, comment, response, language,
                create_at, localized_data, reviewer_name, reviewer_id,
                rating, deleted, last_modified as collected
                FROM reviews where room_id in ( select room_id from room where city = '{city}')
                order by role, room_id, id""".format(city=city)

        # create a directory for reviews
        directory = ('files/').format(project=project)
        if not os.path.isdir(directory): # if directory don't exists, create
            os.mkdir(directory)

        today = today = dt.date.today().isoformat()
        pd.read_sql(sql,conn).to_excel(directory + '{table}_reviews_{city}_{today}.xlsx'.\
                    format(table=table,city=city,today=today), sheet_name="Total Listings")

        logging.info("Finishing export")

    except PermissionError:
        print("Permission denied: ", directory, " is open")
    except Exception:
        logging.error("Failed to export reviews")
        raise


def export_booking_room(config, city, project, format):
    try:
        rowcount = -1
        logging.info("Initializing export for Booking's rooms of " + city)
        conn = config.connect()
        cur = conn.cursor()
   
        sql = """SELECT room_id, hotel_id, reviews, overall_satisfaction, property_type, accommodates,
                latitude, longitude, price, currency, name, room_name, bed_type
                popular_facilidades, comodities, qtd_rooms, images,
                address, route, sublocality, city, state,
                country, last_modified as collected
                from booking_room where city = '{city}'
                order by comodities, room_id, hotel_id, last_modified""".format(city=city)

        directory = ('files/').format(project=project)
        if not os.path.isdir(directory): # if directory don't exists, create
            os.mkdir(directory)

        today = today = dt.date.today().isoformat()

        directory = directory + 'booking_{city}_{today}.xlsx'.format(city=city,today=today)
        pd.read_sql(sql,conn).to_excel(directory, sheet_name="Total Listings")

        data = pd.read_excel(directory)
    
        # update the file inserting the region

        region = [ define_region(sub, lat, lng) for sub, lat, lng in zip(data['sublocality'], data['latitude'], data['longitude']) ]
        
        #region = ['Centro' if x in centro else 'Entorno' if x in entorno else 'Distrito' if x in distrito else x for x in data['sublocality']]
        data.insert(16, "region", region)
        data = data.drop(columns=['Unnamed: 0'])
        data.to_excel(directory, sheet_name="Total Listings")

        logging.info("Finishing export")

        return directory

    except PermissionError:
        print("Permission denied: ", directory, " is open")
    except Exception:
        logging.error("Failed to export reviews")
        raise

def report_airbnb_room(config, city, project, format, start_date):
    rowcount = -1
    logging.info("Initializing export Airbnb'b rooms for " + city)
    conn = config.connect()
    cur = conn.cursor()
    cnxn = config.connect()
    sql = """SELECT count(distinct(room_id))
            FROM room where city = '{city}'""".format(city=city)

    cur.execute(sql)
    survey_id = cur.fetchone()[0]

    print(survey_id, " rooms from Airbnb");

    rowcount = -1
    logging.info("Initializing export Airbnb'b rooms for " + city)
    conn = config.connect()
    cur = conn.cursor()
    cnxn = config.connect()
    sql = """SELECT count(distinct(room_id))
            FROM booking_room where city = '{city}'""".format(city=city)

    cur.execute(sql)
    survey_id = cur.fetchone()[0]

    print(survey_id, " rooms from Booking");

    rowcount = -1
    logging.info("Initializing export Airbnb'b rooms for " + city)
    conn = config.connect()
    cur = conn.cursor()
    cnxn = config.connect()
    sql = """SELECT count(distinct(id))
            FROM reviews where room_id in
            ( select distinct room_id from room where city = '{city}')""".format(city=city)

    cur.execute(sql)
    survey_id = cur.fetchone()[0]

    print(survey_id, " reviews from Airbnb");

    rowcount = -1
    logging.info("Initializing export Airbnb'b rooms for " + city)
    conn = config.connect()
    cur = conn.cursor()
    cnxn = config.connect()
    sql = """SELECT count(distinct(review_url))
            FROM booking_reviews where hotel_id in
            ( select distinct hotel_id from booking_room where city = '{city}')""".format(city=city)

    cur.execute(sql)
    survey_id = cur.fetchone()[0]

    print(survey_id, " reviews from Booking");

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
                        metavar='format', action='store', default="xlsx",
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

    report_airbnb_room(ab_config, args.city, args.project.lower(),
                          args.format, args.start_date)
    exit(0)
    if args.city:
        if args.listings_airbnb:
            export_airbnb_room(ab_config, args.city, args.project.lower(),
                          args.format, args.start_date) # conferir
        elif args.listings_booking:
            export_booking_room(ab_config, args.city, args.project.lower(),
                args.format) # conferir
        elif args.reviews_booking:
            export_reviews(ab_config, 'booking',args.city, args.project.lower(),
                args.format)
        elif args.reviews_airbnb:
            export_reviews(ab_config, 'airbnb',args.city, args.project.lower(),
                args.format)
        else: # export all
            export_airbnb_room(ab_config, args.city, args.project.lower(),
                          args.format, args.start_date) # conferir
            export_booking_room(ab_config, args.city, args.project.lower(),
                args.format)
            export_reviews(ab_config, 'booking',args.city, args.project.lower(),
                args.format)
            export_reviews(ab_config, 'airbnb',args.city, args.project.lower(),
                args.format)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()