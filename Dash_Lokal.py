import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
from pages.grundlegende import layout as grundlegende_layout
from pages.dry_powder import layout as dry_powder_layout
from pages.positioning_price import layout as positioning_price_layout
from pages.shapley import layout as shapley_layout
from pages.decision_tree import layout as decision_tree_layout
import pandas as pd
from influxdb_client_3 import InfluxDBClient3
import plotly.graph_objs as go
import webbrowser
from threading import Timer
from datetime import datetime as dt, timedelta
import dash_bootstrap_components as dbc
import numpy as np
from src.analysis.shapley_owen import compute_rolling_shapley, prepare_market_for_shapley
from src.analysis.decision_tree import (
    train_decision_tree,
    render_tree_image,
    feature_importance_figure as dt_feature_importance_figure,
)
from src.analysis.market_config import get_price_col, get_contract_size
from src.analysis.cot_indicators import clustering_0_100, rel_concentration, calculate_ranges

# Function to open the web browser
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8051/")

# Connect to InfluxDB v3
host = "http://localhost:8181"  # InfluxDB v3 Core default port
token = "apiv3_m8zHCYoKyZwSHfrt4oPUMMMDCGD4XZMS6KEV2C9SMchecjhVig4y_27rcHE58uiSSqCjBJby95dsaSNtMYnscA"
database = "CoT-Data"

print("Connecting to InfluxDB v3...")
client = InfluxDBClient3(host=host, token=token, database=database)

# Define SQL query to fetch data (v3 Core uses SQL instead of Flux)
query = """
SELECT *
FROM cot_data
WHERE time >= now() - INTERVAL '4 years'
"""

print("Fetching data from InfluxDB v3...")
# Execute query - v3 returns data as PyArrow Table, convert to pandas DataFrame
table = client.query(query=query, language="sql")

# Convert PyArrow Table to pandas DataFrame
df_pivoted = table.to_pandas()

print(f"Fetched {len(df_pivoted)} rows from InfluxDB v3")

# Fetch futures prices for PPCI (stored by the pipeline in futures_prices measurement)
query_futures = """
SELECT *
FROM futures_prices
WHERE time >= now() - INTERVAL '4 years'
"""
print("Fetching futures prices from InfluxDB v3...")
try:
    table_futures = client.query(query=query_futures, language="sql")
    df_futures_prices = table_futures.to_pandas()
    df_futures_prices.rename(columns={'time': 'Date'}, inplace=True)
    df_futures_prices['Date'] = pd.to_datetime(df_futures_prices['Date']).dt.tz_localize(None)
    df_futures_prices = df_futures_prices.sort_values('Date').reset_index(drop=True)
    print(f"[PPCI] Loaded {len(df_futures_prices)} futures price rows")
except Exception as _e:
    print(f"[PPCI] Could not load futures prices: {_e}")
    df_futures_prices = pd.DataFrame(columns=['Date'])

# Fetch FRED macro data (VIX, USD Index etc.) – stored by pipeline in macro_by_date
query_macro = """
SELECT *
FROM macro_by_date
WHERE time >= now() - INTERVAL '2 years'
"""
print("Fetching macro data (FRED) from InfluxDB v3...")
try:
    table_macro = client.query(query=query_macro, language="sql")
    df_macro = table_macro.to_pandas()
    df_macro.rename(columns={'time': 'Date'}, inplace=True)
    df_macro['Date'] = pd.to_datetime(df_macro['Date']).dt.tz_localize(None)
    df_macro = df_macro.sort_values('Date').reset_index(drop=True)
    print(f"[FRED] Loaded {len(df_macro)} macro rows")
except Exception as _e:
    print(f"[FRED] Could not load macro data: {_e}")
    df_macro = pd.DataFrame(columns=['Date'])

# Fill macro gaps: fetch 4 years from yfinance as base, InfluxDB values take precedence
_MACRO_FALLBACK = {
    "vix":       "^VIX",
    "usd_index": "DX-Y.NYB",
    "usd_chf":   "CHF=X",
}
try:
    import yfinance as yf
    from datetime import date as _date
    _fb_start = _date.today().replace(year=_date.today().year - 4)
    for _col, _ticker in _MACRO_FALLBACK.items():
        _raw = yf.download(_ticker, start=_fb_start.isoformat(), progress=False, auto_adjust=True)
        if _raw.empty:
            print(f"[Macro fallback] No data returned for {_col} ({_ticker})")
            continue
        if isinstance(_raw.columns, pd.MultiIndex):
            _cc = next((c for c in _raw.columns if c[0] == "Close"), None)
            _series = _raw[_cc] if _cc else None
        else:
            _series = _raw["Close"]
        if _series is None:
            continue
        _fb = _series.reset_index()
        _fb.columns = ["Date", _col]
        _fb["Date"] = pd.to_datetime(_fb["Date"]).dt.tz_localize(None)
        if df_macro.empty or 'Date' not in df_macro.columns:
            df_macro = _fb
        elif _col in df_macro.columns:
            # Merge yfinance (4yr base) with InfluxDB; InfluxDB values take precedence
            _tmp = pd.merge(_fb, df_macro[['Date', _col]].rename(columns={_col: f'{_col}_db'}),
                            on="Date", how="outer")
            _tmp[_col] = _tmp[f'{_col}_db'].combine_first(_tmp[_col])
            _tmp.drop(columns=[f'{_col}_db'], inplace=True)
            df_macro = pd.merge(df_macro.drop(columns=[_col]), _tmp[['Date', _col]],
                                on="Date", how="outer").sort_values("Date").reset_index(drop=True)
        else:
            df_macro = pd.merge(df_macro, _fb, on="Date", how="outer").sort_values("Date").reset_index(drop=True)
        print(f"[Macro fallback] Loaded {len(_fb)} rows for {_col} from yfinance")
except Exception as _fb_e:
    print(f"[Macro fallback] Error: {_fb_e}")

# Close the client
client.close()

# Rename columns for convenience
# v3 uses 'time' instead of '_time', data is already pivoted
df_pivoted.rename(columns={'time': 'Date', 'market_names': 'Market Names'}, inplace=True)

# Berechnung der Spalte 'Total Number of Traders'
df_pivoted = df_pivoted.sort_values(['Market Names', 'Date'])

# 1) Total Traders (TTF)
TOTAL_TRADERS_COL = 'Total Traders'
df_pivoted['Total Number of Traders'] = df_pivoted[TOTAL_TRADERS_COL]

# 2) Anteil Trader in Gruppe (nicht Open Interest!)
df_pivoted['MM_Long_share']  = df_pivoted['Traders M Money Long']  / df_pivoted['Total Number of Traders']
df_pivoted['MM_Short_share'] = df_pivoted['Traders M Money Short'] / df_pivoted['Total Number of Traders']

# 3) 1 Jahr = ~52 Wochen, und pro Markt (keine Markt-Mischung)
df_pivoted['Long Clustering'] = (
    df_pivoted.groupby('Market Names')['MM_Long_share']
    .transform(lambda s: clustering_0_100(s, window=52))
)

df_pivoted['Short Clustering'] = (
    df_pivoted.groupby('Market Names')['MM_Short_share']
    .transform(lambda s: clustering_0_100(s, window=52))
)

df_pivoted['Rolling Min'] = df_pivoted['Producer/Merchant/Processor/User Long'].rolling(365, min_periods=1).min()
df_pivoted['Rolling Max'] = df_pivoted['Producer/Merchant/Processor/User Long'].rolling(365, min_periods=1).max()

# Define size categories for traders
df_pivoted['Trader Size'] = pd.cut(
    df_pivoted['Total Number of Traders'],
    bins=[0, 50, 100, 150],
    labels=['≤ 50 Traders', '51–100 Traders', '101–150 Traders']
)

print(df_pivoted.columns)  # Zeigt alle Spalten in df_pivoted
print(df_pivoted.head())   # Zeigt die ersten Zeilen


# Additional calculations for the new graphs
df_pivoted['Total Long Traders'] = df_pivoted[['Traders Prod/Merc Short', 'Traders Swap Long', 'Traders M Money Long']].sum(axis=1)
df_pivoted['Total Short Traders'] = df_pivoted[['Traders Prod/Merc Short', 'Traders Swap Short', 'Traders M Money Short']].sum(axis=1)
df_pivoted['Long Position Size'] = df_pivoted['Producer/Merchant/Processor/User Long']
df_pivoted['Short Position Size'] = df_pivoted['Producer/Merchant/Processor/User Short']
df_pivoted['MML Position Size'] = (
    df_pivoted['Managed Money Long'] / df_pivoted['Traders M Money Long']
).replace([np.inf, -np.inf], np.nan)
df_pivoted['MMS Position Size'] = (
    df_pivoted['Managed Money Short'] / df_pivoted['Traders M Money Short']
).replace([np.inf, -np.inf], np.nan)

df_pivoted['Net Short Position Size'] = (
    df_pivoted['Short Position Size'] - df_pivoted['Long Position Size']
)
df_pivoted['PMPUL Position Size'] = (
    df_pivoted['Producer/Merchant/Processor/User Long'] / df_pivoted['Traders Prod/Merc Long']
).replace([np.inf, -np.inf], np.nan)

df_pivoted['PMPUS Position Size'] = (
    df_pivoted['Producer/Merchant/Processor/User Short'] / df_pivoted['Traders Prod/Merc Short']
).replace([np.inf, -np.inf], np.nan)
df_pivoted['SDL Position Size'] = (
    df_pivoted['Swap Dealer Long'] / df_pivoted['Traders Swap Long']
).replace([np.inf, -np.inf], np.nan)

df_pivoted['SDS Position Size'] = (
    df_pivoted['Swap Dealer Short'] / df_pivoted['Traders Swap Short']
).replace([np.inf, -np.inf], np.nan)
df_pivoted['ORL Position Size'] = (
    df_pivoted['Other Reportables Long'] / df_pivoted['Traders Other Rept Long']
).replace([np.inf, -np.inf], np.nan)

df_pivoted['ORS Position Size'] = (
    df_pivoted['Other Reportables Short'] / df_pivoted['Traders Other Rept Short']
).replace([np.inf, -np.inf], np.nan)

df_pivoted['MML Long OI'] = df_pivoted['Managed Money Long']
df_pivoted['MML Short OI'] = -df_pivoted['Managed Money Short']
df_pivoted['MMS Long OI'] = df_pivoted['Managed Money Long']
df_pivoted['MMS Short OI'] = -df_pivoted['Managed Money Short']
df_pivoted['MML Traders'] = df_pivoted['Traders M Money Long']
df_pivoted['MMS Traders'] = df_pivoted['Traders M Money Short']

max_bubble_size = 100
max_oi = max(df_pivoted['MML Long OI'].max(), abs(df_pivoted['MML Short OI'].max()))
max_oi = max(df_pivoted['MMS Short OI'].max(), abs(df_pivoted['MML Short OI'].max()))

sizeref = 2. * max_oi / (max_bubble_size**3.2)

# Calculate relative concentration for each trader group
df_pivoted['PMPUL Relative Concentration'] = df_pivoted['Producer/Merchant/Processor/User Long'] - df_pivoted['Producer/Merchant/Processor/User Short']
df_pivoted['PMPUS Relative Concentration'] = df_pivoted['Producer/Merchant/Processor/User Short'] - df_pivoted['Producer/Merchant/Processor/User Long']
df_pivoted['SDL Relative Concentration'] = df_pivoted['Swap Dealer Long'] - df_pivoted['Swap Dealer Short']
df_pivoted['SDS Relative Concentration'] = df_pivoted['Swap Dealer Short'] - df_pivoted['Swap Dealer Long']
df_pivoted['MML Relative Concentration'] = df_pivoted['Managed Money Long'] - df_pivoted['Managed Money Short']
df_pivoted['MMS Relative Concentration'] = df_pivoted['Managed Money Short'] - df_pivoted['Managed Money Long']
df_pivoted['ORL Relative Concentration'] = df_pivoted['Other Reportables Long'] - df_pivoted['Other Reportables Short']
df_pivoted['ORS Relative Concentration'] = df_pivoted['Other Reportables Short'] - df_pivoted['Other Reportables Long']

# Aliase für Shapley-Owen: lesbare Kurzbezeichnungen der Netto-Positionierungen
df_pivoted['PMPU Net'] = df_pivoted['PMPUL Relative Concentration']
df_pivoted['SD Net']   = df_pivoted['SDL Relative Concentration']
df_pivoted['MM Net']   = df_pivoted['MML Relative Concentration']
df_pivoted['OR Net']   = df_pivoted['ORL Relative Concentration']

