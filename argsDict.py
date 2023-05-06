dict = {
  "PLATFORM": {
    0: None,
    1: 'Airbnb',
    2: 'Booking',
  },
  "INCLUIR_BAIRROS": {
    0: True,
    1: False,
  },
  "INCLUIR_RUAS": {
    0: True,
    1: False,
  },
  "AGGREGATE_METHODS": {
    0: None,
    1: 'AVG',
    2: 'MAX',
    3: 'MIN',
  },
  "IA": {
    0: None,
    1: 'K-Means',
    2: 'Booking',
  },
  "COLUMNS": {
    "IdDoAnfitriao": {
      "name": 'host_id',
      "type": "string"
    },
    "Preço": {
      "name": 'price',
      "type": "number"
    },
    "Nome": {
      "name": 'name',
      "type": "string"
    },
    "Latitude": {
      "name": 'latitude',
      "type": "number"
    },
    "Longitude": {
      "name": 'Longitude',
      "type": "number"
    },
    "TipoDePropriedade": {
      "name": 'property_type',
      "type": "string"
    },
    "TipoDeQuarto": {
      "name": 'room_type',
      "type": "string"
    },
    "EstadiaMinima": {
      "name": 'minstay',
      "type": "number"
    },
    "QuantidadeDeReviews": {
      "name": 'reviews',
      "type": "number"
    },
    "QuantidadeDePessoasAcomodadas": {
      "name": 'accommodates',
      "type": "number"
    },
    "QuantidadeDeQuartos": {
      "name": 'bedrooms',
      "type": "number"
    },
    "QuantidadeDeBanheiros": {
      "name": 'bathrooms',
      "type": "number"
    },
    "TipoDeDeBanheiro": {
      "name": 'bathroom',
      "type": "number"
    },
    "IdiomasDoAnfitriao": {
      "name": 'extra_host_languages',
      "type": "string"
    },
    "ESuperAnfitriao": {
      "name": 'is_superhost',
      "type": "number"
    },
    "Comodidades": {
      "name": 'comodities',
      "type": "string"
    },
    "Rua": {
      "name": 'route',
      "type": "string"
    },
    "Bairro": {
      "name": 'sublocality',
      "type": "string"
    },
    "Cidade": {
      "name": 'locality', # n opcional
  }
}

def update_sql_with_string_field(sql, field):
    return sql + ", STRING_AGG(DISTINCT CAST({field} AS varchar), 'JOIN ') AS {field}".format(field=field)

def update_sql_with_numeric_field(sql, field, agg_method='1'):
    return sql + ", {AGG}({field}) AS {AGG}_{field}".format(AGG=dict['AGGREGATE_METHODS'][agg_method], field=field)

def build_airbnb_export_sql(columns=[]):
  sql = "SELECT room_id "
  
  if (True): # (columns.includes('host_id')):
      sql = update_sql_with_string_field(sql, "host_id")
      print(sql)
  if (True): # (columns.includes('price')):
      sql = update_sql_with_numeric_field(sql, 'price', 1)
      print(sql)

  if (True): # (columns.includes("route"))
      sql = sql + ", location.route"
  sql = sql + " FROM room "
  if (True): # (columns.includes("route" or "sublocality" or "locality")):
      sql = sql +  """INNER JOIN location
      ON location.location_id = room.location_id GROUP BY
          locality, location.sublocality, location.route, location.location_id, room_id"""
  else:
      sql = sql + "GROUP BY room_id"

  """
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
          MAX(latitude) AS latitude,
          MAX(longitude) AS longitude,
          STRING_AGG(DISTINCT extra_host_languages, 'JOIN ') AS extra_host_languages,
          AVG(CAST(is_superhost AS int)) AS avg_is_superhost,
          STRING_AGG(DISTINCT comodities, 'JOIN ') AS comodities,
		      location.location_id,
          location.route,
          location.sublocality,
          location.locality """
  sql = sql + """  FROM
          room
      INNER JOIN location
      ON location.location_id = room.location_id
        GROUP BY
          locality, location.sublocality, location.route, location.location_id, room_id
    """
  return sql

print(dict["AGGREGATE_METHODS"][1])
print(build_airbnb_export_sql())