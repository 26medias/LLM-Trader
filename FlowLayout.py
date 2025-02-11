from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtWidgets import QLayout, QSizePolicy

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)

        self.itemList = []
        self.setSpacing(spacing)

    def __del__(self):
        """Ensure that all QLayoutItems are properly cleaned up."""
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        """
        This layout does not expand in either direction by default.
        """
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        """
        We calculate height depending on width.
        """
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        """
        Layout all items in FlowLayout, either only computing
        the final size (testOnly=True) or also setting geometry.
        """
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            widget = item.widget()
            if not widget:
                continue

            spaceX = self.spacing()
            spaceY = self.spacing()

            # The widget's recommended size
            widgetSize = widget.sizeHint()
            nextX = x + widgetSize.width() + spaceX

            # If nextX passes the right boundary, wrap to the next line
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + widgetSize.width() + spaceX
                lineHeight = 0

            if not testOnly:
                # Position the child widget
                item.setGeometry(QRect(QPoint(x, y), widgetSize))

            x = nextX
            lineHeight = max(lineHeight, widgetSize.height())

        return y + lineHeight - rect.y()