# Columns for the number of traders for each group
df_pivoted['PMPUL Traders'] = df_pivoted['Traders Prod/Merc Long']
df_pivoted['PMPUS Traders'] = df_pivoted['Traders Prod/Merc Short']
df_pivoted['SDL Traders'] = df_pivoted['Traders Swap Long']
df_pivoted['SDS Traders'] = df_pivoted['Traders Swap Short']
df_pivoted['MML Traders'] = df_pivoted['Traders M Money Long']
df_pivoted['MMS Traders'] = df_pivoted['Traders M Money Short']
df_pivoted['ORL Traders'] = df_pivoted['Traders Other Rept Long']
df_pivoted['ORS Traders'] = df_pivoted['Traders Other Rept Short']

# Determine the quarter for each date
df_pivoted['Quarter'] = df_pivoted['Date'].dt.quarter.map({1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'})

# Calculate a global sizeref to ensure consistency across markets
max_bubble_size = 100  # Adjusted for better visualization
max_oi = max(df_pivoted[['PMPUL Relative Concentration', 'PMPUS Relative Concentration', 
                         'SDL Relative Concentration', 'SDS Relative Concentration', 
                         'MML Relative Concentration', 'MMS Relative Concentration', 
                         'ORL Relative Concentration', 'ORS Relative Concentration']].max().max(),
             abs(df_pivoted[['PMPUL R'
                             'elative Concentration', 'PMPUS Relative Concentration',
                             'SDL Relative Concentration', 'SDS Relative Concentration', 
                             'MML Relative Concentration', 'MMS Relative Concentration', 
                             'ORL Relative Concentration', 'ORS Relative Concentration']].min().min()))
sizeref = 2. * max_oi / (max_bubble_size**2.5)

min_bubble_size = 10  # Set minimum bubble size

# Add Year column for color coding
df_pivoted['Year'] = df_pivoted['Date'].dt.year

# Calculate Net OI for Managed Money (MM)
df_pivoted['MM Net OI'] = df_pivoted['Managed Money Long'] - df_pivoted['Managed Money Short']

# Calculate Net Number of Traders for MM
df_pivoted['MM Net Traders'] = df_pivoted['Traders M Money Long'] - df_pivoted['Traders M Money Short']

# Define the default end date (most recent date)
default_end_date = df_pivoted['Date'].max()

# Define the default start date (6 months prior to the end date)
default_start_date = default_end_date - timedelta(days=182)

# ---------------------------------------------------------------------------
# PPCI – Positioning Price Concentration Indicator
# Markt-Konfiguration und Lookup-Funktionen: siehe src/analysis/market_config.py
# Lokale Aliase für Rückwärtskompatibilität innerhalb dieser Datei.
# ---------------------------------------------------------------------------
_ppci_get_price_col    = get_price_col
_ppci_get_contract_size = get_contract_size


def get_global_xaxis():
    return dict(
        tickmode='array',
        tickvals=df_pivoted['Date'].dt.year.unique(),
        ticktext=[str(year) for year in df_pivoted['Date'].dt.year.unique()],
        showgrid=True,
        ticks="outside",
        tickangle=45
    )

global_xaxis = dict(
    tickmode='array',
    tickvals=df_pivoted['Date'].dt.year.unique(),  # Unique years
    ticktext=[str(year) for year in df_pivoted['Date'].dt.year.unique()],  # Format as strings
    showgrid=True,
    ticks="outside",
    tickangle=45  # Rotate for better visibility
)

def add_last_point_highlight(fig, df, x_col, y_col, inner_size=10, outer_line_width=4, outer_color='red', inner_color='black'):
    if not df.empty:  # Sicherstellen, dass die Daten nicht leer sind
        last_point = df.iloc[-1]

        # Innerer Punkt mit rotem Rand
        fig.add_trace(go.Scatter(
            x=[last_point[x_col]],
            y=[last_point[y_col]],
            mode='markers',
            marker=dict(
                size=inner_size,  # Größe des inneren Punkts
                color=inner_color,  # Farbe des inneren Punkts
                opacity=1.0,
                line=dict(
                    width=outer_line_width,  # Breite des äußeren Rands
                    color=outer_color  # Farbe des äußeren Rands
                )
            ),
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
    median_oi = df['MM Net OI'].median()
    median_traders = df['MM Net Traders'].median()
    return median_oi, median_traders

# Function to calculate the scaling factors for long and short positions
def calculate_scaling_factors(df):
    max_long_position_size = df['Long Position Size'].max()
    max_short_position_size = df['Short Position Size'].max()
    long_scaling_factor = max_long_position_size / 50  # Adjust divisor as needed
    short_scaling_factor = max_short_position_size / 50  # Adjust divisor as needed
    return long_scaling_factor, short_scaling_factor

def _indicator_cols(indicator: str) -> tuple[str, str]:
    """Gibt (concentration_col, clustering_col) für 'MML' oder 'MMS' zurück."""
    if indicator == 'MML':
        return 'MML Relative Concentration', 'Long Clustering'
    elif indicator == 'MMS':
        return 'MMS Relative Concentration', 'Short Clustering'
    raise ValueError("Invalid indicator. Must be 'MML' or 'MMS'.")

def nz(series):
    return pd.to_numeric(series, errors='coerce')

def scaled_diameters(vals, min_px=6, max_px=26, lo=None, hi=None, log_scale=False):
    """Mappe Werte auf Pixeldurchmesser [min_px, max_px].

    Parameters
    ----------
    vals      : Werte (Series, ndarray, list, scalar)
    min_px    : kleinster Durchmesser in Pixel
    max_px    : größter  Durchmesser in Pixel
    lo, hi    : explizite Referenz-Grenzen (None → aus vals berechnen).
                Für die Legende MUSS derselbe lo/hi wie für den Scatter
                übergeben werden, damit Legende und Punkte konsistent sind.
    log_scale : True → log1p-Transformation vor der Interpolation
                (empfohlen für stark rechts-schiefe Daten wie Open Interest).
    """
    # In ein float-Array konvertieren (verträglich mit Series/ndarray/list/scalar)
    v = np.asarray(vals, dtype=float)

    # Nicht-finite durch 0 ersetzen
    v = np.where(np.isfinite(v), v, 0.0)

    if v.size == 0:
        return np.array([], dtype=float)

    _lo = float(lo) if lo is not None else float(np.nanmin(v))
    _hi = float(hi) if hi is not None else float(np.nanmax(v))

    # Falls alle Werte gleich (oder leer), mittlere Größe verwenden
    if not np.isfinite(_lo) or not np.isfinite(_hi) or _hi <= _lo:
        return np.full_like(v, (min_px + max_px) / 2.0, dtype=float)

    if log_scale:
        v_t  = np.log1p(np.maximum(v, 0.0))
        lo_t = np.log1p(max(_lo, 0.0))
        hi_t = np.log1p(_hi)
    else:
        v_t, lo_t, hi_t = v, _lo, _hi

    return np.interp(v_t, (lo_t, hi_t), (min_px, max_px))

def scaled_diameters_rank(vals, min_px=6, max_px=45, gamma=0.8):

    s = pd.to_numeric(pd.Series(vals), errors='coerce').fillna(0).clip(lower=0)

    # alles gleich / keine Variation -> konstante Größe
    if s.nunique(dropna=False) <= 1:
        return np.full(len(s), (min_px + max_px) / 2.0, dtype=float)

    # Rang/Perzentil (0..1)
    p = s.rank(pct=True, method='average').to_numpy(dtype=float)

    # in Pixel mappen
    return (min_px + (p ** gamma) * (max_px - min_px)).astype(float)

# Example calculation
median_oi, median_traders = calculate_medians(df_pivoted)

# ---------------------------------------------------------------------------
# Shapley-Owen: Rollende Zerlegung des R² für alle Märkte vorberechnen
# ---------------------------------------------------------------------------
_SHAPLEY_X_COLS      = ['Δ PMPU Net', 'Δ SD Net', 'Δ MM Net', 'Δ OR Net']
_SHAPLEY_Y_COL       = '_price_change'
_SHAPLEY_WINDOW      = 52
_SHAPLEY_MIN_PERIODS = 26

_shapley_results: dict = {}   # market_name → DataFrame (Shapley-Resultate)

for _mkt in df_pivoted['Market Names'].unique():
    _pcol = get_price_col(_mkt)
    if _pcol is None or df_futures_prices.empty or _pcol not in df_futures_prices.columns:
        print(f"[Shapley] Kein Preisdaten für {_mkt} – überspringe.")
        continue

    _dff = df_pivoted[df_pivoted['Market Names'] == _mkt].copy()
    _dff = prepare_market_for_shapley(_dff, df_futures_prices, _pcol)
    if _dff is None:
        print(f"[Shapley] {_mkt}: Keine Preisdaten nach Merge – überspringe.")
        continue

    _result = compute_rolling_shapley(
        _dff,
        x_cols=_SHAPLEY_X_COLS,
        y_col=_SHAPLEY_Y_COL,
        window=_SHAPLEY_WINDOW,
        min_periods=_SHAPLEY_MIN_PERIODS,
    )
    _shapley_results[_mkt] = _result
    print(f"[Shapley] {_mkt}: {len(_result)} Datenpunkte berechnet.")

# ---------------------------------------------------------------------------
# Decision Tree: vorberechnen für alle Märkte mit Preisdaten
# ---------------------------------------------------------------------------
_dt_results: dict = {}   # market_name → dict (Modell + Prognose)

for _mkt in df_pivoted['Market Names'].unique():
    _pcol = get_price_col(_mkt)
    if _pcol is None or df_futures_prices.empty or _pcol not in df_futures_prices.columns:
        print(f"[DecisionTree] Keine Preisdaten für {_mkt} – überspringe.")
        continue

    _dff = df_pivoted[df_pivoted['Market Names'] == _mkt].copy()
    _result = train_decision_tree(_dff, df_futures_prices, _pcol)
    if _result is not None:
        _dt_results[_mkt] = _result
        _dir = "steigend" if _result["prediction"] == 1 else "fallend"
        print(f"[DecisionTree] {_mkt}: Prognose {_dir} ({_result['n_samples']} Beobachtungen)")
    else:
        print(f"[DecisionTree] {_mkt}: zu wenige Daten – überspringe.")

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
                    id='market-dropdown',
                    options=[{'label': market, 'value': market} for market in df_pivoted['Market Names'].unique()],
                    value='Palladium',
                    clearable=False,
                    style={'width': '100%'}
                ),
            ], width=12, lg=4),
            dbc.Col([
                html.Label("Zeitraum", className="fw-semibold mb-1 d-block"),
                dcc.DatePickerRange(
                    id='date-picker-range',
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
    Output('overview-table', 'data'),
    [
        Input('market-dropdown', 'value'),
        Input('date-picker-range', 'start_date'),
        Input('date-picker-range', 'end_date')
    ]
)
def update_table(selected_market, start_date, end_date):
    filtered_df = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ]

    if filtered_df.empty:
        return []

    first_row = filtered_df.iloc[0]
    current_row = filtered_df.iloc[-1]

    def safe_pct_change(curr, first):
        # verhindert Division durch 0 / NaN
        if pd.isna(first) or float(first) == 0:
            return 0
        return round(((float(curr) - float(first)) / float(first)) * 100, 2)

    data = {
        'Trader Group': [
            'Producer/Merchant/Processor/User',
            'Swap Dealer',
            'Managed Money',
            'Other Reportables'
        ],
        'Positions': [
            positions_bar(
                first_row['Producer/Merchant/Processor/User Long'],
                first_row['Producer/Merchant/Processor/User Short'],
                None
            ),
            positions_bar(
                first_row['Swap Dealer Long'],
                first_row['Swap Dealer Short'],
                first_row['Swap Dealer Spread']
            ),
            positions_bar(
                first_row['Managed Money Long'],
                first_row['Managed Money Short'],
                first_row['Managed Money Spread']
            ),
            positions_bar(
                first_row['Other Reportables Long'],
                first_row['Other Reportables Short'],
                first_row['Other Reportables Spread']
            ),
        ],

        'Difference (Long %)': [
            safe_pct_change(current_row['Producer/Merchant/Processor/User Long'], first_row['Producer/Merchant/Processor/User Long']),
            safe_pct_change(current_row['Swap Dealer Long'], first_row['Swap Dealer Long']),
            safe_pct_change(current_row['Managed Money Long'], first_row['Managed Money Long']),
            safe_pct_change(current_row['Other Reportables Long'], first_row['Other Reportables Long'])
        ],
        'Difference (Short %)': [
            safe_pct_change(current_row['Producer/Merchant/Processor/User Short'], first_row['Producer/Merchant/Processor/User Short']),
            safe_pct_change(current_row['Swap Dealer Short'], first_row['Swap Dealer Short']),
            safe_pct_change(current_row['Managed Money Short'], first_row['Managed Money Short']),
            safe_pct_change(current_row['Other Reportables Short'], first_row['Other Reportables Short'])
        ],
        'Difference (Spread %)': [
            0,  # PMPU hat bei dir keinen Spread
            safe_pct_change(current_row['Swap Dealer Spread'], first_row['Swap Dealer Spread']),
            safe_pct_change(current_row['Managed Money Spread'], first_row['Managed Money Spread']),
            safe_pct_change(current_row['Other Reportables Spread'], first_row['Other Reportables Spread'])
        ],

        'Total Traders': [
            current_row['Traders Prod/Merc Long'] + current_row['Traders Prod/Merc Short'],
            current_row['Traders Swap Long'] + current_row['Traders Swap Short'] + current_row['Traders Swap Spread'],
            current_row['Traders M Money Long'] + current_row['Traders M Money Short'] + current_row['Traders M Money Spread'],
            current_row['Traders Other Rept Long'] + current_row['Traders Other Rept Short'] + current_row['Traders Other Rept Spread']
        ],
        '% of Traders': [
            f"Long: {round(current_row['Traders Prod/Merc Long'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Short: {round(current_row['Traders Prod/Merc Short'] / current_row['Total Number of Traders'] * 100, 2)}%",

            f"Long: {round(current_row['Traders Swap Long'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Short: {round(current_row['Traders Swap Short'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Spread: {round(current_row['Traders Swap Spread'] / current_row['Total Number of Traders'] * 100, 2)}%",

            f"Long: {round(current_row['Traders M Money Long'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Short: {round(current_row['Traders M Money Short'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Spread: {round(current_row['Traders M Money Spread'] / current_row['Total Number of Traders'] * 100, 2)}%",

            f"Long: {round(current_row['Traders Other Rept Long'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Short: {round(current_row['Traders Other Rept Short'] / current_row['Total Number of Traders'] * 100, 2)}%, "
            f"Spread: {round(current_row['Traders Other Rept Spread'] / current_row['Total Number of Traders'] * 100, 2)}%"
        ],

        'Number of Traders': [
            traders_bar(current_row['Traders Prod/Merc Long'],  current_row['Traders Prod/Merc Short'],  None),
            traders_bar(current_row['Traders Swap Long'],       current_row['Traders Swap Short'],       current_row['Traders Swap Spread']),
            traders_bar(current_row['Traders M Money Long'],    current_row['Traders M Money Short'],    current_row['Traders M Money Spread']),
            traders_bar(current_row['Traders Other Rept Long'], current_row['Traders Other Rept Short'], current_row['Traders Other Rept Spread'])
        ],
    }

    return pd.DataFrame(data).to_dict('records')

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
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('mm-radio', 'value'),
     Input('trader-group-radio', 'value')]
)

