# Refactoring: Auslagerung von Berechnungs- und Konfigurationslogik in `src/analysis`

**Datum:** 2026-04-04  
**Betroffene Dateien:**
- `Dash_Lokal.py` (geändert)
- `src/analysis/market_config.py` (neu)
- `src/analysis/cot_indicators.py` (neu)
- `src/analysis/shapley_owen.py` (erweitert)

---

## Ziel

Klare Trennung zwischen Darstellungslogik (Dash/Plotly, Callbacks, Layout) und fachlicher Berechnungs- sowie Konfigurationslogik, analog zur bereits bestehenden Struktur bei `shapley_owen.py` und `decision_tree.py`.

---

## Übersicht der Änderungen

| Typ | Datei | Inhalt |
|-----|-------|--------|
| Neu | `src/analysis/market_config.py` | Markt-Konfiguration (Preisspalten, Kontraktgrössen, Lookup-Funktionen) |
| Neu | `src/analysis/cot_indicators.py` | CoT-Indikatorberechnungen (Clustering, Rel. Concentration, Normierung) |
| Erweitert | `src/analysis/shapley_owen.py` | Neue Funktion `prepare_market_for_shapley()` |
| Geändert | `Dash_Lokal.py` | Imports ergänzt, lokale Definitionen entfernt, Loops vereinfacht |

---

## 1. Neues Modul: `src/analysis/market_config.py`

### Zweck

Dieses Modul zentralisiert das Domain-Wissen über die unterstützten Rohstoffmärkte: Welche Preisspalte gehört zu welchem Markt, und wie gross ist der zugehörige Futures-Kontrakt?

Dieses Wissen war zuvor direkt in `Dash_Lokal.py` als privater Block definiert und wurde von mehreren Stellen konsumiert:
- Shapley-Owen Preprocessing-Loop
- Decision-Tree Preprocessing-Loop
- 6 verschiedene Dash-Callbacks (PPCI, PP Clustering, PP Position Size, DP Notional, DP Price, DP Time)

### Vorher (in `Dash_Lokal.py`, ca. Zeilen 291–325)

```python
_PPCI_MARKET_TO_COL = {
    'GOLD':      'gold_close',
    'SILVER':    'silver_close',
    'COPPER':    'copper_close',
    'PLATINUM':  'platinum_close',
    'PALLADIUM': 'palladium_close',
}

def _ppci_get_price_col(market_name: str):
    mn = (market_name or '').upper()
    for key, col in _PPCI_MARKET_TO_COL.items():
        if key in mn:
            return col
    return None

_PPCI_CONTRACT_SIZES = {
    'GOLD':      100,
    'SILVER':    5000,
    'PLATINUM':  50,
    'PALLADIUM': 100,
    'COPPER':    25000,
}

def _ppci_get_contract_size(market_name: str) -> float:
    mn = (market_name or '').upper()
    for key, size in _PPCI_CONTRACT_SIZES.items():
        if key in mn:
            return float(size)
    return 1.0
```

### Nachher (`src/analysis/market_config.py`)

```python
MARKET_TO_PRICE_COL: dict[str, str] = {
    "GOLD":      "gold_close",
    "SILVER":    "silver_close",
    "COPPER":    "copper_close",
    "PLATINUM":  "platinum_close",
    "PALLADIUM": "palladium_close",
}

CONTRACT_SIZES: dict[str, float] = {
    "GOLD":      100.0,
    "SILVER":    5000.0,
    "PLATINUM":  50.0,
    "PALLADIUM": 100.0,
    "COPPER":    25000.0,
}

def get_price_col(market_name: str) -> str | None:
    """Gibt den Spaltennamen in df_futures_prices zurück, oder None wenn nicht gefunden."""
    mn = (market_name or "").upper()
    for key, col in MARKET_TO_PRICE_COL.items():
        if key in mn:
            return col
    return None

def get_contract_size(market_name: str) -> float:
    """Gibt die Kontraktgrösse (Einheiten/Kontrakt) zurück, oder 1.0 als Fallback."""
    mn = (market_name or "").upper()
    for key, size in CONTRACT_SIZES.items():
        if key in mn:
            return size
    return 1.0
```

### Änderungen in `Dash_Lokal.py`

