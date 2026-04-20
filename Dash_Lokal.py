import dash
from dotenv import load_dotenv
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
from pages.grundlegende import layout as grundlegende_layout
from pages.dry_powder import layout as dry_powder_layout
from pages.positioning_price import layout as positioning_price_layout
from pages.obos import layout as obos_layout
from pages.shapley import layout as shapley_layout
from pages.decision_tree import layout as decision_tree_layout
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import webbrowser
from threading import Timer
from datetime import datetime as dt, timedelta
import dash_bootstrap_components as dbc
import numpy as np
from src.data_loading.influxdb_loader import load_all_data
from src.analysis.feature_engineering import enrich_cot_dataframe
from src.analysis.bubble_sizing import scaled_diameters, scaled_diameters_rank
from src.analysis.data_merging import merge_series_asof
from src.analysis.shapley_owen import compute_rolling_shapley, prepare_market_for_shapley, precompute_all_markets as _shapley_precompute_all
from src.analysis.decision_tree import (
    train_decision_tree,
    train_all_markets as _dt_train_all,
    render_tree_image,
    feature_importance_figure as dt_feature_importance_figure,
    confusion_matrix_figure as dt_confusion_matrix_figure,
    roc_curve_figure as dt_roc_curve_figure,
    pr_curve_figure as dt_pr_curve_figure,
)
from src.analysis.market_config import get_price_col, get_contract_size, get_2nd_nearby_price_col, get_3rd_nearby_price_col
from src.analysis.cot_indicators import rel_concentration, calculate_ranges
from src.analysis.obos_indicators import (
    build_market_row as _obos_build_market_row,
    COLOR_CONTANGO as _OBOS_COLOR_CONTANGO,
    COLOR_BACKWARDATION as _OBOS_COLOR_BACKWARDATION,
    COLOR_NA as _OBOS_COLOR_NA,
)

# Function to open the web browser
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8051/")

load_dotenv()

# DataFrame-Spalten
MARKET_NAMES_COL         = 'Market Names'
OPEN_INTEREST_LABEL      = 'Open Interest'
NUMBER_OF_TRADERS_LABEL  = 'Number of Traders'
TOTAL_TRADERS_LABEL      = 'Total Number of Traders'
MANAGED_MONEY_LONG_COL   = 'Managed Money Long'
MANAGED_MONEY_SHORT_COL  = 'Managed Money Short'
TRADERS_MM_LONG_COL      = 'Traders M Money Long'
TRADERS_MM_SHORT_COL     = 'Traders M Money Short'
PMPU_LONG_COL            = 'Producer/Merchant/Processor/User Long'
PMPU_SHORT_COL           = 'Producer/Merchant/Processor/User Short'
TRADERS_PROD_MERC_LONG   = 'Traders Prod/Merc Long'
TRADERS_PROD_MERC_SHORT  = 'Traders Prod/Merc Short'
TRADERS_SWAP_LONG_COL    = 'Traders Swap Long'
TRADERS_SWAP_SHORT_COL   = 'Traders Swap Short'
TRADERS_OTHER_REPT_LONG  = 'Traders Other Rept Long'
TRADERS_OTHER_REPT_SHORT = 'Traders Other Rept Short'
SWAP_DEALER_LONG_COL     = 'Swap Dealer Long'
SWAP_DEALER_SHORT_COL    = 'Swap Dealer Short'
SWAP_DEALER_SPREAD_COL   = 'Swap Dealer Spread'
OTHER_REPT_LONG_COL      = 'Other Reportables Long'
OTHER_REPT_SHORT_COL     = 'Other Reportables Short'
MML_LONG_OI_COL          = 'MML Long OI'
MML_SHORT_OI_COL         = 'MML Short OI'
MMS_SHORT_OI_COL         = 'MMS Short OI'
MML_TRADERS_COL          = 'MML Traders'
MMS_TRADERS_COL          = 'MMS Traders'
MML_POSITION_SIZE_COL    = 'MML Position Size'
MMS_POSITION_SIZE_COL    = 'MMS Position Size'
PMPUL_REL_CONC_COL       = 'PMPUL Relative Concentration'
MML_REL_CONC_COL         = 'MML Relative Concentration'
MM_NET_OI_COL            = 'MM Net OI'
MM_NET_TRADERS_COL       = 'MM Net Traders'
# Dash-Komponenten-IDs
DATE_PICKER_ID           = 'date-picker-range'
MARKET_DROPDOWN_ID       = 'market-dropdown'
# Plotly / UI-Labels
MOST_RECENT_WEEK         = 'Most Recent Week'
DEFAULT_COLORSCALE       = 'Viridis'
LIGHTGRAY                = 'LightGray'
HOVER_OPEN_INTEREST      = '<br>Open Interest: '
HOVER_POS_SIZE           = '<br>PosSize (avg): '
# ---------------------------------------------------------------------------

# weitere Spalten-Konstanten (zweite Runde)
LONG_CLUSTERING_COL        = 'Long Clustering'
SHORT_CLUSTERING_COL       = 'Short Clustering'
PMPUL_POSITION_SIZE_COL    = 'PMPUL Position Size'
PMPUS_POSITION_SIZE_COL    = 'PMPUS Position Size'
SDL_POSITION_SIZE_COL      = 'SDL Position Size'
SDS_POSITION_SIZE_COL      = 'SDS Position Size'
ORL_POSITION_SIZE_COL      = 'ORL Position Size'
ORS_POSITION_SIZE_COL      = 'ORS Position Size'
PMPUS_REL_CONC_COL         = 'PMPUS Relative Concentration'
SDL_REL_CONC_COL           = 'SDL Relative Concentration'
MMS_REL_CONC_COL           = 'MMS Relative Concentration'
ORL_REL_CONC_COL           = 'ORL Relative Concentration'
SDS_REL_CONC_COL           = 'SDS Relative Concentration'
ORS_REL_CONC_COL           = 'ORS Relative Concentration'
PMPUL_TRADERS_COL          = 'PMPUL Traders'
TRADER_GROUP_COL           = 'Trader Group'
MM_LONG_OI_CONTRACTS_COL   = 'MM Long OI (Contracts)'
MM_SHORT_OI_CONTRACTS_COL  = 'MM Short OI (Contracts)'
CRUDE_OIL_STOCKS_COL       = 'crude_oil_stocks_kb'
MM_NUM_LONG_TRADERS_COL    = 'MM Number of Long Traders'
MM_NUM_SHORT_TRADERS_COL   = 'MM Number of Short Traders'
LONG_POSITION_SIZE_COL     = 'Long Position Size'
SHORT_POSITION_SIZE_COL    = 'Short Position Size'
MANAGED_MONEY_SPREAD_COL   = 'Managed Money Spread'
OTHER_REPT_SPREAD_COL      = 'Other Reportables Spread'
FIRST_WEEK_LABEL           = 'First Week'
MARKERS_TEXT_MODE          = 'markers+text'
PRICE_2ND_NEARBY_LABEL     = 'Price (2nd Nearby) (Report Date)'
REPORT_DATE_LABEL          = 'Report Date'
SHAPLEY_COL_PMPU           = 'Δ PMPU Net'
SHAPLEY_COL_SD             = 'Δ SD Net'
SHAPLEY_COL_MM             = 'Δ MM Net'
SHAPLEY_COL_OR             = 'Δ OR Net'


# ---------------------------------------------------------------------------
# Datenladen: InfluxDB v3 + yfinance-Fallback
# Implementierung: siehe src/data_loading/influxdb_loader.py
# ---------------------------------------------------------------------------
_data = load_all_data()
df_pivoted         = _data["df_pivoted"]
df_futures_prices  = _data["df_futures_prices"]
df_macro           = _data["df_macro"]
df_eia             = _data["df_eia"]
df_deferred_prices = _data["df_deferred_prices"]
del _data

# ---------------------------------------------------------------------------
# DataFrame-Anreicherung: abgeleitete Spalten berechnen
# Implementierung: siehe src/analysis/feature_engineering.py
# ---------------------------------------------------------------------------
df_pivoted = enrich_cot_dataframe(df_pivoted)
print(df_pivoted.columns)
print(df_pivoted.head())

# Define the default end date (most recent date)
default_end_date = df_pivoted['Date'].max()

# Define the default start date (6 months prior to the end date)
default_start_date = default_end_date - timedelta(days=182)

# ---------------------------------------------------------------------------
# PPCI – Positioning Price Concentration Indicator
# Markt-Konfiguration und Lookup-Funktionen: siehe src/analysis/market_config.py
# Lokale Aliase für Rückwärtskompatibilität innerhalb dieser Datei.
# ---------------------------------------------------------------------------
_ppci_get_price_col          = get_price_col
_ppci_get_contract_size      = get_contract_size
_ppci_get_2nd_nearby_col     = get_2nd_nearby_price_col
_ppci_get_3rd_nearby_col     = get_3rd_nearby_price_col


def get_global_xaxis():
    return {
        "tickmode": 'array',
        "tickvals": df_pivoted['Date'].dt.year.unique(),
        "ticktext": [str(year) for year in df_pivoted['Date'].dt.year.unique()],
        "showgrid": True,
        "ticks": "outside",
        "tickangle": 45
    }

global_xaxis = {
    "tickmode": 'array',
    "tickvals": df_pivoted['Date'].dt.year.unique(),  # Unique years
    "ticktext": [str(year) for year in df_pivoted['Date'].dt.year.unique()],  # Format as strings
    "showgrid": True,
    "ticks": "outside",
    "tickangle": 45  # Rotate for better visibility
}

def add_last_point_highlight(fig, df, x_col, y_col, inner_size=10, outer_line_width=4, outer_color='red', inner_color='black'):
    if not df.empty:  # Sicherstellen, dass die Daten nicht leer sind
        last_point = df.iloc[-1]

        # Innerer Punkt mit rotem Rand
        fig.add_trace(go.Scatter(
            x=[last_point[x_col]],
            y=[last_point[y_col]],
            mode='markers',
            marker={
                "size": inner_size,  # Größe des inneren Punkts
                "color": inner_color,  # Farbe des inneren Punkts
                "opacity": 1.0,
                "line": {
                    "width": outer_line_width,  # Breite des äußeren Rands
                    "color": outer_color  # Farbe des äußeren Rands
                }
            },
            showlegend=False  # Spur nicht in der Legende anzeigen
        ))

def safe_sizes(series, exp=2.2, min_px=0):
    s = pd.to_numeric(series, errors='coerce').clip(lower=0)
    s = s.pow(1/exp).fillna(0)
    s = s * 0.7
    if min_px > 0:
        s = s + min_px
    return s

def dynamic_bubble_sizes(series, steps=5):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return [50, 100, 150]  # Fallback

    max_val = s.max()
    # Aufrunden auf "schöne" Zahl
    magnitude = 10 ** (len(str(int(max_val))) - 1)
    max_rounded = int(np.ceil(max_val / magnitude) * magnitude)

    # Gleichmäßig verteilte Werte
    return np.linspace(max_rounded / steps, max_rounded, steps, dtype=int).tolist()

def col(df, name):
    if name in df:
        return pd.to_numeric(df[name], errors='coerce')
    return pd.Series(np.nan, index=df.index, dtype='float64')

def safe_colors(series):
    return pd.to_numeric(series, errors='coerce').fillna(0)

# Function to calculate medians
def calculate_medians(df):
    median_oi = df[MM_NET_OI_COL].median()
    median_traders = df[MM_NET_TRADERS_COL].median()
    return median_oi, median_traders

# Function to calculate the scaling factors for long and short positions
def calculate_scaling_factors(df):
    max_long_position_size = df[LONG_POSITION_SIZE_COL].max()
    max_short_position_size = df[SHORT_POSITION_SIZE_COL].max()
    long_scaling_factor = max_long_position_size / 50  # Adjust divisor as needed
    short_scaling_factor = max_short_position_size / 50  # Adjust divisor as needed
    return long_scaling_factor, short_scaling_factor

def _indicator_cols(indicator: str) -> tuple[str, str]:
    """Gibt (concentration_col, clustering_col) für 'MML' oder 'MMS' zurück."""
    if indicator == 'MML':
        return MML_REL_CONC_COL, LONG_CLUSTERING_COL
    elif indicator == 'MMS':
        return MMS_REL_CONC_COL, SHORT_CLUSTERING_COL
    raise ValueError("Invalid indicator. Must be 'MML' or 'MMS'.")

def nz(series):
    return pd.to_numeric(series, errors='coerce')

# scaled_diameters / scaled_diameters_rank: siehe src/analysis/bubble_sizing.py

def _oi_dtick(market: str) -> int:
    """dtick-Wert für OI-Achse je nach Markt (S3358: kein verschachtelter Ternary)."""
    if 'WTI' in market.upper():
        return 500000
    if market in ['Gold', 'Silver', 'Copper']:
        return 20000
    return 5000

# Example calculation
median_oi, median_traders = calculate_medians(df_pivoted)

# ---------------------------------------------------------------------------
# Shapley-Owen: Rollende Zerlegung des R² für alle Märkte vorberechnen
# ---------------------------------------------------------------------------
_SHAPLEY_X_COLS      = [SHAPLEY_COL_PMPU, SHAPLEY_COL_SD, SHAPLEY_COL_MM, SHAPLEY_COL_OR]
_SHAPLEY_Y_COL       = '_price_change'
_SHAPLEY_WINDOW      = 52
_SHAPLEY_MIN_PERIODS = 26

_shapley_results: dict = _shapley_precompute_all(
    df_pivoted, df_futures_prices,
    x_cols=_SHAPLEY_X_COLS,
    y_col=_SHAPLEY_Y_COL,
    window=_SHAPLEY_WINDOW,
    min_periods=_SHAPLEY_MIN_PERIODS,
)

# ---------------------------------------------------------------------------
# Decision Tree: vorberechnen für alle Märkte mit Preisdaten
# ---------------------------------------------------------------------------
_dt_results: dict = _dt_train_all(df_pivoted, df_futures_prices)

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    external_scripts=["https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"]
)

