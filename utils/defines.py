APIKEY = 'APIKEY'
APISECRET = 'APISECRET'
BASE_URL = 'BASE_URL'
URL = 'URL'
PUBLIC = 'PUBLIC'
PRIVATE = 'PRIVATE'


BYBIT = 'BYBIT'
FTX = 'FTX'
BITMEX = 'BITMEX'

SoundOptions = {'liquidation': {'name' : 'Liquidation'},
                 'order_fail': {'name': 'Unsucessful Order'},
                 'fills': {'name': 'Order Filled'},
                 'orders': {'name': 'Order Placed'}}

EmptySettings = {
    "dom_settings": {
        "aggregation_levels": {
            "default": [
                0.00025,
                0.001,
                0.0025,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.5,
                1,
                2,
                2.5,
                5,
                10,
                50,
                100
            ]
        },
        "button_values": {
            "default": [
                0.001,
                0.01,
                0.1,
                0.5,
                1.0,
                10.0
            ]
        }
    },
    "favourites": {
        "FTX": []
    },
    "keys": {
        "FTX": {
            "private": "",
            "public": "",
            "save_keys_in_settings_file": False
        },

    },
    "quoteboard": {0: ""},
    "sounds": {
        "fills": {
            "file": ""
        },
        "liquidation": {
            "file": ""
        },
        "orders": {
            "file": ""
        },
        "order_fail": {
            "file": ""
        }
    },
    "themes": {
        "background": "",
        "frame": ""
    },
    "trade_subs": {
        "FTX": []
    }
}
