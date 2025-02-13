# refresh_worker.py
import pandas as pd
from PyQt5.QtCore import QObject, pyqtSignal

class RefreshWorker(QObject):
    # Signal to emit when processing is complete. The signal carries the DataFrame.
    finished = pyqtSignal(pd.DataFrame)
    # Optional: Signal to emit if an error occurs.
    error = pyqtSignal(Exception)
    
    def __init__(self, dashboard, refreshReddit, refreshStock, merge_type):
        super().__init__()
        self.dashboard = dashboard
        self.refreshReddit = refreshReddit
        self.refreshStock = refreshStock
        self.merge_type = merge_type

    def run(self):
        try:
            # Do the heavy computation
            self.dashboard.refreshAll(self.refreshReddit, self.refreshStock, 50, self.merge_type)
            # Make a copy of the DataFrame to pass back to the main thread.
            df = self.dashboard.data["symbol_table"].copy()
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(e)
