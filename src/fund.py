from bs4 import BeautifulSoup
from utils import *
import requests

var_names = dict(
    name="fS_name",
    stock_codes="stockCodes",
    fund_yield_one_year="syl_1n",
    fund_yield_six_months="syl_6y",
    fund_yield_three_months="syl_3y",
    fund_yield_one_month="syl_1y"
)


class Fund:
    def __init__(self, code):
        self.code = code
        self.fund_data_html = requests.get(FUND_DATA_URL.format(code)).text
        self.stock_html = requests.get(STOCK_DATA_URL.format(code)).content
        self._stocks = None
        self._fund_data = None
        self.overall_prediction = None

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
