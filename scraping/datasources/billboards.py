import billboard
import json
import datetime


class BillboardScraper:

    def __init__(self):
        self.charts_processed = 0   # total number of charts processed
        self.entries_processed = 0  # total number of entries processed

    def get_chart(self, chart_name: str, date_str=None) -> dict:
        """
        Gets billboard chart of the given name and gate,
        returns a dictionary of dictionaries of song artist,
        track title, and peak rank

        :param chart_name: name of chart as str (i.e. hot-100)
        :param date_str: date of chart to poll (str) (YYYY-MM-DD)
        :return: dictionary of songs in chart
        """
        self.charts_processed += 1
        master_dict = {'Billboard_Chart': chart_name}
        master_dict.update(self._parse_date(date_str))
        chart = billboard.ChartData(name=chart_name, date=date_str)
        for song in chart:
            master_dict.update(self._extract_song_info(song))
        return master_dict

    def get_usage_report(self):
        """
        returns dict of usage of billboards

        :return: dict of form {
            "Billboard_Usage_Report": {
                "Charts_Processed": int,
                "Entries_Processed": int
            }
        }
        """
        usage = {
            "Billboard_Usage_Report": {
                "Charts_Processed": self.charts_processed,
                "Entries_Processed": self.entries_processed
            }
        }
        return usage

    def clear_usage_stats(self):
        self.charts_processed = 0
        self.entries_processed = 0

    def _extract_song_info(self, song) -> dict:
        """
        Takes a song item and returns a dictionary
        of the characteristics of that song, looking like:
        { Current Rank: {"Artist": str, "Title": str, "Peak_Rank": int}}

        :param song: song item to extract info from
        :return: dict as described above
        """
        self.entries_processed += 1
        artist = artist_raw = song.artist
        feature = ""
        for word in ["Featuring", ",", "&"]:
            if word in artist_raw:
                artist_raw = artist_raw.split(word)
                artist = artist_raw[0].strip()
                feature = artist_raw[1].strip()
                break
        return {
            song.rank: {
                "Artist": artist,
                "Featuring": feature,
                "Title": song.title,
                "Peak_Rank": int(song.peakPos)
            }
        }

    @staticmethod
    def rewind_one_week(date_str: str) -> str:
        """
        Takes a date string of form YYYY-MM-DD and
        subtracts one week

        :param date_str: date string to rewind one week from (str)
        :return: date string of one week previous in format YYYY-MM-DD
        """
        date_arr = date_str.split("-")
        year = int(date_arr[0])
        month = int(date_arr[1])
        day = int(date_arr[2])

        current_date = datetime.date(year, month, day)
        new_date = current_date - datetime.timedelta(days=7)

        return new_date.strftime("%Y-%m-%d")

    @staticmethod
    def _parse_date(date_str: str) -> dict:
        """
        Parses a date string in YYYY-MM-DD format
        into a dict of {"Year": int, "Month": int, "Day": int}

        :param date_str: date  string to parse
        :return: dict as described above
        """
        date_arr = date_str.split("-")
        return {"Year": int(date_arr[0]),
                "Month": int(date_arr[1]),
                "Day": int(date_arr[2])}


if __name__ == "__main__":
    date = datetime.date(2018, 10, 13)
    scraper = BillboardScraper()

    info = scraper.get_chart('hot-100', scraper.rewind_one_week(date.strftime("%Y-%m-%d")))
    json_dump = json.dumps(info, indent=4)
    print(json_dump)
    print()

    usage = scraper.get_usage_report()
    json_dump = json.dumps(usage, indent=4)
    print(json_dump)
    print()
