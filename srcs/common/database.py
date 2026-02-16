from common.constants import MONGO_URL
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# client = pymongo.MongoClient(MONGO_URL)
uri = MONGO_URL
client = MongoClient(uri, server_api=ServerApi('1'), tlsAllowInvalidCertificates=True)

def is_url_in_database(url):
	"""
	Return True if the given URL is already in our MongoDB database.
	url: String
	"""

	conds = {
		'url': url
	}

	o = client.jobs_database.jobs_collection.find_one(conds)

	return o is not None


def add_url_in_database(url):
	"""
	Add an URL into our MongoDB database.
	url: String
	"""

	doc = {
		'url': url
	}

	client.jobs_database.jobs_collection.insert_one(doc)
