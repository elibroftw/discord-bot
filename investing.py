"""
Investing Quick Analytics
Author: Elijah Lopez
Version: 1.17
Created: April 3rd 2020
Updated: February 10th 2021
https://gist.github.com/elibroftw/2c374e9f58229d7cea1c14c6c4194d27

Resources:
Black-Scholes variables:
    https://aaronschlegel.me/black-scholes-formula-python.html#Dividend-Paying-Black-Scholes-Formula
Black-Scholes formulas:
    https://quantpie.co.uk/bsm_formula/bs_summary.php
Volatility (Standard Deviation) of a stock:
    https://tinytrader.io/how-to-calculate-historical-price-volatility-with-python/
"""

from contextlib import suppress
import csv
from datetime import datetime, timedelta
import multiprocessing
import math
from statistics import NormalDist
# noinspection PyUnresolvedReferences
from pprint import pprint
# 3rd party libraries
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import random
import pandas as pd
import requests
# import grequests
import yfinance as yf
from yahoo_fin import stock_info
from enum import IntEnum
import numpy as np
from functools import lru_cache, wraps
import time


def time_cache(max_age, maxsize=128, typed=False):
    """Least-recently-used cache decorator with time-based cache invalidation.

    Args:
        max_age: Time to live for cached results (in seconds).
        maxsize: Maximum cache size (see `functoolslru_cache`).
        typed: Cache on distinct input types (see `functools.lru_cache`).
    """

    def _decorator(fn):
        @lru_cache(maxsize=maxsize, typed=typed)
        def _new(*args, __time_salt, **kwargs):
            return fn(*args, **kwargs)

        @wraps(fn)
        def _wrapped(*args, **kwargs):
            return _new(*args, **kwargs, __time_salt=int(time.time() / max_age))

        return _wrapped

    return _decorator


NASDAQ_TICKERS_URL = 'https://api.nasdaq.com/api/screener/stocks?exchange=nasdaq&download=true'
NYSE_TICKERS_URL = 'https://api.nasdaq.com/api/screener/stocks?exchange=nyse&download=true'
AMEX_TICKERS_URL = 'https://api.nasdaq.com/api/screener/stocks?exchange=amex&download=true'
PREMARKET_FUTURES = 'https://ca.investing.com/indices/indices-futures'
SP500_URL = 'http://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
DOW_URL = 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
SORTED_INFO_CACHE = {}  # for when its past 4 PM
GENERIC_HEADERS = {
    'accept': 'text/html,application/xhtml+xml',
    'user-agent': 'Mozilla/5.0'
}
# NOTE: something for later https://www.alphavantage.co/


@time_cache(24 * 3600)  # cache request for a full day
def make_request(url, method='GET', headers=GENERIC_HEADERS, json=None):
    if method == 'GET':
        return requests.get(url, headers=headers)
    elif method == 'POST':
        return requests.post(url, json=json, headers=headers)
    else:
        raise ValueError(f'Invalid method {method}')


