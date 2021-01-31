import traceback
from datetime import datetime

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

from logger import logger
from utils import *
import requests
import dateutil.relativedelta as date_diff

var_names = dict(
    name="fS_name",
    stock_codes="stockCodes",
    fund_yield_one_year="syl_1n",
    fund_yield_six_months="syl_6y",
    fund_yield_three_months="syl_3y",
    fund_yield_one_month="syl_1y"
)

nav_columns = ["date", "net_asset_value", "cumulative_value", "daily_yield"]


class Fund:
    def __init__(self, code):
        self.code = code
        self.fund_data_html = requests.get(FUND_DATA_URL.format(code)).text
        self.stock_html = requests.get(STOCK_DATA_URL.format(code)).content
        self._stocks = None
        self._fund_data = None
        self.overall_prediction = None
        self._historical_data = None

    @property
    def data(self):
        """
        Parse and retrieve data related to the fund from the html
        """
        if self._fund_data is not None:
            return self._fund_data
        else:
            try:
                fund_data = {}
                for metric in var_names.keys():
                    fund_data[metric] = get_variable_from_js(self.fund_data_html, var_names[metric])
                self._fund_data = fund_data
                return fund_data
            except AttributeError as exception:
                raise exception

    @property
    def historical_data(self):
        """
        Code from https://zhuanlan.zhihu.com/p/58264923.
        Return the historical net asset values of the fund in a pandas dataframe.
        """
        if self._historical_data is not None:
            return self._historical_data
        else:
            logger.log("Retrieving historical data...", quiet=False)
            try:
                # First obtain the total number of pages
                net_value_html = requests.get(NET_VALUE_URL.format(self.code, None)).text
                pages = int(re.search(r"pages:(.*),", net_value_html).group(1))

                all_records = []

                for page in range(1, pages + 1):
                    net_value_html = requests.get(NET_VALUE_URL.format(self.code, page)).text
                    soup = BeautifulSoup(net_value_html, "html.parser")

                    for row in soup.findAll("tbody")[0].findAll("tr"):
                        row_record = []
                        for record in row.findAll("td"):
                            value = record.contents
                            # Handle empty values
                            row_record.append(np.nan if len(value) == 0 else value[0])
                        all_records.append(row_record)

                logger.log("Successfully collected data on historical net asset values")
                np_records = np.array(all_records)
                historical_data = pd.DataFrame()
                for i, column in enumerate(nav_columns):  # Keep only the first four columns
                    historical_data[column] = np_records[:, i]

                # Modify data types
                historical_data["date"] = pd.to_datetime(historical_data["date"], format="%Y-%m-%d")
                historical_data["net_asset_value"] = historical_data["net_asset_value"].astype(float)
                historical_data["cumulative_value"] = historical_data["cumulative_value"].astype(float)
                historical_data["daily_yield"] = historical_data["daily_yield"].str.strip("%").astype(float)
                historical_data = historical_data.sort_values(by="date", axis=0, ascending=True).reset_index(drop=True)
                self._historical_data = historical_data
                return historical_data

            except Exception as exception:
                traceback.print_exc()
                logger.log("Failed to fetch data on historical data on {}: {}".format(self.code, exception),
                           "error", False)

    def net_asset_values(self, months=1):
        return self.get_historical_data(["net_asset_value"], months)

    def cumulative_net_values(self, months=1):
        return self.get_historical_data(["cumulative_value"], months)

    def daily_yields(self, months=1):
        return self.get_historical_data(["daily_yield"], months)

    def get_historical_data(self, column_names, months):
        data = self.historical_data
        data = data[["date", *column_names]]
        date = datetime.today() - date_diff.relativedelta(months=months)
        data = data[data["date"] >= date]
        return data.iloc[::-1]

    @property
    def yields(self):
        """
        Return the yields of the fund in the following format:
        [(time_period, yield)]
        """
        data = self.data
        yields = []
        for item in data.items():
            metric, val = item
            if metric.startswith("fund_yield"):
                yields.append(item)
        return yields

    @property
    def stock_codes(self):
        return [info["code"] for info in self.stocks]

    @property
    def stock_names(self):
        return [info["name"] for info in self.stocks]

    @property
    def stocks(self):
        """
        Return the data on the stock positions in a list of dictionaries with the following format:
        [{"code":stock_code,
         "name": stock_name,
         "position_ratio": position_ratio}]
        """
        if self._stocks is not None:
            return self._stocks
        else:
            soup = BeautifulSoup(self.stock_html, "html.parser")
            table = soup.find(id="quotationItem_DataTable")
            rows = table.find_all("table")[0].find_all("tr")[1:]  # Ignore the column names of the table
            stocks = []
            for row in rows:
                columns = row.find_all("td")
                if len(columns) > 3:
                    stock_name = columns[0].get_text().strip(" ")
                    position_ratio = float(columns[1].get_text().strip(" ").strip("%"))
                    stock_code = columns[2].get("stockcode").strip("stock_")
                    stocks.append(dict(
                        code=stock_code,
                        name=stock_name,
                        position_ratio=position_ratio
                    ))
            self._stocks = stocks
            return stocks
