from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, Div, Button, CustomJS
from bokeh.models import Select, HoverTool, Column, Row, LabelSet, FactorRange
from bokeh.models import Button, TextInput
from bokeh.tile_providers import Vendors, get_provider
from bokeh.plotting import figure
import pandas as pd
from bokeh.transform import dodge
from bokeh.core.properties import value
from bokeh.models.widgets.tables import (
    DataTable, TableColumn, IntEditor
)
from bokeh.embed import components
from bokeh import events
from bokeh.plotting import figure
# import datetime as dt

import utils_bokeh as ub

class Inputs():
    def __init__(self, inputs):
        self.button1 = button1
        self.cities = cities
        self.kclusters = kclusters
        self.ksite = ksite
        self.cluster = cluster
        self.site = site
        self.categorical_column = categorical_column
        self.numerical_column = numerical_column
        self.region = region
        self.room_type = room_type
        self.category = category
        self.price = price
        self.consulta = consulta

# today = dt.date.today().isoformat()

curdoc().clear()

def map_plot(source):
    TOOLTIPS = [
        ('nome:', '@name'),
        ('cluster', '@cluster'),
        ('price per capita', 'R$@{price_pc}{0.2f}'),
        ('classificação média', '@{overall_satisfaction}{0.2f}'),
        ('região', '@region'),
        ('site', '@site')
    ]
    tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)
    
    (lat_max, lat_min, lng_max, lng_min) = ub.get_coordinates('Ouro Preto')
    plot = figure(tools=["pan,wheel_zoom,box_zoom,reset,hover"], tooltips=TOOLTIPS,
        toolbar_location="below",
        x_range=(lng_min,lng_max), y_range=(lat_min, lat_max),
        x_axis_type="mercator", y_axis_type="mercator",
        min_width=1000)

    plot.xaxis.axis_label = 'Longitude'
    plot.yaxis.axis_label = 'Latitude'

    plot.add_tile(tile_provider)
    plot.circle('x','y', size=5, color='color',source=source,alpha=0.5)
        
    return plot

# Plot with variable x and y axis, grouped by distinct sites
def variable_plot(source_airbnb, source_booking, source_both):
    TOOLTIPS = [
        ('categoria', '@x'),
        ('valor', '@{desc}{0.3f}')
    ]

    p=figure(x_range=[],y_range=(0, 100), min_width=1300, min_height=300, height=500, width=1300,
            tooltips=TOOLTIPS)
    p.vbar(x=dodge('x', -0.25, range=p.x_range), top='top', width=0.2, source=source_airbnb,
        color="blue")
    p.vbar(x=dodge('x', 0.0, range=p.x_range), top='top', width=0.2, source=source_booking,
        color="red")
    p.vbar(x=dodge('x', 0.25, range=p.x_range), top='top', width=0.2, source=source_both,
        color="purple")

    '''labels15=LabelSet(x=dodge('x', -0.25, range=p.x_range),y='top',text='desc',source=source_airbnb,text_align='center')
    labels16=LabelSet(x=dodge('x', 0.0, range=p.x_range),y='top',text='desc',source=source_booking,text_align='center')
    labels17=LabelSet(x=dodge('x', 0.25, range=p.x_range),y='top',text='desc',source=source_both,text_align='center')
    
    p.add_layout(labels15)
    p.add_layout(labels16)
    p.add_layout(labels17)'''
    return p

# Plot with price correlation values, grouped by distinct sites
# def corr_plot(source_airbnb, source_booking, source_both):
#     TOOLTIPS = [
#         ('site', '@site'),
#         ('valor categórico', '@x'),
#         ('valor numérico', '@{desc}{0.3f}')
#     ]

#     pc=figure(x_range=[],
#         y_range=(0, 100), min_width=1300, min_height=600,
#         tooltips=TOOLTIPS)
#     pc.vbar(x=dodge('x', -0.25, range=pc.x_range), top='top', width=0.2, source=source_airbnb,
#         color="blue")
#     pc.vbar(x=dodge('x', 0.0, range=pc.x_range), top='top', width=0.2, source=source_booking,
#         color="red")
#     pc.vbar(x=dodge('x', 0.25, range=pc.x_range), top='top', width=0.2, source=source_both,
#         color="purple")