def get_dow_tickers() -> dict:
    resp = make_request(DOW_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'}).find('tbody')
    rows = table.find_all('tr')
    tickers = dict()
    for row in rows:
        with suppress(IndexError):
            ticker = row.find_all('td')[1].text.split(':')[-1].strip()
            name = row.find('th').text.strip()
            tickers[ticker] = {'symbol': ticker, 'name': name}
    return tickers


def get_sp500_tickers() -> dict:
    resp = make_request(SP500_URL)
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    tickers = {}
    for row in table.findAll('tr')[1:]:
        tds = row.findAll('td')
        ticker = tds[0].text.strip()
        if '.' not in ticker:
            name = tds[1].text.strip()
            tickers[ticker] = {'symbol': ticker, 'name': name}
    return tickers


def clean_stock_info(stock_info):
    stock_info['name'] = stock_info['name'].replace('Common Stock', '').strip()
    return stock_info


def get_nasdaq_tickers() -> dict:
    r = make_request(NASDAQ_TICKERS_URL).json()
    return {stock['symbol']: clean_stock_info(stock) for stock in r['data']['rows']}


def get_nyse_tickers() -> dict:
    r = make_request(NYSE_TICKERS_URL).json()
    return {stock['symbol']: clean_stock_info(stock) for stock in r['data']['rows']}


def get_amex_tickers() -> dict:
    r = make_request(AMEX_TICKERS_URL).json()
    return {stock['symbol']: clean_stock_info(stock) for stock in r['data']['rows']}


def get_tsx_tickers() -> dict:
    url = 'https://www.tsx.com/json/company-directory/search/tsx/.*'
    r = make_request(url).json()
    tickers = {}
    for stock in r['results']:
        ticker = stock['symbol'] + '.TO'
        name = stock['name'].replace('Common Stock', '').strip()
        tickers[ticker] = {'symbol': ticker, 'name': name}
    return tickers


def get_nyse_arca_tickers() -> dict:
    post_data = {'instrumentType': 'EXCHANGE_TRADED_FUND', 'pageNumber': 1, 'sortColumn': 'NORMALIZED_TICKER',
                 'sortOrder': 'ASC', 'maxResultsPerPage': 5000, 'filterToken': ''}
    r = requests.post('https://www.nyse.com/api/quotes/filter',
                      json=post_data).json()
    tickers = {}
    for stock in r:
        ticker = stock['symbolTicker']
        tickers[ticker] = {'symbol': ticker, 'name': stock['instrumentName']}
    return tickers


def get_tickers(market) -> dict:
    market = market.upper()
    # OPTIONS: CUSTOM, ALL, US, NYSE, NASDAQ, S&P500, DOW/DJIA, TSX/CA
    tickers = dict()
    # EXCHANGES
    if market in {'S&P500', 'S&P 500'}:
        tickers.update(get_sp500_tickers())
    if market in {'DOW', 'DJIA'}:
        tickers.update(get_dow_tickers())

    if market in {'NASDAQ', 'US', 'ALL'}:
        tickers.update(get_nasdaq_tickers())
    if market in {'NYSE', 'US', 'ALL'}:
        tickers.update(get_nyse_tickers())
    if market in {'AMEX', 'US', 'ALL'}:
        tickers.update(get_amex_tickers())
    if market in {'NYSEARCA', 'US', 'ALL'}:
        tickers.update(get_nyse_arca_tickers())
    if market in {'TSX', 'CA', 'ALL'}:
        tickers.update(get_tsx_tickers())
    # elif market in {'MORTGAGE REITS', 'MREITS'}:
    #     tickers_to_download = {'NLY', 'STWD', 'AGNC', 'TWO', 'PMT', 'MITT', 'NYMT', 'MFA',
    #                            'IVR', 'NRZ', 'TRTX', 'RWT', 'DX', 'XAN', 'WMC'}
    # elif market == 'OIL': tickers_to_download = {'DNR', 'PVAC', 'ROYT', 'SWN', 'CPE', 'CEQP', 'PAA', 'PUMP', 'PBF'}
    # elif market in {'AUTO', 'AUTOMOBILE', 'CARS'}:
    #     tickers_to_download={'TSLA', 'GM', 'F', 'NIO', 'RACE', 'FCAU', 'HMC', 'NIO', 'TTM', 'TM'}
    # elif market in {'INDEXFUTURES', 'INDEX_FUTURES'}: tickers_to_download = {'YM=F', 'NQ=F', 'RTY=F', 'ES=F'}
    # elif market == 'TANKERS':
    #     tickers_to_download = {'EURN', 'TNK', 'TK', 'TNP', 'DSX', 'NAT',
    #         'STNG', 'SFL', 'DHT', 'CPLP', 'DSSI', 'FRO', 'INSW', 'NNA', 'SBNA'}
    # elif market in {'UTILS', 'UTILITIES'}:
    #     tickers_to_download = {'PCG', 'ELLO', 'AT', 'ELP', 'ES', 'EDN', 'IDA', 'HNP', 'GPJA', 'NEP', 'SO', 'CEPU', 'AES', 'ETR', 'KEP', 'OGE', 'EIX', 'NEE', 'TVC', 'TAC', 'EE', 'CIG', 'PNW', 'EMP', 'EBR.B', 'CPL', 'DTE', 'POR', 'EAI',
    #         'NRG', 'CWEN', 'KEN', 'AGR', 'BEP', 'ORA', 'EAE', 'PPX', 'AZRE', 'ENIC', 'FE', 'CVA', 'BKH', 'ELJ', 'EZT', 'HE', 'VST', 'ELU', 'ELC', 'TVE', 'AQN', 'PAM', 'AEP', 'ENIA', 'EAB', 'PPL', 'CNP', 'D', 'PNM', 'EBR', 'FTS'}
    # elif market == 'CUSTOM': pass
    return tickers


def get_company_name_from_ticker(ticker: str):
    ticker = ticker.upper()
    with suppress(KeyError):
        return ALL_STOCKS[ticker]['name']
    if ticker.count('.TO'):
        try:
            return get_tsx_tickers()[ticker]['name']
        except KeyError:
            ticker = ticker.replace('.TO', '')
            r = requests.get(
                f'https://www.tsx.com/json/company-directory/search/tsx/{ticker}')
            results = {}
            for s in r.json()['results']:
                s['name'] = s['name'].upper()
                results[s['symbol']] = s
            best_match = process.extractOne(ticker, list(results.keys()))[0]
            return results[best_match]['name']
    raise ValueError('Something went wrong')


@time_cache(30)  # cache for 30 seconds
def get_ticker_info(ticker: str, round_values=True) -> dict:
    '''
    Throws ValueError
    '''
    ticker = ticker.upper()
    yf_ticker = yf.Ticker(ticker)
    try:
        info = yf_ticker.info
    except (KeyError, ValueError):
        raise ValueError(f'Invalid ticker "{ticker}"')
    data_latest = yf_ticker.history(period='5d', interval='1m', prepost=True)
    timestamp = data_latest.last_valid_index()
    latest_price = float(data_latest.tail(1)['Close'].iloc[0])
    # get previous closing price
    # TODO: test in different time zones
    timestamp_ending = str(timestamp)[-6:]
    if (timestamp.hour >= 16):  # post market
        today = datetime(timestamp.year, timestamp.month, timestamp.day, 15, 59)
        _closing_timestamp = today.strftime(f'%Y-%m-%d %H:%M:%S{timestamp_ending}')
        closing_price = data_latest.loc[_closing_timestamp]['Close']
    else:  # market is currently open / pre-market
        prev_day = datetime(timestamp.year, timestamp.month,
                            timestamp.day, 15, 59) - timedelta(days=1)
        while True:
            try:
                prev_day_timestamp = prev_day.strftime(f'%Y-%m-%d %H:%M:%S{timestamp_ending}')
                closing_price = data_latest.loc[prev_day_timestamp]['Close']
                break
            except KeyError:
                prev_day -= timedelta(days=1)
    change = latest_price - closing_price
    if round_values:
        change = round(change, 4)
        percent_change = round(change/closing_price * 100, 2)
        latest_price = round(latest_price, 4)
        closing_price = round(closing_price, 4)
    else:
        percent_change = change/closing_price * 100
    name = info['longName']
    dividend_yield = info['trailingAnnualDividendYield']
    eps_ttm = info['trailingEps']
    return_info = {'name': name,
                   'price': latest_price,
                   'last_close_price': closing_price,
                   'dividend_yield': dividend_yield,
                   'change': change, 'percent_change': percent_change,
                   'timestamp': timestamp, 'symbol': ticker,
                   'eps_ttm': eps_ttm,
                   'volume': info['volume'],
                   'last_dividend': info['lastDividendValue']}
    return return_info


def get_data(tickers: set, start_date=None, end_date=None, period='3mo', group_by='ticker', interval='1d',
             show_progress=True):
    # http://www.datasciencemadesimple.com/union-and-union-all-in-pandas-dataframe-in-python-2/
    # new format
    _key = ' '.join(tickers) + f' {start_date} {end_date} {period} {group_by}'
    _data = yf.download(tickers, start_date, end_date, period=period, group_by=group_by, threads=3,
                        progress=show_progress, interval=interval)
    return _data


def parse_info(_data, ticker, start_date, end_date, start_price_key='Open'):
    """
    start_price_key: can be 'Open' or 'Close'
    TODO: change parse_info keys to snake_case
    """
    start_price = _data[ticker][start_price_key][start_date]
    if math.isnan(_data[ticker]['Open'][end_date]):
        end_date = _data[ticker]['Open'].last_valid_index()
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
    if tickers is None:
        tickers = list(get_tickers(market).keys())
    if _today.hour >= 16 and of == 'day':
        # TODO: cache pre-market as well
        # key format will be
        with suppress(KeyError):
            return SORTED_INFO_CACHE[of][str(todays_date)][','.join(tickers)]
    if of == 'custom':
        assert start_date and end_date
        if _data is None:
            _data = get_data(tickers, start_date=start_date, end_date=end_date)
        start_date, end_date = _data.first_valid_index(), _data.last_valid_index()
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker] = info
    elif of in {'day', '1d'}:
        # ALWAYS USE LATEST DATA
        _data = get_data(tickers, period='5d', interval='1m')
        market_day = _data.last_valid_index().date() == todays_date
        if not market_day or (_today.hour * 60 + _today.minute >= 645):  # >= 10:45 AM
            # movers of the latest market day [TODAY]
            recent_day = _data.last_valid_index()
            recent_start_day = recent_day.replace(hour=9, minute=30, second=0)
            parsed_info = {}
            for ticker in tickers:
                try:
                    info = parse_info(_data, ticker, recent_start_day, recent_day)
                    if not math.isnan(info['Start']):
                        parsed_info[ticker] = info
                except ValueError:
                    # TODO: fix
                    print('ERROR: Could not get info for', ticker)
        else:  # movers of the second last market day
            yest = _data.tail(2).first_valid_index()  # assuming interval = 1d
            parsed_info = {}
            for ticker in tickers:
                info = parse_info(_data, ticker, yest, yest)
                if not math.isnan(info['Start']):
                    parsed_info[ticker] = info
    # TODO: custom day amount
    elif of in {'mtd', 'month_to_date', 'monthtodate'}:
        start_date = todays_date.replace(day=1)
        if _data is None:
            _data = get_data(tickers, start_date=start_date, end_date=_today)
        while start_date not in _data.index and start_date < todays_date:
            start_date += timedelta(days=1)
        if start_date >= todays_date:
            raise RuntimeError(
                'No market days this month')
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, todays_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker] = info
    elif of in {'month', '1m', 'm'}:
        start_date = todays_date - timedelta(days=30)
        if _data is None:
            _data = get_data(
                tickers, start_date=start_date, end_date=_today)
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
            _temp = _today.replace(day=1, month=1)
            _data = get_data(tickers, start_date=_temp, end_date=_today)
            start_date = _data.first_valid_index()  # first market day of the year
        else:
            start_date = _today.replace(day=1, month=1).date()  # Jan 1st
            # find first market day of the year
            while start_date not in _data.index:
                start_date += timedelta(days=1)
        end_date = _data.last_valid_index()
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker] = info
    elif of in {'year', '1yr', 'yr', 'y'}:
        if _data is None:
            _data = get_data(tickers, start_date=_today -
                             timedelta(days=365), end_date=_today)
            start_date = _data.first_valid_index()  # first market day of the year
        else:
            start_date = _today.date() - timedelta(days=365)
            _data = get_data(tickers, start_date=_today.replace(
                day=1, month=1), end_date=_today)
        end_date = _data.last_valid_index()
        parsed_info = {}
        for ticker in tickers:
            info = parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker] = info
    # TODO: x years
    else:
        parsed_info = {}  # invalid of
    if sort_key is None:
        return parsed_info
    sorted_info = sorted(parsed_info.items(),
                         key=lambda item: item[1][sort_key])
    if _today.hour >= 16 and of == 'day':
        if of not in SORTED_INFO_CACHE:
            SORTED_INFO_CACHE[of] = {}
        if str(todays_date) not in SORTED_INFO_CACHE[of]:
            SORTED_INFO_CACHE[of][str(todays_date)] = {}
        SORTED_INFO_CACHE[of][str(todays_date)][','.join(tickers)] = sorted_info
    return sorted_info


