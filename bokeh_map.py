import numpy as np
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, Div, Button, CustomJS
from bokeh.models import Select, HoverTool, Column, Row, LabelSet, FactorRange
from bokeh.models import Button, TextInput
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
import copy
import argparse
from bokeh.embed import components
from bokeh import events
from bokeh.plotting import figure

import os
import redis

try:
	r = redis.from_url(os.environ.get("REDIS_URL"))
except:
	r = 'redis://:p1653267bfcf309937d2be15e0ec9fbda4b87ff5ccb6d03d5d7b7244270368c48@ec2-54-159-105-72.compute-1.amazonaws.com:9949'

SITE_OPTIONS = ['Airbnb', 'Booking']
COMODITIES_OPTIONS = ['academia', 'ar-condicionado', 'banheira', 'café', 'máquina',
                'estacionamento', 'piscina', 'tv', 'wifi']
REGION_OPTIONS = ['Centro', 'Distrito', 'Entorno']
ROOM_TYPE_OPTIONS = ['Entire home/apt', 'Hotel room', 'Private room', 'Shared room']
BATHROOM_OPTIONS = ['private_bathroom', 'shared_bathroom']
CATEGORY_OPTIONS = ['Quarto compartilhado com banheiro privativo',
                    'Quarto compartilhado com banheiro compartilhado',
                    'Quarto privativo com banheiro privativo',
                    'Quarto privativo com banheiro compartilhado']
CITY_OPTIONS = [ 'Diamantina', 'Ouro Preto', 'Tiradentes']

colors = ['red', 'orange', 'blue', 'green', 'gray']

curdoc().clear()

def get_coordinates(city):
    k = 6378137

    if city == 'Ouro Preto':
        lat_min = -20.5229
        lat_max = -20.2519
        lng_min = -43.7846
        lng_max = -43.4372
    elif city == 'Diamantina':
        lat_max = -17.3788619
        lat_min = -18.4465918
        lng_max = -43.217604
        lng_min = -44.0883539
    elif city == 'Tiradentes':
        lat_max = -21.0523569
        lat_min = -21.1787859
        lng_max = -44.0919139
        lng_min = -44.2244889

    lat_min = np.log(np.tan((90 + lat_min ) * np.pi/360.0)) * k
    lat_max = np.log(np.tan((90 + lat_max) * np.pi/360.0)) * k
    lng_min = lng_min * (k * np.pi/180.0)
    lng_max = lng_max * (k * np.pi/180.0)

    return (lat_max, lat_min, lng_min, lng_max)

def filter_data(df, site, region, room_type, cluster, price, category):
    if region != 'ALL': df = df[df.region == region]
    if room_type != 'ALL': df = df[df.room_type == room_type]
    if category != 'ALL': df = df[df.category == category]

    clusters = df['cluster'].unique().tolist()
    if int(cluster) in clusters: df = df[df.cluster == cluster]

    df = df[df.price_pc > price]

    if site != 'ALL': df = df[df.site == site]
    return df

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
    
    (lat_max, lat_min, lng_min, lng_max) = get_coordinates('Ouro Preto')
    plot = figure(tools=["pan,wheel_zoom,box_zoom,reset,hover"], tooltips=TOOLTIPS,
        title='Mapa de Anúncios em Ouro Preto', toolbar_location="below",
        x_range=(lng_min,lng_max), y_range=(lat_min, lat_max),
        x_axis_type="mercator", y_axis_type="mercator",
        plot_width=1000)

    plot.xaxis.axis_label = 'Longitude'
    plot.yaxis.axis_label = 'Latitude'

    plot.add_tile(tile_provider)
    plot.circle('x','y', size=5, color='color',source=source,alpha=0.5)
        
    return plot

# Plot with variable x and y axis, grouped by distinct sites
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