#     pc.xaxis.major_label_orientation = 3.1415/4
#     return pc

# Set up callbacks
def button1_callback():
    # Update x and y axis in variable plot
    # Also get the data
    def get_variable_source(p, df, site):
        x_range = ub.get_x_range(categorical_column.value)
        
        p.x_range.factors = []
        p.x_range.factors = x_range
        (p.y_range.start, p.y_range.end) = (0, 0)
        (p.y_range.start, p.y_range.end) = ub.get_y_range(numerical_column.value)

        new_data = dict()
        new_data['x'] = ub.get_x_range(categorical_column.value)
        new_data['top'] = [0, 10, 40]
        df = ub.dataframe_for_vbar(df, site, categorical_column.value, numerical_column.value)
        return df

    # def update_corr_plot_range(pc, df, site):
    #     pc.x_range.factors = [] # <-- This is the trick, make the x_rage empty first, before assigning new value
    #     pc.x_range.factors = ub.get_corr_columns(df, site)
    #     (pc.y_range.start, pc.y_range.end) = (-1.5, 1.5)

    def update_map_plot_range(plot, city):
        (lat_max, lat_min, lng_max, lng_min) = ub.get_coordinates(city)

        (plot.y_range.start, plot.y_range.end) = (lat_min, lat_max)
        (plot.x_range.start, plot.x_range.end) = (lng_min, lng_max)

    # def get_df_corr(df, site):
    #     df_corr = df
    #     if site != 'Airbnb and Booking': df_corr = df_corr[df_corr.site == site]

    #     try:
    #         df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
    #                         'Unnamed: 0', 'Unnamed: 0.1',
    #                         'name', 'comodities', 'host_id', 'qtd_rooms', 'qtd', 'route',
    #                         'property_type', 'sublocality', 'bed_type', 'bathroom',
    #                         'site', 'cluster', 'room_type', 'x', 'y','color'])
    #     except:
    #         df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
    #                         'Unnamed: 0', 'Unnamed: 0.1',
    #                         'name', 'comodities', 'host_id','route',
    #                         'property_type', 'sublocality', 'bathroom',
    #                         'site', 'cluster', 'room_type', 'x', 'y','color'])

    #     df_corr = pd.get_dummies(df_corr)
    #     df_corr = df_corr.corr().sort_values(by='price')
    #     columns = df_corr.index.tolist()

    #     print("CORR COLUMNS", columns)

    #     corr_plot_values = []
    #     for c, x in zip(columns, df_corr['price']):
    #         corr_plot_values.append((c,x,x))
    #     k = pd.DataFrame(corr_plot_values, columns = ['x' , 'top', 'desc'])
    #     k['site'] = [ site for x in k['x']]

    #     return k

    # print("VEIO AQUIIIIIIIIIIII")

    # armazena o que está no arquivo no redis
    # dessa forma, não é necessário fazer leitura do arquivo há todo momento
    odf = None
    # ub.loadFromRedis(r, 'odf_' + cities.value + str(kclusters.value))
    if odf is None:
        print("Realizando carregamento inicial dos dados")
        fdf = pd.ExcelFile('bokeh_plataform/files/dados preparados em até 3 clusters_2020-12-05.xlsx')

        for ct in ub.CITY_OPTIONS:
            for i in range(1, 4):
                print("Carregando dados de " + ct + " para " + str(i) + " clusters")
                odf = pd.read_excel(fdf, ct + ' ' + str(i))
                odf = ub.wgs84_to_web_mercator(odf, lon="longitude", lat="latitude")
                odf['color'] = [ ub.colors[x] for x in odf['cluster'] ]
                # ub.storeInRedis(r, 'odf_' + ct + str(i), odf)

    # odf = ub.loadFromRedis(r, 'odf_' + cities.value + str(kclusters.value))
    
    # verifica se o df tá armazenado, se não tiver, lê ele e armazena
    # chave_temp_data = ub.get_chave('df_', inps)
    # df = ub.loadFromRedis(r, chave_temp_data)
    
    ''' na primeira vez, sempre haverá necessidade de carregamento
    já que não haverá nada armazenado no redis'''

    ''' nem sempre é necessário filtrar a data porque os filtros de coluna catégoria e numérica
    não alteram os dados em si, apenas a visualização dos gráficos '''
    
    df = None
    if df is None:
        # and ub.necessidade_de_carregamento(r, inps):
        print("Filtrando dados e inserindo na cache")
        # print("O TAMANHO DO ORIGINAL:",odf['Unnamed: 0'].count())
        df = ub.filter_data(odf, inps)
        # print("O TAMANHO DO FILTRADO", df['Unnamed: 0'].count())
        # ub.storeInRedis(r, ub.get_chave('df_', inps), df)
    # ub.storeNewFilterValues(r, inps)
        
    source.data = dict(
        x=df['x'], y=df['y'], cluster=df['cluster'],
        price_pc=df['price_pc'], overall_satisfaction = df['overall_satisfaction'],
        region = df['region'], name = df['name'], site = df['site'],
        comodities=df['comodities'], room_id=df['room_id'], host_id=df['host_id'],
        hotel_id=df['hotel_id'], room_type=df['room_type'],
        property_type=df['property_type'], category=df['category'],
        count_host_id=df['count_host_id'], count_hotel_id=df['count_hotel_id'],color=df["color"]
    )

    # dva = ub.loadFromRedis(r, ub.get_chave('dva_', inps))
    dva = None
    # se dva é none, então dvb e dv também
    if dva is None:
        dva = get_variable_source(p_airbnb, df, 'Airbnb')
        # ub.storeInRedis(r, ub.get_chave('dva_', inps), dva)
        
        dvb = get_variable_source(p_airbnb, df, 'Booking')
        # ub.storeInRedis(r, ub.get_chave('dvb_', inps), dvb)
        
        dv = get_variable_source(p_airbnb, df, 'Airbnb and Booking')
        # ub.storeInRedis(r, ub.get_chave('dv_', inps), dv)

        source_airbnb.data = dict(
            x=dva['x'], top=dva['top'], desc=dva['desc']
        )

        source_booking.data = dict(
            x=dvb['x'], top=dvb['top'], desc=dvb['desc']
        )

        source_both.data = dict(
            x=dv['x'], top=dv['top'], desc=dv['desc']
        )

    # ATÉ A LINHA DE CIMA TÁ FUNCIONANDO

    # sca = ub.loadFromRedis(r, ub.get_chave('sca_', inps))
    sca = None
    # se sca é none, então scb e sc também
    if sca is None:
        print("")
        # sca = get_df_corr(df, 'Airbnb')
        # ub.storeInRedis(r, ub.get_chave('sca_', inps), sca)
        # source_corr_airbnb.data=dict(x=sca['x'], top=sca['top'], desc=sca['desc'], site=sca['site'])

        # scb = get_df_corr(df, 'Booking')
        # ub.storeInRedis(r, ub.get_chave('scb_', inps), scb)
        # source_corr_booking.data=dict(x=scb['x'], top=scb['top'], desc=scb['desc'], site=scb['site'])

        # sc = get_df_corr(df, 'Airbnb and Booking')
        # ub.storeInRedis(r, ub.get_chave('sc_', inps), sc)
        # source_corr_both.data=dict(x=sc['x'], top=sc['top'], desc=sc['desc'], site=sc['site'])

        # print(source_corr_airbnb.data)
        # print(source_corr_booking.data)
        # print(source_corr_both.data)

    # update_corr_plot_range(p_corr, df, 'Airbnb and Booking')
    update_map_plot_range(plot, cities.value)

