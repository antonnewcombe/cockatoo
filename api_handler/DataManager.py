#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from utils.utilfunc import mergeForMarketsList, aggregateTriggerOrders
from utils.HttpNameConform import NamingConform
from api_handler.RestAPIs import ftxAPI


class HttpCleaner:
    def __init__(self, keys={'FTX': {'public': '', 'private': ''}}, ignore_account = False):
        self.use_keys = False
        if not ignore_account:
            self.use_keys = self.testValidKeys(keys['FTX']['public'], keys['FTX']['private'])
        self.keys = keys
        self.ftx = ftxAPI(self.keys['FTX']['public'], self.keys['FTX']['private'])

        self.rename = NamingConform['FTX']['rename']
        self.display_columns = NamingConform['FTX']['display']

        self.not_logged_in_df = pd.DataFrame({'Status': ['Not Logged In']})

    def availableMarkets(self):
        """
        used to populate treeview
        """
        markets = {}
        markets['FTX'] = self.FTXMarkets()
        return markets
    
    def marketList(self):
        req_dict = {'markets': self.ftx.markets(),
                    'futures': self.ftx.futures()}
        
        return mergeForMarketsList(req_dict)

    def FTXMarkets(self):
        """
        Data from symbols and futures endpoints is combined

        """
        symbols = self.ftx.markets()
        futures = self.ftx.futures()
        futuresDict = {future['name']: future for future in futures}

        symbolDict = {}

        # need to do this in a loop to check if the key is in symbol, on new
        # listings volumeUsd24h, change24h can be missing
        pairings = [['tick_size', 'priceIncrement', None],
                    ['min_quantity', 'sizeIncrement', None],
                    ['last_price', 'last', None],
                    ['24hr_vol', 'volumeUsd24h', None],
                    ['24hr_price_change', 'change24h', 4]]
        for symbol in symbols:
            name = symbol['name']
            symbolDict[name] = symbol
            symbolDict[name]['quote_currency'] = 'USD'
            # rename
            for renamed, api_name, rounding in pairings:
                if api_name in symbol.keys():
                    if renamed == '24hr_vol':
                        symbolDict[name][renamed] = f'{int(symbol[api_name]):,}'
                    elif renamed == '24hr_price_change':
                        symbolDict[name][renamed] = round(symbol[api_name], 4)

                    else:
                        symbolDict[name][renamed] = symbol[api_name]
                else:
                    symbolDict[name][renamed] = 0

            # add description if available - only descriptions for futures exist
            if name in futuresDict.keys():
                symbolDict[name]['description'] = futuresDict[name]['description']
            else:
                symbolDict[name]['description'] = ''

            # add special formatting
            symbolDict[name]['24hr_vol'] = symbolDict[name]['24hr_vol']
        return symbolDict

    def balances(self):
        """
        Returns pandas dataframe for balances section

        """
        #dont request if there arent any api keys
        if not self.use_keys:
            return {'FTX' : self.not_logged_in_df}
        balances = {}
        # ftx
        response = self.ftx.getAllBalances()
        if response:
            df = pd.DataFrame(response['main'])
            df = df.rename(self.rename['balance'], axis=1)
            df['USD Value'] = np.round(df['USD Value'],2 )
            df = df.sort_values('USD Value', ascending=False)
            df = df.reset_index()
            df = df[self.display_columns['balance']]
            balances['FTX'] = df
        else:
            balances['FTX'] = self.not_logged_in_df

        return balances

    def positions(self):
        """
        Returns pandas dataframe for positions section
        """
        #dont request if there arent any api keys
        if not self.use_keys:
            return {'FTX' : self.not_logged_in_df}
        positions = {}

        # ftx
        # the Api structure is different to content from website. entry price looks to be as at last funding
        response = self.ftx.getAllPositions()
        if type(response) == list:
            df = pd.DataFrame(response)
            if len(df) != 0:
                df = df.rename(self.rename['position'], axis=1)

                df = df[df['Position Size'] != 0]
                df['Avg Price'] = round(df['Avg Price'], 6)
                df = df.reset_index()
                df = df[self.display_columns['position']]

                positions['FTX'] = df
            else:
                positions['FTX'] = pd.DataFrame({'Status': ['No Open Positions']})
        else:
            positions['FTX'] = self.not_logged_in_df

        return positions

    def orders(self):
        """
        Returns pandas dataframe for positions orders section
        open orders and trigger orders are on different endpoints
        """
        #dont request if there arent any api keys
        if not self.use_keys:
            orders = {'FTX' : {'trigger' : self.not_logged_in_df,
                               'open': self.not_logged_in_df
                               }
                      }
            return {'orders_df': orders, 'trigger': {}, 'open': self.not_logged_in_df}
        orders = {}

        # ftx orders
        orders['FTX'] = {}
        # open limit orders
        open_orders = self.ftx.activeOrders()
        if type(open_orders) == list:
            df = pd.DataFrame(open_orders)
            if len(df) != 0:
                df = df.rename(self.rename['open_orders'], axis = 1)
                df = df[self.display_columns['open_orders']]
                df[' '] = 'Cancel Order'
                orders['FTX']['open'] = df

            else:
                orders['FTX']['open'] = pd.DataFrame({'Status': ['No Open Orders']})
        else:
            orders['FTX']['open'] = self.not_logged_in_df

        #open trigger orders
        trigger_orders = self.ftx.triggerOrders()
        trigger_orders_aggregated = aggregateTriggerOrders(trigger_orders)
        if type(trigger_orders) == list:
            df = pd.DataFrame(trigger_orders)
            if len(df) != 0:
                df = df.rename(self.rename['trigger_orders'], axis = 1)
                df = df[self.display_columns['trigger_orders']]
                df[' '] = 'Cancel Trigger'

            else:
                df = pd.DataFrame({'Status': ['No Trigger Orders']})
            orders['FTX']['trigger'] = df
            #print(df)
        else:
            orders['FTX']['trigger'] = self.not_logged_in_df
        return {'orders_df': orders, 'trigger': trigger_orders_aggregated, 'open': open_orders}

    def testConnection(self, exchange):
        if exchange == 'FTX':
            response = self.ftx.getAllBalances()
            if response:
                return 'Success'
            else:
                return 'Fail'
    def testValidKeys(self, public, private):
        """
        Tests whether user entered api keys are valid
        If they arent no request made to the private api endpoints
        keys not valid if response = {'success':False}
        """
        con = ftxAPI(public, private)
        response = con.getAllBalances()
        self.use_keys = True if response != {'success': False} else False
        return self.use_keys


