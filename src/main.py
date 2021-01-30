import cmd
import os
import traceback
from datetime import datetime
from enum import Enum
from functools import wraps

from tqdm import tqdm

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

shorthands = dict(
    nav="net_asset_value",
    cnv="cumulative_value",
    dy="daily_yield"
)


class DateRange(Enum):
    h = 'Past hour'
    d = 'Past day'
    w = 'Past week'
    m = 'Past month'
    y = 'Past year'


class FundAssistant(Cmd):
    """
    Interactive shell
    """
    prompt = "fund-assistant> "
    intro = "Welcome to FundAssistant!\nType '?' to see all available commands.\nType 'exit' to exit the program."

    def __init__(self):
        Cmd.__init__(self)
        self.fund_obj = None
        self.google_service = GoogleServices()
        self.text_extractor = HTMLTextExtractor()
        self.analysis_statistics = None
        self.prediction_contribution = None
        # Parameters used for stock analysis
        self.analysis_config = dict(
            num_results=10,
            date_range=DateRange.w,
            verbose=True
        )

    # ==================== Custom decorators ====================
    def _requires_fund_obj(func):
        @wraps(func)
        def inner(self, *args, **kwargs):
            if self.fund_obj is None:
                logger.log("Fund has not been set yet. Use 'set <fund_code>' to specify the fund.", "warning", False)
            else:
                return func(self, *args, **kwargs)

        return inner

    # ==================== Private helper functions ====================
    def _show_analysis_params(self):
        logger.log("num_results: {}".format(self.analysis_config["num_results"]), quiet=False)
        logger.log("date_range : {}".format(self.analysis_config["date_range"].value), quiet=False)
        logger.log("verbose    : {}".format(self.analysis_config["verbose"]), quiet=False)

    # ==================== Base class methods overrides ====================
    def parseline(self, line):
        if line != "":
            logger.log("Executing command '{}'...".format(line))
        ret = cmd.Cmd.parseline(self, line)
        return ret

    def emptyline(self):
        pass

    # ==================== Interactive commands ====================
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

    @_requires_fund_obj
    def do_fund(self, arg):
        """Performs actions based on the arguments given:
> fund info      : prints all information on the current fund
> fund code      : prints the fund code
> fund name      : prints the name of the current fund
> fund nav       : prints the net asset value of the fund in the past month
> fund nav <int> : prints the net asset value of the fund of the past <int> months
> fund cnv       : prints the cumulative net value of the fund in the past month
> fund cnv <int> : prints the cumulative net value of the fund in the past <int> months
> fund dy        : prints the daily yield of the fund in the past month
> fund dy <int>  : prints the daily yield value of the fund in the past <int> months
> fund stocks    : prints the stock positions of the current fund
> fund yields    : prints the yields of the fund in 1 year, 6 months, 3 months and 1 month
> fund prediction: prints the contribution of each stock to the overall prediction of the fund"""
        args = arg.split()

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

        def print_historical_data():
            column_name = args[0]
            months = 1
            try:
                if len(args) > 1:
                    months = int(args[1])
                data = self.fund_obj.get_historical_data([shorthands[column_name]], months)
                logger.log(data.to_string(index=False), quiet=False)
            except KeyError:
                logger.log("Parameter {} not supported".format(column_name), "error", False)
            except ValueError:
                logger.log("The parameter following '{}' must be an integer".format(column_name), "error", False)

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
            nav=print_historical_data,
            cnv=print_historical_data,
            dy=print_historical_data,
            prediction=print_prediction
        )

        try:
            command = args[0]
            actions[command]()
        except KeyError:
            logger.log("Command 'fund {}' not supported".format(arg), "error", False)

    @_requires_fund_obj
    def do_plot(self, arg):
        """Performs actions based on the arguments given:
> plot <options>      : plots the any combination of the three metrics nav, cnv, and dy for the current fund
                        in the past month. Note that metrics must be separated with spaces.
                        i.e. 'plot nav', 'plot nav cnv', 'plot nav cnv dy'
> plot <options> <int>: performs the same plotting action as 'plot <options>'. The only difference is
                        <int> specifies that data will be selected from the previous <int> months."""

        possible_metrics = {"nav", "cnv", "dy"}
        metrics_to_plot = []
        input_args = arg.split()
        months = 1
        for i, metric in enumerate(input_args):
            if i > 3:
                logger.log("The number of arguments cannot be greater than 4", "error", False)
                return
            if metric.isdigit():
                if i != len(input_args) - 1:  # if the integer argument is not the last argument
                    logger.log("The integer must be the last argument", "error", False)
                    return
                months = int(metric)
            else:
                if metric not in possible_metrics:
                    logger.log("Argument {} is not a possible metric to plot".format(metric), "error", False)
                    return
                else:
                    metrics_to_plot.append(metric)

        if len(metrics_to_plot) == 0:
            logger.log("There has to be at least one metric", "error", False)
        else:
            graph_historical_data(self.fund_obj.get_historical_data(list(shorthands.values()), months), metrics_to_plot)

    def do_param(self, arg):
        """Modifies the parameters used for predicting the value of stock. The parameters are as follows:
num_results: number of results retrieved from a single Google search query on the stock. [Default: 10]
date_range : date range of the Google query, has the the following options [Default: 'w']:
             h: past hour,
             d: past day,
             w: past week,
             m: past month,
             y: past year
verbose    : if set set to True, detailed messages will be printed out during news article retrieval. [Default: True]

Performs actions based on the arguments given:
> param show          : displays the values of the parameters in use
> param n <int>       : sets the num_results parameter to <int>
> param d <date_range>: sets the date_range parameter to be <date_range>. <date_range> can only be one of
                        letters in the list ['h', 'd', 'w', 'm', 'y']
> param v             : toggles the value of the verbose parameter. If verbose is True, it will set to
                        False after this command is executed, and vice versa."""
        args = arg.split()

        def show_params():
            logger.log("Analysis parameters (use 'help param' to see what each parameter does):", quiet=False)
            self._show_analysis_params()

        def set_num_results():
            try:
                new_num_results = int(args[1])
                if new_num_results == 0:
                    raise ValueError
                self.analysis_config["num_results"] = new_num_results
                logger.log("Parameter {} successfully set to '{}'".format("num_results", new_num_results), quiet=False)
            except IndexError:
                logger.log("There must another argument following 'n'", "error", False)
            except ValueError:
                logger.log("The second argument given must be an integer greater than 0.", "error", False)

        def set_date_range():
            try:
                self.analysis_config["date_range"] = DateRange[args[1]]
                logger.log("Parameter {} successfully set to '{}'".format("date_range", DateRange[args[1]].value),
                           quiet=False)
            except IndexError:
                logger.log("There must another argument following 'd'", "error", False)
            except KeyError:
                logger.log("The second argument can only be one of the letters from the list {}".format(
                    [date_range.name for date_range in DateRange]
                ), "error", False)

        def toggle_verbose():
            self.analysis_config["verbose"] = not self.analysis_config["verbose"]
            logger.log("Parameter {} successfully set to '{}'".format("verbose", self.analysis_config["verbose"]),
                       quiet=False)

        actions = dict(
            show=show_params,
            n=set_num_results,
            d=set_date_range,
            v=toggle_verbose
        )
        try:
            parameter = args[0]
            actions[parameter]()
        except KeyError:
            logger.log("Command 'param {}' not supported".format(arg), "error", False)

    def do_predict(self, arg):
        """Predicts the trend of the values of stocks based on news articles found on Google and
sentiment analysis of the content of the articles. For the aggregate analysis, a number between
-1 and 1 will be given. The greater the value, the more likely for the net asset value of the
fund to increase. If the number is less than 0, the net asset value of the fund is likely to
drop based on the prediction.
Performs actions based on the argument given:
> predict all         : performs an aggregate analysis to predict the trend of the net asset value of the fund
> predict <stock_code>: predicts the trend of the value of the stock given by <stock_code>
> predict <stock_name>: predicts the trend of the value of the stock given by <stock_name>"""
        self.analysis_statistics = dict(
            crawled_links=0,
            failed_links=[]
        )
        logger.log("Analysis will be run with the following parameters:", quiet=False)
        self._show_analysis_params()
        quiet = not self.analysis_config["verbose"]
        if arg == "all":
            prediction = 0
            for stock in self.fund_obj.stocks:
                sentiment_score = self._run_analysis(stock["name"], quiet)
                weighted_score = sentiment_score * stock["position_ratio"]
                self.prediction_contribution[stock["code"]] = dict(
                    name=stock["name"],
                    sentiment_score=sentiment_score,
                    position_ratio=stock["position_ratio"],
                    weighted_score=weighted_score
                )
                logger.log("Weighted sentiment score of {:.3f} added to the current prediction".format(weighted_score),
                           quiet=quiet)
                prediction += weighted_score
            self.fund_obj.overall_prediction = prediction / 100
            logger.log("Prediction for {} ({}): {:.5f}"
                       .format(self.fund_obj.data["name"], self.fund_obj.code, prediction / 100), quiet=False)
            table = table_str(list(self.prediction_contribution.values()),
                              ["Name", "Sentiment score", "Position Ratio", "Weighted Score"])
            logger.log(table, quiet=False)
        else:
            # Only supports stocks held in the fund
            name = None
            for stock in self.fund_obj.stocks:
                if stock["name"] == arg or stock["code"] == arg:
                    name = stock["name"]
            if name is not None:
                self._run_analysis(name, quiet)
            else:
                logger.log("Stock {} is not held in the current fund.\n"
                           "Use 'fund stocks' to see stocks that can be analyzed.".format(name), "error", False)
        logger.log("Statistics:")
        logger.log("Total number links crawled: {}".format(self.analysis_statistics["crawled_links"]), quiet=False)
        failed_links_num = len(self.analysis_statistics["failed_links"])
        logger.log("Number of failed links: {}".format(failed_links_num), quiet=False)
        for url, exception in self.analysis_statistics["failed_links"]:
            logger.log("{}: {}".format(url, exception), quiet=False)

    def _run_analysis(self, stock_name, quiet):
        """
        Performs the operation of gathering news links from Google, extracting
        text from news articles, then sending it to Google natural language API.
        :param stock_name: name of the stock to be analyzed
        :return: the sentiment score returned by Google API
        """
        score = 0
        logger.log("Searching news articles on Google on {}".format(stock_name), quiet=quiet)
        clear_payload()
        try:
            results = self.google_service.google_search(
                stock_name,
                self.analysis_config["num_results"],
                self.analysis_config["date_range"].name
            )
            logger.log("Search results retrieved successfully")

            iterator = tqdm(enumerate(results), total=len(results), desc=stock_name, ncols=100) \
                if quiet else enumerate(results)

            for i, result in iterator:
                logger.log("{}. {}: {}".format(i + 1, *result), quiet=quiet)
                title, url = result
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
                       "error", quiet)
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

    def do_article(self, arg):
        """In order for a news articles to be cached, 'predict' command needs to be run first.
Performs actions based on the arguments given:
> article view <int>       : print out the content of the article which has the index specified by <int>
> article list all         : lists the title and url of all the cached articles during analysis
> article list <stock_name>: lists the title and url of cached articles on the stock specified by <stock_name>
> article clear            : clears all the cached news articles"""
        args = arg.split()

        def view_article():
            try:
                index = int(args[1])
                if index == 0:
                    raise ValueError
                _, stock_name, title, url = logger.get_all_articles()[index - 1]
                logger.log("{}\n{}\n{}".format(stock_name, url, logger.search_article_content(url)),
                           quiet=False)
            except IndexError:
                logger.log("Please enter the index of the article which you wish to view", "error", False)
            except ValueError:
                logger.log("The index of the article must be an integer greater than 0.", "error", False)

        def list_articles():
            try:
                arg2 = args[1]
                stock_names = logger.get_cached_stock_names()
                if arg2 != "all" and arg2 not in stock_names:
                    logger.log("There is no cached news articles on {}".format(arg2), "error", False)
                    return
                stock_names = stock_names if arg2 == "all" else [arg2]
                all_articles = logger.get_all_articles()
                for name in stock_names:
                    logger.log("Stock: {}".format(name), quiet=False)
                    for i, _, title, url in filter(lambda t: t[1] == name, all_articles):
                        logger.log("{}. {}: {}".format(i, title, url), quiet=False)
            except IndexError:
                logger.log("Please enter a second argument for 'article list' command", "error", False)

        actions = dict(
            view=view_article,
            list=list_articles,
            clear=logger.clear_article_log
        )
        try:
            command = args[0]
            actions[command]()
        except KeyError:
            logger.log("Command 'article {}' not supported".format(arg), "error", False)

    def complete_article(self, text, line, begidx, endidx):
        args = line.split()
        if text == "" and args[1] == "list":
            return logger.get_cached_stock_names()
        else:
            return get_autocomplete_terms(text, logger.get_cached_stock_names())


    def do_log(self, arg):
        """Performs actions based on the arguments given:
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

    _requires_fund_obj = staticmethod(_requires_fund_obj)


if __name__ == '__main__':
    try:
        logger.log("Fund assistant started")
        FundAssistant().cmdloop()
    finally:
        logger.log("Exiting...", quiet=False)
