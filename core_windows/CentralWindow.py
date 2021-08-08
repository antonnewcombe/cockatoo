#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import PyQt5.QtWidgets
import PyQt5.QtCore
import PyQt5.QtGui

import sys
import json
import os
import time
import re
import numpy as np
from functools import partial
from collections import defaultdict
import pandas as pd

from core_windows.Dom import DomWindow
from app_styles.AppStyles import quote_board_colors
from api_handler.DataManager import HttpCleaner
from api_handler.RestAPIs import ftxAPI
from ws_streams.Runnables import httpRequestPublicThread, httpRequestPrivateThread, WebsocketThread
from utils.SoundEffects import SoundEffects
from utils.utilfunc import aggregateTriggerOrders
from custom_qt.CustomWidgets import (CustomButtonClass, ComboBox, TableWidgetItem, ListSlider, Toggle)
from custom_qt.CustomModels import (CheckablePandasModel, DataFrameModel)
from custom_qt.CustomDelegates import (MarketQuoteBoardDelegate, LastQuoteBoardDelegate, MarginQuoteBoardDelegate,
                                   BasisQuoteBoardDelegate, AlignDelegate, StyleActivityCells)
from utils.defines import SoundOptions
from utils.defines import EmptySettings

exchanges = ['FTX']

class SoundSettings(PyQt5.QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QDialog {background-color: white; color : black;}")  # font-size:15px
        self.setWindowTitle('Sound Settings')

        self.setMinimumSize(630, 50)

        options = SoundOptions.keys()
        current_choices = self.parent().settings['sounds']
        #handle where the key is missing from the settings file
        current_choices = {**current_choices,
                           **{option: {'file': ''} for option in options if
                              option not in current_choices.keys()}}
        self.parent().settings['sounds'] = current_choices

        layout = PyQt5.QtWidgets.QGridLayout()

        self.widget_dict = {}
        for i, option in enumerate(options):
            # label of the sound setting
            display_name = SoundOptions[option]['name']
            label = PyQt5.QtWidgets.QLabel(f'{display_name}:')
            # line of users current selected sound
            selected_sound = os.path.split(current_choices[option]['file'])[-1]
            choice = PyQt5.QtWidgets.QLineEdit(selected_sound)
            choice.setReadOnly(True)
            # browse system sounds
            browse_button = PyQt5.QtWidgets.QPushButton('Browse')
            browse_button.clicked.connect(lambda state, option=option: self.openDialog(option))
            # test sound button
            test_button = PyQt5.QtWidgets.QPushButton()
            test_button.clicked.connect(lambda state, option=option: self.testSound(option))
            test_button.setIcon(PyQt5.QtGui.QIcon('assets/speaker.svg'))
            if not selected_sound:
                test_button.setEnabled(False)

            # test_button.setIcon()
            layout.addWidget(label, i, 0)
            layout.addWidget(choice, i, 1)
            layout.addWidget(browse_button, i, 2)
            layout.addWidget(test_button, i, 3)

            self.widget_dict[option] = {}
            self.widget_dict[option]['label'] = label
            self.widget_dict[option]['choice'] = choice
            self.widget_dict[option]['browse_button'] = browse_button
            self.widget_dict[option]['test_button'] = test_button

        close_button = PyQt5.QtWidgets.QPushButton('Close')
        close_button.clicked.connect(lambda: self.close())
        layout.addWidget(close_button, len(options), 3)
        self.widget_dict['Close Button'] = close_button

        self.setLayout(layout)

    def openDialog(self, option):

        filter = 'Wav File (*.wav)'
        choice, _ = PyQt5.QtWidgets.QFileDialog.getOpenFileName(self, 'Sound Files', 'assets/sounds/', filter)
        if self.parent:
            'open diaglog'
            self.parent().settings['sounds'][option]['file'] = choice
        else:
            self.settings['sounds'][option]['file'] = choice
        if choice:
            # enable the test button
            self.widget_dict[option]['test_button'].setEnabled(True)
        else:
            # enable the test button
            self.widget_dict[option]['test_button'].setEnabled(False)

        self.widget_dict[option]['choice'].setText(os.path.split(choice)[-1])

    def testSound(self, option):
        if self.parent:
            file = self.parent().settings['sounds'][option]['file']
        else:
            file = self.settings['sounds'][option]['file']
        SoundEffects.play(file)


class ThemeSettings(PyQt5.QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QDialog {background-color: white; color : black;}")  # font-size:15px
        self.setWindowTitle('Background Settings')

        self.setMinimumSize(630, 50)

        options = ['background', 'frame']
        current_choices = self.parent().settings['themes']
        layout = PyQt5.QtWidgets.QGridLayout()

        self.widget_dict = {}
        for i, option in enumerate(options):
            # label of the sound setting
            label = PyQt5.QtWidgets.QLabel(f'{option}:')
            # line of users current selected sound
            selected_sound = os.path.split(current_choices[option])[-1]
            choice = PyQt5.QtWidgets.QLineEdit(selected_sound)
            choice.setReadOnly(True)
            # browse system sounds
            browse_button = PyQt5.QtWidgets.QPushButton('Browse')
            browse_button.clicked.connect(lambda state, option=option: self.openDialog(option))
            # test sound button
            test_button = PyQt5.QtWidgets.QPushButton('Update')
            test_button.clicked.connect(lambda state, option=option: self.updateImage(option))
            layout.addWidget(label, i, 0)
            layout.addWidget(choice, i, 1)
            layout.addWidget(browse_button, i, 2)
            layout.addWidget(test_button, i, 3)

            self.widget_dict[option] = {}
            # self.widget_dict[option]['checkbox'] = enable_sound
            self.widget_dict[option]['label'] = label
            self.widget_dict[option]['choice'] = choice
            self.widget_dict[option]['browse_button'] = browse_button
            self.widget_dict[option]['test_button'] = test_button

        close_button = PyQt5.QtWidgets.QPushButton('Close')
        close_button.clicked.connect(lambda: self.closeUpdate())
        layout.addWidget(close_button, len(options), 3)
        self.widget_dict['Close Button'] = close_button

        self.setLayout(layout)

    def openDialog(self, option):

        filter = 'Images (*.jpg *.jpeg *png)'
        choice, _ = PyQt5.QtWidgets.QFileDialog.getOpenFileName(self, 'Image Files', 'assets', filter)
        info = PyQt5.QtCore.QFileInfo(choice)
        if info.size() <= 500_000:
            if self.parent:
                self.parent().settings['themes'][option] = choice
            else:
                self.settings['themes'][option] = choice

            self.widget_dict[option]['choice'].setText(os.path.split(choice)[-1])
        else:
            self.widget_dict[option]['choice'].setText('File Size Must Be Smaller Than 500kb')

    def updateImage(self, option):
        self.parent().updateSettings('themes', self.parent().settings['themes'])

    def closeUpdate(self):
        self.parent().updateSettings('themes', self.parent().settings['themes'])
        self.close()


class DomSettings(PyQt5.QtWidgets.QDialog):
    def __init__(self, parent=None, markets=None, settings=None):
        super().__init__(parent)

        """
        settings = {'dom_settings': {'button_values' : {'ETH-PERP' : [0.001, 0.01, 0.1, 0.5, 2, 10],
                                     'default': [0.001, 0.01, 0.1, 0.5, 1, 10]
                                     },
                                     'aggregation_levels' : {'ETH-PERP' : [0.5, 1, 2, 2.5, 5, 10, 20],
                                     'default' : [0.00025, 0.001, 0.0025, 0.005, 0.01, ....]}
                            }}
        
        markets = [list of all markets]
        
        """

        self.setStyleSheet("QDialog {background-color: white; color : black;}")  # font-size:15px
        self.setWindowTitle('Dom Settings')
        self.setStyleSheet("""
        MainWindow{background-color: #e6dddc; }
        QListView{background-color:  #ffe0cc; color:black; font: bold;}
        QListView:item:hover{background-color:  #ffe0cc; color:#364b70; font: bold;}
        QListView:item:text{border-style: dot-dash;}
        QListView:item{background-color:  #ffe0cc; color:black;  font: bold;}
        QLineEdit {background-color: white; color: black; font: bold}
        """)

        self.markets = markets
        self.selected = markets[0]

        self.settings = settings

        layout = PyQt5.QtWidgets.QGridLayout()

        self.order_quantity_label = PyQt5.QtWidgets.QLineEdit('Order Quantity Settings')
        self.order_quantity_label.setReadOnly(True)

        hlayout = PyQt5.QtWidgets.QHBoxLayout()

        self.market_combo_box = ComboBox()
        self.market_view = PyQt5.QtWidgets.QListView()
        self.market_combo_box.setView(self.market_view)
        self.market_combo_box.addItems(self.markets)
        self.market_combo_box.currentIndexChanged.connect(self.displayCurrentSettings)
        hlayout.addWidget(self.market_combo_box)

        # 5 qlineedits for entering in order quantity values
        self.order_row_widgets = {}
        order_quantity_row = PyQt5.QtWidgets.QHBoxLayout()
        for i in range(6):
            self.order_row_widgets[str(i)] = PyQt5.QtWidgets.QLineEdit()
            self.order_row_widgets[str(i)].setAlignment(PyQt5.QtCore.Qt.AlignCenter)
            self.order_row_widgets[str(i)].textChanged.connect(
                lambda text, i=i: self.handleOrderChanges(text, i))
            order_quantity_row.addWidget(self.order_row_widgets[str(i)])

        self.aggregation_label = PyQt5.QtWidgets.QLineEdit('Aggregation Level Options')
        self.aggregation_label.setMinimumWidth(200)
        self.aggregation_label.setReadOnly(True)
        self.aggregation_values = PyQt5.QtWidgets.QLineEdit('')
        self.aggregation_values.textChanged.connect(self.handleAggregationChanges)

        self.displayCurrentSettings(0)  # init
        layout.addLayout(hlayout, 0, 0, PyQt5.QtCore.Qt.AlignLeft)
        # layout.addWidget(self.market_combo_box, 0, 0)
        layout.addWidget(self.order_quantity_label, 1, 0)
        layout.addLayout(order_quantity_row, 1, 1)

        layout.addWidget(self.aggregation_label, 2, 0)
        layout.addWidget(self.aggregation_values, 2, 1)

        save_button = PyQt5.QtWidgets.QPushButton('Save')
        save_button.clicked.connect(self.saveSettings)
        layout.addWidget(save_button, 3, 1, PyQt5.QtCore.Qt.AlignRight)

        self.setLayout(layout)

    def displayCurrentSettings(self, index):
        self.populateMarketChoice(index)
        self.populateAggregationValues(index)

    def populateMarketChoice(self, index):
        self.selected = self.markets[index]

        use = 'default' if self.selected not in self.settings['dom_settings']['button_values'].keys() else self.selected
        quantities = self.settings['dom_settings']['button_values'][use]
        for i, value in enumerate(quantities):
            self.order_row_widgets[str(i)].setText(str(value))

    def populateAggregationValues(self, index):
        selected = self.markets[index]
        use = 'default' if selected not in self.settings['dom_settings']['aggregation_levels'].keys() else selected
        levels = self.settings['dom_settings']['aggregation_levels'][use]
        string_values = ', '.join(list(map(str, levels)))
        self.aggregation_values.setText(string_values)

    def handleOrderChanges(self, text, i):

        if self.selected not in self.settings['dom_settings']['button_values'].keys():
            self.settings['dom_settings']['button_values'][self.selected] = \
                EmptySettings['dom_settings']['button_values']['default']
        try:
            new_value = float(text)

            self.settings['dom_settings']['button_values'][self.selected][i] = new_value
            self.parent().updateSettings('dom_settings', self.settings['dom_settings'])
            self.order_row_widgets[str(i)].setStyleSheet(
                "QLineEdit {background-color: white; color: black; font: bold}")

        except Exception as e:
            self.order_row_widgets[str(i)].setStyleSheet(
                "QLineEdit {background-color: #FF3A66; color: white; font: bold}")

    def handleAggregationChanges(self, text):
        if self.selected not in self.settings['dom_settings']['aggregation_levels'].keys():
            self.settings['dom_settings']['aggregation_levels'][self.selected] = \
                self.settings['dom_settings']['aggregation_levels']['default']
        try:
            levels = list(map(float, text.split(',')))
            self.settings['dom_settings']['aggregation_levels'][self.selected] = levels
            self.parent().updateSettings('dom_settings', self.settings['dom_settings'])
            self.aggregation_values.setStyleSheet("QLineEdit {background-color: white; color: black; font: bold}")
        except Exception as e:
            self.aggregation_values.setStyleSheet("QLineEdit {background-color: #FF3A66; color: white; font: bold}")

    def saveSettings(self):
        self.parent().updateSettings('dom_settings', self.settings['dom_settings'])
        self.close()
        pass


class FileDialog(PyQt5.QtWidgets.QFileDialog):
    def __init__(self):
        super().__init__()


class SearchBox(PyQt5.QtWidgets.QLineEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QLineEdit {background-color: white; color : black;}")  # font-size:15px
        self.setText('Search Markets')
        self.searched = False

    def mousePressEvent(self, event):
        self.setText('')

    def keyPressEvent(self, event):
        # clear text on first time keyboard is pressed
        if not self.searched:
            self.setText('')
            self.searched = True
        return super(SearchBox, self).keyPressEvent(event)


class APIForm(PyQt5.QtWidgets.QGroupBox):
    def __init__(self, exchange, publicKey='', privateKey=''):
        super().__init__()
        self.setStyleSheet("""APIForm {background-color:  white; color : black; font-size:11px;}
                              QLineEdit {background-color:  white; color : black; font-size:11px;}
                              QLabel {color : black; font-size:11px;}""")
        self.exchange = exchange
        self.publicKey = publicKey
        self.privateKey = privateKey
        self.setTitle(self.exchange)

        layout = PyQt5.QtWidgets.QFormLayout()

        self.publicEntry = PyQt5.QtWidgets.QLineEdit(self.publicKey)
        self.publicEntry.textChanged.connect(lambda text: self.storeKeys('public', text))
        layout.addRow(PyQt5.QtWidgets.QLabel('API Public Key'), self.publicEntry)

        self.privateEntry = PyQt5.QtWidgets.QLineEdit(self.privateKey)
        self.privateEntry.textChanged.connect(lambda text: self.storeKeys('private', text))
        layout.addRow(PyQt5.QtWidgets.QLabel('API Private Key'), self.privateEntry)

        self.testButton = PyQt5.QtWidgets.QPushButton('Test')
        self.testButton.clicked.connect(self.testAPI)
        self.testOutput = PyQt5.QtWidgets.QLineEdit()
        layout.addRow(self.testButton, self.testOutput)

        self.setLayout(layout)

    def areKeysValid(self):
        api = HttpCleaner({'FTX': {'public': self.publicKey, 'private': self.privateKey}})
        flag = api.testValidKeys(self.publicKey, self.privateKey)
        return flag

    def testAPI(self):
        keys = defaultdict(lambda: defaultdict(str))
        keys[self.exchange]['public'] = self.publicKey
        keys[self.exchange]['private'] = self.privateKey
        keys_valid = self.areKeysValid()
        if keys_valid:
            self.testOutput.setText('Success')
            self.testOutput.setStyleSheet("QLineEdit {background-color: #05BD7A; color: white; font: bold}")
        else:
            self.testOutput.setText('Fail - Invalid keys not saved')
            self.publicKey = ''
            self.privateKey = ''
            self.testOutput.setStyleSheet("QLineEdit {background-color: #FF3A66; color: white; font: bold}")

    def storeKeys(self, key_type, text):

        if key_type == 'public':
            self.publicKey = text
        elif key_type == 'private':
            self.privateKey = text

class APISaveKeysSection(PyQt5.QtWidgets.QWidget):
    def __init__(self,save=False):
        super().__init__(parent=None)
        self.setStyleSheet("QLabel {color: red, font: bold}")
        #main_layout = PyQt5.QtWidgets.QVBoxLayout()
        layout = PyQt5.QtWidgets.QGridLayout()
        save_keys_str = 'Save Keys In Settings File?'
        warning_str_1 = 'Warning this will save the keys in a readable settings file in the folder!'
        warning_str_2 = 'Do not use if anyone else uses your computer!'
        layout.addWidget(PyQt5.QtWidgets.QLabel(save_keys_str), 0, 0)
        self.toggle = Toggle("Yes", "No", check_status=save)
        self.toggle.setStyleSheet("")
        layout.addWidget(self.toggle, 0, 1, PyQt5.QtCore.Qt.AlignRight)
        #main_layout.addLayout(layout)
        warning_label_1 = PyQt5.QtWidgets.QLabel(warning_str_1)
        warning_label_2 = PyQt5.QtWidgets.QLabel(warning_str_2)
        self.continue_button = PyQt5.QtWidgets.QPushButton('Continue')
        layout.addWidget(warning_label_1, 1, 0)
        layout.addWidget(warning_label_2, 2, 0)
        layout.addWidget(self.continue_button, 3, 1, PyQt5.QtCore.Qt.AlignRight)

        self.setLayout(layout)


class APIKeyManager(PyQt5.QtWidgets.QDialog):
    key_update_signal = PyQt5.QtCore.pyqtSignal(str, dict, bool)

    def __init__(self, parent=None, exchanges=['FTX']):

        super().__init__(parent)
        self.setStyleSheet("QDialog {background-color: white; color : black; font-size:11px;}")
        self.exchanges = exchanges
        self.setWindowTitle('API Key Manager')

        self.setFixedWidth(600)
        if parent:
            self.key_settings = self.initSettings(self.parent().settings['keys'], exchanges)
        else:
            self.key_settings = self.initSettings({}, exchanges)
        self.api_form = {}

        self.main_layout = PyQt5.QtWidgets.QGridLayout()

        public = self.key_settings['FTX']['public']
        private = self.key_settings['FTX']['private']
        self.api_form['FTX'] = APIForm('FTX', public, private)
        self.main_layout.addWidget(self.api_form['FTX'], 0, 0)

        self.main_layout.setColumnStretch(0, 1)
        self.save_choice = APISaveKeysSection(self.key_settings['FTX']['save_keys_in_settings_file'])
        self.save_choice.continue_button.clicked.connect(self.setAPIKeys)
        #save_button = PyQt5.QtWidgets.QPushButton('Save')
        #save_button.clicked.connect(self.setAPIKeys)
        #self.main_layout.addWidget(save_button, len(exchanges), 1, PyQt5.QtCore.Qt.AlignRight)

        self.main_layout.addWidget(self.save_choice)

        self.setLayout(self.main_layout)

    def initSettings(self, settings, exchanges, key_types=['private', 'public']):
        for exchange in exchanges:
            if exchange not in settings.keys():
                settings[exchange] = {}

            for key in key_types:
                if key not in settings[exchange].keys():
                    settings[exchange][key] = ''
        return settings

    def setAPIKeys(self):

        keys = {}
        for exchange in self.exchanges:
            keys[exchange] = {}
            if self.api_form[exchange].areKeysValid():
                keys[exchange]['public'] = self.api_form[exchange].publicKey
                keys[exchange]['private'] = self.api_form[exchange].privateKey
                valid = True
            else:
                keys[exchange]['public'] = ''
                keys[exchange]['private'] = ''
                valid = False
            keys[exchange]['save_keys_in_settings_file'] = self.save_choice.toggle.isChecked()
        self.key_update_signal.emit('keys', keys, valid)


class SubscriptionDialog(PyQt5.QtWidgets.QDialog):
    trade_sub_update_signal = PyQt5.QtCore.pyqtSignal(list)

    def __init__(self, parent=None, name=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle(name)

        self.okButton = PyQt5.QtWidgets.QPushButton('OK')
        self.cancelButton = PyQt5.QtWidgets.QPushButton('Cancel')
        self.okButton.clicked.connect(self.onAccepted)
        self.cancelButton.clicked.connect(self.reject)

        self.tree_section = TreeSection(self, settings=settings, market_list='trade_subs')

        hbox = PyQt5.QtWidgets.QHBoxLayout()
        hbox.addWidget(self.okButton)
        hbox.addWidget(self.cancelButton)

        vbox = PyQt5.QtWidgets.QVBoxLayout()
        vbox.addWidget(self.tree_section)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

    def onAccepted(self):
        self.choices = self.tree_section.treeWidget.fav_settings['FTX']
        self.accept()
        self.trade_sub_update_signal.emit(self.choices)

class ActivityWindow(PyQt5.QtWidgets.QTableWidget):
    def __init__(self):
        super().__init__()
        color, background = quote_board_colors['header']['color'], quote_board_colors['header']['background']
        self.setStyleSheet("QHeaderView:section {" + f'color:{color}; background-color:{background};' + 'font:bold}')
        self.setRowCount(0)
        self.colnames = ['Time', 'Market', 'Price', 'USD']
        self.columns = ['time', 'market', 'price', 'USD']
        self.setColumnCount(len(self.columns))

        for i, col in enumerate(self.colnames):
            self.setHorizontalHeaderItem(i, TableWidgetItem(col))

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(16)

        self.horizontalHeader().setSectionResizeMode(len(self.columns)-1, PyQt5.QtWidgets.QHeaderView.Stretch)


class ActivityWindowSection(PyQt5.QtWidgets.QWidget):
    update_trade_sub_signal = PyQt5.QtCore.pyqtSignal(str, dict)
    play_sound_signal = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.display_count = 0 #for resize on first trade data
        self.settings = settings
        self.markets = self.parent().available_markets['FTX']
        self.selections = self.settings['trade_subs']['FTX']
        frame_image = self.settings['themes']['frame']
        self.setStyleSheet("QTableWidget {background-color: white; gridline-color: #76458a; border:1px solid black}"
                           "QScrollBar {height:0px;}"
                           ".QFrame {background-color: #e6dddc; background-image: " + f"url({frame_image})" + "}")
        self.frame = PyQt5.QtWidgets.QFrame()
        self.frame.setFrameShape(PyQt5.QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(PyQt5.QtWidgets.QFrame.Raised)

        layout = PyQt5.QtWidgets.QGridLayout()
        button_layout = PyQt5.QtWidgets.QHBoxLayout()
        # insert row
        activity_settings_button = PyQt5.QtWidgets.QPushButton()
        activity_settings_button.clicked.connect(self.launchSettings)
        activity_settings_button.setIcon(PyQt5.QtGui.QIcon('assets/banana.svg'))
        button_layout.addWidget(activity_settings_button)
        layout.addLayout(button_layout, 0, 0, PyQt5.QtCore.Qt.AlignLeft)
        self.activity_window = ActivityWindow()
        self.activity_window.horizontalScrollBar().setEnabled(False)
        window_layout = PyQt5.QtWidgets.QVBoxLayout(self.frame)

        window_layout.addWidget(self.activity_window)
        window_layout.setStretch(0, 1)
        layout.addWidget(self.frame)

        self.setLayout(layout)

        self.startTradeThread()

    def startTradeThread(self):
        self.threads = []
        self.pool = PyQt5.QtCore.QThreadPool()

        downloader = WebsocketThread(markets=self.selections)
        downloader.signals.trades_signal.connect(self.populateWindow)
        self.pool.start(downloader)
        self.threads.append(downloader)

    def populateWindow(self, data):
        for trade in data:
            row_position = self.activity_window.rowCount()  # - 100
            self.activity_window.insertRow(row_position)
            for i, col in enumerate(self.activity_window.columns):
                cell = StyleActivityCells(trade, col)
                if trade['type'][0] == 'liq':
                    self.play_sound_signal.emit('liquidation')
                self.activity_window.setItem(row_position, i, cell)
            self.activity_window.resizeRowToContents(row_position)
            self.activity_window.scrollToItem(self.activity_window.item(row_position, 0))
            self.activity_window.selectRow(
                row_position)  # this and below line ensure the table is fully scrolled to the bottom.doesnt work otherwise
            self.activity_window.clearSelection()
        if self.display_count == 0 and data: #data can be empty list
            self.activity_window.resizeColumnToContents(0)
            self.display_count += 1

    def launchSettings(self):

        self.trade_sub_dialog = SubscriptionDialog(self,
                                                   name='Trade Subscriptions',
                                                   settings=self.settings)
        self.trade_sub_dialog.trade_sub_update_signal.connect(partial(self.updateSettings))
        self.trade_sub_dialog.exec_()

    def updateSettings(self, data):
        self.update_trade_sub_signal.emit('trade_subs', {'FTX': data})
        subbed_markets = [sub['market'] for sub in self.threads[0].stream._subscriptions]
        for sub in data:
            if sub not in subbed_markets:
                self.threads[0].stream.get_trades(sub)
        for subbed in subbed_markets:
            if subbed not in data:
                self.threads[0].stream._unsubscribe({'channel': 'trades', 'market': subbed})

    def updateStyle(self, image):
        self.setStyleSheet("QTableWidget {background-color: white; gridline-color: #76458a; border:1px solid black}"
                           "QScrollBar {height:0px;}"
                           ".QFrame {background-color: #e6dddc; background-image: " + f"url({image})" + "}")

    def close(self):
        for thread in self.threads:
            thread.stop()
            time.sleep(0.1)

    def closeEvent(self, event):
        self.close()

class TreeWidget(PyQt5.QtWidgets.QTreeWidget):
    """
    widget used in the dom launch window and the trade subscription window
    """
    open_market_signal = PyQt5.QtCore.pyqtSignal(str, str, dict)

    def __init__(self, parent=None, market_list='favourites'):
        super().__init__(parent)
        # launchable is flag for using either market explorer or tradesubscription
        launchable = True if market_list == 'favourites' else False
        self.setStyleSheet("QHeaderView {background-color: white}"
                           "QTreeWidget:indicator:checked {image: url(assets/Citrus2.svg)} "
                           "QTreeWidget:indicator:unchecked {image: url(assets/Citrus_unchecked.svg)};")

        self.market_list = market_list
        if parent:
            self.par = self.parent()
            while self.par is not None and not isinstance(self.par, Window):
                self.par = self.par.parent()
            self.fav_settings = self.initSettings(self.par.settings[self.market_list], exchanges)
        else:
            self.fav_settings = self.initSettings({}, exchanges)

        self.itemClicked.connect(self.handleItemClick)

        cleaner = HttpCleaner(ignore_account=True)
        self.availableMarkets = cleaner.availableMarkets()
        self.setColumnCount(2)
        # description font
        description_font = PyQt5.QtGui.QFont()
        description_font.setPointSize(7)
        description_font.setItalic(True)
        symbol_font = PyQt5.QtGui.QFont()
        symbol_font.setBold(True)
        self.exchange_markets = {}
        for exchange, markets in self.availableMarkets.items():
            self.exchange_markets[exchange] = []
            for market, data in markets.items():
                self.exchange_markets[exchange].append(market)
                parent = PyQt5.QtWidgets.QTreeWidgetItem([market])
                # change the colors of the text fields
                parent.setForeground(0, PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor('#000000')))
                parent.setFont(0, symbol_font)
                parent.setFlags(parent.flags() | PyQt5.QtCore.Qt.ItemIsUserCheckable)
                parent.setTextAlignment(PyQt5.QtCore.Qt.AlignLeft, PyQt5.QtCore.Qt.AlignLeft)
                check_state = PyQt5.QtCore.Qt.Checked if market in self.fav_settings[
                    exchange] else PyQt5.QtCore.Qt.Unchecked
                parent.setCheckState(0, check_state)
                if data['description']:
                    child = PyQt5.QtWidgets.QTreeWidgetItem([data['description']])
                    child.setFont(0, description_font)
                    child.setForeground(0, PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor('#757474')))

                    parent.addChild(child)
                self.addTopLevelItem(parent)
        self.setRootIsDecorated(False)
        self.setHeaderHidden(True)
        if launchable:
            # this widget is also used for the trade subscription settings window where we dont want to launch ladders
            self.itemDoubleClicked.connect(self.openWindow)
        self.expandAll()
        for i in range(self.columnCount()):
            self.resizeColumnToContents(i)

        self.horizontalScrollBar().hide()

    def createHeader(self):
        columns = ['Market', 'Description']
        self.setColumnCount(len(columns))
        HeaderItem = self.headerItem()
        for i, col in enumerate(columns):
            HeaderItem.setText(i, col)

    def initSettings(self, settings, exchanges):

        for exchange in exchanges:
            if exchange not in settings.keys():
                settings[exchange] = []
        return settings

    def openWindow(self, item):
        exchange = 'FTX'
        contract = item.text(0)
        if contract in self.exchange_markets['FTX']:
            specs = self.availableMarkets['FTX'][item.text(0)]
            self.open_market_signal.emit(exchange, contract, specs)

    def handleItemClick(self, item, column):

        self.fav_settings = self.par.settings[self.market_list]
        exchange = 'FTX'
        if not item.parent():
            market = item.text(0)
            if item.checkState(column) == PyQt5.QtCore.Qt.Checked:
                if market not in self.fav_settings[exchange]:
                    self.fav_settings[exchange].append(market)
            elif item.checkState(column) == PyQt5.QtCore.Qt.Unchecked:
                if market in self.fav_settings[exchange]:
                    self.fav_settings[exchange].remove(market)

        self.par.settings[self.market_list] = self.fav_settings


class TreeSection(PyQt5.QtWidgets.QWidget):
    def __init__(self, parent=None, settings=None, market_list='favourites'):
        super().__init__(parent)
        self.settings = settings
        frame_image = settings['themes']['frame']
        self.setStyleSheet(".QFrame {background-color: #e6dddc; background-image: " + f"url({frame_image})" + "}"
                           "TreeWidget {background-color: white;}")

        layout = PyQt5.QtWidgets.QGridLayout()
        hor_layout = PyQt5.QtWidgets.QHBoxLayout()
        self.searchBox = SearchBox()
        self.searchBox.textChanged.connect(self.filterTree)
        self.treeWidget = TreeWidget(self, market_list=market_list)
        self.favourites_checkbox = PyQt5.QtWidgets.QPushButton()
        self.filter_favourites = False
        self.favourites_checkbox.setIcon(PyQt5.QtGui.QIcon('assets/Citrus_unchecked.svg'))
        self.favourites_checkbox.clicked.connect(self.filterFavourites)

        self.frame = PyQt5.QtWidgets.QFrame()
        self.frame.setFrameShape(PyQt5.QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(PyQt5.QtWidgets.QFrame.Raised)
        tree_layout = PyQt5.QtWidgets.QVBoxLayout(self.frame)
        tree_layout.addWidget(self.treeWidget)

        hor_layout.addWidget(self.searchBox)
        hor_layout.addWidget(self.favourites_checkbox)
        layout.addLayout(hor_layout, 0, 0)
        layout.addWidget(self.frame, 1, 0)
        self.setLayout(layout)

    def filterTree(self, text):

        text = text.lower()
        for i in range(self.treeWidget.topLevelItemCount()):
            root = self.treeWidget.topLevelItem(i)
            if root.child(0):
                condition = text in root.text(0).lower() or text in root.child(0).text(0).lower()
            else:
                # there is no description
                condition = text in root.text(0).lower()

            if condition:
                root.setHidden(False)
            else:
                root.setHidden(True)
            root.setExpanded(True)

    def filterFavourites(self):
        self.filter_favourites = True if self.filter_favourites == False else False  # switch the button pseudo state
        if self.filter_favourites:
            self.favourites_checkbox.setIcon(PyQt5.QtGui.QIcon('assets/Citrus2.svg'))
            for i in range(self.treeWidget.topLevelItemCount()):
                root = self.treeWidget.topLevelItem(i)
                if root.checkState(0) == PyQt5.QtCore.Qt.Checked:
                    root.setHidden(False)
                else:
                    root.setHidden(True)
        else:
            self.favourites_checkbox.setIcon(PyQt5.QtGui.QIcon('assets/Citrus_unchecked.svg'))
            self.filterTree('')

    def updateStyle(self, image):
        self.setStyleSheet(".QFrame {background-color: #e6dddc; background-image: " + f"url({image})" + "}"
                           "TreeWidget {background-color: white;}")


class QuoteTab(PyQt5.QtWidgets.QWidget):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setStyleSheet(".QTabBar:tab {margin: 0px; padding: -2px -2px -2x 10px; max-width: 2em; min-width: 2em}")
        layout = PyQt5.QtWidgets.QGridLayout()
        self.quote_tab = PyQt5.QtWidgets.QTabWidget()
        self.quote_tab.setContentsMargins(0, 0, 0, 0)
        self.quote_tab.setTabPosition(1)

        # balances
        custom_tab = PyQt5.QtWidgets.QWidget()
        custom_layout = PyQt5.QtWidgets.QVBoxLayout()

        self.custom_table = QuoteBoard(self, settings=settings)  # coin, balance, available balance, USD value
        self.custom_table.verticalHeader().setVisible(False)
        custom_layout.addWidget(self.custom_table)
        custom_tab.setLayout(custom_layout)
        self.quote_tab.addTab(custom_tab, PyQt5.QtGui.QIcon('assets/ch.png'), '')

        layout.addWidget(self.quote_tab, 0, 0)

        master_tab = PyQt5.QtWidgets.QWidget()
        master_tab.setContentsMargins(0, 0, 0, 0)
        self.master_table = MasterQuoteBoard()
        master_layout = PyQt5.QtWidgets.QVBoxLayout()
        master_layout.addWidget(self.master_table)
        master_tab.setLayout(master_layout)
        self.quote_tab.addTab(master_tab, PyQt5.QtGui.QIcon('assets/ch_light.svg'), '')
        self.quote_tab.setIconSize(PyQt5.QtCore.QSize(19, 26))
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)


class MasterQuoteBoard(PyQt5.QtWidgets.QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        color, background = quote_board_colors['header']['color'], quote_board_colors['header']['background']
        self.setStyleSheet("QHeaderView:section {" + f'color:{color}; background-color:{background};' + 'font:bold}')
        self.columns = ['name', 'last', 'index', 'basis', 'rate', 'change1h', 'change24h', 'volumeUsd24h',
                        'lend_estimate_APY']
        self.colnames = ['Market', 'Last', 'Index', 'Basis', 'Funding', '1hrΔ',
                         '24hrΔ', '24hr USD', 'Lend APY']
        self.mapping = {k: v for k, v in zip(self.columns, self.colnames)}

        init_frame = np.full((100, len(self.columns)), '-')
        self.model = DataFrameModel(df=pd.DataFrame(init_frame, columns=self.columns), mapping=self.mapping)
        self.view = PyQt5.QtWidgets.QTableView()
        self.proxy = PyQt5.QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.view.setModel(self.proxy)

        self.view.setShowGrid(False)

        market_delegate = MarketQuoteBoardDelegate(self.view)
        self.view.setItemDelegateForColumn(0, market_delegate)
        last_delegate = LastQuoteBoardDelegate(self.view)
        self.view.setItemDelegateForColumn(1, last_delegate)
        self.view.setItemDelegateForColumn(2, last_delegate)
        basis_delegate = BasisQuoteBoardDelegate(self.view)
        self.view.setItemDelegateForColumn(3, basis_delegate)
        self.view.setItemDelegateForColumn(4, basis_delegate)
        self.view.setItemDelegateForColumn(5, basis_delegate)
        self.view.setItemDelegateForColumn(6, basis_delegate)
        self.view.setItemDelegateForColumn(7, last_delegate)
        margin_delegate = MarginQuoteBoardDelegate()
        self.view.setItemDelegateForColumn(8, margin_delegate)

        self.view.horizontalHeader().setSectionResizeMode(len(self.columns)-1, PyQt5.QtWidgets.QHeaderView.Stretch)

        self.view.verticalHeader().hide()
        self.view.verticalHeader().setDefaultSectionSize(18)
        self.view.setVerticalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOff)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, PyQt5.QtCore.Qt.SortOrder.AscendingOrder)

        layout = PyQt5.QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

    def displayQuotes(self, df):
        df = df[self.columns]
        self.model.setDataFrame(df)


class QuoteBoard(PyQt5.QtWidgets.QTableWidget):
    quote_board_signal = PyQt5.QtCore.pyqtSignal(str, dict)

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setRowCount(len(settings))
        self.parent = parent
        color, background = quote_board_colors['header']['color'], quote_board_colors['header']['background']
        self.setStyleSheet("QHeaderView:section {" + f'color:{color}; background-color:{background};' + 'font:bold}')
        self.columns = ['exchange:market', 'last', 'basis', 'rate', 'change1h', 'change24h', 'volumeUsd24h']
        self.colnames = ['Market', 'Last', 'Basis', 'Funding', '1hrΔ',
                         '24hrΔ', '24hr USD', 'Lend APY']
        self.setColumnCount(len(self.columns))
        self.settings = settings

        self.display_count = 0

        self.setShowGrid(False)

        for i, col in enumerate(self.colnames):
            self.setHorizontalHeaderItem(i, PyQt5.QtWidgets.QTableWidgetItem(col))

        for row, value in settings.items():
            row = int(row)
            cell = PyQt5.QtWidgets.QTableWidgetItem(value)
            self.setItem(row, 0, cell)
            for col, heading in enumerate(self.columns[1:], 1):
                data_cell = PyQt5.QtWidgets.QTableWidgetItem('')
                data_cell.setTextAlignment(PyQt5.QtCore.Qt.AlignCenter)
                self.setItem(row, col, data_cell)

            self.resizeRowToContents(row)

        # hide the row numbers
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(16)

        self.setVerticalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOff)

        market_delegate = MarketQuoteBoardDelegate(self, defaultWidth=260)
        self.setItemDelegateForColumn(0, market_delegate)
        last_delegate = LastQuoteBoardDelegate(self)
        self.setItemDelegateForColumn(1, last_delegate)

        basis_delegate = BasisQuoteBoardDelegate(self)
        self.setItemDelegateForColumn(2, basis_delegate)
        self.setItemDelegateForColumn(3, basis_delegate)
        self.setItemDelegateForColumn(4, basis_delegate)
        self.setItemDelegateForColumn(5, basis_delegate)
        volume_delegate = LastQuoteBoardDelegate(self)
        self.setItemDelegateForColumn(6, volume_delegate)

        self.horizontalHeader().setSectionResizeMode(len(self.columns)-1, PyQt5.QtWidgets.QHeaderView.Stretch)

    def addSeperatorRow(self):
        if not self.selectedItems():
            row_to_insert = self.rowCount()
        else:
            row_to_insert = self.getSelectedRowsFast()
        self.insertRow(row_to_insert)
        for column in range(len(self.columns)):
            self.setItem(row_to_insert, column, TableWidgetItem(''))

    def delSeperatorRow(self):
        if not self.selectedItems():  # there is nothing selected
            if self.rowCount() > 1:
                self.removeRow(self.rowCount() - 1)
        else:
            index = self.getSelectedRowsFast()
            self.removeRow(index)

    def getSelectedRowsFast(self):
        selRows = []
        for item in self.selectedItems():
            if item.row() not in selRows:
                selRows.append(item.row())
        return selRows[0]

    def calcSpecialFormalas(self, df, formulas):
        df['name_adj'] = df['name'].apply(lambda x: x.replace('-', '_').replace('/', '_'))
        df = df.set_index('name_adj')
        numbers_df = df[['last', 'basis', 'rate', 'change1h', 'change24h', 'volumeUsd24h']]
        t = numbers_df.T
        df = df.reset_index()
        df = df.set_index('name')
        specials = pd.DataFrame()
        for k, v in formulas.items():
            temp = pd.DataFrame()
            try:
                temp[k] = pd.eval(v)
                temp.T['last'] = np.round(temp.T['last'], 6)
                specials = specials.append(temp.T)
            except:
                temp[k] = 'na'

        df = df.append(specials)
        return df

    def displayQuotes(self, df):
        formulas = {}
        for i in range(self.rowCount()):
            col1 = self.item(i, 0)
            if not col1:
                continue
            col1 = col1.text()
            col1 = self.item(i, 0).text()
            if col1.startswith('?'):
                # TODO make into 1 regex
                # substitues the '/' and '-' to in order to allow divide and subtract in special formula
                formula = re.sub(r'(\[[^\/\]]*)(\/)([^\/\]]*\])', r'\1_\3', col1)
                formula = re.sub(r'(\[[^-\]]*)(-)([^-\]]*\])', r'\1_\3', formula)
                for n, rep in [['?', ''], [']', ''], ['FTX:', ''], ['[', 't.']]:
                    formula = formula.replace(n, rep)
                formulas[col1] = formula
        df = self.calcSpecialFormalas(df, formulas)
        columns = ['exchange:market', 'last', 'basis', 'rate', 'change1h', 'change24h', 'volumeUsd24h']
        custom_markets = {}
        for row in range(self.rowCount()):
            col1 = self.item(row, 0)
            col1 = col1.text()
            custom_markets[str(row)] = col1

            if col1 != '':
                col1 = col1.replace('FTX:', '') if not col1.startswith('?') else col1
                col_end = 2 if col1.startswith('?') else len(columns)
                try:
                    for j, column in enumerate(columns[1:col_end], 1):
                        value = df.loc[col1][column]
                        if col1.startswith('~') or col1 == '':
                            value = ''

                        self.item(row, j).setText(str(value))
                except Exception as e:
                    pass

            else:
                for i in range(len(columns)):
                    cell = self.item(row, i)
                    if not cell:
                        continue
                    if cell.text() != '':
                        blank = PyQt5.QtWidgets.QTableWidgetItem('')
                        self.setItem(row, i, blank)

        if self.display_count == 0:
            #reize the first column
            self.resizeColumnToContents(0)
            self.display_count += 1

        if custom_markets != self.settings:
            self.quote_board_signal.emit('quoteboard', custom_markets)
            self.settings = custom_markets

    def close(self):
        for thread in self.threads:
            thread.stop()
            time.sleep(0.1)

    def closeEvent(self, event):
        self.close()


class QuoteBoardSection(PyQt5.QtWidgets.QWidget):

    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        frame_image = self.parent().settings['themes']['frame']
        self.setStyleSheet("QTabWidget:pane { border: 0; }"
                           ".QWidget {background-color: #e6dddc; background-image: " + f"url({frame_image})" + "}")
        self.parent = parent
        self.settings = settings
        layout = PyQt5.QtWidgets.QGridLayout()

        # get the current settings
        self.quote_settings = settings['quoteboard']
        self.quote_board = QuoteTab(settings=self.quote_settings)
        button_layout = PyQt5.QtWidgets.QHBoxLayout()
        # insert row
        add_row_button = CustomButtonClass('')
        add_row_button.setStyleSheet("""
                QPushButton{ background-color: white}
                """)
        add_row_button.setIcon(PyQt5.QtGui.QIcon('assets/coconut.svg'))
        add_row_button.left_clicked.connect(self.quote_board.custom_table.addSeperatorRow)
        add_row_button.right_clicked.connect(self.quote_board.custom_table.delSeperatorRow)
        button_layout.addWidget(add_row_button)
        layout.addLayout(button_layout, 0, 0, PyQt5.QtCore.Qt.AlignLeft)
        layout.addWidget(self.quote_board, 1, 0)

        self.setLayout(layout)
        self.quotesStream()

    def quotesStream(self):
        self.threads = []
        self.quote_thread_pool = PyQt5.QtCore.QThreadPool()
        downloader = httpRequestPublicThread(feed='quote_board')
        downloader.signals.quotes_signal.connect(self.updateQuoteBoard)
        self.threads.append(downloader)
        self.quote_thread_pool.start(downloader)

    def updateQuoteBoard(self, data):
        current_selected_tab = self.quote_board.quote_tab.currentIndex()
        if current_selected_tab == 0:
            self.quote_board.custom_table.displayQuotes(data)
        else:
            self.quote_board.master_table.displayQuotes(data)

    def updateStyle(self, image):
        self.setStyleSheet("QTabWidget:pane { border: 0; }"
                           ".QWidget {background-color: #e6dddc; background-image: " + f"url({image})" + "}")

    def close(self):
        for thread in self.threads:
            thread.stop()
            time.sleep(0.1)

    def closeEvent(self, event):
        self.close()


class AccountTableView(PyQt5.QtWidgets.QTableView):
    def __init__(self):
        super().__init__()
        color, background = quote_board_colors['header']['color'], quote_board_colors['header']['background']
        self.setStyleSheet("QTableView {font: bold}"
                           "QHeaderView:section {" + f'color:{color}; background-color:{background};' + 'font:bold}')
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(PyQt5.QtWidgets.QHeaderView.Stretch)
        self.verticalHeader().setDefaultSectionSize(16)


class AccountInfo(PyQt5.QtWidgets.QDialog):
    def __init__(self, parent=None, account_info=None):
        super().__init__(parent)
        self.setWindowTitle('Account Settings')
        heading_font = PyQt5.QtGui.QFont()
        heading_font.setBold(True)
        layout = PyQt5.QtWidgets.QVBoxLayout()
        # fees
        fees_layout = PyQt5.QtWidgets.QGridLayout()
        self.fees_text = PyQt5.QtWidgets.QLineEdit('Fees')
        self.fees_text.setReadOnly(True)
        self.fees_text.setFont(heading_font)

        if account_info:
            self.fees_taker = account_info['takerFee']
            self.fees_taker = f'{self.fees_taker: .5%}'
            self.fees_maker = account_info['makerFee']
            self.fees_maker = f'{self.fees_maker: .5%}'
        else:
            self.fees_taker = 'Not Logged In'
            self.fees_maker = 'Not Logged In'

        self.fees_maker_label = PyQt5.QtWidgets.QLabel('Maker Fees')
        self.fees_maker_val = PyQt5.QtWidgets.QLabel(self.fees_maker)
        self.fees_taker_label = PyQt5.QtWidgets.QLabel('Taker Fees')
        self.fees_taker_val = PyQt5.QtWidgets.QLabel(self.fees_taker)

        fees_layout.addWidget(self.fees_maker_label, 0, 0)
        fees_layout.addWidget(self.fees_maker_val, 0, 1, PyQt5.QtCore.Qt.AlignRight)
        fees_layout.addWidget(self.fees_taker_label, 1, 0)
        fees_layout.addWidget(self.fees_taker_val, 1, 1, PyQt5.QtCore.Qt.AlignRight)
        leverage_layout = PyQt5.QtWidgets.QVBoxLayout()
        if account_info:
            self.leverage_values = [1, 3, 5, 10, 20]
            self.current_leverage = int(pd.DataFrame(account_info).iloc[0]['leverage'] if account_info else 0)

            slider_layout = PyQt5.QtWidgets.QVBoxLayout()
            self.leverage_text = PyQt5.QtWidgets.QLineEdit('Account Leverage')
            self.leverage_text.setReadOnly(True)
            self.leverage_text.setFont(heading_font)

            self.leverage_slider = ListSlider(PyQt5.QtCore.Qt.Horizontal)
            self.leverage_slider.elementChanged.connect(self.leverageChange)
            self.leverage_slider.elementReleased.connect(self.updateLeverageRelease)

            self.leverage_slider.setMinimumWidth(200)
            self.leverage_slider.setMaximumWidth(200)

            self.leverage_slider.setValue(self.leverage_values.index(self.current_leverage))
            disclaimer_text = PyQt5.QtWidgets.QLabel(
                'Not recommended to use more than 3x leverage for inexperienced traders')
            disclaimer_text.setStyleSheet("QLabel {color: red; font: bold; background-color: #e6dddc;}")
            leverage_layout.addStretch()
            leverage_layout.setDirection(PyQt5.QtWidgets.QBoxLayout.BottomToTop)
            leverage_layout.addWidget(disclaimer_text)
            leverage_layout.addWidget(self.leverage_slider)
            leverage_layout.addWidget(self.leverage_text)
            self.leverageChange(None, self.current_leverage, False)

        layout.addWidget(self.fees_text)
        layout.addLayout(fees_layout)
        layout.addLayout(leverage_layout)

        self.setLayout(layout)

    def leverageChange(self, index, value, changed=True):
        # update display on sliding
        value = int(value)
        if not changed:
            self.leverage_text.setText(f'Maximum Account Leverage - {value}x')
            return
        self.leverage_text.setText(f'Maximum Account Leverage - {value}x')

    def updateLeverageRelease(self, value):

        self.parent().updateLeverage(int(value))
        leverage = int(self.parent().updateAccount()['leverage'])
        self.leverage_slider.setValue(self.leverage_values.index(leverage))
        self.leverage_text.setText(f'Maximum Account Leverage - {leverage}x')


class AccountTab(PyQt5.QtWidgets.QWidget):
    def __init__(self, parent=None, account_info=None):
        super().__init__(parent)
        self.setStyleSheet(".QTabBar:tab {margin: 0px; padding: -2px -2px -2x 10px; max-width: 2em; min-width: 2em}"
                           ".QWidget {background-color:white}")

        layout = PyQt5.QtWidgets.QGridLayout()

        self.account_tab = PyQt5.QtWidgets.QTabWidget()
        self.account_tab.setContentsMargins(0, 0, 0, 0)
        self.account_tab.setTabPosition(1)
        heading_font = PyQt5.QtGui.QFont()
        heading_font.setBold(True)
        # orders - 2tables open limit, open trigger
        order_widget = PyQt5.QtWidgets.QWidget()
        order_layout_for_scroll = PyQt5.QtWidgets.QVBoxLayout()
        order_tab = PyQt5.QtWidgets.QScrollArea(widgetResizable=True)
        order_tab.setVerticalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOn)
        sub_order_widget = PyQt5.QtWidgets.QWidget()
        order_layout = PyQt5.QtWidgets.QVBoxLayout()
        order_layout.setContentsMargins(0, 0, 0, 0)
        order_layout.setSpacing(0);
        # open limit orders
        olo = PyQt5.QtWidgets.QLineEdit('Open Limit Orders')
        olo.setFont(heading_font)
        olo.setReadOnly(True)

        order_layout.addWidget(olo)
        self.limit_table = AccountTableView()
        order_layout.addWidget(self.limit_table)
        # open trigger orders
        oto = PyQt5.QtWidgets.QLineEdit('Open Trigger Orders')
        oto.setFont(heading_font)
        order_layout.addWidget(oto)
        self.trigger_table = AccountTableView()

        order_layout.addWidget(self.trigger_table)
        sub_order_widget.setLayout(order_layout)
        order_tab.setWidget(sub_order_widget)

        order_layout_for_scroll.addWidget(order_tab)
        order_widget.setLayout(order_layout_for_scroll)
        order_widget.setContentsMargins(0, 0, 0, 0)
        self.account_tab.addTab(order_widget, PyQt5.QtGui.QIcon('assets/ready_cockatoo.svg'), '')
        # positions - 1 table
        position_tab = PyQt5.QtWidgets.QWidget()
        position_layout = PyQt5.QtWidgets.QVBoxLayout()
        p = PyQt5.QtWidgets.QLineEdit('Positions')
        p.setFont(heading_font)

        self.position_table = AccountTableView()

        position_layout.addWidget(p)
        position_layout.addWidget(self.position_table)
        position_tab.setLayout(position_layout)
        self.account_tab.addTab(position_tab, PyQt5.QtGui.QIcon('assets/sleepy_cockatoo.svg'), '')

        # balances
        balance_tab = PyQt5.QtWidgets.QWidget()
        balance_layout = PyQt5.QtWidgets.QVBoxLayout()
        self.balance_heading_line = PyQt5.QtWidgets.QLineEdit('Balances')
        self.balance_heading_line.setFont(heading_font)

        self.balance_table = AccountTableView()  # coin, balance, available balance, USD value

        balance_layout.addWidget(self.balance_heading_line)
        balance_layout.addWidget(self.balance_table)
        balance_tab.setLayout(balance_layout)
        self.account_tab.addTab(balance_tab, PyQt5.QtGui.QIcon('assets/cone3.svg'), '')
        self.account_tab.setIconSize(PyQt5.QtCore.QSize(19, 26))
        layout.addWidget(self.account_tab, 0, 0)
        self.setLayout(layout)

    def updateLeverage(self, value, changed=True):
        if not changed:
            self.leverage_tab.leverage_text.setText(f'Maximum Account Leverage - {value}x')
            return
        self.parent().updateLeverage(int(value))
        self.leverage_tab.leverage_text.setText(f'Maximum Account Leverage - {value}x')
        leverage = self.parent().updateAccount()['leverage']
        self.self.leverage_tab.leverage_slider.setValue(int(leverage))

    def getLimitTableSize(self, rowcount):
        h = self.limit_table.horizontalHeader().height() + 4
        h = h + self.limit_table.rowHeight(0) * rowcount
        return h

    def getTriggerTableSize(self, rowcount):
        h = self.trigger_table.horizontalHeader().height() + 4
        h = h + self.trigger_table.rowHeight(0) * rowcount
        return h


