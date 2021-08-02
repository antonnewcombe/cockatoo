#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time

from auth.Authenticator import Authenticator

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class ftxAPI:
    def __init__(self, public = None, private = None):
        self.endpoint = 'https://ftx.com'
        self.api_key = public
        self.api_secret = private
        
        self.auth = Authenticator.FTXAuthentication(self.api_key)
        self.future = None
        """
                    {
              "success": true,
              "result": {
                "ask": 4196,
                "bid": 4114.25,
                "change1h": 0,
                "change24h": 0,
                "description": "Bitcoin March 2019 Futures",
                "enabled": true,
                "expired": false,
                "expiry": "2019-03-29T03:00:00+00:00",
                "index": 3919.58841011,
                "last": 4196,
                "lowerBound": 3663.75,
                "mark": 3854.75,
                "name": "BTC-0329",
                "perpetual": false,
                "postOnly": false,
                "priceIncrement": 0.25,
                "sizeIncrement": 0.001,
                "underlying": "BTC",
                "upperBound": 4112.2,
                "type": "future"
              }
            }
        """
        self.future_stats = None
        """
        future_stats
        {
              "success": true,
              "result": {
                "volume": 1000.23,
                "nextFundingRate": 0.00025,
                "nextFundingTime": "2019-03-29T03:00:00+00:00",
                "expirationPrice": 3992.1,
                "predictedExpirationPrice": 3993.6,
                "strikePrice": 8182.35,
                "openInterest": 21124.583
              }
            }
        """
        
    def ticker(self, symbol):
        path_url = f'/api/futures/{symbol}'
        response = self.apiRequest(path_url, '', 'GET')
        return response
    
    def futures(self):
        path_url = '/api/futures'
        response = self.apiRequest(path_url, '', 'GET')
        self.future = response
        return response

    def markets(self):
        path_url = '/api/markets'
        response = self.apiRequest(path_url, '', 'GET')
        return response
    
    def account(self):
        path_url = '/api/account'
        response = self.apiRequest(path_url, {}, 'GET')
        return response

    def balance(self):
        path_url = '/api/wallet/balances'
        response = self.apiRequest(path_url, {}, 'GET')
        return response
    

    def snapshot(self, symbol):
        path_url = f'/api/markets/{symbol}/orderbook?depth=50'
        response = self.apiRequest(path_url, '', 'GET')
        return response

    def setLeverage(self, value):
        path_url = f'/api/account/leverage'
        postdict = {'leverage': int(value)}
        response = self.apiRequest(path_url, postdict, 'POST')
        return response

    def server_time(self):
        pass

    def getAllPositions(self, symbol = None):
        path_url = '/api/positions?showAvgPrice=true'
        params = {'showAvgPrice' : True}
        response = self.apiRequest(path_url, params, 'GET')
        return response

    def liquidations(self, symbol):
        pass

    def order(self, symbol):
        """
        {'avgFillPrice': None,
        'clientId': None,
        'createdAt': '2021-01-09T15:43:39.326835+00:00',
        'filledSize': 0.0,
        'future': 'RUNE-PERP',
        'id': 21497298117,
        'ioc': False,
        'liquidation': False,
        'market': 'RUNE-PERP',
        'postOnly': False,
        'price': 1.15,
        'reduceOnly': False,
        'remainingSize': 10.0,
        'side': 'buy',
        'size': 10.0,
        'status': 'open',
        'type': 'limit'}
        """
        path_url = f'/api/orders?market={symbol}'
        req_param = {'market': symbol}
        response = self.apiRequest(path_url, req_param, 'GET')
        return response

    def placeMarketOrder(self, symbol, side, quantity):
        path_url = '/api/orders'
        post_dict = {'market': symbol,
                     'side': side,
                     'price': None,
                     'type': 'market',
                     'size': quantity,
                     'externalReferralProgram': 'Cockatoo'}

        response = self.apiRequest(path_url, post_dict, 'POST')
        return response

    def activeOrder(self, symbol):
        path_url = f'/api/orders?market={symbol}'
        req_param = {'market': symbol}
        response = self.apiRequest(path_url, req_param, 'GET')
        return response
    
    
    def activeOrders(self):
        path_url = '/api/orders'
        response = self.apiRequest(path_url, {}, 'GET')
        return response

    def triggerOrders(self):
        path_url = '/api/conditional_orders'
        response = self.apiRequest(path_url, {}, 'GET')
        return response
    
    def getAccount(self):
        path_url = '/api/account'
        response = self.apiRequest(path_url, {}, 'GET')
        return response
    
    def getAllBalances(self):
        path_url = '/api/wallet/all_balances'
        
        response = self.apiRequest(path_url, {}, 'GET')
        return response

    def getCoins(self):
        path_url = '/api/wallet/coins'

        response = self.apiRequest(path_url, {}, 'GET')
        return response
    
    def fundingRates(self):
        start, end = int(time.time() - 60*60), int(time.time() + 60*60)
        path_url = f'/api/funding_rates?start_time={start}&end_time={end}'
        req_param = {'start_time': start,
                     'end_time': end}
        response = self.apiRequest(path_url, req_param, 'GET')
        return response

    def lendingRates(self):
        path_url = '/api/spot_margin/lending_rates'
        response = self.apiRequest(path_url, {}, 'GET')
        return response

    def borrowRates(self):
        path_url = '/api/spot_margin/borrow_rates'
        response = self.apiRequest(path_url, {}, 'GET')
        return response

    def futureStats(self, symbol):
        path_url = f'/api/futures/{symbol}/stats'
        req_param = {'market': symbol}
        response = self.apiRequest(path_url, req_param, 'GET')
        return response

    def predictedFunding(self, symbol):
        path_url = f'/api/futures/{symbol}/stats'
        self.future_stats = self.apiRequest(path_url, {}, 'GET')
        return str(round(self.future_stats['nextFundingRate'] * 100,2)) +'%'

    def lastFunding(self, symbol):
        path_url = f'/api/funding_rates?future={symbol}'
        response = self.apiRequest(path_url, '', 'GET')
        funding = str(round(response[0]['rate'] * 100,4)) + '%'
        return funding

    def markPrice(self, symbol):
        path_url = f'/api/futures/{symbol}'
        response = self.apiRequest(path_url, '', 'GET')
        self.future = response
        if self.future:
            return str(self.future['mark'])
        return ''

    def placeStopOrder(self, symbol, side, price, quantity, reduce_only_flag, order_price = None):
        """
        {
          "market": "XRP-PERP",
          "side": "sell",
          "triggerPrice": 0.306525,
          "size": 31431.0,
          "type": "stop",
          "reduceOnly": false,
        }
        """
        address = '/api/conditional_orders'
        postdict = {'market': symbol,
                     'side': side.lower(),
                     'triggerPrice': price,
                     'size': quantity,
                     'type': 'stop',
                     'reduceOnly': reduce_only_flag,
                    'externalReferralProgram': 'cockatoo'}
        if order_price:
            postdict['orderPrice'] = order_price
        response = self.apiRequest(address, postdict, 'POST')
        return response

    def placeTrailingStopOrder(self, symbol, side, trail_value, quantity, reduce_only_flag):
        """
        {
          "market": "XRP-PERP",
          "side": "sell",
          "trailValue": -0.05,
          "size": 31431.0,
          "type": "trailingStop",
          "reduceOnly": false,
        }
        """
        address = '/api/conditional_orders'
        postdict = {
                      'market': symbol,
                      'side': side.lower(),
                      'trailValue': trail_value,
                      'size': quantity,
                      'type': 'trailingStop',
                      'reduceOnly': reduce_only_flag,
                      'externalReferralProgram': 'cockatoo'
                    }
        response = self.apiRequest(address, postdict, 'POST')
        return response

    def placeTakeProfitOrder(self, symbol, side, price, quantity, reduce_only_flag, order_price = None):
        """
        {
          "market": "XRP-PERP",
          "side": "buy",
          "triggerPrice": 0.367895,
          "size": 31431.0,
          "type": "takeProfit",
          "reduceOnly": false,
        }
        """
        address = '/api/conditional_orders'
        postdict = {'market': symbol,
                     'side': side.lower(),
                     'triggerPrice': price,
                     'size': quantity,
                     'type': 'takeProfit',
                     'reduceOnly': reduce_only_flag,
                    'externalReferralProgram': 'cockatoo'}
        if order_price:
            postdict['orderPrice'] = order_price
        response = self.apiRequest(address, postdict, 'POST')
        return response

    def placeOrder(self, symbol, price, quantity, side, order_type, post_only_flag, reduce_only_flag):

        address = '/api/orders'
        postdict = {
                    'market' : symbol,
                    'side' : side.lower(),
                    'price' : price,
                    'type' : order_type.lower(),
                    'size' : quantity,
                    'reduceOnly' : reduce_only_flag,
                    'postOnly' : post_only_flag,
                    'ioc' : False,
                    'clientId' : None,
                    'externalReferralProgram': 'cockatoo'
            }
        response = self.apiRequest(address, postdict, 'POST')
        return response
    
    def cancel(self, symbol = None, orderID = None):
        """
        successful response will be 
        {
          "success": true,
          "result": "Order queued for cancelation"
        }

        """
        orderID = str(orderID)
        address = f'/api/orders/{orderID}'
        req_params = {'orderID' : orderID}
        response = self.apiRequest(address, req_params, 'DELETE')
        return response

    def cancelTriggerOrder(self, orderID = None):
        orderID = str(orderID)
        address = f'/api/conditional_orders/{orderID}'
        req_params = {'orderID' : orderID}
        response = self.apiRequest(address, req_params, 'DELETE')
        return response

    def cancelAll(self, symbol = None):
        address = '/api/orders'
        req_params = {'market': symbol}
        response = self.apiRequest(address, req_params, 'DELETE')
        return response

    def apiRequest(self, address, params, request_type):
        url = self.endpoint + address
        ts = int(time.time() * 1000)
        request = requests.Request(request_type, url, json=params)
        
        prepared = request.prepare()
        signature = self.auth.get_signature(self.api_secret, ts, params, request_type, address)

        prepared.headers['FTX-KEY'] = self.api_key
        prepared.headers['FTX-SIGN'] = signature
        prepared.headers['FTX-TS'] = str(ts)
        session = requests.Session()
        response = session.send(prepared)
        return self.processResponse(response, address)

    def processResponse(self, response, address):
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            if not data['success']:
                print(['[API MESSAGE] - ', data, address])
                error_dict = {'success': False}
                if address.split('/')[-1] in ['conditional_orders', 'orders']:
                    error_dict['order_fail'] = True
                return error_dict
            else:
                return data['result']
