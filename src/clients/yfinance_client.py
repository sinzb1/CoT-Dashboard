import json
import pandas as pd
import yfinance as yf
from datetime import date


# Yahoo Finance continuous futures tickers for the relevant commodities
COMMODITY_TICKERS = {
    "Gold":           "GC=F",
    "Silver":         "SI=F",
    "Copper":         "HG=F",
    "Platinum":       "PL=F",
    "Palladium":      "PA=F",
    "Crude_Oil_WTI":  "CL=F",
}

# Yahoo Finance tickers for macro factors (replaces FRED)
MACRO_TICKERS = {
    "vix":       "^VIX",       # CBOE Volatility Index
    "usd_index": "DX-Y.NYB",   # US Dollar Index
    "usd_chf":   "CHF=X",      # USD/CHF
}


class YFinanceClient:
    def __init__(self, config_path="config/config.json"):
        with open(config_path) as f:
            config = json.load(f)

        self.years_back = config.get("pipeline", {}).get("years_back", 4)
        self.tickers = COMMODITY_TICKERS
        self.macro_tickers = MACRO_TICKERS

    def _default_date_range(self):
        end = date.today()
        start = date(end.year - self.years_back, end.month, end.day)
        return start, end

    def fetch_close_prices(self) -> pd.DataFrame:
        """Fetch daily close prices for all configured commodity futures.

        Returns a DataFrame with columns: date, gold, silver, copper, platinum, palladium
        """
        start, end = self._default_date_range()

        frames = []
        for commodity, ticker in self.tickers.items():
            col_name = commodity.lower()
            try:
                df = yf.download(
                    ticker,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    progress=False,
                    auto_adjust=True,
                )
                if df.empty:
                    print(f"[YFinanceClient] No data returned for {commodity} ({ticker})")
                    continue

                # yfinance >= 0.2.x returns MultiIndex columns (Price, Ticker)
                # Ticker names in columns may be normalized differently across versions,
                # so we search for the Close column by first level instead of exact key.
                if isinstance(df.columns, pd.MultiIndex):
                    close_col = next(
                        (c for c in df.columns if c[0] == "Close"), None
                    )
                    if close_col is None:
                        raise ValueError(f"No 'Close' column found for {ticker}: {list(df.columns)}")
                    close = df[close_col].rename(col_name)
                else:
                    close = df["Close"].rename(col_name)

                close_df = close.reset_index()
                close_df.columns = ["date", col_name]
                frames.append(close_df)
                print(f"[YFinanceClient] Retrieved {len(close_df)} rows for {commodity} ({ticker})")
            except Exception as e:
                print(f"[YFinanceClient] Error fetching {commodity} ({ticker}): {e}")

        if not frames:
            return pd.DataFrame(columns=["date"])

        # Outer-merge all commodity close prices on date
        result = frames[0]
        for f in frames[1:]:
            result = result.merge(f, on="date", how="outer")

        result = result.sort_values("date").reset_index(drop=True)
        return result

    def fetch_macro_close_prices(self) -> pd.DataFrame:
        """Fetch daily close prices for macro factors (VIX, USD Index, USD/CHF).

        Returns a DataFrame with columns: date, vix, usd_index, usd_chf
        """
        start, end = self._default_date_range()

        frames = []
        for col_name, ticker in self.macro_tickers.items():
            try:
                df = yf.download(
                    ticker,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    progress=False,
                    auto_adjust=True,
                )
                if df.empty:
                    print(f"[YFinanceClient] No data returned for {col_name} ({ticker})")
                    continue

                if isinstance(df.columns, pd.MultiIndex):
                    close_col = next(
                        (c for c in df.columns if c[0] == "Close"), None
                    )
                    if close_col is None:
                        raise ValueError(f"No 'Close' column found for {ticker}: {list(df.columns)}")
                    close = df[close_col].rename(col_name)
                else:
                    close = df["Close"].rename(col_name)

                close_df = close.reset_index()
                close_df.columns = ["date", col_name]
                frames.append(close_df)
                print(f"[YFinanceClient] Retrieved {len(close_df)} rows for {col_name} ({ticker})")
            except Exception as e:
                print(f"[YFinanceClient] Error fetching {col_name} ({ticker}): {e}")

        if not frames:
            return pd.DataFrame(columns=["date"])

        result = frames[0]
        for f in frames[1:]:
            result = result.merge(f, on="date", how="outer")

        result = result.sort_values("date").reset_index(drop=True)
        return result
