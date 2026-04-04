# Refactoring: Mehrseiten-Dashboard

**Datum:** 2026-04-04  
**Betrifft:** `Dash_Lokal.py`, neues Verzeichnis `pages/`

---

## Ausgangslage

Das CoT-Dashboard war ursprünglich als **eine einzige, lange Seite** implementiert. Alle Indikatoren, Grafiken und Beschreibungen wurden in einem einzigen `app.layout`-Block untereinander gereiht. Dieser Block umfasste rund **78'000 Zeichen reinen Layout-Code** (Zeilen 497–2202 im Original).

Die wichtigsten Nachteile dieser Struktur:

- Schwer wartbar: Jede Änderung erforderte mühsames Scrollen durch den riesigen Layout-Block
- Schlechte Übersichtlichkeit für den Nutzer: Alle Themen waren auf einer einzigen Scroll-Seite gemischt
- Kein klarer thematischer Fokus: DP-Indikatoren, PP-Indikatoren, Shapley und Decision Tree lagen alle durcheinander

---

## Ziel des Refactorings

1. Aufteilung des Dashboards in **fünf thematische Seiten**
2. Saubere Navigation über **horizontale Tabs**
3. **Globale Filter** (Markt, Zeitraum) sichtbar und wirksam auf allen Seiten
4. Saubere Modulstruktur durch Auslagerung in ein `pages/`-Verzeichnis

---

## Neue Dateistruktur

```
DIFA_influxv3/
├── Dash_Lokal.py               ← Hauptdatei (Daten, App, Callbacks, globale Filter)
├── pages/
│   ├── __init__.py
│   ├── grundlegende.py         ← Seite 1: Grundlegende Indikatoren
│   ├── dry_powder.py           ← Seite 2: Dry Powder Indikatoren
│   ├── positioning_price.py    ← Seite 3: Positioning Price Indikatoren
│   ├── shapley.py              ← Seite 4: Shapley-Owen Zerlegung
│   └── decision_tree.py        ← Seite 5: Preisprognose (Entscheidungsbaum)
└── docs/
    └── multipage_dashboard_refactoring.md  ← dieses Dokument
```

---

## Seitenaufteilung im Detail

### Seite 1 – Grundlegende Indikatoren (`pages/grundlegende.py`)

Enthält die grundlegenden Übersichts- und Positionierungsindikatoren:

| Abschnitt | Grafik-ID(s) |
|-----------|--------------|
| Übersichtstabelle (Market Overview) | `overview-table` |
| Clustering Indicator | `long-clustering-graph`, `short-clustering-graph` |
| Position Size Indicator – Producer/Merchant | `pmpu-long-position-size-graph`, `pmpu-short-position-size-graph` |
| Position Size Indicator – Swap Dealers | `sd-long-position-size-graph`, `sd-short-position-size-graph` |
| Position Size Indicator – Money Managers | `long-position-size-graph`, `short-position-size-graph` |
| Position Size Indicator – Other Reportables | `or-long-position-size-graph`, `or-short-position-size-graph` |

---

### Seite 2 – Dry Powder Indikatoren (`pages/dry_powder.py`)

Enthält alle DP-Indikatoren (13 Abschnitte):

| Abschnitt | Grafik-ID(s) | Steuerelement |
|-----------|--------------|---------------|
| DP Indicator | `dry-powder-indicator-graph` | – |
| DP Notional Indicator | `dp-notional-indicator-graph` | – |
| DP Time Indicator | `dp-time-indicator-graph` | – |
| DP Price Indicator | `dp-price-indicator-graph` | `dp-price-radio` (PMPUL / PMPUS) |
| DP Factor (VIX) Indicator | `dp-vix-indicator-graph` | `dp-vix-radio` (MML / MMS) |
| DP Factor (DXY) Indicator | `dp-dxy-indicator-graph` | `dp-dxy-radio` (MML / MMS) |
| DP Currency Indicator (USD/CHF) | `dp-currency-indicator-graph` | `dp-currency-radio` (MML / MMS) |
| DP Relative Concentration Indicator | `dp-relative-concentration-graph` | – |
| DP Seasonal Indicator | `dp-seasonal-indicator-graph` | – |
| DP Net Indicator with Median | `dp-net-indicators-graph` | – |
| DP Position Size Indicator | `dp-position-size-indicator` | `mm-radio` (MML / MMS) |
| DP Hedging Indicator | `hedging-indicator-graph` | `trader-group-radio` (MML / MMS) |
| DP Concentration / Clustering Indicator | `dp-concentration-clustering-graph` | `concentration-clustering-date-picker-range`, `concentration-clustering-radio` |

