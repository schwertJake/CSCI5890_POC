from bs4 import BeautifulSoup
import requests
import string
import json


class GeniusScraper:

    def __init__(self, token: str):
        """
        Initialize GeniusScraper Object

        :param token: api token for Genius API (str)
        """
        self.song_not_found_count = 0   # count of songs not found by genius api
        self.total_count = 0            # Count of total attempts to process a song
        self.base_url = 'https://api.genius.com'
        self.token = token
        self.headers = {'Authorization': 'Bearer ' + self.token}

    def get_song_data(self, artist_name: str, song_title: str,
                      flatten_lyrics=False) -> dict:
        """
        Public method for getting lyrics from Genius. Takes the
        name of an artist and track, and returns the lyrics as a long string.
        String can be flattened into all lower case and no punctuation with the
        boolean argument flatter

        :param artist_name: name of artist (str)
        :param song_title: name of song title (str)
        :param flatten_lyrics: boolean option as described above
        :return: dict of lyrics or empty string if no lyrics found
        """
        self.total_count += 1
        song_id = self._find_song_id(artist_name=artist_name,
                                     song_title=song_title)
        if song_id is "":
            return {"lyrics": ""}

        html_path = self._get_html_path_from_song_id(song_api_path=song_id)
        lyrics = self._get_lyrics_from_html_path(html_path=html_path)

        if flatten_lyrics:
            lyrics = self._string_strip_lyrics(" ".join(lyrics.split()))

        return {"lyrics": lyrics}

    def get_usage_report(self):
        """
        Returns usage report of total scraping behaviour

        :return: dict of form {
        "Genius_Usage_Report": {
            "Song_Not_Found": int,
            "Total_Attempts": int
        }
        """
        return {
            "Genius_Usage_Report": {
                "Song_Not_Found": self.song_not_found_count,
                "Total_Attempts": self.total_count
            }
        }

    def _find_song_id(self, artist_name: str, song_title: str) -> str:
        """
        Searches for a genius entry with the given song title and name
        The API response gives a list of possible results
        So we filter it by string matching, and return the unique ID of the
        geiuns entry that looks like "songs/*song id int*"

        :param artist_name: name of artist as a string
        :param song_title: title of song as a string
        :return: string of song id from genius or blank string if not found
        """
        search_url = self.base_url + '/search'
        params = {'q': song_title + ' ' + artist_name}
        response = requests.get(search_url, params=params, headers=self.headers)
        json_response = response.json()
        for hit in json_response["response"]["hits"]:
            if artist_name.lower() in hit["result"]["primary_artist"]["name"].lower():
                return hit["result"]["api_path"]
        self.song_not_found_count += 1
        return ""

    def _get_html_path_from_song_id(self, song_api_path: str) -> str:
        """
        After a song ID has been found from searching genius api,
        get the html path to the song's lyrics page

        :param song_api_path: song id from genius api (str)
        :return: url path to genius lyrics page (str)
        """
        song_url = self.base_url + song_api_path
        response = requests.get(song_url, headers=self.headers)
        json_response = response.json()
        path = json_response["response"]["song"]["path"]
        return "http://genius.com" + path

    @staticmethod
    def _get_lyrics_from_html_path(html_path: str) -> str:
        """
        Returns lyrics from a given genius url path

        :param html_path: path to genius lyrics page
        :return: lyrics as str
        """
        page = requests.get(html_path)
        html = BeautifulSoup(page.text, "html.parser")
        [h.extract() for h in html('script')]
        return html.find('div', class_='lyrics').get_text()

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


if __name__ == "__main__":

    import keys
    import time
    k = keys.Keys()

    GS = GeniusScraper(k.genius_token)

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
        info = GS.get_song_data(key, val, flatten_lyrics=True)
        json_dump = json.dumps(info, indent=4)
        print(json_dump)
        print()
        time.sleep(2)

    report = GS.get_usage_report()
    json_dump = json.dumps(report, indent=4)
    print(json_dump)
    print()
