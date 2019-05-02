import os
import urllib

MONGO_USER = urllib.parse.quote_plus(os.environ.get('MONGODB_USER', 'user'))
MONGO_HOST = os.environ.get('MONGODB_HOST', 'host')
MONGO_PORT = int(os.environ.get('MONGODB_PORT', '17671'))
MONGO_DB_NAME = os.environ.get('MONGODB_DBNAME', 'dbname')
MONGO_PASS = urllib.parse.quote_plus(os.environ.get('MONGODB_PASS', 'pass'))