r = False
# ub.connect_redis()

source = ColumnDataSource(data=dict(x=[], y=[], cluster=[], price_pc=[], overall_satisfaction=[],
    region=[], name=[], site=[], comodities=[], room_id=[], host_id=[], hotel_id=[], room_type=[],
    property_type=[], category=[], count_host_id=[],count_hotel_id=[],color=[]))
source_ksite = ColumnDataSource(data=dict(valor=[3]))
# print(source_ksite.data['valor'][0])

# Set up widgets
cities = Select(title="Cidade visualizada:", value="Ouro Preto",
                options=ub.CITY_OPTIONS)

cluster = Slider(title="Cluster visualizado (0 para ver todos)", value=0,
                start=0, end=3)
kclusters_callback = CustomJS(args=dict(cluster=cluster), code="""
    var qtd_clusters = cb_obj.value;
    cluster.value = 0;
    cluster.end = qtd_clusters;
""")
kclusters = Slider(title="Quantidade de clusters gerados", value=3,
                start=0, end=3)
kclusters.js_on_change('value', kclusters_callback)

ksite = Select(title="Site para clusterização", value='Airbnb and Booking',
    options=['Airbnb and Booking', 'Airbnb', 'Booking'])
site = Select(title="Site visualizado:", value="ALL",
    options=['ALL'] + ub.SITE_OPTIONS)
