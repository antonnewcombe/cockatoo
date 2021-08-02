#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import PyQt5.QtCore

import asyncio

from ws_streams import FTXStream
from api_handler.DataManager import HttpCleaner
from api_handler.RestAPIs import ftxAPI
from utils.utilfunc import cleanTradeData, conHTTP, mergeForQuoteBoard, staticTable, aggregateVolume, aggregateOrders
from utils.defines import FTX

class WorkerSignals(PyQt5.QtCore.QObject):
    # signals for dom ladder
    price_feed_signal = PyQt5.QtCore.pyqtSignal(object)
    last_trade_signal = PyQt5.QtCore.pyqtSignal(object)
    order_feed_signal = PyQt5.QtCore.pyqtSignal(object)
    position_feed_signal = PyQt5.QtCore.pyqtSignal(object)
    volume_profile_signal = PyQt5.QtCore.pyqtSignal(object)

    order_id_signal = PyQt5.QtCore.pyqtSignal(object)

    # information http request signals
    last_funding_signal = PyQt5.QtCore.pyqtSignal(object)
    pred_funding_signal = PyQt5.QtCore.pyqtSignal(object)
    mark_price_signal = PyQt5.QtCore.pyqtSignal(object)

    liquidation_signal = PyQt5.QtCore.pyqtSignal(object)

    quotes_signal = PyQt5.QtCore.pyqtSignal(object)
    accounts_signal = PyQt5.QtCore.pyqtSignal(object)
    trigger_orders_signal = PyQt5.QtCore.pyqtSignal(object) #used to populate the DOM ladders

    # for ladder
    all_ladders = PyQt5.QtCore.pyqtSignal(object)
    closeWindow = PyQt5.QtCore.pyqtSignal(object)

    trades_signal = PyQt5.QtCore.pyqtSignal(object)

    #for sounds
    sound_signal = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self):
        PyQt5.QtCore.QObject.__init__(self)


class httpRequestPrivateThread(PyQt5.QtCore.QRunnable):
    def __init__(self, keys = None, feed = None):
        PyQt5.QtCore.QRunnable.__init__(self)
        self.signals = WorkerSignals()
        self.keys = keys
        self.channel = HttpCleaner(self.keys)
        self.feed = feed
        self.closed = False

    def run(self):
        while not self.closed:
            try:
                if self.feed == 'accounts':

                    req_dict = {'balances': self.channel.balances,
                                'positions': self.channel.positions,
                                'orders': self.channel.orders}

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(conHTTP(req_dict))
                    self.signals.accounts_signal.emit(req_dict) #emit for account section in mainwindow
                    self.signals.trigger_orders_signal.emit(req_dict['orders']['trigger']) #emit for ladder display
                    PyQt5.QtCore.QThread.msleep(1000)


            except Exception as e:
                print([f'[EXCEPTION] - Exception in httpRequestPrivateThread {e}'])
                PyQt5.QtCore.QThread.msleep(2000)


    def stop(self):
        self.closed = True


class httpRequestPublicThread(PyQt5.QtCore.QRunnable):
    def __init__(self, feed = None):
        PyQt5.QtCore.QRunnable.__init__(self)
        self.signals = WorkerSignals()
        self.feed = feed
        self.closed = False
        self.channel = HttpCleaner(ignore_account=True)

    def run(self):
        while not self.closed:
            try:
                if self.feed == 'quote_board':
                    req_dict = {'markets': self.channel.ftx.markets,
                                'futures': self.channel.ftx.futures,
                                'funding': self.channel.ftx.fundingRates,
                                'lending': self.channel.ftx.lendingRates}#,
                                #'borrowing': None} #this only works if you have completed customer verification for spot margin
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(conHTTP(req_dict))
                    df = mergeForQuoteBoard(req_dict)
                    self.signals.quotes_signal.emit(df)
                    PyQt5.QtCore.QThread.msleep(6000)

            except Exception as e:
                print([f'[EXCEPTION] - Exception in httpRequestPublicThread {e}'])
                PyQt5.QtCore.QThread.msleep(2000)


    def stop(self):
        self.closed = True