# Layout of the app
app.layout = html.Div([
    dbc.Navbar(
        dbc.Container([
            html.Span(
                "COT-Data Overview/Analysis Dashboard",
                style={'fontSize': '1.6rem', 'fontWeight': '600', 'color': 'white'}
            ),
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-4"
    ),
    dbc.Container([
        # Globale Filter – immer sichtbar, auf allen Seiten gültig
        dbc.Row([
            dbc.Col([
                html.Label("Markt", className="fw-semibold mb-1"),
                dcc.Dropdown(
                    id=MARKET_DROPDOWN_ID,
                    options=[{'label': market, 'value': market} for market in df_pivoted[MARKET_NAMES_COL].unique()],
                    value='Palladium',
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], width=12, lg=4),
            dbc.Col([
                html.Label("Zeitraum", className="fw-semibold mb-1 d-block"),
                dcc.DatePickerRange(
                    id=DATE_PICKER_ID,
                    start_date=df_pivoted['Date'].min(),
                    end_date=df_pivoted['Date'].max(),
                    display_format='YYYY-MM-DD',
                ),
            ], width=12, lg=8),
        ], className="mb-3 mt-1"),

        html.Hr(className="mt-0 mb-3"),

        # Seitennavigation
        dbc.Tabs(
            [
                dbc.Tab(grundlegende_layout(),    label="Grundlegende Indikatoren",        tab_id="tab-grundlegende"),
                dbc.Tab(dry_powder_layout(),      label="Dry Powder Indikatoren",           tab_id="tab-dry-powder"),
                dbc.Tab(positioning_price_layout(), label="Positioning Price Indikatoren", tab_id="tab-pp"),
                dbc.Tab(obos_layout(),            label="Overbought / Oversold Analyse",   tab_id="tab-obos"),
                dbc.Tab(shapley_layout(),         label="Shapley-Owen Zerlegung",           tab_id="tab-shapley"),
                dbc.Tab(decision_tree_layout(),   label="Preisprognose (Entscheidungsbaum)", tab_id="tab-dt"),
            ],
            id="main-tabs",
            active_tab="tab-grundlegende",
            className="mb-4",
        ),

    ], fluid=True),
    html.Footer(
        '© 2026 Market Analysis Dashboard',
        style={
            'backgroundColor': '#0d6efd',
            'color': 'white',
            'textAlign': 'center',
            'padding': '14px',
            'marginTop': '32px',
            'fontWeight': '500',
        }
    ),
])

def positions_bar(long_val, short_val, spread_val=None, bar_width_px=220, height_px=14):
    lv = 0 if pd.isna(long_val) else float(long_val)
    sv = 0 if pd.isna(short_val) else float(short_val)
    sp = 0 if (spread_val is None or pd.isna(spread_val)) else float(spread_val)

    lv = max(lv, 0)
    sv = max(sv, 0)
    sp = max(sp, 0)

    total = lv + sv + sp
    if total <= 0:
        return f"<div style='width:{bar_width_px}px;height:{height_px}px;border:1px solid #ccc;border-radius:3px;'></div>"

    p_long  = 100 * lv / total
    p_short = 100 * sv / total
    p_spread = 100 * sp / total

    spread_div = f"<div title='Spread: {int(sp)}' style='width:{p_spread:.2f}%;background:#1f77b4;'></div>" if sp > 0 else ""
    spread_txt = f", <b>Spread:</b> {int(sp)}" if sp > 0 else ""

    return (
        f"<div style='width:{bar_width_px}px;display:flex;flex-direction:column;'>"
        f"  <div style='display:flex;width:100%;height:{height_px}px;border:1px solid #ccc;border-radius:3px;overflow:hidden;'>"
        f"    <div title='Long: {int(lv)}'  style='width:{p_long:.2f}%;background:#2ca02c;'></div>"
        f"    <div title='Short: {int(sv)}' style='width:{p_short:.2f}%;background:#d62728;'></div>"
        f"    {spread_div}"
        f"  </div>"
        f"  <div style='font-size:11px;margin-top:4px;font-family:\"Courier New\", Courier, monospace;'>"
        f"    <b>Long:</b> {int(lv)}, <b>Short:</b> {int(sv)}{spread_txt}"
        f"  </div>"
        f"</div>"
    )

def traders_bar(long_val, short_val, spread_val=None, bar_width_px=220, height_px=14):
    lv = 0 if pd.isna(long_val) else float(long_val)
    sv = 0 if pd.isna(short_val) else float(short_val)
    tv = 0 if (spread_val is None or pd.isna(spread_val)) else float(spread_val)
    total = lv + sv + tv

    if total <= 0:
        return f"<div style='width:{bar_width_px}px;height:{height_px}px;border:1px solid #ccc;border-radius:3px;'></div>"

    p_long  = 100 * lv / total
    p_short = 100 * sv / total
    p_spread = 100 * tv / total

    spread_div = f"<div title='Spread: {int(tv)}' style='width:{p_spread:.2f}%;background:#1f77b4;'></div>" if tv > 0 else ""
    spread_txt = f", <b>Spread:</b> {int(tv)}" if tv > 0 else ""

    return (
        f"<div style='width:{bar_width_px}px;display:flex;flex-direction:column;'>"
        f"  <div style='display:flex;width:100%;height:{height_px}px;border:1px solid #ccc;border-radius:3px;overflow:hidden;'>"
        f"    <div title='Long: {int(lv)}'  style='width:{p_long:.2f}%;background:#2ca02c;'></div>"
        f"    <div title='Short: {int(sv)}' style='width:{p_short:.2f}%;background:#d62728;'></div>"
        f"    {spread_div}"
        f"  </div>"
        f"  <div style='font-size:11px;margin-top:4px;font-family:\"Courier New\", Courier, monospace;'>"
        f"    <b>Long:</b> {int(lv)}, <b>Short:</b> {int(sv)}{spread_txt}"
        f"  </div>"
        f"</div>"
    )

# Callback to update the table
@app.callback(
    [
        Output('overview-table', 'data'),
        Output('overview-table', 'tooltip_data'),
    ],
    [
        Input(MARKET_DROPDOWN_ID, 'value'),
        Input(DATE_PICKER_ID, 'start_date'),
        Input(DATE_PICKER_ID, 'end_date')
    ]
)
def update_table(selected_market, start_date, end_date):
    filtered_df = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ]

    if filtered_df.empty:
        return [], []

    first_row = filtered_df.iloc[0]
    current_row = filtered_df.iloc[-1]

    def safe_pct_change(curr, first):
        # verhindert Division durch 0 / NaN
        if pd.isna(first) or float(first) == 0:
            return 0
        return round(((float(curr) - float(first)) / float(first)) * 100, 2)

    data = {
        TRADER_GROUP_COL: [
            'Producer/Merchant/Processor/User',
            'Swap Dealer',
            'Managed Money',
            'Other Reportables'
        ],
        'Positions': [
            positions_bar(
                first_row[PMPU_LONG_COL],
                first_row[PMPU_SHORT_COL],
                None
            ),
            positions_bar(
                first_row[SWAP_DEALER_LONG_COL],
                first_row[SWAP_DEALER_SHORT_COL],
                first_row[SWAP_DEALER_SPREAD_COL]
            ),
            positions_bar(
                first_row[MANAGED_MONEY_LONG_COL],
                first_row[MANAGED_MONEY_SHORT_COL],
                first_row[MANAGED_MONEY_SPREAD_COL]
            ),
            positions_bar(
                first_row[OTHER_REPT_LONG_COL],
                first_row[OTHER_REPT_SHORT_COL],
                first_row[OTHER_REPT_SPREAD_COL]
            ),
        ],

        'Difference (Long %)': [
            safe_pct_change(current_row[PMPU_LONG_COL], first_row[PMPU_LONG_COL]),
            safe_pct_change(current_row[SWAP_DEALER_LONG_COL], first_row[SWAP_DEALER_LONG_COL]),
            safe_pct_change(current_row[MANAGED_MONEY_LONG_COL], first_row[MANAGED_MONEY_LONG_COL]),
            safe_pct_change(current_row[OTHER_REPT_LONG_COL], first_row[OTHER_REPT_LONG_COL])
        ],
        'Difference (Short %)': [
            safe_pct_change(current_row[PMPU_SHORT_COL], first_row[PMPU_SHORT_COL]),
            safe_pct_change(current_row[SWAP_DEALER_SHORT_COL], first_row[SWAP_DEALER_SHORT_COL]),
            safe_pct_change(current_row[MANAGED_MONEY_SHORT_COL], first_row[MANAGED_MONEY_SHORT_COL]),
            safe_pct_change(current_row[OTHER_REPT_SHORT_COL], first_row[OTHER_REPT_SHORT_COL])
        ],
        'Difference (Spread %)': [
            'Keine Daten ℹ️',  # PMPU hat keinen Spread im CFTC Disaggregated COT-Report
            safe_pct_change(current_row[SWAP_DEALER_SPREAD_COL], first_row[SWAP_DEALER_SPREAD_COL]),
            safe_pct_change(current_row[MANAGED_MONEY_SPREAD_COL], first_row[MANAGED_MONEY_SPREAD_COL]),
            safe_pct_change(current_row[OTHER_REPT_SPREAD_COL], first_row[OTHER_REPT_SPREAD_COL])
        ],

        'Total Traders': [
            current_row[TRADERS_PROD_MERC_LONG] + current_row[TRADERS_PROD_MERC_SHORT],
            current_row[TRADERS_SWAP_LONG_COL] + current_row[TRADERS_SWAP_SHORT_COL] + current_row['Traders Swap Spread'],
            current_row[TRADERS_MM_LONG_COL] + current_row[TRADERS_MM_SHORT_COL] + current_row['Traders M Money Spread'],
            current_row[TRADERS_OTHER_REPT_LONG] + current_row[TRADERS_OTHER_REPT_SHORT] + current_row['Traders Other Rept Spread']
        ],
        '% of Traders': [
            f"Long: {round(current_row[TRADERS_PROD_MERC_LONG] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Short: {round(current_row[TRADERS_PROD_MERC_SHORT] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%",

            f"Long: {round(current_row[TRADERS_SWAP_LONG_COL] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Short: {round(current_row[TRADERS_SWAP_SHORT_COL] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Spread: {round(current_row['Traders Swap Spread'] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%",

            f"Long: {round(current_row[TRADERS_MM_LONG_COL] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Short: {round(current_row[TRADERS_MM_SHORT_COL] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Spread: {round(current_row['Traders M Money Spread'] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%",

            f"Long: {round(current_row[TRADERS_OTHER_REPT_LONG] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Short: {round(current_row[TRADERS_OTHER_REPT_SHORT] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%, "
            f"Spread: {round(current_row['Traders Other Rept Spread'] / current_row[TOTAL_TRADERS_LABEL] * 100, 2)}%"
        ],

        NUMBER_OF_TRADERS_LABEL: [
            traders_bar(current_row[TRADERS_PROD_MERC_LONG],  current_row[TRADERS_PROD_MERC_SHORT],  None),
            traders_bar(current_row[TRADERS_SWAP_LONG_COL],       current_row[TRADERS_SWAP_SHORT_COL],       current_row['Traders Swap Spread']),
            traders_bar(current_row[TRADERS_MM_LONG_COL],    current_row[TRADERS_MM_SHORT_COL],    current_row['Traders M Money Spread']),
            traders_bar(current_row[TRADERS_OTHER_REPT_LONG], current_row[TRADERS_OTHER_REPT_SHORT], current_row['Traders Other Rept Spread'])
        ],
    }

    _pmpu_spread_tooltip = (
        'Keine Daten verfügbar. Im CFTC Disaggregated CoT-Report werden für '
        'PMPU keine Spread-Positionen ausgewiesen. '
        'PMPU-Händler sind physische Martkeilnehmende (Produzenten, Händler, Verarbeiter, '
        'Endnutzer) und halten keine separaten Spread-Positionen gemäss CFTC-Definition.'
    )

    tooltip_data = [
        # Zeile 0: PMPU — Tooltip nur auf der Spread-Zelle
        {
            'Difference (Spread %)': {'value': _pmpu_spread_tooltip, 'type': 'text'},
        },
        # Zeilen 1–3: Swap Dealer, Managed Money, Other Reportables — kein Tooltip nötig
        {},
        {},
        {},
    ]

    return pd.DataFrame(data).to_dict('records'), tooltip_data

def _build_position_size_fig(df, traders_col, pos_size_col, direction, colorbar_title,
                              title, use_year_ticks=False, selected_market=None):
    """Build a position-size bubble chart. Shared by PMPU/SD/OR/MM long & short variants."""
    fig = go.Figure()

    tr = pd.to_numeric(df[traders_col], errors='coerce').fillna(0).clip(lower=0).astype(float)

    try:
        col = safe_colors(df[pos_size_col])
    except Exception:
        col = pd.to_numeric(df[pos_size_col], errors='coerce').fillna(0)

    _pos = tr[tr > 0]
    lo = float(_pos.min()) if _pos.size > 0 else 1.0
    hi = float(tr.max()) if tr.max() > 0 else 1.0
    sizes = scaled_diameters(tr, min_px=6, max_px=26, lo=lo, hi=hi)

    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df[OPEN_INTEREST_LABEL],
        mode='markers',
        marker={
            "size": sizes, "sizemode": 'diameter', "sizeref": 1,
            "color": col, "colorscale": DEFAULT_COLORSCALE, "showscale": True,
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75, "yanchor": 'middle', "y": 0.5}
        },
        text=[
            f"Date: {d:%Y-%m-%d}<br>Open Interest: {int(oi):,}<br>"
            f"Traders ({direction}): {int(t)}<br>PosSize (avg): {float(ps):,.0f}"
            for d, oi, t, ps in zip(
                df['Date'],
                pd.to_numeric(df[OPEN_INTEREST_LABEL], errors='coerce').fillna(0),
                tr,
                pd.to_numeric(df[pos_size_col], errors='coerce').fillna(0)
            )
        ],
        hoverinfo='text', showlegend=False
    ))

    base = tr[tr > 0]
    if base.size >= 3 and base.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])
    for v, s in zip(legend_vals, legend_sizes):
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker={"size": float(s), "sizemode": 'diameter', "sizeref": 1, "color": 'gray', "opacity": 0.6},
            showlegend=True, name=f"{int(v)} Traders", hoverinfo='skip'
        ))

    if use_year_ticks:
        xaxis_cfg = {
            "tickmode": 'array',
            "tickvals": df['Date'].dt.year.unique(),
            "ticktext": [str(y) for y in df['Date'].dt.year.unique()],
            "showgrid": True, "ticks": "outside", "tickangle": 45
        }
        yaxis_cfg = {"title": OPEN_INTEREST_LABEL, "showgrid": True, "tick0": 0,
                     "dtick": _oi_dtick(selected_market)}
        legend_x = 1.2
    else:
        xaxis_cfg = {"showgrid": True, "ticks": "outside", "tickangle": 45}
        yaxis_cfg = {"title": OPEN_INTEREST_LABEL, "showgrid": True}
        legend_x = 1.18

    fig.update_layout(
        title=title, xaxis_title='Date', yaxis_title=OPEN_INTEREST_LABEL,
        xaxis=xaxis_cfg, yaxis=yaxis_cfg,
        legend={"title": {"text": NUMBER_OF_TRADERS_LABEL}, "itemsizing": 'trace',
                "x": legend_x, "y": 0.5, "font": {"size": 12}},
        margin={"l": 60, "r": 160, "t": 60, "b": 60}
    )

    try:
        add_last_point_highlight(fig=fig, df=df, x_col='Date', y_col=OPEN_INTEREST_LABEL,
                                 inner_size=2, inner_color='black')
    except Exception:
        pass

    return fig


