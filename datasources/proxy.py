import requests
import json

"""
--------------------------------------
This is a test file for playing with proxies - things aren't going too hot
-------------------------------------
"""
class ProxyRotator:

    def __init__(self):
        self.base_url = "https://gimmeproxy.com/api/getProxy"

    def get_proxy(self, **args):
        request = requests.get(self.base_url, params=args)

        if request.status_code == 200:
            response = request.json()
        else:
            print(request.json())
            raise Exception("An unknown error occured, status_code = {}".format(request.status_code))

        return response["curl"]


class ProxyRotator2:

    def __init__(self):
        self.url = 'http://httpbin.org/ip'
        self.key = '9c8e8101692e5fbdc9f198fa3e914dc6'

    def get_proxy(self):
        headers = {
            'Accept': 'application/json'
        }

        request = requests.get('http://api.scraperapi.com/?key=' + self.key + '&url=' + self.url, headers=headers)

        print(request.json())

if __name__ == "__main__":
    PR = ProxyRotator()
    print(PR.get_proxy(protocol="http"))

    proxyDict = {
        "http": "23.88.106.10",
    }

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/60.0.3112.113 Safari/537.36'}

    r = requests.get("http://azlyrics.com/lyrics/usher/climax", headers=headers, proxies=proxyDict)
    print(r.status_code)
    print(r.json())
