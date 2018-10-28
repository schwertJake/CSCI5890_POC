import json

import requests


class SpotifyScraper:

    def __init__(self, client_id: list, client_secret: list):
        """
        Initialize spotify scraper object

        :param client_id: API client ID (str)
        :param client_secret: API client secret (str)
        """
        self.song_not_found_count = 0   # count of soungs not found by spotify
        self.total_attempts = 0         # count of all attempts to find songs
        self.token_1_calls = 0
        self.token_2_calls = 0
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = self._get_token(client_id[0], client_secret[0])
        if len(client_id) > 1:
            self.token2 = self._get_token(client_id[1], client_secret[1])

    def get_song_data(self, artist_name: str, track_title: str,
                      flatten_lyrics=True) -> dict:
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
        if self.total_attempts % 2 != 0:
            token = self.token2
            self.token_2_calls += 1
        else:
            token = self.token
            self.token_1_calls += 1
        song_data = self._search_artist_track(song_key=track_title,
                                              artist_key=artist_name,
                                              token=token)
        if song_data == {}:
            song_data = {"Spotify_Artist_ID": "Not Found"}
        return song_data

    def get_usage_report(self) -> dict:
        """
        Returns usage report of the spotify scraperr

        :return: dict of form {
            "Spotify_Usage_Report": {
                "Missed Searches": int,
                "Total_Attempts": int
            }
        }
        """
        usage = {
            "Spotify_Usage_Report": {
                "Missed_Searches": self.song_not_found_count,
                "Token1_Calls": self.token_1_calls,
                "Token2_Calls": self.token_2_calls,
                "Total_Attempts": self.total_attempts,
            }
        }
        return usage

    def clear_usage_stats(self):
        self.song_not_found_count = 0
        self.total_attempts = 0
        self.token_1_calls = 0
        self.token_2_calls = 0

    def _search_artist_track(self, song_key: str, artist_key: str,
                             token: str) -> dict:
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
            'access_token': token,
            'q': 'track:' + song_key + " artist:" + artist_key,
            'type': "track",
        }
        response = requests.get(song_url, params=p)
        if response.status_code > 210:
            if response.status_code == 401:
                print("\n\n--- Refresehd Spotify Token ---\n\n")
                self.token = self._get_token(self.client_id[0], self.client_secret[0])
                self.token2 = self._get_token(self.client_id[1], self.client_secret[1])
            self.song_not_found_count += 1
            print("Spotify problems:", response.status_code)
            return {}
        tracks = response.json().get('tracks').get('items')

        for item in tracks:
            artist = [x["name"] for x in item["artists"]]
            if artist[0].lower() == artist_key.lower():
                return{
                    "Spotify_Artist_ID": item["album"]["artists"][0]["id"],
                    "Spotify_Artist_URI": item["album"]["artists"][0]["uri"],
                    "Release_Date": item["album"]["release_date"],
                    "Spotify_Song_Popularity": item["popularity"]
                }
        self.song_not_found_count += 1
        return {}

    def _get_artist_info_from_raw_dict(self, artist_info: dict) -> dict:
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
        return {
            "Genres": {
                "Names": artist_info["genres"],
                "Source": "Spotify"
            },
            "Spotify_Artist_Followers": artist_info["followers"]["total"],
            "Spotify_Artist_Popularity": artist_info["popularity"]
        }

    def _get_multiple_artist_info(self, artist_ids: list) -> list:
        """

        :param artist_ids:
        :return:
        """
        if artist_ids == []:
            return []
        artist_url = "https://api.spotify.com/v1/artists?ids=" + \
                     (",".join(artist_ids))
        response = requests.get(artist_url, params={'access_token': self.token})
        artist_info = response.json()
        return artist_info["artists"]

    def get_artist_info_list(self, id_list):
        """

        :param id_list:
        :return:
        """
        ret_dict ={}
        id_info = self._get_multiple_artist_info(id_list)
        for artist in id_info:
            ret_dict.update({
                artist["id"]:
                    self._get_artist_info_from_raw_dict(artist)
                            }
            )
        return ret_dict


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

    songs = {
        "AC/DC": "Thunderstruck",
        "Twenty One Pilots": "Bandito",
        "BROCKHAMPTON": "BERLIN",
        "Eric Church": "The Snake",
        "Bad Artist Name": "Bad Song Name"
    }

    result = {}

    for artist, song in songs.items():
        result.update({
            artist+"_"+song:
                SS.get_song_data(track_title=song, artist_name=artist)
        })

    artist_info = SS.get_artist_info_list([])
    for key, val in result.items():
        if val["Spotify_Artist_ID"] != "Not Found":
            result[key].update(artist_info[val["Spotify_Artist_ID"]])

    json_dump = json.dumps(result, indent=4)
    print(json_dump)
    json_dump = json.dumps(result, indent=4)
    print(json_dump)

    report = SS.get_usage_report()
    json_dump = json.dumps(report, indent=4)
    print(json_dump)
