import os
from urllib.parse import quote_plus

MONGO_USER = quote_plus(os.environ.get('MONGODB_USER', 'user'))
MONGO_HOST = os.environ.get('MONGODB_HOST', 'host')
MONGO_PORT = int(os.environ.get('MONGODB_PORT', '17671'))
MONGO_DB_NAME = os.environ.get('MONGODB_DBNAME', 'dbname')
MONGO_PASS = quote_plus(os.environ.get('MONGODB_PASS', 'pass'))
DISCORD_NAME_FIELD = "discordName"
BNET_ID_FIELD = "bnetid"
