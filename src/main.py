import os
import traceback

from config import NUM_RESULTS
from fund import Fund
from google_services import GoogleServices
from text_extractor import HTMLTextExtractor
from utils import *
try:
    from logger import logger
except FileNotFoundError:
    print("Log files cannot be found!")
    exit()
from cmd import Cmd


class FundAssistant(Cmd):
    prompt = "fund-assistant> "
    intro = "Welcome to FundAssistant!\nType '?' to see all available commands.\nType 'exit' to exit the program."

    def __init__(self):
        Cmd.__init__(self)
        self.fund_obj = None
        self.google_service = GoogleServices()
        self.text_extractor = HTMLTextExtractor()
        self.analysis_statistics = None
        self.prediction_contribution = None

    def do_set(self, fund_code):
        """Sets the fund to analyze to be the one specified by the parameter fund code.
Usage: fund <fund_code>"""

        # Change the command prompt style
        logger.log("Retrieving data on fund with code {}".format(fund_code))
        try:
            self.fund_obj = Fund(fund_code)
            fund_name = self.fund_obj.data["name"]
            self.prediction_contribution = dict()
            logger.log("Data retrieval successful", quiet=False)
            logger.log("Current fund set to {} ({})".format(fund_name, fund_code), quiet=False)
            self.prompt = "fund-assistant ({})> ".format(fund_code)
        except AttributeError:
            logger.log("Failed to retrieve data on fund with code {}\n"
                       "Make sure there is a stable Internet connection and the fund exists.".format(fund_code),
                       "error", False)
        except Exception as exception:
            logger.log(exception, "error", quiet=False)

    def do_fund(self, arg):
        """Performs actions based on the argument given:
> fund info      : prints all information on the current fund
> fund code      : prints the fund code
> fund name      : prints the name of the current fund
> fund stocks    : prints the stock positions of the current fund
> fund yields    : prints the yields of the fund in 1 year, 6 months, 3 months and 1 month
> fund prediction: prints the contribution of each stock to the overall prediction of the fund."""

        def print_fund_code():
            logger.log("code: {}".format(self.fund_obj.code), quiet=False)

        def print_fund_name():
            logger.log("name: {}".format(self.fund_obj.data["name"]), quiet=False)

        def print_stocks():
            logger.log("Stock positions:", quiet=False)
            table = table_str(self.fund_obj.stocks, ["Code", "Name", "Ratio"])
            logger.log(table, quiet=False)

        def print_yields():
            logger.log("Yields:", quiet=False)
            for metric, value in self.fund_obj.yields:
                logger.log("{}: {}%".format(metric.replace("_", " ").strip("fund yield"), value), quiet=False)

        def print_prediction():
            if self.fund_obj.overall_prediction is not None:
                table = table_str(list(self.prediction_contribution.values()),
                                  ["Name", "Sentiment score", "Position Ratio", "Weighted Score"])
                logger.log(table, quiet=False)
            else:
                logger.log("You need to run 'predict all' command first to obtain the predictions of each stock",
                           "error", False)

        def print_fund_info():
            print_fund_code()
            print_fund_name()
            print_stocks()
            print_yields()

        actions = dict(
            info=print_fund_info,
            code=print_fund_code,
            name=print_fund_name,
            stocks=print_stocks,
            yields=print_yields,
            prediction=print_prediction
        )

        try:
            if self.fund_obj is None:
                logger.log("Fund has not been set yet. Use 'set <fund_code>' to specify the fund.", "warning", False)
            else:
                logger.log("Executing command 'fund {}'...".format(arg))
                actions[arg]()
        except KeyError:
            logger.log("Command 'fund {}' not supported".format(arg), "error", False)

    def do_predict(self, arg):
        """Performs actions based on the argument given:
> predict all         : performs an aggregate analysis to predict the trend of the net asset value of the fund
> predict <stock_code>: predict the trend of the value of the stock given by <stock_code>
> predict <stock_name>: predict the trend of the value of the stock given by <stock_name>"""
        self.analysis_statistics = dict(
            crawled_links=0,
            failed_links=[]
        )
        logger.log("Executing command 'predict {}'...".format(arg))
        if arg == "all":
            prediction = 0
            for stock in self.fund_obj.stocks:
                sentiment_score = self._run_analysis(stock["name"])
                weighted_score = sentiment_score * stock["position_ratio"]
                self.prediction_contribution[stock["code"]] = dict(
                    name=stock["name"],
                    sentiment_score=sentiment_score,
                    position_ratio=stock["position_ratio"],
                    weighted_score=weighted_score
                )
                logger.log("Weighted sentiment score of {:.3f} added to the current prediction".format(weighted_score),
                           quiet=False)
                prediction += weighted_score
            self.fund_obj.overall_prediction = prediction / 100
            logger.log("Prediction for {} ({}): {:.5f}"
                       .format(self.fund_obj.data["name"], self.fund_obj.code, prediction / 100), quiet=False)
            logger.log("Use 'fund prediction' to view the detailed contribution of each stock", quiet=False)
        else:
            # Only supports stocks held in the fund
            name = None
            for stock in self.fund_obj.stocks:
                if stock["name"] == arg or stock["code"] == arg:
                    name = stock["name"]
            if name is not None:
                self._run_analysis(name)
            else:
                logger.log("Stock {} is not held in the current fund.\n"
                           "Use 'fund stocks' to see stocks that can be analyzed.", "error", False)
        logger.log("Statistics:")
        logger.log("Total number links crawled: {}".format(self.analysis_statistics["crawled_links"]), quiet=False)
        failed_links_num = len(self.analysis_statistics["failed_links"])
        logger.log("Number of failed links: {}".format(failed_links_num), quiet=False)
        for url, exception in self.analysis_statistics["failed_links"]:
            logger.log("{}: {}".format(url, exception), quiet=False)

    def _run_analysis(self, stock_name):
        """
        Performs the operation of gathering news links from Google, extracting
        text from news articles, then sending it to Google natural language API.
        :param stock_name: name of the stock to be analyzed
        :return: the sentiment score returned by Google API
        """
        score = 0
        logger.log("Searching news articles on Google on {}".format(stock_name), quiet=False)
        clear_payload()
        try:
            results = self.google_service.google_search(stock_name, NUM_RESULTS)
            logger.log("Search results retrieved successfully")
            for i, result in enumerate(results):
                logger.log("{}. {}: {}".format(i + 1, *result), quiet=False)
                url = result[1]
                title = result[0]
                try:
                    content_lines = self.text_extractor.extract_essential_text(url)
                    content_lines = [title] + content_lines
                    logger.log_article(stock_name, result, "\n".join(content_lines))
                    add_to_payload("".join(content_lines) + "\n")
                except Exception as exception:
                    logger.log("Failed to extract text from url {}: {}".format(url, exception), "error")
                    self.analysis_statistics["failed_links"].append((url, exception))
                finally:
                    self.analysis_statistics["crawled_links"] += 1
            try:
                prepare_payload()
                reply = self.google_service.analyze_text()
                logger.log("Obtained sentiment analysis for information gathered on {}: (score: {}, magnitude: {})".
                           format(stock_name, reply["documentSentiment"]["score"],
                                  reply["documentSentiment"]["magnitude"]), quiet=False),
                score = reply["documentSentiment"]["score"]
            except Exception as exception:
                logger.log("Failed to analyze sentiment for information gathered on {}: {}"
                           .format(stock_name, exception), "error", False)
        except Exception as exception:
            logger.log("Failed to fetch news articles on {} from Google due to: {}".format(stock_name, exception),
                       "error", False)
        finally:
            return score

    def complete_predict(self, text, line, begidx, endidx):
        if self.fund_obj is not None:
            stock_codes = self.fund_obj.stock_codes
            stock_names = self.fund_obj.stock_names
            if not text:
                completions = ["{}: {}".format(c, n) for c, n in zip(stock_codes, stock_names)]
            else:
                if text.isdigit():
                    completions = [c for c in stock_codes if c.startswith(text)]
                else:
                    completions = [c for c in stock_names if c.startswith(text)]
            return completions
        return ""

    def do_log(self, arg):
        """Performs actions based on the argument given:
> log clear      : clears all the log entries
> log print all  : prints all the content in the log (use with caution as the size of the log might be large)
> log print <int>: prints the last <int> of lines of the log file."""
        args = arg.split()

        def print_content():
            lines = logger.get_all_content()
            try:
                num_lines = len(lines) if args[1] == "all" else int(args[1])
                for i, line in enumerate(lines[-num_lines:]):
                    print("{:>5} {}".format(num_lines - i, line))
            except IndexError:
                logger.log("Please enter a second argument for the 'log' command", "error", False)
            except ValueError:
                logger.log("Please enter a valid integer to represent the number of lines", "error", False)

        actions = dict(
            clear=logger.clear_log,
            print=print_content
        )
        try:
            logger.log("Executing command 'log {}'...".format(arg))
            actions[args[0]]()
        except KeyError:
            logger.log("Command 'log {}' not supported".format(arg), "error", False)

    def do_clear(self, _):
        """Clears the console"""
        logger.log("Console cleared")
        os.system('cls' if os.name == 'nt' else 'clear')

    def do_exit(self, _):
        """Exit the application"""
        self.do_EOF(_)
        return True

    def do_EOF(self, _):
        return True