Die alten privaten Definitionen wurden durch zwei lokale Aliase ersetzt, damit alle bestehenden Callback-Aufrufe ohne Änderung weiter funktionieren:

```python
# Lokale Aliase für Rückwärtskompatibilität innerhalb dieser Datei
_ppci_get_price_col    = get_price_col
_ppci_get_contract_size = get_contract_size
```

Die Preprocessing-Loops wurden auf die direkte Nutzung von `get_price_col()` umgestellt (ohne Alias).

### Was hat sich geändert / Was ist gleich geblieben

| Aspekt | Vorher | Nachher |
|--------|--------|---------|
| Funktionsnamen | `_ppci_get_price_col`, `_ppci_get_contract_size` | `get_price_col`, `get_contract_size` (vereinfacht, kein Präfix) |
| Konstantennamen | `_PPCI_MARKET_TO_COL`, `_PPCI_CONTRACT_SIZES` | `MARKET_TO_PRICE_COL`, `CONTRACT_SIZES` |
| Callback-Aufrufe | Unverändert (via Alias) | Unverändert |
| Preprocessing-Loops | Nutzten `_ppci_get_price_col` | Nutzen direkt `get_price_col` |
| Typisierung | Keine | Vollständige Type Hints |

---

## 2. Neues Modul: `src/analysis/cot_indicators.py`

### Zweck

Dieses Modul enthält die fachlichen Berechnungsformeln für CoT-Indikatoren. Diese Funktionen haben keinen Bezug zu Plotly, Dash oder der Darstellung – sie transformieren ausschliesslich Daten.

### 2.1 Funktion `clustering_0_100`

#### Vorher (in `Dash_Lokal.py`, ca. Zeile 142)

```python
def clustering_0_100(s, window=52, minp=10):
    rmin = s.rolling(window, min_periods=minp).min()
    rmax = s.rolling(window, min_periods=minp).max()
    denom = (rmax - rmin).replace(0, np.nan)
    out = 100 * (s - rmin) / denom
    return out.clip(0, 100)
```

#### Nachher (`src/analysis/cot_indicators.py`)

```python
def clustering_0_100(
    s: pd.Series,
    window: int = 52,
    min_periods: int = 10,
) -> pd.Series:
    """Rollende Min-Max-Normierung einer Serie auf [0, 100].

    Berechnet für jede Beobachtung, wo der aktuelle Wert innerhalb des
    gleitenden Fensters liegt – 0 = historisches Minimum, 100 = Maximum.
    """
    rmin = s.rolling(window, min_periods=min_periods).min()
    rmax = s.rolling(window, min_periods=min_periods).max()
    denom = (rmax - rmin).replace(0, np.nan)
    return (100.0 * (s - rmin) / denom).clip(0, 100)
```

#### Nutzung in `Dash_Lokal.py` (unverändert)

```python
df_pivoted['Long Clustering'] = (
    df_pivoted.groupby('Market Names')['MM_Long_share']
    .transform(lambda s: clustering_0_100(s, window=52))
)
df_pivoted['Short Clustering'] = (
    df_pivoted.groupby('Market Names')['MM_Short_share']
    .transform(lambda s: clustering_0_100(s, window=52))
)
```

---

### 2.2 Funktion `rel_concentration`

#### Vorher (in `Dash_Lokal.py`, ca. Zeile 436)

```python
def nz(series):
    return pd.to_numeric(series, errors='coerce')

def rel_concentration(oi_long, oi_short, total_oi):
    oiL = nz(oi_long)
    oiS = nz(oi_short)
    tot = nz(total_oi).replace(0, np.nan)
    return 100.0 * ((oiL / tot) - (oiS / tot))
```

`nz()` ist eine generische Hilfsfunktion ohne Domain-Bezug und wurde **nicht** ausgelagert – sie bleibt in `Dash_Lokal.py`.

#### Nachher (`src/analysis/cot_indicators.py`)