# Plot with price correlation values, grouped by distinct sites
def corr_plot(source_airbnb, source_booking, source_both):
    TOOLTIPS = [
        ('site', '@site'),
        ('column', '@x'),
        ('correlation', '@{desc}{0.3f}')
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

# Set up callbacks
def button1_callback():
    def get_clusterization_file_directory(city, kcluster, site):
        return 'files/' + city + '_dados agrupados em ' + str(kcluster) + ' clusters para ' + site + '.xlsx'

    def get_data(directory): # Set up data
        # Convert coordinate values to web_mercator for use in plot
        def wgs84_to_web_mercator(df, lon="LON", lat="LAT"):
            k = 6378137
            df["x"] = df[lon] * (k * np.pi/180.0)
            df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
            return df
        df = pd.read_excel(directory)
        wgs84_to_web_mercator(df, lon="longitude", lat="latitude")

        df['color'] = [ colors[x] for x in df['cluster'] ]
        return df

    # Get x range for variable plot
    def get_x_range(c):
        if c == 'region': return list(REGION_OPTIONS)
        elif c == 'room_type': return list(ROOM_TYPE_OPTIONS)
        elif c == 'category': return list(CATEGORY_OPTIONS)
        elif c == 'comodities': return list(COMODITIES_OPTIONS)
        elif c == 'bathroom': return list(BATHROOM_OPTIONS)
        elif c == 'site': return list(SITE_OPTIONS)

    # Get y range for variable plot
    def get_y_range(n):
        if n == 'overall_satisfaction': return (0, 6)
        elif n == 'price_pc': return (0, 700)
        elif n == 'quantidade': return (0, 1000)

    # Update x and y axis in variable plot
    # Also get the data
    def update_variable_plot_range(p, df, site, variable_source):
        x_range = get_x_range(categorical_column.value)
        
        p.x_range.factors = []
        p.x_range.factors = x_range
        (p.y_range.start, p.y_range.end) = (0, 0)
        (p.y_range.start, p.y_range.end) = get_y_range(numerical_column.value)

        new_data = dict()
        new_data['x'] = get_x_range(categorical_column.value)
        new_data['top'] = [0, 10, 40]
        df = dataframe_for_vbar(df, site, categorical_column.value, numerical_column.value)
        variable_source.data = dict(
            x=df['x'], top=df['top'], desc=df['desc']
        )

    def update_corr_plot_range(pc, df, site):
        x_range = get_x_range(categorical_column.value)
        
        pc.x_range.factors = [] # <-- This is the trick, make the x_rage empty first, before assigning new value
        pc.x_range.factors = get_corr_columns(df, site)
        (pc.y_range.start, pc.y_range.end) = (-1.5, 1.5)

    def update_map_plot_range(plot, city):
        (lat_max, lat_min, lng_max, lng_min) = get_coordinates(city)

        (plot.y_range.start, plot.y_range.end) = (lat_min, lat_max)
        (plot.x_range.start, plot.x_range.end) = (lng_min, lng_max)

    # Get source data for columns if boolean logic (0 or 1)
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

    # Get source data for columns with non boolean values
    # For example, region == 'Centro', not Centro == 1
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
        try:
            df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
                            'Unnamed: 0', 'Unnamed: 0.1',
                            'name', 'comodities', 'host_id', 'qtd_rooms', 'qtd', 'route',
                            'property_type', 'sublocality', 'bed_type', 'bathroom',
                            'site', 'cluster', 'room_type', 'x', 'y','color'])
        except:
            df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
                            'Unnamed: 0', 'Unnamed: 0.1',
                            'name', 'comodities', 'host_id','route',
                            'property_type', 'sublocality', 'bathroom',
                            'site', 'cluster', 'room_type', 'x', 'y','color'])
        df_corr = pd.get_dummies(df_corr)
        df_corr = df_corr.corr().sort_values(by='price')
        return df_corr.index.tolist()

    def get_source_corr(df, source, site):
        df_corr = df
        if site != 'Airbnb and Booking': df_corr = df_corr[df_corr.site == site]

        try:
            df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
                            'Unnamed: 0', 'Unnamed: 0.1',
                            'name', 'comodities', 'host_id', 'qtd_rooms', 'qtd', 'route',
                            'property_type', 'sublocality', 'bed_type', 'bathroom',
                            'site', 'cluster', 'room_type', 'x', 'y','color'])
        except:
            df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
                            'Unnamed: 0', 'Unnamed: 0.1',
                            'name', 'comodities', 'host_id','route',
                            'property_type', 'sublocality', 'bathroom',
                            'site', 'cluster', 'room_type', 'x', 'y','color'])

        df_corr = pd.get_dummies(df_corr)
        df_corr = df_corr.corr().sort_values(by='price')
        columns = df_corr.index.tolist()

        corr_plot_values = []
        for c, x in zip(columns, df_corr['price']):
            corr_plot_values.append((c,x,x))
        k = pd.DataFrame(corr_plot_values, columns = ['x' , 'top', 'desc'])
        k['site'] = [ site for x in k['x']]
        source.data=dict(x=k['x'], top=k['top'], desc=k['desc'], site=k['site'])

    clusterization_file = get_clusterization_file_directory(cities.value, kclusters.value, ksite.value)
    df = get_data(clusterization_file) #tentar fazer df['cluster'] ao inves de df.cluster
    
    if table_row.value != '': df = df.query(table_row.value)
        
    df = filter_data(df, site.value, region.value, room_type.value,
                    cluster.value, price.value, category.value)
    source.data = dict(
        x=df['x'], y=df['y'], cluster=df['cluster'],
        price_pc=df['price_pc'], overall_satisfaction = df['overall_satisfaction'],
        region = df['region'], name = df['name'], site = df['site'],
        comodities=df['comodities'], room_id=df['room_id'], host_id=df['host_id'],
        hotel_id=df['hotel_id'], room_type=df['room_type'],
        property_type=df['property_type'], category=df['category'],
        count_host_id=df['count_host_id'], count_hotel_id=df['count_hotel_id'],color=df["color"]
    )

    update_variable_plot_range(p_airbnb, df, 'Airbnb', source_airbnb)
    update_variable_plot_range(p_airbnb, df, 'Booking', source_booking)
    update_variable_plot_range(p_airbnb, df, 'Airbnb and Booking', source_both)

    update_corr_plot_range(p_corr, df, 'Airbnb and Booking')
    update_map_plot_range(plot, cities.value)

    get_source_corr(df, source_corr_airbnb, 'Airbnb')
    get_source_corr(df, source_corr_booking, 'Booking')
    get_source_corr(df, source_corr_both, 'Airbnb and Booking')

