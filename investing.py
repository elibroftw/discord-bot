"""
Investing Quick Analytics
Author: Elijah Lopez
Version: 1.12
Source: https://gist.github.com/elibroftw/2c374e9f58229d7cea1c14c6c4194d27
"""

from contextlib import suppress
import csv
from datetime import datetime, timedelta
import io
import json
import math
from threading import main_thread
from numpy.lib.function_base import average
import pandas
from yahoo_fin import stock_info
# noinspection PyUnresolvedReferences
from pprint import pprint
# 3rd party libraries
from bs4 import BeautifulSoup
from fuzzywuzzy import process
import pandas as pd
import requests
import yfinance as yf

import functools
import time
import random


def time_cache(max_age, maxsize=128, typed=False):
    """Least-recently-used cache decorator with time-based cache invalidation.

    Args:
        max_age: Time to live for cached results (in seconds).
        maxsize: Maximum cache size (see `functools.lru_cache`).
        typed: Cache on distinct input types (see `functools.lru_cache`).
    """

    def _decorator(fn):
        @functools.lru_cache(maxsize=maxsize, typed=typed)
        def _new(*args, __time_salt, **kwargs):
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        def _wrapped(*args, **kwargs):
            return _new(*args, **kwargs, __time_salt=int(time.time() / max_age))

        return _wrapped

    return _decorator


NASDAQ_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download'
NYSE_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download'
AMEX_TICKERS_URL = 'https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download'
PREMARKET_FUTURES = 'https://ca.investing.com/indices/indices-futures'
US_COMPANY_LIST = []
SORTED_INFO_CACHE = {}  # for when its past 4 PM
GENERIC_HEADERS = {
    'accept': 'text/html,application/xhtml+xml',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
}
# NOTE: something for later https://www.alphavantage.co/


@time_cache(24 * 3600)  # cache for a full day
def get_dow_tickers():
    resp = requests.get('https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average')
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'}).find('tbody')
    rows = table.find_all('tr')
    _dow_tickers = set()
    for row in rows:
        with suppress(IndexError):
            ticker = row.find_all('td')[2].text.split(':')[-1].strip()
            _dow_tickers.add(ticker)
    return _dow_tickers


@time_cache(24 * 3600)  # cache for a full day
def get_sp500_tickers():
    resp = requests.get(
        'http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    soup = BeautifulSoup(resp.text, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    _sp500_tickers = {row.find('td').text.strip()
                               for row in table.findAll('tr')[1:]}
    return _sp500_tickers


@time_cache(24 * 3600)  # cache for a full day
def get_nasdaq_tickers():
    return tickers_from_csv(NASDAQ_TICKERS_URL, name='NASDAQ')


@time_cache(24 * 3600)  # cache for a full day
def get_nyse_tickers():
    return tickers_from_csv(NYSE_TICKERS_URL, name='NYSE')


@time_cache(24 * 3600)  # cache for a full day
def get_amex_tickers():
    return tickers_from_csv(AMEX_TICKERS_URL, name='AMEX')


@time_cache(24 * 3600)  # cache for a full day
def get_tsx_tickers():
    base_url = 'http://eoddata.com/stocklist/TSX/'
    _tsx_tickers = []
    for i in range(26):
        resp = requests.get(base_url + chr(65 + i) + '.html')
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', {'class': 'quotes'})
        _tsx_tickers += {row.find('a').text.strip().upper() +
                                  '.TO' for row in table.findAll('tr')[1:]}
    return _tsx_tickers


@time_cache(24 * 3600)  # cache for a full day
def get_nyse_arca_tickers():
    post_data = {'instrumentType': 'EXCHANGE_TRADED_FUND', 'pageNumber': 1, 'sortColumn': 'NORMALIZED_TICKER',
                 'sortOrder': 'ASC', 'maxResultsPerPage': 5000, 'filterToken': ''}
    r = requests.post('https://www.nyse.com/api/quotes/filter', json=post_data)
    _arca_tickers = {item['normalizedTicker'] for item in r.json()}
    return _arca_tickers


