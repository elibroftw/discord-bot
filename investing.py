"""
Investing Quick Analytics
Author: Elijah Lopez
Version: 1.7.3
Source: https://gist.github.com/elibroftw/2c374e9f58229d7cea1c14c6c4194d27
"""

from contextlib import suppress
import csv
from datetime import datetime, timedelta
import io
import json
import math
# noinspection PyUnresolvedReferences
from pprint import pprint
# 3rd party libraries
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import pandas as pd
import requests
import yfinance as yf


NASDAQ_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download'
NYSE_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'
AMEX_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download'
GLOBAL_DATA = {}
US_COMPANY_LIST = []
SORTED_INFO_CACHE = {}  # for when its past 4 PM
REQUEST_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}
# NOTE: something for later https://www.alphavantage.co/

def load_cache(filename='investing_cache.json'):
    global GLOBAL_DATA
    with suppress(FileNotFoundError):
        with open(filename) as f:
            GLOBAL_DATA = json.load(f)


def save_cache(filename='investing_cache.json'):
    def default(obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError
    with open(filename, 'w') as f:
        json.dump(GLOBAL_DATA, f, indent=4, default=default)


def get_dow_tickers():
    if 'DOW' in GLOBAL_DATA and datetime.strptime(GLOBAL_DATA['DOW']['UPDATED'],
                                                  '%m/%d/%Y').date() == datetime.today().date():
        return set(GLOBAL_DATA['DOW']['TICKERS'])
    resp = requests.get('https://money.cnn.com/data/dow30/')
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'class': 'wsod_dataTable wsod_dataTableBig'})
    _dow_tickers = {row.find('a').text.strip() for row in table.findAll('tr')[1:]}
    GLOBAL_DATA['DOW'] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'),
                          'TICKERS': _dow_tickers}
    save_cache()
    return _dow_tickers


def get_sp500_tickers():
    global GLOBAL_DATA
    if 'S&P500' in GLOBAL_DATA and datetime.strptime(GLOBAL_DATA['S&P500']['UPDATED'],
                                                     '%m/%d/%Y').date() == datetime.today().date():
        return set(GLOBAL_DATA['S&P500']['TICKERS'])
    resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    _sp500_tickers = {row.find('td').text.strip() for row in table.findAll('tr')[1:]}
    GLOBAL_DATA['S&P500'] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'), 'TICKERS': _sp500_tickers}
    save_cache()
    return _sp500_tickers


def get_tsx_tickers():
    global GLOBAL_DATA
    if 'TSX' in GLOBAL_DATA and datetime.strptime(GLOBAL_DATA['TSX']['UPDATED'],
                                                  '%m/%d/%Y').date() == datetime.today().date():
        return set(GLOBAL_DATA['TSX']['TICKERS'])
    base_url = 'http://eoddata.com/stocklist/TSX/'
    _tsx_tickers = []
    for i in range(26):
        resp = requests.get(base_url + chr(65 + i) + '.html')
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', {'class': 'quotes'})
        _tsx_tickers += {row.find('a').text.strip().upper() + '.TO' for row in table.findAll('tr')[1:]}
    GLOBAL_DATA['TSX'] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'), 'TICKERS': _tsx_tickers}
    save_cache()
    return _tsx_tickers


def get_nyse_arca_tickers():
    global GLOBAL_DATA
    if 'NYSEARCA' in GLOBAL_DATA and datetime.strptime(GLOBAL_DATA['NYSEARCA']['UPDATED'], '%m/%d/%Y').date() == datetime.today().date():
        return set(GLOBAL_DATA['NYSE']['TICKERS'])
    base_url = 'https://www.nyse.com/api/quotes/filter'
    post_data = {'instrumentType': 'EXCHANGE_TRADED_FUND', 'pageNumber': 1, 'sortColumn': 'NORMALIZED_TICKER',
                 'sortOrder': 'ASC', 'maxResultsPerPage': 5000, 'filterToken': ''}
    r = requests.post('https://www.nyse.com/api/quotes/filter', json=post_data)
    _arca_tickers = {item['normalizedTicker'] for item in r.json()}
    GLOBAL_DATA['NYSEARCA'] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'), 'TICKERS': _arca_tickers}
    save_cache()
    return _arca_tickers



def tickers_from_csv(url, name=''):
    if name and name in GLOBAL_DATA and datetime.strptime(GLOBAL_DATA[name]['UPDATED'],
                                                          '%m/%d/%Y').date() == datetime.today().date():
        return set(GLOBAL_DATA[name]['TICKERS'])
    s = requests.get(url).content
    _tickers = set(pd.read_csv(io.StringIO(s.decode('utf-8')))['Symbol'])
    GLOBAL_DATA[name] = {'UPDATED': datetime.today().strftime('%m/%d/%Y'), 'TICKERS': _tickers}
    save_cache()
    return _tickers