def _build_clustering_fig(df, clustering_col, colorbar_title, title, selected_market):
    """Build a clustering bubble chart. Shared by Long/Short Clustering variants."""
    fig = go.Figure()

    tr_total = pd.to_numeric(df[TOTAL_TRADERS_LABEL], errors='coerce').fillna(0).clip(lower=0).astype(float)

    _tr_pos = tr_total[tr_total > 0]
    tr_lo = float(_tr_pos.min()) if _tr_pos.size > 0 else 1.0
    tr_hi = float(tr_total.max()) if tr_total.max() > 0 else 1.0
    sizes_total = scaled_diameters(tr_total, min_px=8, max_px=30, lo=tr_lo, hi=tr_hi)

    fig.add_trace(go.Scatter(
        x=df['Date'],
        y=df[OPEN_INTEREST_LABEL],
        mode='markers',
        marker={
            "size": sizes_total, "sizemode": 'diameter', "sizeref": 1,
            "color": df[clustering_col], "colorscale": DEFAULT_COLORSCALE, "showscale": True,
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75, "yanchor": 'middle', "y": 0.5},
        },
        text=[
            f"Date: {d:%Y-%m-%d}<br>Traders: {int(t)}"
            for d, t in zip(df['Date'], tr_total)
        ],
        hoverinfo='text', showlegend=False
    ))

    base = tr_total[tr_total > 0]
    if base.size >= 3:
        legend_vals = np.unique(np.round(np.quantile(base, [0.10, 0.30, 0.50, 0.70, 0.90])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([50, 75, 100, 125, 150], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])
    for v, s in zip(legend_vals, legend_sizes):
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker={"size": float(s), "sizemode": 'diameter', "sizeref": 1, "color": 'gray', "opacity": 0.6},
            showlegend=True, name=f"{int(v)} Traders", hoverinfo='skip'
        ))

    fig.update_layout(
        title=title, xaxis_title='Date', yaxis_title=OPEN_INTEREST_LABEL,
        xaxis={
            "tickmode": 'array',
            "tickvals": df['Date'].dt.year.unique(),
            "ticktext": [str(year) for year in df['Date'].dt.year.unique()],
            "showgrid": True, "ticks": "outside", "tickangle": 45
        },
        yaxis={"title": OPEN_INTEREST_LABEL, "showgrid": True, "tick0": 0,
               "dtick": _oi_dtick(selected_market)},
        legend={"title": {"text": NUMBER_OF_TRADERS_LABEL}, "itemsizing": 'trace',
                "x": 1.2, "y": 0.5, "font": {"size": 12}},
        margin={"l": 60, "r": 160, "t": 60, "b": 60}
    )

    add_last_point_highlight(fig=fig, df=df, x_col='Date', y_col=OPEN_INTEREST_LABEL,
                             inner_size=2, inner_color='black')
    return fig


def _build_dp_rc_fig(filtered_df):
    """Baut den DP Relative Concentration Indicator (8 Gruppen, je historische + letzter Punkt)."""
    fig_rc = go.Figure()

    total_oi = pd.to_numeric(filtered_df.get(OPEN_INTEREST_LABEL), errors='coerce')

    def _rc(long_col, short_col):
        return rel_concentration(filtered_df.get(long_col), filtered_df.get(short_col), total_oi)

    groups = [
        {"name": 'MML',   "x": TRADERS_MM_LONG_COL,     "rc": _rc(MANAGED_MONEY_LONG_COL,  MANAGED_MONEY_SHORT_COL), "color": '#2c7fb8'},
        {"name": 'MMS',   "x": TRADERS_MM_SHORT_COL,    "rc": _rc(MANAGED_MONEY_SHORT_COL, MANAGED_MONEY_LONG_COL),  "color": '#7fcdbb'},
        {"name": 'ORL',   "x": TRADERS_OTHER_REPT_LONG,  "rc": _rc(OTHER_REPT_LONG_COL,     OTHER_REPT_SHORT_COL),    "color": '#f39c12'},
        {"name": 'ORS',   "x": TRADERS_OTHER_REPT_SHORT, "rc": _rc(OTHER_REPT_SHORT_COL,    OTHER_REPT_LONG_COL),     "color": '#f1c40f'},
        {"name": 'PMPUL', "x": TRADERS_PROD_MERC_LONG,   "rc": _rc(PMPU_LONG_COL,           PMPU_SHORT_COL),          "color": '#27ae60'},
        {"name": 'PMPUS', "x": TRADERS_PROD_MERC_SHORT,  "rc": _rc(PMPU_SHORT_COL,          PMPU_LONG_COL),           "color": '#2ecc71'},
        {"name": 'SDL',   "x": TRADERS_SWAP_LONG_COL,    "rc": _rc(SWAP_DEALER_LONG_COL,    SWAP_DEALER_SHORT_COL),   "color": '#e67e22'},
        {"name": 'SDS',   "x": TRADERS_SWAP_SHORT_COL,   "rc": _rc(SWAP_DEALER_SHORT_COL,   SWAP_DEALER_LONG_COL),    "color": '#e74c3c'},
    ]

    bubble_px = 14
    recent_px = bubble_px + 6

    # 1) Historische Punkte je Gruppe
    for g in groups:
        x = pd.to_numeric(filtered_df.get(g['x']), errors='coerce')
        y = g['rc']
        mask = x.notna() & y.notna()
        if mask.sum() == 0:
            continue
        fig_rc.add_trace(go.Scatter(
            x=x[mask], y=y[mask], mode='markers',
            marker={"size": bubble_px, "color": g['color'], "opacity": 0.8,
                    "line": {"width": 0.6, "color": 'black'}},
            name=g['name']
        ))

    # 2) Schwarzer Punkt für die letzte verfügbare Beobachtung je Gruppe
    first_legend_done = False
    for g in groups:
        x_series = pd.to_numeric(filtered_df.get(g['x']), errors='coerce')
        y_series = g['rc']
        mask = x_series.notna() & y_series.notna()
        if mask.sum() == 0:
            continue
        last_idx = y_series[mask].index[-1]
        x_last = x_series.loc[last_idx]
        y_last = y_series.loc[last_idx]
        if pd.notna(x_last) and pd.notna(y_last):
            fig_rc.add_trace(go.Scatter(
                x=[x_last], y=[y_last], mode='markers',
                marker={"size": recent_px, "color": 'black', "line": {"width": 2, "color": 'white'}},
                name=MOST_RECENT_WEEK, legendgroup='recent',
                showlegend=not first_legend_done
            ))
            first_legend_done = True

    fig_rc.update_layout(
        title="DP Relative Concentration Indicator",
        xaxis={"title": NUMBER_OF_TRADERS_LABEL, "showgrid": True, "gridcolor": LIGHTGRAY},
        yaxis={"title": 'Long and Short Concentration', "showgrid": True, "gridcolor": LIGHTGRAY},
        plot_bgcolor='white',
        legend_title=TRADER_GROUP_COL
    )
    return fig_rc


# Callback to update graphs based on selected market and date range
@app.callback(
    [
        Output('long-clustering-graph', 'figure'),
        Output('short-clustering-graph', 'figure'),
        Output('pmpu-long-position-size-graph', 'figure'),
        Output('pmpu-short-position-size-graph', 'figure'),
        Output('sd-long-position-size-graph', 'figure'),
        Output('sd-short-position-size-graph', 'figure'),
        Output('long-position-size-graph', 'figure'),
        Output('short-position-size-graph', 'figure'),
        Output('or-long-position-size-graph', 'figure'),
        Output('or-short-position-size-graph', 'figure'),
        Output('dry-powder-indicator-graph', 'figure'),
        Output('dp-relative-concentration-graph', 'figure'),
        Output('dp-seasonal-indicator-graph', 'figure'),
        Output('dp-net-indicators-graph', 'figure'),
        Output('dp-position-size-indicator', 'figure'),
        Output('hedging-indicator-graph', 'figure')
    ],
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('mm-radio', 'value'),
     Input('trader-group-radio', 'value')]
)

