import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import logging
import os.path
import create_map as cm
from pandas import ExcelWriter

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
	fig, axs = plt.subplots(ncols=3, nrows=3)
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
		
		'''g = sns.barplot(x="region", y="reviews", hue="current_cluster", data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (  data['reviews'].mean() / 2))
		show_values_on_bars(g)'''

	fig.suptitle('quantidade de quartos filtrados por região para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()

def plot_graph_with_clusters_average_values(table, data):
	fig, axs = plt.subplots(nrows=3, ncols=3)
	
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
		
		'''g = sns.barplot(y="reviews", x="current_cluster",  data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (data['reviews'].mean() / 2) )
		show_values_on_bars(g)'''

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

def plot_graph_qtd_pct(table, data):
	fig, axs = plt.subplots(ncols=3, nrows=2)
	for n in range(1, 4):
		tmp_data = data[data.total_clusters == n]
		groupedvalues=tmp_data.groupby('current_cluster').sum().reset_index()
		
		g = sns.barplot(x="room_type", y="qtd", hue="current_cluster", data=tmp_data, ax=axs[0][n-1])
		g.axes.set_ylim(0, data['total_listings'].max())
		show_values_on_bars(g)
		
		g = sns.barplot(x="room_type", y="percentage", hue="current_cluster", data=tmp_data, ax=axs[1][n-1])
		g.axes.set_ylim(0, 100)
		show_values_on_bars(g)
		
		'''g = sns.barplot(x="room_type", y="reviews", hue="current_cluster", data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (  data['reviews'].mean() / 2))
		show_values_on_bars(g)'''

	fig.suptitle(table + ': relação quantidade x porcentagem para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()

def plot_graph_with_clusters_room_type_values(table, data, qtd=False, percentage=False):
	fig, axs = plt.subplots(ncols=3, nrows=2)
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
		
		'''g = sns.barplot(x="room_type", y="reviews", hue="current_cluster", data=tmp_data, ax=axs[3][n-1])
		g.axes.set_ylim(0, data['reviews'].max() + (  data['reviews'].mean() / 2))
		show_values_on_bars(g)'''

	fig.suptitle(table + 'quantidade de quartos filtrados por tipo de quarto para cada cluster em k clusterizações', fontsize=16)
	mng = plt.get_current_fig_manager()
	mng.resize(*mng.window.maxsize())
	plt.subplots_adjust(left=0.05, bottom=0.11, right=0.97, top=0.88, wspace=0.25, hspace=0.20)
	plt.show()