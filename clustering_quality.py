import numpy as np
import matplotlib.pyplot as plt
from sklearn import metrics
from sklearn.cluster import KMeans
import pandas as pd

def get_optimal_clusters(X):
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
	 # Print the silhouette score for the current value:
	 #print("\nNumber of clusters =", num_clusters)
	 #print("Silhouette score =", score)

	 scores.append(score)

	# Plot silhouette scores
	plt.figure()
	plt.bar(values, scores, width=0.7, color='black', align='center')
	plt.title('Silhouette score vs number of clusters')

	# Extract best score and optimal number of clusters
	num_clusters = np.argmax(scores) + values[0]
	#print('\nOptimal number of clusters =', num_clusters)

	return num_clusters

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
	#plt.show()