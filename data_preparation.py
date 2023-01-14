import pandas as pd
import numpy as np
import time
import psycopg2 as pg
import argparse
import datetime as dt
import logging
from airbnb_config import ABConfig
import clustering_quality as cq
import export_spreadsheet as exs
from kmodes import kmodes
from pandas import ExcelWriter
from googletrans import Translator
import re

logger = logging.getLogger()
LOG_LEVEL = logging.INFO

# Set up logging
LOG_FORMAT = '%(levelname)-8s%(message)s'
logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
DEFAULT_START_DATE = '2020-03-03'
today = dt.date.today().isoformat()


shared_rooms = ['Albergue', 'Hospedagem domiciliar', 'Cama e Café (B&B)']
entire_homes = ['Pousada', 'Pousada campestre', 'Chalé', 'Chalés alpinos', \
				'Casa de temporada', 'Camping']
private_rooms = ['Motel', 'Apartamento']
hotel_rooms = ['Hotel', 'Apartamentos']

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
entorno_coordenadas = [-43.554224, -20.43521, -43.490107, -20.395795]

westlimit=-43.534224; southlimit=-20.43521; eastlimit=-43.490107; northlimit=-20.395795
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

# Python code to find frequency of each word 
def frequency_table(str): 
	# break the string into list of words  
	str2 = []
  
	# loop till string values present in list str 
	for i in str: # checking for the duplicacy 
		if i not in str2:
			str2.append(i) # insert value in str2 
			  
	values = []
	for i in range(0, len(str2)): 
		# count the frequency of each word (present in str2) in str and print 
		if str.count(str2[i]) > 1:
			#x = (str2[i], str.count(str2[i]))
			values.append(str2[i])
	return values

def create_columns_with_bathroom_propriety(site, da):
	def get_category(site, room_type, private_bathroom, shared_bathroom, pt):
		if 'shared' in str(pt).lower() and private_bathroom == 1:
			return 'Quarto compartilhado com banheiro privativo'
		elif 'shared' in str(pt).lower() and shared_bathroom == 1:
			return 'Quarto compartilhado com banheiro compartilhado'
		elif 'private' in str(pt).lower() and private_bathroom == 1:
			return 'Quarto privativo com banheiro privativo'
		elif 'private' in str(pt).lower() and private_bathroom == 1:
			return 'Quarto privativo com banheiro compartilhado'

		# para os quartos compartilhados, assume-se que o quarto é compartilhado, privado se especificado
		# caso o quarto nao seja compartilhado para hoteis/quartos privados/casas inteiras, assume-se que é privado
		if room_type == 'Shared room' and private_bathroom == 1:
			return 'Quarto compartilhado com banheiro privativo'
		elif room_type == 'Shared room':
			return 'Quarto compartilhado com banheiro compartilhado'
		elif shared_bathroom == 1:
			return 'Quarto privativo com banheiro compartilhado'
		else: 
			return 'Quarto privativo com banheiro privativo'
		return 'Não especificado'
	
	da['republica'] = [ 1 if 'república' in str(x).lower() else 0 for x in da['name'] ]

	if site == 'Airbnb':
		da['private_bathroom'] = [ 1 if 'privado' in str(x).lower() else 0 for x in da['bathroom']]
		da['shared_bathroom'] = [ 1 if 'compartilhado' in str(x).lower() else 0 for x in da['bathroom'] ]
	elif site == 'Booking':
		da['private_bathroom'] = [ 1 if 'banheiro privativo' in str(x).lower() else 0 for x in da['name']]
		da['shared_bathroom'] = [ 1 if 'banheiro compartilhado' in str(x).lower() else 0 for x in da['name'] ]
	
	da['category'] = [ get_category(s, rt, sb, pb, pt)
						for s, rt, sb, pb, pt in zip(da['site'], da['room_type'],
												da['shared_bathroom'],
												da['private_bathroom'],
												da['property_type'])]

	return da