@time_cache(60)  # cache for 1 minute
def winners(sorted_info=None, tickers: list = None, market='ALL', of='day', start_date=None, end_date=None, show=5):
    # sorted_info is the return of get_parsed_data with non-None sort_key
    if sorted_info is None:
        sorted_info = get_parsed_data(
            tickers=tickers, market=market, of=of, start_date=start_date, end_date=end_date)
    return list(reversed(sorted_info[-show:]))


@time_cache(60)  # cache for 1 minute
def losers(sorted_info=None, tickers: list = None, market='ALL', of='day', start_date=None, end_date=None, show=5):
    # sorted_info is the return of get_parsed_data with non-None sort_key
    if sorted_info is None:
        sorted_info = get_parsed_data(
            tickers=tickers, market=market, of=of, start_date=start_date, end_date=end_date)
    return sorted_info[:show]


@time_cache(60)  # cache for 1 minute
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


@time_cache(60)  # cache for 1 minute
def top_movers(_data=None, tickers=None, market='ALL', of='day', start_date=None, end_date=None, show=5,
               console_output=True, csv_output=''):
    return winners_and_losers(_data=_data, tickers=tickers, market=market, of=of, start_date=start_date,
                              end_date=end_date, show=show, console_output=console_output, csv_output=csv_output)


