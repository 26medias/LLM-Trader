#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
App skeleton for a PyQt layout matching the attached wireframe.
Each section (Tabs, Actions, TickerTable, News, Charts) is its own class,
currently displaying only a placeholder. 
We then assemble them in the main App class using a clean, DRY approach.
"""

import sys

from TabsContainer import *
from ActionsContainer import *
from TickerTableContainer import *
from NewsContainer import *
from ChartsContainer import *

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Application")

        # Central widget & main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout()
        central_widget.setLayout(main_layout)

        # -- Top row: Tabs (left) + Actions (right)
        self.tabs_container = TabsContainer()
        self.actions_container = ActionsContainer()
        main_layout.addWidget(self.tabs_container, 0, 0)
        main_layout.addWidget(self.actions_container, 0, 1)

        # -- Bottom row: TickerTable (left) + [News (top), Charts (bottom)] (right)
        self.ticker_table_container = TickerTableContainer()
        news_charts_layout = QVBoxLayout()
        self.news_container = NewsContainer()
        self.charts_container = ChartsContainer()
        news_charts_layout.addWidget(self.news_container)
        news_charts_layout.addWidget(self.charts_container)

        right_col_widget = QWidget()
        right_col_widget.setLayout(news_charts_layout)

        main_layout.addWidget(self.ticker_table_container, 1, 0)
        main_layout.addWidget(right_col_widget, 1, 1)

        # Make sure the table expands nicely
        main_layout.setRowStretch(1, 1)
        main_layout.setColumnStretch(0, 2)
        main_layout.setColumnStretch(1, 1)


def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