@time_cache(24 * 3600)  # cache for a full day
def tickers_from_csv(url, name=''):
    s = requests.get(url).content
    _tickers = set(pd.read_csv(io.StringIO(s.decode('utf-8')))['Symbol'])
    return _tickers


@time_cache(24 * 3600)  # cache for a full day
def get_tickers(market):
    # TODO: add ETFs to the markets
    market = market.upper()
    # OPTIONS: CUSTOM, ALL, US, NYSE, NASDAQ, S&P500, DOW/DJIA, TSX/CA, Mortgage REITs
    tickers_to_download = set()
    if market in {'S&P500', 'S&P 500'}: tickers_to_download = tickers_to_download.union(get_sp500_tickers())
    if market in {'DOW', 'DJIA'}: tickers_to_download = tickers_to_download.union(get_dow_tickers())
    if market in {'NASDAQ', 'US', 'ALL'}:
        tickers_to_download = tickers_to_download.union(get_nasdaq_tickers())
    if market in {'NYSE', 'US', 'ALL'}:
        tickers_to_download=tickers_to_download.union(get_nyse_tickers())
    if market in {'AMEX', 'US', 'ALL'}:
        tickers_to_download=tickers_to_download.union(get_amex_tickers())
    if market in {'NYSEARCA', 'US', 'ALL'}:
        tickers_to_download=tickers_to_download.union(get_nyse_arca_tickers())
    if market in {'TSX', 'CA', 'ALL'}: tickers_to_download=tickers_to_download.union(get_tsx_tickers())
    elif market == 'Mortgage REITs':
        tickers_to_download={'NLY', 'STWD', 'AGNC', 'TWO', 'PMT', 'MITT', 'NYMT', 'MFA',
                               'IVR', 'NRZ', 'TRTX', 'RWT', 'DX', 'XAN', 'WMC'}
    elif market == 'OIL': tickers_to_download={'DNR', 'PVAC', 'ROYT', 'SWN', 'CPE', 'CEQP', 'PAA', 'PUMP', 'PBF'}
    elif market in {'AUTO', 'AUTOMOBILE', 'CARS'}:
        tickers_to_download={'TSLA', 'GM', 'F',
            'RACE', 'FCAU', 'HMC', 'NIO', 'TTM', 'TM'}
    elif market in {'INDEXFUTURES', 'INDEX_FUTURES'}: tickers_to_download={'YM=F', 'NQ=F', 'RTY=F', 'ES=F'}
    elif market == 'TANKERS':
        tickers_to_download={'EURN', 'TNK', 'TK', 'TNP', 'DSX', 'NAT',
            'STNG', 'SFL', 'DHT', 'CPLP', 'DSSI', 'FRO', 'INSW', 'NNA', 'SBNA'}
    elif market in {'UTILS', 'UTILITIES'}:
        tickers_to_download={'PCG', 'ELLO', 'AT', 'ELP', 'ES', 'EDN', 'IDA', 'HNP', 'GPJA', 'NEP', 'SO', 'CEPU', 'AES', 'ETR', 'KEP', 'OGE', 'EIX', 'NEE', 'TVC', 'TAC', 'EE', 'CIG', 'PNW', 'EMP', 'EBR.B', 'CPL', 'DTE', 'POR', 'EAI',
            'NRG', 'CWEN', 'KEN', 'AGR', 'BEP', 'ORA', 'EAE', 'PPX', 'AZRE', 'ENIC', 'FE', 'CVA', 'BKH', 'ELJ', 'EZT', 'HE', 'VST', 'ELU', 'ELC', 'TVE', 'AQN', 'PAM', 'AEP', 'ENIA', 'EAB', 'PPL', 'CNP', 'D', 'PNM', 'EBR', 'FTS'}
    elif market == 'CUSTOM': pass
    # TODO: add more sectors
    return tickers_to_download