class WebsocketThread(PyQt5.QtCore.QRunnable):
    def __init__(self, markets = ['BTC-PERP', 'ETH-PERP', 'DOGE-PERP', 'LINK-PERP', 'SUSHI-PERP',
                                  'DOT-PERP', 'SOL-PERP', 'CRV-PERP']):
        PyQt5.QtCore.QRunnable.__init__(self)

        self.markets = markets

        self.signals = WorkerSignals()
        self.channel = HttpCleaner(ignore_account=True)

        self.closed = False

    def run(self):
        self.stream = FTXStream.FtxWebsocketClient()
        for market in self.markets:
            self.stream.get_trades(market)

        threshold = 20_000
        while not self.closed:
            while len(self.stream.trades_list) > 0:
                message = self.stream.trades_list.popleft()
                formatted = cleanTradeData(message, threshold)
                self.signals.trades_signal.emit(formatted)

            PyQt5.QtCore.QThread.msleep(300)



    def stop(self):
        self.closed = True
        self.stream.keep_running = False
        self.stream.stopHeartBeat()
        self.stream._unsubscribe_all()
        self.stream.closedFlag = True

class DownloadPublicThread(PyQt5.QtCore.QRunnable):
    """

    TODO: better way to set out the runnable classes
    TODO: https://stackoverflow.com/questions/58327821/how-to-pass-parameters-to-pyqt-qthreadpool-running-function
    """

    def __init__(self, exchange=None, contract=None, parent=None, specs=None, launch_agg = None):

        PyQt5.QtCore.QRunnable.__init__(self)

        self.contract = contract
        self.exchange = exchange
        self.tick = specs['tick_size']
        self.agg = launch_agg
        self.closed = False
        self.agg_change_flag = False
        self.refresh_flag = True #signals to refresh whole volume profile after change in aggregation as model updates on diff usually
        self.stream = ''
        self.signals = WorkerSignals()
        self.thread_sleep = 75
        self.volume_profile = {}

    def run(self):

        self.stream = FTXStream.FtxWebsocketClient(agg_choice = self.agg)
        self.stream._subscribe({'channel': 'orderbookGrouped', 'market': self.contract, 'grouping': self.agg})
        self.stream._subscriptions.append({'channel': 'orderbookGrouped', 'market': self.contract, 'grouping': self.agg})
        self.stream.get_trades(self.contract)


        book_counter = 0
        trade_counter = 0
        while not self.closed:
            if self.agg_change_flag:
                self.manageSubscriptions()
                self.agg_change_flag = False
                self.agg = self.new_agg
                PyQt5.QtCore.QThread.msleep(self.thread_sleep)
                self.refresh_flag = True
            else:
                try:
                    data = staticTable(self.stream.orderbook_state)
                    if data['counter'] != 0 and data['counter'] != book_counter:
                        mid = (data['best'][0] + data['best'][1]) / 2 #mid price for centering the ladders. use rather than last trade
                        self.signals.price_feed_signal.emit(data)
                        self.signals.last_trade_signal.emit(mid)
                        book_counter = data['counter']
                        PyQt5.QtCore.QThread.msleep(self.thread_sleep)
                    else:
                        PyQt5.QtCore.QThread.msleep(self.thread_sleep)
                    if self.stream.trade_volume_dict['counter'] != trade_counter \
                            and \
                            self.stream.trade_volume_dict['counter'] != 0:

                        volume_profile = aggregateVolume(self.stream.trade_volume_dict,self.agg, self.tick)
                        # only emit the changes between current memory dict and new dict
                        dict_diff = {k: volume_profile[k] for k, _ in
                                     set(volume_profile.items()) - set(self.volume_profile.items())}
                        self.signals.volume_profile_signal.emit([volume_profile, dict_diff, self.refresh_flag])
                        self.refresh_flag = False
                        trade_counter = self.stream.trade_volume_dict['counter']
                        self.volume_profile = volume_profile.copy()
                        PyQt5.QtCore.QThread.msleep(5)
                    PyQt5.QtCore.QThread.msleep(5)

                except Exception as e:
                    print([f'[EXCEPTION] - Exception in DownloadPublicThread {e}'])
                    PyQt5.QtCore.QThread.msleep(2000)

    def update_snapshot(self, data):
        if self.exchange == FTX:
            self.signals.price_feed_signal.emit(data)

    def changeAggregation(self, grouping):
        self.new_agg = grouping
        self.agg_change_flag = True

    def clearVolumeProfile(self):
        self.stream.reset_volume_profile()
        self.refresh_flag = True

    def manageSubscriptions(self):
        # unsub from agg
        self.stream.agg_choice = self.new_agg  # tells websocket connection to ignore the last of the old aggregation data
        if self.agg == 'full':
            self.stream._unsubscribe({'channel': 'orderbook', 'market': self.contract})
        else:
            self.stream._unsubscribe({'channel': 'orderbookGrouped', 'market': self.contract, 'grouping': self.agg})
        PyQt5.QtCore.QThread.msleep(500)
        # sub to new agg
        if self.new_agg == 'full':
            self.stream._subscribe({'channel': 'orderbook', 'market': self.contract})
        else:
            self.stream._subscribe({'channel': 'orderbookGrouped', 'market': self.contract, 'grouping': self.new_agg})

        return

    def stop(self):
        self.stream.stop()
        self.stream.closedFlag = True
        self.closed = True

