from RedditTracker import *
from NewsLoader import NewsLoader
from Screener import Screener

import pandas as pd
import math
import json
import os

class Dashboard:
    def __init__(self):
        self.data_dir = "data/test"
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
    
    def refreshAll(self, refreshReddit=True, refreshStocks=True, count=50, merge_type="Trending"):
        print(refreshReddit, refreshStocks)
        self.data = {
            "news": None,   # dict, symbol-index
            "news_raw": None, # array of dict
            "reddit": None, # dict, symbol-index
            "marketCycles": None,
            "symbol_table": None # df [Ticker  News  Rank  Rank Change  Mentions  Mentions Change  Upvotes]
        }
        self.refreshNews()
        self.refreshReddit(refreshReddit)
        self.mergeData(refreshStocks, count)
        

        #self.write(f"{self.data_dir}/data.json", self.data)
    
    def refreshStockData(self, symbols, refreshData=True):
        print("refreshStockData()", refreshData)
        self.screener = Screener(self.data_dir, symbols=symbols)
        if refreshData:
            self.screener.refreshData()

        if "marketCycles_raw" not in self.data or refreshData:
            self.data["marketCycles_raw"] = self.screener.build(timeframes=["1d", "1wk", "1mo"])
        
        data = self.data["marketCycles_raw"]
        timeframes = ["", "_week", "_month"]
        timeframe_labels = ["day", "week", "month"]
        keeps = []
        rename = {}
        for n, timeframe in enumerate(timeframes):
            keeps.append(f"Prev_MarketCycle{timeframe}")
            keeps.append(f"MarketCycle{timeframe}")
            rename[f"Prev_MarketCycle{timeframe}"] = f"prev_{timeframe_labels[n]}"
            rename[f"MarketCycle{timeframe}"] = f"{timeframe_labels[n]}"

        self.data["marketCycles"] = data[keeps].rename(columns=rename)#.to_dict(orient="index")
        #print(self.data["marketCycles"])


    # Refresh & reformat the news
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
    
    # Refresh & reformat Reddit stats
    def refreshReddit(self, refreshData=True):
        print("refreshReddit()", refreshData)
        if refreshData:
            self.reddit.refresh(pages=3)
        self.data["reddit"] = {}
        redditData = self.reddit.all(as_dict=True)
        for item in redditData:
            self.data["reddit"][item["ticker"]] = item
        
    
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