# Set up widgets
cities = Select(title="Cidade visualizada", value="Ouro Preto",
    options=CITY_OPTIONS)
kclusters = Select(title="Quantidade k de clusters para clusterização",
                value='3', options=['1', '2', '3'])
ksite = Select(title="Site para clusterização", value='Airbnb and Booking',
    options=['Airbnb and Booking', 'Airbnb', 'Booking'])
site = Select(title="Site visualizado", value="ALL",
    options=['ALL'] + SITE_OPTIONS)
region = Select(title="Região", value="ALL",
    options=['ALL'] + REGION_OPTIONS)
room_type = Select(title="Tipo de quarto", value="ALL",
    options=['ALL'] + ROOM_TYPE_OPTIONS)
category = Select(title="Categoria", value="ALL",
    options=['ALL'] + CATEGORY_OPTIONS)
cluster = Slider(title="Cluster visualizado", value=3, start=0, end=3)
price = Slider(title="Price per capita mínimo", value=0, start=0.0, end=1000) # max price
categorical_column = Select(title="Coluna categórica para visualização no gráfico: ", value="category",
    options=['region', 'room_type', 'category', 'comodities', 'bathroom', 'site'])
numerical_column = Select(title="Coluna numérica para visualização no gráfico: ", value="quantidade",
    options=['overall_satisfaction', 'price_pc', 'quantidade'])
table_row = TextInput(value = '', title = "Query:")
button1 = Button(label="Aplicar filtros")
button1.on_click(button1_callback)

div = Div(text="""<h1 class="h3 mb-2 text-gray-800">Mapa de atuação da indústria hoteleira em Ouro Preto</h1>
          <p class="mb-4">Pesquisa desenvolvida por Victor Martins sob orientação da professora Amanda Nascimento
          e co-orentação do professor Rodrigo Martoni durante o período de março de 2020 à março de 2021.
          Com o intuito de analisar os impactos do Airbnb na economia e na legislação local, foram coletados
          anúncios tanto para a plataforma referida quanto para o Booking, plataforma que aqui representa a
          indústria hoteleira tradicional.

          <p> Quer saber mais sobre o projeto ou está em dúvidas de como interagir com os filtros? Talvez
          este link <a target="_blank" href="https://github.com/VictorHugoMartins/airbnb-data-collection/blob/master/README.md">aqui</a> possa ser útil.</p>""")

inputs = column(button1, cities, kclusters, ksite, cluster, site, categorical_column, numerical_column,
                region, room_type, category, price, table_row)

source = ColumnDataSource(data=dict(x=[], y=[], cluster=[], price_pc=[], overall_satisfaction=[],
    region=[], name=[], site=[], comodities=[], room_id=[], host_id=[], hotel_id=[], room_type=[],
    property_type=[], category=[], count_host_id=[],count_hotel_id=[],color=[]))

plot = map_plot(source)
source_airbnb = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_booking = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_both = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_corr_airbnb = ColumnDataSource(dict(x=[],top=[],desc=[], site=[]))
source_corr_booking = ColumnDataSource(dict(x=[],top=[],desc=[], site=[]))
source_corr_both = ColumnDataSource(dict(x=[],top=[],desc=[], site=[]))

p_airbnb = variable_plot(source_airbnb, source_booking, source_both)
p_corr = corr_plot(source_corr_airbnb, source_corr_booking, source_corr_both)

point_events = [
    events.Tap, events.DoubleTap, events.Press, events.PressUp,
    events.MouseMove, events.MouseEnter, events.MouseLeave,
    events.PanStart, events.PanEnd, events.PinchStart, events.PinchEnd,
]

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
    TableColumn(field="count_host_id", title="host_id (qtd total)"),
    TableColumn(field="count_hotel_id", title="hotel_id (qtd total)")
]

data_table = DataTable(
    source=source,
    columns=columns,
    width=1300,
    editable=True,
    reorderable=False,
)

layout = column(div, row(inputs, plot, width=1000), p_airbnb, p_corr, data_table)
curdoc().add_root(layout)
curdoc().title = "Mapa de anúncios em Ouro Preto"