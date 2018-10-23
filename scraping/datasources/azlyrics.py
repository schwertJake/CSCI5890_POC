from bs4 import BeautifulSoup
import requests
import string
import json


class AZLyricsScraper:

    def __init__(self):
        self.bad_response_count = 0     # Number of bad/null/404 responses from azlyrics
        self.bad_response_items = []    # list of artist/track pairs and exceptions to cause bad response
        self.missed_genre = 0           # Number of items that couldn't find genres
        self.missed_album_year = 0      # Number of items that couldn't find album and year
        self.missed_writer = 0          # Number of items that couldn't find writers
        self.total_attempts = 0         # Total attempts to process a song
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                                      'Chrome/60.0.3112.113 Safari/537.36'}

    def get_song_data(self, artist_name: str, track_title: str,
                      flatten_lyrics=False) -> dict:
        """
        Top Level method that will return all available data from AZlyrics
        for the given artist and track name.

        :param artist_name: name of artist (str)
        :param track_title: name of track (str)
        :param flatten_lyrics: boolean option - true
            to get rid of all punctuation and uppercase in lyrics
        :return: dict of all data (see _extract_info for structure)
        """
        url = self._build_url(artist_name=artist_name,
                              song_title=track_title)
        self.total_attempts += 1
        try:
            response = self._get_html(url)
        except Exception as e:
            self._bad_response_tracker(artist_name, track_title, str(e))
            return {}
        if response is "":
            self._bad_response_tracker(artist_name, track_title)
            return {}
        return self._extract_info(html_text=response,
                                  flatten_lyrics=flatten_lyrics)

    def get_usage_report(self):
        """
        Returns usage report of how the AZ lyrics scraper has
        performed.

        :return: dict of form {
        "AZ_Lyrics_Usage": {
                "Total_Attempts": int,
                "Missed_Writer": int,
                "Missed_Album_and_Year": int,
                "Missed_Genre": int,
                "Bad_Response_Count": int,
                "Bad_Response_Items": self.bad_response_items
        """
        return {
            "AZ_Lyrics_Usage": {
                "Total_Attempts": self.total_attempts,
                "Missed_Writer": self.missed_writer,
                "Missed_Album_and_Year": self.missed_album_year,
                "Missed_Genre": self.missed_genre,
                "Bad_Response_Count": self.bad_response_count
            }}

    def _extract_info(self, html_text: str, flatten_lyrics=False) -> dict:
        """
        Top level method that takes in the html text returned from
        the http request and parses it into a dictionary of lyrics,
        writers, album, year, and genre

        :param html_text: html from AZ lyrics web page
        :param flatten_lyrics: boolean option to get rid of punctuation and
            upper case letters in the lyrics
        :return: dictionary of all parsed values, looks like:
            {
             "lyrics": str,
             "written_by": #there can be 0 to many writers
                [{"first_name": str, "last_name": str},
                {"first_name": str, "last_name": str}],
             "album": str,
             "year": int,
             "genre": str
            }
        """
        soup = BeautifulSoup(html_text, 'html.parser')

        data_dict = self._get_lyrics(soup, flatten_lyrics)
        data_dict.update(self._get_writers(soup))
        data_dict.update(self._get_album_and_year(soup))
        data_dict.update(self._get_genre(soup))

        return data_dict

    def _get_lyrics(self, soup, flatten=False) -> dict:
        """
        Takes a soup object and extracts the lyrics on that page

        :param soup: soup object of webpage
        :param flatten: boolean option - true to get rid of all punctionation and uppercase
        :return: dict object of {"lyrics": str}
        """
        lyrics = [x.getText() for x in soup.find_all("div", attrs={"class": None, "id": None})]
        if flatten:
            lyrics = self._string_strip_lyrics(" ".join(lyrics[0].split()))
        else:
            lyrics = " ".join(lyrics)
        return {"lyrics": lyrics}

    def _build_url(self, artist_name: str, song_title: str):
        """
        Builds url to access azlyrics for given artist's song

        :param artist_name: Name of artist
        :param song_title: Name of song
        :return: url path as string
        """
        return 'http://azlyrics.com/lyrics/' +\
            self._strip_string_url(artist_name) + '/' +\
            self._strip_string_url(song_title) + '.html'

    def _bad_response_tracker(self, artist, track, e="None"):
        """
        Tracks bad responses (when AZ lyrics doesn't have
        lyrics or there are otherwise issues in getting the html
        response.

        :param artist: name of artist (str)
        :param track: name of track (str)
        :return: None
        """
        self.bad_response_count += 1

    def _get_writers(self, soup) -> dict:
        """
        Takes a soup object and extracts the writers for that track
        It's possible there aren't any writers credited, in which case
        it will return an empty string as the value. Otherwise, it will
        return a list of names, that could be in reverse or correct order,
        as there is variability in the data

        :param soup: soup object of webpage
        :return: dict of list of strings {"written_by": [str, str]
        """
        writers = soup.find_all("small")
        for div_small in writers:
            if "Writer(s):" in div_small.getText():
                writers = div_small.getText()
                writers = writers.replace("Writer(s): ", "").split(", ")
                return {"written by": writers}
        self.missed_writer += 1
        return {"written by": ""}

    def _get_album_and_year(self, soup) -> dict:
        """
        Takes a soup object and extracts the album and year for that track

        :param soup: soup object of webpage
        :return: dict of form {"album": str, "year": int}
        """
        try:
            album_year_raw = soup.find("div", class_="panel songlist-panel noprint"). \
                getText().strip().split('\n')[0]
        except Exception as e:
            self.missed_album_year += 1
            return {"album": "",
                    "year": ""}
        album_year_list = album_year_raw.replace("\"", "").split(" ")
        return {"album": " ".join(album_year_list[1:-1]),
                "year": int(album_year_list[-1][1:-1])}

    def _get_genre(self, soup) -> dict:
        """
        Takes a soup object and extracts the genre that AZ lyrics stores
        internally for that track. If a genre isn't found it will return a
        blank string

        :param soup: soup object of webpage
        :return: dict of form {"genre": str}
        """
        all_scripts = [x.getText() for x in soup.find_all("script")]
        for text in all_scripts:
            if "cf_page" in text:
                genre = text.split(";")[2].replace("cf_page_genre = \"", "")[:-1]
                return {"genre": genre.strip()}
        self.missed_genre += 1
        return {"genre": ""}

    def _get_html(self, url: str) -> str:
        """
        Gets html code as a string, returns empty string if http
        returns a bad request

        :param url: url of azlyrics as string
        :return: html page as string
        """
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            return ""
        return r.text

    @staticmethod
    def _strip_string_url(raw_string: str) -> str:
        """
        Takes a generic string, and converts to all lower case, no spaces or punctuation

        :param raw_string: string to convert
        :return: cleaned string as described above
        """
        return raw_string.lower().strip().replace(" ", ""). \
            translate(str.maketrans(dict.fromkeys(string.punctuation)))

    @staticmethod
    def _string_strip_lyrics(raw_string: str) -> str:
        """
        Takes a string of lyrics and converts to all lower case
        and no punctuation, also removes newlines

        :param raw_string: raw lyrics as str
        :return: cleaned string as described above
        """
        return raw_string.lower().strip().replace("\n", " "). \
            translate(str.maketrans(dict.fromkeys(string.punctuation)))


if __name__ == '__main__':

    import time
    AZ = AZLyricsScraper()

    songs = {
        "AC/DC": "Thunderstruck",
        "Twenty One Pilots": "Bandito",
        "BROCKHAMPTON": "BERLIN",
        "Eric Church": "The Snake",
        "D'Angelo": "Sugah Daddy",
        "Bad Artist Name": "Bad Song Name"
    }

    for key, val in songs.items():
        print("Artist:", key, " : ", "Track:", val)
        info = AZ.get_song_data(key, val, flatten_lyrics=True)
        json_dump = json.dumps(info, indent=4)
        print(json_dump)
        print()
        time.sleep(2)
    usage = (AZ.get_usage_report())
    json_dump = json.dumps(usage, indent=4)
    print(json_dump)
