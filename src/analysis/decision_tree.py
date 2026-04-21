"""
Decision-Tree-Prognose: Preisrichtung der nächsten Woche auf Basis von CoT-Daten.

Für jeden Rohstoff wird ein DecisionTreeClassifier (max_depth=3) auf den vollständigen
verfügbaren Datensatz trainiert. Als Zielvariable dient, ob der Futures-Preis in der
darauffolgenden Woche gestiegen oder gefallen ist.  Die aktuellste Beobachtung wird
dann zur Prognose herangezogen.

Zur Modell-Evaluation wird zusätzlich ein zeitbasierter 70/30-Split durchgeführt:
Die ersten 70 % der Daten dienen als Trainingsset, die letzten 30 % als Testset.
Konfusionsmatrix, ROC-Kurve und Precision-Recall-Kurve werden ausschliesslich auf
dem Out-of-Sample-Testset berechnet.

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
from sklearn.metrics import (
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)
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

_Z_WINDOW    = 13    # Rolling-Fenster für Z-Score (~1 Quartal)
_TRAIN_RATIO = 0.70  # Zeitbasierter Train/Test-Split


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

    Zusätzlich zum Prognose-Modell (trainiert auf 100 % der Daten) wird ein
    separates Evaluierungs-Modell mit zeitbasiertem 70/30-Split berechnet.
    Die Out-of-Sample-Metriken (Konfusionsmatrix, ROC, PR) werden ausschliesslich
    auf dem Testset (letzte 30 % chronologisch) ermittelt.

    Parameters
    ----------
    df_market  : gefilterte Markt-Daten für einen einzelnen Rohstoff aus df_pivoted
    df_prices  : DataFrame mit mindestens den Spalten 'Date' und *price_col*
    price_col  : Spaltenname des Futures-Schlusskurses in df_prices

    Returns
    -------
    dict mit den Schlüsseln:
        model          – Prognose-Modell (trainiert auf 100 % der Daten)
        feature_labels – lesbare Feature-Bezeichnungen (in FEATURE_COLS-Reihenfolge)
        prediction     – 1 (steigt) oder 0 (fällt) für die aktuellste Woche
        proba          – [P(fällt), P(steigt)] der Vorhersage
        n_samples      – Anzahl Beobachtungen (Vollmodell)
        last_date      – Datum der aktuellsten Beobachtung im Datensatz
        eval           – dict mit Out-of-Sample-Evaluationsdaten (siehe unten)

    eval-Dict:
        y_test        – tatsächliche Labels des Testsets
        y_pred        – vorhergesagte Labels des Testsets
        y_score       – P(steigt) für jede Testbeobachtung (für ROC/PR)
        n_train       – Anzahl Trainingsbeobachtungen
        n_test        – Anzahl Testbeobachtungen
        train_start   – erstes Datum im Trainingsset
        train_end     – letztes Datum im Trainingsset
        test_start    – erstes Datum im Testset
        test_end      – letztes Datum im Testset

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

    # ------------------------------------------------------------------
    # 1) Prognose-Modell: trainiert auf 100 % der Daten
    # ------------------------------------------------------------------
    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=3, random_state=42, ccp_alpha=0.0)
    clf.fit(X, y)

    last_x = df[FEATURE_COLS].iloc[-1].values.reshape(1, -1)
    pred   = int(clf.predict(last_x)[0])
    proba  = clf.predict_proba(last_x)[0]

    # ------------------------------------------------------------------
    # 2) Evaluierungs-Modell: zeitbasierter 70/30-Split (Out-of-Sample)
    # ------------------------------------------------------------------
    split_idx = int(len(df) * _TRAIN_RATIO)

    train_df = df.iloc[:split_idx]
    test_df  = df.iloc[split_idx:]

    x_train_e = train_df[FEATURE_COLS].values
    y_train_e = train_df["_y"].values
    x_test_e  = test_df[FEATURE_COLS].values
    y_test_e  = test_df["_y"].values

    clf_eval = DecisionTreeClassifier(max_depth=3, min_samples_leaf=3, random_state=42, ccp_alpha=0.0)
    clf_eval.fit(x_train_e, y_train_e)

    y_pred_e  = clf_eval.predict(x_test_e)
    proba_e   = clf_eval.predict_proba(x_test_e)
    pos_idx   = list(clf_eval.classes_).index(1) if 1 in clf_eval.classes_ else 0
    y_score_e = proba_e[:, pos_idx]

    eval_data = {
        "y_test":      y_test_e,
        "y_pred":      y_pred_e,
        "y_score":     y_score_e,
        "n_train":     len(train_df),
        "n_test":      len(test_df),
        "train_start": train_df["Date"].iloc[0],
        "train_end":   train_df["Date"].iloc[-1],
        "test_start":  test_df["Date"].iloc[0],
        "test_end":    test_df["Date"].iloc[-1],
    }

    return {
        "model":          clf,
        "feature_labels": [FEATURE_LABELS[f] for f in FEATURE_COLS],
        "prediction":     pred,
        "proba":          proba,
        "n_samples":      len(df),
        "last_date":      df["Date"].iloc[-1],
        "eval":           eval_data,
    }


# ---------------------------------------------------------------------------
# Visualisierungen – Prognose-Modell
# ---------------------------------------------------------------------------

def train_all_markets(
    df_pivoted: pd.DataFrame,
    df_futures_prices: pd.DataFrame,
    market_names_col: str = "Market Names",
) -> dict:
    """Trainiert Decision Trees für alle Märkte in df_pivoted.

    Wrapper um train_decision_tree() für die Batch-Vorberechnung aller
    Märkte beim App-Start.

    Parameters
    ----------
    df_pivoted        : Vollständiger CoT-Datensatz (alle Märkte).
    df_futures_prices : DataFrame mit Futures-Preisspalten.
    market_names_col  : Spaltenname für den Marktnamen in df_pivoted.

    Returns
    -------
    dict: market_name → Ergebnis-dict von train_decision_tree().
    """
    from src.analysis.market_config import get_price_col

    results: dict = {}
    for mkt in df_pivoted[market_names_col].unique():
        pcol = get_price_col(mkt)
        if pcol is None or df_futures_prices.empty or pcol not in df_futures_prices.columns:
            print(f"[DecisionTree] Keine Preisdaten für {mkt} – überspringe.")
            continue

        dff = df_pivoted[df_pivoted[market_names_col] == mkt].copy()
        result = train_decision_tree(dff, df_futures_prices, pcol)
        if result is not None:
            results[mkt] = result
            direction = "steigend" if result["prediction"] == 1 else "fallend"
            print(f"[DecisionTree] {mkt}: Prognose {direction} ({result['n_samples']} Beobachtungen)")
        else:
            print(f"[DecisionTree] {mkt}: zu wenige Daten – überspringe.")

    return results


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
        margin={"l": 10, "r": 20, "t": 45, "b": 40},
        showlegend=False,
        xaxis={"showgrid": True, "gridcolor": "LightGray"},
    )
    return fig


# ---------------------------------------------------------------------------
# Visualisierungen – Out-of-Sample-Evaluation (Testset)
# ---------------------------------------------------------------------------

def confusion_matrix_figure(result: dict, market_name: str) -> go.Figure:
    """Plotly-Heatmap der Konfusionsmatrix (Out-of-Sample-Testset)."""
    ev      = result["eval"]
    cm      = confusion_matrix(ev["y_test"], ev["y_pred"])

    # Zeilenbeschriftungen: tatsächlich | Spaltenbeschriftungen: vorhergesagt
    labels  = ["fällt", "steigt"]
    z       = cm.tolist()
    z_text  = [[str(v) for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f"Vorhergesagt:<br><b>{l}</b>" for l in labels],
        y=[f"Tatsächlich:<br><b>{l}</b>"  for l in labels],
        text=z_text,
        texttemplate="%{text}",
        textfont={"size": 18, "color": "white"},
        colorscale=[[0, "#bbdefb"], [1, "#1565c0"]],
        showscale=False,
        hovertemplate="Tatsächlich: %{y}<br>Vorhergesagt: %{x}<br>Anzahl: %{z}<extra></extra>",
    ))
    fig.update_layout(
        title={"text": f"Konfusionsmatrix – {market_name}<br>"
                       f"<sup>Testset: {ev['n_test']} Beobachtungen</sup>",
               "font": {"size": 14}},
        plot_bgcolor="white",
        height=360,
        margin={"l": 10, "r": 10, "t": 70, "b": 10},
        xaxis={"side": "bottom"},
        yaxis={"autorange": "reversed"},
    )
    return fig


def roc_curve_figure(result: dict, market_name: str) -> go.Figure:
    """Plotly-Liniendiagramm der ROC-Kurve (Out-of-Sample-Testset)."""
    ev              = result["eval"]
    fpr, tpr, _     = roc_curve(ev["y_test"], ev["y_score"])
    roc_auc         = auc(fpr, tpr)

    fig = go.Figure()

    # Diagonale (Zufallsklassifikator)
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line={"dash": "dash", "color": "#9e9e9e", "width": 1.5},
        name="Zufall (AUC = 0.50)",
        hoverinfo="skip",
    ))

    # ROC-Kurve
    fig.add_trace(go.Scatter(
        x=fpr, y=tpr,
        mode="lines",
        line={"color": "#1565c0", "width": 2.5},
        name=f"Modell (AUC = {roc_auc:.2f})",
        hovertemplate="FPR: %{x:.2f}<br>TPR: %{y:.2f}<extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(21,101,192,0.10)",
    ))

    fig.update_layout(
        title={"text": f"ROC-Kurve – {market_name}<br>"
                       f"<sup>Testset: {ev['n_test']} Beobachtungen | AUC = {roc_auc:.2f}</sup>",
               "font": {"size": 14}},
        xaxis={"title": "False Positive Rate", "showgrid": True, "gridcolor": "LightGray",
               "range": [0, 1]},
        yaxis={"title": "True Positive Rate", "showgrid": True, "gridcolor": "LightGray",
               "range": [0, 1]},
        plot_bgcolor="white",
        height=360,
        margin={"l": 10, "r": 10, "t": 70, "b": 40},
        legend={"x": 0.55, "y": 0.08, "bgcolor": "rgba(255,255,255,0.8)",
                "bordercolor": "#ccc", "borderwidth": 1},
    )
    return fig


def pr_curve_figure(result: dict, market_name: str) -> go.Figure:
    """Plotly-Liniendiagramm der Precision-Recall-Kurve (Out-of-Sample-Testset)."""
    ev                     = result["eval"]
    precision, recall, _   = precision_recall_curve(ev["y_test"], ev["y_score"])
    pr_auc                 = auc(recall, precision)

    # Baseline: Anteil der positiven Klasse im Testset
    baseline = ev["y_test"].mean()

    fig = go.Figure()

    # Baseline (No-Skill-Klassifikator)
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[baseline, baseline],
        mode="lines",
        line={"dash": "dash", "color": "#9e9e9e", "width": 1.5},
        name=f"Baseline (Anteil Klasse 1: {baseline:.2f})",
        hoverinfo="skip",
    ))

    # PR-Kurve
    fig.add_trace(go.Scatter(
        x=recall, y=precision,
        mode="lines",
        line={"color": "#c62828", "width": 2.5},
        name=f"Modell (AUC = {pr_auc:.2f})",
        hovertemplate="Recall: %{x:.2f}<br>Precision: %{y:.2f}<extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(198,40,40,0.08)",
    ))

    fig.update_layout(
        title={"text": f"Precision-Recall-Kurve – {market_name}<br>"
                       f"<sup>Testset: {ev['n_test']} Beobachtungen | AUC = {pr_auc:.2f}</sup>",
               "font": {"size": 14}},
        xaxis={"title": "Recall", "showgrid": True, "gridcolor": "LightGray", "range": [0, 1]},
        yaxis={"title": "Precision", "showgrid": True, "gridcolor": "LightGray", "range": [0, 1]},
        plot_bgcolor="white",
        height=360,
        margin={"l": 10, "r": 10, "t": 70, "b": 40},
        legend={"x": 0.02, "y": 0.08, "bgcolor": "rgba(255,255,255,0.8)",
                "bordercolor": "#ccc", "borderwidth": 1},
    )
    return fig