> **Hinweis:** Der DP Concentration/Clustering Indicator hat einen **eigenen, lokalen DatePicker**, da er alle Märkte gleichzeitig auswertet und einen separaten Analysezeitraum benötigt.

---

### Seite 3 – Positioning Price Indikatoren (`pages/positioning_price.py`)

| Abschnitt | Grafik-ID(s) | Steuerelement |
|-----------|--------------|---------------|
| PP Concentration Indicator | `positioning-price-concentration-graph` | `ppci-mm-radio` (MML / MMS) |
| PP Clustering Indicator | `pp-clustering-graph` | `ppci-clustering-radio` (MML / MMS) |
| PP Position Size Indicator | `pp-position-size-graph` | `ppci-position-size-radio` (MML / MMS) |

---

### Seite 4 – Shapley-Owen Zerlegung (`pages/shapley.py`)

| Abschnitt | Grafik-/Tabellen-ID(s) |
|-----------|------------------------|
| Zeitverlauf der Shapley-Werte (52-Wochen-Fenster) | `shapley-timeseries-chart` |
| Balkendiagramm (aktuellste Shapley-Werte) | `shapley-bar-chart` |
| Tabelle (aktuellste Shapley-Werte) | `shapley-table` |
| R²-Infotext | `shapley-r2-info` |

---

### Seite 5 – Preisprognose / Entscheidungsbaum (`pages/decision_tree.py`)

| Abschnitt | ID |
|-----------|----|
| Prognosetext | `dt-prediction-text` |
| Entscheidungsbaum-Grafik | `dt-tree-image` |
| Feature Importance | `dt-feature-importance` |

---

## Globale Filterlogik

### Architekturentscheidung

Die globalen Filter befinden sich **oberhalb der Tabs** in `Dash_Lokal.py` und sind damit auf jeder Seite sichtbar. Es werden **die selben Komponenten-IDs** verwendet, die alle Callbacks bereits vorher referenziert haben:

| Filter | Komponenten-ID | Typ |
|--------|---------------|-----|
| Markt | `market-dropdown` | `dcc.Dropdown` |
| Zeitraum | `date-picker-range` | `dcc.DatePickerRange` |

### Warum keine `dcc.Store`-Lösung?

Da alle 14 Callbacks bereits dieselben IDs (`market-dropdown`, `date-picker-range`) als Inputs verwenden, hätte ein `dcc.Store`-basierter Ansatz **zusätzliche Sync-Callbacks** erfordert. Die gewählte Lösung ist simpler und hat denselben Effekt:

- Ein Wechsel des Markts auf einer Seite gilt sofort für alle Seiten
- Der Zeitraum bleibt beim Tab-Wechsel erhalten (die Komponenten existieren nur einmal im DOM)
- Kein Callback-Overhead

### Rendering-Strategie

Alle Tabs werden beim **Start vollständig gerendert** (kein Lazy-Loading). Das bedeutet:

- Alle Grafiken sind sofort berechnet, wenn man zu einem Tab wechselt
- Kein Ladezustand bei Tab-Wechsel
- Callbacks werden beim Start für alle Grafiken gleichzeitig ausgelöst

---

## Änderungen an `Dash_Lokal.py`

### 1. Neue Imports (Zeilen 4–8)

