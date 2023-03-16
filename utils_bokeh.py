import os
# import redis
# import pyarrow as pa
import pandas as pd
import numpy as np
import re

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
CITY_OPTIONS = [ 'Ouro Preto']

colors = ['red', 'orange', 'blue', 'green', 'gray']

# def connect_redis():
#     try:
#         return redis.from_url(os.environ.get("REDIS_URL"))
#     except:
#         return redis.from_url('redis://:p0a5ac88ade982df103ad8617909c3dc69d90d86f2de775ffdc2c1f0e07c1a905@ec2-23-21-231-30.compute-1.amazonaws.com:13679')

# def storeInRedis(r, alias, df):
#     df_compressed = pa.serialize(df).to_buffer().to_pybytes()
#     res = r.set(alias,df_compressed)
#     if res == True:
#         print(f'{alias} cached')

# def loadFromRedis(r, alias):
#     data = r.get(alias)
#     try:
#         return pa.deserialize(data)
#     except:
#         #print("No data")
#         return None

def houve_mudanca(r, valorAtual, chave):
    if ( r.get(chave) != valorAtual ):
        print("Houve mudanca em " + chave)
    return ( r.get(chave) != valorAtual )

def necessidade_de_carregamento(r, inps):
    return ( houve_mudanca(r, inps.kclusters.value, 'kclusters') or
            houve_mudanca(r, inps.ksite.value, 'ksite') or
            houve_mudanca(r, inps.site.value, 'site') or
            houve_mudanca(r, inps.cities.value, 'cities') or
            houve_mudanca(r, inps.cluster.value, 'cluster') or
            houve_mudanca(r, inps.room_type.value, 'room_type.value') or
            houve_mudanca(r, inps.region.value, 'region') or
            houve_mudanca(r, inps.price.value, 'price') or
            houve_mudanca(r, inps.consulta.value, 'consulta') or
            houve_mudanca(r, inps.category.value, 'category') )

def storeNewFilterValues(r, inps):
    r.set('kclusters', inps.kclusters.value)
    r.set('ksite', inps.ksite.value)
    r.set('site', inps.site.value)
    r.set('cities', inps.cities.value)
    r.set('cluster', inps.cluster.value)
    r.set('room_type.value', inps.room_type.value)
    r.set('region', inps.region.value)
    r.set('price', inps.price.value)
    r.set('consulta', inps.consulta.value)
    r.set('category', inps.category.value)
    r.set('kclusters', inps.kclusters.value)

# def carregamento_redis(city, kclusters, ksite, site, regiao, tipoDeQuarto, categoria, price):
#     ub.storeInRedis('cidade', city)
#     ub.storeInRedis('kclusters', kClusters)
#     ub.storeInRedis('ksite', kSite)
#     ub.storeInRedis('site', site)
#     ub.storeInRedis('regiao', regiao)
#     ub.storeInRedis('tipodequarto', tipoDeQuarto)
#     ub.storeInRedis('categoria', categoria)
#     ub.storeInRedis('cluster', cluster)
#     ub.storeInRedis('price', price)

def get_chave(tipo, inps):
    chave = tipo
    chave = chave + 'kcl' + str(inps.kclusters.value)
    chave = chave + 'ks' + inps.ksite.value
    chave = chave + 'st' + inps.site.value
    chave = chave + 'ct' + inps.cities.value
    chave = chave + 'cl' + str(inps.cluster.value)
    chave = chave + 'rt' + inps.room_type.value
    chave = chave + 'rg' + inps.region.value
    chave = chave + 'pc' + str(inps.price.value)
    chave = chave + 'cons' + inps.consulta.value
    chave = chave + 'cat' + inps.category.value
    chave = chave + 'c_col' + inps.categorical_column.value
    chave = chave + 'n_col' + inps.numerical_column.value

    #chave = re.sub(r' ', '', chave)

    return chave

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

