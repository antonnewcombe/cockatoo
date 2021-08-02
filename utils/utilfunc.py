#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import decimal
import math
from collections import defaultdict
import asyncio
import concurrent.futures
import pandas as pd
import numpy as np

def priceBand(price, tick_size):

    decimal_places = abs(int(decimal.Decimal(str(tick_size)).as_tuple().exponent))

    upper = round(int(math.ceil(price / tick_size)) * tick_size, decimal_places)
    lower = round(upper - tick_size, decimal_places)

    return upper, lower


def aggregateVolume(tradeDict, tick_size, default_tick):
    """
    aggregate trade volumes for volume profile when aggregation in dom ladder tick size changes

    """
    trade_dict_cleaned = defaultdict(float)
    if tick_size == default_tick:
        for price, values in list(tradeDict['prices'].items()):
            volume = tradeDict['prices'][price]['buy'] + tradeDict['prices'][price]['sell']
            trade_dict_cleaned[price] = round(volume, 2)

    else:
        # need to round up buys to next highest tick, rounddown sells to next lower tick
        for price, values in list(tradeDict['prices'].items()):
            bounds = priceBand(price, tick_size)
            for bound, side in list(zip(bounds, ['buy', 'sell'])):
                if bound not in trade_dict_cleaned.keys():
                    trade_dict_cleaned[bound] = values[side]
                else:
                    trade_dict_cleaned[bound] += values[side]
    return trade_dict_cleaned

def priceAgg(bounds, side, order_price, order_label):
    """
    find the correct aggregation level for a given order at a price
    handle the case where the order_price is the same as the upper bound price for a bid (dont want to round down)
    """

    if (side == 'buy' and order_label == 'open') or (side == 'sell' and order_label == 'trigger'):
        return max(bounds) if order_price == max(bounds) else min(bounds)
    else:
        return min(bounds) if order_price == min(bounds) else max(bounds)

def aggregateOrders(order_dict, trigger_dict, agg_size, default_tick_size):
    """
    aggregate order dict to display the orders when the aggregation in the dom ladder tick size changes

    bids get rounded down to next lower agg price, offers get rounded up to next higher agg price
    eg: agg size is 0.1, default is 0.01. bid @ 54.52 -> bid @ 54.5

    open and trigger orders are combined

    agg_order_dict = {price : {'open' : aggregated info,
                               'trigger': aggregated info,
                               'order_id': combined order ids for open and trigger}}

    """
    agg_order_dict = {}

    for order_dict_variant, label in [[order_dict, 'open'], [trigger_dict, 'trigger']]:

        for price, values in list(order_dict_variant.items()):
            bounds = priceBand(price, agg_size)
            price_agg = priceAgg(bounds, values['side'], price, label)
            if price_agg not in agg_order_dict.keys():
                agg_order_dict[price_agg] = {}
            if label not in agg_order_dict[price_agg].keys():
                agg_order_dict[price_agg][label] = {k: j for k, j in values.items()}
                agg_order_dict[price_agg][label + '_order_id'] = agg_order_dict[price_agg][label]['order_id']

            else:
                # sum the quantities, combine the orders lists, combine the order_id lists
                if values['side'] == agg_order_dict[price_agg][label]['side']:  # this should always best the case
                    agg_order_dict[price_agg][label]['quantity'] = round(agg_order_dict[price_agg][label]['quantity'] + \
                                                                   values['quantity'], 10)
                    agg_order_dict[price_agg][label]['orders'] = agg_order_dict[price_agg][label]['orders'].copy() + \
                                                                 values['orders']
                    agg_order_dict[price_agg][label]['order_id'] = agg_order_dict[price_agg][label]['order_id'].copy() + \
                                                                   values['order_id']
                    agg_order_dict[price_agg][label + '_order_id'] = agg_order_dict[price_agg][label + '_order_id'].copy() + values[
                        'order_id']

    return agg_order_dict


def cleanTradeData(message, threshold):

    """
        FTX trade message of form
    {'channel': 'trades', 'market': 'ETH-PERP', 'type': 'update', 'data': [{'id': 371820267, 'price': 1350.5, 'size': 14.81, 'side': 'sell', 'liquidation': False, 'time': '2021-01-28T14:21:03.838575+00:00'}]}
    {'channel': 'trades', 'market': 'BTC-PERP', 'type': 'update', 'data': [{'id': 371820275, 'price': 31999.0, 'size': 0.0001, 'side': 'buy', 'liquidation': False, 'time': '2021-01-28T14:21:03.906966+00:00'}]}
    {'channel': 'trades', 'market': 'ETH-PERP', 'type': 'update', 'data': [{'id': 371820286, 'price': 1350.4, 'size': 0.215, 'side': 'sell', 'liquidation': False, 'time': '2021-01-28T14:21:04.071084+00:00'}, {'id': 371820287, 'price': 1350.3, 'size': 0.004, 'side': 'sell', 'liquidation': False, 'time': '2021-01-28T14:21:04.071084+00:00'}]}

    """
    formatted = []
    trades = message['data']
    market = message['market']
    for trade in trades:
        date_time = trade['time'].split('.')[0]
        date, time = date_time.split('T')
        exchange = 'FTX'
        side = trade['side'].upper()
        price = trade['price']
        size = int(round(trade['size'] * trade['price'],0))
        size_str =  f'{size:,}' if size < 1_000_000 else f'{round(size/1_000_000,2)}M'
        trade_type = 'liq' if trade['liquidation'] else 'trade'
        if size >= threshold:
            d = {'time': [time],
                 'market': [market],
                 'exchange': [exchange],
                 'USD': [size_str, size],
                 'side': [side],
                 'price': [str(price), price],
                 'type': [trade_type]}
            formatted.append(d)
    return formatted