class OrderPosition(PyQt5.QtWidgets.QWidget):
    update_trigger_orders_signal = PyQt5.QtCore.pyqtSignal(object)

    def __init__(self, settings=None, exchanges=['FTX'], account_info=None):
        super().__init__()
        frame_image = settings['themes']['frame']
        self.setStyleSheet(".QTabWidget:pane { border: 0; }"
                           ".QWidget {background-color: #e6dddc; background-image: " + f"url({frame_image})" + "}"
                           ".QTabBar:tab {margin: 0px; padding: -2px -2px -2x 10px; max-width: 2em; min-width: 2em}")

        # cancel order functionality
        self.api_key = settings['keys']['FTX']['public']
        self.api_secret = settings['keys']['FTX']['private']
        self.channel = ftxAPI(public=self.api_key, private=self.api_secret)

        self.layout = PyQt5.QtWidgets.QVBoxLayout()
        self.tabs = PyQt5.QtWidgets.QTabWidget()

        self.auth_keys = settings['keys']

        self.ftx_account = AccountTab(self, account_info=account_info)
        self.tabs.addTab(self.ftx_account.account_tab, PyQt5.QtGui.QIcon('assets/ftx1.svg'), '')
        self.tabs.setIconSize(PyQt5.QtCore.QSize(18, 20))

        self.open_order_model = DataFrameModel(
            df=pd.DataFrame(columns=['Market', 'Side', 'Size', 'Price', 'Reduce Only',
                                     'Filled', 'Order ID', ' ']))

        self.ftx_account.limit_table.setModel(self.open_order_model)
        self.ftx_account.limit_table.setItemDelegate(AlignDelegate())

        self.open_trigger_model = DataFrameModel(
            df=pd.DataFrame(columns=['Market', 'Type', 'Order Type', 'Side', 'Size',
                                     'Filled Size', 'Limit Price', 'Trigger Price', 'Order ID', ' ']))

        self.ftx_account.trigger_table.setModel(self.open_trigger_model)
        self.ftx_account.trigger_table.setItemDelegate(AlignDelegate())

        self.cancel_widget_dict = {}
        self.cancel_trigger_widget_dict = {}

        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.quote_thread_pool = {}
        self.counter = 0
        self.accountStream()

        self.orders = {}

    def accountStream(self):
        self.threads = []
        self.quote_thread_pool[self.counter] = PyQt5.QtCore.QThreadPool()
        downloader = httpRequestPrivateThread(keys=self.auth_keys, feed='accounts')
        downloader.signals.accounts_signal.connect(self.displayAccounts)
        downloader.signals.trigger_orders_signal.connect(self.sendToLadders)
        self.threads.append(downloader)
        self.quote_thread_pool[self.counter].start(downloader)
        self.counter += 1

    def sendToLadders(self, trigger_orders):

        self.update_trigger_orders_signal.emit(trigger_orders)

    def displayAccounts(self, data):
        balances, positions, orders = data['balances'], data['positions'], data['orders']['orders_df']
        if balances['FTX'].iloc[0].values[0] == 'Not Logged In':
            total_usd_balance = 'Not Logged In'
        else:
            total_usd_balance = round(balances['FTX']['USD Value'].sum(), 2)
            total_usd_balance = f'{total_usd_balance:,.2f} USD'
        self.ftx_account.balance_heading_line.setText(f'Balances - {total_usd_balance}')
        accounts = [self.ftx_account]
        for exchange, account in zip(['FTX'], accounts):
            model = DataFrameModel(balances[exchange])
            account.balance_table.setModel(model)
            account.balance_table.setItemDelegate(AlignDelegate())

            position_model = DataFrameModel(positions[exchange])
            account.position_table.setModel(position_model)
            account.position_table.setItemDelegate(AlignDelegate())

            self.open_order_model.setDataFrame(orders[exchange]['open'])
            # add in the cancel buttons for open limit orders
            for i in range(len(orders[exchange]['open'])):
                button_exists = account.limit_table.indexWidget(self.open_order_model.index(i, 7))
                if not button_exists:
                    orderID = self.open_order_model.index(i, 6).data(PyQt5.QtCore.Qt.DisplayRole)
                    self.cancel_widget_dict[str(i)] = PyQt5.QtWidgets.QPushButton('Cancel Order')
                    self.cancel_widget_dict[str(i)].setStyleSheet(
                        "QPushButton {background-color: red; color: white; font: bold}")  # fa0a4d
                    self.cancel_widget_dict[str(i)].clicked.connect(partial(self.cancel_order, orderID))
                    account.limit_table.setIndexWidget(self.open_order_model.index(i, 7),
                                                       self.cancel_widget_dict[str(i)])
            account.limit_table.setMinimumHeight(account.getLimitTableSize(len(orders[exchange]['open'])))

            self.open_trigger_model.setDataFrame(orders[exchange]['trigger'])
            for i in range(len(orders[exchange]['trigger'])):
                button_exists = account.trigger_table.indexWidget(self.open_trigger_model.index(i, 9))
                if not button_exists:
                    orderID = self.open_trigger_model.index(i, 8).data(PyQt5.QtCore.Qt.DisplayRole)
                    self.cancel_trigger_widget_dict[str(i)] = PyQt5.QtWidgets.QPushButton('Cancel Trigger')
                    self.cancel_trigger_widget_dict[str(i)].setStyleSheet(
                        "QPushButton {background-color: red; color: white; font: bold}")  # fa0a4d
                    self.cancel_trigger_widget_dict[str(i)].clicked.connect(partial(self.cancel_trigger_order, orderID))
                    account.trigger_table.setIndexWidget(self.open_trigger_model.index(i, 9),
                                                         self.cancel_trigger_widget_dict[str(i)])
            account.trigger_table.setMinimumHeight(account.getLimitTableSize(len(orders[exchange]['trigger'])))

    def resetStream(self):
        self.close()
        self.accountStream()

    def updateStyle(self, image):
        self.setStyleSheet("QTabWidget:pane { border: 0; }"
                           ".QWidget {background-color: #e6dddc; background-image: " + f"url({image})" + "}"
                           "QTabBar:tab {margin: 0px; padding: -2px -2px -2x 10px; max-width: 2em; min-width: 2em}")

    def updateLeverage(self, value):
        self.channel.setLeverage(int(value))

    def updateAccount(self):
        response = self.channel.account()
        return response

    def cancel_order(self, orderID):
        self.channel.cancel(orderID=orderID)

    def cancel_trigger_order(self, orderID):
        self.channel.cancelTriggerOrder(orderID)

    def close(self):
        for thread in self.threads:
            thread.stop()
            time.sleep(0.1)

    def closeEvent(self, event):
        self.close()