def filter_data(df, inps):
    query = 'price_pc > ' + str(inps.price.value) + ' & cidade == "' + inps.cities.value + \
            '" & total_clusters == ' + str(inps.kclusters.value) + \
            ' & table == "' + inps.ksite.value + '"'

    if inps.region.value != 'ALL': query = query + ' & region == "' + inps.region.value  + '"'
    if inps.room_type.value != 'ALL': query = query + ' & room_type == "' + inps.room_type.value  + '"'
    if inps.category.value != 'ALL': query = query + ' & category == "' + inps.category.value + '"'
    if inps.site.value != 'ALL': query = query + ' & site == "' + inps.site.value  + '"'
    if inps.consulta.value != '': query = query + ' & ' + inps.consulta.value
    
    clusters = df['cluster'].unique().tolist()
    if int(inps.cluster.value - 1) in clusters: query = query + ' cluster == ' + str(inps.cluster.value - 1)

    # print("AO QUERY", query)
    # df = df.query(query)

    return df

def wgs84_to_web_mercator(df, lon="LON", lat="LAT"):
    k = 6378137
    df["x"] = df[lon] * (k * np.pi/180.0)
    df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k
    return df
    
def get_data(directory): # Set up data
    # Convert coordinate values to web_mercator for use in plot
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

def mudanca_arquivo(kClustersAntigo, kclusters, cityAntigo, cities, siteAntigo, ksite):
    return ( kClustersAntigo != kclusters or
           cityAntigo != cities or
           siteAntigo != ksite )

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
                        'Unnamed: 0', 'Unnamed: 0.1', 'qtd_rooms',
                        'name', 'comodities', 'host_id', 'qtd_rooms', 'qtd', 'route',
                        'property_type', 'sublocality', 'bed_type', 'bathroom',
                        'site', 'cluster', 'room_type', 'x', 'y','color'])
    except:
        df_corr = df_corr.drop(columns=['latitude', 'longitude', 'room_id',
                        'Unnamed: 0', 'Unnamed: 0.1', 'qtd_rooms',
                        'name', 'comodities', 'host_id','route',
                        'property_type', 'sublocality', 'bathroom',
                        'site', 'cluster', 'room_type', 'x', 'y','color'])
    df_corr = pd.get_dummies(df_corr)
    # df_corr = df_corr.corr().sort_values(by='price')
    return df_corr.index.tolist()

'''
for index, row in df.iterrows():

def insert(self, row):
    logger.debug("Values: ")
        logger.debug("\troom: {}".format(self.room_id))
        conn = config.connect()
        cur = conn.cursor()

        banco = sqlite3.connect('airbnb.db')
        cursor = banco.cursor()

        sql == """INSERT INTO prepared_data(name,cidade, room_id, host_id, price,
        overall_satisfaction, accommodates, bedrooms,
        bathrooms, bathroo,, latitude, longitude, region, room_type, property_type,
        route, sublocality, comoditiesi, collected, price_pc, qtd_comodities,
        deleted, count_host_id, hotel_id, count_hotel_id, qtd, republica, private_bathroom,
        shared_bathroom, category, qtd_rooms, ar-condicionado, café, espaco, estacionamento,
        máquina, piscina, tv, wifi, cluster, total_clusters, inserted, site)
        VALUES (?, ?, ?,?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?,?,?, ?, ?,?,?, ?, ?, ?, ?, ?, ?, ?, ?)
        """;
        
        insert_args = (
            self.room_id, self.hotel_id, self.name, self.room_name, self.address, self.popular_facilities,
            self.overall_satisfaction, self.reviews, self.property_type, self.bed_type, self.adults_accommodates,
            self.children_accommodates, self.price, self.latitude, self.longitude,
            self.city, self.state, self.country, self.currency, self.comodities,
            self.images, self.bedroom_type, self.qtd_rooms
            )
        cur.execute(sql, insert_args)
        conn.commit()

        cursor.execute(sql, insert_args)
        cursor.close()
        cur.close()
        banco.commit()
        print("FOOOOOOOOOI")
        
'''