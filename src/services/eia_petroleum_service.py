import pandas as pd

from src.clients.eia_client import EIAClient


class EIAPetroleumService:
    """Loads EIA weekly crude oil inventory data and aligns it to CoT dates.

    Alignment strategy (Option A, consistent with MacroPriceService and
    FuturesPriceService):

        EIA publishes week-ending dates (Fridays). CoT report dates are
        Tuesdays. For each CoT Tuesday we pick the most recent EIA observation
        on or before that Tuesday using merge_asof backward with a 7-day
        tolerance.

        Normal cadence example:
            EIA period end  Fri 2024-01-05  → matched to CoT Tue 2024-01-09
            (Tuesday is 4 days after the preceding Friday → within tolerance)

        The resulting timestamps are the CoT dates, identical to how
        macro_by_date and futures_prices are stored in InfluxDB.
    """

    # 7-day tolerance: covers the normal 4-day gap (Fri→Tue) plus a 3-day
    # buffer for holiday weeks where EIA may delay publication.
    _ALIGNMENT_TOLERANCE = pd.Timedelta(days=7)

    def __init__(self):
        self.client = EIAClient()

    def load_dataframe(self, start_date=None) -> pd.DataFrame:
        """Load raw weekly crude oil stock data from EIA API.

        Returns a DataFrame with columns:
            period  – datetime (UTC)
            value   – float (thousands of barrels, kb)
        """
        return self.client.fetch_crude_oil_stocks(start_date=start_date)

    def align_to_cot_dates(
        self, stocks_df: pd.DataFrame, cot_dates: pd.Series
    ) -> pd.DataFrame:
        """Align EIA weekly inventory data to CoT dates.

        Parameters
        ----------
        stocks_df : DataFrame with columns 'period' (UTC datetime) and 'value'
        cot_dates : Series of CoT report dates (Tuesdays)

        Returns
        -------
        DataFrame with columns:
            date                 – CoT-aligned timestamp (UTC)
            crude_oil_stocks_kb  – crude oil stocks in thousands of barrels
        """
        if stocks_df.empty:
            return pd.DataFrame(columns=["date", "crude_oil_stocks_kb"])

        # Rename 'value' to the canonical field name used in InfluxDB
        stocks_df = stocks_df.rename(columns={"value": "crude_oil_stocks_kb"})

        if cot_dates is not None and len(cot_dates) > 0:
            cot_dt = (
                pd.to_datetime(cot_dates, utc=True)
                .astype("datetime64[s, UTC]")
                .drop_duplicates()
                .sort_values()
                .reset_index(drop=True)
            )
            cot_ref = pd.DataFrame({"cot_date": cot_dt})

            stocks_sorted = (
                stocks_df.rename(columns={"period": "date"})
                .sort_values("date")
                .reset_index(drop=True)
            )

            merged = pd.merge_asof(
                cot_ref,
                stocks_sorted,
                left_on="cot_date",
                right_on="date",
                direction="backward",
                tolerance=self._ALIGNMENT_TOLERANCE,
            )

            merged["date"] = merged["cot_date"]
            merged = merged.drop(columns=["cot_date"])
            merged = merged.dropna(subset=["crude_oil_stocks_kb"])

            print(
                f"[EIAPetroleumService] Aligned {len(merged)} EIA inventory points to CoT dates"
            )
            return merged.reset_index(drop=True)

        else:
            # Fallback: no CoT dates available – return raw data unchanged
            result = stocks_df.rename(columns={"period": "date"}).copy()
            print(
                f"[EIAPetroleumService] No CoT dates provided – "
                f"returning {len(result)} raw EIA points (fallback)"
            )
            return result

    def load_aligned(self, cot_dates: pd.Series = None, start_date=None) -> pd.DataFrame:
        """Load EIA crude oil stocks and align to CoT dates.

        Returns a DataFrame with columns 'date' and 'crude_oil_stocks_kb'.
        """
        df = self.load_dataframe(start_date=start_date)
        return self.align_to_cot_dates(df, cot_dates)