def update_graphs(selected_market, start_date, end_date, mm_type, trader_group):
    filtered_df = df_pivoted[(df_pivoted[MARKET_NAMES_COL] == selected_market) &
                             (df_pivoted['Date'] >= start_date) &
                             (df_pivoted['Date'] <= end_date)]

    pmpu_long_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_PROD_MERC_LONG, PMPUL_POSITION_SIZE_COL,
        'Long', 'PMPU Long Position Size', 'Long Position Size Indicator (PMPU)'
    )
    pmpu_short_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_PROD_MERC_SHORT, PMPUS_POSITION_SIZE_COL,
        'Short', 'PMPU Short Position Size', 'Short Position Size Indicator (PMPU)'
    )
    sd_long_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_SWAP_LONG_COL, SDL_POSITION_SIZE_COL,
        'Long', 'SD Long Position Size', 'Long Position Size Indicator (Swap Dealers)'
    )
    sd_short_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_SWAP_SHORT_COL, SDS_POSITION_SIZE_COL,
        'Short', 'SD Short Position Size', 'Short Position Size Indicator (Swap Dealers)'
    )
    or_long_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_OTHER_REPT_LONG, ORL_POSITION_SIZE_COL,
        'Long', 'OR Long Position Size', 'Long Position Size Indicator (Other Reportables)'
    )
    or_short_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_OTHER_REPT_SHORT, ORS_POSITION_SIZE_COL,
        'Short', 'OR Short Position Size', 'Short Position Size Indicator (Other Reportables)'
    )
    long_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_MM_LONG_COL, MML_POSITION_SIZE_COL,
        'Long', 'MM Long Position Size', 'Long Position Size Indicator (Money Managers)',
        use_year_ticks=True, selected_market=selected_market
    )
    short_position_size_fig = _build_position_size_fig(
        filtered_df, TRADERS_MM_SHORT_COL, MMS_POSITION_SIZE_COL,
        'Short', 'MM Short Position Size', 'Short Position Size Indicator (Money Managers)',
        use_year_ticks=True, selected_market=selected_market
    )

    _, _ = calculate_scaling_factors(filtered_df)

    long_clustering_fig = _build_clustering_fig(
        filtered_df, LONG_CLUSTERING_COL,
        'Long Clustering (%)', 'Long Positions Clustering Indicator', selected_market
    )
    short_clustering_fig = _build_clustering_fig(
        filtered_df, SHORT_CLUSTERING_COL,
        'Short Clustering (%)', 'Short Positions Clustering Indicator', selected_market
    )

    # --- Dry Powder Indicator---
    dry_powder_fig = go.Figure()

    BUBBLE_PX = 14
    desired_max_px = 28

    COL_LONG = "#2c7fb8"  # MML
    COL_SHORT = "#7fcdbb"  # MMS

    # MML Wolke
    dry_powder_fig.add_trace(go.Scatter(
        x=filtered_df[MML_TRADERS_COL],
        y=filtered_df[MML_LONG_OI_COL],
        mode='markers',
        marker={
            "size": BUBBLE_PX,
            "color": COL_LONG, "opacity": 0.75, "line": {"width": 0.6, "color": 'black'}
        },
        name='MML'
    ))

    # MMS Wolke
    dry_powder_fig.add_trace(go.Scatter(
        x=filtered_df[MMS_TRADERS_COL],
        y=filtered_df[MML_SHORT_OI_COL],
        mode='markers',
        marker={
            "size": BUBBLE_PX,
            "color": COL_SHORT, "opacity": 0.75, "line": {"width": 0.6, "color": 'black'}
        },
        name='MMS'
    ))

    # x-Range über beide Gruppen
    x_min = float(min(filtered_df[MML_TRADERS_COL].min(), filtered_df[MMS_TRADERS_COL].min()))
    x_max = float(max(filtered_df[MML_TRADERS_COL].max(), filtered_df[MMS_TRADERS_COL].max()))
    xs = np.array([x_min, x_max])

    def add_trend(x_series, y_series, color, name):
        # NaNs entfernen
        mask = x_series.notna() & y_series.notna()
        x = x_series[mask].astype(float).values
        y = y_series[mask].astype(float).values
        if len(x) < 2:
            return
        m, b = np.polyfit(x, y, 1)
        ys = m * xs + b

        # Unterzug (weiß, breit) für bessere Sichtbarkeit
        dry_powder_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": 'white', "width": 7},
            name=name, showlegend=False, hoverinfo='skip'
        ))
        # Farblinie oben drauf
        dry_powder_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": color, "width": 3},
            name=name, showlegend=True
        ))

    # Trendlinien hinzufügen (durch den ganzen Graph)
    add_trend(filtered_df[MML_TRADERS_COL], filtered_df[MML_LONG_OI_COL], COL_LONG, "MML Trend")
    add_trend(filtered_df[MMS_TRADERS_COL], filtered_df[MML_SHORT_OI_COL], COL_SHORT, "MMS Trend")

    # Most Recent Week
    dry_powder_fig.add_trace(go.Scatter(
        x=[filtered_df[MML_TRADERS_COL].iloc[-1]],
        y=[filtered_df[MML_LONG_OI_COL].iloc[-1]],
        mode='markers',
        marker={"size": desired_max_px + 4, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK, legendgroup='recent', showlegend=True
    ))
    dry_powder_fig.add_trace(go.Scatter(
        x=[filtered_df[MMS_TRADERS_COL].iloc[-1]],
        y=[filtered_df[MML_SHORT_OI_COL].iloc[-1]],
        mode='markers',
        marker={"size": desired_max_px + 4, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK, legendgroup='recent', showlegend=False  # keine doppelte Legende
    ))

    dry_powder_fig.update_layout(
        title="DP Indicator",
        xaxis={"title": NUMBER_OF_TRADERS_LABEL, "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False},
        yaxis={"title": 'Long and Short OI', "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False},
        plot_bgcolor='white',
        legend_title=TRADER_GROUP_COL
    )

    # --- DP Relative Concentration Indicator ---
    fig_rc = _build_dp_rc_fig(filtered_df)

    # DP Seasonal Indicator
    dp_seasonal_indicator_fig = go.Figure()

    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    colors = ['#1f77b4', '#17becf', '#ff7f0e', '#d62728']

    for quarter, color in zip(quarters, colors):
        quarter_data = filtered_df[filtered_df['Quarter'] == quarter]
        if quarter_data.empty:
            continue

        dp_seasonal_indicator_fig.add_trace(go.Scatter(
            x=quarter_data[PMPUL_TRADERS_COL],
            y=quarter_data[PMPUL_REL_CONC_COL],
            mode='markers',
            marker={
                "size": 10,  # 🔹 Fixe, einheitliche Bubblegröße
                "color": color,
                "opacity": 0.7,
                "line": {"width": 0.6, "color": 'black'}
            },
            name=quarter
        ))

    # Schwarzer Punkt für Most Recent Week
    most_recent_date = filtered_df['Date'].max()
    recent_data = filtered_df[filtered_df['Date'] == most_recent_date]
    if not recent_data.empty:
        dp_seasonal_indicator_fig.add_trace(go.Scatter(
            x=recent_data[PMPUL_TRADERS_COL],
            y=recent_data[PMPUL_REL_CONC_COL],
            mode='markers',
            marker={
                "size": 12,  # etwas grösser zur Hervorhebung
                "color": 'black',
                "symbol": 'circle',
                "line": {"width": 1.5, "color": 'white'}
            },
            name=MOST_RECENT_WEEK
        ))

    dp_seasonal_indicator_fig.update_layout(
        title=f"DP Seasonal Indicator – {most_recent_date.strftime('%d/%m/%Y')}",
        xaxis_title=NUMBER_OF_TRADERS_LABEL,
        yaxis_title="Long and Short Concentration",
        plot_bgcolor='white',
        legend_title="Quarter",
        xaxis={"showgrid": True, "gridcolor": LIGHTGRAY},
        yaxis={"showgrid": True, "gridcolor": LIGHTGRAY}
    )

    # DP Net Indicators with Medians
    most_recent_date = filtered_df['Date'].max()
    first_date = filtered_df['Date'].min()
    median_oi, median_traders = calculate_medians(filtered_df)
    
    dp_net_indicators_fig = go.Figure()

    # Color coding by Year
    for year in filtered_df['Year'].unique():
        year_data = filtered_df[filtered_df['Year'] == year]

        dp_net_indicators_fig.add_trace(go.Scatter(
            x=year_data[MM_NET_TRADERS_COL],
            y=year_data[MM_NET_OI_COL],
            mode='markers',
            marker={"size": 10, "opacity": 0.6},
            name=str(year)
        ))

    # Adding markers for the most recent and first weeks
    recent_data = filtered_df[filtered_df['Date'] == most_recent_date]
    first_data = filtered_df[filtered_df['Date'] == first_date]
    
    dp_net_indicators_fig.add_trace(go.Scatter(
        x=recent_data[MM_NET_TRADERS_COL],
        y=recent_data[MM_NET_OI_COL],
        mode='markers',
        marker={"size": 12, "color": 'black', "symbol": 'circle'},
        name=MOST_RECENT_WEEK
    ))

    dp_net_indicators_fig.add_trace(go.Scatter(
        x=first_data[MM_NET_TRADERS_COL],
        y=first_data[MM_NET_OI_COL],
        mode='markers',
        marker={"size": 12, "color": 'red', "symbol": 'circle'},
        name=FIRST_WEEK_LABEL
    ))

    # Adding medians
    dp_net_indicators_fig.add_trace(go.Scatter(
        x=[median_traders, median_traders],
        y=[filtered_df[MM_NET_OI_COL].min(), filtered_df[MM_NET_OI_COL].max()],
        mode='lines',
        line={"color": 'gray', "dash": 'dash'},
        name='Median Net Traders'
    ))

    dp_net_indicators_fig.add_trace(go.Scatter(
        x=[filtered_df[MM_NET_TRADERS_COL].min(), filtered_df[MM_NET_TRADERS_COL].max()],
        y=[median_oi, median_oi],
        mode='lines',
        line={"color": 'gray', "dash": 'dash'},
        name='Median Net OI'
    ))

    dp_net_indicators_fig.update_layout(
        title='DP Net Indicators with Medians',
        xaxis_title='MM Net Number of Traders',
        yaxis_title=MM_NET_OI_COL,
        legend_title='Year'
    )

    # Dry Powder Position Size Indicator (MML & MMS)
    dff = filtered_df
    if mm_type == 'MML':
        x = dff[TRADERS_MM_LONG_COL]
        y = dff[MML_POSITION_SIZE_COL]
        color = dff[OPEN_INTEREST_LABEL]
        recent_week = dff[MML_POSITION_SIZE_COL].iloc[-1]
        recent_x = dff[TRADERS_MM_LONG_COL].iloc[-1]
        first_week = dff[MML_POSITION_SIZE_COL].iloc[0]
        first_x = dff[TRADERS_MM_LONG_COL].iloc[0]
    else:
        x = dff[TRADERS_MM_SHORT_COL]
        y = dff[MMS_POSITION_SIZE_COL]
        color = dff[OPEN_INTEREST_LABEL]
        recent_week = dff[MMS_POSITION_SIZE_COL].iloc[-1]
        recent_x = dff[TRADERS_MM_SHORT_COL].iloc[-1]
        first_week = dff[MMS_POSITION_SIZE_COL].iloc[0]
        first_x = dff[TRADERS_MM_SHORT_COL].iloc[0]

    median_x = x.median()
    median_y = y.median()

    dp_position_size_fig = go.Figure()

    dp_position_size_fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='markers',
        marker={
            "size": 10,
            "color": color,
            "colorscale": DEFAULT_COLORSCALE,
            "showscale": True,
            "colorbar": {
                "title": OPEN_INTEREST_LABEL,
                "thickness": 15,
                "len": 0.75,
                "yanchor": 'middle'
            }
        },
        text=dff['Date'],
        hoverinfo='text',
        showlegend=False
    ))

    dp_position_size_fig.add_trace(go.Scatter(
        x=[recent_x],
        y=[recent_week],
        mode='markers',
        marker={
            "size": 12,
            "color": 'black'
        },
        name=MOST_RECENT_WEEK
    ))

    dp_position_size_fig.add_trace(go.Scatter(
        x=[first_x],
        y=[first_week],
        mode='markers',
        marker={
            "size": 12,
            "color": 'red'
        },
        name=FIRST_WEEK_LABEL
    ))

    dp_position_size_fig.add_shape(type="line",
                  x0=median_x, y0=0, x1=median_x, y1=max(y),
                  line={"color": "Gray", "width": 1, "dash": "dash"})

    dp_position_size_fig.add_shape(type="line",
                  x0=0, y0=median_y, x1=max(x), y1=median_y,
                  line={"color": "Gray", "width": 1, "dash": "dash"})

    dp_position_size_fig.update_layout(
        title='DP Position Size Indicator ({})'.format(mm_type),
        xaxis_title='Number of {} Traders'.format(mm_type),
        yaxis_title='{} Position Size'.format(mm_type),
        showlegend=True,
    )

    # Dry Powder Hedging Indicator (MML vs PMPUL / MMS vs PMPUS)
    hedging_fig = create_hedging_indicator(filtered_df, trader_group, start_date, end_date)

    return (
        long_clustering_fig,
        short_clustering_fig,
        pmpu_long_position_size_fig,
        pmpu_short_position_size_fig,
        sd_long_position_size_fig,
        sd_short_position_size_fig,
        long_position_size_fig,
        short_position_size_fig,
        or_long_position_size_fig,
        or_short_position_size_fig,
        dry_powder_fig,
        fig_rc,
        dp_seasonal_indicator_fig,
        dp_net_indicators_fig,
        dp_position_size_fig,
        hedging_fig
    )


# Function to create the hedging indicator
def create_hedging_indicator(data, trader_group, start_date, end_date):
    import numpy as np
    # Filter data by date range
    mask = (data['Date'] >= start_date) & (data['Date'] <= end_date)
    data = data.loc[mask]

    if trader_group == "MML":
        x = TRADERS_MM_LONG_COL
        y = MML_LONG_OI_COL
        color = PMPUL_REL_CONC_COL
        title = 'DP Hedging Indicator (MML vs PMPUL)'
        colorbar_title = 'PMPUL OI Range'
        x_title = MM_NUM_LONG_TRADERS_COL
        y_title = 'MM Long OI'
    else:
        x = TRADERS_MM_SHORT_COL
        y = MMS_SHORT_OI_COL
        color = PMPUS_REL_CONC_COL
        title = 'DP Hedging Indicator (MMS vs PMPUS)'
        colorbar_title = 'PMPUS OI Range'
        x_title = MM_NUM_SHORT_TRADERS_COL
        y_title = 'MM Short OI'

    # Vorab die gewünschten Achsenranges bestimmen (benötigen wir auch für die Trendlinie)
    x_min = float(np.nanmin(data[x])) - 10
    x_max = float(np.nanmax(data[x])) + 10
    y_min = float(np.nanmin(data[y])) - 50000
    y_max = float(np.nanmax(data[y])) + 50000

    # Haupt-Scatter
    # --- Bubble sizing---
    oi = pd.to_numeric(data[OPEN_INTEREST_LABEL], errors='coerce').abs()

    desired_max_px = 26
    desired_min_px = 6
    sizeref = 2.0 * oi.max() / (desired_max_px ** 2)

    trace = go.Scatter(
        x=data[x],
        y=data[y],
        mode='markers',
        marker={
            "size": oi,
            "sizemode": 'area',
            "sizeref": sizeref,
            "sizemin": desired_min_px,
            "color": data[color],
            "colorscale": 'RdBu',
            "showscale": True,
            "colorbar": {"title": colorbar_title, "len": 0.5, "x": 1.1}
        },
        text=data[MARKET_NAMES_COL],
        hoverinfo='text',
        showlegend=False
    )

    # First / Last Week Marker
    first_week = data.iloc[0]
    last_week = data.iloc[-1]

    first_week_trace = go.Scatter(
        x=[first_week[x]], y=[first_week[y]],
        mode='markers', marker={"color": 'red', "size": 15},
        name=FIRST_WEEK_LABEL
    )
    last_week_trace = go.Scatter(
        x=[last_week[x]], y=[last_week[y]],
        mode='markers', marker={"color": 'black', "size": 15},
        name=MOST_RECENT_WEEK
    )

    # --- Trendlinie (OLS) - über die ganze Plotbreite, solid, ohne Legende/Annotation ---
    xv = data[x].astype(float).to_numpy()
    yv = data[y].astype(float).to_numpy()
    mask_finite = np.isfinite(xv) & np.isfinite(yv)

    trend_trace = None
    if mask_finite.sum() >= 2:
        m, c = np.polyfit(xv[mask_finite], yv[mask_finite], 1)
        x_line = np.array([x_min, x_max])
        y_line = m * x_line + c
        trend_trace = go.Scatter(
            x=x_line, y=y_line,
            mode='lines',
            line={"color": 'black', "width": 2},
            hoverinfo='skip',
            showlegend=False
        )

    # Layout
    layout = go.Layout(
        title=title,
        xaxis={"title": x_title, "range": [x_min, x_max]},
        yaxis={"title": y_title, "range": [y_min, y_max]},
        showlegend=True,
        width=1000, height=600
    )

    # Figure zusammensetzen
    traces = [trace, first_week_trace, last_week_trace]
    if trend_trace:
        traces.append(trend_trace)

    fig = go.Figure(data=traces, layout=layout)
    return fig

# Callback to update the Dry Powder Concentration/Clustering Indicator graph
@app.callback(
    Output('dp-concentration-clustering-graph', 'figure'),
    [Input('concentration-clustering-date-picker-range', 'start_date'),
     Input('concentration-clustering-date-picker-range', 'end_date'),
     Input('concentration-clustering-radio', 'value')]
)
def update_concentration_clustering_graph(start_date, end_date, selected_indicator):
    _sd = start_date if start_date is not None else default_start_date
    _ed = end_date   if end_date   is not None else default_end_date
    filtered_df = df_pivoted[(df_pivoted['Date'] >= _sd) &
                             (df_pivoted['Date'] <= _ed)]
    
    # Aggregate the data by market, keeping only numeric columns
    agg_df = filtered_df.groupby(MARKET_NAMES_COL).mean(numeric_only=True).reset_index()
    
    conc_col, clust_col = _indicator_cols(selected_indicator)
    concentration_range, clustering_range = calculate_ranges(agg_df, conc_col, clust_col)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=clustering_range,
        y=concentration_range,
        mode=MARKERS_TEXT_MODE,
        text=agg_df[MARKET_NAMES_COL],
        textposition='top center',
        marker={"size": 10, "opacity": 0.6, "color": 'green', "line": {"width": 1, "color": 'black'}}
    ))
    
    fig.update_layout(
        title=f'DP Concentration/Clustering Indicator ({selected_indicator})',
        xaxis_title='MM Long Clustering Range' if selected_indicator == 'MML' else 'MM Short Clustering Range',
        yaxis_title='MM Long Concentration Range' if selected_indicator == 'MML' else 'MM Short Concentration Range',
        xaxis={"range": [-5, 110]},  # Adjusted to ensure all bubbles are visible
        yaxis={"range": [-5, 110]},  # Adjusted to ensure all bubbles are visible
        showlegend=False
    )
    
    return fig


