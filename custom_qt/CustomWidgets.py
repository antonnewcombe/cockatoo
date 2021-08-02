#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import PyQt5.QtGui
import PyQt5.QtWidgets
import PyQt5.QtCore
import PyQt5.Qt

import sys

class CustomButtonClass(PyQt5.QtWidgets.QPushButton):
    right_clicked = PyQt5.QtCore.pyqtSignal(int)
    left_clicked = PyQt5.QtCore.pyqtSignal(int)
    space_bar_btn_clicked = PyQt5.QtCore.pyqtSignal(object)


    def __init__(self, text, value=None):
        super().__init__()
        self.setText(text)
        self.value = value
        self.setStyleSheet("""
        QPushButton{ background-color: #364b70 ; color: white; font: bold }
        QPushButton:pressed{ background-color: orange; }
        QPushButton:hover{ background-color: #4d6da8; color: black; font; bold }
        """)


    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # item = self.itemAt(event.pos())
        # if not item:
        #    return
        if event.button() == PyQt5.QtCore.Qt.RightButton:
            self.right_clicked.emit(-1)
        elif event.button() == PyQt5.QtCore.Qt.LeftButton:
            self.left_clicked.emit(1)

    def keyPressEvent(self, event):
        event.ignore()

class ComboBox(PyQt5.QtWidgets.QComboBox):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QComboBox{background-color: #ffd1b3;  font: bold;}")
    def keyPressEvent(self, event):
        event.ignore()

class ListSlider(PyQt5.QtWidgets.QSlider):
    # https://stackoverflow.com/questions/58318440/qslider-with-arbitrary-values-from-list-array
    elementChanged = PyQt5.QtCore.pyqtSignal(int, int)
    elementReleased = PyQt5.QtCore.pyqtSignal(int)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimum(0)
        values = [1, 3, 5, 10, 20]
        self._values = []
        self.valueChanged.connect(self._on_value_changed)
        self.sliderReleased.connect(self._on_released)
        self.values = values or []

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._values = values
        maximum = max(0, len(self._values) - 1)
        self.setMaximum(maximum)
        self.setValue(0)

    def _on_value_changed(self, index):
        value = self.values[index]
        self.elementChanged.emit(index, value)

    def _on_released(self):
        index = self.value()
        value = self.values[index]
        self.elementReleased.emit(value)

class TableWidgetItem(PyQt5.QtWidgets.QTableWidgetItem):
    def setData(self, role, value):
        if role == PyQt5.QtCore.Qt.DisplayRole:
            try:
                newvalue = round(float(value),4)
                oldvalue = round(float(self.data(role)),4)
            except (ValueError, TypeError):
                pass
            else:
                if newvalue != oldvalue:
                    #background_color = PyQt5.QtGui.QColor('#d19fe8')
                    foreground_color = PyQt5.QtGui.QColor('#3A4055')
                    if newvalue > oldvalue:
                        background_color = PyQt5.QtGui.QColor('#05BD7A')
                    elif newvalue < oldvalue:
                        background_color = PyQt5.QtGui.QColor('#FF3A66')
                    else:
                        background_color = PyQt5.QtGui.QColor('#000000')
                    def update_background(color = None):
                        try:
                            super(TableWidgetItem, self).setData(
                                PyQt5.QtCore.Qt.BackgroundRole, color)
                        except:#row has been deleted before callback
                            pass
                    def update_foreground(color = None):
                        try:
                            super(PyQt5.QtWidgets.QTableWidgetItem, self).setData(
                                PyQt5.QtCore.Qt.ForegroundRole, color)
                        except: #row has been deleted before callback
                            pass
                    update_background(background_color)
                    update_foreground(foreground_color)

                    PyQt5.QtCore.QTimer.singleShot(800, update_background)
                    PyQt5.QtCore.QTimer.singleShot(800, update_foreground)
        super(TableWidgetItem, self).setData(role, value)

class PositionBox(PyQt5.QtWidgets.QLineEdit):
    """
    Widget for position status
    """
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QLineEdit {background-color: white; color: black; font: bold}")
        self.setReadOnly(True)
        self.setAlignment(PyQt5.QtCore.Qt.AlignCenter)
        self.setText('No Position 没有')

