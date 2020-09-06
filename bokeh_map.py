import numpy as np
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, Div, Select, HoverTool, Column, Row, LabelSet, FactorRange
from bokeh.tile_providers import Vendors, get_provider
from bokeh.plotting import figure
import pandas as pd
from os.path import dirname, join
import matplotlib.pyplot as plt
from bokeh.transform import dodge
from bokeh.core.properties import value
from bokeh.models.widgets.tables import (
	DataTable, TableColumn, IntEditor
)

from random import randint

from bokeh.models import Button, TextInput, ColumnDataSource
import copy


SITE_OPTIONS = ['Airbnb', 'Booking']
COMODITIES_OPTIONS = ['academia', 'ar-condicionado', 'banheira', 'café', 'máquina',
				'estacionamento', 'piscina', 'tv', 'wifi']
REGION_OPTIONS = ['Centro', 'Distrito', 'Entorno']
ROOM_TYPE_OPTIONS = ['Entire home/apt', 'Hotel room', 'Private room', 'Shared room']
BATHROOM_OPTIONS = ['private_bathroom', 'shared_bathroom']
CATEGORY_OPTIONS = ['Quarto compartilhado com banheiro privativo', 'Quarto compartilhado com banheiro compartilhado',
				'Quarto privativo com banheiro privativo', 'Quarto privativo com banheiro compartilhado', 'Não especificado']

k = 6378137
lat_min = np.log(np.tan((90 -20.5229) * np.pi/360.0)) * k
lat_max = np.log(np.tan((90 -20.2519) * np.pi/360.0)) * k
lng_min = -43.7846 * (k * np.pi/180.0)
lng_max = -43.4372 * (k * np.pi/180.0)

colors = ['red', 'orange', 'blue', 'green', 'gray']

curdoc().clear()

def filter_data(df, site, region, room_type, cluster, price, category):
	if region != 'ALL': df = df[df.region == region]
	if room_type != 'ALL': df = df[df.room_type == room_type]
	if category != 'ALL': df = df[df.category == category]

	clusters = df['cluster'].unique().tolist()
	if int(cluster) in clusters: df = df[df.cluster == cluster]

	df = df[df.price_pc > price]

	if site != 'ALL': df = df[df.site == site]
	return df

def variable_plot(source_airbnb, source_booking, source_both):
	p=figure(x_range=[],title="Dados agrupados", y_range=(0, 100), plot_width=1300, plot_height=300)
	p.vbar(x=dodge('x', -0.25, range=p.x_range), top='top', width=0.2, source=source_airbnb,
       legend=value("Airbnb"), color="blue")
	p.vbar(x=dodge('x', 0.0, range=p.x_range), top='top', width=0.2, source=source_booking,
       legend=value("Booking"), color="red")
	p.vbar(x=dodge('x', 0.25, range=p.x_range), top='top', width=0.2, source=source_both,
       legend=value("Dados unidos"), color="purple")

	labels15=LabelSet(x=dodge('x', -0.25, range=p.x_range),y='top',text='desc',source=source_airbnb,text_align='center')
	labels16=LabelSet(x=dodge('x', 0.0, range=p.x_range),y='top',text='desc',source=source_booking,text_align='center')
	labels17=LabelSet(x=dodge('x', 0.25, range=p.x_range),y='top',text='desc',source=source_both,text_align='center')

	p.add_layout(labels15)
	p.add_layout(labels16)
	p.add_layout(labels17)
	return p

def corr_plot(source_airbnb, source_booking, source_both):
	TOOLTIPS = [
		('column:', '@x'),
		('correlation:', '@{desc}{0.3f}')
	]

	pc=figure(x_range=[],title="Correlação dos dados em relação ao preço",
		y_range=(0, 100), plot_width=1300, plot_height=600,
		tooltips=TOOLTIPS)
	pc.vbar(x=dodge('x', -0.25, range=pc.x_range), top='top', width=0.2, source=source_airbnb,
       legend=value("Airbnb"), color="blue")
	pc.vbar(x=dodge('x', 0.0, range=pc.x_range), top='top', width=0.2, source=source_booking,
       legend=value("Booking"), color="red")
	pc.vbar(x=dodge('x', 0.25, range=pc.x_range), top='top', width=0.2, source=source_both,
       legend=value("Dados unidos"), color="purple")

	pc.xaxis.major_label_orientation = 3.1415/4
	return pc