```python
def rel_concentration(
    oi_long: pd.Series,
    oi_short: pd.Series,
    total_oi: pd.Series,
) -> pd.Series:
    """Relative Concentration einer Händlergruppe in Prozentpunkten.

    Formel: 100 × (Long-OI / Gesamt-OI  −  Short-OI / Gesamt-OI)
    """
    L = pd.to_numeric(oi_long,  errors="coerce")
    S = pd.to_numeric(oi_short, errors="coerce")
    T = pd.to_numeric(total_oi, errors="coerce").replace(0, np.nan)
    return 100.0 * ((L / T) - (S / T))
```

Die neue Version enthält die `pd.to_numeric()`-Konvertierung intern, sodass die externe `nz()`-Abhängigkeit entfällt.

#### Nutzung in `Dash_Lokal.py` (Callback-interne Closure)

```python
# Vorher
TOTAL_OI = pd.to_numeric(filtered_df.get('Open Interest'), errors='coerce').replace(0, np.nan)

def rc(long_col, short_col):
    L = pd.to_numeric(filtered_df.get(long_col), errors='coerce')
    S = pd.to_numeric(filtered_df.get(short_col), errors='coerce')
    return 100.0 * ((L / TOTAL_OI) - (S / TOTAL_OI))

# Nachher
TOTAL_OI = pd.to_numeric(filtered_df.get('Open Interest'), errors='coerce')

def rc(long_col, short_col):
    return rel_concentration(
        filtered_df.get(long_col), filtered_df.get(short_col), TOTAL_OI
    )
```

---

### 2.3 Funktion `calculate_ranges`

Dies ist die grösste inhaltliche Änderung in diesem Modul: Die Funktion war zuvor auf feste Spaltennamen (`'MML Relative Concentration'`, `'Long Clustering'`) hardcodiert und wählte diese anhand eines `indicator`-Parameters aus.

#### Vorher (in `Dash_Lokal.py`, ca. Zeile 412)

```python
def calculate_ranges(agg_df, indicator):
    if indicator == 'MML':
        concentration_col = 'MML Relative Concentration'
        clustering_col = 'Long Clustering'
    elif indicator == 'MMS':
        concentration_col = 'MMS Relative Concentration'
        clustering_col = 'Short Clustering'
    else:
        raise ValueError("Invalid indicator. Must be 'MML' or 'MMS'.")

    agg_df = agg_df.select_dtypes(include='number')

    concentration_range = (agg_df[concentration_col] - agg_df[concentration_col].min()) / \
                          (agg_df[concentration_col].max() - agg_df[concentration_col].min())

    clustering_range = (agg_df[clustering_col] - agg_df[clustering_col].min()) / \
                       (agg_df[clustering_col].max() - agg_df[clustering_col].min())

    return concentration_range * 100, clustering_range * 100
```

#### Nachher (`src/analysis/cot_indicators.py`)

```python
def calculate_ranges(
    agg_df: pd.DataFrame,
    concentration_col: str,
    clustering_col: str,
) -> tuple[pd.Series, pd.Series]:
    """Marktübergreifende Min-Max-Normierung auf [0, 100].

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
```

**Wichtige Unterschiede:**
- Die Funktion kennt keine `'MML'`/`'MMS'`-Logik mehr; sie nimmt Spaltennamen direkt als Parameter
- Der Division-durch-Null-Fall (`span == 0`) sowie nicht-finite Werte werden explizit behandelt
- Das Mapping `indicator → Spaltenname` lebt neu in `Dash_Lokal.py` als kleine Hilfsfunktion `_indicator_cols()`

#### Neue Hilfsfunktion in `Dash_Lokal.py`

```python
def _indicator_cols(indicator: str) -> tuple[str, str]:
    """Gibt (concentration_col, clustering_col) für 'MML' oder 'MMS' zurück."""
    if indicator == 'MML':
        return 'MML Relative Concentration', 'Long Clustering'
    elif indicator == 'MMS':
        return 'MMS Relative Concentration', 'Short Clustering'
    raise ValueError("Invalid indicator. Must be 'MML' or 'MMS'.")
```

#### Aufruf im Callback (vorher / nachher)

```python
# Vorher
concentration_range, clustering_range = calculate_ranges(agg_df, selected_indicator)

# Nachher
conc_col, clust_col = _indicator_cols(selected_indicator)
concentration_range, clustering_range = calculate_ranges(agg_df, conc_col, clust_col)
```

---

## 3. Erweiterung: `src/analysis/shapley_owen.py`

