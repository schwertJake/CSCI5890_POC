import json

import requests


class SpotifyScraper:

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize spotify scraper object

        :param client_id: API client ID (str)
        :param client_secret: API client secret (str)
        """
        self.song_not_found_count = 0   # count of soungs not found by spotify
        self.total_attempts = 0         # count of all attempts to find songs
        self.token = self._get_token(client_id, client_secret)

    def get_song_data(self, artist_name: str, song_title: str) -> dict:
        """
        Top level method to get song data from spotify api

        :param artist_name: name of artist (str)
        :param song_title: name of song (str)
        :return: dict of form {
            "Main_Artist_ID": str,
            "Artist_URI": str,
            "Release_Date": str,
            "Song_Popularity": int,
            "Genres": ["str", "str"],
            "Artist_Followers": int,
            "Artist_Popularity": int
        }
        """
        self.total_attempts += 1
        song_data = self._search_artist_track(song_key=song_title,
                                              artist_key=artist_name)
        if song_data != {}:
            song_data.update(self._get_artist_info(song_data["Main_Artist_ID"]))
        return song_data

    def get_usage_report(self) -> dict:
        """
        Returns usage report of the spotify scraperr

        :return: dict of form {
            "Spotify_Usage_Report": {
                "Missed Searches": int
            }
        }
        """
        return {
            "Spotify_Usage_Report": {
                "Missed_Searches": self.song_not_found_count,
                "Total_Attempts": self.total_attempts
            }}

    def _search_artist_track(self, song_key: str, artist_key: str) -> dict:
        """
        Searches for a song in spotify's db given the track name and
        artist name

        :param song_key: name of song (str)
        :param artist_key: name of artist (str)
        :return: if match is found, dict of form {
            "Main_Artist_ID": str,
            "Artist_URI": str,
            "Release_Date": str,
            "Song_Popularity": int
        }
        """
        song_url = "https://api.spotify.com/v1/search/"
        p = {
            'access_token': self.token,
            'q': 'track:' + song_key + " artist:" + artist_key,
            'type': "track",
        }
        response = requests.get(song_url, params=p)
        if response.status_code > 210:
            self.song_not_found_count += 1
            return {}
        tracks = response.json().get('tracks').get('items')

        for item in tracks:
            artist = [x["name"] for x in item["artists"]]
            track = item["name"]
            if artist[0].lower() == artist_key.lower():
                return{
                    "Main_Artist_ID": item["album"]["artists"][0]["id"],
                    "Artist_URI": item["album"]["artists"][0]["uri"],
                    "Release_Date": item["album"]["release_date"],
                    "Song_Popularity": item["popularity"]
                }
        self.song_not_found_count += 1
        return {}

    def _get_artist_info(self, artist_id: str) -> dict:
        """
        Gets artist info, specifically genre and popularity from
        a given spotify id

        :param artist_id: spotify artist id (str)
        :return: dict of form {
            "Genres": ["str", "str"],
            "Artist_Followers": int,
            "Artist_Popularity": int
        }
        """
        artist_url = "https://api.spotify.com/v1/artists/" + artist_id
        response = requests.get(artist_url, params={'access_token': self.token})
        artist_info = response.json()
        return {
            "Genres": artist_info["genres"],
            "Artist_Followers": artist_info["followers"]["total"],
            "Artist_Popularity": artist_info["popularity"]
        }

    @staticmethod
    def _get_token(client_id: str, client_secret: str) -> str:
        """
        Establishes access token

        :param client_id: Api client id (str)
        :param client_secret: Api client secret (str)
        :return: api token (str)
        """
        url = "https://accounts.spotify.com/api/token"
        body_params = {'grant_type': 'client_credentials'}
        client_id = client_id
        client_secret = client_secret
        token_response = requests.post(url, data=body_params, auth=(client_id, client_secret))
        token = token_response.json().get('access_token')
        return token


if __name__ == "__main__":
    from scraping import keys

    k = keys.Keys()
    SS = SpotifyScraper(client_id=k.spotify_client_id,
                        client_secret=k.spotify_client_secret)

    result = SS.get_song_data(song_title="I Like It", artist_name="Cardi B")

    json_dump = json.dumps(result, indent=4)
    print(json_dump)

    report = SS.get_usage_report()
    json_dump = json.dumps(report, indent=4)
    print(json_dump)
