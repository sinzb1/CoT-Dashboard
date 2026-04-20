"""
Datenladen aus InfluxDB v3 und yfinance-Fallback für Macro-Daten.

Stellt load_all_data() bereit, das alle für das Dashboard benötigten
DataFrames lädt und zurückgibt.
"""

import os
from datetime import date as _date

import pandas as pd

from influxdb_client_3 import InfluxDBClient3


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

_LOOKBACK_INTERVAL = "10 years"

_MACRO_FALLBACK_TICKERS: dict[str, str] = {
    "vix":       "^VIX",
    "usd_index": "DX-Y.NYB",
    "usd_chf":   "CHF=X",
}


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _to_datetime_naive(df: pd.DataFrame, col: str = "Date") -> pd.DataFrame:
    s = pd.to_datetime(df[col])
    if s.dt.tz is not None:
        s = s.dt.tz_convert(None)
    df[col] = s.astype("datetime64[s]")
    return df.sort_values(col).reset_index(drop=True)


def _load_table(client: InfluxDBClient3, query: str, label: str) -> pd.DataFrame | None:
    """Führt eine SQL-Abfrage aus und gibt einen DataFrame zurück.

    Gibt None zurück wenn die Abfrage fehlschlägt.
    """
    try:
        table = client.query(query=query, language="sql")
        df = table.to_pandas()
        print(f"[{label}] {len(df)} Zeilen geladen.")
        return df
    except Exception as exc:
        print(f"[{label}] Fehler beim Laden: {exc}")
        return None


def _extract_close_series(raw: pd.DataFrame) -> pd.Series | None:
    if isinstance(raw.columns, pd.MultiIndex):
        close_col = next((c for c in raw.columns if c[0] == "Close"), None)
        return raw[close_col] if close_col else None
    return raw["Close"]


def _merge_ticker_into_macro(df_macro: pd.DataFrame, fb: pd.DataFrame, col: str) -> pd.DataFrame:
    if df_macro.empty or "Date" not in df_macro.columns:
        return fb
    if col not in df_macro.columns:
        return pd.merge(df_macro, fb, on="Date", how="outer", validate="1:1").sort_values("Date").reset_index(drop=True)
    tmp = pd.merge(
        fb,
        df_macro[["Date", col]].rename(columns={col: f"{col}_db"}),
        on="Date", how="outer", validate="1:1",
    )
    tmp[col] = tmp[f"{col}_db"].combine_first(tmp[col])
    tmp = tmp.drop(columns=[f"{col}_db"])
    return pd.merge(
        df_macro.drop(columns=[col]),
        tmp[["Date", col]],
        on="Date", how="outer", validate="1:1",
    ).sort_values("Date").reset_index(drop=True)