def map_plot(source):
	TOOLTIPS = [
		('name:', '@name'),
		('cluster', '@cluster'),
		('price per capita', 'R$@{price_pc}{0.2f}'),
		('overall satisfaction', '@{overall_satisfaction}{0.2f}'),
		('region', '@region'),
		('site', '@site')
	]

	tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)
	plot = figure(tools=["pan,wheel_zoom,box_zoom,reset,hover"], tooltips=TOOLTIPS,
		title='Mapa de Anúncios em Ouro Preto', toolbar_location="below",
		x_range=(lng_min, lng_max), y_range=(lat_min, lat_max),
		x_axis_type="mercator", y_axis_type="mercator",
		plot_width=1000)
	plot.xaxis.axis_label = 'Longitude'
	plot.yaxis.axis_label = 'Latitude'

	plot.add_tile(tile_provider)
	plot.circle('x','y', size=5, color='color',source=source,alpha=0.5)
	return plot

# Set up callbacks
def button1_callback():
	def get_clusterization_file_directory(kcluster, site):
		return 'public/data/dados agrupados em ' + str(kcluster) + ' clusters para ' + site + '.xlsx'

	def get_data(directory): # Set up data
		def wgs84_to_web_mercator(df, lon="LON", lat="LAT"):
			k = 6378137
			df["x"] = df[lon] * (k * np.pi/180.0)
			df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
			return df
		df = pd.read_excel(directory)
		wgs84_to_web_mercator(df, lon="longitude", lat="latitude")

		df['color'] = [ colors[x] for x in df['cluster'] ]
		return df

	def get_x_range(c):
		if c == 'region': return list(REGION_OPTIONS)
		elif c == 'room_type': return list(ROOM_TYPE_OPTIONS)
		elif c == 'category': return list(CATEGORY_OPTIONS)
		elif c == 'comodities': return list(COMODITIES_OPTIONS)
		elif c == 'bathroom': return list(BATHROOM_OPTIONS)
		elif c == 'site': return list(SITE_OPTIONS)

	def get_y_range(n):
		if n == 'overall_satisfaction': return (0, 6)
		elif n == 'price_pc': return (0, 600)
		elif n == 'quantidade': return (0, 900)

	def update_p_range(p, df, site, source):
		x_range = get_x_range(categorical_column.value)
		#(p.y_range.start, p.y_range.end) = get_y_range(numerical_column.value)
		
		p.x_range.factors = [] # <-- This is the trick, make the x_rage empty first, before assigning new value
		p.x_range.factors = x_range
		(p.y_range.start, p.y_range.end) = (0, 0)
		(p.y_range.start, p.y_range.end) = get_y_range(numerical_column.value)

		new_data = dict()
		new_data['x'] = get_x_range(categorical_column.value)
		new_data['top'] = [0, 10, 40]
		df = dataframe_for_vbar(df, site, categorical_column.value, numerical_column.value)
		source.data = dict(
			x=df['x'], top=df['top'], desc=df['desc']
			)

	def update_pc_range(pc, df, site):
		x_range = get_x_range(categorical_column.value)
		
		pc.x_range.factors = [] # <-- This is the trick, make the x_rage empty first, before assigning new value
		pc.x_range.factors = get_corr_columns(df, site)
		(pc.y_range.start, pc.y_range.end) = (-1.5, 1.5)

	def count_columns_dataframe(df, lista, column):
		values = []
		len_df= df['Unnamed: 0'].count()
		if column == 'quantidade':
			for x in lista:
				try:
					qtd_x = df[x].sum()
					pct_x = ( qtd_x / len_df) * 100
					desc = '%.2f' % pct_x + '% (' + str(qtd_x) + ')'
					values.append((x, pct_x, desc))
				except:
					continue
		else:
			for x in lista:
				try:
					qtd_x = df.query(x + '==1')[column].mean()
					pct_x = ( qtd_x / len_df) * 100
					try:
						desc =  '%.2f' % value
					except TypeError:
						desc =  str(value)
					values.append((x, qtd_x, desc))
				except:
					continue
		return pd.DataFrame(values, columns = ['x' , 'top', 'desc'])

	def dataframe_for_vbar(df, site, categorical_column, value_column):
		def average(data, x, categorical_column, column):
			if column == 'quantidade':
				return data.query(categorical_column + "=='" + x + "'")['Unnamed: 0'].count()
			return data.query(categorical_column + "=='" + x + "'")[column].mean()
		
		if site != 'Airbnb and Booking': df = df[df.site == site]
		if categorical_column in ['region', 'room_type', 'category', 'site']:
			categorical_values = []
			if categorical_column == 'region': categorical_types = REGION_OPTIONS
			elif categorical_column == 'room_type': categorical_types = ROOM_TYPE_OPTIONS
			elif categorical_column == 'category': categorical_types = CATEGORY_OPTIONS
			elif categorical_column == 'site': categorical_types = SITE_OPTIONS

			len_df= df['Unnamed: 0'].count()
			for x in categorical_types:
				value = average(df, x, categorical_column, value_column)
				
				try:
					desc =  '%.2f' % value
				except TypeError:
					desc =  str(value)
				
				categorical_values.append((x, value, desc))
			return pd.DataFrame(categorical_values, columns = ['x' , 'top', 'desc'])
		else:
			if categorical_column == 'comodities': return count_columns_dataframe(df, COMODITIES_OPTIONS, value_column)
			elif categorical_column == 'bathroom': return count_columns_dataframe(df, BATHROOM_OPTIONS, value_column)

	def get_corr_columns(df, site):
		df_corr = df
		if site != 'Airbnb and Booking': df_corr = df_corr[df_corr.site == site]
		df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id', 'Unnamed: 0', 'Unnamed: 0.1',
			'name', 'comodities', 'host_id', 'qtd_rooms', 'qtd', 'route',
			'property_type', 'sublocality', 'bed_type', 'bathroom',
			'site', 'cluster', 'room_type', 'x', 'y','color'])
		df_corr = pd.get_dummies(df_corr)
		df_corr = df_corr.corr().sort_values(by='price')
		return df_corr.index.tolist()

	def get_source_corr(df, source, site):
		df_corr = df
		if site != 'Airbnb and Booking': df_corr = df_corr[df_corr.site == site]
		df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id', 'Unnamed: 0', 'Unnamed: 0.1',
			'name', 'comodities', 'host_id', 'qtd_rooms', 'qtd', 'route',
			'property_type', 'sublocality', 'bed_type', 'bathroom',
			'site', 'cluster', 'room_type', 'x', 'y','color'])
		df_corr = pd.get_dummies(df_corr)
		df_corr = df_corr.corr().sort_values(by='price')
		columns = df_corr.index.tolist()

		valuse = []
		for c, x in zip(columns, df_corr['price']):
			valuse.append((c,x,x))
		k = pd.DataFrame(valuse, columns = ['x' , 'top', 'desc'])
		source.data=dict(x=k['x'], top=k['top'], desc=k['desc'])

	clusterization_file = get_clusterization_file_directory(kclusters.value, ksite.value)
	df = get_data(clusterization_file) #tentar fazer df['cluster'] ao inves de df.cluster
	
	if table_row.value != '': df = df.query(table_row.value)
		
	df = filter_data(df, site.value, region.value, room_type.value, cluster.value, price.value, category.value)
	source.data = dict(
		x=df['x'], y=df['y'], cluster=df['cluster'],
		price_pc=df['price_pc'], overall_satisfaction = df['overall_satisfaction'],
		region = df['region'], name = df['name'], site = df['site'],
		comodities=df['comodities'], room_id=df['room_id'], host_id=df['host_id'],
		hotel_id=df['hotel_id'], room_type=df['room_type'],
		property_type=df['property_type'], category=df['category'],
		count_host_id=df['count_host_id'], count_hotel_id=df['count_hotel_id'],color=df["color"]
	)

	update_p_range(p_airbnb, df, 'Airbnb', source_airbnb)
	update_p_range(p_airbnb, df, 'Booking', source_booking)
	update_p_range(p_airbnb, df, 'Airbnb and Booking', source_both)

	update_pc_range(p_corr, df, 'Airbnb and Booking')

	get_source_corr(df, source_corr_airbnb, 'Airbnb')
	get_source_corr(df, source_corr_booking, 'Booking')
	get_source_corr(df, source_corr_both, 'Airbnb and Booking')
	

