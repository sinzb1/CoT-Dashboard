# Import, Verarbeitung und Speicherung von Yahoo-Finance-Marktdaten im CoT-Dashboard

## Inhaltsverzeichnis

1. [Ziel und Zweck](#1-ziel-und-zweck)
2. [Verwendete Datenquellen und Ticker](#2-verwendete-datenquellen-und-ticker)
3. [Technischer Datenimport mit yfinance](#3-technischer-datenimport-mit-yfinance)
4. [Datenaufbereitung](#4-datenaufbereitung)
5. [Zeitlicher Abgleich mit den CoT-Daten](#5-zeitlicher-abgleich-mit-den-cot-daten)
6. [Speicherung in InfluxDB](#6-speicherung-in-influxdb)
7. [Gesamter Prozessablauf](#7-gesamter-prozessablauf)
8. [Fachliche Einordnung](#8-fachliche-einordnung)

---

## 1. Ziel und Zweck

### 1.1 Kontext: Das CoT-Dashboard

Das CoT-Dashboard (Commitments of Traders) wertet wöchentliche Positionsdaten der US-amerikanischen Commodity Futures Trading Commission (CFTC) aus. Diese Daten zeigen, wie verschiedene Marktteilnehmergruppen – insbesondere *Managed Money* (MM) und *Producer/Merchant/Processor/User* (PMPU) – in Rohstoff-Futures positioniert sind.

Die CoT-Daten allein beschreiben jedoch ausschliesslich Menge und Richtung der offenen Positionen. Sie enthalten keine Aussage über das Marktumfeld zum Zeitpunkt der Positionierung – also etwa über Preisbewegungen, Volatilität oder Währungsveränderungen, die das Verhalten der Marktteilnehmer beeinflussen.

### 1.2 Warum zusätzliche Marktdaten benötigt werden

Um die Positionierungsdaten kontextuell einordnen und interpretieren zu können, werden ergänzende Marktdaten aus Yahoo Finance importiert. Diese Daten dienen dazu, jede CoT-Beobachtung mit einem aussagekräftigen äusseren Marktkontext zu verknüpfen.

Konkret werden zwei Kategorien von Zusatzdaten benötigt:

**Rohstoff-Futures-Preise:** Der Schlusskurs eines Rohstoffs am CoT-Stichtag ermöglicht es, die Positionsgrösse einer Tradergruppe in Relation zum aktuellen Preisniveau zu setzen. Dadurch wird sichtbar, ob hohe Long- oder Short-Positionierungen in Phasen steigender oder fallender Preise aufgebaut wurden.

**Makroökonomische Faktoren:** Externe Faktoren wie Volatilität, Dollar-Stärke und Wechselkurse beeinflussen die Rohstoffmärkte strukturell. Durch deren Einbindung können Positionierungsmuster im Zusammenhang mit dem übergeordneten Marktumfeld analysiert werden.

### 1.3 Mehrwert der einzelnen Datenarten

| Datenart | Zweck im Dashboard |
|---|---|
| **Rohstoff-Futures-Preise** | Preisbezug für DP Price Indicator und ähnliche Visualisierungen |
| **VIX** | Risiko- und Volatilitätskontext für den DP Factor (VIX) Indicator |
| **DXY (US-Dollar-Index)** | Dollarstärke als Währungskontext für den DP Factor (DXY) Indicator |
| **USD/CHF** | Wechselkursperspektive für den DP Currency Indicator |

---

## 2. Verwendete Datenquellen und Ticker

Alle marktbezogenen Zusatzdaten werden über die Python-Bibliothek **yfinance** bezogen, die einen kostenlosen Zugang zu historischen Kursdaten von Yahoo Finance bietet. Die verwendeten Instrumente sind in zwei Gruppen unterteilt.

### 2.1 Rohstoff-Futures (Commodity Futures)

Für die Preisvisualisierungen werden die Schlusskurse kontinuierlicher Futures-Kontrakte der folgenden Rohstoffe verwendet:

| Rohstoff | Yahoo-Finance-Ticker | Beschreibung |
|---|---|---|
| Gold | `GC=F` | COMEX Gold Futures (Continuous) |
| Silber | `SI=F` | COMEX Silver Futures (Continuous) |
| Kupfer | `HG=F` | COMEX Copper Futures (Continuous) |
| Platin | `PL=F` | NYMEX Platinum Futures (Continuous) |
| Palladium | `PA=F` | NYMEX Palladium Futures (Continuous) |

Das Suffix `=F` kennzeichnet bei Yahoo Finance kontinuierliche (rollende) Futures-Kontrakte, die automatisch auf den nächsten fälligen Kontrakt umrollen. Dadurch entsteht eine lückenlose historische Preiszeitreihe ohne manuelle Kontraktanpassung.

Importierter Wert: ausschliesslich **Close (Schlusskurs)** nach automatischer Adjustierung (`auto_adjust=True`).

### 2.2 Makroökonomische Faktoren (Macro Factors)

Für die kontextuellen Indikatoren werden drei weitere Zeitreihen importiert:

| Bezeichnung | Spaltenname | Yahoo-Finance-Ticker | Beschreibung |
|---|---|---|---|
| CBOE Volatility Index | `vix` | `^VIX` | Mass für die implizite 30-Tage-Volatilität des S&P 500 |
| US-Dollar-Index | `usd_index` | `DX-Y.NYB` | Gewichteter Kurs des USD gegenüber einem Währungskorb (DXY) |
| USD/CHF-Wechselkurs | `usd_chf` | `CHF=X` | Spotpreis des US-Dollars in Schweizer Franken |

Auch hier wird ausschliesslich der **Close-Kurs** importiert. Volumen, Open Interest oder Bid-Ask-Spreads sind für diese Anwendungsfälle nicht relevant.

---

## 3. Technischer Datenimport mit yfinance

### 3.1 Konfiguration des Zeitraums

Der Abholzeitraum wird zentral über die Projektdatei `config/config.json` gesteuert:

```json
{
  "pipeline": {
    "years_back": 4
  }
}
```

Der `YFinanceClient` liest diesen Wert beim Initialisieren ein und berechnet daraus dynamisch Start- und Enddatum:

```python
def _default_date_range(self):
    end = date.today()
    start = date(end.year - self.years_back, end.month, end.day)
    return start, end
```

Das Startdatum liegt damit stets exakt `years_back` Jahre vor dem Ausführungsdatum der Pipeline. Beim Standardwert von 4 Jahren umfasst die importierte Zeitreihe rund 1000 Handelstage pro Instrument.

### 3.2 Datenimport für Rohstoff-Futures

Die Methode `fetch_close_prices()` iteriert über alle konfigurierten Rohstoff-Ticker und ruft für jeden Ticker einzeln die Tagesdaten ab:

```python
for commodity, ticker in self.tickers.items():
    col_name = commodity.lower()
    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=end.isoformat(),
        progress=False,
        auto_adjust=True,
    )
```

Der Parameter `auto_adjust=True` bewirkt, dass yfinance die Schlusskurse automatisch für Splits und Dividenden adjustiert. Für Futures ist dies vor allem beim Kontraktrollover relevant, um Preissprünge zu glätten.

Da yfinance ab Version 1.x bei Einzelabrufen MultiIndex-Spalten zurückgibt (Format: `(Price, Ticker)`), wird dieser Fall explizit behandelt:

```python
if isinstance(df.columns, pd.MultiIndex):
    close = df[("Close", ticker)].rename(col_name)
else:
    close = df["Close"].rename(col_name)
```

### 3.3 Datenimport für Makrofaktoren

Der Ablauf für Makrodaten ist strukturell identisch zur Rohstoff-Abholung. Die Methode `fetch_macro_close_prices()` iteriert über die drei Makro-Ticker (`^VIX`, `DX-Y.NYB`, `CHF=X`) und extrahiert jeweils den Close-Kurs:

```python
for col_name, ticker in self.macro_tickers.items():
    df = yf.download(ticker, start=..., end=..., progress=False, auto_adjust=True)
    close = df[("Close", ticker)].rename(col_name)
```

### 3.4 Zusammenführung mehrerer Ticker

Nach dem individuellen Abruf werden alle Einzelzeitreihen über einen iterativen Outer-Merge auf der Datumsspalte zusammengeführt:

```python
result = frames[0]
for f in frames[1:]:
    result = result.merge(f, on="date", how="outer")
```

Der `outer`-Join stellt sicher, dass kein Handelstag verloren geht, selbst wenn ein einzelnes Instrument an einem bestimmten Tag nicht gehandelt wurde (z.B. Feiertage auf einzelnen Börsen). Fehlende Werte werden in diesem Fall als `NaN` eingetragen und später im Aufbereitungsschritt behandelt.

Das Ergebnis ist ein einziger DataFrame mit der Spalte `date` und je einer numerischen Spalte pro Instrument.

---

## 4. Datenaufbereitung

### 4.1 Zeitstempel und Zeitzonen

yfinance liefert Datumswerte je nach Instrument und Version entweder als timezone-naive oder timezone-aware Timestamps. Um eine konsistente Verarbeitung sicherzustellen, werden alle Zeitstempel in `FuturesPriceService` und `MacroPriceService` einheitlich in **UTC** konvertiert:

```python
df["date"] = pd.to_datetime(df["date"], utc=True)
```

Diese Normalisierung ist zwingend erforderlich, da der spätere Abgleich mit den CoT-Daten einen direkten Zeitstempelvergleich voraussetzt. Zeitzonendifferenzen würden zu fehlerhaften Zuordnungen führen.

### 4.2 Numerische Datenbereinigung

Nicht alle von yfinance gelieferten Werte sind unmittelbar als Gleitkommazahlen verwendbar. Insbesondere bei fehlenden Handelstagen, delisteten Kontrakten oder Lücken in der Zeitreihe können Strings wie `"NaN"` oder leere Strings auftreten. Diese werden explizit bereinigt:

```python
value_cols = [c for c in df.columns if c != "date"]
df[value_cols] = (
    df[value_cols]
    .replace({"": np.nan, "NaN": np.nan, None: np.nan})
    .apply(pd.to_numeric, errors="coerce")
)
```

Der Parameter `errors="coerce"` bei `pd.to_numeric` wandelt alle nicht konvertierbaren Werte automatisch in `NaN` um, ohne eine Exception auszulösen.

### 4.3 Sortierung

Nach der Bereinigung werden alle DataFrames aufsteigend nach Datum sortiert:

```python
df = df.sort_values("date").reset_index(drop=True)
```

Diese Sortierung ist eine Voraussetzung für den nachfolgenden zeitlichen Abgleich via `merge_asof`, der ein geordnetes linkes und rechtes DataFrame erwartet.

### 4.4 Relevante Spalten

Nach der Aufbereitung haben die DataFrames folgende Struktur:

**Rohstoff-Futures (`FuturesPriceService`):**

| Spalte | Typ | Beschreibung |
|---|---|---|
| `date` | datetime (UTC) | Handelstag |
| `gold` | float | Schlusskurs Gold-Future |
| `silver` | float | Schlusskurs Silber-Future |
| `copper` | float | Schlusskurs Kupfer-Future |
| `platinum` | float | Schlusskurs Platin-Future |
| `palladium` | float | Schlusskurs Palladium-Future |

**Makrofaktoren (`MacroPriceService`):**

| Spalte | Typ | Beschreibung |
|---|---|---|
| `date` | datetime (UTC) | Handelstag |
| `vix` | float | CBOE VIX Schlusskurs |
| `usd_index` | float | DXY Schlusskurs |
| `usd_chf` | float | USD/CHF Schlusskurs |

---

## 5. Zeitlicher Abgleich mit den CoT-Daten

### 5.1 Die Rolle des Dienstags in CoT-Daten

Die CFTC veröffentlicht die CoT-Reports wöchentlich, wobei der Berichtsstichtag stets der **Dienstag** der jeweiligen Woche ist. Dieser Stichtag gibt an, zu welchem Zeitpunkt die Positionsdaten der Marktteilnehmer erhoben wurden. Die Veröffentlichung erfolgt typischerweise am darauffolgenden Freitagabend.

Für die Analyse ist ausschliesslich der Dienstag als Referenzdatum massgebend, da nur so eine zeitlich konsistente Verknüpfung zwischen Positionierung und Marktpreis möglich ist. Ein Preiswert vom Freitag (Veröffentlichungstag) würde zum Stichtag der Positionsdaten nicht passen.

### 5.2 Abgleichstrategie: `merge_asof`

Die Herausforderung besteht darin, dass Yahoo Finance täglich handelnde Märkte abbildet, während die CoT-Daten nur wöchentliche Datenpunkte (jeweils dienstags) enthalten. Zudem ist nicht garantiert, dass an jedem CoT-Dienstag auch für jedes Instrument ein Handelstag vorliegt – etwa aufgrund von US-Feiertagen oder Marktschliessungen.

Beide Service-Klassen lösen dieses Problem mit `pandas.merge_asof`. Diese Funktion führt einen zeitbasierten Nearest-Neighbour-Join durch, der für jeden CoT-Datenpunkt den zeitlich nächstliegenden vorherigen Marktpreis innerhalb einer definierten Toleranz sucht:

```python
merged = pd.merge_asof(
    cot_ref,            # linkes DataFrame: sortierte CoT-Stichtage
    prices_sorted,      # rechtes DataFrame: sortierte Tageskurse
    left_on="cot_date",
    right_on="date",
    direction="backward",
    tolerance=pd.Timedelta(days=4),
)
```

**Parameter im Detail:**

- `direction="backward"`: Sucht den letzten verfügbaren Kurs, der **am oder vor** dem CoT-Stichtag liegt. Zukünftige Kurse werden nie verwendet, da diese zum Zeitpunkt der Positionierung noch nicht bekannt waren.
- `tolerance=pd.Timedelta(days=4)`: Akzeptiert maximal 4 Tage Abstand. Wenn kein Handelstag innerhalb dieser Toleranz liegt, wird `NaN` eingetragen. Eine Toleranz von 4 Tagen stellt sicher, dass auch bei Feiertagen zu Wochenbeginn (Montag/Dienstag) der letzte verfügbare Freitagskurs verwendet wird.

### 5.3 Fallback: Dienstags-Filter

Falls beim Aufruf von `load_aligned()` keine konkreten CoT-Stichtage übergeben werden, greift ein Fallback-Mechanismus:

```python
tuesday_mask = prices_df["date"].dt.dayofweek == 1   # 1 = Dienstag
result = prices_df[tuesday_mask].copy()
```

In Python entspricht `dayofweek == 1` dem Dienstag (Montag = 0, Sonntag = 6). Dieser Fallback filtert die täglichen Kursdaten auf alle Dienstage, was ohne konkrete CoT-Stichtage eine gute Näherung darstellt.

### 5.4 Umgang mit Sonderfällen

| Sonderfall | Behandlung |
|---|---|
| Kein Handelstag am CoT-Dienstag (Feiertag) | `merge_asof` verwendet den letzten verfügbaren Kurs bis max. 4 Tage zurück (z.B. Freitag der Vorwoche) |
| Mehr als 4 Tage ohne Handelstag | Eintrag wird als `NaN` übernommen und beim Schreiben in InfluxDB übersprungen |
| Unterschiedliche Handelskalender | Da jeder Ticker separat abgerufen und per Outer-Join zusammengeführt wird, hat jedes Instrument seinen eigenen Verfügbarkeits-Kalender; fehlende Werte eines Instruments beeinflussen die anderen nicht |
| VIX an Nicht-Handelstagen | Der VIX wird an US-Börsentagen berechnet; bei US-Feiertagen greift dieselbe `backward`-Toleranz wie bei Futures |

### 5.5 Ergebnis des Abgleichs

Das Ergebnis von `load_aligned()` ist ein DataFrame, der exakt die CoT-Stichtage als Zeitindex enthält und für jeden dieser Stichtage den nächstliegenden vorherigen Marktpreis enthält. Zeilen, bei denen **alle** Wertspalten `NaN` sind, werden entfernt:

```python
merged = merged.dropna(subset=value_cols, how="all")
```

Dieses Vorgehen stellt sicher, dass nur Datenpunkte in die Datenbank geschrieben werden, für die mindestens ein valider Marktpreis vorliegt.

---

## 6. Speicherung in InfluxDB

### 6.1 Datenbankstruktur

Die aufbereiteten Daten werden in einer lokalen **InfluxDB v3 Core**-Instanz gespeichert, die standardmässig auf Port `8181` läuft. Die Datenbank trägt den Namen `CoT-Data`.

Innerhalb dieser Datenbank werden drei separate **Measurements** (entspricht in InfluxDB dem Konzept einer Tabelle) verwendet:

| Measurement | Inhalt | Schreibquelle |
|---|---|---|
| `cot_data` | Wöchentliche CoT-Positionsdaten (alle Tradergruppen) | `TradesCategoryService` |
| `macro_by_date` | Makrofaktoren (VIX, DXY, USD/CHF) – auf CoT-Stichtage aligniert | `MacroPriceService` |
| `futures_prices` | Rohstoff-Futures-Schlusskurse – auf CoT-Stichtage aligniert | `FuturesPriceService` |

### 6.2 Measurement: `macro_by_date`

Das Measurement `macro_by_date` enthält die Makrofaktordaten. Es werden keine Tags verwendet, da alle Makrofaktoren marktübergreifend gelten und nicht marktsegmentspezifisch sind.

**Struktur:**

| Ebene | Name | Typ | Beschreibung |
|---|---|---|---|
| Timestamp | `time` | datetime (UTC) | CoT-Stichtag (Dienstag) |
| Field | `vix` | float | VIX-Schlusskurs zum Stichtag |
| Field | `usd_index` | float | DXY-Schlusskurs zum Stichtag |
| Field | `usd_chf` | float | USD/CHF-Schlusskurs zum Stichtag |

Ein einzelner Datenpunkt (Point) wird wie folgt aufgebaut:

```python
p = Point("macro_by_date").time(row["date"].to_pydatetime())

if pd.notna(row.get("vix")):
    p = p.field("vix", float(row["vix"]))
if pd.notna(row.get("usd_index")):
    p = p.field("usd_index", float(row["usd_index"]))
if pd.notna(row.get("usd_chf")):
    p = p.field("usd_chf", float(row["usd_chf"]))
```

Wichtig: Fields werden nur dann gesetzt, wenn der jeweilige Wert nicht `NaN` ist. Dadurch entstehen keine Dummy-Einträge mit Nullwerten, was die Abfrageeffizienz verbessert und falsche Interpolationen vermeidet.

### 6.3 Measurement: `futures_prices`

Das Measurement `futures_prices` enthält die Rohstoff-Schlusskurse, ebenfalls ohne Tags:

| Ebene | Name | Typ | Beschreibung |
|---|---|---|---|
| Timestamp | `time` | datetime (UTC) | CoT-Stichtag |
| Field | `gold_close` | float | Gold-Future Schlusskurs |
| Field | `silver_close` | float | Silber-Future Schlusskurs |
| Field | `copper_close` | float | Kupfer-Future Schlusskurs |
| Field | `platinum_close` | float | Platin-Future Schlusskurs |
| Field | `palladium_close` | float | Palladium-Future Schlusskurs |

Die Field-Namen im Measurement (`gold_close`, `silver_close` etc.) unterscheiden sich bewusst von den internen Spaltennamen im DataFrame (`gold`, `silver` etc.), um in InfluxDB-Abfragen eindeutig auf Preiswerte hinzuweisen.

### 6.4 Measurement: `cot_data`

Das Measurement `cot_data` enthält die CoT-Positionsdaten und weist als einziges Measurement ein **Tag** auf:

| Ebene | Name | Typ | Beschreibung |
|---|---|---|---|
| Timestamp | `time` | datetime (UTC) | CoT-Stichtag |
| Tag | `market_names` | string | Marktbezeichnung (z.B. "GOLD - COMMODITY EXCHANGE INC.") |
| Fields | diverse | float | Open Interest, Long/Short-Positionen, Traderanzahlen etc. |

Der Tag `market_names` ermöglicht es, Abfragen effizient auf einzelne Märkte zu filtern, da Tags in InfluxDB indiziert werden.

### 6.5 Schreibprozess und Idempotenz

Vor jedem Schreibvorgang werden die bestehenden Daten im jeweiligen Measurement gelöscht, um Duplikate zu vermeiden:

```python
def delete_measurement_range(client, measurement, start, end):
    delete_sql = (
        f"DELETE FROM \"{measurement}\" "
        f"WHERE time >= '{start_str}' AND time <= '{end_str}'"
    )
    client.query(query=delete_sql, language="sql")
```

Das Delete-Fenster beginnt beim `2000-01-01`, um sicherzustellen, dass auch eventuelle Legacy-Daten ausserhalb des 4-Jahres-Fensters entfernt werden. Falls die DELETE-Operation fehlschlägt (z.B. wenn die InfluxDB-Version dieses Kommando nicht unterstützt), wird die Pipeline nicht abgebrochen – InfluxDB schreibt bei identischem Timestamp idempotent (Upsert-Verhalten).

Die eigentlichen Datenpunkte werden als Liste von `Point`-Objekten in einem einzigen Batch-Schreibvorgang an InfluxDB übertragen:

```python
client.write(record=points)
```

Dieses Batch-Vorgehen ist deutlich effizienter als einzelne Schreiboperationen pro Datenpunkt, da der Netzwerk- und Serialisierungsaufwand minimiert wird.

---

## 7. Gesamter Prozessablauf

Der gesamte Datenpipeline-Prozess wird durch das Skript `Influx.py` orchestriert und läuft in drei sequenziellen Schritten ab.

### 7.1 Ablaufdiagramm

```
┌─────────────────────────────────────────────────────────────┐
│                       Influx.py                              │
│                                                             │
│  1. CoT-Daten laden (Socrata API)                          │
│     └─ TradesCategoryService.load_dataframe()               │
│     └─ Eindeutige CoT-Stichtage extrahieren                 │
│                                                             │
│  2. Makrodaten laden und alignieren                         │
│     └─ MacroPriceService.load_aligned(cot_dates)            │
│         └─ YFinanceClient.fetch_macro_close_prices()        │
│             └─ yf.download(^VIX, DX-Y.NYB, CHF=X)          │
│         └─ Aufbereitung (UTC, numeric coerce)               │
│         └─ merge_asof auf CoT-Stichtage (4 Tage Toleranz)   │
│                                                             │
│  3. Futures-Preisdaten laden und alignieren                 │
│     └─ FuturesPriceService.load_aligned(cot_dates)          │
│         └─ YFinanceClient.fetch_close_prices()              │
│             └─ yf.download(GC=F, SI=F, HG=F, PL=F, PA=F)   │
│         └─ Aufbereitung (UTC, numeric coerce)               │
│         └─ merge_asof auf CoT-Stichtage (4 Tage Toleranz)   │
│                                                             │
│  4. InfluxDB schreiben                                      │
│     └─ DELETE cot_data, macro_by_date, futures_prices       │
│     └─ WRITE cot_data     → Measurement: cot_data           │
│     └─ WRITE macro_df     → Measurement: macro_by_date      │
│     └─ WRITE futures_df   → Measurement: futures_prices     │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Schrittweise Beschreibung

**Schritt 1: CoT-Daten laden**

`TradesCategoryService` ruft die Rohdaten über die Socrata-API der CFTC ab und gibt nach Filterung und Umbenennung einen DataFrame mit den wöchentlichen Positionsdaten zurück. Aus diesem DataFrame werden die eindeutigen Berichtsstichtage extrahiert:

```python
cot_dates = tc_df["Date"].drop_duplicates().sort_values()
```

Diese Stichtage dienen als Referenz-Zeitachse für alle nachfolgenden Abgleiche.

**Schritt 2: Makrodaten laden und alignieren**

`MacroPriceService.load_aligned(cot_dates)` führt intern drei Teilschritte durch:

1. **Abruf:** `YFinanceClient.fetch_macro_close_prices()` lädt Tageskurse für VIX, DXY und USD/CHF via `yf.download()`.
2. **Aufbereitung:** UTC-Normalisierung, Duplikat-Bereinigung, numerisches Coercion.
3. **Abgleich:** `merge_asof` mit `direction="backward"` und `tolerance=4 Tage` aligniert jeden täglichen Kurs auf den nächstliegenden CoT-Stichtag.

Das Ergebnis ist ein DataFrame mit exakt den CoT-Dienstagen als Zeitindex.

**Schritt 3: Futures-Preisdaten laden und alignieren**

`FuturesPriceService.load_aligned(cot_dates)` folgt identischer Logik: Abruf der fünf Rohstoff-Futures via yfinance, Aufbereitung, `merge_asof`-Abgleich auf CoT-Stichtage.

**Schritt 4: Daten in InfluxDB schreiben**

Für jedes der drei Measurements wird zunächst ein gezieltes DELETE ausgeführt, anschliessend werden die aufbereiteten Datenpunkte als Batch geschrieben. Datenpunkte mit ausschliesslich `NaN`-Werten werden übersprungen.

---

## 8. Fachliche Einordnung

### 8.1 Rohstoff-Futures-Preise

Der Futures-Preis eines Rohstoffs zum CoT-Stichtag ist der primäre Referenzwert für alle preisbezogenen Dry-Powder-Indikatoren im Dashboard. Der sogenannte *Dry Powder Price Indicator* setzt die Anzahl Trader einer Gruppe in Bezug zu deren offenem Interesse und färbt jeden Datenpunkt anhand des damaligen Preisniveaus ein.

Dadurch wird sichtbar, ob grosse Positionierungen (hohes Open Interest, wenige Trader) bevorzugt in Hochpreis- oder Tiefpreisphasen entstehen – ein Hinweis auf akkumulatives oder distributives Verhalten einer Tradergruppe.

Der Einsatz kontinuierlicher Futures-Kontrakte (`=F`-Ticker) ist dabei bewusst gewählt: Sie bilden den effektiven Handelsmarkt ab, in dem die CoT-Teilnehmer aktiv sind, und vermeiden die Preissprünge beim Kontraktrollover.

### 8.2 VIX – Volatilitätskontext

Der VIX misst die vom Optionsmarkt implizierte erwartete Schwankungsbreite des S&P 500 für die nächsten 30 Tage. Er gilt als Mass für die Risikoaversion der Marktteilnehmer: Ein hoher VIX signalisiert Stress und Unsicherheit, ein tiefer VIX ein ruhiges Marktumfeld.

Im Dashboard dient der VIX als externer Risikofaktor im *DP Factor (VIX) Indicator*. Die Einfärbung der Scatter-Plot-Punkte nach VIX-Niveau erlaubt es zu erkennen, ob bestimmte Positionierungsmuster bevorzugt in risikoaversen (hoher VIX) oder risikofreudigen (tiefer VIX) Marktphasen auftreten. Dies ist insbesondere für Managed Money relevant, da diese Gruppe typischerweise auf makroökonomische Risikosignale reagiert.

### 8.3 DXY – Dollar-Index

Der US-Dollar-Index (DXY) misst den Wert des US-Dollars gegenüber einem gewichteten Korb aus sechs Hauptwährungen (EUR, JPY, GBP, CAD, SEK, CHF). Da Rohstoffe global in US-Dollar gehandelt werden, besteht eine strukturelle Wechselwirkung zwischen Dollarstärke und Rohstoffpreisen: Ein starker Dollar macht Rohstoffe für nicht-amerikanische Käufer teurer und dämpft tendenziell die Nachfrage.

Der *DP Factor (DXY) Indicator* zeigt, ob Positionierungen in Rohstoff-Futures bevorzugt in Phasen eines starken oder schwachen Dollars aufgebaut werden. Dieses Muster kann Hinweise auf die Währungssensitivität einzelner Märkte und Tradergruppen liefern.

### 8.4 USD/CHF – Wechselkursperspektive

Der USD/CHF-Kurs bildet das Verhältnis des US-Dollars zum Schweizer Franken ab. Der Franken gilt traditionell als Fluchtwährung (*Safe Haven*) und tendiert in Krisenzeiten zur Aufwertung, was einem fallenden USD/CHF-Kurs entspricht.

Im Kontext einer Schweizer Masterarbeit ist die CHF-Perspektive besonders relevant: Der *DP Currency Indicator (USD/CHF)* zeigt, wie Rohstoff-Positionen in Relation zur Frankenstärke stehen. Ein tiefer USD/CHF-Kurs (starker Franken) kann auf risikoscheues Verhalten hindeuten, das parallel mit bestimmten Positionierungsmustern bei Rohstoffen auftreten kann.

### 8.5 Kombination von CoT- und Yahoo-Finance-Daten

Die Yahoo-Finance-Daten sind im Dashboard ausschliesslich als **Kontextinformation** zu verstehen – sie erklären oder verursachen keine CoT-Positionierungen, sondern ermöglichen deren Einordnung in das übergeordnete Marktumfeld.

Technisch werden sie im Dashboard via `merge_asof` (Toleranz 7 Tage) dem jeweiligen CoT-Datenpunkt zugeordnet, um Farb- und Hover-Informationen in den Scatter-Plots bereitzustellen. Die etwas grosszügigere Toleranz von 7 Tagen gegenüber der Pipeline-Toleranz von 4 Tagen stellt sicher, dass auch bei leicht abweichenden Datumsformaten zwischen der InfluxDB-Abfrage und dem DataFrame eine zuverlässige Zuordnung erfolgt.

Diese strikte Trennung zwischen Positionsdaten (CoT) und Kontextdaten (Yahoo Finance) gewährleistet die analytische Klarheit der Indikatoren und verhindert eine unbeabsichtigte Vermischung der Datenquellen.