# ---------------------------------------------------------------------------
# PPCI – Callback
# ---------------------------------------------------------------------------
@app.callback(
    Output('positioning-price-concentration-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('ppci-mm-radio', 'value')]
)
def update_ppci(selected_market, start_date, end_date, direction):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy()

    if dff.empty:
        return go.Figure()

    # Normalize Date to tz-naive for merging
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    # Long/Short Concentration (%)
    total_oi = pd.to_numeric(dff[OPEN_INTEREST_LABEL], errors='coerce').replace(0, np.nan)
    dff['_long_conc']  = 100.0 * pd.to_numeric(dff[MANAGED_MONEY_LONG_COL],  errors='coerce') / total_oi
    dff['_short_conc'] = 100.0 * pd.to_numeric(dff[MANAGED_MONEY_SHORT_COL], errors='coerce') / total_oi

    if direction == 'MML':
        color_col      = '_long_conc'
        colorbar_title = 'MML Concentration (%)'
    else:
        color_col      = '_short_conc'
        colorbar_title = 'MMS Concentration (%)'

    # Merge Databento 2nd-nearby prices (futures_deferred_prices)
    price_col = _ppci_get_2nd_nearby_col(selected_market)
    y_title = PRICE_2ND_NEARBY_LABEL

    if price_col and not df_deferred_prices.empty and price_col in df_deferred_prices.columns:
        dff = merge_series_asof(dff, df_deferred_prices, price_col)
        y_vals = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        y_vals = pd.Series([np.nan] * len(dff), index=dff.index)
        y_title = f'Price (keine Daten für {selected_market})'

    # Bubble sizing: Total Open Interest
    oi = pd.to_numeric(dff[OPEN_INTEREST_LABEL], errors='coerce').fillna(0).abs()

    MIN_PX = 8
    MAX_PX = 30
    _oi_pos = oi[oi > 0]
    oi_lo = float(_oi_pos.min()) if _oi_pos.size > 0 else 1.0
    oi_hi = float(oi.max()) if oi.max() > 0 else 1.0
    sizes_oi = scaled_diameters(oi, min_px=MIN_PX, max_px=MAX_PX, lo=oi_lo, hi=oi_hi, log_scale=True)

    color_vals = pd.to_numeric(dff[color_col], errors='coerce')

    # Hover-Text
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f"Date: {d}<br>Price: {p:.2f}<br>Total Open Interest: {o:,.0f}<br>{colorbar_title}: {c:.1f}%"
        for d, p, o, c in zip(
            dates_str,
            y_vals.fillna(0),
            oi.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    # Haupttrace
    fig.add_trace(go.Scatter(
        x=dff['Date'],
        y=y_vals,
        mode='markers',
        marker={
            "size": sizes_oi,
            "sizemode": 'diameter',
            "sizeref": 1,
            "color": color_vals,
            "colorscale": 'RdYlGn',
            "showscale": True,
            "colorbar": {
                "title": colorbar_title,
                "thickness": 15,
                "len": 0.75,
                "yanchor": 'middle',
                "y": 0.5
            },
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Bubble-Size-Legende dynamisch
    base = oi[oi > 0]
    if base.size >= 3:
        q = [0.10, 0.30, 0.50, 0.70, 0.90]
        legend_vals = np.unique(np.round(np.quantile(base, q)).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([50000, 100000, 150000, 200000, 250000], dtype=int)

    n_leg = len(legend_vals)
    legend_sizes = np.linspace(7, 20, n_leg) if n_leg > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker={
                "size": float(s),
                "sizemode": 'diameter',
                "sizeref": 1,
                "color": 'gray',
                "opacity": 0.6
            },
            showlegend=True,
            name=f"{int(v):,}",
            hoverinfo='skip'
        ))

    # Letzter Datenpunkt hervorheben
    if not dff.empty and not y_vals.empty:
        fig.add_trace(go.Scatter(
            x=[dff.iloc[-1]['Date']],
            y=[y_vals.iloc[-1]],
            mode='markers',
            marker={
                "size": 10,
                "color": 'black',
                "opacity": 1.0,
                "line": {"width": 4, "color": 'red'}
            },
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'Positioning Price Concentration Indicator ({direction}) – {selected_market}',
        xaxis_title=REPORT_DATE_LABEL,
        yaxis_title=y_title,
        legend={
            "title": {"text": 'Total Open Interest'},
            "itemsizing": 'trace',
            "x": 1.2,
            "y": 0.5,
            "font": {"size": 12}
        },
        margin={"l": 60, "r": 160, "t": 60, "b": 60},
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# PP Clustering Indicator – Callback
# Preisquelle: df_deferred_prices via _ppci_get_2nd_nearby_col (Databento .c.1).
# Unterschied zum PPCI: Farbe = Long/Short Clustering statt Concentration (%).
# ---------------------------------------------------------------------------
@app.callback(
    Output('pp-clustering-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('ppci-clustering-radio', 'value')]
)
def update_pp_clustering(selected_market, start_date, end_date, mm_type):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy()

    if dff.empty:
        return go.Figure()

    # Normalize Date to tz-naive for merging (identisch zu PPCI)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if mm_type == 'MML':
        color_col      = LONG_CLUSTERING_COL
        colorbar_title = 'MML Clustering'
    else:
        color_col      = SHORT_CLUSTERING_COL
        colorbar_title = 'MMS Clustering'

    # Databento 2nd-nearby prices (futures_deferred_prices)
    price_col = _ppci_get_2nd_nearby_col(selected_market)
    y_title = PRICE_2ND_NEARBY_LABEL

    if price_col and not df_deferred_prices.empty and price_col in df_deferred_prices.columns:
        dff = merge_series_asof(dff, df_deferred_prices, price_col)
        y_vals = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        y_vals = pd.Series([np.nan] * len(dff), index=dff.index)
        y_title = f'Price (keine Daten für {selected_market})'

    # Bubble-Größen (identisch zu PPCI)
    oi = pd.to_numeric(dff[OPEN_INTEREST_LABEL], errors='coerce').fillna(0).abs()
    MIN_PX = 8
    MAX_PX = 30
    _oi_pos = oi[oi > 0]
    oi_lo = float(_oi_pos.min()) if _oi_pos.size > 0 else 1.0
    oi_hi = float(oi.max()) if oi.max() > 0 else 1.0
    sizes_oi = scaled_diameters(oi, min_px=MIN_PX, max_px=MAX_PX, lo=oi_lo, hi=oi_hi, log_scale=True)

    color_vals = pd.to_numeric(dff[color_col], errors='coerce')

    # Hover-Text
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f"Date: {d}<br>Price: {p:.2f}<br>Total Open Interest: {o:,.0f}<br>{colorbar_title}: {c:.1f}"
        for d, p, o, c in zip(
            dates_str,
            y_vals.fillna(0),
            oi.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dff['Date'],
        y=y_vals,
        mode='markers',
        marker={
            "size": sizes_oi,
            "sizemode": 'diameter',
            "sizeref": 1,
            "color": color_vals,
            "colorscale": 'RdYlGn',
            "showscale": True,
            "colorbar": {
                "title": colorbar_title,
                "thickness": 15,
                "len": 0.75,
                "yanchor": 'middle',
                "y": 0.5
            },
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # OI-Bubble-Größen-Legende (identisch zu PPCI)
    base = oi[oi > 0]
    if base.size >= 3:
        q = [0.10, 0.30, 0.50, 0.70, 0.90]
        legend_vals = np.unique(np.round(np.quantile(base, q)).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([50000, 100000, 150000, 200000, 250000], dtype=int)

    n_leg = len(legend_vals)
    legend_sizes = np.linspace(7, 20, n_leg) if n_leg > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker={
                "size": float(s),
                "sizemode": 'diameter',
                "sizeref": 1,
                "color": 'gray',
                "opacity": 0.6
            },
            showlegend=True,
            name=f"{int(v):,}",
            hoverinfo='skip'
        ))

    # Letzter Datenpunkt hervorheben (identisch zu PPCI)
    if not dff.empty and not y_vals.empty:
        fig.add_trace(go.Scatter(
            x=[dff.iloc[-1]['Date']],
            y=[y_vals.iloc[-1]],
            mode='markers',
            marker={
                "size": 10,
                "color": 'black',
                "opacity": 1.0,
                "line": {"width": 4, "color": 'red'}
            },
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'PP Clustering Indicator ({mm_type}) – {selected_market}',
        xaxis_title=REPORT_DATE_LABEL,
        yaxis_title=y_title,
        legend={
            "title": {"text": 'Total Open Interest'},
            "itemsizing": 'trace',
            "x": 1.2,
            "y": 0.5,
            "font": {"size": 12}
        },
        margin={"l": 60, "r": 160, "t": 60, "b": 60},
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# PP Position Size Indicator – Callback
# Preisquelle: df_deferred_prices via _ppci_get_2nd_nearby_col (Databento .c.1).
# Bubble-Größe = Anzahl MM-Trader (statt OI), Farbe = Position Size in USD.
# Position Size ($) = MML/MMS Position Size (Kontrakte/Trader) × Price.
# ---------------------------------------------------------------------------
@app.callback(
    Output('pp-position-size-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('ppci-position-size-radio', 'value')]
)
def update_pp_position_size(selected_market, start_date, end_date, mm_type):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy()

    if dff.empty:
        return go.Figure()

    # Normalize Date to tz-naive for merging (identisch zu PPCI)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    # Databento 2nd-nearby prices (futures_deferred_prices)
    price_col = _ppci_get_2nd_nearby_col(selected_market)
    y_title = PRICE_2ND_NEARBY_LABEL

    if price_col and not df_deferred_prices.empty and price_col in df_deferred_prices.columns:
        dff = merge_series_asof(dff, df_deferred_prices, price_col)
        y_vals = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        y_vals = pd.Series([np.nan] * len(dff), index=dff.index)
        y_title = f'Price (keine Daten für {selected_market})'

    # Position Size in USD = (MML/MMS Position Size in Kontrakten) × Kontraktgröße × Price
    price_series = y_vals.reset_index(drop=True)
    dff = dff.reset_index(drop=True)
    contract_size = _ppci_get_contract_size(selected_market)

    if mm_type == 'MML':
        traders_col    = TRADERS_MM_LONG_COL
        pos_size_contr = pd.to_numeric(dff[MML_POSITION_SIZE_COL], errors='coerce')
        colorbar_title = 'Long Position Size ($)'
        size_legend_title = 'Number of Long Traders'
    else:
        traders_col    = TRADERS_MM_SHORT_COL
        pos_size_contr = pd.to_numeric(dff[MMS_POSITION_SIZE_COL], errors='coerce')
        colorbar_title = 'Short Position Size ($)'
        size_legend_title = 'Number of Short Traders'

    # Farbwerte: Position Size in USD
    color_vals = pos_size_contr * contract_size * price_series

    # Bubble-Größe = Anzahl Trader
    traders = pd.to_numeric(dff[traders_col], errors='coerce').fillna(0).abs()
    MIN_PX = 8
    MAX_PX = 30
    _tr_pos = traders[traders > 0]
    tr_lo = float(_tr_pos.min()) if _tr_pos.size > 0 else 1.0
    tr_hi = float(traders.max()) if traders.max() > 0 else 1.0
    sizes_traders = scaled_diameters(traders, min_px=MIN_PX, max_px=MAX_PX, lo=tr_lo, hi=tr_hi)

    # Hover-Text
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f"Date: {d}<br>Price: {p:.2f}<br>{size_legend_title}: {t:,.0f}<br>{colorbar_title}: {c:,.0f}"
        for d, p, t, c in zip(
            dates_str,
            y_vals.fillna(0),
            traders.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dff['Date'],
        y=y_vals,
        mode='markers',
        marker={
            "size": sizes_traders,
            "sizemode": 'diameter',
            "sizeref": 1,
            "color": color_vals,
            "colorscale": 'RdYlGn',
            "showscale": True,
            "colorbar": {
                "title": colorbar_title,
                "thickness": 15,
                "len": 0.75,
                "yanchor": 'middle',
                "y": 0.5
            },
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Trader-Anzahl-Legende (Bubble-Größen)
    base = traders[traders > 0]
    if base.size >= 3:
        q = [0.10, 0.30, 0.50, 0.70, 0.90]
        legend_vals = np.unique(np.round(np.quantile(base, q)).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([20, 40, 60, 80, 100], dtype=int)

    n_leg = len(legend_vals)
    legend_sizes = np.linspace(7, 20, n_leg) if n_leg > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker={
                "size": float(s),
                "sizemode": 'diameter',
                "sizeref": 1,
                "color": 'gray',
                "opacity": 0.6
            },
            showlegend=True,
            name=f"{int(v):,}",
            hoverinfo='skip'
        ))

    # Letzter Datenpunkt hervorheben (identisch zu PPCI)
    if not dff.empty and not y_vals.empty:
        fig.add_trace(go.Scatter(
            x=[dff.iloc[-1]['Date']],
            y=[y_vals.iloc[-1]],
            mode='markers',
            marker={
                "size": 10,
                "color": 'black',
                "opacity": 1.0,
                "line": {"width": 4, "color": 'red'}
            },
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'PP Position Size Indicator ({mm_type}) – {selected_market}',
        xaxis_title=REPORT_DATE_LABEL,
        yaxis_title=y_title,
        legend={
            "title": {"text": size_legend_title},
            "itemsizing": 'trace',
            "x": 1.2,
            "y": 0.5,
            "font": {"size": 12}
        },
        margin={"l": 60, "r": 160, "t": 60, "b": 60},
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# Dry Powder Notional Indicator – Callback
# Orientierung am DP Indicator: Farben, Trendlinien, Most-Recent-Week-Marker,
# Bubble-Sizing und Layout-Parameter werden identisch übernommen.
# Y-Achse: Notional Exposure in USD bn = (MM OI × Kontraktgröße × Price) / 1e9
#   MML (Long):  positiv (oberhalb Nulllinie)
#   MMS (Short): negativ (unterhalb Nulllinie)
# Preisquelle: df_futures_prices via _ppci_get_price_col (Front-Month, yfinance).
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-notional-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date')]
)
def update_dp_notional(selected_market, start_date, end_date):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    # Front-Month-Preis (yfinance, futures_prices)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)
    price_col = _ppci_get_price_col(selected_market)

    if price_col and not df_futures_prices.empty and price_col in df_futures_prices.columns:
        dff = merge_series_asof(dff, df_futures_prices, price_col)
        price_series = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        price_series = pd.Series([np.nan] * len(dff), index=dff.index)

    # Notional Exposure in USD bn
    # Formel: Kontrakte × Kontraktgröße (Einheiten/Kontrakt) × Preis (USD/Einheit) / 1e9
    contract_size = _ppci_get_contract_size(selected_market)
    mml_oi = pd.to_numeric(dff[MANAGED_MONEY_LONG_COL],  errors='coerce')
    mms_oi = pd.to_numeric(dff[MANAGED_MONEY_SHORT_COL], errors='coerce')

    y_mml =  mml_oi * contract_size * price_series / 1e9   # positiv
    y_mms = -mms_oi * contract_size * price_series / 1e9   # negativ

    x_mml = pd.to_numeric(dff[MML_TRADERS_COL], errors='coerce')
    x_mms = pd.to_numeric(dff[MMS_TRADERS_COL], errors='coerce')

    BUBBLE_PX = 14
    desired_max_px = 28

    COL_LONG  = "#2c7fb8"  # MML
    COL_SHORT = "#7fcdbb"  # MMS

    fig = go.Figure()

    # Wolken
    fig.add_trace(go.Scatter(
        x=x_mml, y=y_mml,
        mode='markers',
        marker={
            "size": BUBBLE_PX,
            "color": COL_LONG, "opacity": 0.75, "line": {"width": 0.6, "color": 'black'}
        },
        name='MML',
        hovertemplate='Traders: %{x}<br>Notional: %{y:.2f} USD bn<extra>MML</extra>'
    ))
    fig.add_trace(go.Scatter(
        x=x_mms, y=y_mms,
        mode='markers',
        marker={
            "size": BUBBLE_PX,
            "color": COL_SHORT, "opacity": 0.75, "line": {"width": 0.6, "color": 'black'}
        },
        name='MMS',
        hovertemplate='Traders: %{x}<br>Notional: %{y:.2f} USD bn<extra>MMS</extra>'
    ))

    # Trendlinien (identisch zu DP Indicator: weißer Untergrund + Farblinie)
    x_min = float(min(x_mml.min(), x_mms.min()))
    x_max = float(max(x_mml.max(), x_mms.max()))
    xs = np.array([x_min, x_max])

    def _add_notional_trend(x_s, y_s, color, label):
        mask = x_s.notna() & y_s.notna()
        xv = x_s[mask].astype(float).values
        yv = y_s[mask].astype(float).values
        if len(xv) < 2:
            return
        m, b = np.polyfit(xv, yv, 1)
        ys = m * xs + b
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": 'white', "width": 7},
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": color, "width": 3},
            name=label, showlegend=True
        ))

    _add_notional_trend(x_mml, y_mml, COL_LONG,  'MML Trend')
    _add_notional_trend(x_mms, y_mms, COL_SHORT, 'MMS Trend')

    # Most Recent Week (identisch zu DP Indicator)
    fig.add_trace(go.Scatter(
        x=[x_mml.iloc[-1]], y=[y_mml.iloc[-1]],
        mode='markers',
        marker={"size": desired_max_px + 4, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK, legendgroup='recent', showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[x_mms.iloc[-1]], y=[y_mms.iloc[-1]],
        mode='markers',
        marker={"size": desired_max_px + 4, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK, legendgroup='recent', showlegend=False
    ))

    fig.update_layout(
        title='DP Notional Indicator',
        xaxis={
            "title": NUMBER_OF_TRADERS_LABEL,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": 'Long and Short $ Exposure (USD bn)',
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2,
            "zeroline": True, "zerolinecolor": 'black', "zerolinewidth": 1
        },
        plot_bgcolor='white',
        legend_title=TRADER_GROUP_COL,
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Time Indicator – Callback
# X = Number of Traders (MML / MMS), Y = Long / Short Concentration (%)
# Farbe = Year (wie DP Net Indicators: separate Trace pro Jahr)
# MML: Kreise (oberhalb 0), MMS: Dreiecke (unterhalb 0)
# Konzentration: 100 * MM Long|Short OI / Total OI  (MMS negativ)
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-time-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date')]
)
def update_dp_time(selected_market, start_date, end_date):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    # Konzentration (%) – identisch zum PPCI-Callback
    total_oi = pd.to_numeric(dff[OPEN_INTEREST_LABEL], errors='coerce').replace(0, np.nan)
    dff['_y_mml'] =  100.0 * pd.to_numeric(dff[MANAGED_MONEY_LONG_COL],  errors='coerce') / total_oi
    dff['_y_mms'] = -100.0 * pd.to_numeric(dff[MANAGED_MONEY_SHORT_COL], errors='coerce') / total_oi

    x_mml = pd.to_numeric(dff[MML_TRADERS_COL], errors='coerce')
    x_mms = pd.to_numeric(dff[MMS_TRADERS_COL], errors='coerce')

    fig = go.Figure()

    # Dummy-Traces für Shape-Legende (MML / MMS)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker={"symbol": 'circle', "color": 'gray', "size": 9},
        name='MML', legendgroup='shape_mml'
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker={"symbol": 'triangle-down', "color": 'gray', "size": 9},
        name='MMS', legendgroup='shape_mms'
    ))

    # Scatter-Traces: pro Jahr eine Farbe, MML=Kreis / MMS=Dreieck
    for year in sorted(dff['Year'].unique()):
        mask = dff['Year'] == year

        fig.add_trace(go.Scatter(
            x=x_mml[mask], y=dff['_y_mml'][mask],
            mode='markers',
            marker={"symbol": 'circle', "size": 12, "opacity": 0.75},
            name=str(year), legendgroup=str(year), showlegend=True,
            hovertemplate=(
                f'Year: {year}<br>'
                'Traders: %{x}<br>'
                'Long Conc.: %{y:.1f}%'
                '<extra>MML</extra>'
            )
        ))
        fig.add_trace(go.Scatter(
            x=x_mms[mask], y=dff['_y_mms'][mask],
            mode='markers',
            marker={"symbol": 'triangle-down', "size": 12, "opacity": 0.75},
            name=str(year), legendgroup=str(year), showlegend=False,
            hovertemplate=(
                f'Year: {year}<br>'
                'Traders: %{x}<br>'
                'Short Conc.: %{y:.1f}%'
                '<extra>MMS</extra>'
            )
        ))

    # Trendlinien (analog zu DP Notional: weißer Untergrund + Farblinie)
    x_all = pd.concat([x_mml, x_mms]).dropna()
    if not x_all.empty:
        xs = np.array([float(x_all.min()), float(x_all.max())])

        def _add_time_trend(xs_arr, x_s, y_s, color, label):
            mask_t = x_s.notna() & y_s.notna()
            xv = x_s[mask_t].astype(float).values
            yv = y_s[mask_t].astype(float).values
            if len(xv) < 2:
                return
            m, b = np.polyfit(xv, yv, 1)
            ys = m * xs_arr + b
            fig.add_trace(go.Scatter(
                x=xs_arr, y=ys, mode='lines',
                line={"color": 'white', "width": 7},
                showlegend=False, hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=xs_arr, y=ys, mode='lines',
                line={"color": color, "width": 3},
                name=label, showlegend=True
            ))

        _add_time_trend(xs, x_mml, dff['_y_mml'], '#2c7fb8', 'MML Trend')
        _add_time_trend(xs, x_mms, dff['_y_mms'], '#7fcdbb', 'MMS Trend')

    # Most Recent Week (identisch zu DP Notional)
    desired_max_px = 18
    fig.add_trace(go.Scatter(
        x=[x_mml.iloc[-1]], y=[dff['_y_mml'].iloc[-1]],
        mode='markers',
        marker={"size": desired_max_px, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK, legendgroup='recent', showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[x_mms.iloc[-1]], y=[dff['_y_mms'].iloc[-1]],
        mode='markers',
        marker={"size": desired_max_px, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK, legendgroup='recent', showlegend=False
    ))

    fig.update_layout(
        title='DP Time Indicator',
        xaxis={
            "title": NUMBER_OF_TRADERS_LABEL,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": 'Long and Short Concentration (%)',
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2,
            "zeroline": True, "zerolinecolor": 'black', "zerolinewidth": 1
        },
        plot_bgcolor='white',
        legend_title='Year',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Price Indicator – Callback
# X = PMPU Long/Short Traders, Y = PMPU Long/Short OI
# Punktfarbe = Futures-Preis (Databento 2nd Nearby .c.1, Report Date)
# Trendlinie + Most-Recent-Week-Marker identisch zu DP Notional/Time Indicator
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-price-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('dp-price-radio', 'value')]
)
def update_dp_price(selected_market, start_date, end_date, pmpu_side):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if pmpu_side == 'PMPUL':
        x_col    = PMPUL_TRADERS_COL
        y_col    = PMPU_LONG_COL
        x_title  = 'PMPU Number of Long Traders'
        y_title  = 'PMPU Long OI (Contracts)'
        pt_title = 'DP Price Indicator (PMPU Long)'
    else:
        x_col    = 'PMPUS Traders'
        y_col    = PMPU_SHORT_COL
        x_title  = 'PMPU Number of Short Traders'
        y_title  = 'PMPU Short OI (Contracts)'
        pt_title = 'DP Price Indicator (PMPU Short)'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce')

    # Databento 2nd-nearby price als Farbe (merge_asof, 7-Tage-Toleranz)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)
    price_col = _ppci_get_2nd_nearby_col(selected_market)

    if price_col and not df_deferred_prices.empty and price_col in df_deferred_prices.columns:
        dff = merge_series_asof(dff, df_deferred_prices, price_col)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce')
        color_vals    = pd.to_numeric(dff[price_col], errors='coerce')
        colorbar_title = 'Price 2nd Nearby (USD)'
    else:
        color_vals    = pd.Series([np.nan] * len(dff), index=dff.index)
        colorbar_title = 'Price (n/a)'

    # Hover
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}<br>'
        + (f'Price 2nd Nearby: {c:.2f} USD' if pd.notna(c) else 'Price 2nd Nearby: n/a')
        for d, x, y, c in zip(dates_str, x_vals, y_vals, color_vals)
    ]

    hover_arr   = np.array(hover_text, dtype=object)
    mask_price  = color_vals.notna().values   # Wochen mit Preisdaten
    mask_noprice = color_vals.isna().values   # Wochen ohne Preisdaten

    fig = go.Figure()

    # Graue Punkte: keine 2nd-Nearby-Preisdaten verfügbar
    if mask_noprice.any():
        fig.add_trace(go.Scatter(
            x=x_vals.values[mask_noprice], y=y_vals.values[mask_noprice],
            mode='markers',
            marker={"size": 14, "color": 'lightgrey', "opacity": 0.7,
                        "line": {"width": 0.6, "color": 'black'}},
            text=hover_arr[mask_noprice],
            hoverinfo='text',
            name='Keine Preisdaten',
            showlegend=True
        ))

    # Farbige Punkte: Preisniveau als Farbskala
    if mask_price.any():
        fig.add_trace(go.Scatter(
            x=x_vals.values[mask_price], y=y_vals.values[mask_price],
            mode='markers',
            marker={
                "size": 14,
                "color": color_vals.values[mask_price],
                "colorscale": 'RdYlGn',
                "showscale": True,
                "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75},
                "opacity": 0.85,
                "line": {"width": 0.6, "color": 'black'}
            },
            text=hover_arr[mask_price],
            hoverinfo='text',
            name='Price 2nd Nearby',
            showlegend=False
        ))

    # Most Recent Week (identisch zu DP Notional/Time)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker={"size": 18, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK
    ))

    fig.update_layout(
        title=pt_title,
        xaxis={
            "title": x_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        plot_bgcolor='white',
        legend={"title": 'Legend', "itemsizing": 'constant'},
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Curve Indicator – Callback
# X = MM Long/Short Traders, Y = MM Long/Short OI
# Punktfarbe = Curve Range (%) = (3rd Nearby − 2nd Nearby) / 2nd Nearby × 100
#   Positiv → Contango (grün), Negativ → Backwardation (rot)
# Colorscale: RdYlGn (identisch zu DP Price Indicator)
# ---------------------------------------------------------------------------
def _build_dp_curve_hover(dates_str, x_vals, y_vals, color_vals, x_title, y_title):
    """Baut die Hover-Texte für den DP Curve Indicator auf."""
    hover_text = []
    for d, x, y, c in zip(dates_str, x_vals.fillna(0), y_vals.fillna(0), color_vals):
        if pd.notna(c):
            structure = 'Contango' if c > 0 else 'Backwardation'
            curve_str = f'{c:.2f}%'
        else:
            structure = 'n/a'
            curve_str = 'n/a'
        hover_text.append(
            f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}'
            f'<br>Curve Range: {curve_str} ({structure})'
        )
    return hover_text


@app.callback(
    Output('dp-curve-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('dp-curve-radio', 'value')]
)
def update_dp_curve(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col    = MML_TRADERS_COL
        y_col    = MML_LONG_OI_COL
        x_title  = MM_NUM_LONG_TRADERS_COL
        y_title  = MM_LONG_OI_CONTRACTS_COL
        pt_title = 'DP Curve Indicator (MM Long)'
    else:
        x_col    = MMS_TRADERS_COL
        y_col    = MMS_SHORT_OI_COL
        x_title  = MM_NUM_SHORT_TRADERS_COL
        y_title  = MM_SHORT_OI_CONTRACTS_COL
        pt_title = 'DP Curve Indicator (MM Short)'

    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    # Curve Range (%) = (3rd Nearby − 2nd Nearby) / 2nd Nearby × 100
    price_col_2nd = _ppci_get_2nd_nearby_col(selected_market)
    price_col_3rd = _ppci_get_3rd_nearby_col(selected_market)

    if (price_col_2nd and price_col_3rd
            and not df_deferred_prices.empty
            and price_col_2nd in df_deferred_prices.columns
            and price_col_3rd in df_deferred_prices.columns):
        prices = df_deferred_prices[['Date', price_col_2nd, price_col_3rd]].dropna(
            subset=[price_col_2nd, price_col_3rd]
        ).copy()
        prices['_curve_range'] = (
            (prices[price_col_3rd] - prices[price_col_2nd]) / prices[price_col_2nd] * 100
        )
        prices = prices.rename(columns={'Date': '_pdate'}).sort_values('_pdate')
        dff = dff.sort_values('_date').reset_index(drop=True)
        dff = pd.merge_asof(
            dff, prices[['_pdate', '_curve_range']],
            left_on='_date', right_on='_pdate',
            direction='backward',
            tolerance=pd.Timedelta(days=7)
        )
        color_vals     = pd.to_numeric(dff['_curve_range'], errors='coerce')
    else:
        color_vals     = pd.Series([np.nan] * len(dff), index=dff.index)

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # Hover
    dates_str  = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = _build_dp_curve_hover(dates_str, x_vals, y_vals, color_vals, x_title, y_title)

    # Binäre Farb-Logik: Grün = Contango (c > 0), Rot = Backwardation (c < 0)
    _COL_CONTANGO      = '#2ca02c'   # grün
    _COL_BACKWARDATION = '#d62728'   # rot
    _COL_NODATA        = '#aec7e8'   # hellblau (keine Kurvendaten verfügbar)
    _MARKER_SIZE       = 20

    hover_arr  = np.array(hover_text, dtype=object)
    mask_c = (color_vals > 0).fillna(False).values   # Contango
    mask_b = (color_vals < 0).fillna(False).values   # Backwardation
    mask_n = color_vals.isna().values                 # keine Daten

    fig = go.Figure()

    if mask_n.any():
        fig.add_trace(go.Scatter(
            x=x_vals.values[mask_n], y=y_vals.values[mask_n],
            mode='markers',
            marker={"size": _MARKER_SIZE, "color": _COL_NODATA, "opacity": 0.6,
                        "line": {"width": 0.6, "color": 'black'}},
            text=hover_arr[mask_n],
            hoverinfo='text',
            name='Keine Kurvendaten',
            showlegend=True
        ))

    if mask_b.any():
        fig.add_trace(go.Scatter(
            x=x_vals.values[mask_b], y=y_vals.values[mask_b],
            mode='markers',
            marker={"size": _MARKER_SIZE, "color": _COL_BACKWARDATION, "opacity": 0.85,
                        "line": {"width": 0.6, "color": 'black'}},
            text=hover_arr[mask_b],
            hoverinfo='text',
            name='Backwardation',
            showlegend=True
        ))

    if mask_c.any():
        fig.add_trace(go.Scatter(
            x=x_vals.values[mask_c], y=y_vals.values[mask_c],
            mode='markers',
            marker={"size": _MARKER_SIZE, "color": _COL_CONTANGO, "opacity": 0.85,
                        "line": {"width": 0.6, "color": 'black'}},
            text=hover_arr[mask_c],
            hoverinfo='text',
            name='Contango',
            showlegend=True
        ))

    # Colorbar-Range: unsichtbarer Dummy-Trace – Rot (min) direkt zu Grün (max), nur Extremwerte
    c_min = float(color_vals.min()) if color_vals.notna().any() else -1.0
    c_max = float(color_vals.max()) if color_vals.notna().any() else  1.0
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker={
            "colorscale": [[0, '#d62728'], [1, '#2ca02c']],
            "showscale": True,
            "cmin": c_min,
            "cmax": c_max,
            "colorbar": {
                "title": 'Curve Range (%)<br>(Report Date)',
                "thickness": 15,
                "len": 0.5,
                "tickvals": [c_min, c_max],
                "ticktext": [f'{c_min:.2f}', f'{c_max:.2f}'],
            }
        },
        hoverinfo='skip',
        showlegend=False
    ))

    # Most Recent Week
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker={"size": _MARKER_SIZE + 4, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK
    ))

    fig.update_layout(
        title=pt_title,
        xaxis={
            "title": x_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        plot_bgcolor='white',
        legend={"title": 'Curve Structure', "itemsizing": 'constant'},
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Factor (VIX) – Callback
# X = MM Long/Short Traders, Y = MM Long/Short OI
# Punktfarbe = VIX-Wert (yfinance via macro_by_date), merge_asof 7-Tage-Toleranz
# Struktur identisch zu DP Price Indicator (ohne Trendlinie)
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-vix-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('dp-vix-radio', 'value')]
)
def update_dp_vix(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col   = MML_TRADERS_COL
        y_col   = MML_LONG_OI_COL
        x_title = MM_NUM_LONG_TRADERS_COL
        y_title = MM_LONG_OI_CONTRACTS_COL
        title   = 'DP Factor (VIX) Indicator – MML'
    else:
        x_col   = MMS_TRADERS_COL
        y_col   = MMS_SHORT_OI_COL
        x_title = MM_NUM_SHORT_TRADERS_COL
        y_title = MM_SHORT_OI_CONTRACTS_COL
        title   = 'DP Factor (VIX) Indicator – MMS'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # VIX-Wert als Farbe (yfinance via df_macro, merge_asof identisch zu df_futures_prices)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_macro.empty and 'vix' in df_macro.columns:
        dff = merge_series_asof(dff, df_macro, 'vix', tolerance_days=None)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        color_vals     = pd.to_numeric(dff['vix'], errors='coerce')
        colorbar_title = 'VIX'
    else:
        color_vals     = pd.Series([np.nan] * len(dff), index=dff.index)
        colorbar_title = 'VIX (n/a)'

    # Hover
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}<br>VIX: {c:.1f}'
        for d, x, y, c in zip(
            dates_str,
            x_vals.fillna(0),
            y_vals.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode='markers',
        marker={
            "size": 14,
            "color": color_vals,
            "colorscale": 'RdYlGn_r',   # hoher VIX = rot (Stress), tiefer VIX = grün
            "showscale": True,
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75},
            "opacity": 0.85,
            "line": {"width": 0.6, "color": 'black'}
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Trendlinie (identisch zu DP Notional: weißer Untergrund + Farblinie)
    mask_t = x_vals.notna() & y_vals.notna()
    if mask_t.sum() >= 2:
        xv = x_vals[mask_t].astype(float).values
        yv = y_vals[mask_t].astype(float).values
        xs = np.array([xv.min(), xv.max()])
        m, b = np.polyfit(xv, yv, 1)
        ys = m * xs + b
        col = '#2c7fb8' if mm_side == 'MML' else '#7fcdbb'
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": 'white', "width": 7},
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": col, "width": 3},
            name='Trend', showlegend=True
        ))

    # Most Recent Week (identisch zu DP Price Indicator)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker={"size": 18, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK
    ))

    fig.update_layout(
        title=title,
        xaxis={
            "title": x_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        plot_bgcolor='white',
        legend_title='Legend',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Factor (DXY) – Callback
# X = MM Long/Short Traders, Y = MM Long/Short OI
# Punktfarbe = DXY-Wert (usd_index via macro_by_date), merge_asof 7-Tage-Toleranz
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-dxy-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('dp-dxy-radio', 'value')]
)
def update_dp_dxy(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col   = MML_TRADERS_COL
        y_col   = MML_LONG_OI_COL
        x_title = MM_NUM_LONG_TRADERS_COL
        y_title = MM_LONG_OI_CONTRACTS_COL
        title   = 'DP Factor (DXY) Indicator – MML'
    else:
        x_col   = MMS_TRADERS_COL
        y_col   = MMS_SHORT_OI_COL
        x_title = MM_NUM_SHORT_TRADERS_COL
        y_title = MM_SHORT_OI_CONTRACTS_COL
        title   = 'DP Factor (DXY) Indicator – MMS'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # DXY-Wert als Farbe (yfinance via df_macro, merge_asof identisch zu VIX)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_macro.empty and 'usd_index' in df_macro.columns:
        dff = merge_series_asof(dff, df_macro, 'usd_index', tolerance_days=None)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        color_vals     = pd.to_numeric(dff['usd_index'], errors='coerce')
        colorbar_title = 'DXY'
    else:
        color_vals     = pd.Series([np.nan] * len(dff), index=dff.index)
        colorbar_title = 'DXY (n/a)'

    # Hover
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}<br>DXY: {c:.2f}'
        for d, x, y, c in zip(
            dates_str,
            x_vals.fillna(0),
            y_vals.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode='markers',
        marker={
            "size": 14,
            "color": color_vals,
            "colorscale": 'RdYlGn',    # tiefer DXY = rot (schwacher Dollar), hoher DXY = grün
            "showscale": True,
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75},
            "opacity": 0.85,
            "line": {"width": 0.6, "color": 'black'}
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Trendlinie (identisch zu VIX: weißer Untergrund + Farblinie)
    mask_t = x_vals.notna() & y_vals.notna()
    if mask_t.sum() >= 2:
        xv = x_vals[mask_t].astype(float).values
        yv = y_vals[mask_t].astype(float).values
        xs = np.array([xv.min(), xv.max()])
        m, b = np.polyfit(xv, yv, 1)
        ys = m * xs + b
        col = '#2c7fb8' if mm_side == 'MML' else '#7fcdbb'
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": 'white', "width": 7},
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": col, "width": 3},
            name='Trend', showlegend=True
        ))

    # Most Recent Week (identisch zu VIX)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker={"size": 18, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK
    ))

    fig.update_layout(
        title=title,
        xaxis={
            "title": x_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        plot_bgcolor='white',
        legend_title='Legend',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Currency Indicator (USD/CHF) – Callback
# X = MM Long/Short Traders, Y = MM Long/Short OI
# Punktfarbe = USD/CHF-Kurs (usd_chf via macro_by_date), merge_asof 7-Tage-Toleranz
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-currency-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('dp-currency-radio', 'value')]
)
def update_dp_currency(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col   = MML_TRADERS_COL
        y_col   = MML_LONG_OI_COL
        x_title = MM_NUM_LONG_TRADERS_COL
        y_title = MM_LONG_OI_CONTRACTS_COL
        title   = 'DP Currency Indicator – USD/CHF (MML)'
    else:
        x_col   = MMS_TRADERS_COL
        y_col   = MMS_SHORT_OI_COL
        x_title = MM_NUM_SHORT_TRADERS_COL
        y_title = MM_SHORT_OI_CONTRACTS_COL
        title   = 'DP Currency Indicator – USD/CHF (MMS)'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # USD/CHF-Kurs als Farbe (via df_macro, merge_asof identisch zu DXY/VIX)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_macro.empty and 'usd_chf' in df_macro.columns:
        dff = merge_series_asof(dff, df_macro, 'usd_chf', tolerance_days=None)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        color_vals     = pd.to_numeric(dff['usd_chf'], errors='coerce')
        colorbar_title = 'USD/CHF'
    else:
        color_vals     = pd.Series([np.nan] * len(dff), index=dff.index)
        colorbar_title = 'USD/CHF (n/a)'

    # Hover
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}<br>USD/CHF: {c:.4f}'
        for d, x, y, c in zip(
            dates_str,
            x_vals.fillna(0),
            y_vals.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode='markers',
        marker={
            "size": 14,
            "color": color_vals,
            "colorscale": 'RdYlGn',    # tiefer USD/CHF = rot (schwacher Dollar), hoher = grün
            "showscale": True,
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75},
            "opacity": 0.85,
            "line": {"width": 0.6, "color": 'black'}
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Trendlinie (identisch zu DXY/VIX: weißer Untergrund + Farblinie)
    mask_t = x_vals.notna() & y_vals.notna()
    if mask_t.sum() >= 2:
        xv = x_vals[mask_t].astype(float).values
        yv = y_vals[mask_t].astype(float).values
        xs = np.array([xv.min(), xv.max()])
        m, b = np.polyfit(xv, yv, 1)
        ys = m * xs + b
        col = '#2c7fb8' if mm_side == 'MML' else '#7fcdbb'
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": 'white', "width": 7},
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": col, "width": 3},
            name='Trend', showlegend=True
        ))

    # Most Recent Week (identisch zu DXY/VIX)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker={"size": 18, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK
    ))

    fig.update_layout(
        title=title,
        xaxis={
            "title": x_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        plot_bgcolor='white',
        legend_title='Legend',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Fundamental Indicator (Crude Oil Inventory) – Callback
# Nur für Crude Oil (WTI). X = PMPU Traders, Y = PMPU OI
# Punktfarbe = EIA Crude Oil Ending Stocks excl. SPR (Tausend Barrel)
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-fundamental-indicator-graph', 'figure'),
    [Input(MARKET_DROPDOWN_ID, 'value'),
     Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date'),
     Input('dp-fundamental-radio', 'value')]
)
def update_dp_fundamental(selected_market, start_date, end_date, pmpu_side):
    # Indikator nur für Crude Oil (WTI) verfügbar
    if selected_market is None or 'WTI' not in selected_market.upper():
        fig = go.Figure()
        fig.add_annotation(
            text=(
                f"Der DP Fundamental Indicator ist ausschliesslich für "
                f"<b>Crude Oil (WTI)</b> verfügbar.<br>"
                f"Aktuell ausgewählt: <b>{selected_market or '–'}</b>"
            ),
            xref='paper', yref='paper',
            x=0.5, y=0.5,
            showarrow=False,
            font={"size": 15, "color": '#555'},
            align='center',
            bgcolor='#f8f9fa',
            bordercolor='#dee2e6',
            borderwidth=1,
            borderpad=14,
        )
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis={"visible": False},
            yaxis={"visible": False},
            height=250,
        )
        return fig

    dff = df_pivoted[
        (df_pivoted[MARKET_NAMES_COL] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if pmpu_side == 'PMPUL':
        x_col   = TRADERS_PROD_MERC_LONG
        y_col   = PMPU_LONG_COL
        x_title = 'PMPU Number of Long Traders'
        y_title = 'PMPU Long OI (Contracts)'
        title   = 'DP Fundamental Indicator – Crude Oil Inventory (PMPUL)'
        trend_col = '#e6550d'
    else:
        x_col   = TRADERS_PROD_MERC_SHORT
        y_col   = PMPU_SHORT_COL
        x_title = 'PMPU Number of Short Traders'
        y_title = 'PMPU Short OI (Contracts)'
        title   = 'DP Fundamental Indicator – Crude Oil Inventory (PMPUS)'
        trend_col = '#fdae6b'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # EIA-Lagerbestand als Farbe (merge_asof identisch zu USD/CHF-Logik)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_eia.empty and CRUDE_OIL_STOCKS_COL in df_eia.columns:
        dff = merge_series_asof(dff, df_eia, CRUDE_OIL_STOCKS_COL, direction='nearest')
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        color_vals     = pd.to_numeric(dff[CRUDE_OIL_STOCKS_COL], errors='coerce')
        colorbar_title = 'Inventory (kb)'
    else:
        color_vals     = pd.Series([np.nan] * len(dff), index=dff.index)
        colorbar_title = 'Inventory (n/a)'

    # Hover
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}<br>EIA Inventory: {c:,.0f} kb'
        for d, x, y, c in zip(
            dates_str,
            x_vals.fillna(0),
            y_vals.fillna(0),
            color_vals.fillna(0)
        )
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode='markers',
        marker={
            "size": 14,
            "color": color_vals,
            "colorscale": 'YlOrBr',   # hell = tiefe Bestände, dunkel = hohe Bestände
            "showscale": True,
            "colorbar": {"title": colorbar_title, "thickness": 15, "len": 0.75},
            "opacity": 0.85,
            "line": {"width": 0.6, "color": 'black'}
        },
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Trendlinie (identisch zu Currency/DXY/VIX)
    mask_t = x_vals.notna() & y_vals.notna()
    if mask_t.sum() >= 2:
        xv = x_vals[mask_t].astype(float).values
        yv = y_vals[mask_t].astype(float).values
        xs = np.array([xv.min(), xv.max()])
        m, b = np.polyfit(xv, yv, 1)
        ys = m * xs + b
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": 'white', "width": 7},
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line={"color": trend_col, "width": 3},
            name='Trend', showlegend=True
        ))

    # Most Recent Week
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker={"size": 18, "color": 'black', "line": {"width": 2, "color": 'white'}},
        name=MOST_RECENT_WEEK
    ))

    fig.update_layout(
        title=title,
        xaxis={
            "title": x_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True, "gridcolor": LIGHTGRAY, "gridwidth": 2, "zeroline": False
        },
        plot_bgcolor='white',
        legend_title='Legend',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# OBOS Concentration Indicator – Callback
# Zeigt alle Märkte gleichzeitig als Snapshot für das letzte Reportdatum
# innerhalb des gewählten Zeitraums. Keine Marktauswahl via Dropdown.
# ---------------------------------------------------------------------------

# OBOS-Konstanten und -Funktionen: siehe src/analysis/obos_indicators.py


def _obos_add_chart_shapes(fig):
    """Fügt Eckzonen (OB/OS) und Mittellinien für beide Panels hinzu."""
    for _, xref, yref in [(1, 'x', 'y'), (2, 'x2', 'y')]:
        for x0, x1, y0, y1 in [(75, 100, 75, 100), (0, 25, 0, 25)]:
            fig.add_shape(
                type='rect', x0=x0, x1=x1, y0=y0, y1=y1,
                xref=xref, yref=yref,
                fillcolor='lightgray', opacity=0.35, line_width=0,
            )
        fig.add_shape(type='line', x0=50, x1=50, y0=0, y1=100,
                      xref=xref, yref=yref,
                      line={"color": '#888', "width": 1, "dash": 'dot'})
        fig.add_shape(type='line', x0=0, x1=100, y0=50, y1=50,
                      xref=xref, yref=yref,
                      line={"color": '#888', "width": 1, "dash": 'dot'})


def _obos_add_scatter_traces(fig, rdf):
    """Plottet je Markt einen Punkt im linken (Short) und rechten (Long) Panel."""
    for _, row in rdf.iterrows():
        common_marker = {
            "size": 32, "color": row['color'], "opacity": 0.90,
            "line": {"width": 1, "color": 'white'},
        }
        common_text = {"size": 9, "color": 'white', "family": 'Arial Black, Arial, sans-serif'}
        hover_base  = (
            f"<b>{row['market']}</b> ({row['ticker']})<br>"
            f"Kurve: {row['curve_label']}<br>"
            f"Price Range (2nd Nearby): {row['price_range']:.0f} %<br>"
        )

        if pd.notna(row['mms_range']) and pd.notna(row['price_range']):
            fig.add_trace(
                go.Scatter(
                    x=[row['mms_range']], y=[row['price_range']],
                    mode=MARKERS_TEXT_MODE, marker=common_marker,
                    text=[row['ticker']], textposition='middle center', textfont=common_text,
                    showlegend=False,
                    hovertemplate=hover_base + f"MMS Range: {row['mms_range']:.0f} %<extra></extra>",
                ),
                row=1, col=1,
            )

        if pd.notna(row['mml_range']) and pd.notna(row['price_range']):
            fig.add_trace(
                go.Scatter(
                    x=[row['mml_range']], y=[row['price_range']],
                    mode=MARKERS_TEXT_MODE, marker=common_marker,
                    text=[row['ticker']], textposition='middle center', textfont=common_text,
                    showlegend=False,
                    hovertemplate=hover_base + f"MML Range: {row['mml_range']:.0f} %<extra></extra>",
                ),
                row=1, col=2,
            )


@app.callback(
    Output('obos-concentration-graph', 'figure'),
    [Input(DATE_PICKER_ID, 'start_date'),
     Input(DATE_PICKER_ID, 'end_date')]
)
def update_obos(start_date, end_date):
    report_end   = pd.to_datetime(end_date)
    report_start = pd.to_datetime(start_date)

    rows = []
    for market in df_pivoted[MARKET_NAMES_COL].unique():
        row = _obos_build_market_row(market, report_start, report_end, df_pivoted, df_deferred_prices)
        if row is not None:
            rows.append(row)

    if not rows:
        return go.Figure()

    rdf = pd.DataFrame(rows)
    report_date_str = pd.to_datetime(rdf['report_date'].max()).strftime('%d/%m/%Y')

    fig = make_subplots(
        rows=1, cols=2,
        shared_yaxes=True,
        subplot_titles=(
            'Rolling One-year Range – MM Short Concentration',
            'Rolling One-year Range – MM Long Concentration',
        ),
        horizontal_spacing=0.02,
    )

    _obos_add_chart_shapes(fig)
    _obos_add_scatter_traces(fig, rdf)

    # Legende (Contango / Backwardation / n/a)
    for label, color in [
        ('Contango (2nd < 3rd)',           _OBOS_COLOR_CONTANGO),
        ('Backwardation (2nd > 3rd)',      _OBOS_COLOR_BACKWARDATION),
        ('Kurvenstruktur n/a (kein 3rd)',  _OBOS_COLOR_NA),
    ]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker={"size": 12, "color": color},
            name=label, showlegend=True,
        ))

    fig.update_xaxes(range=[100, 0], showgrid=True, dtick=25, ticksuffix=' %', row=1, col=1)
    fig.update_xaxes(range=[0, 100], showgrid=True, dtick=25, ticksuffix=' %', row=1, col=2)
    fig.update_yaxes(
        range=[0, 100], showgrid=True, dtick=25, ticksuffix=' %',
        title_text='Rolling One-year Range – Price (2nd Nearby)', row=1, col=1,
    )
    fig.update_yaxes(range=[0, 100], showgrid=True, dtick=25, ticksuffix=' %', row=1, col=2)

    fig.update_layout(
        title={
            "text": (
                f'OBOS Concentration Indicator \u2013 {report_date_str}<br>'
                f'<sup>Colour: Blue\u00a0=\u00a0Contango (2nd\u00a0\u2013\u00a03rd Nearby),\u00a0'
                f'Green\u00a0=\u00a0Backwardation (2nd\u00a0\u2013\u00a03rd Nearby)</sup>'
            ),
            "x": 0, "xanchor": 'left', "font": {"size": 14},
        },
        height=620, showlegend=True,
        legend={"x": 1.01, "y": 0.5, "yanchor": 'middle', "font": {"size": 12}},
        margin={"l": 60, "r": 180, "t": 90, "b": 60},
    )

    return fig