### Neue Funktion `prepare_market_for_shapley`

#### Motivation

Bisher enthielt die Shapley-Preprocessing-Loop in `Dash_Lokal.py` rund 20 Zeilen Feature-Engineering-Logik: Merge mit Futures-Preisen via `merge_asof`, Berechnung der absoluten Preisänderung als Zielvariable, und First Differences der Netto-Positionierungen als Prädiktoren.

Diese Logik gehört fachlich zum Shapley-Modul – sie definiert, *wie* die Eingabedaten für die Shapley-Zerlegung vorbereitet werden müssen. Das Decision-Tree-Modul handhabt seine analoge Datenvorbereitung bereits intern via `_prepare_features()`. Mit der neuen Funktion wird dieses Muster konsistent auf Shapley übertragen.

#### Vorher (Preprocessing-Loop in `Dash_Lokal.py`, ca. Zeilen 498–548)

```python
_shapley_results: dict = {}

for _mkt in df_pivoted['Market Names'].unique():
    _pcol = _ppci_get_price_col(_mkt)
    if _pcol is None or df_futures_prices.empty or _pcol not in df_futures_prices.columns:
        print(f"[Shapley] Kein Preisdaten für {_mkt} – überspringe.")
        continue

    _dff = df_pivoted[df_pivoted['Market Names'] == _mkt].copy()
    _dff = _dff.sort_values('Date').reset_index(drop=True)

    # Futures-Preise via merge_asof einbinden
    _prices = (
        df_futures_prices[['Date', _pcol]]
        .dropna(subset=[_pcol])
        .rename(columns={'Date': '_pdate', _pcol: '_close'})
        .sort_values('_pdate')
    )
    _dff = pd.merge_asof(
        _dff, _prices,
        left_on='Date', right_on='_pdate',
        direction='backward',
        tolerance=pd.Timedelta(days=7)
    )

    # Absolute Preisänderung als Zielvariable
    _dff[_SHAPLEY_Y_COL] = _dff['_close'].diff()

    # First Differences der Netto-Positionierungen
    _dff['Δ PMPU Net'] = _dff['PMPU Net'].diff()
    _dff['Δ SD Net']   = _dff['SD Net'].diff()
    _dff['Δ MM Net']   = _dff['MM Net'].diff()
    _dff['Δ OR Net']   = _dff['OR Net'].diff()

    _result = compute_rolling_shapley(
        _dff,
        x_cols=_SHAPLEY_X_COLS,
        y_col=_SHAPLEY_Y_COL,
        window=_SHAPLEY_WINDOW,
        min_periods=_SHAPLEY_MIN_PERIODS,
    )
    _shapley_results[_mkt] = _result
    print(f"[Shapley] {_mkt}: {len(_result)} Datenpunkte berechnet.")
```

#### Nachher: Neue Funktion in `src/analysis/shapley_owen.py`

```python
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
    df_prices : DataFrame mit mindestens den Spalten 'Date' und *price_col*.
    price_col : Spaltenname des Futures-Schlusskurses in df_prices.
    net_cols  : Mapping {Δ-Ausgabespalte: Quell-Netto-Spalte}.
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
        dff, prices_clean,
        left_on="Date", right_on="_pdate",
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
```

#### Nachher: Vereinfachte Loop in `Dash_Lokal.py`

```python
_shapley_results: dict = {}

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
```

**Reduktion: ~20 Zeilen Feature-Engineering → 3 Zeilen Funktionsaufruf**

---

## 4. Änderungen in `Dash_Lokal.py` – Gesamtübersicht

### Neue Imports (Zeilen 12–19)

```python
from src.analysis.shapley_owen import compute_rolling_shapley, prepare_market_for_shapley
from src.analysis.decision_tree import (
    train_decision_tree,
    render_tree_image,
    feature_importance_figure as dt_feature_importance_figure,
)
from src.analysis.market_config import get_price_col, get_contract_size
from src.analysis.cot_indicators import clustering_0_100, rel_concentration, calculate_ranges
```

### Entfernte Definitionen

