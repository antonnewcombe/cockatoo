#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Renaming Http response fields for use in the orders position, accounts and open positions window
"""

NamingConform = {'FTX': {
                        'rename': {'balance': {'free': 'Available Balance',
                                                'total': 'Balance',
                                                'usdValue': 'USD Value',
                                                'coin': 'Coin'
                                                },
                                    'position': {'future': 'Market',
                                                 'side': 'Side',
                                                 'size': 'Position Size',
                                                 'estimatedLiquidationPrice': 'Est Liquidation Price',
                                                 'recentPnl': 'PNL',
                                                 'recentAverageOpenPrice': 'Avg Price'
                                                 },
                                    'open_orders': {'market': 'Market',
                                                    'side': 'Side',
                                                    'size': 'Size',
                                                    'price': 'Price',
                                                    'reduceOnly': 'Reduce Only',
                                                    'filledSize': 'Filled',
                                                    'type': 'Type',
                                                    'id': 'Order ID'
                                                    },
                                    'trigger_orders': {'market': 'Market',
                                                       'type': 'Type',
                                                       'orderType': 'Order Type',
                                                       'side': 'Side',
                                                       'size': 'Size',
                                                       'filledSize': 'Filled Size',
                                                       'orderPrice': 'Limit Price',
                                                       'triggerPrice': 'Trigger Price',
                                                       'id': 'Order ID'
                                                       }

                                    },
                        'display': {'balance': ['Coin',
                                                  'Balance',
                                                  'Available Balance',
                                                  'USD Value'
                                                  ],
                                      'position': ['Market',
                                                   'Avg Price',
                                                   'Side',
                                                   'Position Size',
                                                   'Est Liquidation Price',
                                                   'PNL'
                                                   ],
                                      'open_orders': ['Market',
                                                      'Side',
                                                      'Size',
                                                      'Price',
                                                      'Reduce Only',
                                                      'Filled',
                                                      'Order ID'
                                                      ],
                                      'trigger_orders': ['Market',
                                                         'Type',
                                                         'Order Type',
                                                         'Side',
                                                         'Size',
                                                         'Filled Size',
                                                         'Limit Price',
                                                         'Trigger Price',
                                                         'Order ID'
                                                         ]
                                      }
                                             }
                 }
