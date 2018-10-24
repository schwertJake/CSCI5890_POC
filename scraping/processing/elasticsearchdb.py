from elasticsearch import Elasticsearch
import json
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
        self.items_posted = 0
        self.song_match_count = 0
        with open('processing/mapping.json', 'r') as file:
            mapping = json.load(file)
        self.ES.indices.create(index=self.index, body=mapping)
        print("Mapping...worked?")

    def song_in_db(self, unique_key: str) -> bool:
        """
        Checks if entry (unique key) is already in db,
        returns boolean val

        :param unique_key: unique key identifying song
        :return: boolean of whether entry exists
        """
        found = self.ES.exists(index=self.index,doc_type="entry",
                               id=unique_key)
        if found:
            self.song_match_count += 1
        return found

    def put_new_data(self, song_data: dict, unique_key: str):
        """
        Puts new data data in elasticsearch

        :param song_data: song data (dict)
        :param unique_key: unique key for song (str)
        :return: none
        """
        try:
            self.ES.index(index=self.index,
                          doc_type='entry',
                          id=unique_key, body=song_data)
            self.items_posted += 1
        except Exception as e:
            print(e, '\n', song_data)

    def log_usage(self, usage_data, ts, records):
        """
        Logs usage reports in seperate index

        :param usage_data: usage data as dict
        :param ts: timestamp of elapsed run time
        :param records: number of records processed
        :return:
        """
        unique_key = str(ts) + ':' + str(records)
        self.ES.index(index="usage_data", doc_type='entry',
                      id=unique_key, body=usage_data)

    def get_usage_report(self) -> dict:
        """
        Returns dict of usage statistics, resets counters

        :return: dict of form {
            "ES_Usage_Report": {
                "Total_Posts": int,
                "Song_Already_Found": int
            }
        }
        """
        usage = {
            "ES_Usage_Report": {
                "Total_Posts": self.items_posted,
                "Song_Already_Found": self.song_match_count
            }
        }
        return usage

    def clear_usage_stats(self):
        self.items_posted = 0
        self.song_match_count = 0
