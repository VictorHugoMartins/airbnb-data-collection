import os
import redis

def uai():
	return redis.from_url('redis://:p1653267bfcf309937d2be15e0ec9fbda4b87ff5ccb6d03d5d7b7244270368c48@ec2-54-159-105-72.compute-1.amazonaws.com:9949')

print(uai())