def create_headers(subdomain):
    hdrs = {'authority': 'finance.yahoo.com',
            'method': 'GET',
            'path': subdomain,
            'scheme': 'https',
            'accept': 'text/html,application/xhtml+xml',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'cookie': 'cookies',
            'dnt': '1',
            'pragma': 'no-cache',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0'}
    return hdrs


@time_cache(3600)  # cache for 1 hour
def get_latest_dividend(ticker: str) -> float:
    url = f'https://finance.yahoo.com/quote/{ticker}/history'
    hdr = create_headers(f'{ticker}/history')
    soup = BeautifulSoup(requests.get(url, headers=hdr).text, 'html.parser')
    soup = soup.find('tbody')
    dividend = soup.find('strong').text
    return float(dividend)


@time_cache(3600)  # cache for 1 hour
def get_target_price(ticker):
    """
    ticker: yahoo finance ticker
    returns: {'avg': float, 'low': float, 'high': float, 'price': float, 'eps_ttm': float}
    """
    try:
        ticker = ticker.upper()
        quarterly_eps = stock_info.get_earnings(ticker)['quarterly_results']['actual'][-4:]
        quote_table = stock_info.get_quote_table(ticker)
        eps_estimates = stock_info.get_analysts_info(ticker)[
            'Earnings Estimate']
        price = quote_table['Quote Price']
        eps_ttm = sum(quarterly_eps)
        # if EPS data DNE for 4 quarters, annualize out of the current ones
        if len(quarterly_eps) < 4:
            eps_ttm = quarterly_eps / len(quarterly_eps) * 4
        iloc_levels = {1: 'avg', 2: 'low', 3: 'high'}
        target_prices = {
            'price': round(price, 2),
            'eps_ttm': round(eps_ttm, 2)
        }
        for iloc_level, level in iloc_levels.items():
            forward_eps = eps_estimates.iloc[iloc_level, -1]  # next year eps
            target_price = price * forward_eps / eps_ttm
            target_prices[level] = round(target_price, 2)
        return target_prices
    except KeyError:
        raise ValueError(f'Invalid ticker "{ticker}"')


def tickers_by_pe(tickers, output_to_csv='', console_output=True):
    """
    Returns the tickers by price-earnings ratio (remove negatives)
    :param tickers: iterable
    :param output_to_csv:
    :param console_output:
    :return:
    """
    # TODO: use grequests
    for ticker in tickers:
        with suppress(ValueError):
            pe = price_to_earnings(ticker)
            if pe > 0:
                pes.append((ticker, pe))
    pes.sort(key=lambda item: item[1])
    if console_output:
        header = 'TOP 5 TICKERS BY P/E'
        line = '-' * len(header)
        print(f'{header}\n{line}')
        for i, (ticker, pe) in enumerate(pes):
            if i == 5:
                break
            print(f'{ticker}: {round(pe, 2)}')
    if output_to_csv:
        with open(output_to_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['TICKER', 'Price-earnings'])
            for ticker in pes:
                writer.writerow(ticker)
    return pes


def price_to_earnings(ticker):
    '''
    EPS: earnings per share
    PER: price over earnings ratio
    useful concept to keep in mind:
    PER = Stock price / EPS
    Stock price = PER * EPS
    raises: ValueError
    '''
    url = 'http://finviz.com/quote.ashx?t=' + ticker.upper()
    soup = BeautifulSoup(make_request(url).content, 'html.parser')
    return float(soup.find(text = 'P/E').find_next(class_='snapshot-td2').text)



def sort_by_volume(tickers):
    pass


def get_index_futures():
    resp = make_request(PREMARKET_FUTURES)
    soup = BeautifulSoup(resp.text, 'html.parser')
    quotes = soup.find('tbody').findAll('tr')
    return_obj = {}
    for quote in quotes:
        index_name = quote.find('a').text.upper()
        nums = quote.findAll('td')[3:]
        price = nums[0].text
        change = nums[3].text
        percent_change = nums[4].text
        return_obj[index_name] = {'name': index_name, 'price': price,
                                  'change': change, 'percent_change': percent_change}
    return return_obj


def get_random_stocks(n=1) -> set:
    # return n stocks from NASDAQ and NYSE
    if n < 1:
        n = 1
    us_stocks = get_nasdaq_tickers()
    us_stocks.update(get_nyse_tickers())
    return_stocks = set()
    while len(return_stocks) < n:
        stock = random.sample(list(us_stocks.keys()), 1)[0]
        if not stock.count('.') and not stock.count('^'):
            return_stocks.add(stock)
    return return_stocks


# Options Section

# Enums are used for some calculations
class Option(IntEnum):
    CALL = 1
    PUT = -1


def get_month_and_year():
    date = datetime.today()
    month = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUNE',
             'JULY', 'AUG', 'SEP', 'DEC'][date.month - 1]
    year = date.year
    return f'{month} {year}'


