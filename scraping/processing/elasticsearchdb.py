from elasticsearch import Elasticsearch
import time

class ElasticSearch:

    def __init__(self, index):
        self.ES = Elasticsearch(hosts=[{"host":'elasticsearch'}])
        self.index = index
        time.sleep(5)
        while not self.ES.ping():
            print("Trying to connect to ES")
            time.sleep(1)
        print("Successfully connected to ES")

    def song_in_db(self, unique_key: str) -> bool:
        """
        Checks if entry (unique key) is already in db,
        returns boolean val

        :param unique_key: unique key identifying song
        :return: boolean of whether entry exists
        """
        return self.ES.exists(index=self.index,
                              doc_type="entry",
                              id=unique_key)

    def put_new_data(self, song_data: dict, unique_key: str):
        """
        Puts new data data in elasticsearch

        :param song_data: song data (dict)
        :param unique_key: unique key for song (str)
        :return: none
        """
        self.ES.index(index=self.index, doc_type='entry',
                      id=unique_key, body=song_data)

    def log_usage(self, usage_data, ts, records):
        unique_key = str(ts) + ':' + str(records)
        self.ES.index(index="usage_data", doc_type='entry',
                      id=unique_key, body=usage_data)