# ---------------------------------------------------------------------------
# Shapley-Owen Callback
# ---------------------------------------------------------------------------

_SHAPLEY_GROUP_LABELS = {
    SHAPLEY_COL_PMPU: 'PMPU (Producer/Merchant)',
    SHAPLEY_COL_SD:   'SD (Swap Dealer)',
    SHAPLEY_COL_MM:   'MM (Managed Money)',
    SHAPLEY_COL_OR:   'OR (Other Reportables)',
}
_SHAPLEY_COLORS = {
    SHAPLEY_COL_PMPU: '#e6550d',
    SHAPLEY_COL_SD:   '#3182bd',
    SHAPLEY_COL_MM:   '#31a354',
    SHAPLEY_COL_OR:   '#756bb1',
}


def _filter_shapley_by_date(df_s, start_date, end_date):
    """Filtert einen Shapley-DataFrame auf den angegebenen Datumsbereich."""
    if start_date:
        df_s = df_s[df_s['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        df_s = df_s[df_s['Date'] <= pd.to_datetime(end_date)]
    return df_s


@app.callback(
    [Output('shapley-timeseries-chart', 'figure'),
     Output('shapley-bar-chart',        'figure'),
     Output('shapley-table',            'data'),
     Output('shapley-r2-info',          'children')],
    [Input(MARKET_DROPDOWN_ID,     'value'),
     Input(DATE_PICKER_ID,   'start_date'),
     Input(DATE_PICKER_ID,   'end_date')],
)
def update_shapley(selected_market, start_date, end_date):
    """Aktualisiert alle drei Shapley-Owen-Elemente (Zeitreihe, Balken, Tabelle)."""

    empty_fig = go.Figure()
    empty_fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{
            "text": "Keine Shapley-Daten verfügbar für diesen Markt.",
            "xref": "paper", "yref": "paper", "x": 0.5, "y": 0.5,
            "showarrow": False, "font": {"size": 14, "color": '#888'}
        }],
        height=400,
    )

    if selected_market not in _shapley_results:
        return empty_fig, empty_fig, [], ""

    df_s = _shapley_results[selected_market].copy()
    df_s['Date'] = pd.to_datetime(df_s['Date'])

    # Datumsfilter
    df_s = _filter_shapley_by_date(df_s, start_date, end_date)

    df_s = df_s.dropna(subset=_SHAPLEY_X_COLS, how='all')

    if df_s.empty:
        return empty_fig, empty_fig, [], "Keine Daten im gewählten Zeitraum."

    # ----------------------------------------------------------------
    # 1) Zeitreihen-Chart
    # ----------------------------------------------------------------
    fig_ts = go.Figure()

    for col in _SHAPLEY_X_COLS:
        label = _SHAPLEY_GROUP_LABELS[col]
        color = _SHAPLEY_COLORS[col]
        valid = df_s[['Date', col]].dropna(subset=[col])
        fig_ts.add_trace(go.Scatter(
            x=valid['Date'],
            y=valid[col],
            mode='lines',
            name=label,
            line={"color": color, "width": 2},
            hovertemplate=(
                f'<b>{label}</b><br>'
                'Datum: %{x|%Y-%m-%d}<br>'
                'φ = %{y:.4f}<extra></extra>'
            ),
        ))

    # Nulllinie
    fig_ts.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)

    fig_ts.update_layout(
        title=f'Shapley-Owen Zeitverlauf – {selected_market}  '
              f'(rollend, {_SHAPLEY_WINDOW} Wochen)',
        xaxis={
            "title": 'Datum',
            "showgrid": True, "gridcolor": LIGHTGRAY,
        },
        yaxis={
            "title": 'Shapley-Wert (φ)',
            "showgrid": True, "gridcolor": LIGHTGRAY,
            "zeroline": True, "zerolinecolor": 'gray', "zerolinewidth": 1,
        },
        plot_bgcolor='white',
        legend={"orientation": 'h', "yanchor": 'bottom', "y": 1.02, "xanchor": 'right', "x": 1},
        height=450,
        hovermode='x unified',
    )

    # ----------------------------------------------------------------
    # 2) Balkendiagramm – letzter Datenpunkt im gefilterten Zeitraum
    # ----------------------------------------------------------------
    last_row = df_s.dropna(subset=_SHAPLEY_X_COLS, how='all').iloc[-1]
    last_date = pd.to_datetime(last_row['Date']).strftime('%Y-%m-%d')
    r2_full   = last_row.get('R2_full', np.nan)

    phi_vals  = [last_row.get(c, np.nan) for c in _SHAPLEY_X_COLS]
    labels    = [_SHAPLEY_GROUP_LABELS[c] for c in _SHAPLEY_X_COLS]
    colors_bar = [
        _SHAPLEY_COLORS[c] if (not np.isnan(v) and v >= 0) else '#d62728'
        for c, v in zip(_SHAPLEY_X_COLS, phi_vals)
    ]

    fig_bar = go.Figure(go.Bar(
        x=labels,
        y=phi_vals,
        marker_color=colors_bar,
        text=[f'{v:.4f}' if not np.isnan(v) else 'n/a' for v in phi_vals],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>φ = %{y:.4f}<extra></extra>',
    ))

    fig_bar.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)

    # R²-Linie als Referenz
    if not np.isnan(r2_full):
        fig_bar.add_hline(
            y=r2_full,
            line_dash='dot',
            line_color='#333',
            line_width=1.5,
            annotation_text=f'R² gesamt = {r2_full:.4f}',
            annotation_position='top right',
            annotation_font_size=11,
        )

    fig_bar.update_layout(
        title=f'Shapley-Werte – {selected_market}  (Datum: {last_date})',
        xaxis={"title": 'Händlergruppe'},
        yaxis={
            "title": 'Shapley-Wert (φ)',
            "showgrid": True, "gridcolor": LIGHTGRAY,
            "zeroline": True, "zerolinecolor": 'gray', "zerolinewidth": 1,
        },
        plot_bgcolor='white',
        height=400,
        showlegend=False,
    )

    # ----------------------------------------------------------------
    # 3) Tabelle
    # ----------------------------------------------------------------
    table_rows = []
    for col, phi in zip(_SHAPLEY_X_COLS, phi_vals):
        share_col = f'R2_share_{col}'
        share_val = last_row.get(share_col, np.nan)
        table_rows.append({
            'group': _SHAPLEY_GROUP_LABELS[col],
            'phi':   round(phi,   4) if not np.isnan(phi)   else None,
            'share': round(share_val, 1) if not np.isnan(share_val) else None,
        })

    table_rows.append({
        'group': 'Gesamt (R²)',
        'phi':   round(r2_full, 4) if not np.isnan(r2_full) else None,
        'share': 100.0,
    })

    r2_info = (
        f"Fenster: {_SHAPLEY_WINDOW} Wochen  |  "
        f"Datum: {last_date}  |  "
        f"R² Vollmodell: {r2_full:.4f}" if not np.isnan(r2_full) else ""
    )

    return fig_ts, fig_bar, table_rows, r2_info