def create_columns_with_comodities(da, lista):
	for cname in lista:
		traducao = cname[0]
		original = cname[1]
		da[original] = [ 1 if ( original in x or traducao in x ) else 0 for x in da['comodities'] ]
	return da

def get_individual_comodities(la):
	m = []
	linha = []
	for x in la:
		xs  = []

		# find the individual values and separe them
		# (ex.: {'wifi', 'estacionamento'} returns 'wifi' and 'estacionamento')
		x = x.replace('{', '')
		x = x.replace('}', '')
		x = x.replace('"', '')
		x = x.split(',')
		for l in x:
			if l == "" or l == "nan":
				continue
			if len(l.split()) > 1:
				l = l.split()[0] # 'wifi gratuito' turns into 'wifi'
			m.append(l)
			xs.append(l)
		linha.append(xs)

	n = list(set(m))
	como = []
	translator = Translator()
	for l in n:
		try:
			k = translator.translate(l, dest='en').text
			k = re.sub(r' ', '', k)
			como.append([k, l])
		except:
			como.append([l, l])
	
	return sorted(como)

def prepare_text(s):
	s = str(s)
	s = s.lower()
	s = re.sub(r' [0-9]+', '', s) #0-9 depois do Z caso manter numeros
	return s

def translate_property_type(data):
	def get_translated_dict_value(dict, value):
		try:
			return dict_properties[x]
		except KeyError:	
			return x

	translator = Translator()
	distinct_properties = data['property_type'].unique().tolist()
	dict_properties = {}

	for x in distinct_properties:
		try:
			dict_properties[x] = translator.translate(str(x), dest='en').text
		except AttributeError:
			dict_properties[x] = x

	data['property_type'] = [ get_translated_dict_value(dict_properties, x)
								for x in data['property_type'] ]
	return data['property_type']

def prepare_airbnb(da, table='Airbnb'):
	# convert the prices for R$
	da['price'] = [x * 5.05 if x != '-1' and y == 'USD' else x for x, y in zip(da['price'], da['currency'])]
	da['currency'] = ['BRL' if x != '.' else x for x in da['currency']]

	# calculate the price per capita

	da['price_pc'] = [x / y if x != '-1' else x for x, y in zip(da['price'], da['accommodates'])]
	da['comodities'] = [ prepare_text(x) for x in da['comodities'] ]

	da['qtd_comodities'] = [ len(x.split(',')) for x in da['comodities']]
	
	da['count_host_id'] = [ da.query('host_id==' + str(x))['Unnamed: 0'].count() for x in da['host_id']]
	da['hotel_id'] = [ -1 for x in da['Unnamed: 0']]
	da['count_hotel_id'] = [ -1 for x in da['Unnamed: 0']]

	da['region'] = [ define_region(sub, lat, lng) for sub, lat, lng in zip(da['sublocality'], da['latitude'], da['longitude']) ]
        
	da['property_type'] = translate_property_type(da)

	da['qtd'] = [ 1 for x in da['Unnamed: 0'] ]

	lena = da['Unnamed: 0'].count()
	da['site'] = [ 'Airbnb' for x in range(lena)]

	da = da.drop(columns=['reviews', 'minstay', 'max_nights', 'avg_rating', 'is_superhost', \
				'rate_type', 'survey_id', 'currency', 'extra_host_languages', 'city', 'country', 'address'])

	da = da.apply(lambda x: x.fillna(x.mean()) if x.dtype.kind in 'biufc' else x.fillna('.'))

	return da

def use_distinct_rooms(db):
	logging.info("Using distinct rooms")
	return db.drop_duplicates(subset ="room_id", keep = 'first')