def staticTable(book):
    # convert d = {'bids:{1900: 90, 1899: 88...}, 'asks':{1901:100, 1902: 200....}} to orderbook table
    static_book = {}
    static_book['book'] = []
    asks = sorted(book['asks'].items(), reverse=True)
    bids = sorted(book['bids'].items(), reverse=True)
    for p, vol in asks:
        static_book['book'].append([0, p, vol])
    for p, vol in bids:
        static_book['book'].append([vol, p, 0])
    static_book['book'] = np.array(static_book['book'])
    static_book['best'] = [asks[-1][0], bids[0][0]]
    static_book['counter'] = book['counter']
    return static_book

def translator(x, mapping):
    for pre, post in mapping.items():
        x = x.replace(pre, post)
    return x

def mergeForMarketsList(req_dict):
    markets = pd.DataFrame(req_dict['markets'])
    markets = markets.set_index('name')
    futures = pd.DataFrame(req_dict['futures'])
    futures = futures.set_index('name')

    df = markets.join(futures, rsuffix='_f')
    df = df.reset_index()
    df = df.fillna('')
    return df[['name','description']]

def mergeForQuoteBoard(req_dict):
    markets = pd.DataFrame(req_dict['markets'])
    markets = markets.fillna(0)
    markets = markets.set_index('name')
    futures = pd.DataFrame(req_dict['futures'])
    futures = futures.fillna(0)
    futures = futures.set_index('name')

    lending = pd.DataFrame(req_dict['lending'])
    lending = lending.rename(columns = {'estimate' : 'lend_estimate', 'previous': 'lend_prior'})
    lending = lending.set_index('coin')

    df = markets.join(futures, rsuffix= '_f')
    funding = pd.DataFrame(req_dict['funding'])
    funding.columns = ['name','rate', 'time']
    funding = funding.set_index('name')
    df = df.join(funding, rsuffix = '_fund')

    #join borrow and lending on name.replace('/USD','').replace('/USDT','')
    df = df.reset_index()
    df['coin'] = df['name'].apply(lambda x: translator(x, {'/USD':'', '/USDT':''}))
    df = df.set_index('coin')
    df = df.join(lending)
    df['lend_estimate_APY'] = df['lend_estimate'].apply(lambda x: (1 + x)**8760 - 1) #8760 is 24hrs * 365 days

    df['spread'] = round(df['ask'] / df['bid'] - 1, 2)
    df['basis'] = round(df['last'] / df['index'] - 1, 4)
    #filter out the MOVE contracts from the basis calc as there is a special formula applied on the index
    df['basis'] = np.where(df['name'].str.contains('BTC-MOVE'), 0,df['basis'])
    df['change1h'] = round(df['change1h'], 4)
    df['change24h'] = round(df['change24h'], 4)
    df['volumeUsd24h'] = np.round(df['volumeUsd24h'].astype(int),0)
    df['index'] = round(df['index'], 4)
    df['rate'] = round(df['rate'] * 100,5)

    df = df.fillna(0)
    return df.reset_index()

async def conHTTP(req_dict):

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(req_dict.keys())) as executor:
        loop = asyncio.get_event_loop()
        for key, function in req_dict.items():
            req_dict[key] = loop.run_in_executor(executor, function)
        for response in await asyncio.gather(*list(req_dict.values())):
            pass
        for request, response in req_dict.items():
            req_dict[request] = response.result()


def aggregateTriggerOrders(trigger_orders):
    order_dict = {}
    for order in trigger_orders:
        market = order['market']
        price = order['triggerPrice']
        qty = order['size']
        side = order['side']
        order_id = order['id']
        if market not in order_dict.keys():
            order_dict[market] = {}
        if price not in order_dict[market].keys():
            order_dict[market][price] = {'quantity': round(qty, 8),
                                         'side': side,
                                         'orders': [order],
                                         'order_id': [order_id]}
        else:
            order_dict[market][price]['quantity'] += round(qty, 8)
            order_dict[market][price]['order_id'].append(order_id)
            order_dict[market][price]['orders'].append(order)
    return order_dict


def rec_dd():
    return defaultdict(rec_dd)