@lru_cache(100)
def get_risk_free_interest_rate(month_and_year=None):
    """
    e.g. month_and_year = 'FEB 2021'
    returns the risk free interest rate:
        the average interest rate of US Treasury Bills
    throws: RunTimeError if interest rate could not be fetched
    """
    del month_and_year
    us_treasury_api = 'https://api.fiscaldata.treasury.gov/services/api/fiscal_service'
    endpoint = f'{us_treasury_api}/v2/accounting/od/avg_interest_rates'
    link = f'{endpoint}?page[size]=10000'
    r = requests.get(link).json()
    last_count = r['meta']['total-count']
    i = last_count - 2
    for i in range(last_count - 1, 0, -1):
        node = r['data'][i]
        if node['security_desc'] == 'Treasury Bills':
            return float(node['avg_interest_rate_amt']) / 100
    raise RuntimeError('Could not get risk free interest rate')


@lru_cache(10000)
def get_volatility(stock_ticker, tll_hash=None):
    """
    ttl_hash = time.time() / (3600 * 24)
    Returns the (annualized) daily standard deviation return of the stock
        for the last 365 days
    """
    del tll_hash
    end = datetime.today()
    start = end - timedelta(days=365)
    data = yf.download(stock_ticker, start=start, end=end, progress=False)
    data['Returns'] = np.log(data['Close'] / data['Close'].shift(-1))
    # annualize daily standard deviation
    return np.std(data['Returns']) * math.sqrt(252)