def prepare_booking(db, table='Booking'):
	def get_qtd(x):
		try:
			return int(str(x).split('\n')[len(str(x).split('\n'))-1].split(' ')[0])
		except ValueError:
			return None

	def get_price(price, qtd_rooms):
		if price is not None:
			return price
		else:
			p = qtd_rooms.split('Selecionar nº de quartos\n0\n1')[1].replace(' ', '')
			return p
		

	# prices already in R$
	db['qtd'] = [ get_qtd(x) for x in db['qtd_rooms']]
	db['price'] = [ get_price(x, y) for x, y in zip(db['price'], db['qtd_rooms'])]
	db['qtd'] = db['qtd'].fillna(db['qtd'].mean())

	for x, y in zip(db['qtd'], db['room_id']):
		if float(x) > 0: z = float(x) - 1
		else: z = 1
		a = str(y).split('.')[0]
		if a != 'nan':
			tmp_db = db.query('room_id=='+a)
		for i in range(0,int(z)):
			db = db.append(tmp_db,ignore_index=True)

	db['price'] = [ float(str(x).split('\n')[0]) if x is not None else 0 for x in db['price'] ]

	db['price_pc'] = [ x / y if x != '-1' else x for x, y in zip(db['price'], db['accommodates'])]
	db['os'] = [ float(x / 2.0 ) for x in db['overall_satisfaction']] #  if x != '-1' else float(x) 
	db = db.drop(columns=['overall_satisfaction'])
	db = db.rename(columns={'os':'overall_satisfaction'})
	db['comodities'] = [ prepare_text(x) for x in db['comodities'] ]
	db['qtd_comodities'] = [ len(x.split(',')) for x in db['comodities']]
	
	db['count_hotel_id'] = [ db.query('hotel_id==' + str(x))['Unnamed: 0'].count()
								if str(x).lower() != 'nan' else 0 for x in db['hotel_id']]
	db['count_host_id'] = [ -1 for x in db['Unnamed: 0']]
	db['host_id'] = [ -1 for x in db['Unnamed: 0']]

	db['region'] = [ ddefine_region(sub, lat, lng) for sub, lat, lng in zip(db['sublocality'], db['latitude'], db['longitude']) ]
        
	db['property_type'] = translate_property_type(db)
	db['bathroom'] = [ '' for x in db['Unnamed: 0']]

	lenb = db['Unnamed: 0'].count()
	db['site'] = [ 'Booking' for x in range(lenb)]

	room_type = [ 'Shared room' if x in shared_rooms else
						'Entire home/apt' if x in entire_homes else
						'Private room' if x in private_rooms else
						'Hotel room' if x in hotel_rooms else x
						for x in db['property_type'] ]
	db.insert(10, "room_type", room_type)

	db['name'] = [ 'Quarto não identificado' if str(x) == 'nan' else x for x in db['room_name']]
	db['name'] = [ '{}, {}'.format(room, hotel) for room, hotel in zip(db['room_name'], db['name'])]

	db = db.drop(columns=['reviews', 'currency', 'images', 'state', 'room_name', 'address',
						'city', 'state', 'country','popular_facilidades'])

	db = db.apply(lambda x: x.fillna(x.mean()) if x.dtype.kind in 'biufc' else x.fillna('.'))
	return db

def same_place():
	def is_inside(lat_center, lng_center, lat_test, lng_test):
		center_point = [{'lat': lat_center, 'lng': lng_center}]
		test_point = [{'lat': lat_test, 'lng': lng_test}]

		radius = 1
		center_point_tuple = tuple(center_point[0].values()) # (-7.7940023, 110.3656535)
		test_point_tuple = tuple(test_point[0].values()) # (-7.79457, 110.36563)

		dis = distance.distance(center_point_tuple, test_point_tuple).km
		
		if dis <= radius:
			return True
		return False

	def funcao(lat_center, lng_center, lat_test, lng_test, host, hosts):
		if host_id not in hosts:
			return False

	hosts = data.query('count_host_id>5')['host_id'].unique().tolist()
	da['same_place'] = [ funcao(lat_center, lng_center, lat_test, lng_test, host, hosts) ]

	#da['same_place'] = [ 1 if is_inside() else 0 for x in ]'''

