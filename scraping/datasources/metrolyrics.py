import requests
import string
from bs4 import BeautifulSoup


class MetroLyrics:

    def __init__(self):
        self.base_url = 'http://www.metrolyrics.com/'
        self.lyrics_not_found = 0
        self.total_count = 0

    def get_song_data(self, artist_name: str, track_title: str,
                      flatten_lyrics: bool):
        """
        Public method for getting lyrics from MetroLyrics. Takes the
        name of an artist and track, and returns the lyrics as a long string.
        String can be flattened into all lower case and no punctuation with the
        boolean argument flatter

        :param artist_name: name of artist (str)
        :param track_title: name of song title (str)
        :param flatten_lyrics: boolean option as described above
        :return: dict of lyrics or empty string if no lyrics found
        """
        self.total_count += 1
        url = self._build_url(artist_name=artist_name,
                              track_title=track_title)
        lyrics = self._get_lyrics_from_url(url)
        if flatten_lyrics:
            lyrics = self._string_strip_lyrics(lyrics)
        return {"MetroLyrics": lyrics}

    def get_usage_report(self):
        """
        Gets usage report of total entries processed and
        songs not found

        :return: dict of form {
            "MetroLyrics_Usage_Report": {
                "Song_Not_Found": int,,
                "Total_Attempts": int
            }
        }
        """
        usage = {
            "MetroLyrics_Usage_Report": {
                "Song_Not_Found": self.lyrics_not_found,
                "Total_Attempts": self.total_count
            }
        }
        return usage

    def clear_usage_stats(self):
        self.lyrics_not_found = 0
        self.total_count = 0

    def _build_url(self, artist_name, track_title):
        """
        Builds url to metrolyrics page given an artist and
        song title

        :param artist_name: name of artist (str)
        :param track_title: name of track (str)
        :return: url to metrolyrics lyrics page (str)
        """
        artist = '-'.join(artist_name.split(' '))
        song = '-'.join(track_title.split(' '))
        url = self.base_url + song + '-lyrics-' + artist + '.html'
        return url

    def _get_lyrics_from_url(self, url):
        """
        Scrapes a given metrolyrics url for lyrics

        :param url: url of metrolyrics lyrics page
        :return: string of raw lyrics or empty string if not found
        """
        html_doc = requests.get(url)
        soup = BeautifulSoup(html_doc.text, 'html.parser')
        complete_lyrics = []
        for i in soup.find_all("p", class_='verse'):
            complete_lyrics.append(i.get_text())
        lyrics = ' '.join(complete_lyrics)
        if lyrics:
            return lyrics
        else:
            self.lyrics_not_found += 1
            return ""

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

    import json
    import time

    ML = MetroLyrics()
    print(ML.get_song_data("Usher", "climax", True))

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
        info = ML.get_song_data(key, val, flatten_lyrics=True)
        json_dump = json.dumps(info, indent=4)
        print(json_dump)
        print()
        time.sleep(2)

    report = ML.get_usage_report()
    json_dump = json.dumps(report, indent=4)
    print(json_dump)
    print()
