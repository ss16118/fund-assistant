import json
import re

import chardet

import html2text
import requests
from goose3 import Goose
from goose3.text import StopWordsChinese
from newspaper import Article

from constants import *
from prettytable import PrettyTable

var_name = dict(
    fund_name="fS_name",
    stock_codes="stockCodes",
)


class HTML2TextConverter:
    def __init__(self):
        self.converter = html2text.HTML2Text()
        self.goose = Goose({"stopwords_class": StopWordsChinese})
        self.converter.ignore_links = True
        self.converter.ignore_emphasis = True
        self.converter.ignore_tables = True
        self.converter.ignore_images = True
        self.converter.unicode_snob = True

    def extract_raw_text(self, url):
        """
        Extract all the text in an HTML page. Does not ignore insignificant information.
        """
        try:
            request = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
            # Detect the encoding of the webpage
            encoding = get_page_encoding(request)
            # print(request.content.decode(encoding, errors="ignore"))
            return self.converter.handle(request.content.decode(encoding, errors="ignore"))
        except Exception as exception:
            raise exception

    def retrieve_raw_html(self, url):
        try:
            request = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
            # Detect the encoding of the webpage
            encoding = get_page_encoding(request)
            # print(request.content.decode(encoding, errors="ignore"))
            return request.content.decode(encoding, errors="ignore")
        except Exception as exception:
            raise exception

    def extract_essential_text(self, url):
        """
        Use Goose and newspaper library to extract the content of the article
        specified by the given url.
        :return: a list of strings that represent the content of the article
        """
        try:
            html = self.retrieve_raw_html(url)
            article_goose = self.goose.extract(raw_html=html)
            text = article_goose.cleaned_text
            # If Goose is unable to extract the article content, try newspaper
            if text == "":
                article = Article(url, language="zh")
                article.download(input_html=html)
                article.parse()
                # If newspaper is unable to extract the content of the article,
                # return the title of the page
                text = article.text if article.text != "" else article.title
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return lines
        except Exception as exception:
            raise exception


def get_page_encoding(request):
    match = re.search(r"charset=\"?([^\"]*)\"?", request.text)
    if match is not None:
        return match.group(1)
    else:
        return chardet.detect(request.content).get("encoding")


def get_variable_from_js(text, variable_name):
    """
    Extract the value assigned to a variable given by "variable_name"
    """
    list_str = re.search(r"var {}\s*=\s*(.*?);".format(variable_name), text).group(1)
    return json.loads(list_str)


def get_complete_fund_code(code):
    """
    Append 'sz' to the front if code starts with 0, 2 or 3. Append 'sh' otherwise
    """
    if code[0] in "023":
        return "sz.{}".format(code)
    else:
        return "sh.{}".format(code)


def print_table(data, column_names):
    """
    Print a list of dictionaries in a table
    """
    table = PrettyTable(column_names)
    for row in data:
        table.add_row(row.values())
    print(table)


def add_to_payload(text):
    """
    Append the given text to the file data/data.txt, which contains the content
    that will later be analyzed for sentiment.
    """
    with open(DATA_FILE, "a", encoding="utf-8") as file:
        file.write(text)


def prepare_payload():
    """
    Move the content of data/data.txt into data/request.json
    """
    data_file = open(DATA_FILE, "r", encoding="utf-8")
    text = data_file.read()
    data_file.close()
    data = read_json_file(REQUEST_FILE)
    data["document"]["content"] = text
    dump_json_to_file(data, REQUEST_FILE)


def clear_payload():
    """
    Remove all content in data/data.txt.
    """
    open('../data/data.txt', 'w').close()


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as json_data:
        data = json.load(json_data)
        return data


def dump_json_to_file(json_data, file_path):
    with open(file_path, "w+", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)
