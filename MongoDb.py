from pymongo import MongoClient

# connect to MongoDB, change the << MONGODB URL >> to reflect your own connection string
import MongoConstants


# pprint library is used to make the output look more pretty


def get_discord_mongo_uri():
    return get_mongo_uri(MongoConstants.MONGO_DB_NAME, MongoConstants.MONGO_HOST, MongoConstants.MONGO_PORT,
                         MongoConstants.MONGO_USER, MongoConstants.MONGO_PASS)


def get_mongo_uri(dbname, host, port, user, pw):
    return "mongodb://{}:{}@{}:{}/{}".format(user, pw, host, port, dbname)


def get_discord_mongo_table():
    return MongoClient(get_discord_mongo_uri()).heroku_50n0tcg4.discord
