import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from bokeh.models import WMTSTileSource
from bokeh.plotting import ColumnDataSource, figure, output_file, show
from bokeh.tile_providers import Vendors, get_provider
from bokeh.io import show
from bokeh.models import ColumnDataSource, HoverTool

def wgs84_to_web_mercator(df, lon="LON", lat="LAT"):
      k = 6378137
      df["x"] = df[lon] * (k * np.pi/180.0)
      df["y"] = np.log(np.tan((90 + df[lat]) * np.pi/360.0)) * k

      return df

airbnb = pd.read_excel('public/data/dados agrupados em 3 clusters para airbnb + booking.xlsx')
wgs84_to_web_mercator(airbnb, lon="longitude", lat="latitude")

TOOLTIPS = [
    ("index", "$index"),
    ("(x,y)", "($x, $y)"),
    ("desc", "@desc"),
    ("room_id", "@room_id"),
]

output_file("tile.html")

tile_provider = get_provider(Vendors.CARTODBPOSITRON_RETINA)

lat_max = airbnb.y.max()
lat_min = airbnb.y.min()
lng_max = airbnb.x.max()
lng_min = airbnb.x.min()

p = figure(x_range=(lng_min, lng_max), y_range=(lat_min, lat_max) , tooltips=TOOLTIPS, x_axis_type="mercator", y_axis_type="mercator")
p.add_tile(tile_provider)
colors = ['red', 'blue', 'yellow']
clusters = airbnb['cluster'].unique().tolist()
for cluster, color in zip(clusters, colors):
	latitude = []
	longitude = []
	for index, room in airbnb[airbnb.cluster == cluster].iterrows():
		latitude.append(room['y'])
		longitude.append(room['x'])
	p.circle(longitude, latitude, size=5, color=color, alpha=0.5)
show(p)
