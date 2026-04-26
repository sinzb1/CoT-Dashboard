# Setup Guide – CoT Dashboard

Schritt-für-Schritt-Anleitung, um das Dashboard lokal unter Windows zum Laufen zu bringen.

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Repository & Python-Umgebung](#2-repository--python-umgebung)
3. [InfluxDB v3 Core installieren](#3-influxdb-v3-core-installieren)
4. [InfluxDB v3 Core starten & Token erstellen](#4-influxdb-v3-core-starten--token-erstellen)
5. [Umgebungsvariablen konfigurieren](#5-umgebungsvariablen-konfigurieren)
6. [Daten laden (Pipeline)](#6-daten-laden-pipeline)
7. [Dashboard starten](#7-dashboard-starten)
8. [Troubleshooting](#8-troubleshooting)
9. [Weiterführende Dokumentation](#9-weiterführende-dokumentation)

---

## 1. Voraussetzungen

### Software

- **Python 3.12+** – [python.org/downloads](https://www.python.org/downloads/)
  - Bei der Installation: **"Add Python to PATH"** aktivieren
- **Git** – [git-scm.com](https://git-scm.com/)
- **InfluxDB v3 Core** – wird in Schritt 3 installiert

### API-Keys (alle kostenlos registrierbar)

| Dienst | Verwendung | Link |
|---|---|---|
| **Databento** | Kontinuierliche Futures-Preise (2nd/3rd Nearby) | [app.databento.com](https://app.databento.com/) |
| **Socrata App Token** | CFTC CoT-Reports (CFTC Open Data) | [dev.socrata.com/register](https://dev.socrata.com/register) |
| **EIA API Key** | Rohöl-Lagerbestände (WTI) | [eia.gov/opendata/register](https://www.eia.gov/opendata/register.php) |

---

## 2. Repository & Python-Umgebung

### Repository klonen

```powershell
git clone https://github.com/sinzb1/CoT-Dashboard_InfluxDB-V3.git
cd CoT-Dashboard_InfluxDB-V3
```

### Virtuelle Umgebung erstellen und aktivieren

```powershell
python -m venv venv
venv\Scripts\activate
```

Die Eingabeaufforderung zeigt jetzt `(venv)` am Anfang.

### Dependencies installieren

```powershell
pip install -r requirements.txt
```

> **Hinweis:** Der InfluxDB v3 Python-Client heisst `influxdb3-python` (nicht `influxdb-client`). Er ist bereits in der `requirements.txt` enthalten.

> **Hinweis Windows:** `gunicorn` in der `requirements.txt` dient dem Production-Deployment unter Linux/Mac und wird unter Windows nicht benötigt. Die Installation schlägt dafür fehl, was den restlichen Betrieb nicht beeinträchtigt.

---

## 3. InfluxDB v3 Core installieren

### 3.1 Binary herunterladen

Lade die neueste Windows-Version von GitHub herunter:

- URL: [github.com/influxdata/influxdb/releases](https://github.com/influxdata/influxdb/releases)
- Datei: `influxdb3-core-x.x.x-windows_amd64.zip`

### 3.2 Entpacken

```powershell
# Zielordner erstellen
New-Item -ItemType Directory -Path "C:\InfluxDB3" -Force

# ZIP entpacken (Pfad anpassen)
Expand-Archive -Path "$env:USERPROFILE\Downloads\influxdb3-core-x.x.x-windows_amd64.zip" `
               -DestinationPath "C:\InfluxDB3"
```

Das Verzeichnis enthält danach: `influxdb3.exe`, `LICENSE`, `README.md`.

---

## 4. InfluxDB v3 Core starten & Token erstellen

### 4.1 Server starten

Öffne ein **neues PowerShell-Fenster** und starte den Server. Der Parameter `--node-id` ist zwingend erforderlich:

```powershell
cd C:\InfluxDB3\influxdb3-core-x.x.x-windows_amd64

.\influxdb3.exe serve `
    --object-store file `
    --data-dir "$env:USERPROFILE\.influxdb" `
    --node-id "cot-dashboard-node"
```

Erwartete Ausgabe:
```
INFO influxdb3_server: startup time: ...ms address=0.0.0.0:8181
```

Der Server läuft auf **Port 8181** und bleibt in diesem Fenster aktiv. Nicht schliessen.

### 4.2 Server-Status prüfen

In einem anderen PowerShell-Fenster:

```powershell
curl http://localhost:8181/health
# Erwartete Antwort: {"status":"ok"}
```

### 4.3 Admin-Token erstellen

```powershell
cd C:\InfluxDB3\influxdb3-core-x.x.x-windows_amd64

.\influxdb3.exe create token --admin
```

Ausgabe:
```
New token created successfully!
Token: apiv3_xxxxxxxxxxxxxxxxxxxxxxxxxxxx...

IMPORTANT: Store this token securely, as it will not be shown again.
```

> **Wichtig:** Den Token sofort sichern – er wird **nicht erneut angezeigt**.

---

## 5. Umgebungsvariablen konfigurieren

Kopiere die Vorlage:

```powershell
copy .env.example .env
```

Öffne `.env` und trage alle Werte ein:

```env
# InfluxDB v3
INFLUXDB_HOST=http://localhost:8181
INFLUXDB_TOKEN=apiv3_xxxxxxxxxxxxxxxxxxxxxxxxxxxx...
INFLUXDB_DATABASE=CoT-Data

# Databento (Futures-Preise)
DATABENTO_API_KEY=db-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Socrata (CFTC CoT-Reports)
SOCRATA_APP_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# EIA (Rohöl-Lagerbestände)
EIA_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> Die `.env`-Datei ist in `.gitignore` eingetragen und wird nicht in Git committet.

---

## 6. Daten laden (Pipeline)

Die Datenpipeline lädt Daten aus allen Quellen und schreibt sie in InfluxDB. Die Datenbank `CoT-Data` wird beim ersten Schreiben automatisch angelegt.

```powershell
python Influx.py
```

Die Pipeline arbeitet **inkrementell**: Sie liest das neueste vorhandene Datum pro Measurement aus InfluxDB und schreibt nur neue Datensätze. Beim ersten Aufruf (leere Datenbank) werden alle Daten für den konfigurierten Zeitraum geladen (`years_back` in `config/config.json`, Standard: 10 Jahre).

Die Pipeline durchläuft 5 Schritte:

| Schritt | Quelle | Measurement in InfluxDB |
|---|---|---|
| 1 | CFTC CoT-Reports (Socrata) | `cot_data` |
| 2 | Makrodaten: VIX, USD Index, USD/CHF (yfinance) | `macro_by_date` |
| 3 | Futures-Frontmonats-Preise (yfinance) | `futures_prices` |
| 4 | EIA Rohöl-Lagerbestände | `eia_petroleum_stocks` |
| 5 | Deferred Futures 2nd/3rd Nearby (Databento) | `futures_deferred_prices` |

Erwartete Ausgabe – erste Ausführung (leere DB):
```
============================================================
Pipeline: VOLLSTÄNDIG (erste Ausführung)
CoT-Daten ab:      2016-04-26  (letzter DB-Eintrag: keiner)
Futures ab:        2016-04-26
Macro ab:          2016-04-26
EIA ab:            2016-04-26
Databento ab:      2016-04-26
============================================================

Geladen: 2299 CoT-Datenpunkte von Socrata.
Davon neu (noch nicht in DB): 2299 Datenpunkte
...
InfluxDB v3 client geschlossen. Pipeline abgeschlossen!
```

Erwartete Ausgabe – folgende Ausführungen (inkrementell):
```
============================================================
Pipeline: INKREMENTELL
CoT-Daten ab:      2026-04-12  (letzter DB-Eintrag: 2026-04-26)
Futures ab:        2026-04-12
...
============================================================

Geladen: 3 CoT-Datenpunkte von Socrata.
Davon neu (noch nicht in DB): 1 Datenpunkte
...
InfluxDB v3 client geschlossen. Pipeline abgeschlossen!
```

---

## 7. Dashboard starten

Sicherstellen, dass der InfluxDB-Server noch läuft (Schritt 4.1), dann:

```powershell
python Dash_Lokal.py
```

Das Dashboard ist verfügbar unter: **http://127.0.0.1:8051/**

### Dashboard-Seiten

| Seite | Inhalt |
|---|---|
| Grundlegende Indikatoren | CoT-Positionierung, Netto-Positionen je Händlergruppe |
| Positioning & Price (PP/DP) | Preiskorrelation, Positionierungsgrad (Bubble Chart) |
| Dry Powder | Verfügbares Kapital je Händlergruppe |
| OB/OS | Overbought/Oversold-Signale |
| Decision Tree | ML-basierte Preisrichtungs-Klassifikation |
| Shapley-Analyse | Feature-Importance der CoT-Indikatoren |

---

## 8. Troubleshooting

### "required arguments were not provided: --node-id"

Der `--node-id` Parameter fehlt beim Serverstart. Siehe Schritt 4.1.

### "401 Unauthorized"

Der Token in der `.env` ist falsch oder abgelaufen. Neuen Token erstellen (Schritt 4.3) und `.env` aktualisieren.

### "Connection refused" / "No connection to localhost:8181"

InfluxDB-Server läuft nicht. PowerShell-Fenster aus Schritt 4.1 prüfen und Server neu starten.

### "Database not found" oder leere Dashboards

Die Pipeline wurde noch nicht ausgeführt oder ist fehlgeschlagen. Schritt 6 (`python Influx.py`) wiederholen und auf Fehlermeldungen achten.

### Port 8181 bereits belegt

```powershell
# Prozess auf Port 8181 finden
netstat -ano | findstr :8181

# Prozess beenden (PID aus obiger Ausgabe einsetzen)
taskkill /PID <PID> /F
```

### Dash-Fehler: "app.run_server is not defined"

Die aktuelle Dash-Version nutzt `app.run()` statt `app.run_server()`. Bereits in diesem Projekt korrekt implementiert – kein Handlungsbedarf.

### gunicorn schlägt bei Installation fehl (Windows)

`gunicorn` ist nicht Windows-kompatibel. Der Fehler kann ignoriert werden – für die lokale Entwicklung unter Windows wird Gunicorn nicht benötigt. Das Dashboard startet direkt mit `python Dash_Lokal.py`.

### Daten verifizieren (optional)

```powershell
cd C:\InfluxDB3\influxdb3-core-x.x.x-windows_amd64

.\influxdb3.exe query `
    --database "CoT-Data" `
    --token "apiv3_..." `
    "SELECT COUNT(*) FROM cot_data"
```

---

## 9. Weiterführende Dokumentation

Im Verzeichnis `docs_lokal/` befinden sich detaillierte Markdown-Dokumente zu Architektur, Datenquellen und Migration:

| Dokument | Inhalt |
|---|---|
| `MIGRATION_GUIDE.md` | Migrationspfad von InfluxDB v2 (Flux) auf v3 (SQL) |
| weitere Dateien | Architektur-Entscheidungen, API-Integrationen, Indikator-Dokumentation |
