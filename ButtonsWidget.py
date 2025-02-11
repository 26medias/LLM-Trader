import sys
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QApplication
)
from PyQt5.QtGui import QIcon
from FlowLayout import FlowLayout

class ButtonsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Use our custom flow layout
        self.flowLayout = FlowLayout(self, margin=5, spacing=5)
        self.setLayout(self.flowLayout)

        # Store the button configs
        self._buttons_data = []

    def setButtons(self, buttons=[]):
        """
        Creates buttons according to the passed-in list of dicts.
        Each dict can have "label", "icon", and "onClick".
        """
        self._buttons_data = buttons

        # First, remove all existing items from the layout
        while self.flowLayout.count():
            item = self.flowLayout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        # Create and add new buttons
        for btn_data in buttons:
            label = btn_data.get("label", "")
            icon_path = btn_data.get("icon", "")
            onClick = btn_data.get("onClick", None)

            button = QPushButton(label, self)

            if icon_path:
                button.setIcon(QIcon(icon_path))

            if onClick is not None:
                button.clicked.connect(onClick)

            # Add to the flow layout
            self.flowLayout.addWidget(button)
