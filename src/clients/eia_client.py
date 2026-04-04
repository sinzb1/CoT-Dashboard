import json
import requests
import pandas as pd
from datetime import date


class EIAClient:
    """Client for EIA API v2 – weekly crude oil petroleum stocks.

    Configuration is read from config/config.json under the "eia" key,
    consistent with how SocrataClient reads its credentials.

    The EIA API v2 returns paginated JSON with a "response.data" array.
    Facet values (product, measure, duoarea) are configurable so they can
    be adjusted without code changes if the API returns unexpected results.
    """

    def __init__(self, config_path: str = "config/config.json"):
        with open(config_path) as f:
            config = json.load(f)

        eia_cfg = config["eia"]
        self.api_key = eia_cfg["api_key"]
        self.base_url = eia_cfg.get("base_url", "https://api.eia.gov/v2").rstrip("/")
        self.route = eia_cfg.get("petroleum_stocks_route", "/petroleum/stocks/data/")
        self.product_facet = eia_cfg.get("product_facet", "EPC0")
        self.process_facet = eia_cfg.get("process_facet", "SAX")
        self.duoarea_facet = eia_cfg.get("duoarea_facet", "NUS")
        self.years_back = config.get("pipeline", {}).get("years_back", 4)
        self.page_size = 5000

    def _start_date(self) -> str:
        today = date.today()
        return date(today.year - self.years_back, today.month, today.day).isoformat()

    def fetch_crude_oil_stocks(self) -> pd.DataFrame:
        """Fetch weekly US crude oil inventory data from EIA API v2.

        Returns a DataFrame with columns:
            period  – datetime (UTC), week-ending date from EIA
            value   – float, crude oil stocks in thousands of barrels (kb)

        The DataFrame is sorted ascending by period and contains only rows
        with a valid numeric value.

        Notes on facet values:
            product   – EIA product code; default "CRUDE_OIL". If the API
                        returns no data, try "EPC0" (the EIA internal code for
                        crude oil total) by updating config/config.json.
            measure   – EIA measure/process code; default "STOCKS". Alternative
                        is "SAE" (Ending Stocks) depending on the endpoint version.
            duoarea   – Geographic area; default "NUS" (National US total).
                        Without this filter the endpoint returns one row per
                        PAD district which would cause duplicate period dates.
        """
        url = self.base_url + self.route
        offset = 0
        all_rows = []

        while True:
            params = {
                "api_key": self.api_key,
                "frequency": "weekly",
                "data[]": "value",
                "facets[product][]": self.product_facet,
                "facets[process][]": self.process_facet,
                "facets[duoarea][]": self.duoarea_facet,
                "start": self._start_date(),
                "sort[0][column]": "period",
                "sort[0][direction]": "asc",
                "length": self.page_size,
                "offset": offset,
            }

            print(f"[EIAClient] GET {url}  offset={offset}")
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[EIAClient] Request failed: {e}")
                break

            body = resp.json()
            response_section = body.get("response", {})
            rows = response_section.get("data", [])

            if not rows:
                if not all_rows:
                    # Log enough detail to diagnose wrong facet values
                    print(f"[EIAClient] No data returned. Top-level keys: {list(body.keys())}")
                    print(f"[EIAClient] response keys: {list(response_section.keys())}")
                    warnings = body.get("warnings", [])
                    if warnings:
                        print(f"[EIAClient] API warnings: {warnings}")
                    print(
                        f"[EIAClient] Hint: verify facet values in config/config.json "
                        f"(product_facet='{self.product_facet}', process_facet='{self.process_facet}', "
                        f"duoarea_facet='{self.duoarea_facet}'). "
                        f"Valid values: product='EPC0', process='SAX'/'SAE'/'SAXL', duoarea='NUS'."
                    )
                break

            all_rows.extend(rows)
            total = int(response_section.get("total", len(all_rows)))
            print(f"[EIAClient] Loaded {len(all_rows)} / {total} rows")

            if len(all_rows) >= total:
                break
            offset += self.page_size

        if not all_rows:
            return pd.DataFrame(columns=["period", "value"])

        df = pd.DataFrame(all_rows)

        # Validate expected columns are present
        missing = [c for c in ("period", "value") if c not in df.columns]
        if missing:
            print(f"[EIAClient] Missing columns {missing}. Available: {list(df.columns)}")
            print(f"[EIAClient] Sample row: {all_rows[0]}")
            return pd.DataFrame(columns=["period", "value"])

        df = df[["period", "value"]].copy()
        df["period"] = pd.to_datetime(df["period"], utc=True)
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).sort_values("period").reset_index(drop=True)

        print(
            f"[EIAClient] Retrieved {len(df)} weekly crude oil stock observations "
            f"({df['period'].min().date()} to {df['period'].max().date()})"
        )
        return df
