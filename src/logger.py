import logging

from utils import read_json_file, dump_json_to_file

from constants import LOG_FILE, ARTICLES_LOG_FILE

log_levels = dict(
    info=logging.info,
    warning=logging.warning,
    debug=logging.debug,
    error=logging.error,
    critical=logging.critical
)


class InfoLogger:
    def __init__(self, log_path, article_log_path):
        self.log_path = log_path
        self.article_log = article_log_path
        logging.basicConfig(format='[%(levelname)s] %(asctime)s: %(message)s',
                           datefmt='%m/%d/%Y %I:%M:%S %p',
                           level=logging.INFO,
                           handlers=[logging.FileHandler(filename=log_path, encoding='utf-8', mode='a+')])
        self.log("Log loaded successfully from {}".format(LOG_FILE))

    def log(self, message, level="info", quiet=True):
        """
        Log the given message to the log file. If
        quiet is set to False, also print in console.
        """
        log_levels[level](message)
        if not quiet:
            print(message)

    def log_article(self, stock_name, search_result, content):
        """
        Log the news article to logs/article.log.json
        :param stock_name: name of the stock which was used as the search query
        :param search_result: a tuple with the first element being the title of the
        title of the search result and second element being the url.
        :param content: the text content of the article
        """
        title, url = search_result
        data = read_json_file(self.article_log)
        if data.get(stock_name) is None:
            data[stock_name] = dict()
        data[stock_name][url] = dict(
            title=title,
            content=content
        )
        dump_json_to_file(data, self.article_log)
        self.log("Saved content of article {} to article.log.json. ({})".format(title, stock_name))

    def get_all_articles(self):
        """
        Return all the articles in articles.log.json in the following format:
        [(index, stock_name, title, url)]
        """
        data = read_json_file(self.article_log)
        index = 1
        articles = []
        for stock_name in data.keys():
            for url, article in data[stock_name].items():
                articles.append((index, stock_name, article["title"], url))
                index += 1
        return articles

    def get_cached_stock_names(self):
        """
        Return all the names of the stocks to which the articles are related.
        """
        data = read_json_file(self.article_log)
        return list(data.keys())

    def search_article_content(self, url):
        """
        Return the title and content of the article that has been extracted and saved in articles.log.json
        in a tuple. Return None if there is no entry cached.
        """
        data = read_json_file(self.article_log)
        try:
            for stock_name in data.keys():
                if data[stock_name].get(url) is not None:
                    return data[stock_name].get(url).get("content")
        except KeyError:
            return None

    def get_all_content(self):
        """
        Return all the content in the log file as a list of strings.
        Each element in the list represents one line in the file.
        """
        with open(self.log_path, "r", encoding="utf-8") as log_file:
            content = log_file.readlines()
            return [line.strip() for line in content if line.strip()]

    def clear_log(self):
        with open(self.log_path, "w"):
            pass

    def clear_article_log(self):
        with open(self.article_log, "w"):
            pass
        dump_json_to_file({}, self.article_log)


logger = InfoLogger(LOG_FILE, ARTICLES_LOG_FILE)
