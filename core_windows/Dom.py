#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import PyQt5.QtGui
import PyQt5.QtWidgets
import PyQt5.QtCore

import time
import decimal
from functools import partial

from ws_streams.Runnables import DownloadPublicThread, DownloadPrivateThread

from custom_qt.CustomWidgets import (CustomButtonClass, PositionBox, OrderBox, OrderSpinBox, OrderTypeCheckBox,
                                  Toggle, MarketBuyButton, MarketSellButton, ComboBox)
from custom_qt.CustomModels import TableModel, TableView
from custom_qt.CustomDelegates import ProgressDelegate, ItemDelegate
from api_handler.Execution import Execution
from api_handler.DataManager import HttpCleaner


class DomWidget(PyQt5.QtWidgets.QWidget):
    all_ladders = PyQt5.QtCore.pyqtSignal(object)

    def __init__(self, exchange=None, contract=None, specs=None, keys=None, launch_agg=None):
        super().__init__()
        self.exchange = exchange
        self.contract = contract
        self.specs = specs
        self.keys = keys
        self.launch_agg = launch_agg
        self.tick = launch_agg if launch_agg else self.specs['tick_size']
        self.rounding = abs(int((decimal.Decimal(str(self.specs['tick_size'])).as_tuple().exponent)))
        self.multiplier = 1 / self.tick
        self.last_trade = self.specs['last_price']
        self.len_text_prices = len(str(self.last_trade))
        self.model = TableModel(self.specs, launch_agg=self.launch_agg)
        self.view = TableView()
        self.proxy = PyQt5.QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.view.setModel(self.proxy)
        delegate = ItemDelegate(self.view)
        self.view.setItemDelegate(delegate)
        self.setStyleSheet(
            "TableView {gridline-color : 1px grey; font-size: 8pt; font: bold; font-family: Arial;}")
        #
        progress_delegate = ProgressDelegate(self.view)
        for i in range(5):
            self.view.setItemDelegateForColumn(i, delegate)
        self.view.setItemDelegateForColumn(5, progress_delegate)

        self.setTableDimensions()

        layout = PyQt5.QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.current_index = self.model.default_length - self.specs['last_price'] * self.multiplier

        self.streamingPublic(self.launch_agg)
        self.center()

    def setTableDimensions(self):

        colnums = 6
        colwidth = 65
        self.view.verticalHeader().setDefaultSectionSize(int(1 / 2 * colwidth))
        total_width = 0
        for i in range(colnums):
            if i in [0, 4, 5]:
                w = colwidth
            elif i == 2:
                if self.len_text_prices > 7:
                    w = colwidth * (1 + 0.03 * self.len_text_prices)
                else:
                    w = colwidth

            elif i in [1, 3]:
                w = int(0.85 * colwidth)
            self.view.setColumnWidth(i, w)
            total_width += w
        total_width = int(total_width)
        self.view.setMaximumWidth(total_width + 25)
        self.view.setMinimumWidth(total_width - 25)
        self.total_width = total_width
        self.view.verticalHeader().setMinimumSectionSize(8)
        self.view.verticalHeader().setDefaultSectionSize(16)

    def cellMiddleClicked(self):
        self.center()

    def streamingPublic(self, launch_agg):
        self.threadsPublic = []
        self.threadpoolPublic = PyQt5.QtCore.QThreadPool()
        downloader = DownloadPublicThread(exchange=self.exchange,
                                          contract=self.contract,
                                          specs=self.specs,
                                          launch_agg=launch_agg)
        downloader.signals.price_feed_signal.connect(self.updateBook)
        downloader.signals.last_trade_signal.connect(self.updateCurrentIndex)
        downloader.signals.volume_profile_signal.connect(self.updateVolumeProfile)
        self.threadpoolPublic.start(downloader)
        self.threadsPublic.append(downloader)

    def centerTable(self, press):
        if press == 32 or press == 'mouse3':  # spacebar or mouse3
            self.view.scrollTo(self.proxy.index(self.current_index, 2),
                               PyQt5.QtWidgets.QAbstractItemView.PositionAtCenter)

    def center(self):
        self.view.scrollTo(self.proxy.index(self.current_index, 2),
                           PyQt5.QtWidgets.QAbstractItemView.PositionAtCenter)
        self.releaseKeyboard()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.all_ladders.emit(1)

    @PyQt5.QtCore.pyqtSlot(object)
    def updateBook(self, data):
        self.model.updateBook(data)

    @PyQt5.QtCore.pyqtSlot(object)
    def updateVolumeProfile(self, data):
        # pass
        self.model.updateVolumeProfile(data)

    @PyQt5.QtCore.pyqtSlot(object)
    def updateCurrentIndex(self, last_trade):
        # pass
        self.last_trade = last_trade
        self.current_index = self.model.default_length - int(last_trade * self.multiplier)

