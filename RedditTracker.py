import os
import time
import csv
import requests
from typing import Optional, Union

class RedditTracker:
    def __init__(self, data_dir: str):
        """
        Initialize the RedditTracker with a directory to store the CSV data and
        a file to record the timestamp of the last refresh.
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        self.csv_path = os.path.join(self.data_dir, "reddit_stocks.csv")
        self.refresh_time_path = os.path.join(self.data_dir, "reddit_last_refreshed.txt")

    def refresh(self, pages: Optional[int] = 5):
        """
        Fetch data from https://apewisdom.io/api/v1.0/filter/all-stocks/page/{page}.
        If 'pages' is None, it fetches from page=1 up to the total available pages.
        Otherwise, it fetches up to 'pages' pages (starting at page=1).

        The data will be cached in a CSV file, and the last-refreshed time will be updated.
        """
        all_results = []
        current_page = 1

        while True:
            url = f"https://apewisdom.io/api/v1.0/filter/all-stocks/page/{current_page}"
            response = requests.get(url)
            data = response.json()

            # If the JSON structure doesn't match, break early
            if "results" not in data:
                break

            all_results.extend(data["results"])

            # Stop if we've reached the requested number of pages
            if pages is not None and current_page >= pages:
                break

            # Or if we've reached the total number of pages reported by the API
            if pages is None and "pages" in data and current_page >= data["pages"]:
                break

            current_page += 1

        # Write results to CSV
        fieldnames = [
            "rank", "ticker", "name", "mentions", "upvotes",
            "rank_24h_ago", "mentions_24h_ago"
        ]
        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in all_results:
                writer.writerow(row)

        # Update last refreshed time
        with open(self.refresh_time_path, "w", encoding="utf-8") as f:
            f.write(str(time.time()))

    def all(self, as_dict: bool = True) -> Union[list, "pandas.DataFrame"]:
        """
        Return the entire dataset.
        If as_dict is True, returns a list of dicts.
        Otherwise, returns a pandas DataFrame.
        """
        if not os.path.exists(self.csv_path):
            if as_dict:
                return []
            else:
                import pandas as pd
                return pd.DataFrame()

        import pandas as pd
        df = pd.read_csv(self.csv_path)

        if as_dict:
            return df.to_dict(orient="records")
        return df

    def get(self, ticker: str) -> Optional[dict]:
        """
        Return the data for a given ticker as a dict, or None if not found.
        """
        if not os.path.exists(self.csv_path):
            return None

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["ticker"].lower() == ticker.lower():
                    return row

        return None

    def lastRefreshed(self) -> Optional[float]:
        """
        Return how many seconds ago the data was last refreshed.
        If the tracker hasn't been refreshed yet, returns None.
        """
        if not os.path.exists(self.refresh_time_path):
            return None

        with open(self.refresh_time_path, "r", encoding="utf-8") as f:
            try:
                last_time = float(f.read().strip())
            except ValueError:
                return None

        return time.time() - last_time


if __name__ == "__main__":
    # Create an instance of the tracker, storing data in the "data" folder
    tracker = RedditTracker("data")

    # Fetch up to 3 pages of data from the API and save locally
    tracker.refresh(pages=3)

    # How many seconds ago was the data refreshed?
    print("Last refreshed:", tracker.lastRefreshed(), "seconds ago")

    # Retrieve the entire dataset as a list of dicts
    data_all = tracker.all(as_dict=True)
    print("Data sample (first 3 entries):", data_all[:3])

    # Get data for a specific ticker
    ticker_info = tracker.get("PLTR")
    if ticker_info:
        print("Data for PLTR:", ticker_info)
    else:
        print("PLTR not found.")
