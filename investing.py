"""
Investing Quick Analytics
Author: Elijah Lopez
Version: 1.4.2
Created: April 3rd 2020
Updated: April 18th 2020
"""

import calendar
from contextlib import suppress
import csv
from datetime import datetime, timedelta
import io
# noinspection PyUnresolvedReferences
import json
import math
import os
from pprint import pprint
# 3rd party libraries
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import pandas as pd
import requests
import yfinance as yf


NASDAQ_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download'
NYSE_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'
global_data = {}
stock_list = []
REQUEST_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}


def load_cache(filename='cache.json'):
    global global_data
    with suppress(FileNotFoundError):
        with open(filename) as f:
            global_data = json.load(f)


def save_cache(filename='cache.json'):
    def default(obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError
    with open(filename, 'w') as f:
        json.dump(global_data, f, indent=4, default=default)


def get_dow_tickers():
    if 'DOW' in global_data and datetime.strptime(global_data['DOW']['UPDATED'],
                                                     '%m/%d/%Y').date() == datetime.today().date():
        return set(global_data['DOW']['TICKERS'])
    resp = requests.get('https://money.cnn.com/data/dow30/')
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'class': 'wsod_dataTable wsod_dataTableBig'})
    _dow_tickers = {row.find('a').text.strip() for row in table.findAll('tr')[1:]}
    global_data['DOW'] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'),
                          'TICKERS': _dow_tickers}
    save_cache()
    return _dow_tickers


def get_sp500_tickers():
    global global_data
    if 'S&P500' in global_data and datetime.strptime(global_data['S&P500']['UPDATED'],
                                                     '%m/%d/%Y').date() == datetime.today().date():
        return set(global_data['S&P500']['TICKERS'])
    resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    _sp500_tickers = {row.find('td').text.strip() for row in table.findAll('tr')[1:]}
    global_data['S&P500'] = {'UPDATED': datetime.today().strftime('%m/%d//Y'), 'TICKERS': _sp500_tickers}
    save_cache()
    return _sp500_tickers


def get_tsx_tickers():
    global global_data
    if 'TSX' in global_data and datetime.strptime(global_data['TSX']['UPDATED'],
                                                  '%m/%d/%Y').date() == datetime.today().date():
        return set(global_data['TSX']['TICKERS'])
    base_url = 'http://eoddata.com/stocklist/TSX/'
    _tsx_tickers = []
    for i in range(26):
        resp = requests.get(base_url + chr(65 + i) + '.html')
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', {'class': 'quotes'})
        _tsx_tickers += {row.find('a').text.strip() + '.TO' for row in table.findAll('tr')[1:]}
    global_data['TSX'] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'), 'TICKERS': _tsx_tickers}
    save_cache()
    return _tsx_tickers


def tickers_from_csv(url, name=''):
    if name and name in global_data and datetime.strptime(global_data[name]['UPDATED'],
                                                          '%m/%d/%Y').date() == datetime.today().date():
        return set(global_data[name]['TICKERS'])
    s = requests.get(url).content
    _tickers = set(pd.read_csv(io.StringIO(s.decode('utf-8')))['Symbol'])
    global_data[name] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'), 'TICKERS': _tickers}
    save_cache()
    return _tickers


def get_company_name_from_ticker(ticker: str):
    global stock_list
    if not stock_list:
        r = requests.get('https://api.iextrading.com/1.0/ref-data/symbols')
        stock_list = r.json()
    return process.extractOne(ticker, stock_list)[0]


def get_ticker_info(ticker: str, round_values=True) -> dict:
    data_latest = yf.download(ticker, interval='1m', period='1d', threads=5, prepost=True, progress=False, group_by='ticker')
    data_last_close = yf.download(ticker, interval='1m', period='5d', threads=5, progress=False)['Close']
    latest_price = float(data_latest.tail(1)['Close'])
    closing_price = float(data_last_close.tail(1))
    timestamp = data_latest.tail(1).first_valid_index()
    if closing_price == latest_price:
        _today = datetime.today()
        _today = datetime(_today.year, _today.month, _today.day, 15, 59)
        _today -= timedelta(days=1)
        while _today.strftime('%Y-%m-%d %H:%M:%S-04:00') not in data_last_close:
            _today -= timedelta(days=1)
        closing_price = data_last_close[_today.strftime('%Y-%m-%d %H:%M:%S-04:00')]
        # as_of = f"Market Open: {timestamp['Datetime']}"
    # else:
        # as_of = f"After hours: {timestamp['Datetime']}"
    change = latest_price - closing_price
    if round_values:
        change = round(change, 4)
        percent_change = round(change/closing_price * 100, 2)
        latest_price = round(latest_price, 4)
        closing_price = round(closing_price, 4)
    else: percent_change = change/closing_price * 100
    name = get_company_name_from_ticker(ticker)['name']
    info = {'name': name, 'price': latest_price, 'change': change, 'percent_change': percent_change, 'timestamp': timestamp, 'symbol': ticker, 'last_close_price': closing_price}
    return info


