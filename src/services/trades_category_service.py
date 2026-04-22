import pandas as pd
import numpy as np

from src.clients.socrata_client import SocrataClient
from src.mappings.categories_of_traders_column_map import COLUMN_MAP


MARKET_NAMES_COL = "Market Names"


class TradesCategoryService:
    def __init__(self):
        self.client = SocrataClient()

    def load_dataframe(self, start_date=None):
        rows = self.client.get_traders_categories(start_date=start_date)
        df = pd.DataFrame.from_records(rows)
        return df

    def filter_and_rename(self, df):
        filtered_df = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)

        market_filter = {
            "GOLD - COMMODITY EXCHANGE INC.": "Gold",
            "SILVER - COMMODITY EXCHANGE INC.": "Silver",
            "PLATINUM - NEW YORK MERCANTILE EXCHANGE": "Platinum",
            "PALLADIUM - NEW YORK MERCANTILE EXCHANGE": "Palladium",
            # Current name (since February 2022)
            "COPPER- #1 - COMMODITY EXCHANGE INC.": "Copper",
            # Legacy name (before February 2022)
            "COPPER-GRADE #1 - COMMODITY EXCHANGE INC.": "Copper",
            # Current name (since February 2022)
            "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE": "Crude Oil (WTI)",
            # Legacy name (before February 2022)
            "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE": "Crude Oil (WTI)",
        }

        # Rename column
        filtered_df[MARKET_NAMES_COL] = filtered_df[MARKET_NAMES_COL].replace(market_filter)

        # convert to date_time
        filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], format="mixed", utc=True)

        # convert data field to numerics
        exclude = [MARKET_NAMES_COL, "Date"]
        num_cols = [c for c in filtered_df.columns if c not in exclude]
        filtered_df[num_cols] = (
            filtered_df[num_cols]
            .replace({"": np.nan, "NaN": np.nan, None: np.nan})
            .apply(pd.to_numeric, errors="coerce")
        )

        return filtered_df
