"""
Shapley-Owen Decomposition of R² for Net Positioning data.

For each predictor X_i (Net Position einer Händlergruppe) wird der Shapley-Wert φ_i
berechnet: der durchschnittliche marginale Beitrag von X_i zur Erklärungskraft (R²)
eines linearen Regressionsmodells  Y ~ X_1 + ... + X_N,  gemittelt über alle
möglichen Prädiktor-Reihenfolgen.

Die Summe aller Shapley-Werte ist gleich R² des Vollmodells:
    φ_1 + φ_2 + ... + φ_N  =  R²(Y ~ X_1, ..., X_N)

Referenz: Owen (1977), Lipovetsky & Conklin (2001).
"""

import math
from itertools import combinations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _r2_ols(y: np.ndarray, X_cols: np.ndarray) -> float:
    """OLS-R² von  y ~ X_cols  (Intercept wird intern ergänzt).

    Gibt 0.0 zurück, wenn X_cols leer ist oder die Regression fehlschlägt.
    Klippt das Ergebnis auf [0, 1] um numerische Artefakte zu vermeiden.
    """
    if X_cols.shape[1] == 0:
        return 0.0

    Xc = np.column_stack([np.ones(len(y)), X_cols])
    try:
        beta, _, _, _ = np.linalg.lstsq(Xc, y, rcond=None)
        y_hat = Xc @ beta
    except np.linalg.LinAlgError:
        return 0.0

    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))

    if ss_tot < 1e-12:
        return 0.0

    return float(np.clip(1.0 - ss_res / ss_tot, 0.0, 1.0))