def _apply_yfinance_fallback(df_macro: pd.DataFrame, lookback_years: int = 10) -> pd.DataFrame:
    """Füllt Lücken in df_macro mit yfinance-Daten.

    InfluxDB-Werte haben Vorrang; yfinance dient als Basis-Fallback.
    """
    try:
        import yfinance as yf
        fb_start = _date.today().replace(year=_date.today().year - lookback_years)

        for col, ticker in _MACRO_FALLBACK_TICKERS.items():
            raw = yf.download(ticker, start=fb_start.isoformat(), progress=False, auto_adjust=True)
            if raw.empty:
                print(f"[Macro fallback] Keine Daten für {col} ({ticker})")
                continue

            series = _extract_close_series(raw)
            if series is None:
                continue

            fb = series.reset_index()
            fb.columns = ["Date", col]
            fb["Date"] = pd.to_datetime(fb["Date"]).dt.tz_localize(None).astype("datetime64[s]")

            df_macro = _merge_ticker_into_macro(df_macro, fb, col)
            print(f"[Macro fallback] {len(fb)} Zeilen für {col} aus yfinance geladen.")

    except Exception as exc:
        print(f"[Macro fallback] Fehler: {exc}")

    return df_macro


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def load_all_data(
    host: str | None = None,
    token: str | None = None,
    database: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Lädt alle für das Dashboard benötigten DataFrames aus InfluxDB v3.

    Liest Verbindungsparameter aus Umgebungsvariablen falls nicht übergeben:
        INFLUXDB_HOST, INFLUXDB_TOKEN, INFLUXDB_DATABASE

    Parameters
    ----------
    host     : InfluxDB-Host-URL (default: INFLUXDB_HOST env, Fallback localhost:8181).
    token    : Auth-Token (default: INFLUXDB_TOKEN env).
    database : Datenbankname (default: INFLUXDB_DATABASE env, Fallback 'CoT-Data').

    Returns
    -------
    dict mit den Schlüsseln:
        df_pivoted         – CoT-Rohdaten (Spalten 'time'/'market_names' bereits umbenannt)
        df_futures_prices  – Front-Month Futures-Preise (yfinance)
        df_macro           – Macro-Daten (VIX, DXY, USD/CHF) inkl. yfinance-Fallback
        df_eia             – EIA Rohöl-Lagerdaten
        df_deferred_prices – Databento 2nd/3rd-Nearby Deferred Futures-Preise
    """
    _host     = host     or os.environ.get("INFLUXDB_HOST", "http://localhost:8181")
    _token    = token    or os.environ["INFLUXDB_TOKEN"]
    _database = database or os.environ.get("INFLUXDB_DATABASE", "CoT-Data")

    print("Verbinde mit InfluxDB v3...")
    client = InfluxDBClient3(host=_host, token=_token, database=_database)

    # ------------------------------------------------------------------
    # CoT-Daten (Haupttabelle)
    # ------------------------------------------------------------------
    print("Lade CoT-Daten...")
    raw = _load_table(client, f"""
        SELECT *
        FROM cot_data
        WHERE time >= now() - INTERVAL '{_LOOKBACK_INTERVAL}'
    """, "CoT")
    if raw is None:
        raise RuntimeError("CoT-Daten konnten nicht geladen werden.")

    df_pivoted = raw.rename(columns={"time": "Date", "market_names": "Market Names"})
    df_pivoted = _to_datetime_naive(df_pivoted)
    print(f"[CoT] {len(df_pivoted)} Zeilen geladen.")

    # ------------------------------------------------------------------
    # Futures-Preise (yfinance Front-Month)
    # ------------------------------------------------------------------
    raw = _load_table(client, f"""
        SELECT *
        FROM futures_prices
        WHERE time >= now() - INTERVAL '{_LOOKBACK_INTERVAL}'
    """, "Futures")
    if raw is not None:
        df_futures_prices = _to_datetime_naive(raw.rename(columns={"time": "Date"}))
    else:
        df_futures_prices = pd.DataFrame(columns=["Date"])

    # ------------------------------------------------------------------
    # Macro-Daten (VIX, USD Index, USD/CHF)
    # ------------------------------------------------------------------
    raw = _load_table(client, f"""
        SELECT *
        FROM macro_by_date
        WHERE time >= now() - INTERVAL '{_LOOKBACK_INTERVAL}'
    """, "Macro")
    if raw is not None:
        df_macro = _to_datetime_naive(raw.rename(columns={"time": "Date"}))
    else:
        df_macro = pd.DataFrame(columns=["Date"])

    df_macro = _apply_yfinance_fallback(df_macro)

    # ------------------------------------------------------------------
    # EIA Rohöl-Lagerdaten
    # ------------------------------------------------------------------
    raw = _load_table(client, f"""
        SELECT time, crude_oil_stocks_kb
        FROM eia_petroleum_stocks
        WHERE time >= now() - INTERVAL '{_LOOKBACK_INTERVAL}'
        ORDER BY time ASC
    """, "EIA")
    if raw is not None:
        df_eia = _to_datetime_naive(raw.rename(columns={"time": "Date"}))
    else:
        df_eia = pd.DataFrame(columns=["Date"])

    # ------------------------------------------------------------------
    # Databento Deferred Futures-Preise (2nd/3rd Nearby)
    # ------------------------------------------------------------------
    raw = _load_table(client, f"""
        SELECT *
        FROM futures_deferred_prices
        WHERE time >= now() - INTERVAL '{_LOOKBACK_INTERVAL}'
    """, "Deferred")
    if raw is not None:
        df_deferred_prices = _to_datetime_naive(raw.rename(columns={"time": "Date"}))
    else:
        df_deferred_prices = pd.DataFrame(columns=["Date"])

    client.close()

    return {
        "df_pivoted":         df_pivoted,
        "df_futures_prices":  df_futures_prices,
        "df_macro":           df_macro,
        "df_eia":             df_eia,
        "df_deferred_prices": df_deferred_prices,
    }
