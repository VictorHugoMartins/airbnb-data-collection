import pandas as pd
from sklearn.cluster import KMeans
import seaborn as sns
from math import sqrt
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
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
from kmodes import kmodes
from pandas import ExcelWriter
from matplotlib.backends.backend_pdf import PdfPages
from pandas.plotting import parallel_coordinates
import mpld3
import re
import table as tb

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
private_rooms = ['Hotel', 'Motel', 'Apartamento', 'Apartamentos'] 

def comparable_comodities(da, names):
	nomes = []
	valores = []

	'''for name in names:
		nomes.append(name)
		valores.append(da[name].sum())

	g = plt.bar(nomes, valores)
	plt.xticks(rotation=90)
	#show_values_on_bars(g)
	plt.show()'''

def create_columns_with_comodities(da, lista):
	for cname in lista:
		da[cname] = [ 1 if cname in x else 0 for x in da['comodities'] ]
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
			if l == "":
				continue
			if len(l.split()) > 1:
				l = l.split()[0] # 'wifi gratuito' turns into 'wifi'
			m.append(l)
			xs.append(l)
		linha.append(xs)
	n = list(set(m))

	return sorted(n)

def prepare_text(s):
	s = str(s)
	s = s.lower()
	s = re.sub('[^a-zA-Z, \n\.]', '', s) #0-9 depois do Z caso manter numeros
	
	return s

def prepare_comodities(da):
	da = da.drop_duplicates(subset ="room_id", keep = 'first')
	distinct = get_individual_comodities(da['comodities'])

	return distinct

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

def plot_graph_with_clusters_comodities_values(data):
	
	for n in range(1, 4):
		fig, axs = plt.subplots(ncols=1)
	
		tmp_data = data[data.total_clusters == n]
		g = sns.barplot(x="comodity", y="qtd", hue="current_cluster", data=tmp_data)
		g.axes.set_ylim(0, data['total_listings'].max() + 10)
		show_values_on_bars(g)
		#g.axes.xticks(rotation=90)

		fig.suptitle('quantidade de comodidades para cada cluster em k = ' + str(n) + ' clusterizações', fontsize=16)
		mng = plt.get_current_fig_manager()
		mng.resize(*mng.window.maxsize())
		plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
		plt.xticks(rotation=90)
		plt.show()