def update_graphs(selected_market, start_date, end_date, mm_type, trader_group):
    filtered_df = df_pivoted[(df_pivoted['Market Names'] == selected_market) &
                             (df_pivoted['Date'] >= start_date) & 
                             (df_pivoted['Date'] <= end_date)]

    # PMPU Long Position Size Indicator
    pmpu_long_position_size_fig = go.Figure()

    # Daten vorbereiten
    tr_long_raw = pd.to_numeric(filtered_df['Traders Prod/Merc Long'], errors='coerce')
    tr_long = tr_long_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Long)
    try:
        col_long = safe_colors(filtered_df['PMPUL Position Size'])
    except Exception:
        col_long = pd.to_numeric(filtered_df['PMPUL Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen (z.B. 6–26 px)
    _pmpu_l_pos = tr_long[tr_long > 0]
    pmpu_l_lo = float(_pmpu_l_pos.min()) if _pmpu_l_pos.size > 0 else 1.0
    pmpu_l_hi = float(tr_long.max()) if tr_long.max() > 0 else 1.0
    sizes_long = scaled_diameters(tr_long, min_px=6, max_px=26, lo=pmpu_l_lo, hi=pmpu_l_hi)

    # 3) Punkte plotten
    pmpu_long_position_size_fig.add_trace(
        go.Scatter(
            x=filtered_df['Date'],
            y=filtered_df['Open Interest'],
            mode='markers',
            marker=dict(
                size=sizes_long,
                sizemode='diameter',
                sizeref=1,
                color=col_long,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="PMPU Long Position Size",
                    thickness=15, len=0.75, yanchor='middle', y=0.5
                )
            ),
            text=[
                f"Date: {d:%Y-%m-%d}<br>"
                f"Open Interest: {int(oi):,}<br>"
                f"Traders (Long): {int(t)}<br>"
                f"PosSize (avg): {float(ps):,.0f}"
                for d, oi, t, ps in zip(
                    filtered_df['Date'],
                    pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                    tr_long,
                    pd.to_numeric(filtered_df['PMPUL Position Size'], errors='coerce').fillna(0)
                )
            ],
            hoverinfo='text',
            showlegend=False
        )
    )

    # 4) Bubble-Size-Legende
    base = tr_long[tr_long > 0]
    if base.size >= 3 and base.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        pmpu_long_position_size_fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
                showlegend=True,
                name=f"{int(v)} Traders",
                hoverinfo='skip'
            )
        )

    # 5) Layout
    pmpu_long_position_size_fig.update_layout(
        title='Long Position Size Indicator (PMPU)',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(showgrid=True, ticks="outside", tickangle=45),
        yaxis=dict(title='Open Interest', showgrid=True),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.18, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(
            fig=pmpu_long_position_size_fig,
            df=filtered_df, x_col='Date', y_col='Open Interest',
            inner_size=2, inner_color='black'
        )
    except Exception:
        pass

    # PMPU Short Position Size Indicator
    pmpu_short_position_size_fig = go.Figure()

    # 1) Daten vorbereiten
    tr_short_raw = pd.to_numeric(filtered_df['Traders Prod/Merc Short'], errors='coerce')
    tr_short = tr_short_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Short)
    try:
        col_short = safe_colors(filtered_df['PMPUS Position Size'])
    except Exception:
        col_short = pd.to_numeric(filtered_df['PMPUS Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen
    _pmpu_s_pos = tr_short[tr_short > 0]
    pmpu_s_lo = float(_pmpu_s_pos.min()) if _pmpu_s_pos.size > 0 else 1.0
    pmpu_s_hi = float(tr_short.max()) if tr_short.max() > 0 else 1.0
    sizes_short = scaled_diameters(tr_short, min_px=6, max_px=26, lo=pmpu_s_lo, hi=pmpu_s_hi)

    # 3) Punkte plotten
    pmpu_short_position_size_fig.add_trace(
        go.Scatter(
            x=filtered_df['Date'],
            y=filtered_df['Open Interest'],
            mode='markers',
            marker=dict(
                size=sizes_short,
                sizemode='diameter',
                sizeref=1,
                color=col_short,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="PMPU Short Position Size",
                    thickness=15, len=0.75, yanchor='middle', y=0.5
                )
            ),
            text=[
                f"Date: {d:%Y-%m-%d}<br>"
                f"Open Interest: {int(oi):,}<br>"
                f"Traders (Short): {int(t)}<br>"
                f"PosSize (avg): {float(ps):,.0f}"
                for d, oi, t, ps in zip(
                    filtered_df['Date'],
                    pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                    tr_short,
                    pd.to_numeric(filtered_df['PMPUS Position Size'], errors='coerce').fillna(0)
                )
            ],
            hoverinfo='text',
            showlegend=False
        )
    )

    # 4) Bubble-Size-Legende
    base_s = tr_short[tr_short > 0]
    if base_s.size >= 3 and base_s.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base_s, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        pmpu_short_position_size_fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
                showlegend=True,
                name=f"{int(v)} Traders",
                hoverinfo='skip'
            )
        )

    # 5) Layout
    pmpu_short_position_size_fig.update_layout(
        title='Short Position Size Indicator (PMPU)',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(showgrid=True, ticks="outside", tickangle=45),
        yaxis=dict(title='Open Interest', showgrid=True),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.18, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(
            fig=pmpu_short_position_size_fig,
            df=filtered_df, x_col='Date', y_col='Open Interest',
            inner_size=2, inner_color='black'
        )
    except Exception:
        pass

    sd_long_position_size_fig = go.Figure()

    # 1) Daten vorbereiten
    sd_tr_long_raw = pd.to_numeric(filtered_df['Traders Swap Long'], errors='coerce')
    sd_tr_long = sd_tr_long_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Long)
    try:
        sd_col_long = safe_colors(filtered_df['SDL Position Size'])
    except Exception:
        sd_col_long = pd.to_numeric(filtered_df['SDL Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen
    _sd_l_pos = sd_tr_long[sd_tr_long > 0]
    sd_l_lo = float(_sd_l_pos.min()) if _sd_l_pos.size > 0 else 1.0
    sd_l_hi = float(sd_tr_long.max()) if sd_tr_long.max() > 0 else 1.0
    sd_sizes_long = scaled_diameters(sd_tr_long, min_px=6, max_px=26, lo=sd_l_lo, hi=sd_l_hi)

    # 3) Punkte plotten
    sd_long_position_size_fig.add_trace(
        go.Scatter(
            x=filtered_df['Date'],
            y=filtered_df['Open Interest'],
            mode='markers',
            marker=dict(
                size=sd_sizes_long,
                sizemode='diameter',
                sizeref=1,
                color=sd_col_long,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="SD Long Position Size",
                    thickness=15, len=0.75, yanchor='middle', y=0.5
                )
            ),
            text=[
                f"Date: {d:%Y-%m-%d}<br>"
                f"Open Interest: {int(oi):,}<br>"
                f"Traders (Long): {int(t)}<br>"
                f"PosSize (avg): {float(ps):,.0f}"
                for d, oi, t, ps in zip(
                    filtered_df['Date'],
                    pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                    sd_tr_long,
                    pd.to_numeric(filtered_df['SDL Position Size'], errors='coerce').fillna(0)
                )
            ],
            hoverinfo='text',
            showlegend=False
        )
    )

    # 4) Bubble-Size-Legende (gleiche Skalierung wie oben)
    sd_baseL = sd_tr_long[sd_tr_long > 0]
    if sd_baseL.size >= 3 and sd_baseL.max() > 1:
        sd_legend_valsL = np.unique(np.round(np.quantile(sd_baseL, [0.25, 0.5, 0.75, 1.0])).astype(int))
        sd_legend_valsL = sd_legend_valsL[sd_legend_valsL > 0]
    else:
        sd_legend_valsL = np.array([10, 20, 35], dtype=int)

    sd_legend_sizesL = np.linspace(7, 20, len(sd_legend_valsL)) if len(sd_legend_valsL) > 1 else np.array([13.0])
    for v, s in zip(sd_legend_valsL, sd_legend_sizesL):
        sd_long_position_size_fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
                showlegend=True,
                name=f"{int(v)} Traders",
                hoverinfo='skip'
            )
        )

    # 5) Layout
    sd_long_position_size_fig.update_layout(
        title='Long Position Size Indicator (Swap Dealers)',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(showgrid=True, ticks="outside", tickangle=45),
        yaxis=dict(title='Open Interest', showgrid=True),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.18, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(
            fig=sd_long_position_size_fig,
            df=filtered_df, x_col='Date', y_col='Open Interest',
            inner_size=2, inner_color='black'
        )
    except Exception:
        pass

    # SD Short Position Size Indicator
    sd_short_position_size_fig = go.Figure()

    # 1) Daten vorbereiten
    sd_tr_short_raw = pd.to_numeric(filtered_df['Traders Swap Short'], errors='coerce')
    sd_tr_short = sd_tr_short_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Short)
    try:
        sd_col_short = safe_colors(filtered_df['SDS Position Size'])
    except Exception:
        sd_col_short = pd.to_numeric(filtered_df['SDS Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen
    _sd_s_pos = sd_tr_short[sd_tr_short > 0]
    sd_s_lo = float(_sd_s_pos.min()) if _sd_s_pos.size > 0 else 1.0
    sd_s_hi = float(sd_tr_short.max()) if sd_tr_short.max() > 0 else 1.0
    sd_sizes_short = scaled_diameters(sd_tr_short, min_px=6, max_px=26, lo=sd_s_lo, hi=sd_s_hi)

    # 3) Punkte plotten
    sd_short_position_size_fig.add_trace(
        go.Scatter(
            x=filtered_df['Date'],
            y=filtered_df['Open Interest'],
            mode='markers',
            marker=dict(
                size=sd_sizes_short,
                sizemode='diameter',
                sizeref=1,
                color=sd_col_short,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="SD Short Position Size",
                    thickness=15, len=0.75, yanchor='middle', y=0.5
                )
            ),
            text=[
                f"Date: {d:%Y-%m-%d}<br>"
                f"Open Interest: {int(oi):,}<br>"
                f"Traders (Short): {int(t)}<br>"
                f"PosSize (avg): {float(ps):,.0f}"
                for d, oi, t, ps in zip(
                    filtered_df['Date'],
                    pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                    sd_tr_short,
                    pd.to_numeric(filtered_df['SDS Position Size'], errors='coerce').fillna(0)
                )
            ],
            hoverinfo='text',
            showlegend=False
        )
    )

    # 4) Bubble-Size-Legende
    sd_baseS = sd_tr_short[sd_tr_short > 0]
    if sd_baseS.size >= 3 and sd_baseS.max() > 1:
        sd_legend_valsS = np.unique(np.round(np.quantile(sd_baseS, [0.25, 0.5, 0.75, 1.0])).astype(int))
        sd_legend_valsS = sd_legend_valsS[sd_legend_valsS > 0]
    else:
        sd_legend_valsS = np.array([10, 20, 35], dtype=int)

    sd_legend_sizesS = np.linspace(7, 20, len(sd_legend_valsS)) if len(sd_legend_valsS) > 1 else np.array([13.0])
    for v, s in zip(sd_legend_valsS, sd_legend_sizesS):
        sd_short_position_size_fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
                showlegend=True,
                name=f"{int(v)} Traders",
                hoverinfo='skip'
            )
        )

    # 5) Layout
    sd_short_position_size_fig.update_layout(
        title='Short Position Size Indicator (Swap Dealers)',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(showgrid=True, ticks="outside", tickangle=45),
        yaxis=dict(title='Open Interest', showgrid=True),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.18, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(
            fig=sd_short_position_size_fig,
            df=filtered_df, x_col='Date', y_col='Open Interest',
            inner_size=2, inner_color='black'
        )
    except Exception:
        pass

    long_scaling_factor, short_scaling_factor = calculate_scaling_factors(filtered_df)

    # Long Positions Clustering
    long_clustering_fig = go.Figure()

    # 1) Trader-Serie sauber vorbereiten
    tr_total = pd.to_numeric(filtered_df['Total Number of Traders'], errors='coerce') \
        .fillna(0).clip(lower=0).astype(float)

    # 2) Marker-Grössen robust auf fixen Pixelbereich mappen
    MIN_PX = 8
    MAX_PX = 30
    _tr_pos = tr_total[tr_total > 0]
    tr_lo = float(_tr_pos.min()) if _tr_pos.size > 0 else 1.0
    tr_hi = float(tr_total.max()) if tr_total.max() > 0 else 1.0
    sizes_total = scaled_diameters(tr_total, min_px=MIN_PX, max_px=MAX_PX, lo=tr_lo, hi=tr_hi)

    # 3) Scatter
    long_clustering_fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Open Interest'],
        mode='markers',
        marker=dict(
            size=sizes_total,
            sizemode='diameter',
            sizeref=1,
            color=filtered_df['Long Clustering'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title="Long Clustering (%)",
                thickness=15,
                len=0.75,
                yanchor='middle',
                y=0.5
            ),
        ),
        text=[
            f"Date: {d:%Y-%m-%d}<br>Traders: {int(t)}"
            for d, t in zip(filtered_df['Date'], tr_total)
        ],
        hoverinfo='text',
        showlegend=False
    ))

    # 4) Bubble-Size-Legende dynamisch (aus der Verteilung des selektierten Marktes)
    base = tr_total[tr_total > 0]
    if base.size >= 3:
        q = [0.10, 0.30, 0.50, 0.70, 0.90]  # 5 Legendenstufen
        legend_vals = np.unique(np.round(np.quantile(base, q)).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([50, 75, 100, 125, 150], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        long_clustering_fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
            showlegend=True,
            name=f"{int(v)} Traders",
            hoverinfo='skip'
        ))

    # 5) Layout
    long_clustering_fig.update_layout(
        title='Long Positions Clustering Indicator',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(
            tickmode='array',
            tickvals=filtered_df['Date'].dt.year.unique(),
            ticktext=[str(year) for year in filtered_df['Date'].dt.year.unique()],
            showgrid=True,
            ticks="outside",
            tickangle=45
        ),
        yaxis=dict(
            title='Open Interest',
            showgrid=True,
            tick0=0,
            dtick=20000 if selected_market in ['Gold', 'Silver', 'Copper'] else 5000,
        ),
        legend=dict(
            title=dict(text="Number of Traders"),
            itemsizing='trace',
            x=1.2,
            y=0.5,
            font=dict(size=12)
        ),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    add_last_point_highlight(
        fig=long_clustering_fig,
        df=filtered_df,
        x_col='Date',
        y_col='Open Interest',
        inner_size=2,
        inner_color='black'
    )

    # Short Positions Clustering
    short_clustering_fig = go.Figure()

    # 1) Trader-Serie (gleich wie Long)
    tr_total = pd.to_numeric(filtered_df['Total Number of Traders'], errors='coerce') \
        .fillna(0).clip(lower=0).astype(float)

    # 2) gleiche Pixel-Skalierung
    MIN_PX = 8
    MAX_PX = 30
    _tr_pos = tr_total[tr_total > 0]
    tr_lo = float(_tr_pos.min()) if _tr_pos.size > 0 else 1.0
    tr_hi = float(tr_total.max()) if tr_total.max() > 0 else 1.0
    sizes_total = scaled_diameters(tr_total, min_px=MIN_PX, max_px=MAX_PX, lo=tr_lo, hi=tr_hi)

    # 3) Scatter
    short_clustering_fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Open Interest'],
        mode='markers',
        marker=dict(
            size=sizes_total,
            sizemode='diameter',
            sizeref=1,
            color=filtered_df['Short Clustering'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title="Short Clustering (%)",
                thickness=15,
                len=0.75,
                yanchor='middle',
                y=0.5
            ),
        ),
        text=[
            f"Date: {d:%Y-%m-%d}<br>Traders: {int(t)}"
            for d, t in zip(filtered_df['Date'], tr_total)
        ],
        hoverinfo='text',
        showlegend=False
    ))

    # 4) Bubble-Size-Legende dynamisch
    base = tr_total[tr_total > 0]
    if base.size >= 3:
        q = [0.10, 0.30, 0.50, 0.70, 0.90]
        legend_vals = np.unique(np.round(np.quantile(base, q)).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([50, 75, 100, 125, 150], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])

    for v, s in zip(legend_vals, legend_sizes):
        short_clustering_fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
            showlegend=True,
            name=f"{int(v)} Traders",
            hoverinfo='skip'
        ))

    # 5) Layout
    short_clustering_fig.update_layout(
        title='Short Positions Clustering Indicator',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(
            tickmode='array',
            tickvals=filtered_df['Date'].dt.year.unique(),
            ticktext=[str(year) for year in filtered_df['Date'].dt.year.unique()],
            showgrid=True,
            ticks="outside",
            tickangle=45
        ),
        yaxis=dict(
            title='Open Interest',
            showgrid=True,
            tick0=0,
            dtick=20000 if selected_market in ['Gold', 'Silver', 'Copper'] else 5000,
        ),
        legend=dict(
            title=dict(text="Number of Traders"),
            itemsizing='trace',
            x=1.2,
            y=0.5,
            font=dict(size=12)
        ),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    add_last_point_highlight(
        fig=short_clustering_fig,
        df=filtered_df,
        x_col='Date',
        y_col='Open Interest',
        inner_size=2,
        inner_color='black'
    )

    # OR Long Position Size Indicator
    or_long_position_size_fig = go.Figure()

    # 1) Daten vorbereiten
    tr_long_raw  = pd.to_numeric(filtered_df['Traders Other Rept Long'], errors='coerce')
    tr_long = tr_long_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Long)
    try:
        col_long = safe_colors(filtered_df['ORL Position Size'])
    except Exception:
        col_long = pd.to_numeric(filtered_df['ORL Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen
    _or_l_pos = tr_long[tr_long > 0]
    or_l_lo = float(_or_l_pos.min()) if _or_l_pos.size > 0 else 1.0
    or_l_hi = float(tr_long.max()) if tr_long.max() > 0 else 1.0
    sizes_long = scaled_diameters(tr_long, min_px=6, max_px=26, lo=or_l_lo, hi=or_l_hi)

    # 3) Punkte plotten
    or_long_position_size_fig.add_trace(
        go.Scatter(
            x=filtered_df['Date'],
            y=filtered_df['Open Interest'],
            mode='markers',
            marker=dict(
                size=sizes_long,
                sizemode='diameter',
                sizeref=1,
                color=col_long,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="OR Long Position Size",
                    thickness=15, len=0.75, yanchor='middle', y=0.5
                )
            ),
            text=[
                f"Date: {d:%Y-%m-%d}<br>"
                f"Open Interest: {int(oi):,}<br>"
                f"Traders (Long): {int(t)}<br>"
                f"PosSize (avg): {float(ps):,.0f}"
                for d, oi, t, ps in zip(
                    filtered_df['Date'],
                    pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                    tr_long,
                    pd.to_numeric(filtered_df['ORL Position Size'], errors='coerce').fillna(0)
                )
            ],
            hoverinfo='text',
            showlegend=False
        )
    )

    # 4) Bubble-Size-Legende (gleiche Skalierung wie oben)
    base = tr_long[tr_long > 0]
    if base.size >= 3 and base.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])
    for v, s in zip(legend_vals, legend_sizes):
        or_long_position_size_fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
                showlegend=True,
                name=f"{int(v)} Traders",
                hoverinfo='skip'
            )
        )

    # 5) Layout
    or_long_position_size_fig.update_layout(
        title='Long Position Size Indicator (Other Reportables)',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(showgrid=True, ticks="outside", tickangle=45),
        yaxis=dict(title='Open Interest', showgrid=True),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.18, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(
            fig=or_long_position_size_fig,
            df=filtered_df, x_col='Date', y_col='Open Interest',
            inner_size=2, inner_color='black'
        )
    except Exception:
        pass

    # OR Short Position Size Indicator
    or_short_position_size_fig = go.Figure()

    # 1) Daten vorbereiten
    tr_short_raw = pd.to_numeric(filtered_df['Traders Other Rept Short'], errors='coerce')
    tr_short = tr_short_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Short)
    try:
        col_short = safe_colors(filtered_df['ORS Position Size'])
    except Exception:
        col_short = pd.to_numeric(filtered_df['ORS Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen
    _or_s_pos = tr_short[tr_short > 0]
    or_s_lo = float(_or_s_pos.min()) if _or_s_pos.size > 0 else 1.0
    or_s_hi = float(tr_short.max()) if tr_short.max() > 0 else 1.0
    sizes_short = scaled_diameters(tr_short, min_px=6, max_px=26, lo=or_s_lo, hi=or_s_hi)

    # 3) Punkte plotten
    or_short_position_size_fig.add_trace(
        go.Scatter(
            x=filtered_df['Date'],
            y=filtered_df['Open Interest'],
            mode='markers',
            marker=dict(
                size=sizes_short,
                sizemode='diameter',
                sizeref=1,
                color=col_short,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="OR Short Position Size",
                    thickness=15, len=0.75, yanchor='middle', y=0.5
                )
            ),
            text=[
                f"Date: {d:%Y-%m-%d}<br>"
                f"Open Interest: {int(oi):,}<br>"
                f"Traders (Short): {int(t)}<br>"
                f"PosSize (avg): {float(ps):,.0f}"
                for d, oi, t, ps in zip(
                    filtered_df['Date'],
                    pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                    tr_short,
                    pd.to_numeric(filtered_df['ORS Position Size'], errors='coerce').fillna(0)
                )
            ],
            hoverinfo='text',
            showlegend=False
        )
    )

    # 4) Bubble-Size-Legende (gleiche Skalierung wie oben)
    base_s = tr_short[tr_short > 0]
    if base_s.size >= 3 and base_s.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base_s, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])
    for v, s in zip(legend_vals, legend_sizes):
        or_short_position_size_fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
                showlegend=True,
                name=f"{int(v)} Traders",
                hoverinfo='skip'
            )
        )

    # 5) Layout
    or_short_position_size_fig.update_layout(
        title='Short Position Size Indicator (Other Reportables)',
        xaxis_title='Date',
        yaxis_title='Open Interest',
        xaxis=dict(showgrid=True, ticks="outside", tickangle=45),
        yaxis=dict(title='Open Interest', showgrid=True),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.18, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(
            fig=or_short_position_size_fig,
            df=filtered_df, x_col='Date', y_col='Open Interest',
            inner_size=2, inner_color='black'
        )
    except Exception:
        pass

    # --- MM Long Position Size Indicator ---
    long_position_size_fig = go.Figure()

    # 1) Daten vorbereiten (Größe = Anzahl Trader)
    mm_tr_long_raw = pd.to_numeric(filtered_df['Traders M Money Long'], errors='coerce')
    mm_tr_long = mm_tr_long_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Long)
    try:
        mm_col_long = safe_colors(filtered_df['MML Position Size'])
    except Exception:
        mm_col_long = pd.to_numeric(filtered_df['MML Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen (z.B. 6–26 px)
    _mm_l_pos = mm_tr_long[mm_tr_long > 0]
    mm_l_lo = float(_mm_l_pos.min()) if _mm_l_pos.size > 0 else 1.0
    mm_l_hi = float(mm_tr_long.max()) if mm_tr_long.max() > 0 else 1.0
    mm_sizes_long = scaled_diameters(mm_tr_long, min_px=6, max_px=26, lo=mm_l_lo, hi=mm_l_hi)

    # 3) Punkte plotten
    long_position_size_fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Open Interest'],
        mode='markers',
        marker=dict(
            size=mm_sizes_long,
            sizemode='diameter',
            sizeref=1,
            color=mm_col_long,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="MM Long Position Size", thickness=15, len=0.75, yanchor='middle', y=0.5)
        ),
        text=[
            f"Date: {d:%Y-%m-%d}<br>"
            f"Open Interest: {int(oi):,}<br>"
            f"Traders (Long): {int(t)}<br>"
            f"PosSize (avg): {float(ps):,.0f}"
            for d, oi, t, ps in zip(
                filtered_df['Date'],
                pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                mm_tr_long,
                pd.to_numeric(filtered_df['MML Position Size'], errors='coerce').fillna(0)
            )
        ],
        hoverinfo='text',
        showlegend=False
    ))

    # 4) Bubble-Size-Legende
    base = mm_tr_long[mm_tr_long > 0]
    if base.size >= 3 and base.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])
    for v, s in zip(legend_vals, legend_sizes):
        long_position_size_fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
            showlegend=True, name=f"{int(v)} Traders", hoverinfo='skip'
        ))

    # 5) Layout
    long_position_size_fig.update_layout(
        title='Long Position Size Indicator (Money Managers)',
        xaxis_title='Date', yaxis_title='Open Interest',
        xaxis=dict(
            tickmode='array',
            tickvals=filtered_df['Date'].dt.year.unique(),
            ticktext=[str(y) for y in filtered_df['Date'].dt.year.unique()],
            showgrid=True, ticks="outside", tickangle=45
        ),
        yaxis=dict(
            title='Open Interest', showgrid=True, tick0=0,
            dtick=20000 if selected_market in ['Gold', 'Silver', 'Copper'] else 5000
        ),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.2, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(long_position_size_fig, filtered_df, 'Date', 'Open Interest', inner_size=2,
                                 inner_color='black')
    except Exception:
        pass

    # --- MM Short Position Size Indicator ---
    short_position_size_fig = go.Figure()

    # 1) Daten vorbereiten (Größe = Anzahl Trader)
    mm_tr_short_raw = pd.to_numeric(filtered_df['Traders M Money Short'], errors='coerce')
    mm_tr_short = mm_tr_short_raw.fillna(0).clip(lower=0).astype(float)

    # Farbe = Positionsgröße (Short)
    try:
        mm_col_short = safe_colors(filtered_df['MMS Position Size'])
    except Exception:
        mm_col_short = pd.to_numeric(filtered_df['MMS Position Size'], errors='coerce').fillna(0)

    # 2) Durchmesser explizit auf Pixel mappen
    _mm_s_pos = mm_tr_short[mm_tr_short > 0]
    mm_s_lo = float(_mm_s_pos.min()) if _mm_s_pos.size > 0 else 1.0
    mm_s_hi = float(mm_tr_short.max()) if mm_tr_short.max() > 0 else 1.0
    mm_sizes_short = scaled_diameters(mm_tr_short, min_px=6, max_px=26, lo=mm_s_lo, hi=mm_s_hi)

    # 3) Punkte plotten
    short_position_size_fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Open Interest'],
        mode='markers',
        marker=dict(
            size=mm_sizes_short,
            sizemode='diameter',
            sizeref=1,
            color=mm_col_short,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="MM Short Position Size", thickness=15, len=0.75, yanchor='middle', y=0.5)
        ),
        text=[
            f"Date: {d:%Y-%m-%d}<br>"
            f"Open Interest: {int(oi):,}<br>"
            f"Traders (Short): {int(t)}<br>"
            f"PosSize (avg): {float(ps):,.0f}"
            for d, oi, t, ps in zip(
                filtered_df['Date'],
                pd.to_numeric(filtered_df['Open Interest'], errors='coerce').fillna(0),
                mm_tr_short,
                pd.to_numeric(filtered_df['MMS Position Size'], errors='coerce').fillna(0)
            )
        ],
        hoverinfo='text',
        showlegend=False
    ))

    # 4) Bubble-Size-Legende
    base_s = mm_tr_short[mm_tr_short > 0]
    if base_s.size >= 3 and base_s.max() > 1:
        legend_vals = np.unique(np.round(np.quantile(base_s, [0.25, 0.5, 0.75, 1.0])).astype(int))
        legend_vals = legend_vals[legend_vals > 0]
    else:
        legend_vals = np.array([10, 20, 35], dtype=int)

    legend_sizes = np.linspace(7, 20, len(legend_vals)) if len(legend_vals) > 1 else np.array([13.0])
    for v, s in zip(legend_vals, legend_sizes):
        short_position_size_fig.add_trace(go.Scatter(
            x=[None], y=[None], mode='markers',
            marker=dict(size=float(s), sizemode='diameter', sizeref=1, color='gray', opacity=0.6),
            showlegend=True, name=f"{int(v)} Traders", hoverinfo='skip'
        ))

    # 5) Layout
    short_position_size_fig.update_layout(
        title='Short Position Size Indicator (Money Managers)',
        xaxis_title='Date', yaxis_title='Open Interest',
        xaxis=dict(
            tickmode='array',
            tickvals=filtered_df['Date'].dt.year.unique(),
            ticktext=[str(y) for y in filtered_df['Date'].dt.year.unique()],
            showgrid=True, ticks="outside", tickangle=45
        ),
        yaxis=dict(
            title='Open Interest', showgrid=True, tick0=0,
            dtick=20000 if selected_market in ['Gold', 'Silver', 'Copper'] else 5000
        ),
        legend=dict(title=dict(text="Number of Traders"), itemsizing='trace', x=1.2, y=0.5, font=dict(size=12)),
        margin=dict(l=60, r=160, t=60, b=60)
    )

    # 6) letzten Punkt hervorheben
    try:
        add_last_point_highlight(short_position_size_fig, filtered_df, 'Date', 'Open Interest', inner_size=2,
                                 inner_color='black')
    except Exception:
        pass

    # --- Dry Powder Indicator---
    dry_powder_fig = go.Figure()

    BUBBLE_PX = 14
    desired_max_px = 28

    COL_LONG = "#2c7fb8"  # MML
    COL_SHORT = "#7fcdbb"  # MMS

    # MML Wolke
    dry_powder_fig.add_trace(go.Scatter(
        x=filtered_df['MML Traders'],
        y=filtered_df['MML Long OI'],
        mode='markers',
        marker=dict(
            size=BUBBLE_PX,
            color=COL_LONG, opacity=0.75, line=dict(width=0.6, color='black')
        ),
        name='MML'
    ))

    # MMS Wolke
    dry_powder_fig.add_trace(go.Scatter(
        x=filtered_df['MMS Traders'],
        y=filtered_df['MML Short OI'],
        mode='markers',
        marker=dict(
            size=BUBBLE_PX,
            color=COL_SHORT, opacity=0.75, line=dict(width=0.6, color='black')
        ),
        name='MMS'
    ))

    # x-Range über beide Gruppen
    x_min = float(min(filtered_df['MML Traders'].min(), filtered_df['MMS Traders'].min()))
    x_max = float(max(filtered_df['MML Traders'].max(), filtered_df['MMS Traders'].max()))
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
            line=dict(color='white', width=7),
            name=name, showlegend=False, hoverinfo='skip'
        ))
        # Farblinie oben drauf
        dry_powder_fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line=dict(color=color, width=3),
            name=name, showlegend=True
        ))

    # Trendlinien hinzufügen (durch den ganzen Graph)
    add_trend(filtered_df['MML Traders'], filtered_df['MML Long OI'], COL_LONG, "MML Trend")
    add_trend(filtered_df['MMS Traders'], filtered_df['MML Short OI'], COL_SHORT, "MMS Trend")

    # Most Recent Week
    dry_powder_fig.add_trace(go.Scatter(
        x=[filtered_df['MML Traders'].iloc[-1]],
        y=[filtered_df['MML Long OI'].iloc[-1]],
        mode='markers',
        marker=dict(size=desired_max_px + 4, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week', legendgroup='recent', showlegend=True
    ))
    dry_powder_fig.add_trace(go.Scatter(
        x=[filtered_df['MMS Traders'].iloc[-1]],
        y=[filtered_df['MML Short OI'].iloc[-1]],
        mode='markers',
        marker=dict(size=desired_max_px + 4, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week', legendgroup='recent', showlegend=False  # keine doppelte Legende
    ))

    dry_powder_fig.update_layout(
        title=f"DP Indicator",
        xaxis=dict(title='Number of Traders', showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False),
        yaxis=dict(title='Long and Short OI', showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False),
        plot_bgcolor='white',
        legend_title='Trader Group'
    )

    # --- DP Relative Concentration Indicator (konstante Grösse + 8 schwarze Punkte) ---
    fig_rc = go.Figure()

    TOTAL_OI = pd.to_numeric(filtered_df.get('Open Interest'), errors='coerce')

    def rc(long_col, short_col):
        return rel_concentration(
            filtered_df.get(long_col), filtered_df.get(short_col), TOTAL_OI
        )

    groups = [
        dict(name='MML', x='Traders M Money Long',
             rc=rc('Managed Money Long', 'Managed Money Short'), color='#2c7fb8'),
        dict(name='MMS', x='Traders M Money Short',
             rc=rc('Managed Money Short', 'Managed Money Long'), color='#7fcdbb'),
        dict(name='ORL', x='Traders Other Rept Long',
             rc=rc('Other Reportables Long', 'Other Reportables Short'), color='#f39c12'),
        dict(name='ORS', x='Traders Other Rept Short',
             rc=rc('Other Reportables Short', 'Other Reportables Long'), color='#f1c40f'),
        dict(name='PMPUL', x='Traders Prod/Merc Long',
             rc=rc('Producer/Merchant/Processor/User Long',
                   'Producer/Merchant/Processor/User Short'), color='#27ae60'),
        dict(name='PMPUS', x='Traders Prod/Merc Short',
             rc=rc('Producer/Merchant/Processor/User Short',
                   'Producer/Merchant/Processor/User Long'), color='#2ecc71'),
        dict(name='SDL', x='Traders Swap Long',
             rc=rc('Swap Dealer Long', 'Swap Dealer Short'), color='#e67e22'),
        dict(name='SDS', x='Traders Swap Short',
             rc=rc('Swap Dealer Short', 'Swap Dealer Long'), color='#e74c3c'),
    ]

    # 1) KONSTANTE Bubble-Grösse in Pixel (für alle gleich)
    bubble_px = 14
    recent_px = bubble_px + 6

    # Historische Punkte je Gruppe
    for g in groups:
        x = pd.to_numeric(filtered_df.get(g['x']), errors='coerce')
        y = g['rc']
        mask = x.notna() & y.notna()
        if mask.sum() == 0:
            continue

        fig_rc.add_trace(go.Scatter(
            x=x[mask],
            y=y[mask],
            mode='markers',
            marker=dict(
                size=bubble_px,
                color=g['color'],
                opacity=0.8,
                line=dict(width=0.6, color='black')
            ),
            name=g['name']
        ))

    # 2) PRO GRUPPE: schwarzer Punkt für die letzte verfügbare Beobachtung
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
                x=[x_last], y=[y_last],
                mode='markers',
                marker=dict(size=recent_px, color='black', line=dict(width=2, color='white')),
                name='Most Recent Week',
                legendgroup='recent',
                showlegend=not first_legend_done  # nur 1 Legenden-Eintrag
            ))
            first_legend_done = True

    fig_rc.update_layout(
        title="DP Relative Concentration Indicator",
        xaxis=dict(title='Number of Traders', showgrid=True, gridcolor='LightGray'),
        yaxis=dict(title='Long and Short Concentration', showgrid=True, gridcolor='LightGray'),
        plot_bgcolor='white',
        legend_title='Trader Group'
    )

    # DP Seasonal Indicator
    dp_seasonal_indicator_fig = go.Figure()

    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    colors = ['#1f77b4', '#17becf', '#ff7f0e', '#d62728']

    for quarter, color in zip(quarters, colors):
        quarter_data = filtered_df[filtered_df['Quarter'] == quarter]
        if quarter_data.empty:
            continue

        dp_seasonal_indicator_fig.add_trace(go.Scatter(
            x=quarter_data['PMPUL Traders'],
            y=quarter_data['PMPUL Relative Concentration'],
            mode='markers',
            marker=dict(
                size=10,  # 🔹 Fixe, einheitliche Bubblegröße
                color=color,
                opacity=0.7,
                line=dict(width=0.6, color='black')
            ),
            name=quarter
        ))

    # Schwarzer Punkt für Most Recent Week
    most_recent_date = filtered_df['Date'].max()
    recent_data = filtered_df[filtered_df['Date'] == most_recent_date]
    if not recent_data.empty:
        dp_seasonal_indicator_fig.add_trace(go.Scatter(
            x=recent_data['PMPUL Traders'],
            y=recent_data['PMPUL Relative Concentration'],
            mode='markers',
            marker=dict(
                size=12,  # etwas grösser zur Hervorhebung
                color='black',
                symbol='circle',
                line=dict(width=1.5, color='white')
            ),
            name='Most Recent Week'
        ))

    dp_seasonal_indicator_fig.update_layout(
        title=f"DP Seasonal Indicator – {most_recent_date.strftime('%d/%m/%Y')}",
        xaxis_title="Number of Traders",
        yaxis_title="Long and Short Concentration",
        plot_bgcolor='white',
        legend_title="Quarter",
        xaxis=dict(showgrid=True, gridcolor='LightGray'),
        yaxis=dict(showgrid=True, gridcolor='LightGray')
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
            x=year_data['MM Net Traders'],
            y=year_data['MM Net OI'],
            mode='markers',
            marker=dict(size=10, opacity=0.6),
            name=str(year)
        ))

    # Adding markers for the most recent and first weeks
    recent_data = filtered_df[filtered_df['Date'] == most_recent_date]
    first_data = filtered_df[filtered_df['Date'] == first_date]
    
    dp_net_indicators_fig.add_trace(go.Scatter(
        x=recent_data['MM Net Traders'],
        y=recent_data['MM Net OI'],
        mode='markers',
        marker=dict(size=12, color='black', symbol='circle'),
        name='Most Recent Week'
    ))

    dp_net_indicators_fig.add_trace(go.Scatter(
        x=first_data['MM Net Traders'],
        y=first_data['MM Net OI'],
        mode='markers',
        marker=dict(size=12, color='red', symbol='circle'),
        name='First Week'
    ))

    # Adding medians
    dp_net_indicators_fig.add_trace(go.Scatter(
        x=[median_traders, median_traders],
        y=[filtered_df['MM Net OI'].min(), filtered_df['MM Net OI'].max()],
        mode='lines',
        line=dict(color='gray', dash='dash'),
        name='Median Net Traders'
    ))

    dp_net_indicators_fig.add_trace(go.Scatter(
        x=[filtered_df['MM Net Traders'].min(), filtered_df['MM Net Traders'].max()],
        y=[median_oi, median_oi],
        mode='lines',
        line=dict(color='gray', dash='dash'),
        name='Median Net OI'
    ))

    dp_net_indicators_fig.update_layout(
        title='DP Net Indicators with Medians',
        xaxis_title='MM Net Number of Traders',
        yaxis_title='MM Net OI',
        legend_title='Year'
    )

    # Dry Powder Position Size Indicator (MML & MMS)
    dff = filtered_df
    if mm_type == 'MML':
        x = dff['Traders M Money Long']
        y = dff['MML Position Size']
        color = dff['Open Interest']
        recent_week = dff['MML Position Size'].iloc[-1]
        recent_x = dff['Traders M Money Long'].iloc[-1]
        first_week = dff['MML Position Size'].iloc[0]
        first_x = dff['Traders M Money Long'].iloc[0]
    else:
        x = dff['Traders M Money Short']
        y = dff['MMS Position Size']
        color = dff['Open Interest']
        recent_week = dff['MMS Position Size'].iloc[-1]
        recent_x = dff['Traders M Money Short'].iloc[-1]
        first_week = dff['MMS Position Size'].iloc[0]
        first_x = dff['Traders M Money Short'].iloc[0]

    median_x = x.median()
    median_y = y.median()

    dp_position_size_fig = go.Figure()

    dp_position_size_fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='markers',
        marker=dict(
            size=10,
            color=color,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(
                title='Open Interest',
                thickness=15,
                len=0.75,
                yanchor='middle'
            )
        ),
        text=dff['Date'],
        hoverinfo='text',
        showlegend=False
    ))

    dp_position_size_fig.add_trace(go.Scatter(
        x=[recent_x],
        y=[recent_week],
        mode='markers',
        marker=dict(
            size=12,
            color='black'
        ),
        name='Most Recent Week'
    ))

    dp_position_size_fig.add_trace(go.Scatter(
        x=[first_x],
        y=[first_week],
        mode='markers',
        marker=dict(
            size=12,
            color='red'
        ),
        name='First Week'
    ))

    dp_position_size_fig.add_shape(type="line",
                  x0=median_x, y0=0, x1=median_x, y1=max(y),
                  line=dict(color="Gray", width=1, dash="dash"))

    dp_position_size_fig.add_shape(type="line",
                  x0=0, y0=median_y, x1=max(x), y1=median_y,
                  line=dict(color="Gray", width=1, dash="dash"))

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
        x = 'Traders M Money Long'
        y = 'MML Long OI'
        color = 'PMPUL Relative Concentration'
        title = 'DP Hedging Indicator (MML vs PMPUL)'
        colorbar_title = 'PMPUL OI Range'
        x_title = 'MM Number of Long Traders'
        y_title = 'MM Long OI'
    else:
        x = 'Traders M Money Short'
        y = 'MMS Short OI'
        color = 'PMPUS Relative Concentration'
        title = 'DP Hedging Indicator (MMS vs PMPUS)'
        colorbar_title = 'PMPUS OI Range'
        x_title = 'MM Number of Short Traders'
        y_title = 'MM Short OI'

    # Vorab die gewünschten Achsenranges bestimmen (benötigen wir auch für die Trendlinie)
    x_min = float(np.nanmin(data[x])) - 10
    x_max = float(np.nanmax(data[x])) + 10
    y_min = float(np.nanmin(data[y])) - 50000
    y_max = float(np.nanmax(data[y])) + 50000

    # Haupt-Scatter
    # --- Bubble sizing---
    oi = pd.to_numeric(data['Open Interest'], errors='coerce').abs()

    desired_max_px = 26
    desired_min_px = 6
    sizeref = 2.0 * oi.max() / (desired_max_px ** 2)

    trace = go.Scatter(
        x=data[x],
        y=data[y],
        mode='markers',
        marker=dict(
            size=oi,
            sizemode='area',
            sizeref=sizeref,
            sizemin=desired_min_px,
            color=data[color],
            colorscale='RdBu',
            showscale=True,
            colorbar=dict(title=colorbar_title, len=0.5, x=1.1)
        ),
        text=data['Market Names'],
        hoverinfo='text',
        showlegend=False
    )

    # First / Last Week Marker
    first_week = data.iloc[0]
    last_week = data.iloc[-1]

    first_week_trace = go.Scatter(
        x=[first_week[x]], y=[first_week[y]],
        mode='markers', marker=dict(color='red', size=15),
        name='First Week'
    )
    last_week_trace = go.Scatter(
        x=[last_week[x]], y=[last_week[y]],
        mode='markers', marker=dict(color='black', size=15),
        name='Most Recent Week'
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
            line=dict(color='black', width=2),
            hoverinfo='skip',
            showlegend=False
        )

    # Layout
    layout = go.Layout(
        title=title,
        xaxis=dict(title=x_title, range=[x_min, x_max]),
        yaxis=dict(title=y_title, range=[y_min, y_max]),
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
    agg_df = filtered_df.groupby('Market Names').mean(numeric_only=True).reset_index()
    
    conc_col, clust_col = _indicator_cols(selected_indicator)
    concentration_range, clustering_range = calculate_ranges(agg_df, conc_col, clust_col)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=clustering_range,
        y=concentration_range,
        mode='markers+text',
        text=agg_df['Market Names'],
        textposition='top center',
        marker=dict(size=10, opacity=0.6, color='green', line=dict(width=1, color='black'))
    ))
    
    fig.update_layout(
        title=f'DP Concentration/Clustering Indicator ({selected_indicator})',
        xaxis_title='MM Long Clustering Range' if selected_indicator == 'MML' else 'MM Short Clustering Range',
        yaxis_title='MM Long Concentration Range' if selected_indicator == 'MML' else 'MM Short Concentration Range',
        xaxis=dict(range=[-5, 110]),  # Adjusted to ensure all bubbles are visible
        yaxis=dict(range=[-5, 110]),  # Adjusted to ensure all bubbles are visible
        showlegend=False
    )
    
    return fig


