import json
import os
import time
import databento as db
import pandas as pd
import numpy as np
from datetime import date, timedelta


# Continuous symbols to fetch: calendar roll (.c.), 2nd and 3rd nearby
CONTINUOUS_SYMBOLS = [
    "GC.c.1", "GC.c.2",
    "SI.c.1", "SI.c.2",
    "HG.c.1", "HG.c.2",
    "PL.c.1", "PL.c.2",
    "PA.c.1", "PA.c.2",
    "CL.c.1", "CL.c.2",
]

# Mapping from Databento symbol to InfluxDB field name
SYMBOL_TO_FIELD = {
    "GC.c.1": "gold_2nd_close",
    "GC.c.2": "gold_3rd_close",
    "SI.c.1": "silver_2nd_close",
    "SI.c.2": "silver_3rd_close",
    "HG.c.1": "copper_2nd_close",
    "HG.c.2": "copper_3rd_close",
    "PL.c.1": "platinum_2nd_close",
    "PL.c.2": "platinum_3rd_close",
    "PA.c.1": "palladium_2nd_close",
    "PA.c.2": "palladium_3rd_close",
    "CL.c.1": "crude_oil_2nd_close",
    "CL.c.2": "crude_oil_3rd_close",
}


class DatabentoClient:
    """Fetches daily OHLCV data for continuous futures from Databento Historical API.

    Symbols: calendar-roll (.c.) 2nd and 3rd nearby for GC, SI, HG, PL, PA, CL.
    Dataset: GLBX.MDP3 (CME Globex).
    Only close prices are retained – OHLCV is not stored downstream.
    """

    DATASET = "GLBX.MDP3"
    MAX_RETRIES = 3
    RETRY_DELAY_S = 15

    def __init__(self, config_path: str = "config/config.json"):
        with open(config_path) as f:
            config = json.load(f)

        self.api_key = os.environ["DATABENTO_API_KEY"]
        self.years_back = config.get("pipeline", {}).get("years_back", 4)
        self._client = db.Historical(self.api_key)

    def _start_date(self) -> str:
        today = date.today()
        return date(today.year - self.years_back, today.month, today.day).isoformat()

    def _fetch_symbol(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch ohlcv-1d for a single continuous symbol with retry logic.

        Returns a two-column DataFrame: date (UTC), <field_name>.
        Returns an empty DataFrame on failure.
        """
        field = SYMBOL_TO_FIELD[symbol]

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                data = self._client.timeseries.get_range(
                    dataset=self.DATASET,
                    symbols=[symbol],
                    stype_in="continuous",
                    schema="ohlcv-1d",
                    start=start,
                    end=end,
                )
                df = data.to_df().reset_index()

                if df.empty:
                    print(f"[DatabentoClient] {symbol}: no data returned")
                    return pd.DataFrame(columns=["date", field])

                # First column after reset_index is ts_event (already UTC-aware)
                ts_col = df.columns[0]
                df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
                df = df.rename(columns={ts_col: "date", "close": field})
                df = df[["date", field]].copy()
                df[field] = pd.to_numeric(df[field], errors="coerce")
                df = df.sort_values("date").reset_index(drop=True)

                print(
                    f"[DatabentoClient] {symbol} ({field}): {len(df)} rows  "
                    f"{df['date'].min().date()} - {df['date'].max().date()}"
                )
                return df

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    print(
                        f"[DatabentoClient] {symbol} attempt {attempt} failed: {e} "
                        f"– retrying in {self.RETRY_DELAY_S}s"
                    )
                    time.sleep(self.RETRY_DELAY_S)
                else:
                    print(
                        f"[DatabentoClient] {symbol} failed after {self.MAX_RETRIES} "
                        f"attempts: {e}"
                    )
                    return pd.DataFrame(columns=["date", field])

    def fetch_continuous_close_prices(self) -> pd.DataFrame:
        """Fetch daily close prices for all configured continuous futures symbols.

        Returns a wide DataFrame with columns:
            date (UTC datetime), gold_2nd_close, gold_3rd_close, silver_2nd_close, ...

        Symbols with no data result in NaN columns (outer merge).
        """
        start = self._start_date()
        # Databento has ~1-day delay: yesterday is the latest fully available date
        end = (date.today() - timedelta(days=1)).isoformat()

        frames = []
        for sym in CONTINUOUS_SYMBOLS:
            df = self._fetch_symbol(sym, start, end)
            if not df.empty:
                frames.append(df)

        if not frames:
            print("[DatabentoClient] No data retrieved for any symbol.")
            return pd.DataFrame(columns=["date"])

        result = frames[0]
        for df in frames[1:]:
            result = result.merge(df, on="date", how="outer")

        result = result.sort_values("date").reset_index(drop=True)
        print(
            f"[DatabentoClient] Combined: {len(result)} date rows, "
            f"{len(result.columns) - 1} price columns"
        )
        return result