def join_data(da, db):
	lena = da['Unnamed: 0'].count()
	lenb = db['Unnamed: 0'].count()

	da['site'] = [ 'Airbnb' for x in range(lena)]
	db['site'] = [ 'Booking' for x in range(lenb)]
	
	data = da.append(db, sort=False)
	return data

def create_document(total_clusters):
	directory = 'bokeh_plataform/files/dados preparados em até ' + str(total_clusters) + \
				'_' + today + '.xlsx'
	writer = ExcelWriter(directory)
	return writer

def make_preparation(area="Ouro Preto", config=None, args=None, rd=1000):
	writer = create_document(3)

	cities = []
	for city in area.split('|'):
		city = re.sub(r"^\s+", "", city)
		city = re.sub(r"\s+$", "", city)
		cities.append(city)

	total_data = []

	for table in ['Airbnb']:
		for city in cities:
			logging.info("Clustering data for " + city)
			(dairbnb, dbooking) = define_directories(config, city, args)
			data = prepare_data(table, dairbnb, dbooking)
			
			compare_sites(writer, table, city, data, rd)
		break
	writer.save()

def get_clustered_data(writer, table, city, total_clusters, original_data, data, rd):
	print(total_clusters, " clusters")
	clustered_data = None
	clustered_data = original_data

	clustered_data['total_clusters'] = [ total_clusters for x in clustered_data['Unnamed: 0']]
	clustered_data['cidade'] = [ city for x in clustered_data['Unnamed: 0']]
	clustered_data['table'] = [ table for x in clustered_data['Unnamed: 0']]
	
	# if theres just 1 cluster, there's "no cluster"
	if total_clusters == 1: # just export the data
		print("UM ÚNICO CLUSTER")

		if 'cluster' in clustered_data.columns:
			clustered_data = clustered_data.drop(columns=['cluster'], inplace=True)

		clustered_data['cluster'] = [ 0 for x in clustered_data['Unnamed: 0']]
		clustered_data.apply(lambda x: x.fillna(x.mean()) if x.dtype.kind in 'biufc' else x.fillna('.')). \
				to_excel(writer, sheet_name=city + ' ' + str(total_clusters))
		return

	logging.info("Clustering data for "  + str(total_clusters) + " clusters")
	'''if total_clusters == 3 and table == 'Airbnb and Booking':
		da_airbnb = data[data.site == 'Airbnb']
		km = kmodes.KModes(n_clusters=2, init='Huang',
				n_init=5, random_state=rd, verbose=0).fit(da_airbnb)
		
		cluster = km.labels_
		da_airbnb.insert(2, "cluster", cluster)

		da_booking = data[data.site == 'Booking']
		da_booking['cluster'] = [ 2 for x in da_booking['Unnamed: 0']]
		clustered_data = da_airbnb.append(da_booking, sort=False)
	else:'''
	km = kmodes.KModes(n_clusters=total_clusters, init='Huang',
					random_state=rd, n_init=5, verbose=0).fit(data)

	cluster = km.labels_
	if 'cluster' in clustered_data.columns:
			clustered_data = clustered_data.drop(columns=['cluster'])

	clustered_data.insert(2, 'cluster', cluster)

	clustered_data.apply(lambda x: x.fillna(0) if x.dtype.kind in 'biufc' else x.fillna('.')). \
				to_excel(writer, sheet_name=city + ' ' + str(total_clusters))

