''' Present an interactive function explorer with slider widgets.
Scrub the sliders to change the properties of the ``sin`` curve, or
type into the title text box to update the title of the plot.
Use the ``bokeh serve`` command to run the example by executing:
    bokeh serve sliders.py
at your command prompt. Then navigate to the URL
    http://localhost:5006/sliders
in your browser.
'''
import numpy as np
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, Div, Select, HoverTool, Column, Row, LabelSet
from bokeh.tile_providers import Vendors, get_provider
from bokeh.plotting import figure
import pandas as pd
from os.path import dirname, join
import matplotlib.pyplot as plt

def create_map(total_clusters):
	k = 6378137
	lat_min = np.log(np.tan((90 -20.5229) * np.pi/360.0)) * k
	lat_max = np.log(np.tan((90 -20.2519) * np.pi/360.0)) * k
	lng_min = -43.7846 * (k * np.pi/180.0)
	lng_max = -43.4372 * (k * np.pi/180.0)

	colors = ['red', 'orange', 'blue', 'green', 'gray']

	def get_data(): # Set up data
		def wgs84_to_web_mercator(df, lon="LON", lat="LAT"):
		  	k = 6378137
		  	df["x"] = df[lon] * (k * np.pi/180.0)
		  	df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
		  	return df
		df = pd.read_excel('public/data/dados agrupados em ' + str(total_clusters) + ' clusters para airbnb + booking.xlsx')
		wgs84_to_web_mercator(df, lon="longitude", lat="latitude")

		df['color'] = [ colors[x] for x in df['cluster'] ]
		return df

	def filter_data(df, site, region, room_type, cluster, price):
		if region != 'ALL':
			df = df[df.region == region]

		if room_type != 'ALL':
			df = df[df.room_type == room_type]

		clusters = df['cluster'].unique().tolist()
		if int(cluster) in clusters:
			df = df[df.cluster == cluster]

		df = df[df.price_pc < price]

		if site != 'ALL':
			df = df[df.site == site]
		return df

	def plot_vbar(source, x, top, x_label, y_label, x_range, y_range, plot_width):
		p = figure(x_range=x_range, y_range=y_range,
					plot_width=plot_width, plot_height=200)
		labels = LabelSet(x=x, y=top, text='desc', level='glyph',
		        	x_offset=-13.5, y_offset=0, source=source, render_mode='canvas',
		        	text_font_size="7pt")
		p.vbar(x=x, width = 0.5, top=top, source=source, color="firebrick")
		p.xaxis.axis_label = x_label #'Region'
		p.yaxis.axis_label = y_label #'Overall satisfaction'
		p.add_layout(labels)
		return p

	def plot_hbar(source, x, top, x_label, y_label, x_range, y_range, plot_width):
		p = figure(y_range=x_range, x_range=y_range,
					plot_width=1300, plot_height=plot_width)
		labels = LabelSet(y=x, x=top, text='desc', level='glyph',
		        	y_offset=-7.5, x_offset=3, source=source, render_mode='canvas',
		        	text_font_size="9pt")
		p.hbar(y=x, height = 0.5, right=top, source=source, color="orange")
		p.xaxis.axis_label = x_label #'Region'
		p.yaxis.axis_label = y_label #'Overall satisfaction'
		p.add_layout(labels)
		return p

	source = ColumnDataSource(data=dict(x=[], y=[], cluster=[], price_pc=[], overall_satisfaction=[],
		region=[], name=[], site=[], color=[]))
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

	source_region_os = ColumnDataSource(dict(x=[],top=[],desc=[]))
	source_room_type_os = ColumnDataSource(dict(x=[],top=[],desc=[]))
	source_region_p = ColumnDataSource(dict(x=[],top=[],desc=[]))
	source_room_type_p = ColumnDataSource(dict(x=[],top=[],desc=[]))
	source_comodities = ColumnDataSource(dict(x=[],top=[],desc=[]))
	p1 = plot_vbar(source_region_os, 'x', 'top', 'Region', 'Overall satisfaction',
					['Centro', 'Distrito', 'Entorno'], (0, 6), 300)
	p2 = plot_vbar(source_room_type_os, 'x', 'top', 'Room type', 'Overall satisfaction',
					['Entire home/apt', 'Hotel room', 'Private room', 'Shared room'], (0, 6), 360)
	p3 = plot_vbar(source_region_p, 'x', 'top', 'Region', 'Price per capita',
					['Centro', 'Distrito', 'Entorno'], (0, 400), 300)
	p4 = plot_vbar(source_room_type_p, 'x', 'top', 'Room type', 'Price per capita',
					['Entire home/apt', 'Hotel room', 'Private room', 'Shared room'], (0, 400), 360)
	p_comodities = plot_hbar(source_comodities, 'x', 'top', 'Quantidade', 'Comodities',
					['academia', 'ar-condicionado', 'banheira', 'café', 'máquina',
       				'estacionamento', 'piscina', 'tv', 'wifi'], (0, 100), 360)
	desc = Div(text=open(join(dirname(__file__), "description.html")).read(), sizing_mode="stretch_width")

	# Set up widgets
	site = Select(title="Site", value="ALL",
		options=['ALL', 'Airbnb', 'Booking'])
	region = Select(title="Region", value="ALL",
		options=['ALL', 'Centro', 'Entorno', 'Distrito'])
	room_type = Select(title="Room type", value="ALL",
		options=['ALL', 'Entire home/apt', 'Private room', 'Hotel room', 'Shared room'])
	cluster = Slider(title="Cluster", value=3, start=0, end=total_clusters)
	price = Slider(title="Price per capita", value=300.0, start=0.0, end=500) # max price

  	# Set up callbacks
	def dataframe_for_vbar(df, categorical_column, value_column):
		def average_room_type(data, room_type, column):
			return data[data.room_type == room_type][column].mean()

		def average_region_type(data, region, column):
			return data[data.region == region][column].mean()

		categorical_values = []
		if categorical_column == 'region': categorical_types = df['region'].unique().tolist()
		if categorical_column == 'room_type': categorical_types = df['room_type'].unique().tolist()

		len_df= df['room_id'].count()
		for x in categorical_types:
			if categorical_column == 'region':
				avg_value = average_region_type(df, x, value_column)
			if categorical_column == 'room_type':
				avg_value = average_room_type(df, x, value_column)
			desc = '%.2f' % avg_value
			categorical_values.append((x, avg_value, desc))
		return pd.DataFrame(categorical_values, columns = ['x' , 'top', 'desc'])
	
	def comodities_graph(df, comodities):
		comodities_values = []
		len_df= df['room_id'].count()
		for x in comodities:
			qtd_x = df[x].sum()
			pct_x = ( qtd_x / len_df) * 100
			desc = '%.2f' % pct_x + '% (' + str(qtd_x) + ')'
			comodities_values.append((x, pct_x, desc))
		return pd.DataFrame(comodities_values, columns = ['x' , 'top', 'desc'])

	def update():
		df = get_data() #tentar fazer df['cluster'] ao inves de df.cluster
		df = filter_data(df, site.value, region.value, room_type.value, cluster.value, price.value)
		source.data = dict(
		  	x=df['x'],
		  	y=df['y'],
		  	cluster=df['cluster'],
		  	price_pc=df['price_pc'],
		  	overall_satisfaction = df['overall_satisfaction'],
		  	region = df['region'],
		  	name = df['name'],
		  	site = df['site'],
		  	color=df["color"]
		)

		comodities = list((df.columns[28:])[:-2])
		df_comodities = comodities_graph(df, comodities)
		source_comodities.data = dict(x=df_comodities['x'], top=df_comodities['top'], desc=df_comodities['desc'])

		df_region_os = dataframe_for_vbar(df, 'region', 'overall_satisfaction')
		source_region_os.data = dict(x=df_region_os['x'], top=df_region_os['top'], desc=df_region_os['desc'])
		
		df_room_type_os = dataframe_for_vbar(df,'room_type', 'overall_satisfaction')
		source_room_type_os.data = dict(x=df_room_type_os['x'], top=df_room_type_os['top'], desc=df_room_type_os['desc'])
		
		df_region_p = dataframe_for_vbar(df, 'region', 'price_pc')
		source_region_p.data = dict(x=df_region_p['x'], top=df_region_p['top'], desc=df_region_p['desc'])
		
		df_room_type_p = dataframe_for_vbar(df,'room_type', 'price_pc')
		source_room_type_p.data = dict(x=df_room_type_p['x'], top=df_room_type_p['top'], desc=df_room_type_p['desc'])
      
	controls = [site, region, room_type, cluster, price]
	for control in controls:
		control.on_change('value', lambda attr, old, new: update())

	# Set up layouts and add to document
	inputs = column(desc, site, region, room_type, cluster, price)

	update()  # initial load of the data

	curdoc().add_root(column(row(inputs, plot, width=800),  row(p1, p2, p3, p4), p_comodities))
	curdoc().title = "Mapa de anúncios em Ouro Preto"

create_map(3)