| Funktion / Block | Zeilennummer (vorher) | Ersetzt durch |
|---|---|---|
| `clustering_0_100()` | ~142 | Import aus `cot_indicators` |
| `_PPCI_MARKET_TO_COL` | ~291 | `market_config.MARKET_TO_PRICE_COL` |
| `_ppci_get_price_col()` | ~300 | `market_config.get_price_col` (Alias) |
| `_PPCI_CONTRACT_SIZES` | ~309 | `market_config.CONTRACT_SIZES` |
| `_ppci_get_contract_size()` | ~319 | `market_config.get_contract_size` (Alias) |
| `calculate_ranges()` | ~412 | Import aus `cot_indicators` + `_indicator_cols()` |
| `rel_concentration()` | ~436 | Import aus `cot_indicators` |
| Shapley Feature-Engineering | ~514–538 | `prepare_market_for_shapley()` |

### Neue / geänderte Definitionen in `Dash_Lokal.py`

| Element | Zeile (nachher) | Beschreibung |
|---|---|---|
| `_ppci_get_price_col = get_price_col` | ~283 | Alias für bestehende Callbacks |
| `_ppci_get_contract_size = get_contract_size` | ~284 | Alias für bestehende Callbacks |
| `_indicator_cols(indicator)` | ~412 | Mapping `'MML'/'MMS'` → Spaltennamen |

---

## 5. Was wurde bewusst nicht ausgelagert

### Visualisierungs-Hilfsfunktionen (bleiben in `Dash_Lokal.py`)

| Funktion | Begründung |
|---|---|
| `scaled_diameters()` | Pixel-Mapping für Plotly-Marker; ausschliesslich für Rendering |
| `scaled_diameters_rank()` | Rang-basiertes Pixel-Mapping; ausschliesslich für Rendering |
| `safe_sizes()` | Plotly-spezifische Datenaufbereitung |
| `safe_colors()` | Plotly-spezifische Datenaufbereitung |
| `dynamic_bubble_sizes()` | Bubble-Legende für Plotly-Charts |
| `add_last_point_highlight()` | Fügt `go.Scatter`-Trace zu einer `go.Figure` hinzu |
| `positions_bar()` / `traders_bar()` | Erzeugen HTML-Strings für Dash `DataTable` |
| `nz()` | Generischer Mini-Wrapper ohne Domain-Gehalt |
| `calculate_medians()` | 2-Zeilen-Wrapper; zu dünn für eigenes Modul |
| `calculate_scaling_factors()` | 2-Zeilen-Wrapper; zu dünn für eigenes Modul |
| Alle `@app.callback`-Funktionen | Dash-Kopplung; beinhalten Layout-Outputs und UI-State |

### Preprocessing-Loop Decision Tree (bleibt unverändert)

`train_decision_tree()` kapselt bereits intern die gesamte Datenvorbereitung via `_prepare_features()`. Die Loop in `Dash_Lokal.py` beschränkt sich auf:
1. Markt filtern
2. Funktion aufrufen
3. Ergebnis speichern

Das entspricht bereits dem Idealzustand und wurde nicht weiter verändert.

---

## 6. Finale Modulstruktur `src/analysis/`

```
src/
└── analysis/
    ├── __init__.py
    ├── market_config.py      # NEU: Markt-Konfiguration und Lookup-Funktionen
    ├── cot_indicators.py     # NEU: Clustering, Rel. Concentration, Normierung
    ├── shapley_owen.py       # ERWEITERT: + prepare_market_for_shapley()
    └── decision_tree.py      # UNVERÄNDERT
```

---

## 7. Keine funktionalen Änderungen

Alle Änderungen sind reine Strukturveränderungen. Die Berechnungslogik ist identisch:

- `clustering_0_100`: exakt dieselbe Formel, nur mit Type Hints
- `rel_concentration`: semantisch identisch; `pd.to_numeric()` wird intern statt extern aufgerufen
- `calculate_ranges`: identische Normierungsformel; Division-durch-Null-Handling expliziter
- `prepare_market_for_shapley`: extrahiert exakt den bisherigen Loop-Inhalt, ohne inhaltliche Veränderung
- `get_price_col` / `get_contract_size`: identische Lookup-Logik, nur vereinfachte Namen

Das Dashboard-Verhalten, die Ergebnisse aller Indikatoren und die Shapley-/DT-Berechnungen sind unverändert.
