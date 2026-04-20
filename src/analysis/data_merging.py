"""
Zeitreihen-Merge-Hilfsfunktionen für Dash-Callbacks.

merge_series_asof() konsolidiert das wiederkehrende merge_asof-Boilerplate-
Muster in den Dash-Callbacks (Preise, Macro-Daten, EIA).
"""

import pandas as pd


def _norm_dt(s: pd.Series) -> pd.Series:
    s = pd.to_datetime(s)
    if s.dt.tz is not None:
        s = s.dt.tz_convert(None)
    return s.astype("datetime64[s]")


def merge_series_asof(
    dff: pd.DataFrame,
    series_df: pd.DataFrame,
    series_col: str,
    tolerance_days: int | None = 7,
    direction: str = "backward",
) -> pd.DataFrame:
    """Joined eine externe Zeitreihe via merge_asof in dff ein.

    Normalisiert das Datum in series_df auf tz-naive und verwendet '_date'
    in dff als linken Join-Key. Die '_date'-Spalte muss bereits vorhanden
    (tz-naive datetime) oder wird aus 'Date' erstellt.

    Parameters
    ----------
    dff            : Ziel-DataFrame.
    series_df      : Quell-DataFrame mit 'Date' und series_col.
    series_col     : Spaltenname der zu mergenden Zeitreihe.
    tolerance_days : Maximale Zeitdifferenz (None = unbegrenzt).
    direction      : 'backward' (default), 'forward' oder 'nearest'.

    Returns
    -------
    dff mit zusätzlicher series_col Spalte (NaN wenn kein Treffer).
    """
    if series_df.empty or series_col not in series_df.columns:
        dff = dff.copy()
        dff[series_col] = float("nan")
        return dff

    ref = (
        series_df[["Date", series_col]]
        .dropna(subset=[series_col])
        .copy()
    )
    ref["_ref_date"] = _norm_dt(ref["Date"])
    ref = ref.drop(columns=["Date"]).sort_values("_ref_date")

    if "_date" not in dff.columns:
        dff = dff.copy()
        dff["_date"] = _norm_dt(dff["Date"])

    dff = dff.sort_values("_date").reset_index(drop=True)

    kwargs: dict = {"left_on": "_date", "right_on": "_ref_date", "direction": direction}
    if tolerance_days is not None:
        kwargs["tolerance"] = pd.Timedelta(days=tolerance_days)

    return pd.merge_asof(dff, ref, **kwargs)