# ---------------------------------------------------------------------------
# Decision-Tree-Callback
# ---------------------------------------------------------------------------
@app.callback(
    [
        Output('dt-prediction-text',    'children'),
        Output('dt-tree-image',         'src'),
        Output('dt-eval-info',          'children'),
        Output('dt-confusion-matrix',   'figure'),
        Output('dt-roc-curve',          'figure'),
        Output('dt-pr-curve',           'figure'),
        Output('dt-feature-importance', 'figure'),
    ],
    [Input(MARKET_DROPDOWN_ID, 'value')]
)
def update_decision_tree(selected_market):
    """Rendert alle Decision-Tree-Komponenten für den gewählten Markt."""
    _empty = go.Figure()
    if selected_market not in _dt_results:
        msg = html.P(
            f"Für '{selected_market}' sind keine Preisdaten verfügbar – kein Modell berechnet.",
            style={'color': '#888', 'fontStyle': 'italic'}
        )
        return msg, "", "", _empty, _empty, _empty, _empty

    result    = _dt_results[selected_market]
    pred      = result["prediction"]
    proba     = result["proba"]
    last_date = pd.to_datetime(result["last_date"]).strftime('%d.%m.%Y')
    ev        = result["eval"]

    # ------------------------------------------------------------------
    # Prognose-Alert
    # ------------------------------------------------------------------
    direction  = "steigende" if pred == 1 else "fallende"
    conf_pct   = proba[pred] * 100
    text_color = "#2e7d32" if pred == 1 else "#c62828"

    prediction_card = dbc.Alert(
        [
            html.Span("Prognose: "),
            html.Strong(
                f"Das Entscheidungsbaum-Modell prognostiziert für {selected_market} "
                f"in der nächsten Woche {direction} Preise.",
                style={"color": text_color}
            ),
            html.Span(
                f"  (Modell-Konfidenz: {conf_pct:.1f} %, "
                f"basierend auf CoT-Daten vom {last_date})",
                style={"fontSize": "14px", "color": "#555"}
            ),
        ],
        color="success" if pred == 1 else "danger",
        className="mb-3",
        style={"fontSize": "16px"},
    )

    # ------------------------------------------------------------------
    # Train/Test-Split-Info
    # ------------------------------------------------------------------
    train_start = pd.to_datetime(ev["train_start"]).strftime('%d.%m.%Y')
    train_end   = pd.to_datetime(ev["train_end"]).strftime('%d.%m.%Y')
    test_start  = pd.to_datetime(ev["test_start"]).strftime('%d.%m.%Y')
    test_end    = pd.to_datetime(ev["test_end"]).strftime('%d.%m.%Y')

    eval_info = html.Div([
        dbc.Badge(
            f"Trainingsset: {ev['n_train']} Beobachtungen  ({train_start} – {train_end})",
            color="primary", className="me-3 p-2",
            style={"fontSize": "13px", "fontWeight": "normal"},
        ),
        dbc.Badge(
            f"Testset (Out-of-Sample): {ev['n_test']} Beobachtungen  ({test_start} – {test_end})",
            color="secondary", className="p-2",
            style={"fontSize": "13px", "fontWeight": "normal"},
        ),
    ])

    # ------------------------------------------------------------------
    # Evaluationsdiagramme (Out-of-Sample)
    # ------------------------------------------------------------------
    tree_src = render_tree_image(result)
    cm_fig   = dt_confusion_matrix_figure(result, selected_market)
    roc_fig  = dt_roc_curve_figure(result, selected_market)
    pr_fig   = dt_pr_curve_figure(result, selected_market)
    feat_fig = dt_feature_importance_figure(result, selected_market)

    return prediction_card, tree_src, eval_info, cm_fig, roc_fig, pr_fig, feat_fig


# Open browser automatically
if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run_server(debug=True, port=8051)