@time_cache(24 * 3600)  # cache for a full day
def get_company_name_from_ticker(ticker: str):
    global US_COMPANY_LIST
    if ticker.count('.TO'):
        ticker=ticker.replace('.TO', '')
        r=requests.get(f'https://www.tsx.com/json/company-directory/search/tsx/{ticker}')
        results={}
        for s in r.json()['results']:
            s['name']=s['name'].upper()
            results[s['symbol']]=s
        best_match=process.extractOne(ticker, list(results.keys()))[0]
        return results[best_match]['name']
    else:
        if not US_COMPANY_LIST:
            r = requests.get('https://api.iextrading.com/1.0/ref-data/symbols')
            US_COMPANY_LIST={s['symbol']: s for s in r.json()}
        best_match=process.extractOne(ticker, list(US_COMPANY_LIST.keys()))[0]
        # noinspection PyTypeChecker
        return US_COMPANY_LIST[best_match]['name']


@time_cache(30)  # cache for 30 seconds
def get_ticker_info(ticker: str, round_values=True) -> dict:
    # TODO: test pre-market values
    data_latest=yf.download(ticker, interval='1m', period='1d', threads=3, prepost=True, progress=False,
                              group_by='ticker')
    data_last_close=yf.download(ticker, interval='1m', period='5d', threads=3, progress=False)['Close']
    latest_price=float(data_latest.tail(1)['Close'])
    closing_price=float(data_last_close.tail(1))
    timestamp=data_latest.last_valid_index()
    if closing_price == latest_price:
        _today=datetime.today()
        _today=datetime(_today.year, _today.month, _today.day, 15, 59)
        _today -= timedelta(days=1)
        while _today.strftime('%Y-%m-%d %H:%M:%S-04:00') not in data_last_close:
            _today -= timedelta(days=1)
        closing_price=data_last_close[_today.strftime('%Y-%m-%d %H:%M:%S-04:00')]
        # as_of = f'Market Open: {timestamp["Datetime"]}'
    # else:
        # as_of = f'After hours: {timestamp["Datetime"]}'
    change=latest_price - closing_price
    if round_values:
        change=round(change, 4)
        percent_change=round(change/closing_price * 100, 2)
        latest_price=round(latest_price, 4)
        closing_price=round(closing_price, 4)
    else: percent_change=change/closing_price * 100
    name=get_company_name_from_ticker(ticker)
    try:
        dividend=get_latest_dividend(ticker)
        pd_ratio=round(latest_price/dividend, 2)
    except Exception as e:
        dividend=0
        pd_ratio=10 ** 10  # basically infinity

    info={'name': name, 'price': latest_price, 'last_close_price': closing_price, 'price:dividend': pd_ratio,
            'change': change, 'percent_change': percent_change, 'timestamp': timestamp, 'symbol': ticker, 'last_dividend': dividend}
    return info


def get_data(tickers: set, start_date=None, end_date=None, period='3mo', group_by='ticker', interval='1d',
             show_progress=True):
    # http://www.datasciencemadesimple.com/union-and-union-all-in-pandas-dataframe-in-python-2/
    # new format
    _key=' '.join(tickers) + f' {start_date} {end_date} {period} {group_by}'
    _data=yf.download(tickers, start_date, end_date, period=period, group_by=group_by, threads=3,
                        progress=show_progress, interval=interval)
    return _data


def parse_info(_data, ticker, start_date, end_date, start_price_key='Open'):
    """
    start_price_key: can be 'Open' or 'Close'
    TODO: change parse_info keys to snake_case
    """
    start_price=_data[ticker][start_price_key][start_date]
    if math.isnan(_data[ticker]['Open'][end_date]):
        end_date=_data[ticker]['Open'].last_valid_index()
    end_price=_data[ticker]['Close'][end_date]
    change=end_price - start_price
    percent_change=change / start_price
    start_volume=round(_data[ticker]['Volume'][start_date])
    end_volume=round(_data[ticker]['Volume'][end_date])
    avg_volume=(start_volume + end_volume) / 2
    return {'Start': start_price, 'End': end_price, 'Change': change, 'Percent Change': percent_change,
            'Open Volume': start_volume, 'Close Volume': end_volume, 'Avg Volume': avg_volume}


