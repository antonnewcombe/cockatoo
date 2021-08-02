import hmac
import json
import time
import zlib
from collections import defaultdict, deque
from itertools import zip_longest
from typing import DefaultDict, Deque, List, Dict, Tuple, Optional

try:
    import websocket_manager
except:
    from ws_streams import websocket_manager


class FtxWebsocketClient(websocket_manager.WebsocketManager):
    _ENDPOINT = 'wss://ftx.com/ws/'
    MAX_TABLE_LEN = 100

    def __init__(self, api_key = '', api_secret = '', agg_choice = None) -> None:
        super().__init__()
        self.hasFirstMsg = False #used for ping thread to let know to start after on message called
        self._trades: DefaultDict[str, Deque] = defaultdict(lambda: deque([], maxlen=1000))
        self._fills: Deque = deque([], maxlen=10000)
        self._api_key = api_key
        self._api_secret = api_secret

        self._reset_data()
        
        self.orderbook_state = {}
        self.orderbook_state['counter'] = 0
        self.orderbook_state['bids'] = {0:0}
        self.orderbook_state['asks'] = {0:0}
        
        self.order_position = []
        
        self.trade_volume_dict = {}
        self.trade_volume_dict['counter'] = 0
        self.trade_volume_dict['prices'] = {}
        
        self.last_trade_price = {}
        self.last_trade_price['counter'] = 0
        self.last_trade_price['price'] = ''
        
        self.trades = {}
        self.trades['counter'] = 0
        self.trades_list: Deque = deque([], maxlen=10000)
        
        self.agg_choice = agg_choice if agg_choice else 'full'
        
        self.message = ''
        
        self.counter = 0
        self.interruptPing = False
        self.closedFlag = False

    def _on_open(self, ws):
        self._reset_data()

    def _reset_data(self) -> None:
        self._subscriptions: List[Dict] = []
        self._orders: Dict[int, Dict] = {}
        self._orderbook_timestamps: Dict[str, float] = {}
        self._orderbook: Dict[str, Dict[float, float]] = {side: {} for side in {'bids', 'asks'}}
        self._logged_in = False
        self._last_received_orderbook_data_at: float = 0.0

    def reset_volume_profile(self) -> None:
        self.trade_volume_dict['prices'] = {}
        self.trade_volume_dict['counter'] = 0


    def _reset_orderbook(self, market: str) -> None:
        self._orderbook: Dict[str, Dict[float, float]] = {side: {} for side in {'bids', 'asks'}}
        self._orderbook_timestamps: Dict[str, float] = {}

    def _get_url(self) -> str:
        return self._ENDPOINT

    def _login(self) -> None:
        ts = int(time.time() * 1000)
        self.send_json({'op': 'login', 'args': {
            'key': self._api_key,
            'sign': hmac.new(
                self._api_secret.encode(), f'{ts}websocket_login'.encode(), 'sha256').hexdigest(),
            'time': ts,
        }})
        self._logged_in = True

    def _subscribe(self, subscription: Dict) -> None:
        self.send_json({'op': 'subscribe', **subscription})
        self._subscriptions.append(subscription)


    def _unsubscribe(self, subscription: Dict) -> None:
        self.send_json({'op': 'unsubscribe', **subscription})
        while subscription in self._subscriptions:
            self._subscriptions.remove(subscription)

    def _unsubscribe_all(self):
        for subscription in self._subscriptions:
            self.send_json({'op': 'unsubscribe', **subscription})

    def stopHeartBeat(self):
        self.interruptPing = True


    def _reset_subscriptions(self):
        if not self.closedFlag:
            for subscription in self._subscriptions:
                self.send_json({'op': 'subscribe', **subscription})
        else:
            pass



    def get_fills(self) -> List[Dict]:
        if not self._logged_in:
            self._login()
        subscription = {'channel': 'fills'}
        if subscription not in self._subscriptions:
            self._subscribe(subscription)
        return list(self._fills.copy())

    def get_orders(self) -> Dict[int, Dict]:
        if not self._logged_in:
            self._login()
        subscription = {'channel': 'orders'}
        if subscription not in self._subscriptions:
            self._subscribe(subscription)
        return dict(self._orders.copy())

    def get_trades(self, market: str) -> List[Dict]:
        subscription = {'channel': 'trades', 'market': market}
        if subscription not in self._subscriptions:
            self._subscribe(subscription)
        return list(self._trades[market].copy())

    def subscribe_orderbook(self, market: str) -> None:
        subscription = {'channel': 'orderbook', 'market': market}
        if subscription not in self._subscriptions:
            self._subscribe(subscription)

    def get_orderbook(self, market: str, grouping = None) -> Dict[str, List[Tuple[float, float]]]:
        if grouping is None:
            subscription = {'channel': 'orderbook', 'market': market}
        else:
            subscription = {'channel': 'orderbookGrouped', 'market': market, 'grouping' : grouping}
        if subscription not in self._subscriptions:
            self._subscribe(subscription)
        d = {
            side: sorted(
                [(price, quantity) for price, quantity in list(self.d[side].items())
                 if quantity],
                key=lambda order: order[0] * (-1 if side == 'bids' else 1)
            )
            for side in {'bids', 'asks'}
        }
        self.best_bid = d['bids'][0][0]
        self.best_ask = d['asks'][0][0]
        return d

    def get_orderbook_timestamp(self, market: str) -> float:
        return self._orderbook_timestamps[market]

    def get_ticker(self, market: str) -> Dict:
        subscription = {'channel': 'ticker', 'market': market}
        if subscription not in self._subscriptions:
            self._subscribe(subscription)
        return self._tickers[market]

    def _handle_orderbook_message(self, message: Dict) -> None:
        market = message['market']
        if self.agg_choice != 'full':
            return
        subscription = {'channel': 'orderbook', 'market': market}
        if subscription not in self._subscriptions:
            return
        data = message['data']
        if data['action'] == 'partial':
        
            self._reset_orderbook(market)
            self.d = {'bids': defaultdict(float), 'asks': defaultdict(float)}
        for side in {'bids', 'asks'}:
            book = self.d[side]
            for price, size in data[side]:
                if size:
                    book[price] = size
                else:
                    del book[price]
            self._orderbook_timestamps[market] = data['time']

        checksum = data['checksum']
        orderbook = self.get_orderbook(market)
        checksum_data = [
            ':'.join([f'{float(order[0])}:{float(order[1])}' for order in (bid, offer) if order])
            for (bid, offer) in zip_longest(orderbook['bids'][:100], orderbook['asks'][:100])
        ]

        computed_result = int(zlib.crc32(':'.join(checksum_data).encode()))
        if computed_result != checksum:
            self._last_received_orderbook_data_at = 0
            self._reset_orderbook(market)
            self._unsubscribe(subscription)
            self._subscribe(subscription)
        else:
            self.orderbook_state = self.d
            self.orderbook_state['counter'] = self.counter
            self.counter += 1

    def _handle_orderbook_grouped_message(self, message: Dict, grouping: float) -> None:
        if self.agg_choice == 'full':
            return
        market = message['market']
        subscription = {'channel': 'orderbookGrouped', 'market': market, 'grouping' : grouping}
        if subscription not in self._subscriptions:
            return
        data = message['data']
        if message['type'] == 'partial':
            self._reset_orderbook(market)
            self.d = {'bids': defaultdict(float), 'asks':defaultdict(float)}
            for side in {'bids', 'asks'}:
                for price, size in data[side]:
                    self.d[side][price] = size

        elif message['type'] == 'update':
            for side in {'bids', 'asks'}:
                for price, size in data[side]:
                    if size != 0:
                        self.d[side][price] = size
                    else:
                        # entry for volume is 0 but
                        if price in self.d[side].keys():
                            del self.d[side][price]
                        else:
                            pass
                            #print(f'{side} {price} not in dict')
        else:
            print(message['data'])

        self.orderbook_state = {'bids' : defaultdict(float), 'asks': defaultdict(float)}
        for bids in list(sorted(self.d['bids'], reverse = True))[:50]:
            self.orderbook_state['bids'][bids] = self.d['bids'][bids]
        for asks in list(sorted(self.d['asks']))[:50]:
            self.orderbook_state['asks'][asks] = self.d['asks'][asks]
        self.orderbook_state['counter'] = self.counter
        self.counter += 1

        
    def _handle_trades_message(self, message: Dict) -> None:

        self.trades_list.append(message)
        self._trades[message['market']].append(message['data'])

        for trade in message['data']:
            price = trade['price']
            volume = round(trade['size'],2)
            side = trade['side']
            if price not in self.trade_volume_dict['prices'].keys():
                self.trade_volume_dict['prices'][price] = {}
                self.trade_volume_dict['prices'][price][side] = round(volume,2)
                init_side = 'buy' if side == 'sell' else 'sell'
                self.trade_volume_dict['prices'][price][init_side] = 0
            else:
                self.trade_volume_dict['prices'][price][side] += round(volume,2)
        self.trade_volume_dict['counter'] += 1
        self.last_trade_price['price'] = message['data'][-1]['price']
        self.last_trade_price['counter'] += 1

    def _handle_ticker_message(self, message: Dict) -> None:
        self._tickers[message['market']] = message['data']

    def _handle_fills_message(self, message: Dict) -> None:
        data = message['data']
        self._fills.append(data)

    def _handle_orders_message(self, message: Dict) -> None:
        data = message['data']
        self._orders.update({data['id']: data})

    def _on_message(self, ws, raw_message: str) -> None:

        self.hasFirstMsg = True
        message = json.loads(raw_message)
        self.message = message
        message_type = message['type']
        if message_type in {'subscribed', 'unsubscribed', 'pong'}:
            return
        elif message_type == 'info':
            if message['code'] == 20001:
                return self.reconnect()
        elif message_type == 'error':
            pass
            #print('error message', message)

        channel = message['channel']
        if channel == 'orderbook':
            self._handle_orderbook_message(message)
        elif channel == 'orderbookGrouped':
            self._handle_orderbook_grouped_message(message, grouping = message['grouping'])
        elif channel == 'trades':
            self._handle_trades_message(message)
        elif channel == 'ticker':
            pass
            self._handle_ticker_message(message)
        elif channel == 'fills':
            #pass
            self.order_position.append(message)
            self._handle_fills_message(message)
        elif channel == 'orders':
            self.order_position.append(message)
            self._handle_orders_message(message)
        else:
            pass



