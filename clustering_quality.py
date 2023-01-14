import numpy as np
import matplotlib.pyplot as plt
from sklearn import metrics
from sklearn.cluster import KMeans
import pandas as pd
from kmodes import kmodes
from math import sqrt


def mean_shift(X):
    # Load data from input file
    scores = []
    values = np.arange(2, 10)

    # Iterate through the defined range
    for num_clusters in values:
        # Train the KMeans clustering model
        kmeans = KMeans(init='k-means++', n_clusters=num_clusters, n_init=10)
        kmeans.fit(X)

        score = metrics.silhouette_score(X, kmeans.labels_,
                                         metric='euclidean', sample_size=len(X))
        scores.append(score)

    # Plot silhouette scores
    plt.figure()
    plt.bar(values, scores, width=0.7, color='black', align='center')
    plt.title('Silhouette score vs number of clusters')

    # Extract best score and optimal number of clusters
    num_clusters = np.argmax(scores) + values[0]
    # print('\nOptimal number of clusters =', num_clusters)

    return num_clusters
    '''
	xc = data.columns.get_loc("longitude") - 1
	yc = data.columns.get_loc("latitude") - 1

	# Plot data
	plt.figure()
	plt.scatter(X[:, xc], X[:, yc], color='black', s=80, marker='o',
	facecolors='none')
	x_min, x_max = X[:, xc].min() - 1, X[:, xc].max() + 1
	y_min, y_max = X[:, yc].min() - 1, X[:, yc].max() + 1


	plt.title('Input data')
	plt.xlim(x_min, x_max)
	plt.ylim(y_min, y_max)
	plt.xticks(())
	plt.yticks(())
	#plt.show()'''


def elbow_method(X):
    wcss = []
    for n in range(2, 21):
        km = kmodes.KModes(n_clusters=n, init='Huang', n_init=5, verbose=0)
        try:
            km.fit(X)
            print(km.cost_)
            wcss.append(km.cost_)
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