def d1(market_price, strike_price, days_to_expiry, volatility, risk_free, dividend_yield):
    block_3 = volatility * math.sqrt(days_to_expiry)
    block_1 = math.log(market_price / strike_price)
    block_2 = days_to_expiry * \
        (risk_free - dividend_yield + volatility ** 2 / 2)
    return (block_1 + block_2) / block_3


def csn(y):
    """
    returns the Cumulative Standard Normal of y
        which is the cumulative distribution function of y with
        mean = 0 and standard deviation = 1
    """
    return NormalDist().cdf(y)


def snd(y):
    """
    returns the Standard Normal Density of y
        which is the probability density function of y with
        mean = 0 and standard deviation = 1
    """
    return NormalDist().pdf(y)


def calc_option_price(market_price, strike_price, days_to_expiry, volatility,
                      risk_free=get_risk_free_interest_rate(), dividend_yield=0, option_type=Option.CALL):
    _d1 = option_type * d1(market_price, strike_price,
                           days_to_expiry, volatility, risk_free, dividend_yield)
    _d2 = _d1 - option_type * volatility * math.sqrt(days_to_expiry)
    block_1 = market_price * \
        math.e ** (-dividend_yield * days_to_expiry) * csn(_d1)
    block_2 = strike_price * math.e ** (-risk_free * days_to_expiry) * csn(_d2)
    return option_type * (block_1 - block_2)


