import PyQt5.QtGui
import PyQt5.QtWidgets
import PyQt5.QtCore
import PyQt5.Qt

import pandas as pd
import numpy as np
import math
import decimal
from collections import defaultdict

from utils.utilfunc import rec_dd


class PandasModel(PyQt5.QtCore.QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        PyQt5.QtCore.QAbstractTableModel.__init__(self, parent=parent)
        self._df = df.copy()
        self.bolds = dict()

    def toDataFrame(self):
        return self._df.copy()

    def headerData(self, section, orientation, role=PyQt5.QtCore.Qt.DisplayRole):
        if orientation == PyQt5.QtCore.Qt.Horizontal:
            if role == PyQt5.QtCore.Qt.DisplayRole:
                return self._df.columns.tolist()[section]

    def data(self, index, role=PyQt5.QtCore.Qt.DisplayRole):
        if role != PyQt5.QtCore.Qt.DisplayRole:
            return PyQt5.QtCore.QVariant()

        if not index.isValid():
            return PyQt5.QtCore.QVariant()

        return PyQt5.QtCore.QVariant(str(self._df.iloc[index.row(), index.column()]))

    def rowCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return len(self._df.columns)

    def sort(self, column, order):
        colname = self._df.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self._df.sort_values(
            colname, ascending=order == PyQt5.QtCore.Qt.AscendingOrder, inplace=True
        )
        self._df.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()


class CheckablePandasModel(PandasModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(df, parent)
        self.checkable_values = set()
        self._checkable_column = -1

    @property
    def checkable_column(self):
        return self._checkable_column

    @checkable_column.setter
    def checkable_column(self, column):
        if self.checkable_column == column:
            return
        last_column = self.checkable_column
        self._checkable_column = column

        if last_column == -1:
            self.beginInsertColumns(
                PyQt5.QtCore.QModelIndex(), self.checkable_column, self.checkable_column
            )
            self.endInsertColumns()

        elif self.checkable_column == -1:
            self.beginRemoveColumns(PyQt5.QtCore.QModelIndex(), last_column, last_column)
            self.endRemoveColumns()
        for c in (last_column, column):
            if c > 0:
                self.dataChanged.emit(
                    self.index(0, c), self.index(self.columnCount() - 1, c)
                )

    def columnCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return super().columnCount(parent) + (1 if self.checkable_column != -1 else 0)

    def data(self, index, role=PyQt5.QtCore.Qt.DisplayRole):
        if self.checkable_column != -1:
            row, col = index.row(), index.column()
            if col == self.checkable_column:
                if role == PyQt5.QtCore.Qt.CheckStateRole:
                    return (
                        PyQt5.QtCore.Qt.Checked
                        if row in self.checkable_values
                        else PyQt5.QtCore.Qt.Unchecked
                    )
                return PyQt5.QtCore.QVariant()
            if col > self.checkable_column:
                index = index.sibling(index.row(), col - 1)
        return super().data(index, role)

    def setData(self, index, value, role):
        if self.checkable_column != -1:
            row, col = index.row(), index.column()
            if col == self.checkable_column:
                if role == PyQt5.QtCore.Qt.CheckStateRole:
                    if row in self.checkable_values:
                        self.checkable_values.discard(row)
                    else:
                        self.checkable_values.add(row)
                    self.dataChanged.emit(index, index, (role,))
                    return True
                return False
            if col > self.checkable_column:
                index = index.sibling(index.row(), col - 1)
        return super().setData(index, value, role)

    def flags(self, index):
        if self.checkable_column != -1:
            col = index.column()
            if col == self.checkable_column:
                return PyQt5.QtCore.Qt.ItemIsUserCheckable | PyQt5.QtCore.Qt.ItemIsEnabled
            if col > self.checkable_column:
                index = index.sibling(index.row(), col - 1)
        return super().flags(index)

class DataFrameModel(PyQt5.QtCore.QAbstractTableModel):
    DtypeRole = PyQt5.QtCore.Qt.UserRole + 1000
    ValueRole = PyQt5.QtCore.Qt.UserRole + 1001

    def __init__(self, df=pd.DataFrame(), parent=None, mapping = None):
        super(DataFrameModel, self).__init__(parent)
        self._dataframe = np.array(df.values)
        self._cols = df.columns
        self.mapping = mapping

    def setDataFrame(self, dataframe):
        self.beginResetModel()
        self._dataframe = np.array(dataframe.values)
        self.endResetModel()

    def dataFrame(self):
        return self._dataframe

    @PyQt5.QtCore.pyqtSlot(int, PyQt5.QtCore.Qt.Orientation, result=str)
    def headerData(self, section: int, orientation: PyQt5.QtCore.Qt.Orientation, role: int = PyQt5.QtCore.Qt.DisplayRole):
        if role == PyQt5.QtCore.Qt.DisplayRole:
            if orientation == PyQt5.QtCore.Qt.Horizontal:
                if self.mapping:
                    return self.mapping[self._cols[section]]
                else:
                    return self._cols[section]
            else:
                return section
        return None

    def rowCount(self, parent=PyQt5.QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return np.shape(self._dataframe)[0]

    def columnCount(self, parent=PyQt5.QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return np.shape(self._dataframe)[1]

    def data(self, index, role=PyQt5.QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount() \
            and 0 <= index.column() < self.columnCount()):
            return None

        val = self._dataframe[index.row()][index.column()]
        if role == PyQt5.QtCore.Qt.DisplayRole:
            return PyQt5.QtCore.QVariant(str(val))
        elif role == DataFrameModel.ValueRole:
            return val
        return None

    def roleNames(self):
        roles = {
            PyQt5.QtCore.Qt.DisplayRole: b'display',
            DataFrameModel.DtypeRole: b'dtype',
            DataFrameModel.ValueRole: b'value'
        }
        return roles

    def flags(self, index):
        flags = super(self.__class__, self).flags(index)
        flags |= PyQt5.QtCore.Qt.ItemIsEditable
        flags |= PyQt5.QtCore.Qt.ItemIsSelectable
        flags |= PyQt5.QtCore.Qt.ItemIsEnabled
        flags |= PyQt5.QtCore.Qt.ItemIsDragEnabled
        flags |= PyQt5.QtCore.Qt.ItemIsDropEnabled
        return flags

    def sort(self, Ncol, order):
        """Sort table by given column number.
        """
        print(f'sorting {Ncol} {order}')
        try:
            self.layoutAboutToBeChanged.emit()
            self._dataframe = self._dataframe.sort_values(self._dataframe.columns[Ncol], ascending=not order)
            self.layoutChanged.emit()
        except Exception as e:
            print(e)

class TableModel(PyQt5.QtCore.QAbstractTableModel):
    ValueRole = PyQt5.QtCore.Qt.UserRole + 1001

    def __init__(self, specs, length=100000, parent=None, launch_agg=None):
        super().__init__(parent)
        self.specs = specs

        self.default_length = self.DefaultLength(specs['last_price'], launch_agg)
        self.prices = self.setPriceColumn(self.tick, self.default_length)
        self.book = np.array([[0, 0, 0], [0, 0, 0]])
        self.volume_profile = defaultdict(float)
        self.order_dict_mem = {'open_buys': rec_dd(),
                               'open_sells': rec_dd(),
                               'trigger_buys': rec_dd(),
                               'trigger_sells': rec_dd()}
        self.order_dict = {'buy': rec_dd(), 'sell': rec_dd()}
        self.trigger_orders_mem = None
        self.trigger_orders = None
        self.last_trade = specs['last']
        self.bests = [0, 0]

    def setPriceColumn(self, tick_size, length):
        rounding = abs(int(decimal.Decimal(str(tick_size)).as_tuple().exponent))
        tick = round(float(tick_size), rounding)
        price = tick * length
        prices = []
        self.price_colum_num = []
        for i in range(length):
            price = price - tick
            prices.append(str.format('{0:.' + str(rounding) + 'f}', price))
            self.price_colum_num.append(round(price, rounding))
        prices[-1] = prices[-1].replace('-', '')
        self.updatePriceColumn(prices)
        return prices

    def updatePriceColumn(self, prices):
        self.prices = prices
        for i in range(self.default_length):
            self.dataChanged.emit(self.index(i, 2), self.index(i, 2))

    def DefaultLength(self, price, launch_agg):
        """
        table is opened with minimum 50% upward allowable market price due to performance.
        TODO: make the table auto increase if the price gets close to the highest allowable price
        """
        self.tick = launch_agg if launch_agg else self.specs['tick_size']
        rows_to_max_price = price / self.tick
        # eg: logan vs mayweather has price 0.05, this rule makes the market only available to 0.075.
        # put in a minimum value to handle this
        return max(int(math.ceil(rows_to_max_price * 1.5)), 10000)

    def defaultify(self, d):
        if not isinstance(d, dict):
            return d
        return defaultdict(lambda: defaultdict(float), {k: self.defaultify(v) for k, v in d.items()})

    def rowCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return len(self.prices)

    def columnCount(self, parent=PyQt5.QtCore.QModelIndex()):
        return 6

    def updateBook(self, book):
        # data = {'best' : [best ask, best bid], 'book': np.array(book)}
        self.book = book['book']
        best_ask, best_bid = book['best']
        best_ask_ix = int(self.default_length - best_ask / self.tick)
        best_bid_ix = int(self.default_length - best_bid / self.tick)
        bid_mem, ask_mem = self.bests
        # smarter refreshing
        if best_ask == ask_mem and best_bid == bid_mem:
            # prices are unchanged
            for i in range(best_bid_ix, best_ask_ix + 30):
                col1_start_index = self.index(i, 1)
                col1_end_index = self.index(i, 1)
                self.dataChanged.emit(col1_start_index, col1_end_index)
            for i in range(best_ask_ix - 30, best_ask_ix):
                col3_start_index = self.index(i, 3)
                col3_end_index = self.index(i, 3)
                self.dataChanged.emit(col3_start_index, col3_end_index)
        else:
            band = range(best_ask_ix - 30, best_bid_ix + 30)
            for i in band:
                col1_start_index = self.index(i, 1)
                col1_end_index = self.index(i, 1)
                self.dataChanged.emit(col1_start_index, col1_end_index)
                col3_start_index = self.index(i, 3)
                col3_end_index = self.index(i, 3)
                self.dataChanged.emit(col3_start_index, col3_end_index)

        self.bests = book['best']

    def updateVolumeProfile(self, data):
        volume_profile, volume_diff, refresh_flag = data
        if refresh_flag:
            # when the tick size changes we need to refresh volumes at each price to account for the aggregation
            self.beginResetModel()
            self.volume_profile = volume_profile
            self.endResetModel()
        else:
            self.volume_profile = volume_profile
            # update only the diffs
            for price, volume in volume_diff.items():
                row_index = int(self.default_length - price / self.tick)
                self.dataChanged.emit(self.index(row_index, 5), self.index(row_index, 5))

    def updateOrderFeed(self, open_order_dict):
        """
        signal will only be sent to this function when there is an update to the order websocket feed
        """
        display_dict = {'buy': {}, 'sell': {}}

        for price, values in open_order_dict.items():
            for order_type in ['open', 'trigger']:
                if order_type not in values.keys():
                    continue
                side = values[order_type]['side']
                flag = 0 if order_type == 'open' else 1
                display_dict[side][price] = [values[order_type]['quantity'], flag]
        display_dict['buy'] = self.defaultify(display_dict['buy'])
        display_dict['sell'] = self.defaultify(display_dict['sell'])
        self.beginResetModel()
        self.order_dict = display_dict
        self.endResetModel()
        for side, column in [['buy', 1], ['sell', 4]]:
            for price, volume in self.order_dict[side].items():
                row_index = int(self.default_length - price / self.tick)
                self.dataChanged.emit(self.index(row_index, column), self.index(row_index, column))

        self.beginResetModel()
        self.order_dict = display_dict
        self.endResetModel()

    def unifyOrderDict(self, order_dict_mem):
        """
        convert from order_dict memory to order dict with only two sides
        """
        order_dict = {}
        order_dict['buys'] = self.defaultify({**order_dict_mem['open_buys'], **order_dict_mem['trigger_buys']})
        order_dict['sells'] = self.defaultify({**order_dict_mem['open_sells'], **order_dict_mem['trigger_sells']})
        return order_dict

    def data(self, index, role):
        if not index.isValid():
            return
        if role == PyQt5.QtCore.Qt.DisplayRole:
            if index.row() < 0 or index.row() >= len(self.prices):
                return None
            if index.column() == 0:
                volume_at_price = self.order_dict['buy'][self.price_colum_num[index.row()]]
                return volume_at_price
            if index.column() == 4:
                volume_at_price = self.order_dict['sell'][self.price_colum_num[index.row()]]
                return volume_at_price

            if index.column() == 2:
                return PyQt5.QtCore.QVariant(str(self.prices[index.row()]))

            if index.column() in [1, 3]:
                row_price = self.price_colum_num[index.row()]
                if row_price in self.book[:, 1]:
                    idx = np.where(self.book[:, 1] == row_price)[0][0]
                    vol = self.book[idx, index.column() - 1]
                    return vol

            if index.column() == 5:
                volume = self.volume_profile[self.price_colum_num[index.row()]]
                price = self.price_colum_num[index.row()]
                return int(round(price * volume, 0))

        return None

    def flags(self, index):
        return PyQt5.QtCore.Qt.ItemIsEditable | PyQt5.QtCore.Qt.ItemIsDragEnabled | PyQt5.QtCore.Qt.ItemIsSelectable | PyQt5.QtCore.Qt.ItemIsEnabled | PyQt5.QtCore.Qt.ItemIsDropEnabled

class TableView(PyQt5.QtWidgets.QTableView):

    item_right_clicked = PyQt5.QtCore.pyqtSignal(object)
    item_left_clicked = PyQt5.QtCore.pyqtSignal(object)
    middle_clicked = PyQt5.QtCore.pyqtSignal(object)
    stop_drag_signal = PyQt5.QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        PyQt5.QtWidgets.QTableView.__init__(self, parent)
        self.setStyleSheet(
            "TableView {font-size: 8pt; font: bold; font-family: Arial;}")
        self.setDragEnabled(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(PyQt5.QtWidgets.QAbstractItemView.DragDrop)
        self.setDragDropOverwriteMode(False)

        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.setVerticalScrollBarPolicy(PyQt5.QtCore.Qt.ScrollBarAlwaysOff)

        self.setSizeAdjustPolicy(PyQt5.QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.setSizePolicy(PyQt5.QtWidgets.QSizePolicy.Expanding, PyQt5.QtWidgets.QSizePolicy.Expanding)

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        index = self.indexAt(event.pos())
        self.stop_drag_signal.emit(index)
        self.setFocus()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        index = self.indexAt(event.pos())
        if not index:
            return
        if event.button() == PyQt5.QtCore.Qt.RightButton:
            self.item_right_clicked.emit(index)
        elif event.button() == PyQt5.QtCore.Qt.LeftButton:
            self.item_left_clicked.emit(index)
        elif event.button() == PyQt5.QtCore.Qt.MidButton:
            self.middle_clicked.emit('mouse3')

    def keyPressEvent(self, event):
        pass
