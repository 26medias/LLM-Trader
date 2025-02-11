import math
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)

class DataFrameTableWidget(QTableWidget):
    """
    A QTableWidget subclass that can display a pandas DataFrame.
    You can set (or reset) the DataFrame at any time via setDataFrame().
    This allows changing the DataFrame/columns/gradients/callback dynamically.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.df = None
        self.columns = []
        self.gradients = {}
        self.onClick = None

        # Make columns sortable
        self.setSortingEnabled(True)

        # Make columns auto-width
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Enable full-row selection
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Set default style with black border on the selected row
        self.setStyleSheet("""
            QTableWidget {
                background-color: #265c99;
                color: #ffffff;
                selection-background-color: #1b4f72;
                selection-color: #ffffff;
                gridline-color: #ffffff;
            }
            QTableWidget::item:selected {
                border: 1px solid black; /* black border around each cell in the selected row */
            }
            QHeaderView::section {
                background-color: #1b4f72;
                color: #ffffff;
                border: 1px solid #ffffff;
            }
        """)

        # Connect cell click to a handler (if onClick is not None)
        self.cellClicked.connect(self._handle_cell_clicked)

    def setDataFrame(self, df, columns, gradients=None, onClick=None):
        """
        Populate the table with the given DataFrame and column/gradient info.
          - df: pandas DataFrame
          - columns: list of columns (in order) to display
          - gradients: dict of {col_name: (min_val, mid_val, max_val)}
          - onClick: callback(row_index_in_df) for row clicks
        """
        self.df = df
        self.columns = columns
        self.gradients = gradients or {}
        self.onClick = onClick

        # Temporarily disable sorting while populating to avoid overhead
        self.setSortingEnabled(False)

        # Clear existing data
        self.clear()
        self.setRowCount(0)
        self.setColumnCount(0)

        if df is None or df.empty or not columns:
            # Restore sorting if we have nothing to display
            self.setSortingEnabled(True)
            return

        # Set up columns
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        # Set up rows
        row_count = len(df)
        self.setRowCount(row_count)

        # Populate cells
        for row_idx in range(row_count):
            # Store the actual df index for this row
            df_index = df.index[row_idx]

            for col_idx, col_name in enumerate(columns):
                raw_val = df.iloc[row_idx][col_name]
                cell_str = "" if pd.isnull(raw_val) else str(raw_val)

                # Try to parse as numeric
                numeric_val = self._to_float(raw_val)

                # Create the item. If it's the "Ticker" column, force string/alphabetical sort;
                # otherwise store numeric data (if valid) for numeric sort.
                if col_name == "Ticker":
                    # Force alphabetical sort
                    item = QTableWidgetItem(cell_str)
                    item.setData(Qt.UserRole, df_index)
                else:
                    # If numeric_val is valid, store it as a float to get numeric sorting
                    if numeric_val is not None and not math.isnan(numeric_val):
                        item = QTableWidgetItem()
                        # Use numeric in both DisplayRole and EditRole
                        item.setData(Qt.DisplayRole, numeric_val)
                        item.setData(Qt.EditRole, numeric_val)
                        item.setData(Qt.UserRole, df_index)
                    else:
                        # Fallback to string if not a valid float
                        item = QTableWidgetItem(cell_str)
                        item.setData(Qt.UserRole, df_index)

                # Default text color
                item.setForeground(QColor("#ffffff"))

                # Apply gradient background if applicable
                if col_name in self.gradients and numeric_val is not None and not math.isnan(numeric_val):
                    min_val, mid_val, max_val = self.gradients[col_name]
                    color_rgb = self._gradient_color(
                        value=numeric_val,
                        min_val=min_val,
                        midpoint=mid_val,
                        max_val=max_val
                    )
                    if color_rgb:
                        item.setBackground(QColor(*color_rgb))

                self.setItem(row_idx, col_idx, item)

        # Auto-size columns based on contents
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Restore sorting
        self.setSortingEnabled(True)

    def _get_cell_value(self, df, row_idx, col_name):
        """Safely fetch cell value and convert to string."""
        if col_name not in df.columns:
            return ""
        val = df.iloc[row_idx][col_name]
        return "" if pd.isnull(val) else str(val)

    def _handle_cell_clicked(self, row, col):
        """
        If an onClick callback is provided, it is called with the
        actual DataFrame index (stored in the item's UserRole).
        """
        if self.onClick and self.df is not None:
            df_index = self.item(row, col).data(Qt.UserRole)
            self.onClick(df_index)

    @staticmethod
    def _to_float(value):
        """
        Safely convert a value to float. Return None if it fails.
        """
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _hex_to_rgb(hex_color):
        """Converts a hex color code (#RRGGBB) to (R, G, B) tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _interpolate_color(c1, c2, t):
        """
        Linearly interpolate between two (R,G,B) colors c1 and c2 by factor t (0..1).
        """
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )

    @classmethod
    def _gradient_color(cls, value, min_val, midpoint, max_val):
        """
        Returns an (R,G,B) color for 'value' within [min_val, max_val] using
        a two-stage gradient: green -> blue -> red.
         - Below min_val => green (#31ce53)
         - [min_val, midpoint] => gradient green->blue
         - [midpoint, max_val] => gradient blue->red
         - Above max_val => red (#eb3333)
        """
        if value is None:
            return None  # No color for None

        green = cls._hex_to_rgb('#31ce53')
        blue = cls._hex_to_rgb('#265c99')
        red = cls._hex_to_rgb('#eb3333')

        # Below min
        if value <= min_val:
            return green
        # Above max
        if value >= max_val:
            return red

        # Interpolate
        if value <= midpoint:
            # [green -> blue]
            denom = midpoint - min_val
            t = (value - min_val) / denom if denom != 0 else 0
            return cls._interpolate_color(green, blue, t)
        else:
            # [blue -> red]
            denom = max_val - midpoint
            t = (value - midpoint) / denom if denom != 0 else 0
            return cls._interpolate_color(blue, red, t)