"""
fills message
{'channel': 'fills',
 'data': {'baseCurrency': None,
          'fee': 2.474664e-05,
          'feeCurrency': 'USD',
          'feeRate': 0.000194,
          'future': 'DOGE-PERP',
          'id': 615145268,
          'liquidity': 'maker',
          'market': 'DOGE-PERP',
          'orderId': 21618241506,
          'price': 0.01063,
          'quoteCurrency': None,
          'side': 'buy',
          'size': 12.0,
          'time': '2021-01-10T10:03:56.865871+00:00',
          'tradeId': 306298848,
          'type': 'order'},
 'type': 'update'}

websocket order place
{'channel': 'orders',
 'data': {'avgFillPrice': None,
          'clientId': None,
          'createdAt': '2021-01-10T09:57:17.305178+00:00',
          'filledSize': 0.0,
          'id': 21617270059,
          'ioc': False,
          'liquidation': False,
          'market': 'DOGE-PERP',
          'postOnly': True,
          'price': 0.010815,
          'reduceOnly': False,
          'remainingSize': 12.0,
          'side': 'buy',
          'size': 12.0,
          'status': 'new',
          'type': 'limit'},
 'type': 'update'}


websocket order filled
{'channel': 'orders',
 'data': {'avgFillPrice': 0.010815,
          'clientId': None,
          'createdAt': '2021-01-10T09:57:17.305178+00:00',
          'filledSize': 12.0,
          'id': 21617270059,
          'ioc': False,
          'liquidation': False,
          'market': 'DOGE-PERP',
          'postOnly': True,
          'price': 0.010815,
          'reduceOnly': False,
          'remainingSize': 0.0,
          'side': 'buy',
          'size': 12.0,
          'status': 'closed',
          'type': 'limit'},
 'type': 'update'}

websocket order cancelled
{'channel': 'orders',
 'data': {'avgFillPrice': None,
          'clientId': None,
          'createdAt': '2021-01-10T10:39:54.104027+00:00',
          'filledSize': 0.0,
          'id': 21623398853,
          'ioc': False,
          'liquidation': False,
          'market': 'DOT-PERP',
          'postOnly': False,
          'price': 6.1,
          'reduceOnly': False,
          'remainingSize': 0.0,
          'side': 'buy',
          'size': 2.0,
          'status': 'closed',
          'type': 'limit'},
 'type': 'update'}


"""

