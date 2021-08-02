#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from api_handler.RestAPIs import ftxAPI

class Execution:

    def __init__(self, contract=None, tableSize=None, keys=None):
        self.channel = ftxAPI(public=keys['public'], private=keys['private'])
        self.tableSize = tableSize
        self.contract = contract

    def execute(self, row, column, price, quantity, post_only_flag, reduce_only_flag,
                offset = None, offset_type = None, stop_mode = None, tick_size = None):

        if column not in [1, 3]:
            return

        side = 'Buy' if column == 1 else 'Sell'
        if stop_mode:
            order_price = self.calculateOrderPrice(column, price, offset, offset_type, tick_size)
            if stop_mode == 'stop':
                return self.channel.placeStopOrder(self.contract, side, price, quantity, reduce_only_flag, order_price)
            elif stop_mode == 'trailingStop':
                trail_value = self.calculateOffset(column, price, offset, offset_type, tick_size)
                return self.channel.placeTrailingStopOrder(self.contract, side, trail_value, quantity, reduce_only_flag)
            elif stop_mode == 'takeProfit':
                return self.channel.placeTakeProfitOrder(self.contract, side, price, quantity, reduce_only_flag, order_price)
            else:
                print('invalid stop order')
        else:
            order_type = 'Limit'
            if price:
                return self.channel.placeOrder(self.contract, price, quantity, side, order_type, post_only_flag, reduce_only_flag)

    def marketOrder(self, contract, quantity, side):
        return self.channel.placeMarketOrder(contract, side, quantity)

    def cancelAll(self, contract):
        self.channel.cancelAll(contract)

    def calculateOffset(self, column, price, offset, offset_type, tick_size):
        side_multiplier = 1 if column == 1 else -1
        if offset_type == 'tick':
            #eg: limit order for 8 ticks away with 0.5 tick size, then order price is 4$ away from trigger price
            price_offset = int(offset) * tick_size
        elif offset_type == 'percent':
            # eg: limit order for 1% away from trigger price - > 1% * trigger price
            price_offset = float(offset) * price
        return price_offset * side_multiplier

    def calculateOrderPrice(self, column, price, offset, offset_type, tick_size):
        if int(offset) == 0:
            #no offset, order will be treated as market order
            return
        offset = self.calculateOffset(column, price, offset, offset_type, tick_size)
        order_price = price + offset


    def cancelPriceOrders(self, symbol, row, column, price, order_dict):
        if price in order_dict.keys():
            if 'open_order_id' in order_dict[price].keys():
                order_ids = order_dict[price]['open_order_id']
                for order_id in order_ids:
                    self.channel.cancel(symbol, order_id)
            if 'trigger_order_id' in order_dict[price].keys():
                order_ids = order_dict[price]['trigger_order_id']
                for order_id in order_ids:
                    self.channel.cancelTriggerOrder(order_id)
                
        else:
            pass
            #print('price not in order_dict')


