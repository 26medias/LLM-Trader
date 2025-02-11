from RedditTracker import *
from NewsLoader import NewsLoader
from Screener import Screener

import threading
import pandas as pd
import math
import json
import os

class Dashboard:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.reddit = RedditTracker(self.data_dir)
        self.news = NewsLoader()
        

    def read(self, filename):
        if os.path.exists(filename):
            f = open(filename, "r")
            data = f.read()
            try:
                return json.loads(data)
            except:
                return data
        return None

    def write(self, filename, data):
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            if isinstance(data, str):
                f = open(filename, "w")
                f.write(data)
                f.close()
            else:
                with open(filename, 'w') as file:
                    json.dump(data, file, indent=4)
            return True
        except Exception as e:
            print(f"Error writing to file {filename}: {e}")
            return False
    
    # Function stack / parallel execution
    def stack(fn_list, onCompleted):
        """
        Execute all functions in fn_list in parallel, then call onCompleted() when all are finished.
        """
        threads = []
        for fn in fn_list:
            thread = threading.Thread(target=fn)
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        onCompleted()
    
    def refreshAll(self, refreshReddit=True, refreshStocks=True, count=50, merge_type="Trending"):
        print(refreshReddit, refreshStocks)
        self.data = {
            "news": None,   # dict, symbol-index
            "news_table": None,   # dict, symbol-index
            "news_raw": None, # array of dict
            "reddit_table": None, # df, table of reddit data
            "marketCycles": None,
            "symbol_table": None # df [Ticker  News  Rank  Rank Change  Mentions  Mentions Change  Upvotes]
        }
        
        self.refreshNews()
        self.refreshReddit(refreshReddit)
        
        # Filter reddit by rank
        reddit_table = self.data["reddit_table"].sort_values(by=['rank'], ascending=True)

        # Limit
        reddit_table = reddit_table.head(count)

        # Get symbols
        symbols = list(reddit_table.index)

        print("\n\n=== SYMBOLS ===")
        print(symbols)

        # Get the stock data for those
        self.refreshStockData(symbols, refreshStocks, merge_type)

        # Merge
        table = self.data["reddit_table"].merge(self.data["news_table"], on="ticker", how="outer").merge(self.data["marketCycles"], on="ticker", how="outer")
        

        # Filter out what we don't need
        table = table[(table["rank"] > 0)] # | (table["News"] > 0)

        table = table.sort_values(by=['rank'], ascending=True)

        print("\n\n=== TABLE ===")
        print(table)

        self.data["symbol_table"] = table
        
        #self.mergeData(refreshStocks, count)

        #self.write(f"{self.data_dir}/data.json", self.data)
    

    # Refresh the stock data for given symbols
    def refreshStockData(self, symbols, refreshData=True, cache_name=""):
        print("refreshStockData()", symbols, refreshData)
        timeframes = ["1d", "1wk", "1mo"]

        cache_filename = f"{self.data_dir}/marketcycles_{cache_name}.csv"
        if not os.path.exists(cache_filename) or refreshData:
            # Refresh the data
            print("-- Refreshing the stock data --")
            self.screener = Screener(self.data_dir, symbols=symbols)
            self.screener.refreshData(timeframes=timeframes)
            raw_data = self.screener.build(timeframes=timeframes)
            
            timeframes = ["", "_week", "_month"]
            timeframe_labels = ["day", "week", "month"]
            keeps = []
            rename = {}
            for n, timeframe in enumerate(timeframes):
                keeps.append(f"Prev_MarketCycle{timeframe}")
                keeps.append(f"MarketCycle{timeframe}")
                rename[f"Prev_MarketCycle{timeframe}"] = f"prev_{timeframe_labels[n]}"
                rename[f"MarketCycle{timeframe}"] = f"{timeframe_labels[n]}"

            self.data["marketCycles"] = raw_data[keeps].rename(columns=rename)
            self.data["marketCycles"]["ticker"] = self.data["marketCycles"].index
            # Save with the ticker column
            self.data["marketCycles"].to_csv(cache_filename, index=False)
            # Convert to index
            #self.data["marketCycles"].set_index("ticker")
            self.data["marketCycles"].rename_axis('ticker')

        else:
            print("-- Loading the stock data from file --")
        self.data["marketCycles"] = pd.read_csv(cache_filename)
        # Set the index again
        self.data["marketCycles"] = self.data["marketCycles"].set_index("ticker")
        
        print("\n\n=== STOCKS ===")
        print(self.data["marketCycles"])


    # Refresh & reformat the news
    # SAve the table and indexed lists
    def refreshNews(self):
        newsList = self.news.load_news(days=7, limit=1000)
        self.data["news_raw"] = newsList
        self.data["news"] = {}
        for item in newsList:
            for insight in item["insights"]:
                if insight["ticker"] not in self.data["news"]:
                    self.data["news"][insight["ticker"]] = []
                self.data["news"][insight["ticker"]].append({
                    "publisher": item["publisher"]["name"],
                    "title": item["title"],
                    "description": item["description"],
                    "sentiment": insight["sentiment"],
                    "reasoning": insight["sentiment_reasoning"],
                })
        news_array = []
        for symbol in self.data["news"]:
            newsCount = len(self.data["news"][symbol])
            positiveNewsCount = sum(1 for item in self.data["news"][symbol] if item.get("sentiment") == "positive")
            negativeNewsCount = sum(1 for item in self.data["news"][symbol] if item.get("sentiment") == "negative")
            news_array.append({
                "ticker": symbol,
                "News": newsCount,
                "News (Positive)": int(positiveNewsCount/newsCount*100),
                "News (Negative)": int(negativeNewsCount/newsCount*100),
            })
        news_df = pd.DataFrame(news_array)
        
        self.data["news_table"] = news_df
        # Ticker as index
        self.data["news_table"]["Ticker"] = self.data["news_table"]["ticker"]
        self.data["news_table"] = self.data["news_table"].set_index("ticker")
        self.data["news_table"] = self.data["news_table"].drop(columns=["Ticker"])
        
        print("\n\n=== NEWS ===")
        print(self.data["news_table"])
    

    # Refresh Reddit stats, save the table
    def refreshReddit(self, refreshData=True):
        print("refreshReddit()", refreshData)
        if refreshData:
            self.reddit.refresh(pages=10)
        self.data["reddit_table"] = self.reddit.all(as_dict=False)
        # Ticker as index
        self.data["reddit_table"]["Ticker"] = self.data["reddit_table"]["ticker"]
        self.data["reddit_table"] = self.data["reddit_table"].set_index("ticker")
        # Extra columns
        self.data["reddit_table"]["rank change"] = self.data["reddit_table"]["rank"] - self.data["reddit_table"]["rank_24h_ago"]
        self.data["reddit_table"]["mentions change"] = self.data["reddit_table"]["mentions"] - self.data["reddit_table"]["mentions_24h_ago"]
        
        self.data["reddit_table"] = self.data["reddit_table"].drop(columns=["Ticker"])
        
        print("\n\n=== REDDIT ===")
        print(self.data["reddit_table"])

    
    # Refresh the Symbol Table
    def mergeData(self, refreshData=True, top=50, merge_type="Trending"):
        print("mergeData()", refreshData, merge_type)
        self.data["symbol_table"] = None
        table = []

        for symbol in self.data["news"]:
            redditData = self.data["reddit"][symbol] if symbol in self.data["reddit"] else None
            newsCount = len(self.data["news"][symbol])
            positiveNewsCount = sum(1 for item in self.data["news"][symbol] if item.get("sentiment") == "positive")
            negativeNewsCount = sum(1 for item in self.data["news"][symbol] if item.get("sentiment") == "negative")

            table.append({
                "Ticker": symbol,
                "Name": "-" if redditData is None else redditData["name"],
                "Reddit Rank": 0 if redditData is None else redditData["rank"],
                "Reddit Rank Change": 0 if redditData is None else redditData["rank"] - (redditData["rank_24h_ago"] or 0),
                "Reddit Mentions": 0 if redditData is None else redditData["mentions"],
                "Reddit Mentions Change": 0 if redditData is None else redditData["mentions"] - (redditData["mentions_24h_ago"] or 0),
                "Reddit Upvotes": 0 if redditData is None else redditData["upvotes"],
                "News": newsCount,
                "News (Positive)": str(int(positiveNewsCount/newsCount*100))+"%",
                "News (Negative)": str(int(negativeNewsCount/newsCount*100))+"%",
            })
        self.data["symbol_table"] = pd.DataFrame(table)
        if merge_type == "Trending":
            self.data["symbol_table"] = self.data["symbol_table"][self.data["symbol_table"]["Reddit Rank"] > 0]
            self.data["symbol_table"] = self.data["symbol_table"].sort_values(by=['Reddit Rank'], ascending=True)
        print(self.data["symbol_table"])

        # Filter the table
        #self.data["symbol_table"] = self.data["symbol_table"][(self.data["symbol_table"]["News"] > 1) & (self.data["symbol_table"]["Reddit Mentions"] > 1)]
        #self.data["symbol_table"] = self.data["symbol_table"][self.data["symbol_table"]["Reddit Mentions"] > 1]

        # Limit
        if top is not None:
            self.data["symbol_table"] = self.data["symbol_table"].head(top)

        # Re-index on ticker
        self.data["symbol_table"] = self.data["symbol_table"].set_index("Ticker")

        # Stock Data
        # Fetch the stock data for the tickers in the table
        self.refreshStockData(list(self.data["symbol_table"].index), refreshData)
        self.data["symbol_table"] = self.data["symbol_table"].join(self.data["marketCycles"], how="outer")

        print(self.data["symbol_table"])

        # ADD: Day change, 3-day change, week change, month change, year high, year low
        
        """
            Ticker  News  Rank  Rank Change  Mentions  Mentions Change  Upvotes
        0      DIS    10   272           14         1             -2.0        1
        1     NFLX     8    64          -33         8              2.0       13
        2     QCOM     6   109         -145         4              3.0        7
        3      AMD    15     1           -3       256            -17.0     1548
        4     NVDA    64     2            1       133           -214.0      482
        ..     ...   ...   ...          ...       ...              ...      ...
        979  MHGVY     1     0            0         0              0.0        0
        980    MAG     1   152           52         2              1.0       19
        981   PNTG     1     0            0         0              0.0        0
        982   VCIG     1     0            0         0              0.0        0
        983    GCT     1     0            0         0              0.0        0
        """
    
    


if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.refreshAll()