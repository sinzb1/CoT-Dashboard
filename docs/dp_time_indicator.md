# Technische Dokumentation: DP Time Indicator

## Inhaltsverzeichnis

1. [Zweck und fachliche Einordnung](#1-zweck-und-fachliche-einordnung)
2. [Verwendete Daten und Quellen](#2-verwendete-daten-und-quellen)
3. [Datenladevorgang](#3-datenladevorgang)
4. [Datenaufbereitung und abgeleitete Spalten](#4-datenaufbereitung-und-abgeleitete-spalten)
5. [Berechnungslogik im Callback](#5-berechnungslogik-im-callback)
6. [Visualisierungsaufbau (Plotly)](#6-visualisierungsaufbau-plotly)
7. [Interaktionen und Callback-Struktur](#7-interaktionen-und-callback-struktur)
8. [Gesamtablauf: Von Rohdaten zur Darstellung](#8-gesamtablauf-von-rohdaten-zur-darstellung)

---

## 1. Zweck und fachliche Einordnung

### 1.1 Analytisches Ziel

Der **Dry Powder Time Indicator (DP Time Indicator)** analysiert, wie sich die Positionierungskonzentration der Tradergruppe *Managed Money* (MM) in Abhängigkeit von der Anzahl aktiver Trader über die Zeit verändert hat.

Die zentrale Frage lautet: Treten hohe Long- oder Short-Konzentrationen bevorzugt in Phasen auf, in denen viele oder wenige Trader aktiv sind – und wie hat sich dieses Muster über verschiedene Jahre entwickelt?

### 1.2 Fachliche Bedeutung

Im Gegensatz zu anderen Dry-Powder-Indikatoren, die Konzentration gegen Preis, Volatilität oder Währung darstellen, kodiert der DP Time Indicator die **zeitliche Dimension** (Jahr) als Farbinformation. Dadurch lassen sich:

- **historische Verschiebungen** in der Marktstruktur sichtbar machen,
- **Extremphasen** aus früheren Jahren mit aktuellen Konstellationen vergleichen,
- **Muster aus mehreren Jahren** gleichzeitig im Scatter-Plot ablesen.

### 1.3 Abgrenzung zu verwandten Indikatoren

| Indikator | X-Achse | Y-Achse | Farbkodierung |
|---|---|---|---|
| DP Time Indicator | Anzahl Trader (MM) | Konzentration (%) | Jahr |
| DP Price Indicator | Anzahl Trader (PMPU) | Open Interest (PMPU) | Futures-Preis |
| DP Factor (VIX) | Anzahl Trader (MM) | Open Interest (MM) | VIX-Wert |
| DP Factor (DXY) | Anzahl Trader (MM) | Open Interest (MM) | DXY-Wert |

---

## 2. Verwendete Daten und Quellen

### 2.1 Primärdatenquelle: CoT-Daten

Der DP Time Indicator basiert ausschliesslich auf **CoT-Daten** (Commitments of Traders), die von der CFTC wöchentlich veröffentlicht werden. Es werden keine externen Marktdaten (Preise, Makrofaktoren) benötigt.

Die relevanten Felder aus dem Measurement `cot_data` in InfluxDB:

| Feld in InfluxDB | Abgeleiteter Spaltenname | Verwendung |
|---|---|---|
| `Managed Money Long` | `Managed Money Long` | Zähler der Long-Konzentrationsformel |
| `Managed Money Short` | `Managed Money Short` | Zähler der Short-Konzentrationsformel |
| `Open Interest` | `Open Interest` | Nenner beider Konzentrationsformeln |
| `Traders M Money Long` | `MML Traders` | X-Achse für Long-Seite |
| `Traders M Money Short` | `MMS Traders` | X-Achse für Short-Seite |
| `market_names` | `Market Names` | Filterkriterium (Marktauswahl) |
| `time` | `Date` | Zeitachse; Basis für `Year`-Spalte |

### 2.2 Abgeleitete Spalte `Year`

Die Spalte `Year` wird nicht in InfluxDB gespeichert, sondern beim Appstart aus der `Date`-Spalte berechnet:

```python
df_pivoted['Year'] = df_pivoted['Date'].dt.year
```

Sie ist die alleinige Grundlage der Farbkodierung im Scatter-Plot.

---

## 3. Datenladevorgang

### 3.1 Verbindung zu InfluxDB v3

Beim Start der Dash-Applikation wird eine Verbindung zu einer lokal laufenden InfluxDB-v3-Core-Instanz hergestellt:

```python
client = InfluxDBClient3(
    host="http://localhost:8181",
    token="...",
    database="CoT-Data"
)
```

### 3.2 SQL-Abfrage

Die CoT-Daten werden über eine SQL-Abfrage geladen, die alle Felder des Measurements `cot_data` für die letzten vier Jahre zurückliefert:

```sql
SELECT *
FROM cot_data
WHERE time >= now() - INTERVAL '4 years'
```

InfluxDB v3 Core unterstützt nativ SQL als Abfragesprache. Die Antwort wird als **Apache Arrow Table** zurückgegeben und unmittelbar in einen Pandas DataFrame konvertiert:

```python
table = client.query(query=query, language="sql")
df_pivoted = table.to_pandas()
```

### 3.3 Spaltenumbenennung

Nach dem Laden werden die InfluxDB-internen Spaltennamen auf Dashboard-kompatible Namen umgeschrieben:

```python
df_pivoted.rename(columns={
    'time':         'Date',
    'market_names': 'Market Names'
}, inplace=True)
```

Die Umbenennung ist notwendig, weil InfluxDB v3 den Timestamp-Index als `time` und den Tag `market_names` in Kleinbuchstaben ausgibt, während alle nachgelagerten Berechnungen und Filteroperationen die aufgeführten Klarnamen verwenden.

### 3.4 Verbindungsschliessung

Nach dem Ladevorgang aller drei Measurements (`cot_data`, `futures_prices`, `macro_by_date`) wird der Client unmittelbar geschlossen:

```python
client.close()
```

Alle Daten befinden sich danach vollständig im Arbeitsspeicher des laufenden Dash-Prozesses. Während der Laufzeit des Dashboards finden keine weiteren Datenbankzugriffe statt.

---

## 4. Datenaufbereitung und abgeleitete Spalten

### 4.1 Sortierung und Alias-Spalten

Nach der Umbenennung wird der gesamte DataFrame nach `Market Names` und `Date` aufsteigend sortiert:

```python
df_pivoted = df_pivoted.sort_values(['Market Names', 'Date'])
```

Diese Sortierung ist Voraussetzung für korrekte Zeitreihenoperationen, insbesondere für Rolling-Berechnungen und die korrekte Bestimmung des letzten Datenpunkts (`iloc[-1]`).

Für den DP Time Indicator werden anschliessend zwei Alias-Spalten angelegt:

```python
df_pivoted['MML Traders'] = df_pivoted['Traders M Money Long']
df_pivoted['MMS Traders'] = df_pivoted['Traders M Money Short']
```

Diese Umbenennung dient der Lesbarkeit im Callback-Code und der einheitlichen Benennung über alle DP-Indikatoren hinweg.

### 4.2 Jahresspalte

```python
df_pivoted['Year'] = df_pivoted['Date'].dt.year
```

Jeder Beobachtung wird das Jahr ihres CoT-Stichtags zugeordnet. Diese Spalte steuert im Callback die Farbzuweisung der Scatter-Punkte.

### 4.3 Datumsbereich der Steuerelemente

Der Standard-Datumsbereich des globalen `DatePickerRange`-Controls wird wie folgt initialisiert:

```python
# Startdatum: frühestes Datum im gesamten Datensatz
start_date = df_pivoted['Date'].min()

# Enddatum: aktuellstes Datum im Datensatz
end_date   = df_pivoted['Date'].max()
```

Das bedeutet: Beim ersten Laden des Dashboards zeigt der DP Time Indicator standardmässig den gesamten verfügbaren 4-Jahres-Zeitraum, da die Steuerelemente auf `min` und `max` vorbelegt sind.

---

## 5. Berechnungslogik im Callback

### 5.1 Datenfiltierung

Der Callback empfängt drei Inputs: den gewählten Markt, das Start- und das Enddatum. Daraus wird ein gefilterter Sub-DataFrame erstellt:

```python
dff = df_pivoted[
    (df_pivoted['Market Names'] == selected_market) &
    (df_pivoted['Date'] >= start_date) &
    (df_pivoted['Date'] <= end_date)
].copy().reset_index(drop=True)
```

Das `.copy()` verhindert, dass Operationen auf `dff` den globalen `df_pivoted` verändern. `.reset_index(drop=True)` sorgt für einen sauberen nullbasierten Index, was für den Zugriff via `iloc[-1]` (letzter Datenpunkt) entscheidend ist.

### 5.2 Konzentrationsberechnung

Das zentrale Merkmal des DP Time Indicators ist die **prozentuale Konzentration** des offenen Interesses einer Tradergruppe am Gesamtmarkt.

**Formel für Managed Money Long (MML):**

$$
\mathrm{DP\_Time}_{\mathrm{MML}} = \frac{\mathrm{Open\,Interest}_{\mathrm{MML}}}{\mathrm{Total\,Open\,Interest}} \cdot 100
$$

**Formel für Managed Money Short (MMS):**

$$
\mathrm{DP\_Time}_{\mathrm{MMS}} = -\frac{\mathrm{Open\,Interest}_{\mathrm{MMS}}}{\mathrm{Total\,Open\,Interest}} \cdot 100
$$

Im Code:

```python
total_oi = pd.to_numeric(dff['Open Interest'], errors='coerce').replace(0, np.nan)

dff['_y_mml'] =  100.0 * pd.to_numeric(dff['Managed Money Long'],  errors='coerce') / total_oi
dff['_y_mms'] = -100.0 * pd.to_numeric(dff['Managed Money Short'], errors='coerce') / total_oi
```

**Warum negatives Vorzeichen bei MMS?**

Die Short-Konzentration erhält ein negatives Vorzeichen, um Long- und Short-Seite im selben Plot visuell zu trennen: MML-Punkte erscheinen im positiven Y-Bereich (oberhalb der Nulllinie), MMS-Punkte im negativen Bereich (unterhalb). Die Nulllinie fungiert so als visuelle Trennlinie zwischen den beiden Gruppen.

**Schutz vor Division durch null:**

`.replace(0, np.nan)` stellt sicher, dass Datenpunkte mit Total Open Interest von 0 (was auf fehlerhafte Quelldaten hindeutet) nicht zu `inf`-Werten führen, sondern als fehlend behandelt werden.

### 5.3 X-Achse: Traderanzahl

```python
x_mml = pd.to_numeric(dff['MML Traders'], errors='coerce')
x_mms = pd.to_numeric(dff['MMS Traders'], errors='coerce')
```

Die X-Achse zeigt die Anzahl der Trader in der jeweiligen Gruppe (Long oder Short). Dieser Wert stammt direkt aus den CoT-Daten (`Traders M Money Long` / `Traders M Money Short`).

### 5.4 Trendlinienberechnung

Für beide Seiten (MML und MMS) wird eine **lineare Regressionsgerade** berechnet, die den globalen Trend der Konzentration in Abhängigkeit von der Traderanzahl zeigt:

```python
def _add_time_trend(xs_arr, x_s, y_s, color, label):
    mask_t = x_s.notna() & y_s.notna()
    xv = x_s[mask_t].astype(float).values
    yv = y_s[mask_t].astype(float).values
    if len(xv) < 2:
        return
    m, b = np.polyfit(xv, yv, 1)   # Lineare Regression (Grad 1)
    ys = m * xs_arr + b
    ...
```

`np.polyfit(xv, yv, 1)` liefert Steigung `m` und Achsenabschnitt `b` der Regressionsgeraden. Die Gerade wird über den gesamten X-Bereich (`[x_min, x_max]`) der aktuellen Datenmenge gespannt.

Die Trendlinie wird zweilagig gezeichnet:
1. **Weisser Untergrund** (Breite 7 px): erzeugt einen visuellen Kontrast zu den farbigen Scatter-Punkten.
2. **Farbige Linie** darüber (Breite 3 px): `#2c7fb8` für MML, `#7fcdbb` für MMS.

---

## 6. Visualisierungsaufbau (Plotly)

Der Scatter-Plot wird als `go.Figure()` mit mehreren Trace-Schichten aufgebaut. Die Reihenfolge der Trace-Erstellung bestimmt die Darstellungsreihenfolge (später hinzugefügte Traces liegen visuell oben).

### 6.1 Schicht 1: Dummy-Traces für die Shape-Legende

Bevor die eigentlichen Datenpunkte gezeichnet werden, fügt der Callback zwei unsichtbare Traces ein:

```python
fig.add_trace(go.Scatter(
    x=[None], y=[None], mode='markers',
    marker=dict(symbol='circle',        color='gray', size=9),
    name='MML', legendgroup='shape_mml'
))
fig.add_trace(go.Scatter(
    x=[None], y=[None], mode='markers',
    marker=dict(symbol='triangle-down', color='gray', size=9),
    name='MMS', legendgroup='shape_mms'
))
```

Diese Traces sind ausschliesslich für die Legende bestimmt: Sie erklären die Symbolkonvention (Kreis = MML, Dreieck = MMS), ohne selbst sichtbare Punkte zu zeichnen (`x=[None], y=[None]`).

### 6.2 Schicht 2: Jahres-Scatter-Traces

Für jedes Jahr im gefilterten Datensatz werden **zwei Traces** hinzugefügt – einer für MML (Kreis), einer für MMS (Dreieck):

```python
for year in sorted(dff['Year'].unique()):
    mask = dff['Year'] == year

    fig.add_trace(go.Scatter(
        x=x_mml[mask], y=dff['_y_mml'][mask],
        mode='markers',
        marker=dict(symbol='circle', size=12, opacity=0.75),
        name=str(year), legendgroup=str(year), showlegend=True,
        hovertemplate='Year: {year}<br>Traders: %{{x}}<br>Long Conc.: %{{y:.1f}}%<extra>MML</extra>'
    ))

    fig.add_trace(go.Scatter(
        x=x_mms[mask], y=dff['_y_mms'][mask],
        mode='markers',
        marker=dict(symbol='triangle-down', size=12, opacity=0.75),
        name=str(year), legendgroup=str(year), showlegend=False,
        ...
    ))
```

**Legendenmanagement via `legendgroup`:**

Beide Traces eines Jahres (MML-Kreis und MMS-Dreieck) teilen dieselbe `legendgroup=str(year)`. Das bedeutet: Ein Klick auf einen Jahreseintrag in der Legende blendet **beide** Formen dieses Jahres gleichzeitig ein oder aus.

Der MML-Trace hat `showlegend=True`, der MMS-Trace `showlegend=False`. Dadurch erscheint in der Legende pro Jahr genau ein Eintrag (mit dem Jahreswert als Label), statt zwei.

**Farbzuweisung:**

Die Farbe wird nicht explizit gesetzt – Plotly weist jedem neu hinzugefügten Trace aus seiner Standardpalette automatisch eine Farbe zu. Da die Traces in aufsteigend sortierter Jahresreihenfolge hinzugefügt werden (`sorted(dff['Year'].unique())`), erhalten aufeinanderfolgende Jahre konsistent benachbarte Farben aus der Plotly-Palette.

### 6.3 Schicht 3: Trendlinien

```python
_add_time_trend(xs, x_mml, dff['_y_mml'], '#2c7fb8', 'MML Trend')
_add_time_trend(xs, x_mms, dff['_y_mms'], '#7fcdbb', 'MMS Trend')
```

Die Trendlinien werden nach den Scatter-Punkten hinzugefügt, liegen also visuell über den Datenpunkten. Das zweischichtige Zeichnen (weisser Hintergrund + Farblinie) sorgt dafür, dass die Trendlinie auch in dichten Punktwolken erkennbar bleibt.

### 6.4 Schicht 4: Most-Recent-Week-Marker

Der aktuellste Datenpunkt im gefilterten Zeitraum wird durch einen grossen schwarzen Marker mit weissem Rand hervorgehoben:

```python
desired_max_px = 18

fig.add_trace(go.Scatter(
    x=[x_mml.iloc[-1]], y=[dff['_y_mml'].iloc[-1]],
    mode='markers',
    marker=dict(size=18, color='black', line=dict(width=2, color='white')),
    name='Most Recent Week', legendgroup='recent', showlegend=True
))
fig.add_trace(go.Scatter(
    x=[x_mms.iloc[-1]], y=[dff['_y_mms'].iloc[-1]],
    mode='markers',
    marker=dict(size=18, color='black', line=dict(width=2, color='white')),
    name='Most Recent Week', legendgroup='recent', showlegend=False
))
```

`iloc[-1]` greift auf den letzten Eintrag des nach `Date` sortierten Sub-DataFrames zu. Da `dff` beim Erstellen via `.reset_index(drop=True)` neu indexiert wird und der Input-DataFrame nach Datum aufsteigend sortiert ist, entspricht `iloc[-1]` stets dem aktuellsten CoT-Stichtag im gewählten Zeitraum.

Auch hier verwenden beide Traces dieselbe `legendgroup='recent'`, sodass nur ein einziger Legendeneintrag für beide Marker erscheint.

### 6.5 Layout-Konfiguration

```python
fig.update_layout(
    title='Dry Powder Time Indicator',
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
```

Die **Nulllinie auf der Y-Achse** (`zeroline=True`) ist bewusst aktiviert: Sie markiert die Trennlinie zwischen Long-Konzentration (positiv) und Short-Konzentration (negativ) und ist damit ein wichtiges Orientierungselement.

Das **weisse Plot-Hintergrundfeld** (`plot_bgcolor='white'`) ist konsistent mit allen anderen DP-Indikatoren des Dashboards.

---

## 7. Interaktionen und Callback-Struktur

### 7.1 Callback-Registrierung

```python
@app.callback(
    Output('dp-time-indicator-graph', 'figure'),
    [
        Input('market-dropdown',      'value'),
        Input('date-picker-range',    'start_date'),
        Input('date-picker-range',    'end_date'),
    ]
)
def update_dp_time(selected_market, start_date, end_date):
    ...
```

Der Callback hat drei Inputs, die alle globalen Steuerelementen des Dashboards entsprechen. Es gibt **keinen lokalen Input** (z.B. RadioItems) für diesen Indikator – er wird vollständig durch die globalen Selektoren gesteuert.

### 7.2 Globale Steuerelemente

| Steuerelement | ID | Typ | Wirkung auf DP Time |
|---|---|---|---|
| Marktauswahl | `market-dropdown` | `dcc.Dropdown` | Filtert `df_pivoted` auf genau einen Markt |
| Startdatum | `date-picker-range` (start) | `dcc.DatePickerRange` | Untere Datumsgrenze für `dff` |
| Enddatum | `date-picker-range` (end) | `dcc.DatePickerRange` | Obere Datumsgrenze für `dff` |

Der `market-dropdown` listet alle eindeutigen Werte aus `df_pivoted['Market Names']` auf. Da der gesamte Datensatz beim Appstart in den Speicher geladen wird, sind alle verfügbaren Märkte (Gold, Silber, Kupfer, Platin, Palladium) sofort auswählbar.

### 7.3 Auswirkung der Datumsfilterung auf die Darstellung

Eine Einschränkung des Datumsbereichs hat folgende Auswirkungen:

- **Weniger Jahre im Plot:** Werden nur 2 Jahre ausgewählt, erscheinen auch nur 2 Jahresfarben.
- **Trendlinie verändert sich:** Die Regressionsgerade wird stets über den aktuell sichtbaren Datenpunkten neu berechnet.
- **Most-Recent-Week-Marker verschiebt sich:** `iloc[-1]` zeigt stets den letzten Datenpunkt *innerhalb* des gewählten Zeitraums, nicht notwendigerweise den jüngsten Gesamtdatenpunkt.

### 7.4 Kein RadioItems-Control

Im Gegensatz zu anderen DP-Indikatoren (z.B. DP Factor DXY, DP Factor VIX, DP Price Indicator) gibt es beim DP Time Indicator **keine Single-Choice-Auswahl** zwischen MM Long und MM Short. Beide Seiten werden stets gleichzeitig im selben Plot dargestellt – differenziert durch die Symbolform (Kreis vs. Dreieck).

---

## 8. Gesamtablauf: Von Rohdaten zur Darstellung

### 8.1 Ablaufdiagramm

```
┌─────────────────────────────────────────────────────────────────┐
│  App-Start (einmalig)                                           │
│                                                                 │
│  InfluxDB v3 → SQL-Abfrage (cot_data, 4 Jahre)                 │
│  → PyArrow Table → pandas DataFrame (df_pivoted)               │
│  → Umbenennung: time → Date, market_names → Market Names        │
│  → Sortierung nach Market Names, Date                           │
│  → Alias-Spalten: MML Traders, MMS Traders                      │
│  → df_pivoted['Year'] = df_pivoted['Date'].dt.year              │
│  → client.close()                                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (bei jeder Nutzerinteraktion)
┌─────────────────────────────────────────────────────────────────┐
│  Callback: update_dp_time()                                     │
│                                                                 │
│  Input: selected_market, start_date, end_date                   │
│                                                                 │
│  1. Filtern:                                                    │
│     dff = df_pivoted                                            │
│       [Market Names == selected_market]                         │
│       [Date >= start_date]                                      │
│       [Date <= end_date]                                        │
│                                                                 │
│  2. Berechnen:                                                  │
│     total_oi = Open Interest (0 → NaN)                          │
│     _y_mml = +100 * MM Long  / total_oi                         │
│     _y_mms = -100 * MM Short / total_oi                         │
│     x_mml  = MML Traders (numeric)                              │
│     x_mms  = MMS Traders (numeric)                              │
│                                                                 │
│  3. Figure aufbauen:                                            │
│     a) Dummy-Traces (Shape-Legende: Kreis=MML, Dreieck=MMS)     │
│     b) Pro Jahr: 2 Scatter-Traces (Kreis + Dreieck)             │
│        – gleiche legendgroup pro Jahr                           │
│        – Farbe: automatische Plotly-Palette                     │
│     c) Trendlinien (MML + MMS), je 2 Lagen                      │
│     d) Most-Recent-Week-Marker (MML + MMS, shared legendgroup)  │
│     e) Layout: weisser Hintergrund, Nulllinie, Gitter           │
│                                                                 │
│  Output: go.Figure → 'dp-time-indicator-graph'                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Schrittweise Beschreibung

**App-Start:**
Beim Start lädt das Dashboard alle CoT-Daten der letzten vier Jahre in den globalen DataFrame `df_pivoted`. Dieser bleibt für die gesamte Laufzeit der Anwendung im Speicher und wird durch Callbacks nicht verändert.

**Filterung im Callback:**
Jede Interaktion mit dem Markt-Dropdown oder dem Datumswähler löst den Callback `update_dp_time` aus. Der Callback erstellt eine gefilterte Kopie (`dff`) des globalen DataFrames.

**Konzentrationsberechnung:**
Die eigentliche Berechnungslogik ist bewusst einfach gehalten: zwei Division-Operationen mit anschliessender Skalierung auf Prozentwerte. Die Berechnung findet vollständig im Callback statt, nicht vorab beim Appstart, da sie vom gewählten Markt und Zeitraum abhängt.

**Jahresbasierte Trace-Generierung:**
Die Schleife über `sorted(dff['Year'].unique())` erstellt für jedes Jahr im gefilterten Zeitraum genau zwei Traces. Die Jahresanzahl und damit die Anzahl der Traces variiert je nach Datumsfilter.

**Trendlinie:**
Die lineare Regression wird über den gesamten gefilterten Datensatz berechnet, also **über alle Jahre gleichzeitig**. Sie zeigt den übergeordneten Trend, unabhängig von der Jahresstruktur.

**Most-Recent-Week:**
Der Marker für den aktuellsten Datenpunkt wird als letzter Trace hinzugefügt, liegt also visuell über allen anderen Elementen. Er markiert stets den zeitlich jüngsten Punkt im gewählten Datumsbereich.
