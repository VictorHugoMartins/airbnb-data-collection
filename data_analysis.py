import pandas as pd
from sklearn.cluster import KMeans
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets
import time
import psycopg2 as pg
import argparse
import datetime as dt
import logging
from airbnb_config import ABConfig
import os.path
import clustering_quality as cq
import export_spreadsheet as exs
import create_map as cm
from kmodes import kmodes
from pandas import ExcelWriter
from matplotlib.backends.backend_pdf import PdfPages
import re
from googletrans import Translator

logger = logging.getLogger()
LOG_LEVEL = logging.INFO
# Set up logging
LOG_FORMAT = '%(levelname)-8s%(message)s'
logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)
DEFAULT_START_DATE = '2020-03-03'
today = dt.date.today().isoformat()

shared_rooms = ['Albergue']
entire_homes = ['Pousada', 'Pousada campestre', 'Chalé', 'Chalés alpinos', \
				'Casa de temporada', 'Cama e Café (B&B)', 'Camping', 'Hospedagem domiciliar']
private_rooms = ['Motel', 'Apartamento', 'Apartamentos']
hotel_rooms = ['Hotel']

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
		# count the frequency of each word(present  
		# in str2) in str and print 
		#print('Frequency of', str2[i], 'is :', str.count(str2[i]))
		if str.count(str2[i]) > 1:
			#x = (str2[i], str.count(str2[i]))
			values.append(str2[i])
	return values

def create_columns_with_comodities(da, lista):
	for cname in lista:
		traducao = cname[0]
		original = cname[1]
		da[original] = [ 1 if original in x or traducao in x else 0 for x in da['comodities'] ]
	return da

def get_individual_comodities(la):
	m = []
	linha = []
	for x in la:
		xs  = []

		# find the individual values and separe them (ex.: {'wifi', 'estacionamento'} returns 'wifi' and 'estacionamento')
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
		k = translator.translate(l, dest='en').text
		k = re.sub(r' ', '', k)
		como.append([k, l])
	
	return sorted(como)

	return sorted(n)

def prepare_text(s):
	s = str(s)
	s = s.lower()
	s = re.sub(r' [0-9]+', '', s) #0-9 depois do Z caso manter numeros
	return s

def show_values_on_bars(axs, h_v="v", space=0.4):
	def _show_on_single_plot(ax):
		if h_v == "v":
			for p in ax.patches:
				_x = p.get_x() + p.get_width() / 2
				_y = p.get_y() + p.get_height()
				value = round(p.get_height(), 2)
				ax.text(_x, _y, value, ha="center", fontsize=6) 
		elif h_v == "h":
			for p in ax.patches:
				_x = p.get_x() + p.get_width() + float(space)
				_y = p.get_y() + p.get_height()
				value = int(p.get_width())
				ax.text(_x, _y, value, ha="left")

	if isinstance(axs, np.ndarray):
		for idx, ax in np.ndenumerate(axs):
			_show_on_single_plot(ax)
	else:
		_show_on_single_plot(axs)

def plot_graph_with_clusters_comodities_values(data, qtd=False, percentage=False):
	for n in range(1, 4):
		fig, axs = plt.subplots(ncols=1)
	
		tmp_data = data[data.total_clusters == n]
		if qtd:
			g = sns.barplot(x="comodity", y="qtd", hue="current_cluster", data=tmp_data)
			g.axes.set_ylim(0, data['total_listings'].max() + 10)
		elif percentage:
			g = sns.barplot(x="comodity", y="percentage", hue="current_cluster", data=tmp_data)
			g.axes.set_ylim(0, 100)
		show_values_on_bars(g)
		
		fig.suptitle('quantidade de comodidades para cada cluster em k = ' + str(n) + ' clusterizações', fontsize=16)
		mng = plt.get_current_fig_manager()
		mng.resize(*mng.window.maxsize())
		plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
		plt.xticks(rotation=90)
		plt.show()