class MainWindow(PyQt5.QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        self.centerAllLadders(event.key())


class DomWindow(MainWindow):
    window_resize = PyQt5.QtCore.pyqtSignal()
    closeWindow = PyQt5.QtCore.pyqtSignal(object)
    all_ladders = PyQt5.QtCore.pyqtSignal(object)

    sound_signal = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, parent=None, contract=None, exchange=None, specs=None, keys=None, dom_settings=None):
        PyQt5.QtWidgets.QMainWindow.__init__(self, parent)

        self.tick = specs['tick_size']
        self.future_flag = True if specs['type'] == 'future' else False
        self.button_values = dom_settings['button_values']['default'] \
            if contract not in dom_settings['button_values'].keys() \
            else dom_settings['button_values'][contract]

        self.choices = self.getGroupings(contract, dom_settings)
        self.launch_aggregation = self.launchGrouping(specs, self.choices)
        self.setStyleSheet("""
        QPushButton{ background-color:  #ffff00 ; color: black; font: bold }
        QPushButton:hover{ background-color:   #cc9900; color: black; font; bold }        
        MainWindow{background-color: #e6dddc; }
        QListView{background-color:  #ffe0cc; color:black; font: bold;}
        QListView:item:hover{background-color:  #ffe0cc; color:#364b70; font: bold;}
        QListView:item:text{border-style: dot-dash;}
        QListView:item{background-color:  #ffe0cc; color:black;  font: bold;}
        """)
        self.exchange = exchange
        self.contract = contract
        self.specs = specs
        self.keys = keys
        self.setWindowTitle(self.specs['name'])
        self.private_active = False

        self.dom = DomWidget(exchange=self.exchange, contract=self.contract, specs=self.specs,
                             launch_agg=self.launch_aggregation)
        self.dom.view.item_right_clicked.connect(partial(self.cancelOrder))
        self.dom.view.item_left_clicked.connect(partial(self.routeOrder))
        self.dom.view.middle_clicked.connect(self.centerAllLadders)
        self.dom.view.stop_drag_signal.connect(partial(self.routeStop))

        # dont allow dom ladder to maximise
        self.setWindowFlags(PyQt5.QtCore.Qt.Window |
                            PyQt5.QtCore.Qt.CustomizeWindowHint |
                            PyQt5.QtCore.Qt.WindowTitleHint |
                            PyQt5.QtCore.Qt.WindowSystemMenuHint |
                            PyQt5.QtCore.Qt.WindowMinimizeButtonHint |
                            PyQt5.QtCore.Qt.WindowCloseButtonHint)

        self.position_box = PositionBox()

        self.options_row = self.createOptions()
        self.stop_row = self.createStopRow()
        self.button_row = self.createOrderButtons()
        self.order_type_row = self.createOrderTypes()
        self.market_button_row = self.createMarketOrderRow()

        # Collect all this stuff into a vertical layout
        self.layout = PyQt5.QtWidgets.QVBoxLayout()

        self.layout.addWidget(self.position_box)
        if self.future_flag:
            self.layout.addLayout(self.stop_row)
        self.layout.addLayout(self.options_row)
        self.layout.addWidget(self.dom)
        self.layout.addLayout(self.order_type_row)
        self.layout.addLayout(self.button_row)
        self.layout.addLayout(self.market_button_row)

        self.window = PyQt5.QtWidgets.QWidget()
        self.window.setLayout(self.layout)
        self.setCentralWidget(self.window)

        self.setMinimumWidth(self.dom.total_width + 38)
        self.setMaximumWidth(self.dom.total_width + 38)

        if self.keysAreValid():
            self.execution = Execution(contract=self.contract, tableSize=self.dom.model.default_length, keys=self.keys)
            self.streamingPrivate(self.launch_aggregation)
            self.private_active = True
        else:
            self.threadsPrivate = []
        self.dom.center()

    def keysAreValid(self):
        c = HttpCleaner(ignore_account=True)
        flag = c.testValidKeys(self.keys['public'], self.keys['private'])
        return flag

    def startPrivateStreams(self):
        if self.threadsPrivate:
            self.threadsPrivate[0].stop()
            time.sleep(.1)
        self.execution = Execution(contract=self.contract, tableSize=self.dom.model.default_length, keys=self.keys)
        self.streamingPrivate(self.dom.model.tick)
        self.private_active = True

    def stopPrivateStreams(self):
        self.private_active = False
        if self.threadsPrivate:
            print(self.threadsPrivate)
            self.threadsPrivate[0].stop()
            time.sleep(.1)
        self.execution = None

    def RowsAtDefaultTick(self, specs):
        """
        find number of rows required for dom window table
         - limit the size of the table for the dom window. some contracts have small tick sizes

        """
        tick_size = specs['tick_size']
        prices = specs['last_price']
        rows_to_max_price = prices / tick_size
        return rows_to_max_price

    def getGroupings(self, contract, dom_settings):
        groupings = dom_settings['aggregation_levels']['default'] \
            if contract not in dom_settings['aggregation_levels'].keys() \
            else dom_settings['aggregation_levels'][contract]

        default_tick_dp = self.getDecimalPlaces(self.tick)
        grouping_options_filt = [i for i in groupings if i > self.tick and default_tick_dp >= self.getDecimalPlaces(i)]
        # TODO - exclude the groupings which result in dom ladder table size too big?
        # TODO - problem for contracts like doge where the tick size is small relative to the price
        return grouping_options_filt

    def getDecimalPlaces(self, number):
        """
        return the number of decimal places
        """
        number = ("%.17f" % number).rstrip('0').rstrip(
            '.')  # handles the case where tick is expressed as 5e-07 eg: DOGE
        if '.' not in str(number):
            return 0
        return len(str(number).split('.')[1])

    def launchGrouping(self, specs, groupings):
        """
        sets the default tick value to be approximately the fee cost
        """
        prices = specs['last_price']
        return min(groupings, key=lambda x: abs(x / prices - 0.05 / 100))

    def createOrderTypes(self):
        dp = self.decimal_places_for_orderbox()
        self.order_box = OrderSpinBox(min=0, max=10000000000000, decimals=dp)
        self.orderbox_value = 0
        self.reduce_only = Toggle(w1='Reduce Only 仅减少', w2='Standard 标准')  # , w3 = 'Trigger 扳机')
        self.post_only = Toggle(w1='Post Only 仅发布', w2='Limit 限价')
        row = PyQt5.QtWidgets.QHBoxLayout()
        row.addWidget(self.reduce_only)
        row.addWidget(self.order_box)
        row.addWidget(self.post_only)

        return row

    def createOrderButtons(self):
        button_row = PyQt5.QtWidgets.QHBoxLayout()
        self.button_row_widgets = {}
        for i, amount in enumerate(self.button_values):
            amount_str = self.formatButtonValues(amount)
            self.button_row_widgets[str(amount)] = CustomButtonClass(amount_str, value=amount)
            self.button_row_widgets[str(amount)].setMinimumWidth(1)
            self.button_row_widgets[str(amount)].right_clicked.connect(partial(self.orderSizing, amount))
            self.button_row_widgets[str(amount)].left_clicked.connect(partial(self.orderSizing, amount))
            self.button_row_widgets[str(amount)].space_bar_btn_clicked.connect(self.center)
            button_row.addWidget(self.button_row_widgets[str(amount)])
        return button_row

    def formatButtonValues(self, button_value):
        """
        CustomButtonClass will contain the button value and button text display seperately.
        This handles case where markets like Shibu-Inu have 100m order sizes
        """
        magnitude = 0
        while abs(button_value) >= 1000:
            magnitude += 1
            button_value /= 1000.0
        # add more suffixes if you need them
        if magnitude > 0:
            return '%.2f%s' % (button_value, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])
        return str(button_value)[:-2] if str(button_value).endswith('.0') else str(button_value)

    def createStopRow(self):
        # stop
        self.stop_order_choices = ['Stop', 'Trail', 'TP']
        self.selected_stop_mode = 'Stop'
        self.stop_choices = ComboBox()
        self.stop_view = PyQt5.QtWidgets.QListView()
        self.stop_view.clicked.connect(self.combo_click)
        self.stop_choices.setView(self.stop_view)
        self.stop_choices.addItems(self.stop_order_choices)
        self.stop_choices.currentIndexChanged.connect(self.handleStopChoices)

        self.offset_box = OrderSpinBox(min=0, max=10000000000000)
        self.tick_dollar = Toggle(w1='Tick Offset 间隔计数', w2='% Offset 价格变动')
        self.tick_dollar.setMinimumWidth(140)

        row = PyQt5.QtWidgets.QHBoxLayout()
        row.addWidget(self.stop_choices)

        row.addWidget(self.offset_box)
        row.addWidget(self.tick_dollar)
        return row

    def createOptions(self):

        self.aggchoice = ComboBox()
        self.list_view = PyQt5.QtWidgets.QListView()
        self.list_view.clicked.connect(self.combo_click)
        self.aggchoice.setView(self.list_view)
        self.choices_str = ['full'] + [str(i) for i in self.choices]
        self.aggchoice.addItems(self.choices_str)
        current_index = self.choices_str.index(str(self.launch_aggregation))
        self.aggchoice.setCurrentIndex(current_index)
        self.aggchoice.currentIndexChanged.connect(self.aggregateFeed)

        # cancel all orders
        self.cancel_all_button = CustomButtonClass('Cancel All 全部取消')

        self.cancel_all_button.right_clicked.connect(self.cancelAllOrders)
        self.cancel_all_button.left_clicked.connect(self.cancelAllOrders)
        # reset volume profile
        self.reset_volume_profile_button = CustomButtonClass('Reset Vol 重置成交量')
        self.reset_volume_profile_button.setMinimumWidth(140)
        self.reset_volume_profile_button.right_clicked.connect(self.resetVolumeProfile)
        self.reset_volume_profile_button.left_clicked.connect(self.resetVolumeProfile)

        row = PyQt5.QtWidgets.QHBoxLayout()
        row.addWidget(self.cancel_all_button)
        row.addWidget(self.aggchoice)
        row.addWidget(self.reset_volume_profile_button)
        return row

    def createMarketOrderRow(self):
        self.center_button = PyQt5.QtWidgets.QPushButton('Center 中央')
        self.center_button.clicked.connect(self.center)

        self.market_buy_button = MarketBuyButton('Market Buy 市场买入')
        self.market_buy_button.clicked.connect(self.marketBuy)
        self.market_sell_button = MarketSellButton('Market Sell 市场卖出')
        self.market_sell_button.clicked.connect(self.marketSell)

        row = PyQt5.QtWidgets.QHBoxLayout()
        row.addWidget(self.market_buy_button)
        row.addWidget(self.center_button)
        row.addWidget(self.market_sell_button)

        return row

    def handleStopChoices(self, index):
        self.selected_stop_mode = self.stop_order_choices[index]
        if self.selected_stop_mode == 'Stop':
            self.stop_init_dict = {'type': 'stop'}
        elif self.selected_stop_mode == 'Trail':
            self.stop_init_dict = {'type': 'trailingStop'}
        elif self.selected_stop_mode == 'TP':
            self.stop_init_dict = {'type': 'takeProfit'}

    def changeOrderButtons(self, button_values):
        self.button_values = button_values

    def orderSizing(self, amount, side):

        current_value = self.order_box.value()
        self.orderbox_value = max(round(current_value + amount * side, 4), 0)
        self.order_box.setValue(self.orderbox_value)
        self.order_box.setSingleStep(round(float(amount), 4))

        self.button_row_widgets[str(amount)].releaseKeyboard()

    def getStopType(self, label):
        if label == 'Stop':
            type = 'stop'
        elif label == 'Trail':
            type = 'trailingStop'
        elif label == 'TP':
            type = 'takeProfit'

        return type

    def decimal_places_for_orderbox(self):
        min_quantity = self.specs['min_quantity']
        dp = max(len(str(min_quantity).split('.')[-1]), 2)
        return dp

    def routeOrder(self, index):
        if self.private_active:  # flag for api connection working
            row, column = index.row(), index.column()
            self.post_only_flag = self.post_only.isChecked()
            self.reduce_only_flag = self.reduce_only.isChecked()
            price = self.dom.model.price_colum_num[row]
            order_response = self.execution.execute(row, column, price, self.order_box.value(), self.post_only_flag,
                                   self.reduce_only_flag)
            self.setFocus()
            if type(order_response) == dict:
                if 'order_fail' in order_response.keys():
                    #send signal to play fail sound
                    self.handleSoundSignals('order_fail')

    def routeStop(self, index):
        if self.private_active:
            row, column = index.row(), index.column()
            self.post_only_flag = self.post_only.isChecked()
            self.reduce_only_flag = self.reduce_only.isChecked()
            price = self.dom.model.price_colum_num[row]
            offset = self.offset_box.value()
            offset_type = 'tick' if self.tick_dollar.isChecked() else 'percent'
            stop_type = self.getStopType(self.selected_stop_mode)
            tick_size = self.getCurrentTickSize()
            order_response = self.execution.execute(row, column, price, self.order_box.value(), self.post_only_flag,
                                                    self.reduce_only_flag, offset, offset_type, stop_type, tick_size)
            self.setFocus()
            if type(order_response) == dict:
                if 'order_fail' in order_response.keys():
                    #send signal to play fail sound
                    self.handleSoundSignals('order_fail')

    def cancelOrder(self, index):
        if self.private_active:
            row, column = index.row(), index.column()
            price = self.dom.model.price_colum_num[row]
            order_dict = self.threadsPrivate[0].aggregated_order_dict
            self.execution.cancelPriceOrders(self.contract, row, column, price, order_dict)
            self.setFocus()
            self.threadsPrivate[0].refreshTriggers()

    def centerAllLadders(self, data):
        self.all_ladders.emit(1)
        self.setFocus()

    def combo_click(self):
        self.setFocus()

    def center(self):
        self.dom.view.scrollTo(self.dom.proxy.index(self.dom.current_index, 2),
                               PyQt5.QtWidgets.QAbstractItemView.PositionAtCenter)
        self.setFocus()
        self.releaseKeyboard()

    def streamingPrivate(self, agg):

        self.threadsPrivate = []
        self.threadpoolPrivate = PyQt5.QtCore.QThreadPool()
        downloader = DownloadPrivateThread(exchange=self.exchange,
                                           contract=self.contract,
                                           specs=self.specs,
                                           keys=self.keys,
                                           agg=agg)
        downloader.signals.position_feed_signal.connect(self.position_box.position_feed_display)
        downloader.signals.order_feed_signal.connect(self.dom.model.updateOrderFeed)
        downloader.signals.sound_signal.connect(self.handleSoundSignals)
        self.threadpoolPrivate.start(downloader)
        self.threadsPrivate.append(downloader)

    def marketBuy(self):
        if self.private_active:
            self.execution.marketOrder(self.contract, self.order_box.value(), 'buy')

    def marketSell(self):
        if self.private_active:
            self.execution.marketOrder(self.contract, self.order_box.value(), 'sell')

    def getCurrentTickSize(self):
        choice = self.aggchoice.currentText()
        if choice != 'full':
            tick = float(choice)
        else:
            tick = self.specs['tick_size']
        return tick

    def aggregateFeed(self, selection):
        """
        change the model based on new aggregation
        """
        choice = self.getCurrentTickSize()
        # length = self.dom.model.default_length
        self.dom.model.default_length = self.dom.model.DefaultLength(self.dom.last_trade, choice)
        self.dom.multiplier = 1 / choice

        prices = self.dom.model.setPriceColumn(tick_size=choice, length=self.dom.model.default_length)
        self.dom.model.tick = choice
        self.dom.current_index = self.dom.model.default_length - int(self.dom.last_trade * self.dom.multiplier)
        self.dom.threadsPublic[0].changeAggregation(choice)
        # need to send the order info again so it can be redisplayed at different table position
        if self.keysAreValid():
            self.threadsPrivate[0].agg = choice  # needed to update the orderdict structure
            self.threadsPrivate[0].updateLadderOrders()  # refreshes the data
        self.dom.center()

    def cancelAllOrders(self):
        if self.private_active:
            self.execution.cancelAll(self.contract)

    def resetVolumeProfile(self):
        self.dom.threadsPublic[0].clearVolumeProfile()
        self.reset_volume_profile_button.releaseKeyboard()

    def handleSoundSignals(self, sound_type):
        """
        sound type can be fills, order_fail,
        """
        self.sound_signal.emit(sound_type)

    def closeThreads(self):
        self.dom.threadsPublic[0].stop()
        time.sleep(.2)
        try:
            self.threadsPrivate[0].stop()
        except Exception as e:
            pass
            #print(f'close private {e}')

    def closeEvent(self, event):
        self.closeThreads()
        event.accept()




def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    form = DomWindow()
    form.show()
    app.exec_()


if __name__ == '__main__':
    main()