def _compute_shapley_values(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    """Berechnet Shapley-Werte für alle N Prädiktoren mittels vollständiger
    Koalitionsaufzählung (exakt für kleine N, hier N = 4).

    Strategie: R² aller 2^N Teilmengen einmal vorberechnen, dann für jeden
    Prädiktor i die gewichteten marginalen Beiträge aufsummieren.

    Parameters
    ----------
    y : (n,) Zielvariable (Preisrenditen)
    X : (n, N) Prädiktoren (Netto-Positionierungen)

    Returns
    -------
    phi : (N,) Shapley-Werte; Summe ≈ R² des Vollmodells.
          NaN-Array wenn nicht genug Beobachtungen vorhanden.
    """
    n_obs, N = X.shape

    if n_obs < N + 2:          # zu wenig Freiheitsgrade
        return np.full(N, np.nan)

    # --- R² aller 2^N Teilmengen vorberechnen ---
    r2_cache: dict[frozenset, float] = {}
    for size in range(N + 1):
        for subset in combinations(range(N), size):
            key = frozenset(subset)
            if not subset:
                r2_cache[key] = 0.0
            else:
                r2_cache[key] = _r2_ols(y, X[:, list(subset)])

    # --- Shapley-Gewichte und Summation ---
    N_fact = math.factorial(N)
    phi = np.zeros(N)

    for i in range(N):
        others = [j for j in range(N) if j != i]
        for size in range(N):          # |S| = 0 .. N-1
            weight = (
                math.factorial(size) * math.factorial(N - size - 1) / N_fact
            )
            for subset in combinations(others, size):
                s_set = frozenset(subset)
                marginal = r2_cache[s_set | {i}] - r2_cache[s_set]
                phi[i] += weight * marginal

    return phi


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def compute_rolling_shapley(
    df: pd.DataFrame,
    x_cols: list,
    y_col: str,
    window: int = 52,
    min_periods: int = 26,
) -> pd.DataFrame:
    """Berechnet rollende Shapley-Owen-Zerlegung des R².

    Für jedes Datum t wird ein Fenster der letzten `window` Beobachtungen
    verwendet.  Erst ab `min_periods` gültigen Zeilen wird ein Wert
    ausgegeben (vorher NaN).

    Parameters
    ----------
    df         : DataFrame, sortiert nach Datum; enthält x_cols und y_col.
    x_cols     : Liste der Prädiktor-Spaltennamen (Netto-Positionierungen).
    y_col      : Spaltenname der Zielvariable (Preisrenditen).
    window     : Fenstergrösse in Zeilen (Standard: 52 Wochen).
    min_periods: Mindestanzahl gültiger Beobachtungen (Standard: 26).

    Returns
    -------
    DataFrame mit Spalten:
        'Date'        – Datum
        *x_cols*      – Shapley-Wert jedes Prädiktors
        'R2_full'     – R² des Vollmodells für dieses Fenster
        'R2_share_*'  – Anteil jedes Prädiktors in % (φ_i / R²_full × 100)
    """
    dates = df["Date"].values
    Y = df[y_col].values.astype(float)
    X = df[x_cols].values.astype(float)
    n = len(df)
    N = len(x_cols)

    records = []
    for t in range(n):
        start = max(0, t - window + 1)
        y_w = Y[start : t + 1]
        X_w = X[start : t + 1]

        # NaN-Zeilen entfernen
        mask = np.isfinite(y_w) & np.all(np.isfinite(X_w), axis=1)
        y_w = y_w[mask]
        X_w = X_w[mask]

        if len(y_w) < min_periods:
            row = [dates[t]] + [np.nan] * N + [np.nan] + [np.nan] * N
            records.append(row)
            continue

        phi = _compute_shapley_values(y_w, X_w)
        r2_full = _r2_ols(y_w, X_w)

        # Anteil in % (nur wenn R² > 0 und alle phi endlich)
        if r2_full > 1e-8 and np.all(np.isfinite(phi)):
            shares = (phi / r2_full * 100.0).tolist()
        else:
            shares = [np.nan] * N

        records.append([dates[t]] + phi.tolist() + [r2_full] + shares)

    share_cols = [f"R2_share_{c}" for c in x_cols]
    cols = ["Date"] + x_cols + ["R2_full"] + share_cols
    result = pd.DataFrame(records, columns=cols)
    result["Date"] = pd.to_datetime(result["Date"])
    return result


def prepare_market_for_shapley(
    df_market: pd.DataFrame,
    df_prices: pd.DataFrame,
    price_col: str,
    net_cols: dict | None = None,
) -> pd.DataFrame | None:
    """Bereitet Marktdaten für die Shapley-Owen-Zerlegung vor.

    Führt identisch zur Logik in `train_decision_tree` aus:
    - Merge mit Futures-Preisen (merge_asof, 7-Tage-Toleranz)
    - Absolute Preisänderung als Zielvariable (_price_change)
    - First Differences der Netto-Positionierungen als Prädiktoren (Δ …)

    Parameters
    ----------
    df_market : CoT-Daten für einen einzelnen Markt aus df_pivoted.
                Muss 'Date' sowie alle Spalten aus net_cols-Werten enthalten.
    df_prices : DataFrame mit mindestens den Spalten 'Date' und *price_col*.
    price_col : Spaltenname des Futures-Schlusskurses in df_prices.
    net_cols  : Mapping {Δ-Ausgabespalte: Quell-Netto-Spalte}, z. B.
                {'Δ MM Net': 'MM Net', ...}.
                Default: die vier Standard-CoT-Händlergruppen.

    Returns
    -------
    DataFrame mit '_price_change' und allen Δ-Spalten, bereit für
    compute_rolling_shapley – oder None wenn keine Preisdaten verfügbar.
    """
    if net_cols is None:
        net_cols = {
            "Δ PMPU Net": "PMPU Net",
            "Δ SD Net":   "SD Net",
            "Δ MM Net":   "MM Net",
            "Δ OR Net":   "OR Net",
        }

    dff = df_market.copy().sort_values("Date").reset_index(drop=True)

    prices_clean = (
        df_prices[["Date", price_col]]
        .dropna(subset=[price_col])
        .rename(columns={"Date": "_pdate", price_col: "_close"})
        .sort_values("_pdate")
    )

    dff = pd.merge_asof(
        dff,
        prices_clean,
        left_on="Date",
        right_on="_pdate",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )

    if "_close" not in dff.columns or dff["_close"].isna().all():
        return None

    dff["_price_change"] = dff["_close"].diff()

    for delta_col, src_col in net_cols.items():
        if src_col in dff.columns:
            dff[delta_col] = dff[src_col].diff()

    return dff