def get_parsed_data(_data=None, tickers: list=None, market='ALL', sort_key='Percent Change',
                    of='day', start_date: datetime=None, end_date: datetime=None):
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
    of=of.lower()
    _today=datetime.today()
    todays_date=_today.date()
    if tickers is None: tickers=get_tickers(market)
    if _today.hour >= 16 and of == 'day':
        # TODO: cache pre-market as well
        # key format will be
        with suppress(KeyError):
            return SORTED_INFO_CACHE[of][str(todays_date)][','.join(tickers)]
    if of == 'custom':
        assert start_date and end_date
        if _data is None: _data=get_data(
            tickers, start_date=start_date, end_date=end_date)
        start_date, end_date=_data.first_valid_index(), _data.last_valid_index()
        parsed_info={}
        for ticker in tickers:
            info=parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']): parsed_info[ticker]=info
    elif of in {'day', '1d'}:
        # ALWAYS USE LATEST DATA
        _data=get_data(tickers, period='5d', interval='1m')
        market_day=_data.last_valid_index().date() == todays_date
        if not market_day or (_today.hour * 60 + _today.minute >= 645):  # >= 10:45 AM
            # movers of the latest market day [TODAY]
            recent_day=_data.last_valid_index()
            recent_start_day=recent_day.replace(hour=9, minute=30, second=0)
            parsed_info={}
            for ticker in tickers:
                try:
                    info=parse_info(
                        _data, ticker, recent_start_day, recent_day)
                    if not math.isnan(info['Start']): parsed_info[ticker]=info
                except ValueError:
                    # TODO: fix
                    print('ERROR: Could not get info for', ticker)
        else:  # movers of the second last market day
            yest=_data.tail(2).first_valid_index()  # assuming interval = 1d
            parsed_info={}
            for ticker in tickers:
                info=parse_info(_data, ticker, yest, yest)
                if not math.isnan(info['Start']): parsed_info[ticker]=info
    # TODO: custom day amount
    elif of in {'mtd', 'month_to_date', 'monthtodate'}:
        start_date=todays_date.replace(day=1)
        if _data is None: _data=get_data(
            tickers, start_date=start_date, end_date=_today)
        while start_date not in _data.index and start_date < todays_date:
            start_date += timedelta(days=1)
        if start_date >= todays_date: raise RuntimeError(
            'No market days this month')
        parsed_info={}
        for ticker in tickers:
            info=parse_info(_data, ticker, start_date, todays_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker]=info
    elif of in {'month', '1m', 'm'}:
        start_date=todays_date - timedelta(days=30)
        if _data is None: _data=get_data(
            tickers, start_date=start_date, end_date=_today)
        while start_date not in _data.index:
            start_date += timedelta(days=1)
        parsed_info={}
        for ticker in tickers:
            info=parse_info(_data, ticker, start_date, todays_date)
            if not math.isnan(info['Start']):
                parsed_info[ticker]=info
    # TODO: x months
    elif of in {'ytd', 'year_to_date', 'yeartodate'}:
        if _data is None:
            _data=get_data(tickers, start_date=_today.replace(
                day=1, month=1), end_date=_today)
            start_date=_data.first_valid_index()  # first market day of the year
        else:
            start_date=_today.replace(day=1, month=1).date()  # Jan 1st
            # find first market day of the year
            while start_date not in _data.index:
                start_date += timedelta(days=1)
        end_date=_data.last_valid_index()
        parsed_info={}
        for ticker in tickers:
            info=parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']): parsed_info[ticker]=info
    elif of in {'year', '1yr', 'yr', 'y'}:
        if _data is None:
            _data=get_data(tickers, start_date=_today - \
                           timedelta(days=365), end_date=_today)
            start_date=_data.first_valid_index()  # first market day of the year
        else:
            start_date=_today.date() - timedelta(days=365)
            _data=get_data(tickers, start_date=_today.replace(
                day=1, month=1), end_date=_today)
        end_date=_data.last_valid_index()
        parsed_info={}
        for ticker in tickers:
            info=parse_info(_data, ticker, start_date, end_date)
            if not math.isnan(info['Start']): parsed_info[ticker]=info
    # TODO: x years
    else: parsed_info={}  # invalid of
    if sort_key is None: return parsed_info
    sorted_info=sorted(parsed_info.items(), key=lambda item: item[1][sort_key])
    if _today.hour >= 16 and of == 'day':
        if of not in SORTED_INFO_CACHE: SORTED_INFO_CACHE[of]={}
        if str(todays_date) not in SORTED_INFO_CACHE[of]: SORTED_INFO_CACHE[of][str(
            todays_date)]={}
        SORTED_INFO_CACHE[of][str(todays_date)][','.join(tickers)]=sorted_info
    return sorted_info


