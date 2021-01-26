import logging

from config import CONSOLE_OUTPUT
from utils import *

from constants import LOG_FILE, ARTICLES_LOG_FILE

log_levels = dict(
    info=logging.info,
    warning=logging.warning,
    debug=logging.debug,
    error=logging.error,
    critical=logging.critical
)


class InfoLogger:
    def __init__(self, log_path, article_log_path, console_output):
        self.console_output = console_output
        self.log_path = log_path
        self.article_log = article_log_path
        logging.basicConfig(format='[%(levelname)s] %(asctime)s: %(message)s',
                           datefmt='%m/%d/%Y %I:%M:%S %p',
                           level=logging.INFO,
                           handlers=[logging.FileHandler(filename=log_path, encoding='utf-8', mode='a+')])

    def log(self, message, level="info"):
        """
        Log the given message to the log file. If
        console is set to True, also print in console.
        """
        log_levels[level](message)
        if self.console_output:
            print(message)

    def log_article(self, stock_name, search_result, content):
        """
        Log the news article to logs/article.log.json
        :param stock_name: name of the stock which was used as the search query
        :param search_result: a tuple with the first element being the title of the
        title of the search result and second element being the url.
        :param content: the text content of the article
        :return: NULL
        """
        title, url = search_result
        data = read_json_file(self.article_log)
        if data.get(stock_name) is None:
            data[stock_name] = {}
        data[stock_name][url] = dict(
            title=title,
            content=content
        )
        dump_json_to_file(data, self.article_log)

    def search_article_content(self, url):
        """
        Return the content of the article that has been extracted and saved in articles.log.json.
        Return None if there is no entry cached.
        """
        data = read_json_file(self.article_log)
        try:
            for stock_name in data.keys():
                if data[stock_name].get(url) is not None:
                    return data[stock_name].get(url).get("content")
        except KeyError as exception:
            return None

    def clear_log(self):
        with open(self.log_path, "w"):
            pass

    def clear_article_log(self):
        with open(self.article_log, "w"):
            pass
        dump_json_to_file({}, self.article_log)


logger = InfoLogger(LOG_FILE, ARTICLES_LOG_FILE, CONSOLE_OUTPUT)
