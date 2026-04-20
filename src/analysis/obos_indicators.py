"""
OBOS-Indikatorberechnungen: MM Long/Short Concentration Range und Curve Style.

Berechnet für jeden Markt:
- MML/MMS Concentration (% des Open Interest)
- Rollende 52-Wochen-Range beider Concentration-Werte (via clustering_0_100)
- Preis-Range des 2nd-Nearby-Kontrakts
- Kurvenstruktur (Contango / Backwardation) aus 2nd vs. 3rd Nearby

Alle Funktionen sind reine Datenberechnungen ohne UI- oder Plotly-Abhängigkeiten.
"""

import numpy as np
import pandas as pd

from src.analysis.cot_indicators import clustering_0_100
from src.analysis.market_config import get_2nd_nearby_price_col, get_3rd_nearby_price_col


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

_TICKERS: dict[str, str] = {
    "GOLD":      "GC",
    "SILVER":    "SI",
    "COPPER":    "HG",
    "PLATINUM":  "PL",
    "PALLADIUM": "PA",
    "CRUDE OIL": "CL",
    "WTI":       "CL",
}

COLOR_CONTANGO      = '#1f77b4'   # Blau
COLOR_BACKWARDATION = '#2ca02c'   # Grün
COLOR_NA            = '#aaaaaa'   # Grau – Kurvenstruktur nicht ermittelbar


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def get_ticker(market_name: str) -> str:
    """Gibt den Futures-Ticker-Kürzel für einen Marktnamen zurück."""
    mn = (market_name or "").upper()
    for key, ticker in _TICKERS.items():
        if key in mn:
            return ticker
    return mn[:3]


def curve_style(p2, p3) -> tuple[str, str]:
    """Gibt (color, curve_label) für ein 2nd/3rd-Nearby-Preispaar zurück.

    Parameters
    ----------
    p2 : Preis des 2nd-Nearby-Kontrakts (oder NaN).
    p3 : Preis des 3rd-Nearby-Kontrakts (oder NaN).

    Returns
    -------
    (hex_color, label) – Backwardation wenn 2nd > 3rd, sonst Contango.
    """
    if pd.notna(p2) and pd.notna(p3):
        if p2 - p3 > 0:
            return COLOR_BACKWARDATION, 'Backwardation'
        return COLOR_CONTANGO, 'Contango'
    return COLOR_NA, 'Kurvenstruktur n/a'


def merge_deferred_prices(
    dff: pd.DataFrame,
    market: str,
    df_deferred_prices: pd.DataFrame,
) -> pd.DataFrame:
    """Mergt 2nd- und 3rd-Nearby-Preise in dff via merge_asof.

    Parameters
    ----------
    dff                 : Markt-DataFrame mit 'Date'-Spalte.
    market              : Marktname (für Lookup in market_config).
    df_deferred_prices  : Databento deferred futures prices.

    Returns
    -------
    dff mit zusätzlichen Spalten '_price2' und ggf. '_price3'.
    Fehlende Preise werden als NaN eingetragen.
    """
    col_2nd = get_2nd_nearby_price_col(market)
    col_3rd = get_3rd_nearby_price_col(market)

    if not (col_2nd and not df_deferred_prices.empty and col_2nd in df_deferred_prices.columns):
        dff['_price2'] = np.nan
        dff['_price3'] = np.nan
        return dff

    cols_deferred = ['Date', col_2nd]
    if col_3rd and col_3rd in df_deferred_prices.columns:
        cols_deferred.append(col_3rd)

    prices = df_deferred_prices[cols_deferred].copy()
    prices['_pdate'] = pd.to_datetime(prices['Date']).dt.tz_localize(None).astype("datetime64[s]")
    prices = prices.sort_values('_pdate')

    rename_map = {col_2nd: '_price2'}
    if col_3rd and col_3rd in df_deferred_prices.columns:
        rename_map[col_3rd] = '_price3'

    prices_ren = prices.drop(columns=['Date']).rename(columns=rename_map)

    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None).astype("datetime64[s]")
    dff = dff.sort_values('_date')
    dff = pd.merge_asof(
        dff, prices_ren,
        left_on='_date', right_on='_pdate',
        direction='backward',
        tolerance=pd.Timedelta(days=7),
    )
    return dff


def build_market_row(
    market: str,
    report_start,
    report_end,
    df_pivoted: pd.DataFrame,
    df_deferred_prices: pd.DataFrame,
) -> dict | None:
    """Berechnet eine Zeile für den OBOS-Chart für einen Markt.

    Parameters
    ----------
    market              : Marktname.
    report_start        : Untere Datumsgrenze des gewählten Zeitraums.
    report_end          : Obere Datumsgrenze (letztes Reportdatum).
    df_pivoted          : Vollständiger CoT-Datensatz (alle Märkte).
    df_deferred_prices  : Databento deferred futures prices.

    Returns
    -------
    dict mit Feldern 'market', 'ticker', 'mml_range', 'mms_range',
    'price_range', 'color', 'curve_label', 'report_date' –
    oder None wenn weniger als 10 Datenpunkte vorhanden.
    """
    dff = df_pivoted[
        (df_pivoted['Market Names'] == market) &
        (df_pivoted['Date'] <= report_end)
    ].copy().sort_values('Date')

    if len(dff) < 10:
        return None

    total_oi = pd.to_numeric(dff['Open Interest'], errors='coerce').replace(0, np.nan)
    dff['_mml_conc'] = 100.0 * pd.to_numeric(dff['Managed Money Long'],  errors='coerce') / total_oi
    dff['_mms_conc'] = 100.0 * pd.to_numeric(dff['Managed Money Short'], errors='coerce') / total_oi
    dff['_mml_range'] = clustering_0_100(dff['_mml_conc'], window=52)
    dff['_mms_range'] = clustering_0_100(dff['_mms_conc'], window=52)

    dff = merge_deferred_prices(dff, market, df_deferred_prices)
    dff['_price2_range'] = clustering_0_100(
        pd.to_numeric(dff.get('_price2', np.nan), errors='coerce'), window=52
    )

    dff_window = dff[dff['Date'] >= report_start]
    if dff_window.empty:
        dff_window = dff  # Fallback: letzter insgesamt verfügbarer Punkt

    last = dff_window.iloc[-1]
    p2 = float(last.get('_price2', np.nan)) if '_price2' in last.index else np.nan
    p3 = float(last.get('_price3', np.nan)) if '_price3' in last.index else np.nan
    color, curve_label = curve_style(p2, p3)

    return {
        'market':      market,
        'ticker':      get_ticker(market),
        'mml_range':   float(last['_mml_range'])    if pd.notna(last['_mml_range'])    else np.nan,
        'mms_range':   float(last['_mms_range'])    if pd.notna(last['_mms_range'])    else np.nan,
        'price_range': float(last['_price2_range']) if pd.notna(last['_price2_range']) else np.nan,
        'color':       color,
        'curve_label': curve_label,
        'report_date': last['Date'],
    }