def plot_graph_with_clusters_region_values(data):
	fig, axs = plt.subplots(ncols=3)
	
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		g = sns.barplot(x="region", y="qtd", hue="current_cluster", data=tmp_data, ax=axs[n-1])
		g.axes.set_ylim(0, data['qtd'].max())
		show_values_on_bars(g)

	fig.suptitle('quantidade de quartos filtrados por região para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()

def plot_graph_with_clusters_average_values(data):
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

	fig.suptitle('Valores médios para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.35, hspace=0.20)
	plt.show()

def plot_graph_with_qtd_values(data):
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

	fig.suptitle('quantidade de anúncios de cada site para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.35, hspace=0.20)
	plt.show()

def plot_graph_with_clusters_room_type_values(data):
	fig, axs = plt.subplots(ncols=3, nrows=4)
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		groupedvalues=tmp_data.groupby('current_cluster').sum().reset_index()
		
		g = sns.barplot(x="room_type", y="qtd", hue="current_cluster", data=tmp_data, ax=axs[0][n-1])
		g.axes.set_ylim(0, data['qtd'].max() + (  data['qtd'].mean() / 2))
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

	fig.suptitle('quantidade de quartos filtrados por tipo de quarto para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()

def create_dataframe_with_means(means, region, rooms, comodities):
	writer = ExcelWriter('public/data/mean values_' + today + '.xlsx')
	
	dcomodities = pd.DataFrame(list(comodities), columns=['total_clusters', 'current_cluster', 'total_listings', 'comodity','qtd','percentage']) #add avg price e outros tbm
	dcomodities.to_excel(writer, sheet_name='region')
	
	plot_graph_with_clusters_comodities_values(dcomodities) # filter the data in clusters by region

	exit(0)
	dmeans = pd.DataFrame(list(means), columns=['total_clusters', 'current_cluster', 'total_listings', \
											'avg_price','avg_overall_satisfaction','reviews', 'qtd_airbnb', 'qtd_booking'])
	dmeans.to_excel(writer, sheet_name='mean values')
	
	plot_graph_with_qtd_values(dmeans)
	plot_graph_with_clusters_average_values(dmeans) # all the values in each cluster, without more filters
	
	dregion = pd.DataFrame(list(region), columns=['total_clusters', 'current_cluster','region','qtd','percentage']) #add avg price e outros tbm
	dregion.to_excel(writer, sheet_name='region')
	plot_graph_with_clusters_region_values(dregion) # filter the data in clusters by region

	drooms = pd.DataFrame(list(rooms), columns=['total_clusters', 'current_cluster','room_type', 'qtd',\
						'pct','price', 'overall_satisfaction','reviews'])
	drooms.to_excel(writer, sheet_name="room values")
	plot_graph_with_clusters_room_type_values(drooms)

	writer.save()

def prepare_airbnb(da):
	# convert the prices for R$
	da['price'] = [x * 5.05 if x != '-1' and y == 'USD' else x for x, y in zip(da['price'], da['currency'])]
	da['currency'] = ['BRL' if x != '.' else x for x in da['currency']]
	# calculate the price per capita
	da['price_pc'] = [x / y if x != '-1' else x for x, y in zip(da['price'], da['accommodates'])]
	da['comodities'] = [ prepare_text(x) for x in da['comodities'] ]
	
	lena = da['Unnamed: 0'].count()
	da['table'] = [ 'airbnb' for x in range(lena)]

	return da

def prepare_booking(db):
	# prices already in R$
	# da['price'] = [x * 5.05 if x != '-1' and y == 'USD' else x for x, y in zip(da['price'], da['currency'])]
	db['price_pc'] = [x / y if x != '-1' else x for x, y in zip(db['price'], db['accommodates'])]
	db['os'] = [ float(x / 2.0 ) for x in db['overall_satisfaction']] #  if x != '-1' else float(x) 
	db = db.drop(columns=['overall_satisfaction'])
	db = db.rename(columns={'os':'overall_satisfaction'})
	db['comodities'] = [ prepare_text(x) for x in db['comodities'] ]
	
	lenb = db['Unnamed: 0'].count()
	db['table'] = [ 'booking' for x in range(lenb)]
	
	room_type = [ 'Shared room' if x in shared_rooms else
						'Entire home/apt' if x in entire_homes else
						'Private room' if x in private_rooms else x
						for x in db['property_type'] ]
	db.insert(10, "room_type", room_type)
	
	return db

def plot_final(da, km, n_clusters):
	da = da.drop(columns=['Unnamed: 0', 'name', 'route', 'city', 'address', \
						'comodities', 'collected', 'survey_id', 'deleted', \
						'neighborhood', 'rate_type', 'coworker_hosted', \
						'extra_host_languages', 'currency', 'neighborhood.1', \
						'property_type', 'sublocality'])

	columns = list(da.columns)
	qtd_columns = len(columns)
	X = da.iloc[:,0:qtd_columns].values
	figure, axes = plt.subplots(nrows=4, ncols=4)

	y = X[:, da.columns.get_loc("room_id")]
	xc = da.columns.get_loc("room_id")

	barWidth = 0.25

	x1 = X[:, da.columns.get_loc("region")]
	c_indice = 1
	for i in range(0, 4):
		for j in range(0, 4):
			try:
				axes[i,j].set_title(f'{columns[c_indice]}')
				axes[i,j].bar(x1, X[:, c_indice], color='#7f6d5f', width=barWidth, edgecolor='white', label='var1')
				
				if c_indice == 9:
					c_indice = c_indice + 2
				else:
					c_indice = c_indice + 1
			except IndexError:
				c_indice = c_indice + 1
				break

	plt.setp(axes[:, 0], ylabel='room_id')
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.03, bottom=0.06, right=0.98, top=0.97, wspace=0.13, hspace=0.43)
	plt.savefig('public/data/' + str(n_clusters) + ' clusters.png')
	#plt.show()
	return
	da.iplot(kind='scatter', x='A', y='B', title='Disperssão entre a coluna A e B', color='red', mode='markers')
	da.scatter_matrix()
	df.order_status.value_counts().iplot(kind='bar', title='Status dos pedidos')

def plot_final_a(da, km, n_clusters):
	da = da.drop(columns=['Unnamed: 0', 'name', 'route', 'city', 'address', \
						'comodities', 'collected', 'survey_id', 'deleted', \
						'neighborhood', 'rate_type', 'coworker_hosted', \
						'extra_host_languages', 'currency', 'neighborhood.1', \
						'property_type', 'sublocality'])

	columns = list(da.columns)
	qtd_columns = len(columns)
	X = da.iloc[:,0:qtd_columns].values
	figure, axes = plt.subplots(nrows=4, ncols=4)

	y = X[:, da.columns.get_loc("room_id")]
	xc = da.columns.get_loc("room_id")

	x1 = X[:, da.columns.get_loc("region")]
	c_indice = 1
	for i in range(0, 4):
		for j in range(0, 4):
			try:
				if c_indice == 10:
					axes[i,j].set_title(f'latitude x longitude')
					axes[i,j].scatter(X[:, da.columns.get_loc("latitude")], X[:,da.columns.get_loc("longitude")], s = 5, c = km.labels_)
					#axes[i, j].plot(x, X[:, j])
					#axes[i,j].scatter(km.cluster_centroids_[:, da.columns.get_loc("latitude")], \
					# km.cluster_centroids_[:, da.columns.get_loc("longitude")], s = 5, c = 'red',label = 'Centroids')
					c_indice = c_indice + 2
				else:
					axes[i,j].set_title(f'{columns[c_indice]}')
					axes[i,j].scatter(X[:, c_indice], y, s = 5, c = km.labels_) #axes[i, j].plot(x, X[:, j])
					#axes[i,j].scatter(km.cluster_centroids_[:, c_indice], \
					#km.cluster_centroids_[:, xc], s = 5, c = 'red',label = 'Centroids')
					c_indice = c_indice + 1
			except IndexError:
				c_indice = c_indice + 1
				break

	plt.setp(axes[:, 0], ylabel='room_id')
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.03, bottom=0.06, right=0.98, top=0.97, wspace=0.13, hspace=0.43)
	plt.savefig('public/data/' + str(n_clusters) + ' clusters.png')
	##plt.show()
	return
	da.iplot(kind='scatter', x='A', y='B', title='Disperssão entre a coluna A e B', color='red', mode='markers')
	da.scatter_matrix()
	df.order_status.value_counts().iplot(kind='bar', title='Status dos pedidos')

def export_clusters(km, data, n_clusters):
	# Identify the clusters and include them in the dataframe
	#data_index = data.index.values
	cluster = km.labels_
	data.insert(2, "cluster", cluster)

	writer = ExcelWriter('public/data/dados agrupados em ' + str(n_clusters) + ' clusters.xlsx')
	for n in range(0, n_clusters):
		data[data.cluster == n].to_excel(writer, sheet_name="cluster " + str(n+1))
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
	return data[column].mean()

def average_room_type(data, room_type, column):
	return data[data.room_type == room_type ][column].mean()

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
	return data[column].sum()

def compare_sites(table=None, dairbnb=None, dbooking=None):
	if table == 'airbnb':
		logging.info("AIRBNB DATA")
		data = pd.read_excel(dairbnb)
		data = prepare_airbnb(data)

		comodities = prepare_comodities(data)
	elif table == 'booking':
		logging.info("BOOKING DATA")
		data = pd.read_excel(dbooking)
		data = prepare_booking(data)

		comodities = prepare_comodities(data)
	else:
		logging.info("JOINED DATA ( Airbnb + Booking) ")
		d1 = pd.read_excel(dairbnb)
		d2 = pd.read_excel(dbooking)

		all_data = 'n'
		if all_data == 'n':
			d1 = d1.drop_duplicates(subset ="room_id", keep = 'first')
			d2 = d2.drop_duplicates(subset ="room_id", keep = 'first')

		d1 = prepare_airbnb(d1)
		comodities_airbnb = prepare_comodities(d1)

		d2 = prepare_booking(d2)
		comodities_booking = prepare_comodities(d2)

		comodities = tb.freq(sorted(comodities_airbnb + comodities_booking))
		data = join_data(d1, d2)
		
	data = create_columns_with_comodities(data, comodities)
	
	#all_data = input("Use all data in the clustering? (y/n): ")
	all_data = 'n'
	if all_data == 'n':
		data = data.drop_duplicates(subset ="room_id", keep = 'first')
		# db = db.drop_duplicates(subset ="room_id", keep = 'first')
		logging.info("Using distinct rooms")
	else:
		logging.info("Using all rooms in database")

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

	for n_clusters in range(1, 6):
		#logging.info("Clustering: " + str(n_clusters))
		clustered_data = p_da

		# if theres just 1 cluster, there's "no cluster"
		if n_clusters > 1:
			km = kmodes.KModes(n_clusters=n_clusters, init='Huang', n_init=5, verbose=0).fit(data)
			export_clusters(km, clustered_data, n_clusters)
		#plot_final(da, km, n_clusters)

		for f in range (0, n_clusters):
			if n_clusters == 1:
				temp_data = clustered_data
			else:
				temp_data = clustered_data[clustered_data.cluster == f]

			len_temp_data = temp_data['room_id'].count()
			
			# valores medios para o cluster
			avg_p = temp_data["price_pc"].mean()
			avg_os = temp_data["overall_satisfaction"].mean()
			r = temp_data['reviews'].sum()
			qtd_a = (temp_data.table == 'airbnb').sum()
			qtd_b = (temp_data.table == 'booking').sum()
			temp = (n_clusters, f, len_temp_data, avg_p, avg_os, r, qtd_a, qtd_b)
			v_medios.append(temp)

			# valores medios para cada tipo de quarto dentro do cluster
			for x in room_types:
				qtd_x = (temp_data.room_type == x).sum()
				percentage_x = (qtd_x / len_temp_data) * 100 if qtd_x > 0 else 0
				
				ap_airbnb = average_room_type(temp_data, x, 'price_pc')
				art_airbnb = average_room_type(temp_data, x, 'overall_satisfaction')
				ar_airbnb = temp_data[temp_data.room_type == x]['reviews'].sum()
				tmp = (n_clusters, f, x, qtd_x, percentage_x, ap_airbnb, art_airbnb, ar_airbnb)
				room_values.append(tmp)

			for x in region_types:
				qtd_x = (temp_data.region == x).sum()
				percentage_x = (qtd_x / len_temp_data) * 100 if qtd_x > 0 else 0
				
				tmp = (n_clusters, f, x, qtd_x, percentage_x)
				region_values.append(tmp)

			for x in comodities:
				qtd_x = temp_data[x].sum()
				percentage_x = (qtd_x / len_temp_data) * 100 if qtd_x > 0 else 0

				tmp = (n_clusters, f, len_temp_data, x, qtd_x, percentage_x)
				comodities_values.append(tmp)

			'''for x in comodities:
				qtd_a = temp_data[table == 'booking'][x].sum()
				percentage_a = (qtd_a / len_temp_data) * 100 if qtd_x > 0 else 0

				qtd_b = temp_data[table == 'booking'][x].sum()
				percentage_b = (qtd_b / len_temp_data) * 100 if qtd_x > 0 else 0

				tmp = (n_clusters, f, x, len_temp_data, qtd_a, percentage_a, qtd_b, percentage_b)
				comodities_table_values.append(tmp)'''

		if n_clusters > 1:
			clustered_data = clustered_data.drop(columns=['cluster'], inplace = True)
	comparable_comodities(data, comodities)
	create_dataframe_with_means(v_medios, region_values, room_values, comodities_values)

def join_data(da, db):
	lena = da['Unnamed: 0'].count()
	lenb = db['Unnamed: 0'].count()

	da['table'] = [ 'airbnb' for x in range(lena)]
	db['table'] = [ 'booking' for x in range(lenb)]
	
	da = da.drop(columns=['bedrooms', 'bathrooms', 'minstay', 'max_nights', 'avg_rating', 'is_superhost', \
					'rate_type', 'survey_id', 'extra_host_languages'])
	db = db.drop(columns=['images', 'state', 'room_name', 'popular_facilidades'])

	result = da.append(db, sort=False)

	writer = ExcelWriter('public/data/dados unidos_' + today + '.xlsx')
	result.to_excel(writer, sheet_name="total listings")
	writer.save()

	return result
	plot_barplot('', result, 'room_id', 'room_id', 'room_id', pp)

def plot_scatter(data, kmeans, X, type, xn, yn, pp):
	xc = data.columns.get_loc(xn) - 1
	yc = data.columns.get_loc(yn) - 1

	plt.scatter(X[:, xc], X[:, yc], s = 50, c = kmeans.labels_)
	plt.scatter(kmeans.cluster_centroids_[:, xc], kmeans.cluster_centroids_[:, yc], s = 50, c = 'red',label = 'Centroids')
	plt.title(type + ": " + xn + 'X' + yn)
	plt.xlabel(xn)
	plt.ylabel(yn)
	plt.legend()
	#plt.show()
	plt.savefig(pp, format='pdf')

def plot_barplot(table, data, xn, yn, huen, pp):
	fig, axs = plt.subplots(ncols=3)

	if table == 'airbnb':
		fig.suptitle('airbnb means', fontsize=16)
		g = sns.barplot(x='overall_satisfaction',y='price_pc',hue='cluster',data=data, ax=axs[0])
		g.axes.set_ylim(data['price_pc'].min(), data['price_pc'].max())
		g = sns.barplot(x='region',y='price_pc',hue='cluster',data=data, ax=axs[1])
		g.axes.set_ylim(data['price_pc'].min(), data['price_pc'].max())
		g = sns.barplot(x='room_type',y='price_pc',hue='cluster',data=data, ax=axs[2])
		g.axes.set_ylim(data['price_pc'].min(), data['price_pc'].max())
	elif table == 'booking':
		fig.suptitle('booking means', fontsize=16)
		g = sns.lineplot(x='overall_satisfaction',y='price',hue='cluster',data=data, ax=axs[0])
		g.axes.set_ylim(data['price'].min(), data['price'].max())
		g = sns.barplot(x='region',y='price',hue='cluster',data=data, ax=axs[1])
		g.axes.set_ylim(data['price'].min(), data['price'].max())
		g = sns.barplot(x='room_type',y='price',hue='cluster',data=data, ax=axs[2])
		g.axes.set_ylim(data['price'].min(), data['price'].max())
	else:
		fig.suptitle('airbnb + booking means', fontsize=16)
		g = sns.lineplot(x="overall_satisfaction", y="price_pc", hue="table", data=data, ax=axs[0])
		g.axes.set_ylim(data['price_pc'].min(), data['price_pc'].max())
		g = sns.barplot(x='region',y='price_pc',hue='table',data=data, ax=axs[1])
		g.axes.set_ylim(data['price_pc'].min(), data['price_pc'].max())
		g = sns.barplot(x='room_type',y='price_pc',hue='table',data=data, ax=axs[2])
		g.axes.set_ylim(data['price_pc'].min(), data['price_pc'].max())
		
	#sns.barplot(y=yn,x=xn,hue=huen,data=data);
	#plt.title("group by " + huen + " : " + xn + 'X' + yn)

	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	
	#plt.savefig(pp, format='pdf')
	#plt.show()

def plot_airbnb_and_booking(da, db, ka, kb, Xa,Xb, xn, yn):
	xc1 = da.columns.get_loc(xn) - 1
	yc1 = da.columns.get_loc(yn) - 1

	plt.scatter(Xa[:, xc1], Xa[:, yc1], s = 100, c = ka.labels_, marker = 'v')
	plt.scatter(ka.cluster_centers_[:, xc1], ka.cluster_centers_[:, yc1], s = 100, \
				c = 'green', label = "Airbnbs' centroids", marker = '.')

	xc2 = db.columns.get_loc(xn) - 1
	yc2 = db.columns.get_loc(yn) - 1
	plt.scatter(Xb[:, xc2], Xb[:, yc2], s = 100, c = kb.labels_, marker = '^')
	plt.scatter(kb.cluster_centers_[:, xc2], kb.cluster_centers_[:, yc2], s = 100, \
				c = 'red', label = "Booking's Centroids", marker = '.')

	plt.title(xn + ' x ' + yn)
	plt.xlabel(xn)
	plt.ylabel(yn)
	plt.legend()
	#plt.show()

def elbow_method(X):
	wcss = []
	for n in range(2, 21):
		kmeans = KMeans(n_clusters=n)
		try:
			kmeans.fit(X=X)
			wcss.append(kmeans.inertia_)
		except:
			continue

	x1, y1 = 2, wcss[0]
	x2, y2 = 20, wcss[len(wcss)-1]

	distances = []
	for i in range(len(wcss)):
		x0 = i+2
		y0 = wcss[i]
		numerator = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
		denominator = sqrt((y2 - y1)**2 + (x2 - x1)**2)
		distances.append(numerator/denominator)

	n = distances.index(max(distances)) + 2
	return n

	# elbow method graphic
	'''wcss = []
	for i in range(1, 11):
		kmeans = KMeans(n_clusters = i, init = 'random')
		kmeans.fit(X)
		logging.info(i,kmeans.inertia_)
		wcss.append(kmeans.inertia_)  
	plt.plot(range(1, 11), wcss)
	plt.title('O Metodo Elbow')
	plt.xlabel('Numero de Clusters')
	plt.ylabel('WSS') #within cluster sum of squares
	#plt.show()'''

	'''plt.scatter(X[:, 12], X[:, 11], s = 100, c = kmeans.labels_)
	plt.scatter(kmeans.cluster_centers_[:, 12], kmeans.cluster_centers_[:, 11], s = 100, c = 'red',label = 'Centroids')
	'''

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

	'''# Set up logging
	logger.setLevel(ab_config.log_level)

	# create a file handler
	logfile = "public/data/analised_data_{today}.log".format(today=today)
	filelog_handler = logging.FileHandler(logfile, encoding="utf-8")
	filelog_handler.setLevel(ab_config.log_level)
	filelog_formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s%(message)s')
	filelog_handler.setFormatter(filelog_formatter)

	# logging: set log file name, format, and level
	logger.addHandler(filelog_handler)

	# Suppress informational logging from requests module
	logging.getLogger("requests").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logger.propagate = False'''

	(d_airbnb, d_booking) = define_directories(config, args)
	if args.booking:
		compare_sites(table='booking', dbooking=d_booking)
	elif args.airbnb:
		compare_sites(table='airbnb', dairbnb=d_airbnb)
	else:
		compare_sites(dairbnb=d_airbnb, dbooking=d_booking)

if __name__ == "__main__":
	main()

# python clustering.py -sc "Ouro Preto" -a
# 1430 - 15:19