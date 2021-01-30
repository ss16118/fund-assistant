import os
import re
import traceback
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote, unquote

import requests

from config import *
from constants import *
from logger import logger


class GoogleClient:
    def __init__(self):
        if os.environ["API_KEY"] is None:
            print("API_KEY for google services needs to be present!")
            exit(-1)
        self.key = os.environ["API_KEY"]

    def analyze_sentiment(self):
        payload = open(REQUEST_FILE, "rb")
        headers = {'content-type': 'application/json'}
        response = requests.post(GOOGLE_LANGUAGE_API.format("analyzeSentiment", self.key),
                                 data=payload, headers=headers)
        return response.json()


class GoogleServices:
    def __init__(self):
        self.client = GoogleClient()
        logger.log("Google services initialized successfully")

    def google_search(self, query, num_result, date_range):
        """
        Returns a list of search results given the query.
        Each element in the list includes both the title
        as well as the url of the result.
        """
        return search(query, num_result, date_range)

    def analyze_text(self):
        reply = self.client.analyze_sentiment()
        return reply


"""
Search functionality comes from the following repo:
https://github.com/aviaryan/python-gsearch/blob/master/gsearch/googlesearch.py
"""


def is_url(url):
    """
    checks if :url is a url
    """
    regex = r'((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)'
    return re.match(regex, url) is not None


def prune_html(text):
    """
    https://stackoverflow.com/a/42461722/2295672
    """
    text = re.sub(r'<.*?>', '', text)
    return text


def convert_unicode(text):
    """
    converts unicode HTML to real Unicode
    """
    try:
        s = unescape(text)
    except Exception:
        # Python 3.3 and below
        # https://stackoverflow.com/a/2360639/2295672
        s = HTMLParser().unescape(text)
    return s


def download(query, num_results, date_range):
    """
    downloads HTML after google search
    """
    # https://stackoverflow.com/questions/11818362/how-to-deal-with-unicode-string-in-url-in-python3
    name = quote(query)

    name = name.replace(' ', '+')
    url = 'http://www.google.com/search?q={}&tbs=qdr:{}&tbm=nws'.format(name, date_range)
    if num_results != 10:
        url += '&num=' + str(num_results)  # adding this param might hint Google towards a bot
    # req = request.get(url)
    try:
        response = requests.get(url)
    except Exception:  # catch connection issues
        # may also catch 503 rate limit exceed
        print('[ERROR] Search failed!\n')
        traceback.print_exc()
        return ''
    data = response.text
    # print(data)
    return data


def search(query, num_results=10, date_range="w"):
    """
    searches google for :query and returns a list of tuples
    of the format (name, url)
    """
    data = download(query, num_results, date_range)
    results = re.findall(r'<div class=\"\w+\"><a href=\"/url?.*?\">.*?</div>', data, re.IGNORECASE)
    if results is None or len(results) == 0:
        print('No results where found. Did the rate limit exceed?')
        return []
    # search has results
    links = []
    for r in results:
        url_match = re.search(r'<a\s*href=\"(.*?)\">', r, flags=re.IGNORECASE)
        if url_match is None:
            continue
        # parse url
        url = url_match.group(1)
        # clean url https://github.com/aviaryan/pythons/blob/master/Others/GoogleSearchLinks.py
        url = re.sub(r'^.*?=', '', url, count=1)  # prefixed over urls \url=q?
        url = re.sub(r'\&amp.*$', '', url, count=1)  # suffixed google things
        url = unquote(url)
        # url = re.sub(r'\%.*$', '', url) # NOT SAFE, causes issues with Youtube watch url
        # parse name
        title_match = re.search(r'<h3 class=\"\w+\"><div class=\"[\w\s]+\">(.*?)<\/div>', r, flags=re.IGNORECASE)
        if title_match is None:
            continue
        name = prune_html(title_match.group(1))
        name = convert_unicode(name).strip(" ...")
        # append to links
        if is_url(url):  # can be google images result
            links.append((name, url))
    return links
