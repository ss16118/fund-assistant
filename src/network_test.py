import os

import requests

from constants import *


def network_test():
    """
    Test the network connectivity. Focus on the Google services that
    will be used in the program. If the connectivity test fails, will
    warn the user.
    """
    test_fund_code = "161725"

    def can_fetch_fund_data():
        try:
            for url in [FUND_DATA_URL, STOCK_DATA_URL, NET_VALUE_URL]:
                response = requests.get(url.format(test_fund_code, None))
                if not str(response.status_code).startswith("2"):
                    raise ConnectionError("Failed to connect to {}".format(url))
            return True
        except Exception as exception:
            print("Failed to fetch fund data, please check network connectivity: {}".format(exception))
        return False

    def can_connect_to_google_services():
        try:
            api_key = os.environ["API_KEY"]
            payload = open(REQUEST_TEST_FILE, "rb")
            headers = {'content-type': 'application/json'}
            response = requests.post(GOOGLE_LANGUAGE_API.format(api_key), data=payload, headers=headers)
            if not str(response.status_code).startswith("2"):
                print("Failed to connect to Google natural language api")
                return False

            response = requests.get("http://www.google.com/search?q=test")
            if not str(response.status_code).startswith("2"):
                print("Failed to fetch query results from Google")
            return True
        except Exception as exception:
            print("Failed to fetch fund data, please check network connectivity: {}".format(exception))
        except KeyError:
            print("Please add your google API key to the list of environment variables")
        return False

    if not all([can_fetch_fund_data(), can_connect_to_google_services()]):
        print("Network connectivity test failed...")
    else:
        print("Network connection stable...")
