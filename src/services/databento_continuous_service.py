import pandas as pd
import numpy as np

from src.clients.databento_client import DatabentoClient, SYMBOL_TO_FIELD


# Canonical InfluxDB field names for the deferred measurement
DEFERRED_FIELDS = list(SYMBOL_TO_FIELD.values())


class DatabentoContinuousService:
    """Loads 2nd- and 3rd-nearby continuous futures close prices via Databento
    and aligns them to CoT weekly dates (Tuesdays).

    Alignment strategy is identical to FuturesPriceService and MacroPriceService:
      - merge_asof backward with 4-day tolerance against CoT dates
      - Fallback: keep only Tuesday observations when no CoT dates are provided
    """

    def __init__(self):
        self.client = DatabentoClient()

    def load_dataframe(self, start_date=None) -> pd.DataFrame:
        """Fetch daily close prices for all deferred continuous futures symbols.

        Returns a wide DataFrame with columns:
            date (UTC), gold_2nd_close, gold_3rd_close, silver_2nd_close, ...
        """
        df = self.client.fetch_continuous_close_prices(start_date=start_date)

        if df.empty or "date" not in df.columns:
            return pd.DataFrame(columns=["date"])

        df["date"] = pd.to_datetime(df["date"], utc=True)
        df = df.sort_values("date").reset_index(drop=True)

        value_cols = [c for c in df.columns if c != "date"]
        df[value_cols] = (
            df[value_cols]
            .replace({"": np.nan, "NaN": np.nan, None: np.nan})
            .apply(pd.to_numeric, errors="coerce")
        )
        return df

    def align_to_cot_dates(
        self, prices_df: pd.DataFrame, cot_dates: pd.Series
    ) -> pd.DataFrame:
        """Align daily deferred futures prices to CoT weekly dates (Tuesday).

        Identical strategy to FuturesPriceService.align_to_cot_dates:
          - merge_asof backward, tolerance 4 days
          - Fallback: Tuesday filter when cot_dates is empty
        """
        if prices_df.empty:
            return prices_df

        if cot_dates is not None and len(cot_dates) > 0:
            cot_dt = (
                pd.to_datetime(cot_dates, utc=True)
                .drop_duplicates()
                .sort_values()
                .reset_index(drop=True)
            )
            cot_ref = pd.DataFrame({"cot_date": cot_dt})

            prices_sorted = prices_df.sort_values("date").reset_index(drop=True)

            merged = pd.merge_asof(
                cot_ref,
                prices_sorted,
                left_on="cot_date",
                right_on="date",
                direction="backward",
                tolerance=pd.Timedelta(days=4),
            )

            merged["date"] = merged["cot_date"]
            merged = merged.drop(columns=["cot_date"])

            value_cols = [c for c in merged.columns if c != "date"]
            merged = merged.dropna(subset=value_cols, how="all")

            print(
                f"[DatabentoContinuousService] Aligned {len(merged)} deferred price "
                f"points to CoT dates"
            )
            return merged.reset_index(drop=True)

        else:
            tuesday_mask = prices_df["date"].dt.dayofweek == 1
            result = prices_df[tuesday_mask].copy().reset_index(drop=True)
            print(
                f"[DatabentoContinuousService] Filtered to {len(result)} Tuesday "
                f"deferred price points (fallback)"
            )
            return result

    def load_aligned(self, cot_dates: pd.Series = None, start_date=None) -> pd.DataFrame:
        """Load deferred futures prices and align them to CoT dates."""
        df = self.load_dataframe(start_date=start_date)
        return self.align_to_cot_dates(df, cot_dates)