# Set up widgets
kclusters = Slider(title="Quantidade k de clusters para clusterização", value=3, start=1, end=3)
ksite = Select(title="Site para clusterização", value='Airbnb and Booking',
	options=['Airbnb and Booking', 'Airbnb', 'Booking'])
site = Select(title="Site visualizado", value="ALL",
	options=['ALL'] + SITE_OPTIONS)
region = Select(title="Region", value="ALL",
	options=['ALL'] + REGION_OPTIONS)
room_type = Select(title="Room type", value="ALL",
	options=['ALL'] + ROOM_TYPE_OPTIONS)
category = Select(title="Categoria", value="ALL",
	options=['ALL'] + CATEGORY_OPTIONS)
cluster = Slider(title="Cluster visualizado", value=3, start=0, end=3)
price = Slider(title="Price per capita mínimo", value=0, start=0.0, end=1000) # max price
categorical_column = Select(title="Coluna categórica para visualização: ", value="category",
	options=['region', 'room_type', 'category', 'comodities', 'bathroom', 'site'])
numerical_column = Select(title="Coluna numérica para visualização: ", value="overall_satisfaction",
	options=['overall_satisfaction', 'price_pc', 'quantidade'])
table_row = TextInput(value = '', title = "Query:")
button1 = Button(label="Aplicar filtros")
button1.on_click(button1_callback)