ksite_callback = CustomJS(args=dict(site=site, op_totais_site=['ALL'] + ub.SITE_OPTIONS), code="""
    var site_clusterizacao = cb_obj.value;
    if ( site_clusterizacao !== 'Airbnb and Booking') {
        site.options = [ site_clusterizacao ];
        site.value = site_clusterizacao;
    } else {
        site.options = op_totais_site;
        site.value = op_totais_site[0];
    }
""")
ksite.js_on_change('value', ksite_callback)

region = Select(title="Região visualizada:", value="ALL",
    options=['ALL'] + ub.REGION_OPTIONS)
room_type = Select(title="Tipo de quarto visualizado:", value="ALL",
    options=['ALL'] + ub.ROOM_TYPE_OPTIONS)
category = Select(title="Categoria visualizada:", value="ALL",
    options=['ALL'] + ub.CATEGORY_OPTIONS)

price = Slider(title="Price per capita mínimo", value=0, start=0.0, end=1000) # max price

categorical_column = Select(title="Coluna categórica para visualização no gráfico: ", value="category",
    options=['region', 'room_type', 'category', 'comodities', 'bathroom', 'site'])
numerical_column = Select(title="Coluna numérica para visualização no gráfico:", value="quantidade",
    options=['overall_satisfaction', 'price_pc', 'quantidade'])
cat_callback = CustomJS(args=dict(numerical_column=numerical_column,
                                    op = ['overall_satisfaction', 'price_pc', 'quantidade'],
                                    op2=['quantidade']), code="""
    var cat_col = cb_obj.value;
    if ( cat_col !== 'comodities' && cat_col !== 'bathroom' ) {
        numerical_column.options = op;
    } else {
        numerical_column.options = op2;
        numerical_column.value = op2[0];
    }
""")
categorical_column.js_on_change('value', cat_callback)

consulta = TextInput(value = '', title = "Deseja aplicar outro filtro? Digite aqui!")
button1 = Button(label="Aplicar filtros")
button1.on_click(button1_callback)


div = Div(text="""<h1 class="h3 mb-2 text-gray-800">Mapa de atuação da indústria hoteleira em Ouro Preto</h1>
          <p class="mb-4">Pesquisa desenvolvida por Victor Martins sob orientação do professor Anderson Ferreira, da professora Amanda Nascimento
          e co-orentação do professor Rodrigo Martoni durante o período de março de 2020 à março de 2021.
          Com o intuito de analisar os impactos do Airbnb na economia e na legislação local, foram coletados
          anúncios tanto para a plataforma referida quanto para o Booking, plataforma que aqui representa a
          indústria hoteleira tradicional.</p>
        <p></p>""")

