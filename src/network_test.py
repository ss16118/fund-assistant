import os

import requests

from constants import *
from utils import clear_console

TEST_URL_1 = "https://finance.sina.com.cn/stock/observe/2021-01-26/doc-ikftssap1033658.shtml"
TEST_URL_2 = "http://www.sohu.com/a/447342555_267106"
TEST_URL_3 = "https://stock.stcn.com/djjd/202101/t20210129_2786925.html"


def network_test():
    """
    Test the network connectivity. Focus on the Google services that
    will be used in the program. If the connectivity test fails, will
    warn the user.
    """

    print("Testing network connectivity...")
    test_fund_code = "161725"

    def can_fetch_fund_data():
        print("Testing fund data APIs...")
        response_time = 0
        try:
            for url in [FUND_DATA_URL, STOCK_DATA_URL, NET_VALUE_URL]:
                response = requests.get(url.format(test_fund_code, None))
                if not str(response.status_code).startswith("2"):
                    raise ConnectionError("Failed to connect to {}".format(url.format(test_fund_code, None)))
                response_time += response.elapsed.total_seconds()
            print("Average time delay: {:.3f}s".format(response_time / 3))
            return True
        except Exception as exception:
            print("Failed to fetch fund data, please check network connectivity: {}".format(exception))
        return False

    def can_fetch_news_articles():
        print("Testing connection to news articles...")
        response_time = 0
        try:
            for url in [TEST_URL_1, TEST_URL_2, TEST_URL_3]:
                response = requests.get(url)
                if not str(response.status_code).startswith("2"):
                    raise ConnectionError("Failed to connect to {}".format(url))
                response_time += response.elapsed.total_seconds()
            print("Average time delay: {:.3f}s".format(response_time / 3))
            return True
        except Exception as exception:
            print("Failed to fetch news articles, please check network connectivity: {}".format(exception))
            return False

    def can_connect_to_google_services():
        print("Testing connection to Google services...")
        response_time = 0
        try:
            api_key = os.environ["API_KEY"]
            payload = open(REQUEST_TEST_FILE, "rb")
            headers = {'content-type': 'application/json'}
            response = requests.post(GOOGLE_LANGUAGE_API.format(api_key), data=payload, headers=headers)
            if not str(response.status_code).startswith("2"):
                print("Failed to connect to Google natural language api")
                return False
            response_time += response.elapsed.total_seconds()

            response = requests.get("http://www.google.com/search?q=test")
            if not str(response.status_code).startswith("2"):
                print("Failed to fetch query results from Google")
            response_time += response.elapsed.total_seconds()
            print("Average time delay: {:.3f}s".format(response_time / 2))
            return True
        except Exception as exception:
            print("Failed to connect to Google services, please check network connectivity: {}".format(exception))
        except KeyError:
            print("Please add your google API key to the list of environment variables")
        return False

    if not all([can_fetch_fund_data(), can_fetch_news_articles(), can_connect_to_google_services()]):
        print("Network connectivity test failed...")
    else:
        clear_console()
        print("Network connection stable...")