```python
from pages.grundlegende import layout as grundlegende_layout
from pages.dry_powder import layout as dry_powder_layout
from pages.positioning_price import layout as positioning_price_layout
from pages.shapley import layout as shapley_layout
from pages.decision_tree import layout as decision_tree_layout
```

### 2. Neues `app.layout`

Der frühere Layout-Block (~78'000 Zeichen) wurde ersetzt durch eine kompakte Struktur (~2'000 Zeichen):

```python
app.layout = html.Div([
    dbc.Navbar(...)           # Titel-Leiste
    dbc.Container([
        dbc.Row([...]),       # Globale Filter: Markt + Zeitraum
        html.Hr(),
        dbc.Tabs([
            dbc.Tab(grundlegende_layout(),      label="Grundlegende Indikatoren"),
            dbc.Tab(dry_powder_layout(),        label="Dry Powder Indikatoren"),
            dbc.Tab(positioning_price_layout(), label="Positioning Price Indikatoren"),
            dbc.Tab(shapley_layout(),           label="Shapley-Owen Zerlegung"),
            dbc.Tab(decision_tree_layout(),     label="Preisprognose (Entscheidungsbaum)"),
        ]),
    ]),
    html.Footer(...)          # Footer über volle Breite
])
```

### 3. Callback-Anpassung: `update_concentration_clustering_graph`

Der DP Concentration/Clustering Callback wurde minimal angepasst, damit er mit einem uninitialisierten lokalen DatePicker umgehen kann:

```python
# Vorher
filtered_df = df_pivoted[(df_pivoted['Date'] >= start_date) & ...]

# Nachher
_sd = start_date if start_date is not None else default_start_date
_ed = end_date   if end_date   is not None else default_end_date
filtered_df = df_pivoted[(df_pivoted['Date'] >= _sd) & ...]
```

### 4. Navbar und Footer

| Element | Vorher | Nachher |
|---------|--------|---------|
| Navbar | `dbc.NavbarSimple` (Titel zentriert, kleine Schrift) | `dbc.Navbar` mit `html.Span` (Titel linksbündig, `1.6rem`, `font-weight: 600`) |
| Footer | Im Container, nur Text (`text-center`) | Ausserhalb des Containers, volle Breite, blauer Hintergrund (`#0d6efd`), weisse Schrift |

---

## Struktur der Page-Module

Jedes Modul in `pages/` folgt demselben Muster:

```python
from dash import dcc, html, dash_table   # nur was nötig
import dash_bootstrap_components as dbc

def layout():
    return html.Div([
        # ... dbc.Row / dbc.Col / dcc.Graph / dbc.Accordion ...
    ])
```

- **Keine Datenzugriffe** in den Page-Modulen — alle Daten (`df_pivoted`, `df_futures_prices` usw.) bleiben in `Dash_Lokal.py`
- **Keine Callbacks** in den Page-Modulen — alle Callbacks bleiben in `Dash_Lokal.py`
- Die Funktionen geben ein `html.Div`-Objekt zurück, das direkt als `children` in `dbc.Tab` eingesetzt wird

---

## Nicht verändert

Folgende Teile des Codes blieben **vollständig unverändert**:

- Alle 14 Callbacks (Inputs, Outputs, Logik)
- Datenlade-Code (InfluxDB, Futures-Preise, Macro-Daten, yfinance)
- Datenvorverarbeitung und alle berechneten Spalten
- Hilfsfunktionen (`positions_bar`, `traders_bar`, `scaled_diameters`, usw.)
- Shapley-Owen und Decision-Tree Vorberechnungen
- Alle Graph-IDs

---

## Zusammenfassung

| Kennzahl | Vorher | Nachher |
|----------|--------|---------|
| Layout-Zeilen in `Dash_Lokal.py` | ~1'700 | ~55 |
| Anzahl Dateien | 1 | 7 |
| Seiten | 1 (Scroll) | 5 (Tabs) |
| Globale Filter | Im Seiteninhalt versteckt | Permanent sichtbar über den Tabs |
| Callback-Änderungen | – | 1 (Null-Behandlung) |
