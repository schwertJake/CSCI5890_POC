import json
import time
from threading import Thread
from elasticsearch import Elasticsearch
import keys
from datasources import azlyrics
from datasources import genius
from datasources import spotify
from datasources import wikia
from datasources import metrolyrics
from datasources import musixmatchapi
from processing import elasticsearchdb
from processing import processing

from datasources import billboards


class LyricScraper:

    def __init__(self, charts, start_date="2018-10-13",
                 stop_date='1958-01-01', backtrack=False,
                 es=False, max_records=20, max_threads=3):
        """

        :param charts:
        :param start_date:
        :param stop_date:
        :param backtrack:
        :param es:
        :param max_records:
        """
        self.start_date = start_date
        self.stop_date = stop_date
        self.backtrack = backtrack
        self.use_es = es
        self.charts = charts
        self.max_records = max_records
        self.max_threads = max_threads
        self.records_processed = 0

        self.chart_partition = []
        for thread in range(self.max_threads):
            self.chart_partition.append([])
        for num in range(len(self.charts)):
            self.chart_partition[num%self.max_threads].\
                append(self.charts[num])

        api_keys = keys.Keys()
        self.data_sources = [
            azlyrics.AZLyricsScraper(),
            genius.GeniusScraper(
                token=api_keys.genius_token
            ),
            wikia.WikiaScraper(),
            metrolyrics.MetroLyrics(),
            spotify.SpotifyScraper(
                client_id=api_keys.spotify_client_id,
                client_secret=api_keys.spotify_client_secret
            )
        ]
        self.BB = billboards.BillboardScraper()
        self.MM = musixmatchapi.MusiXMatchAPI(key=api_keys.musixmatch_key)
        self.Proc = processing.LyricAnalyst()
        if self.use_es:
            self.ES = elasticsearchdb.ElasticSearch("song_data")

    def run(self):
        """
        Main run loop

        :return: None
        """
        begin = time.time()
        cur_date = self.start_date

        while (time.strptime(cur_date, "%Y-%m-%d") > time.strptime(self.stop_date, "%Y-%m-%d")) and \
                (self.max_records == 0 or self.records_processed < self.max_records):

            threads = []

            # Main process for data collection:
            for charts in self.chart_partition:
                t = Thread(target=self.get_data_load_balanced, args=(charts, cur_date), daemon=True)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()

            # All charts are done for this time period. Cleanup:
            self.log_performance(begin)
            cur_date = self.BB.rewind_one_week(cur_date)

    def log_performance(self, begin):
        """
        Log usage report in file or in elasticsearch

        :param begin: timestamp from start of calling run()
        :return: None
        """
        if self.use_es:
            self.ES.log_usage(self.get_usage_reports(),
                              (time.time() - begin),
                              self.records_processed)
        else:
            self._log_to_file(self.get_usage_reports(),
                              "usage",
                              (str(self.records_processed) + "records"))
        self.clear_usage()

    def get_data_load_balanced(self, chart_list: list, date: str):
        """
        Wrapper for get_augemented_chart_list that cycles through a list of
        charts. This is called by each working thread, and allows a decoupling
        of number of threads to number of working charts.

        :param chart_list: list of charts to get data from (str)
        :param date: date of chart to read (str)
        :return:
        """
        for chart in chart_list:
            self.get_augmented_chart_list(chart=chart, date=date)

    def get_augmented_chart_list(self, chart: str, date: str):
        """
        Takes a billboard charts and gets
        all of the artist and track names from them and all song info
        ans lyrics, returns a dictionary of results

        :param chart: name of billboard chart (str)
        :param date: date to poll charts for
        :return: dictionary of chart info
        """
        master_dict = {}
        chart_dict = self.BB.get_chart(chart_name=chart, date_str=date)
        if "Error" in chart_dict.keys():
            print({"Bad Billboard Chart": chart_dict["Error"]})
            return

        for key, val in chart_dict.items():

            # Do we even need to do this?:
            if self.max_records != 0 and self.records_processed >= self.max_records:
                break
            status = "No Update"
            if key in ["Billboard_Chart", "Year", "Month", "Day"]:
                continue

            # setup main key and date str
            master_key = val["BB_Artist"] + "_" + val["BB_Song_Title"]
            date_str = val["BB_Chart_Discovered"]["Date"]

            # If new song:
            if (self.use_es and not self.ES.song_in_db(
                    master_key)) or not self.use_es:

                song_dict = self._get_song_data(val, True)
                status = "New Entry"
                master_dict[master_key] = song_dict

            # Finished Message so we know there's progress
            print(self._progress_message(status, chart, date_str,
                                         val, self.records_processed))
            self.records_processed += 1

        if self.use_es:
            self._put_data_in_es(master_dict)
        else:
            self._log_to_file(master_dict, chart, date)

    def _put_data_in_es(self, master_dict: dict):
        """
        puts augmented chart data into elasticsearch

        :param master_dict: dict of augmented chart/song data
        :return: none
        """
        for key, val in master_dict.items():
            if not self.ES.song_in_db(key):
                self.ES.put_new_data(song_data=val, unique_key=key)

    def _get_song_data(self, val: dict, flatten_lyrics=False) -> dict:
        """
        Gets data from all sources for a song

        :param val: dict containing song info
        :param flatten_lyrics: boolean value to flatten lyrics
        :return: dict of aggregate data
        """
        song_dict = val
        artist_name = val["BB_Artist"]
        track_title = val["BB_Song_Title"]

        for data in self.data_sources:
            song_dict.update(data.get_song_data(artist_name=artist_name,
                                                track_title=track_title,
                                                flatten_lyrics=flatten_lyrics))
        if song_dict["Spotify_Artist_ID"] == "":
            song_dict.update(
                self.MM.get_song_data(artist_name, track_title)
            )
        # Add basic lyric analytics:
        results = self.Proc.get_lyric_stats([
            {"Genius": song_dict["Genius_Lyrics"]},
            {"AZ": song_dict["AZ_Lyrics"]},
            {"Wikia": song_dict["Wikia_Lyrics"]},
            {"Metro": song_dict["MetroLyrics"]}
        ])
        song_dict.update(results)
        return song_dict

    def get_usage_reports(self):
        """
        Creates aggregate usage report from all scraping/processing
        modules

        :return: dict
        """
        report_dict = {"Total_Records": self.records_processed}
        report_dict.update(self.BB.get_usage_report())
        for data in self.data_sources:
            report_dict.update(data.get_usage_report())
        report_dict.update(self.MM.get_usage_report())
        report_dict.update(self.Proc.get_usage_report())
        if self.use_es:
            report_dict.update(self.ES.get_usage_report())
        return report_dict

    def clear_usage(self):
        self.BB.clear_usage_stats()
        for data in self.data_sources:
            data.clear_usage_stats()
        self.MM.clear_usage_stats()
        self.Proc.clear_usage_stats()
        if self.use_es:
            self.ES.clear_usage_stats()

    @staticmethod
    def _log_to_file(data: dict, chart_name: str, date: str):
        """
        Logs augmented chart dict to file

        :param data: dictionary to log
        :param chart_name: name of chart (str)
        :param date: date string
        :return: None
        """
        file_path = 'sample_results/' + chart_name + '_'+date+'.json'
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile, indent=4)

    @staticmethod
    def _progress_message(status: str, chart: str, date_str: str,
                          val: dict, records_processed: int) -> str:
        """
        Returns simple progress message so we know things haven't crashed

        :param status: status (str)
        :param chart: name of billboard chart (str)
        :param date_str: str of date values "YYYY-MM-DD"
        :param val: dict of song info
        :param records_processed: number of records processed (int)
        :return: string detailing progress
        """
        ret_str = status + " : " + chart + " : " + date_str + \
                  " : " + val["BB_Artist"] + " : " + val["BB_Song_Title"] + \
                  " : " + "Records Processed: " + str(records_processed)
        return ret_str


if __name__ == "__main__":
    with open('run.json', 'r') as file:
        param = json.load(file)

    charts = param["charts"]
    start_date = param["start_date"]
    end_date = param["end_date"]
    es = param["use_elastic_search"]
    max_entries = param["max_entries"]
    max_threads = param["max_threads"]

    print("Running For Parameters:")
    print("Charts :", charts)
    print("Start Date : ", start_date)
    print("End Date :", end_date)
    print("Use ES? :", es)
    print("Max Entries :", max_entries)
    print("Max Threads :", max_threads)

    if es:
        time.sleep(10)
        Elasticsearch()

    LS = LyricScraper(charts=charts,
                      start_date=start_date,
                      stop_date=end_date,
                      backtrack=True,
                      es=es,
                      max_records=max_entries,
                      max_threads=max_threads)
    LS.run()
