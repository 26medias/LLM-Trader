import os

class WatchlistManager:
    def __init__(self, data_dir: str):
        """
        Initialize the WatchlistManager with a directory to store the watchlist file.
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.watchlist_path = os.path.join(self.data_dir, "watchlist.txt")
        # Ensure file exists
        if not os.path.exists(self.watchlist_path):
            with open(self.watchlist_path, "w", encoding="utf-8"):
                pass  # Create an empty file

    def add(self, ticker: str) -> None:
        """
        Add a ticker to the watchlist (if not already present).
        """
        current_tickers = self.list()
        if ticker.upper() not in [t.upper() for t in current_tickers]:
            with open(self.watchlist_path, "a", encoding="utf-8") as f:
                f.write(f"{ticker}\n")

    def remove(self, ticker: str) -> None:
        """
        Remove a ticker from the watchlist (if present).
        """
        current_tickers = self.list()
        filtered = [t for t in current_tickers if t.upper() != ticker.upper()]
        with open(self.watchlist_path, "w", encoding="utf-8") as f:
            for t in filtered:
                f.write(f"{t}\n")

    def list(self) -> list[str]:
        """
        Return the watchlist as a list of tickers (strings).
        """
        if not os.path.exists(self.watchlist_path):
            return []
        with open(self.watchlist_path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def contains(self, ticker: str) -> bool:
        """
        Check if a ticker is in the watchlist.
        """
        return ticker.upper() in [t.upper() for t in self.list()]

if __name__ == "__main__":
    manager = WatchlistManager("data")

    # Add a couple of tickers
    manager.add("TSLA")
    manager.add("AAPL")

    # Attempt to remove a ticker not on the list (no effect)
    manager.remove("ABCD")

    # Display the current watchlist
    print("Current watchlist:", manager.list())
    
    # Check if a ticker is in the watchlist
    print("Contains TSLA:", manager.contains("TSLA"))
    print("Contains GOOGL:", manager.contains("GOOGL"))