class Window(PyQt5.QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('cockatoo')
        self.setWindowIcon(PyQt5.QtGui.QIcon('assets/cockatoo.svg'))


        self.settings = EmptySettings
        self.configureSettings()
        # splash page
        self.loading_screen = LoadingScreen(settings=self.settings)
        self.main = PyQt5.QtWidgets.QWidget()
        self.setCentralWidget(self.main)
        self.updateStyle(self.settings['themes']['background'])

        self.api_key = self.settings['keys']['FTX']['public']
        self.api_secret = self.settings['keys']['FTX']['private']
        self.channel = ftxAPI(self.api_key, self.api_secret)

        self.trigger_order_mem = None

        self.account_info = self.accountInfo()

        # create dom ladder dict
        self.windowDict = {}
        self.counter = 0

        # Market explorer
        self.marketExplorer = TreeSection(self, self.settings)
        self.marketExplorer.treeWidget.open_market_signal.connect(self.openDomWindow)
        self.available_markets = self.marketExplorer.treeWidget.exchange_markets  # dict
        self.marketExplorer.sizePolicy().setHorizontalStretch(1)
        self.marketExplorer.setMaximumWidth(350)
        self.marketExplorer.setMinimumWidth(0)
        # Quoteboard
        self.quoteBoard = QuoteBoardSection(self, self.settings)
        self.quoteBoard.quote_board.custom_table.quote_board_signal.connect(partial(self.updateSettings))
        self.quoteBoard.sizePolicy().setHorizontalStretch(2)
        #trade window
        self.activityWindow = ActivityWindowSection(self, self.settings)
        self.activityWindow.update_trade_sub_signal.connect(partial(self.updateSettings))
        self.activityWindow.play_sound_signal.connect(self.playSound)
        self.activityWindow.setMinimumWidth(0)
        self.activityWindow.setMaximumWidth(800)

        self.orderPosition = OrderPosition(self.settings, account_info=self.account_info)
        self.orderPosition.update_trigger_orders_signal.connect(self.updateTriggerOrders)
        self.orderPosition.sizePolicy().setVerticalStretch(2)
        self.orderPosition.setMinimumHeight(200)
        self.orderPosition.setMaximumHeight(700)

        self.createMenuBar()

        layout = PyQt5.QtWidgets.QGridLayout(self.main)
        sub_layout1 = PyQt5.QtWidgets.QGridLayout()
        splitter1 = PyQt5.QtWidgets.QSplitter(PyQt5.QtCore.Qt.Horizontal)

        splitter1.addWidget(self.marketExplorer)
        splitter1.addWidget(self.quoteBoard)

        splitter2 = PyQt5.QtWidgets.QSplitter(PyQt5.QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.orderPosition)

        splitter3 = PyQt5.QtWidgets.QSplitter(PyQt5.QtCore.Qt.Horizontal)
        splitter3.addWidget(splitter2)
        splitter3.addWidget(self.activityWindow)
        splitter3.setStretchFactor(0, 65)
        splitter3.setStretchFactor(1, 35)

        sub_layout1.addWidget(splitter3)

        layout.addLayout(sub_layout1, 0, 0)

        layout.setColumnStretch(0, 0)  # Give column 1 no stretch ability

        self.setWindowState(PyQt5.QtCore.Qt.WindowMaximized)
        self.showMaximized()

        self.loading_screen.splash.show()

    def playSound(self, sound_type):
        """
        sound type can be fills, liquidation, order_fail, orders
        """
        SoundEffects.play(self.settings['sounds'][sound_type]['file'])

    def accountInfo(self):
        """
        return None if not logged in
        """
        account_info = self.channel.getAccount()
        if account_info == {'success': False}:
            return
        return account_info

    def updateTriggerOrders(self, trigger_orders):
        if self.trigger_order_mem == trigger_orders:
            return
        """
        for each trigger order, check the windowDict to see if instance exists for that name
        If it does then send the trigger order to self.windowDict[self.counter]['window'].dom
        """
        for counter, window_dict in self.windowDict.items():
            for market, values in trigger_orders.items():
                if window_dict['contract'] == market:
                    window_dict['window'].threadsPrivate[0].refreshTriggers()

        self.trigger_order_mem = trigger_orders

    def createMenuBar(self):

        menubar = self.menuBar()
        # file
        file = menubar.addMenu('File')

        exitFile = PyQt5.QtWidgets.QAction('Exit', self)
        exitFile.triggered.connect(self.close)
        file.addAction(exitFile)

        # account
        account_settings = menubar.addMenu('Account')

        apiAccount = PyQt5.QtWidgets.QAction('API Keys', self)
        apiAccount.triggered.connect(self.apiDialog)
        account_settings.addAction(apiAccount)

        accountSettings = PyQt5.QtWidgets.QAction('Settings', self)
        accountSettings.triggered.connect(self.accountSettingsDialog)
        account_settings.addAction(accountSettings)

        # preferences
        preferences = menubar.addMenu('Preferences')
        soundPreferences = PyQt5.QtWidgets.QAction('Sounds', self)
        soundPreferences.triggered.connect(self.soundSettings)
        preferences.addAction(soundPreferences)

        themes = PyQt5.QtWidgets.QAction('Themes', self)
        themes.triggered.connect(self.themeSettings)
        preferences.addAction(themes)

        dom_settings = PyQt5.QtWidgets.QAction('DOM Settings', self)
        dom_settings.triggered.connect(self.launchDomSettings)
        preferences.addAction(dom_settings)

    def configureSettings(self):
        sections = self.settings.keys()
        settings_saved = os.path.isfile('settings.json')
        if settings_saved:
            with open('settings.json') as json_file:
                settings = json.load(json_file)
                self.settings = {**settings, **{section: {} for section in sections if section not in settings.keys()}}

    def openDomWindow(self, exchange, contract, specs):
        self.windowDict[self.counter] = {}
        self.windowDict[self.counter]['contract'] = contract
        self.windowDict[self.counter]['window'] = DomWindow(exchange=exchange,
                                                            contract=contract,
                                                            specs=specs,
                                                            keys=self.settings['keys'][exchange],
                                                            dom_settings=self.settings['dom_settings'])
        self.windowDict[self.counter]['window'].dom.all_ladders.connect(self.centerAllTables)
        self.windowDict[self.counter]['window'].all_ladders.connect(self.centerAllTables)
        self.windowDict[self.counter]['window'].sound_signal.connect(self.playSound)
        self.windowDict[self.counter]['window'].closeWindow.connect(self.removeInstance)
        self.windowDict[self.counter]['window'].show()

        self.counter += 1

    def removeInstance(self, counter):

        self.windowDict[counter]['window'].close()

    def centerAllTables(self, event):
        if self.windowDict != {}:
            for counter, info in self.windowDict.items():
                info['window'].dom.center()

    def domPrivateThreadUpdate(self, start=None):
        """
        where the user has entered their keys we want to restart the private stream for each ladder
        """
        if self.windowDict:
            for counter, window_dict in self.windowDict.items():
                try:
                    window_dict['window'].keys = self.settings['keys']['FTX']
                    if start:
                        window_dict['window'].startPrivateStreams()
                    else:
                        window_dict['window'].stopPrivateStreams()

                except Exception as e:
                    pass

    def getSettings(self):
        return self.settings

    def updateSettings(self, key, value, valid=None):
        self.settings[key] = value
        if key == 'keys':
            self.api_key_dialog.close()
            # login details have changed, restart stream with new keys
            self.orderPosition.auth_keys = value
            self.orderPosition.resetStream()
            # start all private threads in each dom ladder
            self.domPrivateThreadUpdate(valid)
        if key == 'themes':
            self.activityWindow.updateStyle(value['frame'])
            self.marketExplorer.updateStyle(value['frame'])
            self.quoteBoard.updateStyle(value['frame'])
            self.orderPosition.updateStyle(value['frame'])

            self.updateStyle(value['background'])

        self.writeSettings()

        return self.settings

    def apiDialog(self):
        self.api_key_dialog = APIKeyManager(self)
        self.api_key_dialog.key_update_signal.connect(partial(self.updateSettings))
        self.api_key_dialog.exec_()

    def accountSettingsDialog(self):
        self.account_info = self.accountInfo()
        self.account_settings_dialog = AccountInfo(self, self.account_info)
        self.account_settings_dialog.exec_()

    def updateLeverage(self, value):
        value = int(value)
        self.channel.setLeverage(value)

    def updateAccount(self):
        response = self.channel.account()
        return response

    def soundSettings(self):
        sound = SoundSettings(self)
        sound.exec_()

    def launchDomSettings(self):
        t = HttpCleaner(ignore_account=True)
        markets = list(t.availableMarkets()['FTX'].keys())
        dom = DomSettings(self, markets=markets, settings=self.settings)
        dom.exec_()

    def themeSettings(self):
        theme = ThemeSettings(self)
        theme.exec_()

    def writeSettings(self):
        with open('settings.json', 'w') as json_file:
            if self.settings['keys']['FTX']['save_keys_in_settings_file']:
                json.dump(self.settings, json_file, sort_keys=True, indent=4)
            else:
                #omit the api keys from the settings file
                empty_keys = {"keys": {"FTX": {"private": "", "public": "", "save_keys_in_settings_file": False}}}
                filtered = {i: v for i, v in self.settings.items() if i != 'keys'}
                json.dump({**empty_keys, **filtered}, json_file, sort_keys=True, indent=4)

    def updateStyle(self, image):
        self.setStyleSheet(
            ".QWidget {background-color: #e6dddc; background-image: " + f"url({image})" + "}"
            "QMenuBar {background-color: #e6dddc; color: white; font: bold}"
            "QMenuBar::item {background-color: #e6dddc;color: black;}")

    def closeEvent(self, event):
        """
        Save the current user settings on central window close
        """
        self.writeSettings()

        self.quoteBoard.close()
        self.orderPosition.close()
        self.activityWindow.close()

        for _, dom in self.windowDict.items():
            try:
                dom['window'].close()
                sys.exit(dom['window'].exec_())
            except Exception as e:
                pass
        return


class LoadingScreen(PyQt5.QtWidgets.QWidget):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.move(50, 50)
        self.splash = PyQt5.QtWidgets.QSplashScreen(PyQt5.QtGui.QPixmap('assets/cockatoo_splash.png'))
        PyQt5.QtCore.QTimer.singleShot(5000, self.splash.close)


if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())