def get_data(tickers: set, start_date=None, end_date=None, period='3mo', group_by='ticker'):
    # http://www.datasciencemadesimple.com/union-and-union-all-in-pandas-dataframe-in-python-2/
    # global_data['yf']
    # new format
    _key = ' '.join(tickers) + f' {start_date} {end_date} {period} {group_by}'
    if 'yf' not in global_data: global_data['yf'] = {}
    if _key not in global_data['yf']:
        _data = yf.download(tickers, start_date, end_date, period=period, group_by=group_by, threads=5)
    return _data


def get_analytics(ticker, _data, month=None, year=None, start_day=None, end_day=None):
    """DATA MUST INCLUDE THE TIME PERIOD"""
    today = datetime.today()
    if month is None: month = today.month - 1 if today.month > 1 else 12
    if year is None: year = today.year
    if start_day is None or start_day > calendar.monthrange(year, 1)[1]: start_day = 1
    if end_day is None or end_day > calendar.monthrange(year, 1)[1]: end_day = calendar.monthrange(year, 1)[1]

    start_date = f'{year}-{month:02}-{start_day:02}'
    while start_date not in _data[ticker]['Open']:
        start_day += 1
        start_date = f'{year}-{month:02}-{start_day:02}'
    month_open_price = _data[ticker]['Open'][start_date]
    end_date = f'{year}-{month:02}-{end_day:02}'
    while end_date not in _data[ticker]['Close']:
        end_day -= 1
        end_date = f'{year}-{month:02}-{end_day:02}'
    month_close_price = _data[ticker]['Close'][end_date]
    change = month_close_price - month_open_price
    percent_change = change / month_open_price
    start_volume = round(_data[ticker]['Volume'][start_date])
    end_volume = round(_data[ticker]['Volume'][end_date])
    avg_volume = (start_volume + end_volume) / 2
    return {'Start': month_open_price, 'End': month_close_price, 'Change': change, 'Percent Change': percent_change,
            'Open Volume': start_volume, 'Close Volume': end_volume, 'Avg Volume': avg_volume}


def get_analytics_multi(tickers, _data, month=None, year=None, start_day=None, end_day=None):
    return_obj = {}
    for ticker in tickers:
        monthly_analytics = get_analytics(ticker, _data, month=month, year=year, start_day=start_day, end_day=end_day)
        if not math.isnan(monthly_analytics['Start']):
            return_obj[ticker] = monthly_analytics
    return return_obj


def price_to_earnings(ticker, return_dict: dict = None, return_price=False):
    # uses latest EPS (diluted)
    if ticker.endswith('.TO'):
        ticker = '.'.join(ticker.split('.')[:-1])
        url = f'https://www.marketwatch.com/investing/stock/{ticker}/financials?country=ca'
    else:
        url = f'https://www.marketwatch.com/investing/stock/{ticker}/financials'
    try:
        text_soup = BeautifulSoup(requests.get(url, headers=REQUEST_HEADERS).text, 'html.parser')
    except requests.TooManyRedirects:
        return -999999
    pe = -999999
    price = -1
    with suppress(AttributeError):
        price = float(text_soup.find('p', {'class': 'bgLast'}).text.replace(',', ''))
        titles = text_soup.findAll('td', {'class': 'rowTitle'})

        for title in titles:
            if 'EPS (Diluted)' in title.text:
                eps = [td.text for td in title.findNextSiblings(attrs={'class': 'valueCell'}) if td.text]
                try: latest_eps = float(eps[-1])
                except ValueError: latest_eps = -float(eps[-1][1:-1])
                pe = price / latest_eps
                break
        if return_dict is not None: return_dict[ticker] = pe, price if return_price else pe
    if return_price: return pe, price
    return pe