    @PyQt5.QtCore.pyqtSlot(object)
    def position_feed_display(self, data):

        self.setText(data['string'])
        if data['side'] == 'buy':
            self.setStyleSheet("QLineEdit {background-color: #05BD7A; color: white; font: bold}")
        elif data['side'] == 'sell':
            self.setStyleSheet("QLineEdit {background-color: #FF3A66; color: white; font: bold}")
        else:  # no position
            self.setStyleSheet("QLineEdit {background-color: white; color: black; font: bold}")

class OrderBox(PyQt5.QtWidgets.QLineEdit):
    def __init__(self):
        super().__init__()
        self.setMaximumWidth(120)
        self.setOrderValue(0)
        self.setAlignment(PyQt5.QtCore.Qt.AlignHCenter)

    def setOrderValue(self, value):
        self.setText(str(value))

class OrderSpinBox(PyQt5.QtWidgets.QDoubleSpinBox):
    def __init__(self, min = None, max = None, include_buttons = False, decimals = 2):
        super().__init__()
        self.setStyleSheet("""
        QDoubleSpinBox{color: black; font: bold }
        """)
        self.setMaximumWidth(110)
        self.setAlignment(PyQt5.QtCore.Qt.AlignHCenter)
        self.setValue(0)
        self.setMaximum(max)
        self.setMinimum(min)
        self.setDecimals(decimals)
        if include_buttons:
            self.setButtonSymbols()
        else:
            self.setButtonSymbols(self.NoButtons)

    def contextMenuEvent(self, event):
        pass

class OrderTypeCheckBox(PyQt5.QtWidgets.QCheckBox):
    space_bar_btn_clicked = PyQt5.QtCore.pyqtSignal(object)
    def __init__(self):
        super().__init__()
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == PyQt5.QtCore.Qt.RightButton:
            self.right_clicked.emit(-1)
        elif event.button() == PyQt5.QtCore.Qt.LeftButton:
            self.left_clicked.emit(1)

    def keyPressEvent(self, event):
        event.ignore()

class Toggle(PyQt5.QtWidgets.QPushButton):
    def __init__(self, w1 = 'On', w2 = 'Off', check_status=False):
        super().__init__()
        self.setStyleSheet("""
        QPushButton{ background-color: #a60234 ; color: white; font: bold }
        QPushButton:pressed{ background-color: orange; }
        QPushButton:hover{ background-color: #f7024d; color: black; font; bold }
        QPushButton:checked{ background-color: pink; color: #f7024d}

        """)
        self.w1 = w1
        self.w2 = w2
        self.setCheckable(True)
        self.setChecked(check_status)
        self.changeState()
        self.clicked.connect(self.changeState)

    def changeState(self):

        if self.isChecked():
            self.setText(self.w1)
        else:
            self.setText(self.w2)

    def keyPressEvent(self, event):
        event.ignore()

class MarketBuyButton(PyQt5.QtWidgets.QPushButton):
    def __init__(self, text):
        super().__init__()
        self.setText(text)
        self.setStyleSheet("""
        QPushButton{ background-color: #05BD7A ; color: black; font: bold }
        QPushButton:pressed{ background-color: orange; }
        QPushButton:hover{ background-color: #51fbbc; color: black; font; bold }
        """)
        self.setMinimumWidth(140)
    def keyPressEvent(self, event):
        event.ignore()

class MarketSellButton(PyQt5.QtWidgets.QPushButton):
    def __init__(self, text):
        super().__init__()
        self.setText(text)
        self.setStyleSheet("""
        QPushButton{ background-color: #FF3A66 ; color: black; font: bold }
        QPushButton:pressed{ background-color: orange; }
        QPushButton:hover{ background-color: #ff99af; color: black; font; bold }
        """)
        self.setMinimumWidth(140)
    def keyPressEvent(self, event):
        event.ignore()

class ComboBox(PyQt5.QtWidgets.QComboBox):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("QComboBox{background-color: #ffd1b3;  font: bold;}")
    def keyPressEvent(self, event):
        event.ignore()


if __name__ == "__main__":
    app = PyQt5.QtWidgets.QApplication(sys.argv)
    window = TableWidgetDrag()
    window.show()
    sys.exit(app.exec_())