def plot_graph_with_clusters_region_values(table, data, qtd=False, percentage=False):
	fig, axs = plt.subplots(ncols=3, nrows=4)
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		groupedvalues=tmp_data.groupby('current_cluster').sum().reset_index()
		
		if qtd:
			g = sns.barplot(x="region", y="qtd", hue="current_cluster", data=tmp_data, ax=axs[0][n-1])
			g.axes.set_ylim(0, data['total_listings'].max())
		elif percentage:
			g = sns.barplot(x="region", y="percentage", hue="current_cluster", data=tmp_data, ax=axs[0][n-1])
			g.axes.set_ylim(0, 100)
		show_values_on_bars(g)
		
		g = sns.barplot(x="region", y="price", hue="current_cluster", data=tmp_data, ax=axs[1][n-1])
		g.axes.set_ylim(0, data['price'].max() + (  data['price'].mean() / 2))
		show_values_on_bars(g)
		
		g = sns.barplot(x="region", y="overall_satisfaction", hue="current_cluster", data=tmp_data, ax=axs[2][n-1])
		g.axes.set_ylim(0, data['overall_satisfaction'].max() + 1)
		show_values_on_bars(g)
		
		g = sns.barplot(x="region", y="reviews", hue="current_cluster", data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (  data['reviews'].mean() / 2))
		show_values_on_bars(g)

	fig.suptitle('quantidade de quartos filtrados por região para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()

def plot_graph_with_clusters_average_values(table, data):
	fig, axs = plt.subplots(nrows=4, ncols=3)
	
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		groupedvalues=tmp_data.groupby('current_cluster').sum().reset_index()
		
		g = sns.barplot(y="total_listings", x="current_cluster",  data=tmp_data, ax=axs[0][n-1])
		g.axes.set_ylim(0, data['total_listings'].max() + 100)
		show_values_on_bars(g)

		g = sns.barplot(y="avg_overall_satisfaction", x="current_cluster", data=tmp_data, ax=axs[1][n-1])
		g.axes.set_ylim(0, 6)
		show_values_on_bars(g)
		
		g = sns.barplot(y="avg_price", x="current_cluster",  data=tmp_data, ax=axs[2][n-1])
		g.axes.set_ylim(0, data['avg_price'].max() + 100)
		show_values_on_bars(g)
		
		g = sns.barplot(y="reviews", x="current_cluster",  data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (data['reviews'].mean() / 2) )
		show_values_on_bars(g)

	fig.suptitle(table + '- valores médios para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.35, hspace=0.20)
	plt.show()

def plot_graph_with_qtd_values(table, data):
	fig, axs = plt.subplots(nrows=3, ncols=3)
	
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		groupedvalues=tmp_data.groupby('current_cluster').sum().reset_index()
		
		g = sns.barplot(y="total_listings", x="current_cluster",  data=tmp_data, ax=axs[0][n-1])
		g.axes.set_ylim(0, data['total_listings'].max() + 100)
		show_values_on_bars(g)

		g = sns.barplot(y="qtd_airbnb", x="current_cluster",  data=tmp_data, ax=axs[1][n-1])
		g.axes.set_ylim(0, data['total_listings'].max() + 100)
		show_values_on_bars(g)

		g = sns.barplot(y="qtd_booking", x="current_cluster",  data=tmp_data, ax=axs[2][n-1])
		g.axes.set_ylim(0, data['total_listings'].max() + 100)
		show_values_on_bars(g)

	fig.suptitle(table + 'quantidade de anúncios de cada site para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.35, hspace=0.20)
	plt.show()

def plot_graph_with_clusters_room_type_values(table, data, qtd=False, percentage=False):
	fig, axs = plt.subplots(ncols=3, nrows=4)
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		groupedvalues=tmp_data.groupby('current_cluster').sum().reset_index()
		
		if qtd:
			g = sns.barplot(x="room_type", y="qtd", hue="current_cluster", data=tmp_data, ax=axs[0][n-1])
			g.axes.set_ylim(0, data['total_listings'].max())
		elif percentage:
			g = sns.barplot(x="room_type", y="percentage", hue="current_cluster", data=tmp_data, ax=axs[0][n-1])
			g.axes.set_ylim(0, 100)
		show_values_on_bars(g)
		
		g = sns.barplot(x="room_type", y="price", hue="current_cluster", data=tmp_data, ax=axs[1][n-1])
		g.axes.set_ylim(0, data['price'].max() + (  data['price'].mean() / 2))
		show_values_on_bars(g)
		
		g = sns.barplot(x="room_type", y="overall_satisfaction", hue="current_cluster", data=tmp_data, ax=axs[2][n-1])
		g.axes.set_ylim(0, data['overall_satisfaction'].max() + 1)
		show_values_on_bars(g)
		
		g = sns.barplot(x="room_type", y="reviews", hue="current_cluster", data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (  data['reviews'].mean() / 2))
		show_values_on_bars(g)

	fig.suptitle(table + 'quantidade de quartos filtrados por tipo de quarto para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()

def create_dataframe_with_means(table, means, region, rooms, comodities):
	writer = ExcelWriter('public/data/mean values_' + table + '_' + today + '.xlsx')
	
	dcomodities = pd.DataFrame(list(comodities), columns=['total_clusters', 'current_cluster', 'total_listings', 'comodity', \
															'qtd','percentage']) #add avg price e outros tbm
	dcomodities.to_excel(writer, sheet_name='region')


	dmeans = pd.DataFrame(list(means), columns=['total_clusters', 'current_cluster', 'total_listings', \
											'avg_price','avg_overall_satisfaction','reviews', 'qtd_airbnb', \
											'qtd_booking', 'percentage_airbnb', 'percentage_booking'])
	dmeans.fillna(0)
	dmeans.to_excel(writer, sheet_name='mean values')

	dregion = pd.DataFrame(list(region), columns=['total_clusters', 'current_cluster', 'total_listings', \
												'region','qtd','percentage', 'price', 'overall_satisfaction','reviews'])

	dregion.fillna(0)
	dregion.to_excel(writer, sheet_name='region filter')

	drooms = pd.DataFrame(list(rooms), columns=['total_clusters', 'current_cluster', 'total_listings',
												'room_type', 'qtd', 'percentage','price', 'overall_satisfaction','reviews'])
	drooms.fillna(0)
	drooms.to_excel(writer, sheet_name="room filter")
	
	writer.save()

	plot_graph_with_qtd_values(table, dmeans)
	plot_graph_with_clusters_average_values(table, dmeans) # all the values in each cluster, without more filters
	
	plot_graph_with_clusters_comodities_values(dcomodities, qtd=True)

	plot_graph_with_clusters_comodities_values(dcomodities, percentage=True)
	
	plot_graph_with_clusters_room_type_values(table, drooms, qtd=True)
	plot_graph_with_clusters_room_type_values(table, drooms, percentage=True)

	plot_graph_with_clusters_region_values(table, dregion, percentage=True)
	plot_graph_with_clusters_region_values(table, dregion, qtd=True)

def prepare_airbnb(da, table='Airbnb'):
	# convert the prices for R$
	da['price'] = [x * 5.05 if x != '-1' and y == 'USD' else x for x, y in zip(da['price'], da['currency'])]
	da['currency'] = ['BRL' if x != '.' else x for x in da['currency']]
	# calculate the price per capita
	da['price_pc'] = [x / y if x != '-1' else x for x, y in zip(da['price'], da['accommodates'])]
	da['comodities'] = [ prepare_text(x) for x in da['comodities'] ]
	
	lena = da['Unnamed: 0'].count()
	da['site'] = [ 'Airbnb' for x in range(lena)]

	if table == 'airbnb + booking':
		da = da.drop(columns=['minstay', 'max_nights', 'avg_rating', 'is_superhost', \
					'rate_type', 'survey_id', 'extra_host_languages'])

	return da

def prepare_booking(db, table='Booking'):
	# prices already in R$
	db['price_pc'] = [x / y if x != '-1' else x for x, y in zip(db['price'], db['accommodates'])]
	db['os'] = [ float(x / 2.0 ) for x in db['overall_satisfaction']] #  if x != '-1' else float(x) 
	db = db.drop(columns=['overall_satisfaction'])
	db = db.rename(columns={'os':'overall_satisfaction'})
	db['comodities'] = [ prepare_text(x) for x in db['comodities'] ]
	
	lenb = db['Unnamed: 0'].count()
	db['site'] = [ 'Booking' for x in range(lenb)]
	
	room_type = [ 'Shared room' if x in shared_rooms else
						'Entire home/apt' if x in entire_homes else
						'Private room' if x in private_rooms else
						'Hotel room' if x in hotel_rooms else x
						for x in db['property_type'] ]
	db.insert(10, "room_type", room_type)

	if table == 'airbnb + booking':
		db['name'] = [ '{}, {}'.format(room, hotel) for room, hotel in zip(db['room_name'], db['name'])]
		db = db.drop(columns=['hotel_id', 'images', 'state', 'room_name', 'popular_facilidades'])
	return db

def join_data(da, db):
	lena = da['Unnamed: 0'].count()
	lenb = db['Unnamed: 0'].count()

	da['site'] = [ 'Airbnb' for x in range(lena)]
	db['site'] = [ 'Booking' for x in range(lenb)]
	
	data = da.append(db, sort=False)

	writer = ExcelWriter('public/data/airbnb_and_booking_' + today + '.xlsx')
	data.to_excel(writer, sheet_name="total listings")
	writer.save()

	return data

def export_clusters(table, data, n_clusters):
	# Identify the clusters and include them in the dataframe
	#data_index = data.index.values
				
	directory = 'public/data/dados agrupados em ' + str(n_clusters) + ' clusters para ' + table + '.xlsx'
	writer = ExcelWriter(directory)
	data.to_excel(writer, sheet_name= str(n_clusters) + " clusters")
	writer.save()

def average_property_type(data, property_type, column):
	if property_type != 'entire home':
		for x in entire_homes:
			data  = data[data.property_type != x ]
	if property_type != 'private room':
		for x in private_rooms:
			data  = data[data.property_type != x ]
	if property_type != 'shared room':
		for x in shared_rooms:
			data  = data[data.property_type != x ]
	if property_type != 'hotel room':
		for x in hotel_rooms:
			data  = data[data.property_type != x ]
	return data[column].mean()

def average_room_type(data, room_type, column):
	return data[data.room_type == room_type][column].mean()

def average_region_type(data, region, column):
	return data[data.region == region][column].mean()

def sum_property_type(data, property_type, column):
	if property_type != 'entire home':
		for x in entire_homes:
			data  = data[data.property_type != x ]
	if property_type != 'private room':
		for x in private_rooms:
			data  = data[data.property_type != x ]
	if property_type != 'shared room':
		for x in shared_rooms:
			data  = data[data.property_type != x ]
	if property_type != 'hotel room':
		for x in hotel_rooms:
			data  = data[data.property_type != x ]
	return data[column].sum()

def compare_sites(table='airbnb + booking', dairbnb=None, dbooking=None):
	if table == 'Airbnb':
		logging.info("AIRBNB DATA")
		data = pd.read_excel(dairbnb)

		drop_duplicates = True
		if drop_duplicates:
			logging.info("Using distinct rooms")
			data = data.drop_duplicates(subset ="room_id", keep = 'first')
		else:
			logging.info("Using all rooms in database")

		data = prepare_airbnb(data, table=table)

		comodities = get_individual_comodities(data['comodities'])
	elif table == 'Booking':
		logging.info("BOOKING DATA")
		data = pd.read_excel(dbooking)

		drop_duplicates = True
		if drop_duplicates:
			logging.info("Using distinct rooms")
			data = data.drop_duplicates(subset ="room_id", keep = 'first')
		else:
			logging.info("Using all rooms in database")

		data = prepare_booking(data, table=table)

		comodities = get_individual_comodities(data['comodities'])
	else:
		logging.info("JOINED DATA ( Airbnb + Booking) ")
		data_airbnb = pd.read_excel(dairbnb)
		data_booking = pd.read_excel(dbooking)

		drop_duplicates = True
		if drop_duplicates:
			logging.info("Using distinct rooms")
			data_airbnb = data_airbnb.drop_duplicates(subset ="room_id", keep = 'first')
			data_booking = data_booking.drop_duplicates(subset ="room_id", keep = 'first')			
		else:
			logging.info("Using all rooms in database")
		data_airbnb = prepare_airbnb(data_airbnb, table=table)
		comodities_airbnb = get_individual_comodities(data_airbnb['comodities'])
		
		data_booking = prepare_booking(data_booking, table=table)
		comodities_booking = get_individual_comodities(data_booking['comodities'])

		comodities = frequency_table(comodities_airbnb + comodities_booking)
		data = join_data(data_airbnb, data_booking)
		
	data = create_columns_with_comodities(data, comodities)		
	region_types = data['region'].unique().tolist()
	room_types = data['room_type'].unique().tolist()
	
	p_da = data

	# fill nan values with mean or '.'
	data = data.apply(lambda x: x.fillna(x.mean()) if x.dtype.kind in 'biufc' else x.fillna('.'))

	region_values = []
	comodities_values = []
	comodities_table_values = []
	room_values = []
	v_medios = []

	for n_clusters in range(1, 4):
		#logging.info("Clustering: " + str(n_clusters))
		clustered_data = p_da

		# if theres just 1 cluster, there's "no cluster"
		if n_clusters > 1:
			if n_clusters == 3 and table == 'airbnb + booking':
				da_airbnb = data[data.site == 'Airbnb']
				km = kmodes.KModes(n_clusters=2, init='Huang', n_init=5, verbose=0).fit(da_airbnb)
				
				cluster = km.labels_
				da_airbnb.insert(2, "cluster", cluster)

				da_booking = data[data.site == 'Booking']
				da_booking['cluster'] = [ 2 for x in da_booking['Unnamed: 0']]
				clustered_data = da_airbnb.append(da_booking, sort=False)
				
				export_clusters(table, clustered_data, n_clusters)
			else:
				km = kmodes.KModes(n_clusters=n_clusters, init='Huang', n_init=5, verbose=0).fit(data)

				cluster = km.labels_
				clustered_data.insert(2, "cluster", cluster)

				export_clusters(table, clustered_data, n_clusters)

		for f in range (0, n_clusters):
			if n_clusters == 1:
				tmp_data = clustered_data
			else:
				tmp_data = clustered_data[clustered_data.cluster == f]

			len_tmp_data = tmp_data['room_id'].count()
			
			# valores medios para o cluster
			avg_p = tmp_data["price_pc"].mean()
			avg_os = tmp_data["overall_satisfaction"].mean()
			r = tmp_data['reviews'].sum()
			qtd_a = (tmp_data.site == 'Airbnb').sum()
			qtd_b = (tmp_data.site == 'Booking').sum()
			pct_a = (qtd_a / len_tmp_data) * 100
			pct_b = (qtd_b / len_tmp_data) * 100
			temp = (n_clusters, f, len_tmp_data, avg_p, avg_os, r, qtd_a, qtd_b, pct_a, pct_b)
			v_medios.append(temp)

			# valores medios para cada tipo de quarto dentro do cluster
			for x in room_types:
				qtd_x = (tmp_data.room_type == x).sum()
				percentage_x = (qtd_x / len_tmp_data) * 100 if qtd_x > 0 else 0
				
				ap_airbnb = average_room_type(tmp_data, x, 'price_pc')
				art_airbnb = average_room_type(tmp_data, x, 'overall_satisfaction')
				ar_airbnb = tmp_data[tmp_data.room_type == x]['reviews'].sum()
				tmp = (n_clusters, f, len_tmp_data, x, qtd_x, percentage_x, ap_airbnb, art_airbnb, ar_airbnb)
				room_values.append(tmp)

			for x in region_types:
				qtd_x = (tmp_data.region == x).sum()
				percentage_x = (qtd_x / len_tmp_data) * 100 if qtd_x > 0 else 0

				ap_airbnb = average_region_type(tmp_data, x, 'price_pc')
				art_airbnb = average_region_type(tmp_data, x, 'overall_satisfaction')
				ar_airbnb = tmp_data[tmp_data.region == x]['reviews'].sum()
				
				tmp = (n_clusters, f, len_tmp_data, x, qtd_x, percentage_x, ap_airbnb, art_airbnb, ar_airbnb)
				region_values.append(tmp)

			for x in comodities:
				cname = x[1]
				qtd_x = tmp_data[cname].sum()
				percentage_x = (qtd_x / len_tmp_data) * 100

				tmp = (n_clusters, f, len_tmp_data, cname, qtd_x, percentage_x)
				comodities_values.append(tmp)

		if n_clusters > 1:
			clustered_data = clustered_data.drop(columns=['cluster'], inplace = True)
	#create_dataframe_with_means(table, v_medios, region_values, room_values, comodities_values)

def define_directories(config, args):
	d_airbnb = None
	d_booking = None

	if args.file_airbnb:
		d_airbnb = args.file_airbnb
	elif args.city:
		d_airbnb = exs.export_airbnb_room(config, args.city, args.project.lower(),
												args.format, args.start_date)

	if args.file_booking:
		d_booking = args.file_booking
	elif args.city:
		d_booking = exs.export_booking_room(config, args.city, args.project.lower(),
												args.format)
	
	if d_airbnb == None and d_booking == None:
		print("City(ies) or file(s) needed")
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
						help="""set the city""")
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

	(d_airbnb, d_booking) = define_directories(config, args)
	if args.booking:
		compare_sites(table='Booking', dbooking=d_booking)
	elif args.airbnb:
		compare_sites(table='Airbnb', dairbnb=d_airbnb)
	else:
		compare_sites(dairbnb=d_airbnb, dbooking=d_booking)

if __name__ == "__main__":
	main()