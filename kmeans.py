import pandas as pd
from sklearn.cluster import KMeans
import seaborn as sns
from math import sqrt
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from sklearn import datasets
import time
import clustering_quality as cq

def two_d(data, kmeans, X, xn, yn):
	xc = data.columns.get_loc(xn) - 1
	yc = data.columns.get_loc(yn) - 1
	
	#2d
	plt.scatter(X[:, xc], X[:, yc], s = 100, c = kmeans.labels_)
	plt.scatter(kmeans.cluster_centers_[:, xc], kmeans.cluster_centers_[:, yc], s = 100, c = 'red',label = 'Centroids')
	plt.title('Geographical distribution of offers')
	plt.xlabel(xn)
	plt.ylabel(yn)
	plt.legend()
	plt.show()

def three_d(data, kmeans, X, xn, yn, zn):
	xc = data.columns.get_loc(xn) - 1
	yc = data.columns.get_loc(yn) - 1
	zc = data.columns.get_loc("region_number") - 1

	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')

	ax.scatter(X[:, xc], X[:, yc], 1, c=kmeans.labels_)
	# ax.scatter([1,2,3], [4,5,6], 0.2, c='blue') # for booking???????????
	ax.scatter(kmeans.cluster_centers_[:, xc], kmeans.cluster_centers_[:, yc], s = 100, c = 'red',label = 'Centroids')
	
	ax.set_xlabel(xn)
	ax.set_ylabel(yn)
	ax.set_zlabel(zn)

	plt.show()

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
	    print(i,kmeans.inertia_)
	    wcss.append(kmeans.inertia_)  
	plt.plot(range(1, 11), wcss)
	plt.title('O Metodo Elbow')
	plt.xlabel('Numero de Clusters')
	plt.ylabel('WSS') #within cluster sum of squares
	plt.show()'''

	'''plt.scatter(X[:, 12], X[:, 11], s = 100, c = kmeans.labels_)
	plt.scatter(kmeans.cluster_centers_[:, 12], kmeans.cluster_centers_[:, 11], s = 100, c = 'red',label = 'Centroids')
	'''

def plot_airbnb():
	pd.set_option('display.max_columns', 32)
	data = pd.read_excel("public/data/l.xlsx")
	data.fillna("-1", inplace = True) # fill empty fields
	#data["price_real"] = data["price"] * 4.98 # create a new column with price in R$
	X = data.iloc[:,1:15].values #12,11

	n = cq.get_optimal_clusters()
	print('\nOptimal number of clusters =', n)

	kmeans = KMeans(n_clusters = n, init = 'random') # preferia o método elbow pq ao inves de 7 eram 2?????
	kmeans.fit(X)

	xn = "longitude"
	yn = "latitude"
	two_d(data, kmeans, X, xn, yn)

	xn = "region_number"
	yn = "overall_satisfaction"
	two_d(data, kmeans, X, xn, yn)

	xn = "room_id"
	yn = "host_id"
	two_d(data, kmeans, X, xn, yn)

	return

	zn = "z label"
	three_d(data, kmeans, X, xn, yn, zn)

	zn = "z label"
	three_d(data, kmeans, X, xn, yn, zn)

	zn = "z label"
	three_d(data, kmeans, X, xn, yn, zn)

def main():
	plot_airbnb()

if __name__ == "__main__":
    main()