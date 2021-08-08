import PyQt5.QtGui
import PyQt5.QtWidgets
import PyQt5.QtCore
import PyQt5.Qt

import bisect
from app_styles.AppStyles import quote_board_colors


def number_string_threshold(number):
    """
     usage LastQuoteBoardDelegate to handle large numbers for market cap formulas etc
    """
    if number < 1_000_000:
        num_str = f'{number: ,}'
        return num_str[:-2] if num_str.endswith('.0') else num_str
    magnitude = 0
    number = number / 1_000
    while abs(number) >= 1_000:
        magnitude += 1
        number /= 1_000
    # add more suffixes if you need them
    suffix = ['','M', 'B', 'T', 'P'][magnitude]
    return f'{number: ,.2f} {suffix}'

def number_string(number):
    magnitude = 0
    while abs(number) >= 1_000:
        magnitude += 1
        number /= 1_000
    # add more suffixes if you need them
    suffix = ['','k','M', 'B', 'T', 'P'][magnitude]
    return f'{number: ,.0f} {suffix}'

def price_format(number):
    num_str = f'{number: ,}'
    return num_str[:-2] if num_str.endswith('.0') else num_str

class MarketQuoteBoardDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    """
    Manages the style for the first column in the quoteboard
    """
    def __init__(self, parent = None, defaultWidth = 160):
        super().__init__(parent)
        self.defaultWidth = defaultWidth

    def paint(self, painter, option, index):
        item = index.data(PyQt5.QtCore.Qt.DisplayRole)
        item = '' if not item else item
        rect =  PyQt5.QtCore.QRect(option.rect.x(), option.rect.y(), option.rect.width(), option.rect.height())

        margin_color = PyQt5.QtGui.QColor('#cad7e0')
        background_color = PyQt5.QtGui.QColor('#cad7e0')
        painter.fillRect(option.rect, margin_color)

        color = PyQt5.QtGui.QColor(background_color)
        painter.setBrush(PyQt5.QtGui.QBrush(color))

        if item == '':
            #no entry in the cell
            background_color = PyQt5.QtGui.QColor('#e6dfe6')
            painter.setPen(PyQt5.QtGui.QColor('#FF6600'))

        if item.startswith('?'):
            #special formula
            background_color = PyQt5.QtGui.QColor('#b2b8cf')
            painter.setPen(PyQt5.QtGui.QColor('#eb2d6e'))
        elif item.startswith('~'):
            #section heading
            background_color = PyQt5.QtGui.QColor('#FFFFFF')
            painter.setPen(PyQt5.QtGui.QColor('#FF6600'))
        else:
            painter.setPen(PyQt5.QtCore.Qt.black)
        painter.fillRect(option.rect, background_color)  # 9dd1d1 #3B4754

        font = PyQt5.QtGui.QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, PyQt5.QtCore.Qt.AlignCenter, str(item))

        #color bottom horizontal gridline

        edge_color = PyQt5.QtGui.QColor('#76458a')
        painter.setPen(edge_color);
        p1 = PyQt5.QtCore.QPoint(option.rect.bottomLeft().x() - 1, option.rect.bottomLeft().y());
        p2 = PyQt5.QtCore.QPoint(option.rect.bottomRight().x() + 1, option.rect.bottomRight().y());
        painter.drawLine(p1, p2);

    def sizeHint(self, option, index):
        hint = PyQt5.QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
        if self.defaultWidth is not None:
            hint.setWidth(self.defaultWidth)
        return hint

class LastQuoteBoardDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    """
    Manages the styling for the last trade price, futures index, 24hr USD
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        item = index.data(PyQt5.QtCore.Qt.DisplayRole)

        painter.setPen(PyQt5.QtCore.Qt.black)
        font = PyQt5.QtGui.QFont()
        font.setBold(True)
        painter.setFont(font)

        default_color = PyQt5.QtGui.QColor('#FFFFFF')
        if item not in ['-',0, '', '0', '0.0']:
            item = number_string_threshold(float(item))
            painter.fillRect(option.rect, default_color)  # 183666
        else:
            item = ''
            painter.fillRect(option.rect, PyQt5.QtCore.Qt.white)

        painter.drawText(option.rect, PyQt5.QtCore.Qt.AlignCenter, str(item))
        edge_color = PyQt5.QtGui.QColor('#76458a')
        painter.setPen(edge_color);
        p1 = PyQt5.QtCore.QPoint(option.rect.bottomLeft().x() - 1, option.rect.bottomLeft().y());
        p2 = PyQt5.QtCore.QPoint(option.rect.bottomRight().x() + 1, option.rect.bottomRight().y());
        painter.drawLine(p1, p2);

class BasisQuoteBoardDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    """
    Manages the style for the basis, funding, 1hr % change, 24hr % change
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.defaultWidth = 57

        self.color_settings = {}
        for i in ['negative','positive']:
            self.color_settings[i] = {}
            self.color_settings[i]['vals'] = []
            self.color_settings[i]['color'] = []
            self.color_settings[i]['font_color'] = []
            for tier, settings in quote_board_colors['percent_changes'][i].items():
                self.color_settings[i]['color'].append(settings[0])
                self.color_settings[i]['vals'].append(abs(settings[1])) #convert negative to positive for use in bisect function
                self.color_settings[i]['font_color'].append(settings[2])

    def paint(self, painter, option, index):
        item = index.data(PyQt5.QtCore.Qt.DisplayRole)

        font = PyQt5.QtGui.QFont()
        font.setBold(True)
        painter.setFont(font)
        blank_color = PyQt5.QtGui.QColor('#ffffff')
        if item:
            if item not in ['-', 0, '0', '0.0']:
                val = float(item)
                side = 'negative' if val < 0 else 'positive'
                sign = '+' if val > 0 else ''
                a = self.color_settings[side]['vals']
                val_index = bisect.bisect(a, abs(val)) - 1 #abs(val) as negative vals are now positive
                color = self.color_settings[side]['color'][val_index]
                text_color = self.color_settings[side]['font_color'][val_index]
                item = f'{sign}{round(val * 100, 2)}%'
            else:
                item = ''
                color = blank_color
                text_color = PyQt5.QtCore.Qt.black
            painter.setPen(PyQt5.QtGui.QColor(text_color))
            painter.fillRect(option.rect, PyQt5.QtGui.QColor(color))
            painter.drawText(option.rect, PyQt5.QtCore.Qt.AlignCenter, item)
        else:
            painter.fillRect(option.rect, PyQt5.QtGui.QColor(PyQt5.QtCore.Qt.white))
            painter.drawText(option.rect, PyQt5.QtCore.Qt.AlignCenter, '')

        edge_color = PyQt5.QtGui.QColor('#76458a')
        painter.setPen(edge_color)
        p1 = PyQt5.QtCore.QPoint(option.rect.bottomLeft().x() - 1, option.rect.bottomLeft().y())
        p2 = PyQt5.QtCore.QPoint(option.rect.bottomRight().x() + 1, option.rect.bottomRight().y())
        painter.drawLine(p1, p2);

    def sizeHint(self, option, index):
        hint = PyQt5.QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
        if self.defaultWidth is not None:
            hint.setWidth(self.defaultWidth)
        return hint

class MarginQuoteBoardDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    """
    Managers the styling for the lend APY column
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.defaultWidth = 65

    def paint(self, painter, option, index):
        item = index.data(PyQt5.QtCore.Qt.DisplayRole)
        font = PyQt5.QtGui.QFont()
        font.setBold(True)
        painter.setFont(font)
        default = '#e6dddc'
        text_color = PyQt5.QtCore.Qt.black
        blank_color = PyQt5.QtGui.QColor('#FFFFFF')

        if item:
            if item != '-':
                val = float(item)
                if val == 0:
                    sign = ''
                    item = '-'
                    color = default
                    text_color = PyQt5.QtCore.Qt.black
                else:
                    sign = '+'
                    if val >= 0.1:
                        color = '#00ffa2'
                        text_color = PyQt5.QtCore.Qt.white
                        font.setBold(True)
                    elif val >= 0.075:
                        color = '#05BD7A'
                    elif val >= 0.05:
                        color = '#a4dec9'
                    elif val >= 0.025:
                        color = '#bfded3'
                    else:
                        color = '#c8dbd4'

                item = f'{sign}{round(val * 100, 2)}%'
            else:
                color = default
                text_color = PyQt5.QtCore.Qt.black
            painter.setPen(text_color)
            painter.fillRect(option.rect, PyQt5.QtGui.QColor(color))
            painter.drawText(option.rect, PyQt5.QtCore.Qt.AlignCenter, item)
        else:
            painter.setPen(text_color)
            painter.fillRect(option.rect, blank_color)
            painter.drawText(option.rect, PyQt5.QtCore.Qt.AlignCenter, '-')


        edge_color = PyQt5.QtGui.QColor('#76458a')
        painter.setPen(edge_color);
        p1 = PyQt5.QtCore.QPoint(option.rect.bottomLeft().x() - 1, option.rect.bottomLeft().y());
        p2 = PyQt5.QtCore.QPoint(option.rect.bottomRight().x() + 1, option.rect.bottomRight().y());
        painter.drawLine(p1, p2);

    def sizeHint(self, option, index):
        hint = PyQt5.QtWidgets.QStyledItemDelegate.sizeHint(self, option, index)
        if self.defaultWidth is not None:
            hint.setWidth(self.defaultWidth)
        return hint

class AlignDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super(AlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = PyQt5.QtCore.Qt.AlignCenter

class PushButtonDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    clicked = PyQt5.QtCore.pyqtSignal(PyQt5.QtCore.QModelIndex)

    def paint(self, painter, option, index):
        if (
            isinstance(self.parent(), PyQt5.QtWidgets.QAbstractItemView)
            and self.parent().model() is index.model()
        ):
            self.parent().openPersistentEditor(index)

    def createEditor(self, parent, option, index):
        button = PyQt5.QtWidgets.QPushButton(parent)
        button.clicked.connect(lambda *args, ix=index: self.clicked.emit(ix))
        return button

    def setEditorData(self, editor, index):
        editor.setText(index.data(PyQt5.QtCore.Qt.DisplayRole))

    def setModelData(self, editor, model, index):
        pass


class ProgressDelegate(PyQt5.QtWidgets.QStyledItemDelegate):
    """
    This controls the trade volume bar sizes
    """

    def paint(self, painter, option, index):
        volume = index.data(PyQt5.QtCore.Qt.DisplayRole)
        if not volume:
            return
        volume = int(volume)
        if volume <= 50_000:
            volume_prop = 0.05
        elif volume <= 200_000:
            volume_prop = 0.1
        elif volume <= 500_000:
            volume_prop = 0.15
        elif volume <= 1_000_000:
            volume_prop = 0.25
        elif volume <= 2_000_000:
            volume_prop = 0.35
        elif volume <= 5_000_000:
            volume_prop = 0.45
        elif volume <= 10_000_000:
            volume_prop = 0.6
        elif volume <= 25_000_000:
            volume_prop = 0.75
        elif volume <= 50_000_000:
            volume_prop = 0.85
        else:
            volume_prop = 0.95
        opt = PyQt5.QtWidgets.QStyleOptionProgressBar()

        progress = volume_prop * 100
        # # draw the progress bar
        painter.setBrush(PyQt5.QtGui.QColor('#facdf4'))
        painter.setPen(PyQt5.QtGui.QColor('#facdf4'))
        progress_bar = PyQt5.QtCore.QRect(option.rect.x(), option.rect.y(),
                                          int((option.rect.width() * progress) / 100),
                                          option.rect.height())
        painter.drawRect(progress_bar)
        # draw the background and text
        background_rect = PyQt5.QtCore.QRect(option.rect.x(), option.rect.y(), option.rect.width(),
                                             option.rect.height())
        painter.setBrush(PyQt5.QtGui.QColor('#facdf4'))
        painter.setPen(PyQt5.QtGui.QColor('#000000'))
        painter.drawText(background_rect, PyQt5.QtCore.Qt.AlignRight, f'{volume:,}')


class ItemDelegate(PyQt5.QtWidgets.QItemDelegate):
    def __init__(self, parent):
        PyQt5.QtWidgets.QItemDelegate.__init__(self, parent)
        self.parent = parent

        self.marginLeft = 10  # margin between text in each cell with the left border
        self.marginRight = 10  # margin between text in each cell with the right border

    def paint(self, painter, option, index):
        item = index.data(PyQt5.QtCore.Qt.DisplayRole)
        if type(item) == list:
            item, order_type = item  # returns [order quantity, order_type]
        if index.column() == 1:
            hex_code = '#05BD7A' if item else '#bfded3'
            painter.setPen(PyQt5.QtCore.Qt.white)
        elif index.column() == 2:
            hex_code = '#cad7e0'
            painter.setPen(PyQt5.QtGui.QPen(PyQt5.QtCore.Qt.black))
        elif index.column() == 3:
            hex_code = '#FF3A66' if item else '#F4DBE1'
            painter.setPen(PyQt5.QtGui.QPen(PyQt5.QtCore.Qt.white))
        else:
            hex_code = '#FFFFFF'
            painter.setPen(PyQt5.QtGui.QPen(PyQt5.QtCore.Qt.black))
        color = PyQt5.QtGui.QColor(hex_code)
        painter.fillRect(option.rect, color)

        # set text color
        # set text formatting
        if item:
            # dim adds some buffer to the edge of the cell
            if index.column() == 1:
                alignment = PyQt5.QtCore.Qt.AlignRight
                item = float(item)
                if item > 9_999_999:
                    item = f'{round(item / 1_000_000, 2)}M'
                else:
                    item = f'{int(round(item, 0)):,}' if item > 2000 else f'{round(item, 2):,.2f}'
                dim = -3
            elif index.column() == 3:
                alignment = PyQt5.QtCore.Qt.AlignLeft
                item = float(item)
                if item > 9_999_999:
                    item = f'{round(item / 1_000_000, 2)}M'
                else:
                    item = f'{int(round(item, 0)):,}' if item > 2000 else f'{round(item, 2):,.2f}'
                dim = -3
            elif index.column() in [0, 4]:
                alignment = PyQt5.QtCore.Qt.AlignLeft
                image_name = 'assets/money_bag2.svg' if order_type == 0 else 'assets/stop.svg'
                image = PyQt5.QtGui.QImage(image_name)
                # image = PyQt5.QtGui.QImage('assets/elvis.png')
                pixmap = PyQt5.QtGui.QPixmap.fromImage(image)
                pixmap.scaled(50, 40, PyQt5.QtCore.Qt.KeepAspectRatio)
                pic_rect = PyQt5.QtCore.QRect(option.rect.x() + 40, option.rect.y() + 2, int(option.rect.width() * .3),
                                              int(option.rect.height() * 0.7))
                painter.drawPixmap(pic_rect, pixmap)
                dim = -3

            else:
                alignment = PyQt5.QtCore.Qt.AlignCenter
                dim = 0
            text_rect = PyQt5.QtCore.QRect(option.rect.x() - dim, option.rect.y(), int(option.rect.width() * 0.9),
                                           option.rect.height())
            painter.drawText(text_rect, alignment, str(item))


def StyleActivityCells(trade_data, col):
    #TODO: put trade value brackets and colors in a config
    """
    trade_data = [{'time' : [time],
                         'market' : [market],
                         'exchange' : [exchange],
                         'USD' : [size_str, size],
                         'side' : [side],
                         'price' : [str(price), price],
                         'type' : [trade_type]}
                         ]
    col is 'time', 'market', 'exchange', 'USD', 'side', 'price', or 'type'
    """
    if col == 'price':
        price_formatted = price_format(trade_data[col][-1])
        cell = PyQt5.QtWidgets.QTableWidgetItem(price_formatted)  # [0] is the formatted version of data
    else:
        cell = PyQt5.QtWidgets.QTableWidgetItem(trade_data[col][0])
    cell.setTextAlignment(PyQt5.QtCore.Qt.AlignCenter)
    side = trade_data['side'][0]
    if col == 'time':
        cell.setBackground(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor('#cad7e0')))
        cell.setForeground(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor(PyQt5.QtCore.Qt.black)))
    else:
        if side == 'BUY':
            cell.setForeground(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor('#05BD7A')))
        else:
            cell.setForeground(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor('#FF3A66')))
        font = PyQt5.QtGui.QFont()
        if trade_data['USD'][-1] < 50_000:
            font.setPointSize(8)
            back_color = '#bfded3' if side == 'BUY' else '#F4DBE1'
            text_color = '#000000'
        elif trade_data['USD'][-1] < 100_000:
            font.setPointSize(10)
            back_color = '#a4dec9' if side == 'BUY' else '#f0a3b5'
            text_color = '#000000'
        elif trade_data['USD'][-1] < 200_000:
            font.setPointSize(12)
            back_color = '#05BD7A' if side == 'BUY' else '#FF3A66'
            text_color = '#FFFFFF'
            font.setBold(True)
        else:
            text_color = '#FFFFFF'
            back_color = '#00ffa2' if side == 'BUY' else '#ff1f51'
            font.setPointSize(13)
            font.setBold(True)
        if trade_data['type'][0] == 'liq':
            back_color = '#364b70'
            text_color = '#05BD7A' if side == 'BUY' else '#FF3A66'
            font.setPointSize(14)
            font.setBold(True)
        cell.setFont(font)
        cell.setBackground(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor(back_color)))
        cell.setForeground(PyQt5.QtGui.QBrush(PyQt5.QtGui.QColor(text_color)))
    return cell