def prepare_data(table, dairbnb=None, dbooking=None):
	if table == 'Airbnb':
		logging.info("AIRBNB DATA")
		data = pd.read_excel(dairbnb)

		logging.info("Preparing data")
		data = use_distinct_rooms(data)

		data = prepare_airbnb(data, table=table)

		comodities = get_individual_comodities(data['comodities'])
		data = create_columns_with_bathroom_propriety('Airbnb', data)
	elif table == 'Booking':
		logging.info("BOOKING DATA")
		data = pd.read_excel(dbooking)

		logging.info("Preparing data")
		data = use_distinct_rooms(data)

		data = prepare_booking(data, table=table)

		comodities = get_individual_comodities(data['comodities'])
		data = create_columns_with_bathroom_propriety('Booking', data)
	else:
		logging.info("JOINED DATA ( Airbnb and Booking) ")
		data_airbnb = pd.read_excel(dairbnb)
		
		data_booking = pd.read_excel(dbooking)

		logging.info("Preparing data")
		data_airbnb = use_distinct_rooms(data_airbnb)

		data_airbnb = prepare_airbnb(data_airbnb, table=table)
		comodities_airbnb = get_individual_comodities(data_airbnb['comodities'])
		data_airbnb = create_columns_with_bathroom_propriety('Airbnb', data_airbnb)

		data_booking = use_distinct_rooms(data_booking)

		data_booking = prepare_booking(data_booking, table=table)
		comodities_booking = get_individual_comodities(data_booking['comodities'])
		data_booking = create_columns_with_bathroom_propriety('Booking', data_booking)

		comodities = frequency_table(comodities_airbnb + comodities_booking)
		data = join_data(data_airbnb, data_booking)

	data = create_columns_with_comodities(data, comodities)
	return data

def compare_sites(writer, table, area, data, rd=1000):
	region_types = data['region'].unique().tolist()
	room_types = data['room_type'].unique().tolist()
	
	# fill nan values with mean or '.'
	filled_data = data.apply(lambda x: x.fillna(x.mean()) if x.dtype.kind in 'biufc'
													else x.fillna('.'))

	city_data = []
	
	for total_clusters in range(1, 4):
		original_data = data
		get_clustered_data(writer, table, area, total_clusters, filled_data, filled_data, rd)

def define_directories(config, city, args):
	d_airbnb = None
	d_booking = None

	if args.city:
		d_airbnb = exs.export_airbnb_room(config, city, args.project.lower(),
												args.format, args.start_date)
		# d_booking = exs.export_booking_room(config, city, args.project.lower(),
		# 										args.format)
	
	if d_airbnb == None and d_booking == None:
		print("City(ies) needed")
		exit(0)
	return (d_airbnb, d_booking)

def main():
	parser = \
		argparse.ArgumentParser(
			description="Create a spreadsheet of surveys from a city")
	parser.add_argument("-cfg", "--config_file",
						metavar="config_file", action="store", default=None,
						help="""explicitly set configuration file, instead of
						using the default <username>.config""")
	parser.add_argument('-a', '--airbnb',
						action='store_true', default=False,
						help="plot graphics for airbnb")
	parser.add_argument('-b', '--booking',
						action='store_true', default=False,
						help="plot graphics for booking")
	parser.add_argument('-c', '--city',
						metavar='city', action='store',
						help="""set the city (or cities, split by the character '|' )""")
	parser.add_argument('-tb', '--table',
						metavar='table', action='store',
						help="""set the table (or tables, split by the character '|' )""")
	parser.add_argument('-tc', '--total_clusters',
						metavar='total_clusters', type=int,
						help="""set the number max of clusters""")
	parser.add_argument('-fla', '--file_airbnb',
						metavar='file', action='store',
						help="not export database, but read file with Airbnb rooms")
	parser.add_argument('-flb', '--file_booking',
						metavar='file', action='store',
						help="not export database, but read file with Booking rooms")
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
	config = ABConfig(args)

	if args.booking:
		make_preparation(area=args.city, config=config, args=args)
	elif args.airbnb:
		make_preparation(area=args.city, config=config, args=args)
	else:
		make_preparation(area=args.city, config=config, args=args, rd=612377)

if __name__ == "__main__":
	main()