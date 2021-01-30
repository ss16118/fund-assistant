import json
import re

import chardet

from constants import *
from prettytable import PrettyTable
import matplotlib.pyplot as plt


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


def graph_historical_data(df, selected_columns):
    date = df["date"]
    nav = df["net_asset_value"]
    cumulative_value = df["cumulative_value"]
    daily_yield = df["daily_yield"]

    # Plot net asset value
    figure = plt.figure()
    ax1 = figure.add_subplot(111)
    if "nav" in selected_columns:
        ax1.plot(date, nav, label="Net asset value")
    if "cnv" in selected_columns:
        ax1.plot(date, cumulative_value, label='Cumulative net asset value')
    if "nav" in selected_columns or "cnv" in selected_columns:
        ax1.set_ylabel("Net asset value")
        ax1.set_xlabel("Date")
        plt.legend(loc="upper left")

    # Plot daily yield
    if "dy" in selected_columns:
        ax2 = ax1.twinx() if len(selected_columns) > 1 else ax1
        ax2.plot(date, daily_yield, 'r', label="Daily yield")
        ax2.set_ylabel("Daily yield")
        plt.legend(loc='upper right')

    plt.title('Net Asset Values of Fund')
    plt.show()


def table_str(data, column_names):
    """
    Print a list of dictionaries in a table
    """
    table = PrettyTable(column_names)
    for row in data:
        table.add_row(row.values())
    return table


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
    open(DATA_FILE, 'w').close()


def read_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as json_data:
        data = json.load(json_data)
        return data


def dump_json_to_file(json_data, file_path):
    with open(file_path, "w+", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)


def get_autocomplete_terms(text, options):
    """
    Return a list of auto complete terms based on the prefix text and
    a list of options
    :return: a list of auto complete terms that will be displayed
    """
    text = text.lower()
    return [option for option in options if option.startswith(text)]
