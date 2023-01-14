import pandas as pd
import numpy as np
import time
import psycopg2 as pg
import argparse
import datetime as dt
import logging
from airbnb_config import ABConfig
import clustering_quality as cq
import export_spreadsheet as exs
from kmodes import kmodes
from pandas import ExcelWriter
from googletrans import Translator
import plot_graphics as plg
import re

def get_max_diference(arr):
	listDiff=[]
	for p,i in enumerate(arr):
		evalList=[e for e in arr[p+1:] if e>i]
	if len(evalList)>0:
		listDiff.append(max(evalList)-i)
	return (max(listDiff))

def get_best_number_of_clusters():
	for i in range(100, 10, 1000):
		for j in range(2, 10):
			v = [ i, 2*j, 3*i-j, 4-4]
			print(get_max_diference(v))

get_best_number_of_clusters()
# calcula as diferencas entre a qtd de elementos de cada cluster
# o que tem as menores diferenças entre si é a q fica, pq está mais equilibrado