class DownloadPrivateThread(PyQt5.QtCore.QRunnable):

    def __init__(self, exchange=None, contract=None, parent=None, specs=None, keys=None, agg=None):
        PyQt5.QtCore.QRunnable.__init__(self)
        self.order_dict = {}
        self.position_dict = {'side': None, 'quantity': None, 'price': None}
        self.contract = contract
        self.exchange = exchange
        self.api_key = keys['public']
        self.api_secret = keys['private']

        self.specs = specs
        self.spot_flag = True if specs['type'] == 'spot' else False
        self.agg = agg

        self.closed = False
        self.stream = ''
        self.signals = WorkerSignals()
        self.channel = ftxAPI(public=self.api_key, private=self.api_secret)
        self.thread_sleep = 20

        self.trigger_orders = {}

    def run(self):

        if self.exchange == FTX:
            self.initOrderDict(self.channel.activeOrders())
            self.trigger_orders = self.initTriggerDict(self.channel.triggerOrders())
            self.updateLadderOrders()
            self.updateLadderPosition()
            self.stream = FTXStream.FtxWebsocketClient(api_key=self.api_key, api_secret=self.api_secret)

            self.stream.get_orders()
            self.stream.get_fills()

            while not self.closed:
                while self.stream.order_position:
                    message = self.stream.order_position.pop(0)
                    if message['data']['market'] == self.contract:
                        if message['channel'] == 'orders':
                            self.process_order(message)
                            self.handle_order_sound_action(message)

                        elif message['channel'] == 'fills':
                            self.signals.sound_signal.emit('fills')
                            self.updateLadderPosition()

                    PyQt5.QtCore.QThread.msleep(10)
                PyQt5.QtCore.QThread.msleep(self.thread_sleep)

    def update_snapshot(self, data):
        self.signals.price_feed_signal.emit(data['result'])

    def process_order(self, message):
        if self.exchange == FTX:
            if message['data']['market'] == self.contract:
                self.update_order_dict(message['data'])

    def handle_order_sound_action(self, message):
        if message['data']['filledSize'] == 0 and message['data']['status'] == 'closed':
            return
        self.signals.sound_signal.emit('orders')

    def initOrderDict(self, active_orders):
        if not active_orders:
            self.aggregated_order_dict = {}
            return
        for order in active_orders:
            if order['market'] != self.contract:
                continue
            price, qty, order_id, side = order['price'], order['remainingSize'], order['id'], order['side']
            if price not in self.order_dict.keys():
                self.order_dict[price] = {'quantity' : qty,
                                          'side': side,
                                          'orders': [order],
                                          'order_id': [order_id]}
            else:
                # multiple orders at the same price
                self.order_dict[price]['quantity'] += qty
                self.order_dict[price]['order_id'].append(order_id)
                self.order_dict[price]['orders'].append(order)

        self.updateLadderOrders()

    def initTriggerDict(self, trigger_orders):
        trigger_dict = {}
        for order in trigger_orders:
            if order['market'] != self.contract:
                continue
            market = order['market']
            price = order['triggerPrice']
            qty = order['size']
            side = order['side']
            order_id = order['id']
            if price not in trigger_dict.keys():
                trigger_dict[price] = {'quantity': qty,
                                             'side': side,
                                             'orders': [order],
                                             'order_id': [order_id]}
            else:
                trigger_dict[price]['quantity'] = round(trigger_dict[price]['quantity'] + qty, 10)
                trigger_dict[price]['order_id'].append(order_id)
                trigger_dict[price]['orders'].append(order)

        return trigger_dict

    def updateLadderPosition(self):
        """
        Spot positions treated differently as holding spot is not considered a position
        """
        if self.spot_flag:
            spot_balances = self.channel.balance()
            spot_coin = self.contract.split('/')[0]
            self.position_dict = {'side': None, 'quantity': None, 'price': None, 'string': 'No Position 没有'}
            for spot_info in spot_balances:
                if spot_info['coin'] == spot_coin:
                    total, free = spot_info['total'], spot_info['free']
                    side = 'buy' if free != 0 else None
                    side_str = 'Long' if side == 'buy' else ''
                    quantity = f'{free} | {total}'
                    string = f'{side_str} {quantity} {spot_coin}'
                    self.position_dict = {'side': side, 'quantity': quantity, 'price': None, 'string': string}
        else:
            positions = self.channel.getAllPositions(self.contract)
            if not positions:
                #not logged in
                return
            found = False
            for position in positions:
                if position['size'] != 0 and position['future'] == self.contract:
                    found = True
                    size, side, price = position['size'], position['side'], position['recentAverageOpenPrice']

                    self.position_dict['quantity'] = size * (1 if side == 'buy' else -1)
                    self.position_dict['price'] = price
                    self.position_dict['side'] = side

                    direction = 'Long' if side == 'buy' else 'Short'
                    sizing = abs(self.position_dict['quantity'])
                    self.position_dict['string'] = f'{direction} {sizing} @ {price}'
            if not found:
                self.position_dict = {'side': None,
                                      'quantity': None,
                                      'price': None,
                                      'string': 'No Position 没有'}
        self.signals.position_feed_signal.emit(self.position_dict)

    def refreshTriggers(self):
        self.trigger_orders = self.initTriggerDict(self.channel.triggerOrders())
        self.updateLadderOrders()

    def updateLadderOrders(self):
        self.aggregated_order_dict = aggregateOrders(self.order_dict, self.trigger_orders, self.agg, self.specs['tick_size'])
        self.signals.order_feed_signal.emit(self.aggregated_order_dict.copy())

    def update_order_dict(self, message):
        price = message['price']
        remain_size = message['remainingSize']
        size = message['size']
        side = message['side']
        order_id = message['id']
        status = message['status']
        filledSize = message['filledSize']
        no_order_condition = (price not in self.order_dict.keys()
                              or
                              (price in self.order_dict.keys() and self.order_dict[price]['quantity'] == 0))
        if no_order_condition:
            if status in ['open', 'new']:
                self.order_dict[price] = {'quantity' : remain_size,
                                          'side': side,
                                          'orders': [message],
                                          'order_id': [order_id]}
            elif status == 'closed':
                #this arises where post only is not filled
                pass

        else:
            if order_id in self.order_dict[price]['order_id']:
                # replace old message with new message for an order_id
                for order in self.order_dict[price]['orders']:
                    if order['id'] == order_id:
                        self.order_dict[price]['orders'].remove(order)
                        self.order_dict[price]['orders'].append(message)
                    else:
                        pass
                        #print('order id not equal')

            else:
                # adding another order onto a price
                self.order_dict[price]['order_id'].append(order_id)
                self.order_dict[price]['orders'].append(message)

            # recalculate the remaining quantity for a price
            qty = 0
            for order in self.order_dict[price]['orders']:
                qty += order['remainingSize']
            self.order_dict[price]['quantity'] = round(qty, 8)
            # remove the orders/order_ids where the remaining size = 0
            self.order_dict[price]['orders'] = [order for order in self.order_dict[price]['orders'] if
                                                order['remainingSize'] != 0]
            self.order_dict[price]['order_id'] = [order['id'] for order in self.order_dict[price]['orders']]

        self.updateLadderPosition()
        self.updateLadderOrders()

    def receive_trigger_orders(self, trigger_orders):
        self.trigger_orders = trigger_orders
        self.updateLadderOrders()

    def defaultify(self, d):
        if not isinstance(d, dict):
            return d
        return defaultdict(lambda: defaultdict(float), {k: self.defaultify(v) for k, v in d.items()})

    def generateDisplayOrderDict(self, order_dict):
        """
        for table model, the order data is
        defaultified
        order_dict = {'buys': {'open_buys' : {2000 : [1, 0],
                                              2001 : [5, 0]},
                               'trigger_buys' : {3000 : [4, 1],
                                                 3005 : [5, 1]}
                      'sells' : {'open_sells' : {2500 : [1,0]},
                                 'trigger_sells' : { 1800 : [5, 1]}}

        """
        d = {}
        d['open_buys'] = self.defaultify(
            {k: [order_dict[k]['quantity'], 0] for k in order_dict if order_dict[k]['side'] == 'buy'})
        d['open_sells'] = self.defaultify(
            {k: [order_dict[k]['quantity'], 0] for k in order_dict if order_dict[k]['side'] == 'sell'})
        d['trigger_buys'] = self.defaultify(
            {k: [self.trigger_orders[k]['quantity'], 1] for k in self.trigger_orders.keys() if self.trigger_orders[k]['side'] == 'buy'})
        d['trigger_sells'] = self.defaultify(
            {k: [self.trigger_orders[k]['quantity'], 1] for k in self.trigger_orders.keys() if self.trigger_orders[k]['side'] == 'sell'})
        return d


    def stop(self):
        self.closed = True
        self.stream.stop()
        self.stream.closedFlag = True

