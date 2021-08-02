#!/usr/bin/env python3
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import PyQt5.QtWidgets
    import sys
    from core_windows.CentralWindow import Window

    app = PyQt5.QtWidgets.QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec_())

