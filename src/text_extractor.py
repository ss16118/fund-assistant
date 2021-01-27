import html2text
import requests
from goose3 import Goose
from goose3.text import StopWordsChinese
from newspaper import Article

from logger import logger
from utils import *

class HTMLTextExtractor:
    def __init__(self):
        self.converter = html2text.HTML2Text()
        self.goose = Goose({"stopwords_class": StopWordsChinese})
        self.converter.ignore_links = True
        self.converter.ignore_emphasis = True
        self.converter.ignore_tables = True
        self.converter.ignore_images = True
        self.converter.unicode_snob = True
        logger.log("HTML text extractor initialized successfully")

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
            logger.log("Extracted text from url {}".format(url))
            return lines
        except Exception as exception:
            raise exception