# ---------------------------------------------------------------------------
# PPCI – Callback
# ---------------------------------------------------------------------------
@app.callback(
    Output('positioning-price-concentration-graph', 'figure'),
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('ppci-mm-radio', 'value')]
)
def update_ppci(selected_market, start_date, end_date, direction):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy()

    if dff.empty:
        return go.Figure()

    # Normalize Date to tz-naive for merging
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    # Long/Short Concentration (%)
    total_oi = pd.to_numeric(dff['Open Interest'], errors='coerce').replace(0, np.nan)
    dff['_long_conc']  = 100.0 * pd.to_numeric(dff['Managed Money Long'],  errors='coerce') / total_oi
    dff['_short_conc'] = 100.0 * pd.to_numeric(dff['Managed Money Short'], errors='coerce') / total_oi

    if direction == 'MML':
        color_col      = '_long_conc'
        colorbar_title = 'MML Concentration (%)'
    else:
        color_col      = '_short_conc'
        colorbar_title = 'MMS Concentration (%)'

    # Merge futures prices from InfluxDB (continuous contract proxy for 2nd Nearby)
    price_col = _ppci_get_price_col(selected_market)
    y_title = 'Price (Continuous Front-Month Proxy) (Report Date)'

    if price_col and not df_futures_prices.empty and price_col in df_futures_prices.columns:
        prices = df_futures_prices[['Date', price_col]].dropna(subset=[price_col]).copy()
        prices = prices.rename(columns={'Date': '_pdate'}).sort_values('_pdate')
        dff = dff.sort_values('_date')

        dff = pd.merge_asof(
            dff, prices,
            left_on='_date', right_on='_pdate',
            direction='backward',
            tolerance=pd.Timedelta(days=7)
        )
        y_vals = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        y_vals = pd.Series([np.nan] * len(dff), index=dff.index)
        y_title = f'Price (keine Daten für {selected_market})'

    # Bubble sizing: Total Open Interest
    oi = pd.to_numeric(dff['Open Interest'], errors='coerce').fillna(0).abs()

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
        marker=dict(
            size=sizes_oi,
            sizemode='diameter',
            sizeref=1,
            color=color_vals,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(
                title=colorbar_title,
                thickness=15,
                len=0.75,
                yanchor='middle',
                y=0.5
            ),
        ),
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
            marker=dict(
                size=float(s),
                sizemode='diameter',
                sizeref=1,
                color='gray',
                opacity=0.6
            ),
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
            marker=dict(
                size=10,
                color='black',
                opacity=1.0,
                line=dict(width=4, color='red')
            ),
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'Positioning Price Concentration Indicator ({direction}) – {selected_market}',
        xaxis_title='Report Date',
        yaxis_title=y_title,
        legend=dict(
            title=dict(text='Total Open Interest'),
            itemsizing='trace',
            x=1.2,
            y=0.5,
            font=dict(size=12)
        ),
        margin=dict(l=60, r=160, t=60, b=60),
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# PP Clustering Indicator – Callback
# Wiederverwendet: _ppci_get_price_col, df_futures_prices, merge_asof,
# scaled_diameters, OI-Legende und Letzter-Punkt-Highlight aus dem PPCI.
# Unterschied zum PPCI: Farbe = Long/Short Clustering statt Concentration (%).
# ---------------------------------------------------------------------------
@app.callback(
    Output('pp-clustering-graph', 'figure'),
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('ppci-clustering-radio', 'value')]
)
def update_pp_clustering(selected_market, start_date, end_date, mm_type):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy()

    if dff.empty:
        return go.Figure()

    # Normalize Date to tz-naive for merging (identisch zu PPCI)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if mm_type == 'MML':
        color_col      = 'Long Clustering'
        colorbar_title = 'MML Clustering'
    else:
        color_col      = 'Short Clustering'
        colorbar_title = 'MMS Clustering'

    # 2nd-Nearby-Preislogik identisch zum PPCI
    price_col = _ppci_get_price_col(selected_market)
    y_title = 'Price (Continuous Front-Month Proxy) (Report Date)'

    if price_col and not df_futures_prices.empty and price_col in df_futures_prices.columns:
        prices = df_futures_prices[['Date', price_col]].dropna(subset=[price_col]).copy()
        prices = prices.rename(columns={'Date': '_pdate'}).sort_values('_pdate')
        dff = dff.sort_values('_date')
        dff = pd.merge_asof(
            dff, prices,
            left_on='_date', right_on='_pdate',
            direction='backward',
            tolerance=pd.Timedelta(days=7)
        )
        y_vals = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        y_vals = pd.Series([np.nan] * len(dff), index=dff.index)
        y_title = f'Price (keine Daten für {selected_market})'

    # Bubble-Größen (identisch zu PPCI)
    oi = pd.to_numeric(dff['Open Interest'], errors='coerce').fillna(0).abs()
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
        marker=dict(
            size=sizes_oi,
            sizemode='diameter',
            sizeref=1,
            color=color_vals,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(
                title=colorbar_title,
                thickness=15,
                len=0.75,
                yanchor='middle',
                y=0.5
            ),
        ),
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
            marker=dict(
                size=float(s),
                sizemode='diameter',
                sizeref=1,
                color='gray',
                opacity=0.6
            ),
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
            marker=dict(
                size=10,
                color='black',
                opacity=1.0,
                line=dict(width=4, color='red')
            ),
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'PP Clustering Indicator ({mm_type}) – {selected_market}',
        xaxis_title='Report Date',
        yaxis_title=y_title,
        legend=dict(
            title=dict(text='Total Open Interest'),
            itemsizing='trace',
            x=1.2,
            y=0.5,
            font=dict(size=12)
        ),
        margin=dict(l=60, r=160, t=60, b=60),
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# PP Position Size Indicator – Callback
# Wiederverwendet: _ppci_get_price_col, df_futures_prices, merge_asof,
# scaled_diameters, Letzter-Punkt-Highlight aus dem PPCI.
# Bubble-Größe = Anzahl MM-Trader (statt OI), Farbe = Position Size in USD.
# Position Size ($) = MML/MMS Position Size (Kontrakte/Trader) × Price.
# ---------------------------------------------------------------------------
@app.callback(
    Output('pp-position-size-graph', 'figure'),
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('ppci-position-size-radio', 'value')]
)
def update_pp_position_size(selected_market, start_date, end_date, mm_type):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy()

    if dff.empty:
        return go.Figure()

    # Normalize Date to tz-naive for merging (identisch zu PPCI)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    # 2nd-Nearby-Preislogik identisch zum PPCI
    price_col = _ppci_get_price_col(selected_market)
    y_title = 'Price (Continuous Front-Month Proxy) (Report Date)'

    if price_col and not df_futures_prices.empty and price_col in df_futures_prices.columns:
        prices = df_futures_prices[['Date', price_col]].dropna(subset=[price_col]).copy()
        prices = prices.rename(columns={'Date': '_pdate'}).sort_values('_pdate')
        dff = dff.sort_values('_date')
        dff = pd.merge_asof(
            dff, prices,
            left_on='_date', right_on='_pdate',
            direction='backward',
            tolerance=pd.Timedelta(days=7)
        )
        y_vals = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        y_vals = pd.Series([np.nan] * len(dff), index=dff.index)
        y_title = f'Price (keine Daten für {selected_market})'

    # Position Size in USD = (MML/MMS Position Size in Kontrakten) × Kontraktgröße × Price
    price_series = y_vals.reset_index(drop=True)
    dff = dff.reset_index(drop=True)
    contract_size = _ppci_get_contract_size(selected_market)

    if mm_type == 'MML':
        traders_col    = 'Traders M Money Long'
        pos_size_contr = pd.to_numeric(dff['MML Position Size'], errors='coerce')
        colorbar_title = 'Long Position Size ($)'
        size_legend_title = 'Number of Long Traders'
    else:
        traders_col    = 'Traders M Money Short'
        pos_size_contr = pd.to_numeric(dff['MMS Position Size'], errors='coerce')
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
        marker=dict(
            size=sizes_traders,
            sizemode='diameter',
            sizeref=1,
            color=color_vals,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(
                title=colorbar_title,
                thickness=15,
                len=0.75,
                yanchor='middle',
                y=0.5
            ),
        ),
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
            marker=dict(
                size=float(s),
                sizemode='diameter',
                sizeref=1,
                color='gray',
                opacity=0.6
            ),
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
            marker=dict(
                size=10,
                color='black',
                opacity=1.0,
                line=dict(width=4, color='red')
            ),
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        title=f'PP Position Size Indicator ({mm_type}) – {selected_market}',
        xaxis_title='Report Date',
        yaxis_title=y_title,
        legend=dict(
            title=dict(text=size_legend_title),
            itemsizing='trace',
            x=1.2,
            y=0.5,
            font=dict(size=12)
        ),
        margin=dict(l=60, r=160, t=60, b=60),
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
# Preisquelle: df_futures_prices via _ppci_get_price_col (identisch zu PPCI).
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-notional-indicator-graph', 'figure'),
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_dp_notional(selected_market, start_date, end_date):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    # 2nd-Nearby-Preis (identisch zu PPCI)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)
    price_col = _ppci_get_price_col(selected_market)

    if price_col and not df_futures_prices.empty and price_col in df_futures_prices.columns:
        prices = df_futures_prices[['Date', price_col]].dropna(subset=[price_col]).copy()
        prices = prices.rename(columns={'Date': '_pdate'}).sort_values('_pdate')
        dff = dff.sort_values('_date').reset_index(drop=True)
        dff = pd.merge_asof(
            dff, prices,
            left_on='_date', right_on='_pdate',
            direction='backward',
            tolerance=pd.Timedelta(days=7)
        )
        price_series = pd.to_numeric(dff[price_col], errors='coerce')
    else:
        price_series = pd.Series([np.nan] * len(dff), index=dff.index)

    # Notional Exposure in USD bn
    # Formel: Kontrakte × Kontraktgröße (Einheiten/Kontrakt) × Preis (USD/Einheit) / 1e9
    contract_size = _ppci_get_contract_size(selected_market)
    mml_oi = pd.to_numeric(dff['Managed Money Long'],  errors='coerce')
    mms_oi = pd.to_numeric(dff['Managed Money Short'], errors='coerce')

    y_mml =  mml_oi * contract_size * price_series / 1e9   # positiv
    y_mms = -mms_oi * contract_size * price_series / 1e9   # negativ

    x_mml = pd.to_numeric(dff['MML Traders'], errors='coerce')
    x_mms = pd.to_numeric(dff['MMS Traders'], errors='coerce')

    BUBBLE_PX = 14
    desired_max_px = 28

    COL_LONG  = "#2c7fb8"  # MML
    COL_SHORT = "#7fcdbb"  # MMS

    fig = go.Figure()

    # Wolken
    fig.add_trace(go.Scatter(
        x=x_mml, y=y_mml,
        mode='markers',
        marker=dict(
            size=BUBBLE_PX,
            color=COL_LONG, opacity=0.75, line=dict(width=0.6, color='black')
        ),
        name='MML',
        hovertemplate='Traders: %{x}<br>Notional: %{y:.2f} USD bn<extra>MML</extra>'
    ))
    fig.add_trace(go.Scatter(
        x=x_mms, y=y_mms,
        mode='markers',
        marker=dict(
            size=BUBBLE_PX,
            color=COL_SHORT, opacity=0.75, line=dict(width=0.6, color='black')
        ),
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
            line=dict(color='white', width=7),
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line=dict(color=color, width=3),
            name=label, showlegend=True
        ))

    _add_notional_trend(x_mml, y_mml, COL_LONG,  'MML Trend')
    _add_notional_trend(x_mms, y_mms, COL_SHORT, 'MMS Trend')

    # Most Recent Week (identisch zu DP Indicator)
    fig.add_trace(go.Scatter(
        x=[x_mml.iloc[-1]], y=[y_mml.iloc[-1]],
        mode='markers',
        marker=dict(size=desired_max_px + 4, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week', legendgroup='recent', showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[x_mms.iloc[-1]], y=[y_mms.iloc[-1]],
        mode='markers',
        marker=dict(size=desired_max_px + 4, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week', legendgroup='recent', showlegend=False
    ))

    fig.update_layout(
        title='DP Notional Indicator',
        xaxis=dict(
            title='Number of Traders',
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        yaxis=dict(
            title='Long and Short $ Exposure (USD bn)',
            showgrid=True, gridcolor='LightGray', gridwidth=2,
            zeroline=True, zerolinecolor='black', zerolinewidth=1
        ),
        plot_bgcolor='white',
        legend_title='Trader Group',
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
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_dp_time(selected_market, start_date, end_date):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    # Konzentration (%) – identisch zum PPCI-Callback
    total_oi = pd.to_numeric(dff['Open Interest'], errors='coerce').replace(0, np.nan)
    dff['_y_mml'] =  100.0 * pd.to_numeric(dff['Managed Money Long'],  errors='coerce') / total_oi
    dff['_y_mms'] = -100.0 * pd.to_numeric(dff['Managed Money Short'], errors='coerce') / total_oi

    x_mml = pd.to_numeric(dff['MML Traders'], errors='coerce')
    x_mms = pd.to_numeric(dff['MMS Traders'], errors='coerce')

    fig = go.Figure()

    # Dummy-Traces für Shape-Legende (MML / MMS)
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(symbol='circle', color='gray', size=9),
        name='MML', legendgroup='shape_mml'
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='markers',
        marker=dict(symbol='triangle-down', color='gray', size=9),
        name='MMS', legendgroup='shape_mms'
    ))

    # Scatter-Traces: pro Jahr eine Farbe, MML=Kreis / MMS=Dreieck
    for year in sorted(dff['Year'].unique()):
        mask = dff['Year'] == year

        fig.add_trace(go.Scatter(
            x=x_mml[mask], y=dff['_y_mml'][mask],
            mode='markers',
            marker=dict(symbol='circle', size=12, opacity=0.75),
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
            marker=dict(symbol='triangle-down', size=12, opacity=0.75),
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
                line=dict(color='white', width=7),
                showlegend=False, hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=xs_arr, y=ys, mode='lines',
                line=dict(color=color, width=3),
                name=label, showlegend=True
            ))

        _add_time_trend(xs, x_mml, dff['_y_mml'], '#2c7fb8', 'MML Trend')
        _add_time_trend(xs, x_mms, dff['_y_mms'], '#7fcdbb', 'MMS Trend')

    # Most Recent Week (identisch zu DP Notional)
    desired_max_px = 18
    fig.add_trace(go.Scatter(
        x=[x_mml.iloc[-1]], y=[dff['_y_mml'].iloc[-1]],
        mode='markers',
        marker=dict(size=desired_max_px, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week', legendgroup='recent', showlegend=True
    ))
    fig.add_trace(go.Scatter(
        x=[x_mms.iloc[-1]], y=[dff['_y_mms'].iloc[-1]],
        mode='markers',
        marker=dict(size=desired_max_px, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week', legendgroup='recent', showlegend=False
    ))

    fig.update_layout(
        title='DP Time Indicator',
        xaxis=dict(
            title='Number of Traders',
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        yaxis=dict(
            title='Long and Short Concentration (%)',
            showgrid=True, gridcolor='LightGray', gridwidth=2,
            zeroline=True, zerolinecolor='black', zerolinewidth=1
        ),
        plot_bgcolor='white',
        legend_title='Year',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Price Indicator – Callback
# X = PMPU Long/Short Traders, Y = PMPU Long/Short OI
# Punktfarbe = Futures-Preis (Continuous Front-Month Proxy, Report Date)
# Trendlinie + Most-Recent-Week-Marker identisch zu DP Notional/Time Indicator
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-price-indicator-graph', 'figure'),
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('dp-price-radio', 'value')]
)
def update_dp_price(selected_market, start_date, end_date, pmpu_side):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if pmpu_side == 'PMPUL':
        x_col    = 'PMPUL Traders'
        y_col    = 'Producer/Merchant/Processor/User Long'
        x_title  = 'PMPU Number of Long Traders'
        y_title  = 'PMPU Long OI (Contracts)'
        pt_title = 'DP Price Indicator (PMPU Long)'
    else:
        x_col    = 'PMPUS Traders'
        y_col    = 'Producer/Merchant/Processor/User Short'
        x_title  = 'PMPU Number of Short Traders'
        y_title  = 'PMPU Short OI (Contracts)'
        pt_title = 'DP Price Indicator (PMPU Short)'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce')

    # Futures-Preis als Farbe (identisch zu PPCI: merge_asof, 7-Tage-Toleranz)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)
    price_col = _ppci_get_price_col(selected_market)

    if price_col and not df_futures_prices.empty and price_col in df_futures_prices.columns:
        prices = df_futures_prices[['Date', price_col]].dropna(subset=[price_col]).copy()
        prices = prices.rename(columns={'Date': '_pdate'}).sort_values('_pdate')
        dff = dff.sort_values('_date').reset_index(drop=True)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce')
        dff = pd.merge_asof(
            dff, prices,
            left_on='_date', right_on='_pdate',
            direction='backward',
            tolerance=pd.Timedelta(days=7)
        )
        color_vals    = pd.to_numeric(dff[price_col], errors='coerce')
        colorbar_title = 'Price (USD)'
    else:
        color_vals    = pd.Series([np.nan] * len(dff), index=dff.index)
        colorbar_title = 'Price (n/a)'

    # Hover
    dates_str = pd.to_datetime(dff['Date']).dt.strftime('%Y-%m-%d')
    hover_text = [
        f'Date: {d}<br>{x_title}: {x:.0f}<br>{y_title}: {y:,.0f}<br>Price: {c:.2f}'
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
        marker=dict(
            size=14,
            color=color_vals,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title=colorbar_title, thickness=15, len=0.75),
            opacity=0.85,
            line=dict(width=0.6, color='black')
        ),
        text=hover_text,
        hoverinfo='text',
        showlegend=False
    ))

    # Most Recent Week (identisch zu DP Notional/Time)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker=dict(size=18, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week'
    ))

    fig.update_layout(
        title=pt_title,
        xaxis=dict(
            title=x_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        plot_bgcolor='white',
        legend_title='Legend',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# DP Factor (VIX) – Callback
# X = MM Long/Short Traders, Y = MM Long/Short OI
# Punktfarbe = VIX-Wert (FRED via macro_by_date), merge_asof 7-Tage-Toleranz
# Struktur identisch zu DP Price Indicator (ohne Trendlinie)
# ---------------------------------------------------------------------------
@app.callback(
    Output('dp-vix-indicator-graph', 'figure'),
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('dp-vix-radio', 'value')]
)
def update_dp_vix(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col   = 'MML Traders'
        y_col   = 'MML Long OI'
        x_title = 'MM Number of Long Traders'
        y_title = 'MM Long OI (Contracts)'
        title   = 'DP Factor (VIX) Indicator – MML'
    else:
        x_col   = 'MMS Traders'
        y_col   = 'MMS Short OI'
        x_title = 'MM Number of Short Traders'
        y_title = 'MM Short OI (Contracts)'
        title   = 'DP Factor (VIX) Indicator – MMS'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # VIX-Wert als Farbe (FRED via df_macro, merge_asof identisch zu df_futures_prices)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_macro.empty and 'vix' in df_macro.columns:
        vix_df = df_macro[['Date', 'vix']].dropna(subset=['vix']).copy()
        vix_df = vix_df.rename(columns={'Date': '_vdate'}).sort_values('_vdate')
        dff = dff.sort_values('_date').reset_index(drop=True)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        dff = pd.merge_asof(
            dff, vix_df,
            left_on='_date', right_on='_vdate',
            direction='backward'
        )
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
        marker=dict(
            size=14,
            color=color_vals,
            colorscale='RdYlGn_r',   # hoher VIX = rot (Stress), tiefer VIX = grün
            showscale=True,
            colorbar=dict(title=colorbar_title, thickness=15, len=0.75),
            opacity=0.85,
            line=dict(width=0.6, color='black')
        ),
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
            line=dict(color='white', width=7),
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line=dict(color=col, width=3),
            name='Trend', showlegend=True
        ))

    # Most Recent Week (identisch zu DP Price Indicator)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker=dict(size=18, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week'
    ))

    fig.update_layout(
        title=title,
        xaxis=dict(
            title=x_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
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
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('dp-dxy-radio', 'value')]
)
def update_dp_dxy(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col   = 'MML Traders'
        y_col   = 'MML Long OI'
        x_title = 'MM Number of Long Traders'
        y_title = 'MM Long OI (Contracts)'
        title   = 'DP Factor (DXY) Indicator – MML'
    else:
        x_col   = 'MMS Traders'
        y_col   = 'MMS Short OI'
        x_title = 'MM Number of Short Traders'
        y_title = 'MM Short OI (Contracts)'
        title   = 'DP Factor (DXY) Indicator – MMS'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # DXY-Wert als Farbe (FRED via df_macro, merge_asof identisch zu VIX)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_macro.empty and 'usd_index' in df_macro.columns:
        dxy_df = df_macro[['Date', 'usd_index']].dropna(subset=['usd_index']).copy()
        dxy_df = dxy_df.rename(columns={'Date': '_ddate'}).sort_values('_ddate')
        dff = dff.sort_values('_date').reset_index(drop=True)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        dff = pd.merge_asof(
            dff, dxy_df,
            left_on='_date', right_on='_ddate',
            direction='backward'
        )
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
        marker=dict(
            size=14,
            color=color_vals,
            colorscale='RdYlGn',    # tiefer DXY = rot (schwacher Dollar), hoher DXY = grün
            showscale=True,
            colorbar=dict(title=colorbar_title, thickness=15, len=0.75),
            opacity=0.85,
            line=dict(width=0.6, color='black')
        ),
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
            line=dict(color='white', width=7),
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line=dict(color=col, width=3),
            name='Trend', showlegend=True
        ))

    # Most Recent Week (identisch zu VIX)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker=dict(size=18, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week'
    ))

    fig.update_layout(
        title=title,
        xaxis=dict(
            title=x_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
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
    [Input('market-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('dp-currency-radio', 'value')]
)
def update_dp_currency(selected_market, start_date, end_date, mm_side):
    dff = df_pivoted[
        (df_pivoted['Market Names'] == selected_market) &
        (df_pivoted['Date'] >= start_date) &
        (df_pivoted['Date'] <= end_date)
    ].copy().reset_index(drop=True)

    if dff.empty:
        return go.Figure()

    if mm_side == 'MML':
        x_col   = 'MML Traders'
        y_col   = 'MML Long OI'
        x_title = 'MM Number of Long Traders'
        y_title = 'MM Long OI (Contracts)'
        title   = 'DP Currency Indicator – USD/CHF (MML)'
    else:
        x_col   = 'MMS Traders'
        y_col   = 'MMS Short OI'
        x_title = 'MM Number of Short Traders'
        y_title = 'MM Short OI (Contracts)'
        title   = 'DP Currency Indicator – USD/CHF (MMS)'

    x_vals = pd.to_numeric(dff[x_col], errors='coerce')
    y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()

    # USD/CHF-Kurs als Farbe (via df_macro, merge_asof identisch zu DXY/VIX)
    dff['_date'] = pd.to_datetime(dff['Date']).dt.tz_localize(None)

    if not df_macro.empty and 'usd_chf' in df_macro.columns:
        chf_df = df_macro[['Date', 'usd_chf']].dropna(subset=['usd_chf']).copy()
        chf_df = chf_df.rename(columns={'Date': '_cdate'}).sort_values('_cdate')
        dff = dff.sort_values('_date').reset_index(drop=True)
        x_vals = pd.to_numeric(dff[x_col], errors='coerce')
        y_vals = pd.to_numeric(dff[y_col], errors='coerce').abs()
        dff = pd.merge_asof(
            dff, chf_df,
            left_on='_date', right_on='_cdate',
            direction='backward'
        )
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
        marker=dict(
            size=14,
            color=color_vals,
            colorscale='RdYlGn',    # tiefer USD/CHF = rot (schwacher Dollar), hoher = grün
            showscale=True,
            colorbar=dict(title=colorbar_title, thickness=15, len=0.75),
            opacity=0.85,
            line=dict(width=0.6, color='black')
        ),
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
            line=dict(color='white', width=7),
            showlegend=False, hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode='lines',
            line=dict(color=col, width=3),
            name='Trend', showlegend=True
        ))

    # Most Recent Week (identisch zu DXY/VIX)
    fig.add_trace(go.Scatter(
        x=[x_vals.iloc[-1]], y=[y_vals.iloc[-1]],
        mode='markers',
        marker=dict(size=18, color='black', line=dict(width=2, color='white')),
        name='Most Recent Week'
    ))

    fig.update_layout(
        title=title,
        xaxis=dict(
            title=x_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        yaxis=dict(
            title=y_title,
            showgrid=True, gridcolor='LightGray', gridwidth=2, zeroline=False
        ),
        plot_bgcolor='white',
        legend_title='Legend',
        height=600,
    )

    return fig


# ---------------------------------------------------------------------------
# Shapley-Owen Callback
# ---------------------------------------------------------------------------

_SHAPLEY_GROUP_LABELS = {
    'Δ PMPU Net': 'PMPU (Producer/Merchant)',
    'Δ SD Net':   'SD (Swap Dealer)',
    'Δ MM Net':   'MM (Managed Money)',
    'Δ OR Net':   'OR (Other Reportables)',
}
_SHAPLEY_COLORS = {
    'Δ PMPU Net': '#e6550d',
    'Δ SD Net':   '#3182bd',
    'Δ MM Net':   '#31a354',
    'Δ OR Net':   '#756bb1',
}


@app.callback(
    [Output('shapley-timeseries-chart', 'figure'),
     Output('shapley-bar-chart',        'figure'),
     Output('shapley-table',            'data'),
     Output('shapley-r2-info',          'children')],
    [Input('market-dropdown',     'value'),
     Input('date-picker-range',   'start_date'),
     Input('date-picker-range',   'end_date')],
)
def update_shapley(selected_market, start_date, end_date):
    """Aktualisiert alle drei Shapley-Owen-Elemente (Zeitreihe, Balken, Tabelle)."""

    empty_fig = go.Figure()
    empty_fig.update_layout(
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(
            text="Keine Shapley-Daten verfügbar für diesen Markt.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color='#888')
        )],
        height=400,
    )

    if selected_market not in _shapley_results:
        return empty_fig, empty_fig, [], ""

    df_s = _shapley_results[selected_market].copy()
    df_s['Date'] = pd.to_datetime(df_s['Date'])

    # Datumsfilter
    if start_date:
        df_s = df_s[df_s['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        df_s = df_s[df_s['Date'] <= pd.to_datetime(end_date)]

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
            line=dict(color=color, width=2),
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
        xaxis=dict(
            title='Datum',
            showgrid=True, gridcolor='LightGray',
        ),
        yaxis=dict(
            title='Shapley-Wert (φ)',
            showgrid=True, gridcolor='LightGray',
            zeroline=True, zerolinecolor='gray', zerolinewidth=1,
        ),
        plot_bgcolor='white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
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
        xaxis=dict(title='Händlergruppe'),
        yaxis=dict(
            title='Shapley-Wert (φ)',
            showgrid=True, gridcolor='LightGray',
            zeroline=True, zerolinecolor='gray', zerolinewidth=1,
        ),
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
        Output('dt-feature-importance', 'figure'),
    ],
    [Input('market-dropdown', 'value')]
)
def update_decision_tree(selected_market):
    """Rendert Prognosetext, Baum-Bild und Feature-Importance für den gewählten Markt."""
    if selected_market not in _dt_results:
        msg = html.P(
            f"Für '{selected_market}' sind keine Preisdaten verfügbar – kein Modell berechnet.",
            style={'color': '#888', 'fontStyle': 'italic'}
        )
        return msg, "", go.Figure()

    result    = _dt_results[selected_market]
    pred      = result["prediction"]
    proba     = result["proba"]
    last_date = pd.to_datetime(result["last_date"]).strftime('%d.%m.%Y')

    direction  = "steigende" if pred == 1 else "fallende"
    conf_pct   = proba[pred] * 100
    text_color = "#2e7d32" if pred == 1 else "#c62828"   # grün / rot

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

    tree_src  = render_tree_image(result)
    feat_fig  = dt_feature_importance_figure(result, selected_market)

    return prediction_card, tree_src, feat_fig


# Open browser automatically
if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run_server(debug=True, port=8051)
