from StockData import StockData
from MarketCycle import MarketCycle
from tqdm import tqdm
import time
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.10+

class Screener:
    def __init__(self, data_dir="./data", symbols=[]):
        print("Screener v2.0")
        self.stockData = StockData(cache_dir=data_dir, symbols=symbols)
        self.cutoff_date = None

    def refreshData(self, timeframes=[]):
        TIMEFRAME_ORDER = {
            "1min": 1,
            "5min": 5,
            "15min": 15,
            "30min": 30,
            "1h": 60,
            "1d": 1440,
            "1wk": 10080,
            "1mo": 43200
        }

        if "1min" in timeframes or "5min" in timeframes or "15min" in timeframes or "30min" in timeframes or "1h" in timeframes:
            print("Refreshing intraday data...")
            self.stockData.refresh_all("1min")
        if "1h" in timeframes or "1d" in timeframes or "1wk" in timeframes or "1mo" in timeframes:
            print("Refreshing daily data...")
            self.stockData.refresh_all("1d")
        # Optionally, add sleep if needed.
        # time.sleep(1)

    def build(self, timeframes=["1min", "30min", "1d", "1wk", "1mo"], date=None):
        """
        Build a combined DataFrame with data from the requested timeframes.
        If a cutoff date is provided (in local time), it is converted to UTC and used for filtering.
        """
        if date is not None:
            local_dt = pd.to_datetime(date)
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            self.cutoff_date = local_dt.astimezone(ZoneInfo("UTC"))
            print(f"Cutoff date set to UTC: {self.cutoff_date}")
        else:
            self.cutoff_date = None

        data_frames = {}
        transformed_frames = {}

        for timeframe in timeframes:
            print(f"\nGetting raw data for timeframe: {timeframe}")
            data = self.stockData.getAll(interval=timeframe)
            data = self.cutOffData(data, timeframe=timeframe, until=self.cutoff_date)
            data_frames[timeframe] = data

            symbols = list(data.columns.get_level_values(0).unique())
            rows = []
            for symbol in tqdm(symbols, desc=f"Processing {timeframe} data"):
                row = self.buildSymbol(symbol, timeframe)
                if row is not None:
                    rows.append(row)
            if rows:
                df_transformed = pd.concat(rows, axis=1).T.reset_index(drop=True)
                df_transformed.set_index("symbol", inplace=True)
            else:
                df_transformed = pd.DataFrame()
            transformed_frames[timeframe] = df_transformed

        # Combine the transformed data from each timeframe.
        combined = None
        for tf, df in transformed_frames.items():
            if not df.empty:
                if tf == "1d":
                    df_temp = df
                elif tf == "1wk":
                    df_temp = df.rename(columns=lambda x: f"{x}_week")
                elif tf == "1mo":
                    df_temp = df.rename(columns=lambda x: f"{x}_month")
                else:
                    df_temp = df.rename(columns=lambda x: f"{x}_{tf}")
                print(f"Columns for timeframe {tf}: {df_temp.columns.tolist()}")
                if combined is None:
                    combined = df_temp
                else:
                    combined = combined.join(df_temp, how="outer")
        return combined

    def cutOffData(self, df, timeframe="1d", until=None):
        data = df.copy()
        if until is not None:
            # If the DataFrame's index is tz-naive but 'until' is tz-aware, convert 'until' to naive.
            if data.index.tz is None and until.tzinfo is not None:
                until = until.tz_localize(None)
            if timeframe in {"1min", "5min", "15min", "30min", "1h", "1d"}:
                data = data[data.index <= until]
            elif timeframe in {"1wk", "1mo"}:
                # For weekly/monthly, keep the period ending at or before 'until'
                last_period = data.index[data.index <= until].max()
                if pd.notna(last_period):
                    data = data[data.index <= last_period]
        return data

    def buildSymbol(self, symbol, timeframe="1d"):
        stock = self.stockData.get(symbol, timeframe)
        stock = self.cutOffData(stock, timeframe=timeframe, until=self.cutoff_date)
        if stock is None or stock.empty:
            return None
        mc = MarketCycle(stock)
        marketCycle = mc.build()
        marketCycle["symbol"] = symbol
        if marketCycle.empty:
            return None
        row = marketCycle.iloc[-1].copy()
        row["Date"] = marketCycle.index[-1]
        return row

    def bounceUp(self, data, name="", level=30):
        data = data.copy()
        return data[
            (data[f"Prev2_MarketCycle{name}"] >= data[f"Prev_MarketCycle{name}"])
            & (data[f"Prev_MarketCycle{name}"] <= data[f"MarketCycle{name}"])
            & (data[f"Prev_MarketCycle{name}"] <= level)
        ]

    def bounceDown(self, data, name="", level=30):
        data = data.copy()
        return data[
            (data[f"Prev2_MarketCycle{name}"] <= data[f"Prev_MarketCycle{name}"])
            & (data[f"Prev_MarketCycle{name}"] >= data[f"MarketCycle{name}"])
            & (data[f"Prev_MarketCycle{name}"] >= level)
        ]

    def trendUp(self, data, name="", level=30):
        data = data.copy()
        return data[
            (data[f"Prev_MarketCycle{name}"] <= data[f"MarketCycle{name}"])
            & (data[f"Prev_MarketCycle{name}"] <= level)
        ]

    def trendDown(self, data, name="", level=30):
        data = data.copy()
        return data[
            (data[f"Prev_MarketCycle{name}"] >= data[f"MarketCycle{name}"])
            & (data[f"Prev_MarketCycle{name}"] >= level)
        ]

    def moreThan(self, data, name="", level=30):
        data = data.copy()
        return data[data[f"MarketCycle{name}"] >= level]

    def lessThan(self, data, name="", level=30):
        data = data.copy()
        return data[data[f"MarketCycle{name}"] <= level]

    def screen(self, data, filters):
        filtered = data.copy()
        for filt in filters:
            if filt[0] == "bounceUp":
                filtered = self.bounceUp(filtered, filt[1], filt[2])
            elif filt[0] == "bounceDown":
                filtered = self.bounceDown(filtered, filt[1], filt[2])
            elif filt[0] == "trendUp":
                filtered = self.trendUp(filtered, filt[1], filt[2])
            elif filt[0] == "trendDown":
                filtered = self.trendDown(filtered, filt[1], filt[2])
            elif filt[0] == "moreThan":
                filtered = self.moreThan(filtered, filt[1], filt[2])
            elif filt[0] == "lessThan":
                filtered = self.lessThan(filtered, filt[1], filt[2])
        return filtered

    def getCutoffDate(self):
        return self.cutoff_date

    def get_timeseries(self, symbol, last=20):
        # Daily timeseries:
        daily_data = self.stockData.get(symbol, "1d")
        daily_data = self.cutOffData(daily_data, timeframe="1d", until=self.cutoff_date)
        if daily_data is not None and not daily_data.empty:
            if self.cutoff_date:
                daily_data = daily_data[daily_data.index <= self.cutoff_date]
            daily_mc = MarketCycle(daily_data).build()[["MarketCycle"]].tail(last)
            daily_close = daily_data["Close"].tail(last).reset_index(drop=True)
        else:
            daily_mc = pd.DataFrame({"MarketCycle": [0] * last})
            daily_close = pd.Series([0] * last, name="Close_daily")

        # Intraday timeseries example using 15min aggregation:
        intraday_data = self.stockData.get(symbol, "15min")
        intraday_data = self.cutOffData(intraday_data, timeframe="15min", until=self.cutoff_date)
        if intraday_data is not None and not intraday_data.empty:
            if self.cutoff_date:
                intraday_data = intraday_data[intraday_data.index <= self.cutoff_date]
            intraday_mc = MarketCycle(intraday_data).build()[["MarketCycle"]].rename(
                columns={"MarketCycle": "MarketCycle_15min"}
            ).tail(last)
            intraday_close = intraday_data["Close"].tail(last).reset_index(drop=True)
        else:
            intraday_mc = pd.DataFrame({"MarketCycle_15min": [0] * last})
            intraday_close = pd.Series([0] * last, name="Close_15min")

        combined = pd.concat(
            [
                daily_mc.reset_index(drop=True),
                intraday_mc.reset_index(drop=True),
                daily_close.rename("Close_daily"),
                intraday_close.rename("Close_15min"),
            ],
            axis=1,
        )
        combined.fillna(0, inplace=True)
        return combined

    def historical(self, symbol="NVDA", timeframes=["1min", "30min", "1d", "1wk", "1mo"], date="2025-01-30 10:00:00"):
        """
        Return a DataFrame containing the historical data for the given symbol.
        The index is the datetime of the smallest timeframe data.
        Columns include the OHLCV data (from the smallest timeframe)
        plus one MarketCycle value (renamed as MarketCycle_{suffix})
        for each timeframe requested.
        
        The `date` parameter (given in local time) is the last data point to return.
        """
        # Convert the provided date (local) to UTC.
        local_dt = pd.to_datetime(date)
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        cutoff_utc = local_dt.astimezone(ZoneInfo("UTC"))
        print(f"Historical data cutoff (UTC): {cutoff_utc}")

        # Define an ordering for timeframes (lower number means finer resolution, approximate minutes)
        TIMEFRAME_ORDER = {
            "1min": 1,
            "5min": 5,
            "15min": 15,
            "30min": 30,
            "1h": 60,
            "1d": 1440,
            "1wk": 10080,
            "1mo": 43200
        }
        # Choose the smallest timeframe from the provided list.
        base_tf = min(timeframes, key=lambda tf: TIMEFRAME_ORDER.get(tf, float("inf")))
        print(f"Base timeframe: {base_tf}")

        # Helper function: determine suffix from timeframe.
        def get_suffix(tf):
            if tf == "1wk":
                return "week"
            elif tf == "1mo":
                return "month"
            else:
                return tf

        # Get the base (smallest) timeframe data for the symbol.
        base_data = self.stockData.get(symbol, base_tf)
        base_data = self.cutOffData(base_data, timeframe=base_tf, until=cutoff_utc)
        if base_data.empty:
            print(f"No base data for {symbol} at {base_tf}")
            return pd.DataFrame()

        # We want only the OHLCV columns from the base data.
        # (Assuming these columns exist: Open, High, Low, Close, Volume, Trades)
        OHLCV = ["Open", "High", "Low", "Close", "Volume", "Trades"]
        base_ohlcv = base_data[OHLCV].copy()

        # Compute the MarketCycle for the base data and select only the main value.
        base_mc = MarketCycle(base_data).build()[["MarketCycle"]]
        base_mc = base_mc.rename(columns=lambda col: f"{col}_{get_suffix(base_tf)}")
        # Ensure the index has a name for merging.
        base_ohlcv.index.name = "datetime"
        base_mc.index.name = "datetime"

        # Start building the result DataFrame with the base OHLCV and its MarketCycle column.
        result = base_ohlcv.copy()
        result = result.join(base_mc, how="left")

        # For each additional timeframe, merge its MarketCycle value onto the base data.
        for tf in timeframes:
            if tf == base_tf:
                continue
            tf_data = self.stockData.get(symbol, tf)
            tf_data = self.cutOffData(tf_data, timeframe=tf, until=cutoff_utc)
            if tf_data.empty:
                print(f"No data for timeframe {tf} for {symbol}")
                continue
            tf_mc = MarketCycle(tf_data).build()[["MarketCycle"]]
            suffix = get_suffix(tf)
            tf_mc = tf_mc.rename(columns=lambda col: f"{col}_{suffix}")
            # Ensure the index name is set.
            tf_mc.index.name = "datetime"
            # Reset indexes for merge_asof.
            base_df = result.reset_index().sort_values("datetime")
            tf_df = tf_mc.reset_index().sort_values("datetime")
            # Merge using merge_asof to fill the MarketCycle value backward.
            merged = pd.merge_asof(base_df, tf_df, on="datetime", direction="backward")
            merged = merged.set_index("datetime")
            result = merged.copy()

        # Finally, restrict the result to rows at or before the cutoff.
        if result.index.tz is None and cutoff_utc.tzinfo is not None:
            cutoff_utc_naive = cutoff_utc.tz_localize(None)
        else:
            cutoff_utc_naive = cutoff_utc
        result = result[result.index <= cutoff_utc_naive]
        return result