''' <p>Deseja baixar os dados que foram coletados? Clique
    <a href="download/bokeh_plataform/files/dados preparados em até 3 clusters_2020-12-05.xlsx"
    download="Dados preparados.xlsx">aquit</a>
    para baixar os dados após pré-preparação para exibição neste site. '''

divMapa = Div(text="""<h3>Mapa de anúncios</h3>
    No mapa estão exibidos os anúncios de forma geográfica. Aqui, é possível passar o mouse
    por determinados anúncios para observar algumas de suas características específicas, tais como o nome,
    preço per capita e classificação média.
    """)

divVariable = Div(text="""<h3>Visão geral dos dados (coluna categórica x numérica)</h3>
                    São exibidos alguns dados de interesse de acordo com os filtros de coluna categórica
                    e coluna numérica de interesse, sendo agrupados os dados tanto por essas categorias quanto,
                    também, pelo site (Airbnb, Booking e a soma de ambos).
                    Passe o mouse pelos campos para observar os números.""")

# divCorr = Div(text="""<h3>Correlação do preço em relação às demais características</h3>
#                     Nesse gráfico, está exposta a relação da variável preço com as demais características
#                     que foram coletados. Um valor próximo de 1 indica uma relação proporcional, onde ambos
#                     crescem juntos, um valor próximo de -1 indica um decréscimo no preço a medida que a outra
#                     coluna cresce e um valor próximo de 0 indica uma relação fraca. Passe o mouse pelos
#                     campos para observar os números absolutos.""")

divTable = Div(text="""<h3>Os dados em si</h3>
                Na tabela estão presentes todos os anúncios que são visualizados no mapa.""")

inps = Inputs((button1,
        cities,
        kclusters, cluster, site, categorical_column, numerical_column,
        region, room_type, category, price, consulta))

plot = map_plot(source)
source_airbnb = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_booking = ColumnDataSource(dict(x=[],top=[],desc=[]))
source_both = ColumnDataSource(dict(x=[],top=[],desc=[]))
# source_corr_airbnb = ColumnDataSource(dict(x=[],top=[],desc=[], site=[]))
# source_corr_booking = ColumnDataSource(dict(x=[],top=[],desc=[], site=[]))
# source_corr_both = ColumnDataSource(dict(x=[],top=[],desc=[], site=[]))

p_airbnb = variable_plot(source_airbnb, source_booking, source_both)
# p_corr = corr_plot(source_corr_airbnb, source_corr_booking, source_corr_both)

point_events = [
    events.Tap, events.DoubleTap, events.Press, events.PressUp,
    events.MouseMove, events.MouseEnter, events.MouseLeave,
    events.PanStart, events.PanEnd, events.PinchStart, events.PinchEnd,
]

columns = [
    TableColumn(title="cluster", field="cluster"),
    TableColumn(title="nome", field="name"),
    TableColumn(title="site", field="site"),
    TableColumn(title="categoria", field="category"),
    TableColumn(title="price per capita", field="price_pc"),
    TableColumn(title="classificação média", field="overall_satisfaction"),
    TableColumn(title="região", field="region"),
    TableColumn(title="tipo de quarto", field="room_type"),
    TableColumn(title="tipo de propriedade", field="property_type"),
    TableColumn(title="comodidades", field="comodities"),
    TableColumn(title="identificador do quarto", field="room_id"),
    TableColumn(title="identificador do anfitrião para airbnb", field="host_id"),
    TableColumn(title="identificador do hotel para booking", field="hotel_id"),
    TableColumn(title="quantidade de anúncios para o anfitrião", field="count_host_id"),
]

data_table = DataTable(
    source=source,
    columns=columns,
    width=1300,
    editable=True,
    reorderable=False,
)

inputs = column(kclusters, ksite,
                # cities,
                cluster, site, categorical_column, numerical_column,
                region, room_type, category, price, consulta, button1)
layout = column(div, row(inputs, column(divMapa, plot), width=1000),
                column(divVariable, p_airbnb),
                #  column(divCorr, p_corr),
                column(divTable, data_table))
curdoc().add_root(layout)
curdoc().title = "Mapa de anúncios em Ouro Preto"