# news.py
import os
import pandas as pd
import requests
from datetime import datetime, timedelta

POLYGON_API_KEY = os.environ['POLYGON_API_KEY']

class NewsLoader:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
    
    def load_news(self, days=7, limit=1000, symbol=None, as_dict=True):
        """
        Loads financial news from Polygon.io.

        If `symbol` is None, we load news for all tickers.
        Otherwise, we load news for the specified symbol.

        Parameters:
            days (int): Number of past days to load news for (using UTC dates).
            limit (int): Maximum number of news items to return.
            symbol (str | None): Symbol to load news for; if None, load all news.

        Returns:
            pandas.DataFrame: A DataFrame containing the aggregated news items.
        """
        base_url = "https://api.polygon.io/v2/reference/news"
        # Calculate UTC time range
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=days)
        published_gte = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        published_lte = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "published_utc.gte": published_gte,
            "published_utc.lte": published_lte,
            "limit": limit,
            "sort": "published_utc",
            "order": "desc",
            "apiKey": POLYGON_API_KEY
        }

        # If a symbol was provided, filter the news by that symbol
        if symbol is not None:
            params["ticker"] = symbol

        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            raise Exception(f"Error fetching news: {response.status_code} {response.text}")

        data = response.json()
        if as_dict:
            if "results" not in data:
                print("== NEWS ERROR ==")
                return None
            return data["results"]
        # Return an empty DataFrame if no results
        if "results" not in data or not data["results"]:
            return pd.DataFrame()

        # Convert the results to a DataFrame
        news_df = pd.DataFrame(data["results"])
        if "published_utc" in news_df.columns:
            news_df["published_utc"] = pd.to_datetime(news_df["published_utc"], utc=True)
        return news_df

if __name__ == "__main__":
    nl = NewsLoader()

    # Load news for a specific symbol
    specific_symbol_news = nl.load_news(days=7, limit=100, symbol="AAPL")
    print("News for AAPL:")
    print(specific_symbol_news.head())

    # Load all news (no symbol specified)
    all_news = nl.load_news(days=7, limit=1000)
    print("All news:")
    print(all_news.head())
