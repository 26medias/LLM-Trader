from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt

class NewsWidget(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        # Create a container widget that will hold all news items
        self.inner_widget = QWidget()
        self.setWidget(self.inner_widget)

        # A vertical layout to stack the news items, with spacing between them
        self.layout = QVBoxLayout(self.inner_widget)
        self.layout.setSpacing(10)  # Space between news containers
        self.layout.setContentsMargins(10, 10, 10, 10)

    def setNews(self, news_array):
        """
        Clears any current news items and repopulates the widget with the news in news_array.
        Each item in news_array should be a dictionary with at least the keys:
          - publisher
          - title
          - description
          - sentiment  (expected values: "positive", "negative", "neutral")
          - reasoning (optional)
        """
        # Clear current contents of the layout
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create a container for each news item and add it to the layout
        for news in news_array:
            news_item = self._create_news_item(news)
            self.layout.addWidget(news_item)

        # Add a stretch so that items are aligned to the top when there are few news items.
        self.layout.addStretch(1)

    def _create_news_item(self, news):
        """
        Creates and returns a widget that represents a single news item.
        The widget consists of an outer frame (border color based on sentiment)
        and an inner widget (content inside without extra styling).
        """
        # Outer frame (applies the border color)
        outer_frame = QFrame()
        outer_frame.setObjectName("outerFrame")  # Unique name to target it in CSS
        outer_frame.setFrameShape(QFrame.Box)
        outer_frame.setLineWidth(2)
        outer_frame.setStyleSheet(self._get_border_style(news.get("sentiment", "neutral")))

        # Inner container (content goes inside here, prevents border from affecting text)
        inner_container = QWidget()
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setSpacing(5)
        inner_layout.setContentsMargins(10, 10, 10, 10)

        # Publisher (italicized)
        publisher = news.get("publisher", "Unknown Publisher")
        publisher_label = QLabel(f"<i>{publisher}</i>")
        inner_layout.addWidget(publisher_label)

        # Title (bold)
        title = news.get("title", "No Title")
        title_label = QLabel(f"<b>{title}</b>")
        inner_layout.addWidget(title_label)

        # Description (word-wrapped)
        description = news.get("description", "")
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        inner_layout.addWidget(description_label)

        # Reasoning (optional, word-wrapped)
        reasoning = news.get("reasoning", "")
        if reasoning:
            reasoning_label = QLabel(reasoning)
            reasoning_label.setWordWrap(True)
            inner_layout.addWidget(reasoning_label)

        # Layout for the outer frame (wraps inner content inside)
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(inner_container)

        return outer_frame

    def _get_border_style(self, sentiment):
        """
        Returns a stylesheet string with the border color depending on the sentiment.
        - "positive" => green (#31ce53)
        - "negative" => red (#eb3333)
        - Otherwise  => gray
        """
        sentiment = sentiment.lower()
        if sentiment == "positive":
            border_color = "#31ce53"
        elif sentiment == "negative":
            border_color = "#eb3333"
        else:
            border_color = "gray"

        # Only apply border to the outer frame, not the child elements
        return f"""
            QFrame#outerFrame {{
                border: 2px solid {border_color};
                border-radius: 5px;
                padding: 5px;
            }}
        """