def get_tickers(market):
    # TODO: add ETFs to the markets
    # OPTIONS: CUSTOM, ALL, US, NYSE, NASDAQ, S&P500, DOW/DJIA, TSX/CA, Mortgage REITs
    tickers_to_download = set()
    if market in {'S&P500', 'S&P 500'}: tickers_to_download = tickers_to_download.union(get_sp500_tickers())
    if market in {'DOW', 'DJIA'}: tickers_to_download = tickers_to_download.union(get_dow_tickers())
    if market in {'NASDAQ', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(tickers_from_csv(NASDAQ_TICKERS_URL, name='NASDAQ'))
    if market in {'NYSE', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(tickers_from_csv(NYSE_TICKERS_URL, name='NYSE'))
    if market in {'AMEX', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(tickers_from_csv(AMEX_TICKERS_URL, name='AMEX'))
    if market in {'NYSEARCA', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(get_nyse_arca_tickers())
    if market in {'TSX', 'CA', 'ALL'}: tickers_to_download = tickers_to_download.union(get_tsx_tickers())
    elif market == 'Mortgage REITs':
        tickers_to_download = {'NLY', 'STWD', 'AGNC', 'TWO', 'PMT', 'MITT', 'NYMT', 'MFA',
                               'IVR', 'NRZ', 'TRTX', 'RWT', 'DX', 'XAN', 'WMC'}
    elif market == 'OIL': tickers_to_download = {'DNR', 'PVAC', 'ROYT', 'SWN', 'CPE', 'CEQP', 'PAA', 'PUMP', 'PBF'}
    elif market in {'AUTO', 'AUTOMOBILE', 'CARS'}:
        tickers_to_download = {'TSLA', 'GM', 'F', 'RACE', 'FCAU', 'HMC', 'NIO', 'TTM', 'TM'}
    elif market == 'CUSTOM': pass
    # TODO: add more sectors
    # TODO: add foreign markets
    return tickers_to_download


def get_company_name_from_ticker(ticker: str):
    global US_COMPANY_LIST
    if ticker.count('.TO'):
        ticker = ticker.replace('.TO', '')
        r = requests.get(f'https://www.tsx.com/json/company-directory/search/tsx/{ticker}')
        results = {}
        for s in r.json()['results']:
            s['name'] = s['name'].upper()
            results[s['symbol']] = s
        best_match = process.extractOne(ticker, list(results.keys()))[0]
        return results[best_match]['name']
    else:
        if not US_COMPANY_LIST:
            r = requests.get('https://api.iextrading.com/1.0/ref-data/symbols')
            US_COMPANY_LIST = {s['symbol']: s for s in r.json()}
        best_match = process.extractOne(ticker, list(US_COMPANY_LIST.keys()))[0]
        # noinspection PyTypeChecker
        return US_COMPANY_LIST[best_match]['name']


def get_ticker_info(ticker: str, round_values=True) -> dict:
    # TODO: test pre-market values
    data_latest = yf.download(ticker, interval='1m', period='1d', threads=3, prepost=True, progress=False,
                              group_by='ticker')
    data_last_close = yf.download(ticker, interval='1m', period='5d', threads=3, progress=False)['Close']
    latest_price = float(data_latest.tail(1)['Close'])
    closing_price = float(data_last_close.tail(1))
    timestamp = data_latest.last_valid_index()
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
    name = get_company_name_from_ticker(ticker)
    info = {'name': name, 'price': latest_price, 'last_close_price': closing_price,
            'change': change, 'percent_change': percent_change, 'timestamp': timestamp, 'symbol': ticker}
    return info


def get_data(tickers: set, start_date=None, end_date=None, period='3mo', group_by='ticker', interval='1d',
             show_progress=True):
    # http://www.datasciencemadesimple.com/union-and-union-all-in-pandas-dataframe-in-python-2/
    # global_data['yf']
    # new format
    _key = ' '.join(tickers) + f' {start_date} {end_date} {period} {group_by}'
    if 'yf' not in GLOBAL_DATA: GLOBAL_DATA['yf'] = {}
    if _key not in GLOBAL_DATA['yf']:
        _data = yf.download(tickers, start_date, end_date, period=period, group_by=group_by, threads=3,
                            progress=show_progress, interval=interval)
        return _data


def parse_info(_data, ticker, start_date, end_date, start_price_key='Open'):
    """
    start_price_key: can be 'Open' or 'Close'
    TODO: change parse_info keys to snake_case
    """
    start_price = _data[ticker][start_price_key][start_date]
    end_price = _data[ticker]['Close'][end_date]
    change = end_price - start_price
    percent_change = change / start_price
    start_volume = round(_data[ticker]['Volume'][start_date])
    end_volume = round(_data[ticker]['Volume'][end_date])
    avg_volume = (start_volume + end_volume) / 2
    return {'Start': start_price, 'End': end_price, 'Change': change, 'Percent Change': percent_change,
            'Open Volume': start_volume, 'Close Volume': end_volume, 'Avg Volume': avg_volume}


def get_parsed_data(_data=None, tickers: list = None, market='ALL', sort_key='Percent Change',
                    of='day', start_date: datetime = None, end_date: datetime = None):
    """
    returns the parsed trading data sorted by percent change
    :param _data: if you are doing a lot of parsing but None is recommended unless you are dealing with >= 1 month
    :param tickers: specify if you have your own custom tickers list, otherwise market is used to get the list
    :param market: the market if data is None
    :param of: one of {'day', 'mtd', 'ytd', '1m', '1yr'}
    :param sort_key: one of {'Start', 'End', 'Change', 'Percent Change', 'Open Volume', 'Close Volume', 'Avg Volume'}
                        if None, a dict with the tickers as keys is returned instead of a list
    :param start_date: if of == 'custom' specify this values
    :param end_date: if of == 'custom' specify this value
    """
    of = of.lower()
    _today = datetime.today()
    todays_date = _today.date()
    if tickers is None: tickers = get_tickers(market)
    if _today.hour >= 16 and of == 'day':
        # key format will be
        with suppress(KeyError):
            return SORTED_INFO_CACHE[of][str(todays_date)][','.join(tickers)]
    if of == 'custom':
        assert start_date and end_date
        if _data is None: _data = get_data(tickers, start_date=start_date, end_date=end_date)
        start_date, end_date = _data.first_valid_index(), _data.last_valid_index()
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']): parsed_info[ticker] = info
    elif of in {'day', '1d'}:
        _data = get_data(tickers, period='5d', interval='1m')  # ALWAYS USE LATEST DATA
        market_day = _data.last_valid_index().date() == todays_date

        if False and (not market_day or (_today.hour * 60 + _today.minute >= 645)):  # >= 10:45 AM
            # movers of the latest market day
            recent_day = _data.last_valid_index()
            start_price_key = 'Open' if market_day else 'Close'
            parsed_info = {}
            for ticker in tickers:
                info = parse_info(_data, ticker, recent_day, recent_day, start_price_key=start_price_key)
                if not math.isnan(info['Start']): parsed_info[ticker] = info
        else:  # movers of the second last market day
            yest = _data.tail(2).first_valid_index()  # assuming interval = 1d
            parsed_info = {}
            for ticker in tickers:
                info = parse_info(_data, ticker, yest, yest)
                if not math.isnan(info['Start']): parsed_info[ticker] = info
    # TODO: custom day amount
    elif of in {'mtd', 'month_to_date', 'monthtodate'}:
        start_date = todays_date.replace(day=1)
        if _data is None: _data = get_data(tickers, start_date=start_date, end_date=_today)
        while start_date not in _data.index and start_date < todays_date:
            start_date += timedelta(days=1)
        if start_date >= todays_date: raise RuntimeError('No market days this month')
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, todays_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker] = info
    elif of in {'month', '1m', 'm'}:
        start_date = todays_date - timedelta(days=30)
        if _data is None: _data = get_data(tickers, start_date=start_date, end_date=_today)
        while start_date not in _data.index:
            start_date += timedelta(days=1)
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, todays_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker] = info
    # TODO: x months
    elif of in {'ytd', 'year_to_date', 'yeartodate'}:
        if _data is None:
            _data = get_data(tickers, start_date=_today.replace(day=1, month=1), end_date=_today)
            start_date = _data.first_valid_index()  # first market day of the year
        else:
            start_date = _today.replace(day=1, month=1).date()  # Jan 1st
            while start_date not in _data.index: start_date += timedelta(days=1)  # find first market day of the year
        end_date = _data.last_valid_index()
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']): parsed_info[ticker] = info
    elif of in {'year', '1yr', 'yr', 'y'}:
        if _data is None:
            _data = get_data(tickers, start_date=_today - timedelta(days=365), end_date=_today)
            start_date = _data.first_valid_index()  # first market day of the year
        else:
            start_date = _today.date() - timedelta(days=365)
            _data = get_data(tickers, start_date=_today.replace(day=1, month=1), end_date=_today)
        end_date = _data.last_valid_index()
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']): parsed_info[ticker] = info
    # TODO: x years
    else: parsed_info = {}  # invalid of
    if sort_key is None: return parsed_info
    sorted_info = sorted(parsed_info.items(), key=lambda item: item[1][sort_key])
    if _today.hour >= 16 and of == 'day':
        if of not in SORTED_INFO_CACHE: SORTED_INFO_CACHE[of] = {}
        if str(todays_date) not in SORTED_INFO_CACHE[of]: SORTED_INFO_CACHE[of][str(todays_date)] = {}
        SORTED_INFO_CACHE[of][str(todays_date)][','.join(tickers)] = sorted_info
    return sorted_info


def winners(sorted_info=None, tickers: list = None, market='ALL', of='day', start_date=None, end_date=None, show=5):
    # sorted_info is the return of get_parsed_data with non-None sort_key
    if sorted_info is None:
        sorted_info = get_parsed_data(tickers=tickers, market=market, of=of, start_date=start_date, end_date=end_date)
    return list(reversed(sorted_info[-show:]))


def losers(sorted_info=None, tickers: list = None, market='ALL', of='day', start_date=None, end_date=None, show=5):
    # sorted_info is the return of get_parsed_data with non-None sort_key
    if sorted_info is None:
        sorted_info = get_parsed_data(tickers=tickers, market=market, of=of, start_date=start_date, end_date=end_date)
    return sorted_info[:show]


# noinspection PyUnresolvedReferences,PyTypeChecker
def winners_and_losers(_data=None, tickers=None, market='ALL', of='day', start_date=None, end_date=None, show=5,
                       console_output=True, csv_output=''):
    sorted_info = get_parsed_data(_data, tickers, market, of=of, start_date=start_date, end_date=end_date)
    if console_output:
        bulls = ''
        bears = ''
        length = min(show, len(sorted_info))
        for i in range(length):
            better_stock = sorted_info[-i - 1]
            worse_stock = sorted_info[i]
            open_close1 = f'{round(better_stock[1]["Start"], 2)}, {round(better_stock[1]["End"], 2)}'
            open_close2 = f'{round(worse_stock[1]["Start"], 2)}, {round(worse_stock[1]["End"], 2)}'
            bulls += f'\n{better_stock[0]} [{open_close1}]: {round(better_stock[1]["Percent Change"] * 100, 2)}%'
            bears += f'\n{worse_stock[0]} [{open_close2}]: {round(worse_stock[1]["Percent Change"] * 100, 2)}%'
        header1 = f'TOP {length} WINNERS of ({of})'
        header2 = f'TOP {length} LOSERS ({of})'
        line = '-' * len(header1)
        print(f'{line}\n{header1}\n{line}{bulls}')
        line = '-' * len(header2)
        print(f'{line}\n{header2}\n{line}{bears}')
    if csv_output:
        with open(csv_output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['TICKER'] + list(sorted_info[0][1].keys()))
            for ticker in sorted_info:
                writer.writerow([ticker[0]] + list(ticker[1].values()))
    return sorted_info


def top_movers(_data=None, tickers=None, market='ALL', of='day', start_date=None, end_date=None, show=5,
               console_output=True, csv_output=''):
    return winners_and_losers(_data=_data, tickers=tickers, market=market, of=of, start_date=start_date,
                              end_date=end_date, show=show, console_output=console_output, csv_output=csv_output)



def price_to_earnings(ticker, return_dict: dict = None, return_price=False):
    # uses latest EPS (diluted)
    pe = -999999
    if ticker.endswith('.TO'):
        ticker = '.'.join(ticker.split('.')[:-1])
        url = f'https://www.marketwatch.com/investing/stock/{ticker}/financials?country=ca'
    else:
        url = f'https://www.marketwatch.com/investing/stock/{ticker}/financials'
    try:
        text_soup = BeautifulSoup(requests.get(url, headers=REQUEST_HEADERS).text, 'html.parser')
    except requests.TooManyRedirects:
        return pe
    try:
        price = float(text_soup.find('p', {'class': 'bgLast'}).text.replace(',', ''))
        titles = text_soup.findAll('td', {'class': 'rowTitle'})

        for title in titles:
            if 'EPS (Diluted)' in title.text:
                eps = [td.text for td in title.findNextSiblings(attrs={'class': 'valueCell'}) if td.text]
                try: latest_eps = float(eps[-1])
                except ValueError: latest_eps = -float(eps[-1][1:-1])
                pe = price / latest_eps
                break
    except AttributeError: price = -1
    if return_dict is not None: return_dict[ticker] = (pe, price) if return_price else pe
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


load_cache()  # IGNORE. This loads cache from investing_cache.json if the file exists