if __name__ == '__main__':
    try:
        logger.log("Fund assistant started")
        FundAssistant().cmdloop()
    finally:
        logger.log("Exiting...", quiet=False)
    """
    fund = Fund(FUND_CODE)
    logger.log("Retrieving stocks in fund: {} ({})...".format(fund.name, FUND_CODE))
    stocks = fund.stocks
    print_table(stocks, ["Code", "Name", "Ratio"])

    google_service = GoogleServices()
    converter = HTML2TextConverter()
    debug = True
    # https://company.stcn.com/gsdt/202101/t20210112_2724171.html
    # https://finance.sina.com.cn/roll/2020-12-29/doc-iiznezxs9554428.shtml
    if debug:
        print(logger.search_article_content("https://finance.sina.com.cn/stock/hkstock/hkstocknews/2021-01-26/doc-ikftpnny2019534.shtml"))
        # print(converter.extract_essential_text("https://finance.sina.com.cn/roll/2020-12-29/doc-iiznezxs9554428.shtml"))
    prediction = 0

    failed_urls = []

    if not debug:
        for stock in stocks:
            clear_payload()
            stock_name = stock["name"]
            logger.log("Google search results on {}".format(stock_name))
            results = google_service.google_search(stock_name, NUM_RESULTS)
            for i, result in enumerate(results):
                print("{}. {}: {}".format(i + 1, *result))
                url = result[1]
                title = result[0]
                try:
                    content_lines = converter.extract_essential_text(url)
                    add_to_payload("".join(content_lines) + "\n")
                    logger.log_article(stock_name, result, "\n".join(content_lines))
                except Exception as exception:
                    logger.log(exception, "error")
                    failed_urls.append((url, exception))
            try:
                prepare_payload()
                reply = google_service.analyze_text()
                logger.log("Obtained sentiment analysis for information gathered on {}: (score: {}, magnitude: {})".
                           format(stock_name, reply.get("documentSentiment").get("score"),
                                  reply.get("documentSentiment").get("magnitude"))),
                sentiment_score = reply.get("documentSentiment").get("score")
                prediction += sentiment_score * stock["position_ratio"]
            except Exception as exception:
                logger.log("Failed to analyze sentiment for information gathered on {}: {}"
                           .format(stock_name, exception), "error")

        if len(failed_urls) > 0:
            print("\nFailed to fetch the following urls:")
            for url, exception in failed_urls:
                print("{}: {}".format(url, exception))
        print("Prediction for {} ({}): {}".format(fund.name, FUND_CODE, prediction / 100))
    """
