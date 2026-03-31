"""
Decision-Tree-Prognose: Preisrichtung der nächsten Woche auf Basis von CoT-Daten.

Für jeden Rohstoff wird ein DecisionTreeClassifier (max_depth=3) auf den vollständigen
verfügbaren Datensatz trainiert. Als Zielvariable dient, ob der Futures-Preis in der
darauffolgenden Woche gestiegen oder gefallen ist.  Die aktuellste Beobachtung wird
dann zur Prognose herangezogen.

Features (analog zum Referenz-Notebook):
  net_mm          – Netto-Position Managed Money (Long − Short)
  net_pmpu        – Netto-Position Producer/Merchant/Processor/User
  net_swap        – Netto-Position Swap Dealer
  pct_mm_long     – MM-Long-OI als % des Gesamt-Open-Interest
  pct_mm_short    – MM-Short-OI als % des Gesamt-Open-Interest
  chg_net_mm      – Wochenveränderung von net_mm
  chg_pct_mm_long – Wochenveränderung von pct_mm_long
  z_net_mm        – Rolling-Z-Score von net_mm (13-Wochen-Fenster)
"""

import base64
import io

import matplotlib
matplotlib.use("Agg")          # Non-interactive backend – muss vor pyplot-Import stehen
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from sklearn.tree import DecisionTreeClassifier, plot_tree


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "net_mm",
    "net_pmpu",
    "net_swap",
    "pct_mm_long",
    "pct_mm_short",
    "chg_net_mm",
    "chg_pct_mm_long",
    "z_net_mm",
]

FEATURE_LABELS = {
    "net_mm":          "Netto MM",
    "net_pmpu":        "Netto Prod/Merc",
    "net_swap":        "Netto Swap",
    "pct_mm_long":     "% MM Long (OI)",
    "pct_mm_short":    "% MM Short (OI)",
    "chg_net_mm":      "Δ Netto MM",
    "chg_pct_mm_long": "Δ % MM Long",
    "z_net_mm":        "Z-Score Netto MM",
}

_Z_WINDOW = 13   # Rolling-Fenster für Z-Score (~1 Quartal)


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet alle CoT-Features aus den rohen df_pivoted-Spalten.

    Erwartet Spalten (exakt wie in InfluxDB gespeichert):
        'Managed Money Long', 'Managed Money Short',
        'Producer/Merchant/Processor/User Long',
        'Producer/Merchant/Processor/User Short',
        'Swap Dealer Long', 'Swap Dealer Short',
        'Open Interest'
    """
    df = df.copy().sort_values("Date").reset_index(drop=True)

    def _num(col: str) -> pd.Series:
        return pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(np.nan, index=df.index)

    oi = _num("Open Interest").replace(0, np.nan)

    df["net_mm"]   = _num("Managed Money Long")   - _num("Managed Money Short")
    df["net_pmpu"] = _num("Producer/Merchant/Processor/User Long") - _num("Producer/Merchant/Processor/User Short")
    df["net_swap"] = _num("Swap Dealer Long")      - _num("Swap Dealer Short")

    df["pct_mm_long"]  = _num("Managed Money Long")  / oi * 100
    df["pct_mm_short"] = _num("Managed Money Short") / oi * 100

    df["chg_net_mm"]      = df["net_mm"].diff()
    df["chg_pct_mm_long"] = df["pct_mm_long"].diff()

    rm = df["net_mm"].rolling(_Z_WINDOW).mean()
    rs = df["net_mm"].rolling(_Z_WINDOW).std().replace(0, np.nan)
    df["z_net_mm"] = (df["net_mm"] - rm) / rs

    return df


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def train_decision_tree(
    df_market: pd.DataFrame,
    df_prices: pd.DataFrame,
    price_col: str,
) -> dict | None:
    """Trainiert einen Entscheidungsbaum zur Prognose der Preisrichtung.

    Parameters
    ----------
    df_market  : gefilterte Markt-Daten für einen einzelnen Rohstoff aus df_pivoted
    df_prices  : DataFrame mit mindestens den Spalten 'Date' und *price_col*
    price_col  : Spaltenname des Futures-Schlusskurses in df_prices

    Returns
    -------
    dict mit den Schlüsseln:
        model          – trainierter DecisionTreeClassifier
        feature_labels – lesbare Feature-Bezeichnungen (in FEATURE_COLS-Reihenfolge)
        prediction     – 1 (steigt) oder 0 (fällt) für die aktuellste Woche
        proba          – [P(fällt), P(steigt)] der Vorhersage
        n_samples      – Anzahl verwendeter Trainingsbeobachtungen
        last_date      – Datum der aktuellsten Beobachtung im Datensatz
    None wenn zu wenige Daten vorhanden (< 20 Beobachtungen nach Feature-Berechnung).
    """
    df = _prepare_features(df_market)

    # Futures-Preise einbinden (identisch zu Shapley-Owen-Logik in Dash_Lokal.py)
    prices_clean = (
        df_prices[["Date", price_col]]
        .dropna(subset=[price_col])
        .rename(columns={"Date": "_pdate", price_col: "_close"})
        .sort_values("_pdate")
    )
    df = pd.merge_asof(
        df,
        prices_clean,
        left_on="Date",
        right_on="_pdate",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )

    # Zielvariable: steigt der Preis in der nächsten Woche?
    df["_close_fwd"] = df["_close"].shift(-1)
    df["_y"] = (df["_close_fwd"] > df["_close"]).astype("Int64")

    df = df.dropna(subset=FEATURE_COLS + ["_y"]).copy()
    df["_y"] = df["_y"].astype(int)

    if len(df) < 20:
        return None

    X = df[FEATURE_COLS].values
    y = df["_y"].values

    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=3, random_state=42)
    clf.fit(X, y)

    last_X = df[FEATURE_COLS].iloc[-1].values.reshape(1, -1)
    pred   = int(clf.predict(last_X)[0])
    proba  = clf.predict_proba(last_X)[0]

    return {
        "model":          clf,
        "feature_labels": [FEATURE_LABELS[f] for f in FEATURE_COLS],
        "prediction":     pred,
        "proba":          proba,
        "n_samples":      len(df),
        "last_date":      df["Date"].iloc[-1],
    }


def render_tree_image(result: dict) -> str:
    """Rendert den Entscheidungsbaum als eingebettetes base64-PNG.

    Returns einen data-URI-String der direkt als `src` eines html.Img
    verwendet werden kann.
    """
    clf    = result["model"]
    labels = result["feature_labels"]

    fig, ax = plt.subplots(figsize=(20, 9), dpi=110)
    plot_tree(
        clf,
        feature_names=labels,
        class_names=["fällt", "steigt"],
        filled=True,
        rounded=True,
        fontsize=9,
        ax=ax,
        impurity=True,
        node_ids=False,
    )
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode()


def feature_importance_figure(result: dict, market_name: str) -> go.Figure:
    """Erstellt ein horizontales Plotly-Balkendiagramm der Feature Importance."""
    importances = result["model"].feature_importances_
    labels      = result["feature_labels"]

    idx            = np.argsort(importances)
    sorted_labels  = [labels[i]      for i in idx]
    sorted_imp     = [importances[i] for i in idx]

    fig = go.Figure(go.Bar(
        x=sorted_imp,
        y=sorted_labels,
        orientation="h",
        marker_color="#2196F3",
        hovertemplate="%{y}: %{x:.4f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Feature Importance – {market_name}",
        xaxis_title="Importance (Gini)",
        yaxis_title="",
        plot_bgcolor="white",
        height=340,
        margin=dict(l=10, r=20, t=45, b=40),
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="LightGray"),
    )
    return fig