def tickers_by_pe(tickers: set, output_to_csv='', console_output=True):
    """
    Returns the tickers by price-earnings ratio (remove negatives)
    :param tickers:
    :param output_to_csv:
    :param console_output:
    :return:
    """
    pes = {}
    # TODO: thread
    for ticker in tickers:
        pe = price_to_earnings(ticker)
        if pe > 0: pes[ticker] = pe
    pes = sorted(pes.items(), key=lambda item: item[1])
    if console_output:
        header = 'TOP 5 TICKERS BY P/E'
        line = '-' * len(header)
        print(f'{header}\n{line}')
        for i, (ticker, pe) in enumerate(pes):
            if i == 5: break
            print(f'{ticker}: {round(pe, 2)}')
    if output_to_csv:
        with open(output_to_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['TICKER', 'Price-earnings'])
            for ticker in pes:
                writer.writerow(ticker)
    return pes


def top_movers_and_losers(tickers, _data, month=None, year=None, start_day=None, end_day=None,
                          output_to_csv='', console_output=True):
    parsed_info = get_analytics_multi(tickers, _data, month=month, year=year, start_day=start_day, end_day=end_day)
    sorted_info = sorted(parsed_info.items(), key=lambda item: item[1]['Percent Change'])
    month = month if month is not None else datetime.today().month
    _month_name = calendar.month_name[month - 1]
    _year = datetime.today().year
    if console_output:
        bulls = ''
        bears = ''
        for i in range(min(5, len(sorted_info))):
            better_stock = sorted_info[-i - 1]
            worse_stock = sorted_info[i]
            open_close1 = f'{round(better_stock[1]["Start"], 2)}, {round(better_stock[1]["End"], 2)}'
            open_close2 = f'{round(worse_stock[1]["Start"], 2)}, {round(worse_stock[1]["End"], 2)}'
            bulls += f'\n{better_stock[0]} [{open_close1}]: {round(better_stock[1]["Percent Change"] * 100, 2)}%'
            bears += f'\n{worse_stock[0]} [{open_close2}]: {round(worse_stock[1]["Percent Change"] * 100, 2)}%'
        if start_day is None or end_day is None:
            header1 = f'BEST 5 PERFORMERS {_month_name} {_year}'
            header2 = f'WORST 5 PERFORMERS {_month_name} {_year}'
        else:
            header1 = f'BEST 5 PERFORMERS {start_day}/{month:02}/{_year} - {end_day}/{month:02}/{_year}'
            header2 = f'WORST 5 PERFORMERS {start_day}/{month:02}/{_year} - {end_day}/{month:02}/{_year}'
        line = '-' * len(header1)
        print(f'{line}\n{header1}\n{line}{bulls}')

        line = '-' * len(header2)
        print(f'{line}\n{header2}\n{line}{bears}')
    if output_to_csv:
        with open(output_to_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['TICKER'] + list(sorted_info[0][1].keys()))
            for ticker in sorted_info:
                writer.writerow([ticker[0]] + list(ticker[1].values()))
    return parsed_info


def get_tickers(market):
    # OPTIONS: CUSTOM, ALL, US, NYSE, NASDAQ, S&P500, DOW/DJIA, TSX/CA, Mortgage REITs
    tickers_to_download = set()
    if market in {'S&P500', 'S&P 500'}: tickers_to_download = tickers_to_download.union(get_sp500_tickers())
    if market in {'DOW', 'DJIA'}: tickers_to_download = tickers_to_download.union(get_dow_tickers())
    if market in {'NASDAQ', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(tickers_from_csv(NASDAQ_TICKERS_URL, name='NASDAQ'))
    if market in {'NYSE', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(tickers_from_csv(NYSE_TICKERS_URL, name='NYSE'))
    if market in {'TSX', 'CA', 'ALL'}: tickers_to_download = tickers_to_download.union(get_tsx_tickers())
    elif market == 'Mortgage REITs': tickers_to_download = {'NLY', 'STWD', 'AGNC', 'TWO', 'PMT', 'MITT', 'NYMT', 'MFA',
                                                          'IVR', 'NRZ', 'TRTX', 'RWT', 'DX', 'XAN', 'WMC'}
    elif market == 'OIL': tickers_to_download = {'DNR', 'PVAC', 'ROYT', 'SWN', 'CPE', 'CEQP', 'PAA', 'PUMP', 'PBF'}
    elif market in {'AUTO', 'AUTOMOBILE', 'CARS'}:
        tickers_to_download = {'TSLA', 'GM', 'F', 'RACE', 'FCAU', 'HMC', 'NIO', 'TTM', 'TM'}
    elif market == 'CUSTOM': pass
    # TODO: add more sectors
    # TODO: add foreign markets
    return tickers_to_download


load_cache()  # IGNORE. This loads cache from cache.json if the file exists

