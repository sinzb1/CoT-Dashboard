"""
Bubble-Sizing-Hilfsfunktionen für Scatter-Plots.

Alle Funktionen sind reine Berechnungen ohne UI- oder Plotly-Abhängigkeiten.
"""

import numpy as np
import pandas as pd


def scaled_diameters(
    vals,
    min_px: float = 6,
    max_px: float = 26,
    lo: float | None = None,
    hi: float | None = None,
    log_scale: bool = False,
) -> np.ndarray:
    """Mappe Werte auf Pixeldurchmesser [min_px, max_px].

    Parameters
    ----------
    vals      : Werte (Series, ndarray, list oder Scalar).
    min_px    : Kleinster Durchmesser in Pixel.
    max_px    : Größter Durchmesser in Pixel.
    lo, hi    : Explizite Referenz-Grenzen (None → aus vals berechnen).
                Für die Legende MÜSSEN dieselben lo/hi wie für den Scatter
                übergeben werden, damit Legende und Punkte konsistent sind.
    log_scale : True → log1p-Transformation vor der Interpolation
                (empfohlen für stark rechts-schiefe Daten wie Open Interest).

    Returns
    -------
    ndarray mit Pixelwerten, gleiche Länge wie vals.
    """
    v = np.asarray(vals, dtype=float)
    v = np.where(np.isfinite(v), v, 0.0)

    if v.size == 0:
        return np.array([], dtype=float)

    _lo = float(lo) if lo is not None else float(np.nanmin(v))
    _hi = float(hi) if hi is not None else float(np.nanmax(v))

    if not np.isfinite(_lo) or not np.isfinite(_hi) or _hi <= _lo:
        return np.full_like(v, (min_px + max_px) / 2.0, dtype=float)

    if log_scale:
        v_t  = np.log1p(np.maximum(v, 0.0))
        lo_t = np.log1p(max(_lo, 0.0))
        hi_t = np.log1p(_hi)
    else:
        v_t, lo_t, hi_t = v, _lo, _hi

    return np.interp(v_t, (lo_t, hi_t), (min_px, max_px))


def scaled_diameters_rank(
    vals,
    min_px: float = 6,
    max_px: float = 45,
    gamma: float = 0.8,
) -> np.ndarray:
    """Rang-basierte Skalierung auf Pixeldurchmesser [min_px, max_px].

    Verwendet den Rang-Perzentil (0..1) jedes Wertes und mappt ihn
    nichtlinear via Gamma-Exponent auf den Pixel-Bereich.

    Parameters
    ----------
    vals   : Werte (Series, ndarray, list).
    min_px : Kleinster Durchmesser in Pixel.
    max_px : Größter Durchmesser in Pixel.
    gamma  : Exponent für nichtlineare Skalierung (< 1 → mehr Punkte oben).

    Returns
    -------
    ndarray mit Pixelwerten.
    """
    s = pd.to_numeric(pd.Series(vals), errors="coerce").fillna(0).clip(lower=0)

    if s.nunique(dropna=False) <= 1:
        return np.full(len(s), (min_px + max_px) / 2.0, dtype=float)

    p = s.rank(pct=True, method="average").to_numpy(dtype=float)
    return (min_px + (p ** gamma) * (max_px - min_px)).astype(float)
