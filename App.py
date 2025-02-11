import sys
import os
import json
import time
from pathlib import Path
import threading

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTabWidget,
    QWidget, QVBoxLayout, QLabel
)

# Import our custom table widget
from DataFrameTableWidget import DataFrameTableWidget
from NewsWidget import NewsWidget
from ButtonsWidget import ButtonsWidget

from Dashboard import Dashboard
from WatchlistManager import WatchlistManager


TAB_ALL = "Trending"
TAB_MARKETCYCLES = "Market Cycles"
TAB_WATCHLIST = "Watchlist"

class Placeholder(QWidget):
    def __init__(self, text):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(text))
        self.setLayout(layout)

class ChartsContainer(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Charts Placeholder"))
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self, data_dir):
        super().__init__()
        self.data_dir = Path(data_dir).expanduser().resolve()
        os.makedirs(self.data_dir, exist_ok=True)
        self.config_path = self.data_dir / "config.json"

        self.watchlist = WatchlistManager()

        # Dashboard states
        self.dashboards = {
            TAB_ALL: None,
            TAB_MARKETCYCLES: None,
            TAB_WATCHLIST: None
        }
        self.selectedTicker = None

        # Prepare UI
        self.init_ui()
        # Load config
        self.read_settings()
        # Hook: UI loaded
        self.onUiInit()

    def init_ui(self):
        self.setWindowTitle("Market Watcher")

        # Create a main vertical splitter with 3 rows
        self.splitter = QSplitter(self)
        self.splitter.setOrientation(Qt.Vertical)

        # ===== TOP TABS =====
        self.top_tabs = QTabWidget()

        # Create a DataFrameTableWidget for TAB_ALL
        self.external_screener_table = DataFrameTableWidget()
        self.market_cycles_table = DataFrameTableWidget()
        self.watchlist_table = DataFrameTableWidget()

        self.news_widget = NewsWidget()

        # Add 3 tabs to the top tab widget
        self.top_tabs.addTab(self.external_screener_table, TAB_ALL)
        self.top_tabs.addTab(self.market_cycles_table, TAB_MARKETCYCLES)
        self.top_tabs.addTab(self.watchlist_table, TAB_WATCHLIST)

        # Connect tab change signal
        self.top_tabs.currentChanged.connect(
            lambda index: self.on_top_tab_changed(index)
        )

        # ===== MIDDLE TABS =====
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.news_widget, "News")
        self.bottom_tabs.addTab(ChartsContainer(), "Charts")
        self.bottom_tabs.currentChanged.connect(
            lambda index: self.on_bottom_tab_changed(index)
        )

        # ===== ACTIONS PANEL (3rd ROW) =====
        self.actions_panel = ButtonsWidget()

        # Add top tabs, middle tabs, and actions panel to the splitter
        self.splitter.addWidget(self.top_tabs)
        self.splitter.addWidget(self.bottom_tabs)
        self.splitter.addWidget(self.actions_panel)

        # Monitor splitter movements => write settings
        self.splitter.splitterMoved.connect(self.write_settings)

        # Set splitter as central widget
        self.setCentralWidget(self.splitter)

    def on_top_tab_changed(self, index):
        tab_name = self.top_tabs.tabText(index)
        print(f"tab change: {tab_name}")

        # EXAMPLE: If TAB_ALL tab is selected, we populate the table:
        #if tab_name == TAB_ALL:
        #    if self.dashboards[TAB_ALL] is None:
        #        self.dashboards[TAB_ALL] = Dashboard()
        #        #self.refreshAll()

        self.write_settings()
        self.refreshButtons()

    def on_bottom_tab_changed(self, index):
        tab_name = self.bottom_tabs.tabText(index)
        print(f"tab change: {tab_name}")
        self.write_settings()
        self.refreshButtons()

    def on_table_row_click(self, row_index):
        """
        Example row-click callback. 'row_index' might be
        "AMD", "NVDA", etc., if that's the DataFrame index.
        """
        print(f"Row clicked: {row_index}")
        self.selectedTicker = row_index
        currentTopTab = self.getCurrentTopTab()
        if row_index in self.dashboards[currentTopTab].data["news"]:
            self.news_widget.setNews(self.dashboards[currentTopTab].data["news"][row_index])
        else:
            print(f"New news for: {row_index}")

        self.refreshButtons()
    
    def getCurrentTopTab(self):
        top_tab_index = self.top_tabs.currentIndex()
        return self.top_tabs.tabText(top_tab_index) if top_tab_index != -1 else "None"

    def onUiInit(self):
        """User hook: Called after UI creation & settings restore."""
        top_tab_index = self.top_tabs.currentIndex()
        bottom_tab_index = self.bottom_tabs.currentIndex()

        top_tab_name = self.top_tabs.tabText(top_tab_index) if top_tab_index != -1 else "None"
        bottom_tab_name = self.bottom_tabs.tabText(bottom_tab_index) if bottom_tab_index != -1 else "None"

        # self.on_top_tab_changed(top_tab_index)
        # self.on_bottom_tab_changed(bottom_tab_index)
        topTab = self.getCurrentTopTab()
        if topTab == TAB_ALL:
            self.dashboards[TAB_ALL] = Dashboard()
            self.refreshAll(False)

        self.refreshButtons()
        print(f"UI loaded - Active Top Tab: {top_tab_name}, Active Bottom Tab: {bottom_tab_name}")

    def refreshAll(self, refreshReddit=False, refreshStock=False):
        thread = threading.Thread(target=self._refreshAll, args=(refreshReddit,refreshStock,))
        thread.start()

    def _refreshAll(self, refreshReddit=False, refreshStock=False):
        print("_refreshAll", refreshReddit, refreshStock)
        self.dashboards[TAB_ALL].refreshAll(refreshReddit, refreshStock, 50)
        df = self.dashboards[TAB_ALL].data["symbol_table"].copy()
        df["Ticker"] = df.index
        columns = ["Ticker", "Name", "Reddit Rank", "Reddit Rank Change", "Reddit Mentions", "Reddit Mentions Change", "Reddit Upvotes", "News", "News (Positive)", "News (Negative)", "prev_day", "day", "prev_week", "week", "prev_month", "month"]
        gradients = {
            "Reddit Rank Change": (-10, 0, 10),
            "Reddit Mentions": (-1, 0, 250),
            "Reddit Upvotes": (-1, 0, 2000),
            "prev_day": (0, 50, 100),
            "day": (0, 50, 100),
            "prev_week": (0, 50, 100),
            "week": (0, 50, 100),
            "prev_month": (0, 50, 100),
            "month": (0, 50, 100),
        }
        self.external_screener_table.setDataFrame(
            df=df,
            columns=columns,
            gradients=gradients,
            onClick=self.on_table_row_click
        )

    def refreshButtons(self):
        def onButtonClick():
            print("Click!")

        buttons = []

        currentTab = self.getCurrentTopTab()
        if currentTab == TAB_ALL:
            buttons.append({
                "label": "Refresh",
                "icon": "./icons/refresh.png",
                "onClick": lambda: self.refreshAll(True, True)
            })
            buttons.append({
                "label": "Reddit",
                "icon": "./icons/refresh.png",
                "onClick": lambda: self.refreshAll(True, False)
            })
            buttons.append({
                "label": "MarketCycles",
                "icon": "./icons/refresh.png",
                "onClick": lambda: self.refreshAll(False, True)
            })
        if self.selectedTicker is not None:
            buttons.append({
                "label": "AI: summary",
                "icon": "./icons/watchlist.png",
                "onClick": onButtonClick
            })
            buttons.append({
                "label": "AI: Actions",
                "icon": "./icons/watchlist.png",
                "onClick": onButtonClick
            })
            buttons.append({
                "label": f"Add {self.selectedTicker} to watchlist",
                "icon": "./icons/watchlist.png",
                "onClick": onButtonClick
            })
        self.actions_panel.setButtons(buttons)

    def read_settings(self):
        """Load settings from config.json, or use defaults if none exist."""
        if not self.config_path.exists():
            # No config => set defaults
            self.resize(800, 600)
            self.move(100, 100)
            self.splitter.setSizes([300, 300, 100])
            self.top_tabs.setCurrentIndex(0)
            self.bottom_tabs.setCurrentIndex(0)
            return

        with open(self.config_path, "r") as f:
            config = json.load(f)

        # Restore window geometry
        x, y, w, h = config.get("geometry", [100, 100, 800, 600])
        self.setGeometry(x, y, w, h)

        # Restore splitter sizes
        sizes = config.get("splitter_sizes", [300, 300, 100])
        self.splitter.setSizes(sizes)

        # Restore selected tabs
        self.top_tabs.setCurrentIndex(config.get("top_tab_index", 0))
        self.bottom_tabs.setCurrentIndex(config.get("bottom_tab_index", 0))

    def write_settings(self):
        """Save current settings to config.json."""
        config = {}
        config["geometry"] = [self.x(), self.y(), self.width(), self.height()]
        config["splitter_sizes"] = self.splitter.sizes()
        config["top_tab_index"] = self.top_tabs.currentIndex()
        config["bottom_tab_index"] = self.bottom_tabs.currentIndex()

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

    def closeEvent(self, event):
        """Ensure settings are saved on close."""
        self.write_settings()
        super().closeEvent(event)

    def _fetch_external_screener_data(self):
        """
        Placeholder logic to retrieve/assemble a DataFrame.
        In your real code, fetch real data or create it dynamically.
        """
        data = {
            "Reddit Rank": [1, 2, 4],
            "Reddit Rank Change": [-3, 1, 2],
            "Reddit Mentions": [256, 133, 127],
            "prev_day": [23.36, 42.39, 92.88]
        }
        df = pd.DataFrame(data, index=["AMD", "NVDA", "PLTR"])
        return df


def main():
    app = QApplication(sys.argv)
    data_dir = "./config_data"
    window = MainWindow(data_dir)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
