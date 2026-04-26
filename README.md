# CoT Dashboard – InfluxDB V3

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Dash](https://img.shields.io/badge/Dash-2.18-green.svg)
![InfluxDB](https://img.shields.io/badge/InfluxDB-V3-orange.svg)

Interaktives Multi-Page-Dashboard zur Analyse von **Commitment of Traders (CoT)**-Daten der CFTC. Daten werden in einer lokalen InfluxDB v3 Core-Instanz gespeichert und mit Plotly Dash visualisiert.

---

## Features

- **Multi-Page-Dashboard**: Separate Seiten je Indikatorgruppe (Positionierung, Dry Powder, OB/OS, Decision Tree, Shapley-Analyse)
- **InfluxDB v3 Core**: SQL-basierte Zeitreihendatenbank als lokales Backend
- **Multi-Source-Daten**: CFTC CoT-Reports (Socrata), Futures-Preise (Databento), Rohöl-Lagerdaten (EIA), Marktpreise (yfinance)
- **ML-Analyse**: Scikit-learn Decision Trees, SHAP/Shapley-Owen Feature Importance
- **Responsive Layout**: Dash Bootstrap Components

---

## Technologie-Stack

| Bereich | Technologie |
|---|---|
| Backend | Python 3.12 |
| Web Framework | Dash 2.18, Flask 3.0 |
| Datenbank | InfluxDB v3 Core (SQL) |
| Datenverarbeitung | Pandas, NumPy, SciPy, Numba |
| Visualisierung | Plotly, Dash Bootstrap Components, Matplotlib |
| ML / Analyse | scikit-learn, SHAP, Keras |
| Datenquellen | Socrata (CFTC), Databento, EIA, yfinance |
| Deployment | Gunicorn (Linux/Mac) |

---

## Voraussetzungen

- Python 3.12+
- Laufende InfluxDB v3 Core-Instanz (Standard: `http://localhost:8181`)
- API-Keys: Databento, Socrata App Token, EIA API Key

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/sinzb1/CoT-Dashboard_InfluxDB-V3.git
cd CoT-Dashboard_InfluxDB-V3
```

### 2. Virtuelle Umgebung erstellen

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Dependencies installieren

```bash
pip install -r requirements.txt
```

### 4. Umgebungsvariablen konfigurieren

Kopiere `.env.example` zu `.env` und trage deine Credentials ein:

```bash
cp .env.example .env            # Linux/Mac
copy .env.example .env          # Windows
```

```env
# InfluxDB v3
INFLUXDB_HOST=http://localhost:8181
INFLUXDB_TOKEN=your_token_here
INFLUXDB_DATABASE=CoT-Data

# Databento (Futures-Preise)
DATABENTO_API_KEY=your_databento_key

# Socrata (CFTC CoT-Reports)
SOCRATA_APP_TOKEN=your_socrata_token

# EIA (Rohöl-Lagerdaten)
EIA_API_KEY=your_eia_key
```

---

## Verwendung

### Daten laden und in InfluxDB schreiben

```bash
python Influx.py
```

### Dashboard starten

```bash
python Dash_Lokal.py
```

Dashboard aufrufbar unter: **http://127.0.0.1:8051/**

Eine vollständige Schritt-für-Schritt-Anleitung (inkl. InfluxDB-Installation) findet sich in [SETUP_GUIDE.md](SETUP_GUIDE.md).

---

## Projektstruktur

```
DIFA_influxv3/
├── Dash_Lokal.py               # Dashboard-Applikation (Einstiegspunkt)
├── Influx.py                   # Daten laden & in InfluxDB schreiben
├── app.py                      # Minimaler Dash-Prototyp (Legacy)
├── requirements.txt
├── .env                        # Credentials (nicht im Repo)
├── .env.example                # Vorlage für Umgebungsvariablen
├── config/
│   └── config.json             # App-Konfiguration (Märkte, Parameter)
├── pages/                      # Dash-Seiten (Multi-Page)
│   ├── grundlegende.py         # Grundlegende CoT-Indikatoren
│   ├── positioning_price.py    # Positionierung & Preis (PP/DP)
│   ├── dry_powder.py           # Dry-Powder-Indikator
│   ├── obos.py                 # Overbought/Oversold-Indikator
│   ├── decision_tree.py        # Decision-Tree-Analyse
│   └── shapley.py              # Shapley-Owen Feature Importance
├── src/
│   ├── analysis/               # Analyse- & Indikator-Module
│   │   ├── cot_indicators.py
│   │   ├── decision_tree.py
│   │   ├── market_config.py
│   │   ├── obos_indicators.py
│   │   ├── shapley_owen.py
│   │   ├── feature_engineering.py
│   │   ├── bubble_sizing.py
│   │   └── data_merging.py
│   ├── clients/                # API-Clients
│   │   ├── databento_client.py
│   │   ├── eia_client.py
│   │   ├── socrata_client.py
│   │   └── yfinance_client.py
│   ├── data_loading/           # InfluxDB-Datenbankzugriff
│   │   └── influxdb_loader.py
│   ├── mappings/               # Daten-Mappings & Spaltenzuordnungen
│   │   └── categories_of_traders_column_map.py
│   └── services/               # Business-Logic / ETL-Services
│       ├── databento_continuous_service.py
│       ├── eia_petroleum_service.py
│       ├── futures_price_service.py
│       ├── macro_price_service.py
│       └── trades_category_service.py
└── docs_lokal/                 # Weiterführende Dokumentation (18 Dateien)
    ├── MIGRATION_GUIDE.md
    └── ...
```

---

## Datenquellen

| Quelle | Inhalt | Client |
|---|---|---|
| [CFTC via Socrata](https://publicreporting.cftc.gov/) | CoT-Reports (Disaggregated, Legacy, TFF) | `socrata_client.py` |
| [Databento](https://databento.com/) | Kontinuierliche Futures-Preise (2nd/3rd Nearby) | `databento_client.py` |
| [EIA](https://www.eia.gov/opendata/) | Rohöl-Lagerbestände (WTI) | `eia_client.py` |
| [yfinance](https://github.com/ranaroussi/yfinance) | Marktpreise & Makro-Daten (VIX, USD Index, USD/CHF) | `yfinance_client.py` |

---

## Datenpipeline

Die Pipeline (`Influx.py`) läuft in 5 sequenziellen Schritten und ist idempotent – sie löscht vorhandene Daten im Zeitfenster und schreibt sie neu:

| Schritt | Quelle | Measurement in InfluxDB |
|---|---|---|
| 1 | CFTC CoT-Reports (Socrata) | `cot_data` |
| 2 | Makrodaten: VIX, USD Index, USD/CHF (yfinance) | `macro_by_date` |
| 3 | Futures-Frontmonats-Preise (yfinance) | `futures_prices` |
| 4 | EIA Rohöl-Lagerbestände | `eia_petroleum_stocks` |
| 5 | Deferred Futures 2nd/3rd Nearby (Databento) | `futures_deferred_prices` |

---

## Migration

Dieses Projekt wurde von **InfluxDB v2 (Flux)** auf **InfluxDB v3 Core (SQL)** migriert:

- **Client**: `influxdb-client` → `influxdb3-python`
- **Query-Sprache**: Flux → SQL
- Details: siehe `docs_lokal/MIGRATION_GUIDE.md`
