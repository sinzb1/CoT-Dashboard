"""
CoT-Indikatorberechnungen: Clustering, Relative Concentration, marktübergreifende
Normierung.

Alle Funktionen sind reine Datenberechnungen ohne UI- oder Plotly-Abhängigkeiten.
"""

import numpy as np
import pandas as pd


def clustering_0_100(
    s: pd.Series,
    window: int = 52,
    min_periods: int = 10,
) -> pd.Series:
    """Rollende Min-Max-Normierung einer Serie auf [0, 100].

    Berechnet für jede Beobachtung, wo der aktuelle Wert innerhalb des
    gleitenden Fensters liegt – 0 = historisches Minimum, 100 = Maximum.

    Parameters
    ----------
    s           : Eingabe-Serie (z. B. Trader-Anteil einer Gruppe).
    window      : Fenstergrösse in Beobachtungen (Standard: 52 Wochen).
    min_periods : Mindestanzahl gültiger Werte im Fenster.

    Returns
    -------
    Serie mit Werten in [0, 100]; NaN wo zu wenige Beobachtungen vorhanden.
    """
    rmin = s.rolling(window, min_periods=min_periods).min()
    rmax = s.rolling(window, min_periods=min_periods).max()
    denom = (rmax - rmin).replace(0, np.nan)
    return (100.0 * (s - rmin) / denom).clip(0, 100)


def rel_concentration(
    oi_long: pd.Series,
    oi_short: pd.Series,
    total_oi: pd.Series,
) -> pd.Series:
    """Relative Concentration einer Händlergruppe in Prozentpunkten.

    Formel: 100 × (Long-OI / Gesamt-OI  −  Short-OI / Gesamt-OI)

    Positive Werte = Netto-Long-Übergewicht, negative = Netto-Short-Übergewicht.
    Division durch 0 wird durch Ersetzen mit NaN vermieden.

    Parameters
    ----------
    oi_long   : Long-Open-Interest der Gruppe.
    oi_short  : Short-Open-Interest der Gruppe.
    total_oi  : Gesamtes Open Interest des Marktes.

    Returns
    -------
    Serie mit Werten in Prozentpunkten.
    """
    L = pd.to_numeric(oi_long,  errors="coerce")
    S = pd.to_numeric(oi_short, errors="coerce")
    T = pd.to_numeric(total_oi, errors="coerce").replace(0, np.nan)
    return 100.0 * ((L / T) - (S / T))


def calculate_ranges(
    agg_df: pd.DataFrame,
    concentration_col: str,
    clustering_col: str,
) -> tuple[pd.Series, pd.Series]:
    """Marktübergreifende Min-Max-Normierung auf [0, 100].

    Skaliert Concentration- und Clustering-Werte über alle Märkte hinweg,
    sodass verschiedene Märkte direkt vergleichbar werden.

    Parameters
    ----------
    agg_df            : DataFrame mit einer Zeile pro Markt (bereits aggregiert).
    concentration_col : Spaltenname der rohen Concentration-Werte.
    clustering_col    : Spaltenname der rohen Clustering-Werte.

    Returns
    -------
    (concentration_range, clustering_range) – je eine Series skaliert auf [0, 100].
    """
    numeric_df = agg_df.select_dtypes(include="number")

    def _minmax(col: str) -> pd.Series:
        s = numeric_df[col]
        span = s.max() - s.min()
        if span == 0 or not np.isfinite(span):
            return pd.Series(0.0, index=s.index)
        return (s - s.min()) / span * 100.0

    return _minmax(concentration_col), _minmax(clustering_col)
