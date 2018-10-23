import json
import random
import time

import keys
from processing import elasticsearchdb
from processing import processing
from datasources import azlyrics
from datasources import billboards
from datasources import genius
from datasources import spotify
from datasources import wikia


class LyricScraper:

    def __init__(self, charts, start_date="2018-10-13",
                 stop_date='1958-01-01', backtrack=False,
                 es=False, max_records=20):
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

        api_keys = keys.Keys()
        self.AZ = azlyrics.AZLyricsScraper()
        self.GS = genius.GeniusScraper(
            token=api_keys.genius_token
        )
        self.SS = spotify.SpotifyScraper(
            client_id=api_keys.spotify_client_id,
            client_secret=api_keys.spotify_client_secret
        )
        self.BB = billboards.BillboardScraper()
        self.WS = wikia.WikiaScraper()
        self.Proc = processing.LyricAnalyst()
        if self.use_es:
            self.ES = elasticsearchdb.ElasticSearch("song_data")
        self.records_processed = 0

    def run(self):
        begin = time.time()
        cur_date = self.start_date

        while (time.strptime(cur_date, "%Y-%m-%d") > time.strptime(self.stop_date, "%Y-%m-%d")) and \
                (self.records_processed < self.max_records):

            # Main process for data collection:
            for chart in self.charts:
                augmented_results = self.get_augmented_chart_list(chart,
                                                                  cur_date)

                if self.use_es:
                    self._put_data_in_es(augmented_results)
                else:
                    self._log_to_file(augmented_results, chart, cur_date)

            # All charts are done for this time period. Cleanup:
            self.log_performance(begin)
            cur_date = self.BB.rewind_one_week(cur_date)

        # We're free! Save final usage stats
        self.log_performance(begin)

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

    def get_augmented_chart_list(self, chart: str, date: str) -> dict:
        """
        Takes a list of billboard charts and gets
        all of the artist and track names from them, returns
        a dictionary of results

        :param chart: name of billboard chart (str)
        :param date: date to poll charts for
        :return: dictionary of chart info
        """
        master_dict = {}
        chart_dict = self.BB.get_chart(chart_name=chart, date_str=date)

        for key, val in chart_dict.items():

            # Do we even need to do this?:
            if self.records_processed >= self.max_records:
                break
            status = "No Update"
            if key in ["Billboard_Chart", "Year", "Month", "Day"]:
                continue

            # setup main key and date array
            master_key = val["Artist"] + "_" + val["Title"]
            date_arr = {
                "Year": str(chart_dict["Year"]),
                "Month": str(chart_dict["Month"]),
                "Day": str(chart_dict["Day"])
            }

            # If new song:
            if (self.use_es and not self.ES.song_in_db(master_key)) or not self.use_es:
                song_dict = self._get_song_data(val, chart, date_arr, True)
                status = "New Entry"
                master_dict[master_key] = song_dict

            # Finished Message so we know there's progress
            print(self._progress_message(status, chart, date_arr,
                                         val, self.records_processed))
            self.records_processed += 1

        return master_dict

    def _put_data_in_es(self, master_dict: dict):
        """
        puts augmented chart data into elasticsearch

        :param master_dict: dict of augmented chart/song data
        :return: none
        """
        for key, val in master_dict.items():
            if not self.ES.song_in_db(key):
                self.ES.put_new_data(song_data=val, unique_key=key)

    def _get_song_data(self, val: dict, chart: str, date_arr: dict,
                       flatten_lyrics=False) -> dict:
        """
        Gets data from all sources for a song

        :param val: dict containing song info
        :param chart: name of billboard chart (str)
        :param date_arr: array of date integers
        :param flatten_lyrics: boolean value to flatten lyrics
        :return: dict of aggregate data
        """
        song_dict = {}
        artist_name = val["Artist"]
        track_title = val["Title"]

        song_dict.update(  # Start with Billboard info
            self._setup_dict_for_new_key(val, chart, date_arr))
        song_dict.update(  # Add Genius Info
            self._get_genius_info(artist_name, track_title, flatten_lyrics))
        song_dict.update(  # Add Wikia Lyrics
            self._get_wikia_info(artist_name, track_title, flatten_lyrics))
        song_dict.update(  # Add AZ Lyrics
            self._get_az_info(artist_name, track_title, flatten_lyrics))
        song_dict.update(  # Add Spotify Metadata
            self._get_spotify_info(artist_name, track_title))
        # Add basic lyric analytics:
        results = self.Proc.get_lyric_stats([
            {"Genius": song_dict["Genius_Lyrics"]},
            {"AZ": song_dict["AZ_Lyrics"]},
            {"Wikia": song_dict["Wikia_Lyrics"]}
        ])
        song_dict.update(results)
        return song_dict

    @staticmethod
    def _setup_dict_for_new_key(val: dict, chart_name: str,
                                date_arr: dict) -> dict:
        """
        Setups up new dictionary with info about billboard chart of discovery

        :param date_arr: JSON dict of Year, Month, Date
        :param val: Dictionary from billboard module/api
        :param chart_name: Name of billboard chart discovered on
        :return: dict of form {
            "BB_Artist": "str",
            "BB_Featuring": "str",
            "BB_Song_Title": "str",
            "BB_Billboard_Charts": [
                {
                    "Chart_Name": "str",
                    "Peak_Position": int
                    "Date": "str"
                }
            ]
        }
        """
        return{"BB_Artist": val["Artist"],
               "BB_Featuring": val["Featuring"],
               "BB_Song_Title": val["Title"],
               "BB_Billboard_Charts": [
                   {
                        "Chart_Name": chart_name,
                        "Peak_Position": val["Peak_Rank"],
                        "Date": date_arr["Year"]+"-"+
                                date_arr["Month"]+"-"+
                                date_arr["Day"]
                    }
                ]
               }

    def _get_az_info(self, artist_name: str, track_title: str,
                     flatten_lyrics=True):
        """
        Gets lyrics through Scraping AZLyrics for the given artist
        name and track title. Flatten is a boolean option that
        gets rid of capital letters, newlines, and punctuation.
        Empty string if lyrics aren't found

        :param artist_name: name of artist (str)
        :param track_title: name of track title (str)
        :param flatten_lyrics: flatten option as descirbed above (bool)
        :return: dict of form:
            {
                "AZ_Lyrics": "str",
                "AZ_Album": "str",
                "AZ_Written_By": ["str", "str"],
                "AZ_Year": "str",
                "AZ_Genre": "str",
            }
        """
        results = self.AZ.get_song_data(artist_name=artist_name,
                                        track_title=track_title,
                                        flatten_lyrics=flatten_lyrics)
        if results == {}:
            return {"AZ_Lyrics": ""}

        return {
            "AZ_Lyrics": results["lyrics"],
            "AZ_Album": results["album"],
            "AZ_Written_By": results["written by"],
            "AZ_Year": results["year"],
            "AZ_Genre": results["genre"]
        }

    def _get_genius_info(self, artist_name: str, track_title: str,
                         flatten_lyrics=True):
        """
        Gets lyrics through Genius API for the given artist
        name and track title. Flatten is a boolean option that
        gets rid of capital letters, newlines, and punctuation.
        Empty string if lyrics aren't found

        :param artist_name: name of artist (str)
        :param track_title: name of track (str)
        :param flatten_lyrics: flatten option (bool)
        :return: dict of form {"Genius_Lyrics": "str"}
        """
        results = self.GS.get_song_data(artist_name=artist_name,
                                        song_title=track_title,
                                        flatten_lyrics=flatten_lyrics)
        return {"Genius_Lyrics": results['lyrics']}

    def _get_spotify_info(self, artist_name: str, track_title: str):
        """
        Gets spotify metadata for a given artist name and track title.
        Searches spotify for the track and returns a data for an exact match.
        Returns the artist_id used be spotify (as it's used to find the genre),
        as well as the Genres (there can be many) the artist creates in, and
        some popularity statistics and release date for the track.

        :param artist_name: name of artist (str)
        :param track_title: name of track title (str)
        :return: dict of form {
            "Spotify_Artist_ID": "str",
            "Spotify_Release Date": "str",
            "Spotify_Song_Popularity": int,
            "Spotify_Genres": ["str", "str"],
            "Spotify_Artist_Followers": int
        }
        """
        results = self.SS.get_song_data(artist_name=artist_name,
                                        song_title=track_title)
        if results == {}:
            return {"Spotify_Artist_ID": ""}
        return {
            "Spotify_Artist_ID": results["Main_Artist_ID"],
            "Spotify_Release Date": results["Release_Date"],
            "Spotify_Song_Popularity": results["Song_Popularity"],
            "Spotify_Genres": results["Genres"],
            "Spotify_Artist_Followers": results["Artist_Followers"],
            "Spotify_Artist_Popularity": results["Artist_Popularity"]
        }

    def _get_wikia_info(self, artist_name: str, track_title: str,
                        flatten_lyrics=True):
        """
        Gets lyrics from wikia through PyLyrics Scraper

        :param artist_name: name of artist (str)
        :param track_title: name of track (str)
        :param flatten_lyrics: flatten option (bool)
        :return: dict of form {"Wikia_Lyrics": "str"}
        """
        return self.WS.get_lyrics(artist_name, track_title, flatten_lyrics)

    def get_usage_reports(self):
        """
        Creates aggregate usage report from all scraping/processing
        modules

        :return: dict
        """
        report_dict = {}
        report_dict.update(self.BB.get_usage_report())
        report_dict.update(self.AZ.get_usage_report())
        report_dict.update(self.GS.get_usage_report())
        report_dict.update(self.WS.get_usage_report())
        report_dict.update(self.SS.get_usage_report())
        report_dict.update(self.Proc.get_usage_report())
        return report_dict

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
    def _progress_message(status: str, chart: str, date_arr: dict,
                          val: dict, records_processed: int) -> str:
        """
        Returns simple progress message so we know things haven't crashed

        :param status: status (str)
        :param chart: name of billboard chart (str)
        :param date_arr: dict of date values (integers) (dict)
        :param val: dict of song info
        :param records_processed: number of records processed (int)
        :return: string detailing progress
        """
        ret_str = status + " : " + chart + " : " + date_arr["Year"] + "-" + \
                  date_arr["Month"] + "-" + date_arr["Day"] + \
                  " : " + val["Artist"] + " : " + val["Title"] + \
                  " : " + "Records Processed: " + str(records_processed)
        return ret_str


if __name__ == "__main__":
    LS = LyricScraper(charts=['hot-100'], backtrack=False,
                      es=False, max_records=5)
    LS.run()
