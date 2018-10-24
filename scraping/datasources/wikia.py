from PyLyrics import *
import string
import time


class WikiaScraper:

    def __init__(self):
        self.song_not_found = 0
        self.total_attempts = 0

    def get_lyrics(self, artist_name: str, song_title: str,
                   flatten_lyrics=False) -> dict:
        """
        Gets lyrics for a given song

        :param artist_name: name of artist (str)
        :param song_title: name of song title (str)
        :param flatten_lyrics: boolean option to flatten lyrics
        :return: dict of form {
            "Wikia_Lyrics": "str"
        }
        """
        self.total_attempts += 1
        try:
            lyrics = PyLyrics.getLyrics(artist_name, song_title)
        except ValueError:
            self.song_not_found += 1
            lyrics = ""
        return {"Wikia_Lyrics": self._string_strip_lyrics(lyrics)}

    def get_usage_report(self):
        """
        Returns dict of usage statistics

        :return: dict of form {
            "Wikia_Usage_Report": {
                "Song_Not_Found": int,
                "Total_Attempts": int
            }
        }
        """
        usage = {
            "Wikia_Usage_Report": {
                "Song_Not_Found": self.song_not_found,
                "Total_Attempts": self.total_attempts
            }
        }
        return usage

    def clear_usage_stats(self):
        self.song_not_found = 0
        self.total_attempts = 0

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
    WS = WikiaScraper()

    songs = {
        "AC/DC": "Thunderstruck",
        "Twenty One Pilots": "Bandito",
        "BROCKHAMPTON": "BERLIN",
        "Eric Church": "The Snake",
        "Bad Artist Name": "Bad Song Name"
    }

    for key, val in songs.items():
        print("Artist:", key, " : ", "Track:", val)
        info = WS.get_lyrics(key, val, flatten_lyrics=True)
        json_dump = json.dumps(info, indent=4)
        print(json_dump)
        print()

    usage = WS.get_usage_report()
    json_dump = json.dumps(usage, indent=4)
    print(json_dump)