desc = Div(text=open(join(dirname(__file__), "description.html")).read())

# Set up layouts and add to document
inputs = column(desc, button1, kclusters, ksite, categorical_column, numerical_column,
				cluster, site, region, room_type, category, price, table_row)

source = ColumnDataSource(data=dict(x=[], y=[], cluster=[], price_pc=[], overall_satisfaction=[],
	region=[], name=[], site=[], comodities=[], room_id=[], host_id=[], hotel_id=[], room_type=[],
	property_type=[], category=[], count_host_id=[],count_hotel_id=[],color=[]))
plot = map_plot(source)
source_airbnb = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_booking = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_both = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_corr_airbnb = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_corr_booking = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_corr_both = ColumnDataSource(dict(x=[],top=[],desc=[]))

p_airbnb = variable_plot(source_airbnb, source_booking, source_both)
p_corr = corr_plot(source_corr_airbnb, source_corr_booking, source_corr_both)

columns = [
	TableColumn(field="cluster", title="cluster"),
	TableColumn(field="name", title="name"),
	TableColumn(field="site", title="site"),
	TableColumn(field="category", title="category"),
	TableColumn(field="price_pc", title="price_pc"),
	TableColumn(field="overall_satisfaction", title="overall_satisfaction"),
	TableColumn(field="region", title="region"),
	TableColumn(field="room_type", title="room_type"),
	TableColumn(field="property_type", title="property_type"),
	TableColumn(field="comodities", title="comodities"),
	TableColumn(field="room_id", title="room_id"),
	TableColumn(field="host_id", title="host_id"),
	TableColumn(field="hotel_id", title="hotel_id"),
	TableColumn(field="count_host_id", title="count_host_id"),
	TableColumn(field="count_hotel_id", title="count_hotel_id")
]

data_table = DataTable(
	source=source,
	columns=columns,
	width=1300,
	editable=True,
	reorderable=False,
)

curdoc().add_root(column(row(inputs, plot, width=1000), p_airbnb, p_corr, data_table))
curdoc().title = "Mapa de anúncios em Ouro Preto"