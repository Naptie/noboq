from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")


def init(connection_string):
    global client
    client = MongoClient(connection_string)


def col(collection):
    return client["noboq"].get_collection(collection)


def get():
    return client["noboq"]
