import json
import time
import sys
from threading import Thread, Lock

from websocket import WebSocketApp

class WebsocketManager:
    _CONNECT_TIMEOUT_S = 5

    def __init__(self):
        self.connect_lock = Lock()
        self.ws = None
        self.api_key = ''
        self.api_secret = ''
        self._logged_in = False
        self.closeFlag = False
        self.subscriptions = []
        

    def _get_url(self):
        raise NotImplementedError()

    def _on_message(self, ws, message):
        raise NotImplementedError()

    def send(self, message):
        self.connect()
        self.ws.send(message)

    def send_json(self, message):
        self.send(json.dumps(message))
        
    def sendHeartBeat(self):
        raise NotImplementedError()

    def _connect(self):
        assert not self.ws, "ws should be closed before attempting to connect"
            
        self.ws = WebSocketApp(
            self._get_url(),
            on_message=self._wrap_callback(self._on_message),
            on_close=self._wrap_callback(self._on_close),
            on_error=self._wrap_callback(self._on_error),
            keep_running=True
        )

        wst = Thread(target=self._run_websocket, args=(self.ws,))
        wst.daemon = True
        wst.start()
        ts = time.time()
        timeout = 10
        while self.ws and (not self.ws.sock or not self.ws.sock.connected) and timeout:
            timeout -= 1
            time.sleep(1)

        if self.api_key and self.api_secret:
            self._login()

        self._reset_subscriptions()

    def _login(self):
        raise NotImplementedError()

    def _reset_subscriptions(self):
        raise NotImplementedError()

    def _wrap_callback(self, f):
        def wrapped_f(ws, *args, **kwargs):
            if ws is self.ws:
                try:
                    f(ws, *args, **kwargs)

                except Exception as e:
                    raise Exception(f'Error running websocket callback: {e}{args}{kwargs}')
        return wrapped_f

    def _run_websocket(self, ws):
        #https://github.com/websocket-client/websocket-client/issues/580

        try:
            ws.run_forever(ping_interval=5, ping_timeout=None)
        except Exception as e:
            raise Exception(f'Unexpected error while running websocket: {e}')
        finally:
            if self.closeFlag:
                return
            self._reconnect(ws)

    def _reconnect(self, ws):
        if self.closeFlag:
            return
        assert ws is not None, '_reconnect should only be called with an existing ws'
        if ws is self.ws:
            self.ws = None
            ws.close()
            self.connect()

    def connect(self):
        if self.ws:
            return
        with self.connect_lock:
            while not self.ws:
                self._connect()
                if self.ws:
                    return

    def _on_close(self, ws):
        self._reconnect(ws)

    def _on_error(self, ws, error):
        self._reconnect(ws)

    def reconnect(self) -> None:
        if self.ws is not None:
            self._reconnect(self.ws)

    def stop(self):
        self.ws.close()