def calc_option_delta(market_price, strike_price, days_to_expiry, volatility,
                      risk_free=get_risk_free_interest_rate(), dividend_yield=0, option_type=Option.CALL):
    block_1 = math.e ** (-dividend_yield * days_to_expiry)
    _d1 = d1(market_price, strike_price, days_to_expiry,
             volatility, risk_free, dividend_yield)
    return option_type * block_1 * csn(option_type * _d1)


def calc_option_gamma(market_price, strike_price, days_to_expiry, volatility,
                      risk_free=get_risk_free_interest_rate(), dividend_yield=0):
    block_1 = math.e ** (-dividend_yield * days_to_expiry)
    _d1 = d1(market_price, strike_price, days_to_expiry,
             volatility, risk_free, dividend_yield)
    return block_1 / (market_price * volatility * math.sqrt(days_to_expiry)) * snd(_d1)


def calc_option_vega(market_price, strike_price, days_to_expiry, volatility,
                     risk_free=get_risk_free_interest_rate(), dividend_yield=0):
    block_1 = market_price * math.e ** (-dividend_yield * days_to_expiry)
    _d1 = d1(market_price, strike_price, days_to_expiry,
             volatility, risk_free, dividend_yield)
    return block_1 * math.sqrt(days_to_expiry) * snd(_d1)


def calc_option_rho(market_price, strike_price, days_to_expiry, volatility,
                    risk_free=get_risk_free_interest_rate(), dividend_yield=0, option_type=Option.CALL):
    block_1 = strike_price * \
        math.e ** (-risk_free * days_to_expiry) * days_to_expiry
    _d1 = d1(market_price, strike_price, days_to_expiry,
             volatility, risk_free, dividend_yield)
    _d2 = option_type * (_d1 - volatility * math.sqrt(days_to_expiry))
    return option_type * block_1 * csn(_d2)


def calc_option_theta(market_price, strike_price, days_to_expiry, volatility,
                      risk_free=get_risk_free_interest_rate(), dividend_yield=0, option_type=Option.CALL):
    _d1 = d1(market_price, strike_price, days_to_expiry,
             volatility, risk_free, dividend_yield)
    block_1 = market_price * \
        math.e ** (-dividend_yield * days_to_expiry) * csn(option_type * _d1)
    block_2 = strike_price * \
        math.e ** (-risk_free * days_to_expiry) * risk_free
    blocK_3 = market_price * math.e ** (-dividend_yield * days_to_expiry)
    blocK_3 *= volatility / (2 * math.sqrt(days_to_expiry)) * snd(_d1)
    return option_type * (block_1 - block_2) - blocK_3


def run_tests():
    print('Getting DOW')
    assert get_dow_tickers()['AAPL']['name'] == 'Apple Inc.'
    print('Getting S&P500')
    assert get_sp500_tickers()['TSLA']['name'] == 'Tesla, Inc.'
    print('Getting NASDAQ')
    assert get_nasdaq_tickers()['AMD']['name'] == 'Advanced Micro Devices Inc.'
    print('Getting AMEX')
    get_amex_tickers()
    print('Getting NYSE')
    assert get_nyse_tickers()['V']['name'] == 'Visa Inc.'
    print('Getting NYSE ARCA')
    assert get_nyse_arca_tickers()['SPY']['name'] == 'SPDR S&P 500 ETF TRUST'
    print('Getting TSX')
    assert 'SHOP.TO' in get_tsx_tickers()
    print('Getting FUTURES')
    get_index_futures()
    print('Testing get company name')
    assert get_company_name_from_ticker('NVDA') == 'NVIDIA Corporation'
    pprint(get_random_stocks(10))
    pprint(get_ticker_info('AMD'))
    get_target_price('DOC')
    sample_target_prices = get_target_price('DOC')
    assert len(sample_target_prices) == 5
    assert isinstance(sample_target_prices, dict)
    assert 0 < get_risk_free_interest_rate(0) < 1
    # test invalid ticker
    print('Testing Invalid Tickers')
    with suppress(ValueError):
        get_target_price('ZWC')
    with suppress(ValueError):
        get_ticker_info('ZWC')
    print('Testing tickers by pe')
    tickers_by_pe(get_dow_tickers())
    print('Testing top movers')
    top_movers(market='DOW')


ALL_STOCKS = get_tickers('ALL')
if __name__ == '__main__':
    run_tests()
