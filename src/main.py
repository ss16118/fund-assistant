from fund import Fund
from google_services import GoogleServices
from config import *
from utils import *
from logger import logger

if __name__ == '__main__':
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
