from musixmatch import Musixmatch


class MusiXMatchAPI:

    def __init__(self, key):
        self.MM = Musixmatch(key)
        self.track_not_found = 0
        self.total_count = 0
        self.error_codes = []

    def get_song_data(self, artist_name: str, track_title: str) -> dict:
        """
        Gets song data from musixmatch api. Using the free API means
        access to only 30% of the lyrics body, so that's a no go. We
        can still use the API to augment our datasets with the
        album name, release date, and genres.

        :param artist_name: name of track artist (str)
        :param track_title: name of track title (str)
        :return: dict of form {
            "Album_name": str,
            "Release_date": "yyyy-MM-dd,
            "Genres": list of strs
        }
        """
        self.total_count += 1
        result = self.MM.matcher_track_get(q_artist=artist_name,
                                           q_track=track_title)

        result = result["message"]
        if result["header"]["status_code"] != 200 or \
                        result["body"]["track"]["has_lyrics"] != 1:
            self.track_not_found += 1
            self.error_codes.append(result["header"]["status_code"])
            return {}

        result = result["body"]["track"]
        return {
            "Album_name": result["album_name"],
            "Release_date": result["first_release_date"].split("T")[0],
            "Genres": [x["music_genre"]["music_genre_name"] for x
                       in result["primary_genres"]["music_genre_list"]]
        }

    def get_usage_report(self) -> dict:
        """
        Returns usage report of the spotify scraperr

        :return: dict of form {
            "Musixmatch_Usage_Reports": {
                "Missed_Searches": int,
                "Total_Attempts": int
            }
        }
        """
        usage = {
            "Musixmatch_Usage_Reports": {
                "Missed_Searches": self.track_not_found,
                "Total_Attempts": self.total_count
            }
        }
        return usage

    def clear_usage_stats(self):
        self.song_not_found_count = 0
        self.total_attempts = 0


if __name__ == "__main__":

    import json
    import time
    from scraping import keys
    k = keys.Keys()

    MM = MusiXMatchAPI(k.musixmatch_key)

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
        info = MM.get_song_data(key, val,)
        json_dump = json.dumps(info, indent=4)
        print(json_dump)
        print()
        time.sleep(2)

    report = MM.get_usage_report()
    json_dump = json.dumps(report, indent=4)
    print(json_dump)
    print()