@time_cache(60)  # cache for 1 minute
def winners(sorted_info=None, tickers: list=None, market='ALL', of='day', start_date=None, end_date=None, show=5):
    # sorted_info is the return of get_parsed_data with non-None sort_key
    if sorted_info is None:
        sorted_info=get_parsed_data(
            tickers=tickers, market=market, of=of, start_date=start_date, end_date=end_date)
    return list(reversed(sorted_info[-show:]))


@time_cache(60)  # cache for 1 minute
def losers(sorted_info=None, tickers: list=None, market='ALL', of='day', start_date=None, end_date=None, show=5):
    # sorted_info is the return of get_parsed_data with non-None sort_key
    if sorted_info is None:
        sorted_info=get_parsed_data(
            tickers=tickers, market=market, of=of, start_date=start_date, end_date=end_date)
    return sorted_info[:show]


@time_cache(60)  # cache for 1 minute
def winners_and_losers(_data=None, tickers=None, market='ALL', of='day', start_date=None, end_date=None, show=5,
                       console_output=True, csv_output=''):
    sorted_info=get_parsed_data(
        _data, tickers, market, of=of, start_date=start_date, end_date=end_date)
    if console_output:
        bulls=''
        bears=''
        length=min(show, len(sorted_info))
        for i in range(length):
            better_stock=sorted_info[-i - 1]
            worse_stock=sorted_info[i]
            open_close1=f'{round(better_stock[1]["Start"], 2)}, {round(better_stock[1]["End"], 2)}'
            open_close2=f'{round(worse_stock[1]["Start"], 2)}, {round(worse_stock[1]["End"], 2)}'
            bulls += f'\n{better_stock[0]} [{open_close1}]: {round(better_stock[1]["Percent Change"] * 100, 2)}%'
            bears += f'\n{worse_stock[0]} [{open_close2}]: {round(worse_stock[1]["Percent Change"] * 100, 2)}%'
        header1=f'TOP {length} WINNERS of ({of})'
        header2=f'TOP {length} LOSERS ({of})'
        line='-' * len(header1)
        print(f'{line}\n{header1}\n{line}{bulls}')
        line='-' * len(header2)
        print(f'{line}\n{header2}\n{line}{bears}')
    if csv_output:
        with open(csv_output, 'w', newline='') as f:
            writer=csv.writer(f)
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
    hdrs={'authority': 'finance.yahoo.com',
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
    url=f'https://finance.yahoo.com/quote/{ticker}/history'
    hdr=create_headers(f'{ticker}/history')
    soup=BeautifulSoup(requests.get(url, headers=hdr).text, 'html.parser')
    soup=soup.find('tbody')
    dividend=soup.find('strong').text
    return float(dividend)


@time_cache(3600)  # cache for 1 hour
def price_to_earnings(ticker, return_dict: dict=None, return_price=False):
    # EPS: earnings per share
    # PER: price over earnings ratio
    # useful concept to keep in mind:
    # PER = Stock price / EPS
    # Stock price = PER * EPS
    pe=-999999
    if ticker.endswith('.TO'):
        ticker='.'.join(ticker.split('.')[:-1])
        url=f'https://www.marketwatch.com/investing/stock/{ticker}/financials?country=ca'
    else:
        url=f'https://www.marketwatch.com/investing/stock/{ticker}/financials'
    try:
        text_soup=BeautifulSoup(requests.get(url, headers=GENERIC_HEADERS).text, 'html.parser')
    except requests.TooManyRedirects:
        return pe
    try:
        price=float(text_soup.find(
            'p', {'class': 'bgLast'}).text.replace(',', ''))
        titles=text_soup.findAll('td', {'class': 'rowTitle'})

        for title in titles:
            if 'EPS (Diluted)' in title.text:
                eps=[td.text for td in title.findNextSiblings(
                    attrs={'class': 'valueCell'}) if td.text]
                try: latest_eps=float(eps[-1])
                except ValueError: latest_eps=-float(eps[-1][1:-1])
                pe=price / latest_eps
                break
    except AttributeError: price=-1
    if return_dict is not None: return_dict[ticker]=(
        pe, price) if return_price else pe
    if return_price: return pe, price
    return pe


@time_cache(3600)  # cache for 1 hour
def get_target_price(ticker, level=None):
    """
    ticker: yahoo finance ticker
    level: either 'avg', 'low', 'high'
        returns (avg, low, high, price, eps_ttm) if level is an invalid value
    """
    quarterly_eps=stock_info.get_earnings(
        ticker)['quarterly_results']['actual'][-4:]
    quote_table=stock_info.get_quote_table(ticker)
    eps_estimates=stock_info.get_analysts_info(ticker)['Earnings Estimate']

    price=quote_table['Quote Price']
    eps_ttm=sum(quarterly_eps)
    # if EPS data DNE for 4 quarters, annualize out of the current ones
    if len(quarterly_eps) < 4: eps_ttm=quarterly_eps / len(quarterly_eps) * 4
    iloc_levels=(1, 2, 3)  # avg, low, high
    target_prices=[]
    for iloc_level in iloc_levels:
        forward_eps=eps_estimates.iloc[iloc_level, -1]  # next year eps
        target_price=price * forward_eps / eps_ttm
        target_prices.append(round(target_price, 2))
    if level == 'avg': return target_prices[0]
    elif level == 'low': return target_prices[1]
    elif level == 'high': return target_prices[2]
    return target_prices + [round(price, 2), round(eps_ttm, 2)]


def tickers_by_pe(tickers: set, output_to_csv='', console_output=True):
    """
    Returns the tickers by price-earnings ratio (remove negatives)
    :param tickers:
    :param output_to_csv:
    :param console_output:
    :return:
    """
    pes={}
    # TODO: thread
    for ticker in tickers:
        pe=price_to_earnings(ticker)
        if pe > 0: pes[ticker]=pe
    pes=sorted(pes.items(), key=lambda item: item[1])
    if console_output:
        header='TOP 5 TICKERS BY P/E'
        line='-' * len(header)
        print(f'{header}\n{line}')
        for i, (ticker, pe) in enumerate(pes):
            if i == 5: break
            print(f'{ticker}: {round(pe, 2)}')
    if output_to_csv:
        with open(output_to_csv, 'w', newline='') as f:
            writer=csv.writer(f)
            writer.writerow(['TICKER', 'Price-earnings'])
            for ticker in pes:
                writer.writerow(ticker)
    return pes


def sort_by_volume(tickers):
    pass


def get_index_futures():
    resp=requests.get(PREMARKET_FUTURES, headers=GENERIC_HEADERS)
    soup=BeautifulSoup(resp.text, 'html.parser')
    quotes=soup.find('tbody').findAll('tr')
    return_obj={}
    for quote in quotes:
        index_name=quote.find('a').text.upper()
        nums=quote.findAll('td')[3:]
        price=nums[0].text
        change=nums[3].text
        percent_change=nums[4].text
        return_obj[index_name]={'name': index_name, 'price': price,
            'change': change, 'percent_change': percent_change}
    return return_obj


def get_random_stocks(n=1):
    # return n stocks from NASDAQ and NYSE
    if n < 1: n = 1
    us_stocks = get_nasdaq_tickers().union(get_nyse_tickers())
    return_stocks = set()
    while len(return_stocks) < n:
        stock = random.sample(us_stocks, 1)[0]
        if not stock.count('.') and not stock.count('^'):
            return_stocks.add(stock)
    return return_stocks


def test_get_tickers():
    print('Getting DOW')
    get_dow_tickers()
    print('Getting S&P500')
    get_sp500_tickers()
    print('Getting NASDAQ')
    get_nasdaq_tickers()
    print('Getting AMEX')
    get_amex_tickers()
    print('Getting NYSE')
    get_nyse_tickers()
    print('Getting FUTURES')
    get_index_futures()
