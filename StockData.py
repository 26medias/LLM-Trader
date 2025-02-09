import os
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import json

POLYGON_API_KEY = os.environ['POLYGON_API_KEY']

# (Optional) For daily data, download from this date
DAILY_START_DATE = "2022-01-01"

# (Optional) For intraday data, download only the last N days (Polygon’s minute‐data can be huge)
INTRADAY_DAYS = 30

# Allowed intervals (you can expand these lists)
INTRADAY_INTERVALS = {"1min", "5min", "15min", "30min", "1h"}
DAILY_INTERVALS = {"1d", "1wk", "1mo"}

# Mapping for intraday aggregation (resample rule for pd.resample)
INTRADAY_RULES = {
    "1min": "min",
    "5min": "5min",
    "15min": "15min",
    "30min": "30min",
    "1h": "60min"
}


# Mapping for daily aggregation
DAILY_RULES = {
    "1d": "D",
    "1wk": "W-FRI",
    # Change "M" to "ME" to avoid the FutureWarning.
    "1mo": "ME"
}


class StockData:
    def __init__(
        self,
        cache_dir="./data",
        period="max",
        api_key=POLYGON_API_KEY,
        intraday_days=INTRADAY_DAYS,
        daily_start_date=DAILY_START_DATE,
        symbols=[]
    ):
        self.cache_dir = cache_dir
        self.api_key = api_key
        self.period = period
        self.intraday_days = intraday_days
        self.daily_start_date = daily_start_date

        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

        # Load symbols (download from Wikipedia if needed)
        #if not os.path.exists(SYMBOLS_FILE):
        #    self.download_symbols_from_wikipedia(SYMBOLS_FILE)
        self.tickers = symbols#self.load_symbols(SYMBOLS_FILE)

        # Load application settings (for last update times)
        self.app_settings_file = os.path.join(self.cache_dir, "app_settings.json")
        if os.path.exists(self.app_settings_file):
            with open(self.app_settings_file, "r") as f:
                self.app_settings = json.load(f)
        else:
            self.app_settings = {"last_update": {}}

    def load_symbols(self, file_path):
        df = pd.read_csv(file_path)
        symbols = df["Symbol"].dropna().unique().tolist()
        return symbols

    def download_symbols_from_wikipedia(self, file_path):
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(url)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", {"id": "constituents"})
        tickers = []
        for row in table.findAll("tr")[1:]:
            ticker = row.findAll("td")[0].text.strip()
            tickers.append(ticker)
        df = pd.DataFrame({"Symbol": tickers})
        df.to_csv(file_path, index=False)

    def _cache_filename(self, base_interval):
        # We cache only base intervals ("1min" or "1d")
        return os.path.join(self.cache_dir, f"{base_interval}-cached.pkl")

    def _load_data(self, filename):
        if os.path.exists(filename):
            return pd.read_pickle(filename)
        return None

    def _save_data(self, data, filename):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        data.to_pickle(filename)

    def _save_app_settings(self):
        with open(self.app_settings_file, "w") as f:
            json.dump(self.app_settings, f, indent=4)

    def fetch_intraday_data(self, symbol, start_date, end_date):
        # Use Polygon.io aggregates endpoint for 1-minute data.
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/{start_date}/{end_date}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": self.api_key,
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "results" in data:
            df = pd.DataFrame(data["results"])
            if df.empty:
                return pd.DataFrame()
            # Convert the millisecond timestamp to UTC-aware datetimes.
            df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df = df.rename(
                columns={
                    "o": "Open",
                    "h": "High",
                    "l": "Low",
                    "c": "Close",
                    "v": "Volume",
                    "n": "Trades",
                }
            )
            df = df[["Open", "High", "Low", "Close", "Volume", "Trades"]]
            return df
        return pd.DataFrame()

    def fetch_daily_data(self, symbol, start_date, end_date):
        # Use Polygon.io aggregates endpoint for daily data.
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": self.api_key,
        }
        response = requests.get(url, params=params)
        data = response.json()
        if "results" in data:
            df = pd.DataFrame(data["results"])
            if df.empty:
                return pd.DataFrame()
            # Convert to UTC-aware datetimes.
            df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            df = df.rename(
                columns={
                    "o": "Open",
                    "h": "High",
                    "l": "Low",
                    "c": "Close",
                    "v": "Volume",
                    "n": "Trades",
                }
            )
            df = df[["Open", "High", "Low", "Close", "Volume", "Trades"]]
            return df
        return pd.DataFrame()

    def fetch_data_for_symbol(self, symbol, base_interval):
        today = datetime.today()
        end_date = today.strftime("%Y-%m-%d")
        if base_interval == "1min":
            start_dt = today - timedelta(days=self.intraday_days)
            start_date = start_dt.strftime("%Y-%m-%d")
            df = self.fetch_intraday_data(symbol, start_date, end_date)
        elif base_interval == "1d":
            start_date = self.daily_start_date
            df = self.fetch_daily_data(symbol, start_date, end_date)
        else:
            df = pd.DataFrame()
        return df

    def refresh_all(self, base_interval):
        # Only support base intervals "1min" and "1d"
        if base_interval not in {"1min", "1d"}:
            raise ValueError("refresh_all supports only base intervals '1min' or '1d'")
        cache_file = self._cache_filename(base_interval)
        combined_data = self._load_data(cache_file)
        updated_data = {}
        today = datetime.today()
        end_date = today.strftime("%Y-%m-%d")
        for symbol in self.tickers:
            symbol_data = None
            if combined_data is not None and symbol in combined_data.columns.get_level_values(0):
                symbol_data = combined_data[symbol]
                last_date = symbol_data.index.max()
                # If last_date is tz-naive, assume it is UTC.
                if last_date.tzinfo is None:
                    last_date = last_date.tz_localize("UTC")
                # For incremental update, start a little after the last date.
                if base_interval == "1min":
                    next_dt = last_date + timedelta(minutes=1)
                else:
                    next_dt = last_date + timedelta(days=1)
                # Only update if there is new data available.
                if next_dt.date() < today.date():
                    new_df = self.fetch_data_for_symbol(symbol, base_interval)
                    if not new_df.empty:
                        new_df = new_df[new_df.index > last_date]
                    if new_df is not None and not new_df.empty:
                        symbol_data = pd.concat([symbol_data, new_df])
            else:
                symbol_data = self.fetch_data_for_symbol(symbol, base_interval)
            if symbol_data is not None and not symbol_data.empty:
                symbol_data = symbol_data[["Open", "High", "Low", "Close", "Volume", "Trades"]]
                # Ensure that the symbol's data index is tz-aware (assume UTC if tz-naive).
                if symbol_data.index.tz is None:
                    symbol_data.index = symbol_data.index.tz_localize("UTC")
                updated_data[symbol] = symbol_data
            # Optionally add a sleep here to respect API rate limits.
        if updated_data:
            # Ensure each DataFrame's index is tz-aware before concatenating.
            for sym, df in updated_data.items():
                if df.index.tz is None:
                    df.index = df.index.tz_localize("UTC")
            combined = pd.concat({sym: df for sym, df in updated_data.items()}, axis=1)
        else:
            combined = pd.DataFrame()
        self._save_data(combined, cache_file)
        self.app_settings["last_update"][base_interval] = datetime.now().isoformat()
        self._save_app_settings()
        return combined



    def aggregate_ohlcv(self, df, rule):
        if df.empty:
            return df
        agg_dict = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
            "Trades": "sum",
        }
        # If the index does not have a frequency, try to set it.
        if df.index.freq is None:
            try:
                df = df.asfreq("min")
            except Exception as e:
                print("Warning: could not set frequency on index:", e)
        df_agg = df.resample(rule).apply(agg_dict)
        df_agg = df_agg.dropna(how="all")
        return df_agg

    def get_resample_rule(self, interval):
        if interval in INTRADAY_INTERVALS:
            return INTRADAY_RULES[interval]
        elif interval in DAILY_INTERVALS:
            return DAILY_RULES[interval]
        else:
            raise ValueError(f"Interval {interval} not supported")

    def get(self, symbol, interval="1d"):
        # Return data for a single symbol at the requested interval.
        if interval in INTRADAY_INTERVALS:
            base_file = self._cache_filename("1min")
            base_data = self._load_data(base_file)
            if base_data is None or symbol not in base_data.columns.get_level_values(0):
                return pd.DataFrame()
            df = base_data[symbol]
            if interval != "1min":
                rule = self.get_resample_rule(interval)
                df = self.aggregate_ohlcv(df, rule)
            return df
        elif interval in DAILY_INTERVALS:
            base_file = self._cache_filename("1d")
            base_data = self._load_data(base_file)
            if base_data is None or symbol not in base_data.columns.get_level_values(0):
                return pd.DataFrame()
            df = base_data[symbol]
            if interval != "1d":
                rule = self.get_resample_rule(interval)
                df = self.aggregate_ohlcv(df, rule)
            return df
        else:
            return pd.DataFrame()

    def getAll(self, interval="1d"):
        # Return a multi-symbol DataFrame for the requested interval.
        if interval in INTRADAY_INTERVALS:
            base_file = self._cache_filename("1min")
            base_data = self._load_data(base_file)
            if base_data is None:
                return pd.DataFrame()
            if interval == "1min":
                return base_data
            else:
                rule = self.get_resample_rule(interval)
                aggregated = {}
                for symbol in base_data.columns.get_level_values(0).unique():
                    df = base_data[symbol]
                    aggregated[symbol] = self.aggregate_ohlcv(df, rule)
                if aggregated:
                    combined = pd.concat(aggregated, axis=1)
                    return combined
                return pd.DataFrame()
        elif interval in DAILY_INTERVALS:
            base_file = self._cache_filename("1d")
            base_data = self._load_data(base_file)
            if base_data is None:
                return pd.DataFrame()
            if interval == "1d":
                return base_data
            else:
                rule = self.get_resample_rule(interval)
                aggregated = {}
                for symbol in base_data.columns.get_level_values(0).unique():
                    df = base_data[symbol]
                    aggregated[symbol] = self.aggregate_ohlcv(df, rule)
                if aggregated:
                    combined = pd.concat(aggregated, axis=1)
                    return combined
                return pd.DataFrame()
        else:
            return pd.DataFrame()

    def Refresh(self, symbol, interval="1d"):
        # (Optional) Implement single-symbol refresh if needed.
        return self.get(symbol, interval)
