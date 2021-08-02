#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from requests.auth import AuthBase
import time
import hmac
import json


class Authenticator:

    """Attaches API Key Authentication to the given Request object. This implementation uses `expires`."""
    
    class BybitAuthenticator(AuthBase):

        def __init__(self, apiKey):
            """Init with Key & Secret."""
            self.apiKey = apiKey

        def generate(self):
            r = {}
            expires = str(int(round(time.time())-1))+"000"
            r["timestamp"] = int(expires)
            r["api_key"] = self.apiKey
            return r
    
        def get_signature(self, apiSecret, req_params):
            _val = '&'.join(
                [str(k) + "=" + str(v).replace('False','false').replace('True','true') for k, v in sorted(req_params.items()) if (k != 'sign') and (v is not None)])
            return str(hmac.new(bytes(apiSecret, "utf-8"), bytes(_val, "utf-8"), digestmod="sha256").hexdigest())
        
    class FTXAuthentication:
        def __init__(self, apiKey):
            self.apiKey = apiKey
        
        def get_signature(self, apiSecret, ts, req_params, method, path_url):
            """
            either /api/markets for GET, /api/orders for POST
            """
            
            if type(req_params) == dict:
                req_params = json.dumps(req_params)
            signature_payload = f'{ts}{method}{path_url}{req_params}'
            signature_payload = signature_payload.encode()
            
            signature = hmac.new(apiSecret.encode(), signature_payload, 'sha256').hexdigest()
            
            return signature
        

