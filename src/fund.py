from bs4 import BeautifulSoup
from utils import *


class Fund:
    def __init__(self, code):
        self.code = code
        self.fund_data_html = requests.get(FUND_DATA_URL.format(code)).text
        self.stock_html = requests.get(STOCK_DATA_URL.format(code)).content

    @property
    def name(self):
        return get_variable_from_js(self.fund_data_html, var_name["fund_name"])

    @property
    def stock_codes(self):
        return list(map(lambda x: x[:-1], get_variable_from_js(self.fund_data_html, var_name["stock_codes"])))

    @property
    def stocks(self):
        """
        Return the data on the stock positions in a list of dictionaries with the following format:
        [{"code":stock_code,
         "name": stock_name,
         "position_ratio": position_ratio}]
        """
        soup = BeautifulSoup(self.stock_html, "html.parser")
        table = soup.find(id="quotationItem_DataTable")
        rows = table.find_all("table")[0].find_all("tr")[1:]  # Ignore the column names of the table
        stocks = []
        for row in rows:
            columns = row.find_all("td")
            stock_name = columns[0].get_text().strip(" ")
            position_ratio = float(columns[1].get_text().strip(" ").strip("%"))
            stock_code = columns[2].get("stockcode").strip("stock_")
            stocks.append(dict(
                code=stock_code,
                name=stock_name,
                position_ratio=position_ratio
            ))
        return stocks
