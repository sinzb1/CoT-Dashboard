# Dokumentation: Preisprognose mit Entscheidungsbaum

**Projekt:** DIFA CoT-Dashboard  
**Modul:** `src/analysis/decision_tree.py`  
**Dashboard-Integration:** `Dash_Lokal.py`  
**Stand:** März 2026

---

## Inhaltsverzeichnis

1. [Überblick und Zielsetzung](#1-überblick-und-zielsetzung)
2. [Architektur und Modulstruktur](#2-architektur-und-modulstruktur)
3. [Datengrundlage](#3-datengrundlage)
4. [Feature Engineering](#4-feature-engineering)
5. [Zielvariable](#5-zielvariable)
6. [Modelltraining](#6-modelltraining)
7. [Pre-Computation beim Dashboard-Start](#7-pre-computation-beim-dashboard-start)
8. [Dashboard-Integration (Layout & Callback)](#8-dashboard-integration-layout--callback)
9. [Visualisierungen und deren Interpretation](#9-visualisierungen-und-deren-interpretation)
10. [Interpretation des Prognosesatzes](#10-interpretation-des-prognosesatzes)
11. [Wichtige Einschränkungen](#11-wichtige-einschränkungen)

---

## 1. Überblick und Zielsetzung

Für jeden im Dashboard verfügbaren Rohstoff (**Gold, Silver, Copper, Platinum, Palladium**) wird ein eigenständiger **Decision Tree Classifier** trainiert. Das Modell beantwortet auf Basis der aktuellsten CoT-Positionierungsdaten eine binäre Frage:

> *Wird der Futures-Preis dieses Rohstoffs in der nächsten Woche steigen oder fallen?*

Das Modell verwendet **ausschliesslich Daten aus der bestehenden InfluxDB-Datenbank** – es werden keine externen Datenquellen oder neuen Importe benötigt. Die Prognose dient als ergänzendes Instrument zur Einschätzung der Marktrichtung auf Basis der Positionierungssignale.

---

## 2. Architektur und Modulstruktur

Die Implementierung folgt dem bestehenden Architekturmuster des Dashboards, bei dem rechenintensive Logik in separate Module unter `src/analysis/` ausgelagert wird – analog zu `src/analysis/shapley_owen.py`.

```
src/
└── analysis/
    ├── shapley_owen.py        ← bereits vorhanden (Shapley-Owen-Zerlegung)
    └── decision_tree.py       ← neu: Decision-Tree-Logik
```

**Warum diese Auslagerung?**

- Das `Dash_Lokal.py` bleibt schlank und enthält nur Dashboard-spezifischen Code (Layout, Callbacks)
- Die Modelllogik ist wiederverwendbar und unabhängig testbar
- Konsistenz mit dem bestehenden Architekturprinzip des Projekts

### Öffentliche API des Moduls

| Funktion | Eingabe | Ausgabe | Zweck |
|---|---|---|---|
| `train_decision_tree(df_market, df_prices, price_col)` | Markt-DataFrame, Preisdaten, Spaltennamen | `dict` mit Modell + Prognose | Trainiert den Baum |
| `render_tree_image(result)` | Ergebnis-Dict | base64-PNG als data-URI | Visualisiert den Baum |
| `feature_importance_figure(result, market_name)` | Ergebnis-Dict, Marktname | Plotly `Figure` | Erstellt Feature-Importance-Diagramm |

---

## 3. Datengrundlage

### CoT-Daten (Measurement: `cot_data`)

Die Rohdaten stammen aus den wöchentlichen **Commitments of Traders (CoT)**-Berichten der CFTC und werden über die Pipeline in die InfluxDB geschrieben. Für das Decision-Tree-Modell werden folgende Spalten aus `df_pivoted` verwendet:

| InfluxDB-Spaltenname | Bedeutung |
|---|---|
| `Managed Money Long` | Open Interest der Managed-Money-Long-Positionen |
| `Managed Money Short` | Open Interest der Managed-Money-Short-Positionen |
| `Producer/Merchant/Processor/User Long` | Open Interest der PMPU-Long-Positionen |
| `Producer/Merchant/Processor/User Short` | Open Interest der PMPU-Short-Positionen |
| `Swap Dealer Long` | Open Interest der Swap-Dealer-Long-Positionen |
| `Swap Dealer Short` | Open Interest der Swap-Dealer-Short-Positionen |
| `Open Interest` | Gesamtes Open Interest des Marktes |

### Futures-Preise (Measurement: `futures_prices`)

Für die Berechnung der **Zielvariable** (steigt/fällt der Preis?) werden die Futures-Schlusskurse aus der `futures_prices`-Tabelle verwendet. Das Mapping zwischen Marktname und Preisspalte:

| Markt | Preisspalte |
|---|---|
| Gold | `gold_close` |
| Silver | `silver_close` |
| Copper | `copper_close` |
| Platinum | `platinum_close` |
| Palladium | `palladium_close` |

Die Preisdaten werden via `merge_asof` mit den CoT-Daten zusammengeführt (max. Toleranz: 7 Tage rückwärts), sodass jeder CoT-Beobachtung der zeitlich nächste verfügbare Schlusskurs zugeordnet wird.

---

## 4. Feature Engineering

Aus den Rohdaten werden **8 Features** berechnet. Diese sind identisch mit den Variablen aus dem Referenz-Notebook (`Decision Tree.py`):

### 4.1 Netto-Positionen

```python
net_mm   = Managed Money Long   - Managed Money Short
net_pmpu = PMPU Long            - PMPU Short
net_swap = Swap Dealer Long     - Swap Dealer Short
```

Die Netto-Position zeigt, ob eine Händlergruppe per saldo Long oder Short positioniert ist und wie stark dieses Engagement ist. Ein positiver Wert bedeutet Netto-Long, ein negativer Netto-Short.

### 4.2 Prozentuale Anteile am Open Interest

```python
pct_mm_long  = (Managed Money Long  / Open Interest) × 100
pct_mm_short = (Managed Money Short / Open Interest) × 100
```

Diese Features geben an, welchen **prozentualen Anteil** des gesamten Open Interests die Managed-Money-Gruppe auf der Long- bzw. Short-Seite hält. Sie sind damit ein Mass für die relative Dominanz dieser Gruppe im Markt. Dieser Wert entspricht exakt dem CFTC-Feld `Pct_of_OI_M_Money_Long_All` aus dem Referenz-Notebook.

### 4.3 Wochenveränderungen

```python
chg_net_mm      = net_mm.diff()       # Δ zur Vorwoche
chg_pct_mm_long = pct_mm_long.diff()  # Δ zur Vorwoche
```

Diese Features messen die **Dynamik** der Positionierungsveränderung: Baut Managed Money seine Netto-Position aus oder ab? Eine starke positive Veränderung deutet auf zunehmendes Long-Engagement hin.

### 4.4 Rollender Z-Score

```python
rolling_mean = net_mm.rolling(window=13).mean()
rolling_std  = net_mm.rolling(window=13).std()
z_net_mm     = (net_mm - rolling_mean) / rolling_std
```

Der Z-Score misst, wie weit die aktuelle Netto-Position der Managed-Money-Gruppe von ihrem **13-Wochen-Durchschnitt** (ca. ein Quartal) abweicht – gemessen in Standardabweichungen. Ein hoher positiver Z-Score signalisiert eine ungewöhnlich starke Long-Positionierung im historischen Vergleich.

**Warum 13 Wochen?** Dieses Fenster entspricht etwa einem Quartal und glättet kurzfristiges Rauschen, ohne strukturelle Positionierungsveränderungen zu verzögern.

### Übersicht aller Features

| Feature | Formel | Interpretation |
|---|---|---|
| `net_mm` | MM_L − MM_S | Gerichtetes Engagement der Spekulanten |
| `net_pmpu` | PMPU_L − PMPU_S | Gerichtetes Engagement der Produzenten/Händler |
| `net_swap` | SD_L − SD_S | Gerichtetes Engagement der Swap Dealer |
| `pct_mm_long` | MM_L / OI × 100 | Relativer Anteil MM-Long am Gesamtmarkt |
| `pct_mm_short` | MM_S / OI × 100 | Relativer Anteil MM-Short am Gesamtmarkt |
| `chg_net_mm` | Δ(net_mm) | Wöchentliche Positionsveränderung MM |
| `chg_pct_mm_long` | Δ(pct_mm_long) | Wöchentliche Änderung des MM-Long-Anteils |
| `z_net_mm` | (net_mm − μ₁₃W) / σ₁₃W | Extremität der MM-Positionierung |

---

## 5. Zielvariable

```python
close_fwd = close.shift(-1)         # Preis der nächsten Woche
y = (close_fwd > close).astype(int) # 1 = steigt, 0 = fällt
```

Die Zielvariable ist **binär**:

- **y = 1 (steigt):** Der Futures-Schlusskurs der nächsten Woche ist höher als der aktuelle.
- **y = 0 (fällt):** Der Futures-Schlusskurs der nächsten Woche ist niedriger oder gleich dem aktuellen.

Da die letzte Zeile des Datensatzes keine bekannte Zukunft hat (`close_fwd` = NaN), wird diese Zeile aus dem **Training** herausgehalten. Für die **Prognose** wird jedoch genau diese aktuellste Zeile verwendet – der Baum sagt voraus, was noch unbekannt ist.

---

## 6. Modelltraining

### Modellparameter

```python
DecisionTreeClassifier(
    max_depth=3,         # Maximale Baumtiefe
    min_samples_leaf=3,  # Mindestgrösse jedes Blattknotens
    random_state=42      # Reproduzierbarkeit
)
```

**Warum `max_depth=3`?**  
Eine Tiefe von 3 erzeugt maximal 8 Blattknoten. Dieser Wert balanciert Interpretierbarkeit (der Baum bleibt visuell lesbar) mit ausreichender Modellkomplexität. Tiefere Bäume würden zu Overfitting neigen, da die Datenmenge (~200 Beobachtungen) begrenzt ist.

**Warum `min_samples_leaf=3`?**  
Jeder Endknoten muss mindestens 3 Trainingsbeobachtungen enthalten. Dies verhindert, dass der Baum auf einzelnen Ausreissern basiert.

### Trainingsschema

Das Modell wird auf dem **vollständigen verfügbaren Datensatz** trainiert (ausgenommen die letzte Zeile, für die kein Folge-Preis bekannt ist). Es gibt keine Aufteilung in Train/Test-Sets, da der Zweck nicht die Modellvalidierung, sondern die Prognose auf Basis aller verfügbaren Informationen ist.

> **Hinweis:** Validierungskennzahlen (Accuracy, Precision, Recall, F1, Confusion Matrix) sind bewusst **nicht** Teil dieser Implementierung, da sie für die reine Prognose-Darstellung nicht benötigt werden.

### Prognose

Nach dem Training wird die **aktuellste Zeile** des Datensatzes (letzter vorliegender CoT-Bericht) durch den trainierten Baum geführt:

```python
last_X = df[FEATURE_COLS].iloc[-1].values.reshape(1, -1)
pred   = clf.predict(last_X)[0]         # 0 oder 1
proba  = clf.predict_proba(last_X)[0]   # [P(fällt), P(steigt)]
```

---

## 7. Pre-Computation beim Dashboard-Start

Beim Start von `Dash_Lokal.py` werden alle Modelle **einmalig vorberechnet** und im Dictionary `_dt_results` gespeichert:

```python
_dt_results: dict = {}   # { market_name → Ergebnis-Dict }

for _mkt in df_pivoted['Market Names'].unique():
    _pcol = _ppci_get_price_col(_mkt)  # z.B. 'gold_close'
    if _pcol is None or ...:
        continue                        # kein Preis → überspringen

    _dff    = df_pivoted[df_pivoted['Market Names'] == _mkt].copy()
    _result = train_decision_tree(_dff, df_futures_prices, _pcol)
    if _result is not None:
        _dt_results[_mkt] = _result
```

**Warum Pre-Computation?**  
Das Training eines Entscheidungsbaums und das Rendering des Baum-Bildes (matplotlib → PNG → base64) dauern pro Rohstoff einige Sekunden. Würde dies bei jedem Dropdown-Wechsel im Callback ausgeführt, wäre die UI spürbar träge. Die einmalige Berechnung beim Start hält das Dashboard responsiv.

Dieses Muster ist identisch mit der Shapley-Owen-Vorberechnung (`_shapley_results`) im selben File.

### Struktur des Ergebnis-Dicts

```python
{
    "model":          DecisionTreeClassifier,      # trainiertes Modell
    "feature_labels": ["Netto MM", "Netto Prod/Merc", ...],  # lesbare Namen
    "prediction":     1,           # 1 = steigt, 0 = fällt
    "proba":          [0.41, 0.59],# [P(fällt), P(steigt)]
    "n_samples":      194,         # Anzahl Trainingsbeobachtungen
    "last_date":      Timestamp,   # Datum des aktuellsten CoT-Berichts
}
```

---

## 8. Dashboard-Integration (Layout & Callback)

### Layout-Sektion

Der neue Bereich wird am Ende des Dashboards eingefügt – nach der Shapley-Owen-Sektion, vor dem Footer. Er besteht aus:

1. **Accordion** mit aufklappbarer Beschreibung und Formelübersicht
2. **Prognose-Alert** (`dbc.Alert`) – farbcodiert (grün/rot)
3. **`html.Img`** – zeigt das Baum-Bild als eingebettetes base64-PNG
4. **`dcc.Graph`** – zeigt das Feature-Importance-Diagramm

### Callback

```python
@app.callback(
    [
        Output('dt-prediction-text',    'children'),
        Output('dt-tree-image',         'src'),
        Output('dt-feature-importance', 'figure'),
    ],
    [Input('market-dropdown', 'value')]
)
def update_decision_tree(selected_market):
    ...
```

Der Callback wird durch dasselbe **`market-dropdown`** ausgelöst wie alle anderen Dashboard-Sektionen. Bei einem Dropdown-Wechsel werden Prognosetext, Baum-Bild und Feature-Importance-Diagramm synchron aktualisiert.

Da die Modelle vorberechnet sind, liest der Callback nur aus `_dt_results` und rendert lediglich das Bild und die Plotly-Figur neu – dies ist sehr schnell.

---

## 9. Visualisierungen und deren Interpretation

### 9.1 Entscheidungsbaum (Baumdiagramm)

Das Baumdiagramm visualisiert die Entscheidungsregeln, die das Modell aus den historischen Daten gelernt hat. Es ist die direkte Darstellung des trainierten `DecisionTreeClassifier`-Objekts.

#### Aufbau eines Knotens

Jeder Knoten im Baum zeigt vier Informationen:

```
┌─────────────────────────────┐
│  Δ Netto MM <= 433.0        │  ← Entscheidungsregel (Split-Kriterium)
│  gini = 0.497               │  ← Unreinheit (Gini-Koeffizient)
│  samples = 194              │  ← Anzahl Beobachtungen in diesem Knoten
│  value = [105, 89]          │  ← [Anzahl "fällt", Anzahl "steigt"]
│  class = fällt              │  ← Mehrheitsklasse im Knoten
└─────────────────────────────┘
```

#### Entscheidungsregel (Split-Kriterium)

Die erste Zeile jedes inneren Knotens zeigt, nach welchem Feature und welchem Schwellenwert der Datensatz aufgeteilt wird:

- **True-Pfad** (linker Ast): Bedingung ist erfüllt (Wert ≤ Schwellenwert)
- **False-Pfad** (rechter Ast): Bedingung ist nicht erfüllt (Wert > Schwellenwert)

**Beispiel:**  
`Δ Netto MM <= 433.0` bedeutet: Hat sich die Managed-Money-Netto-Position in der letzten Woche um weniger als 433 Kontrakte verändert? Falls ja → linker Ast, falls nein → rechter Ast.

#### Gini-Koeffizient

Der **Gini-Koeffizient** misst die Unreinheit eines Knotens:

$$\text{Gini} = 1 - \sum_{k} p_k^2 = 2 \cdot p_{\text{steigt}} \cdot p_{\text{fällt}}$$

- **Gini = 0.0:** Reiner Knoten – alle Beobachtungen gehören zur selben Klasse (perfekte Trennung)
- **Gini = 0.5:** Maximale Unreinheit – beide Klassen sind gleich häufig vertreten (50/50)
- **Gini = 0.497:** Fast maximale Unreinheit → der Knoten trennt kaum

Ein Baum versucht, bei jedem Split den Gini-Koeffizient im resultierenden Teilbaum zu minimieren. Je schneller die Gini-Werte auf dem Weg zur Wurzel auf 0 sinken, desto trennschärfer sind die Features.

#### Samples

Gibt an, wie viele der Trainingsbeobachtungen in diesen Knoten geflossen sind. An der Wurzel = alle verfügbaren Beobachtungen. In Blattknoten sind es typischerweise deutlich weniger.

#### Value

`value = [105, 89]` bedeutet: Von den 194 Beobachtungen in diesem Knoten haben 105 die Klasse "fällt" (y=0) und 89 die Klasse "steigt" (y=1).

#### Farbkodierung

- **Blaue Töne:** Mehrheitsklasse ist "steigt" (y=1). Je tiefer die Farbe, desto höher ist der Anteil der "steigt"-Klasse.
- **Orange/Braune Töne:** Mehrheitsklasse ist "fällt" (y=0). Je dunkler, desto dominanter ist die "fällt"-Klasse.
- **Weiss/Hellgrau:** Ausgeglichene Verteilung (~50/50)

#### Blattknoten

Knoten ohne weitere Verzweigung sind **Blattknoten** (Endknoten). Jeder Datenpunkt landet durch das Traversieren des Baums in genau einem Blattknoten. Die **Mehrheitsklasse** des Blattknotens ist die Vorhersage des Modells für alle Datenpunkte, die in diesen Knoten fallen.

#### Wie liest man den Pfad zur Prognose?

Um zu verstehen, warum das Modell eine bestimmte Prognose liefert, verfolgt man den Pfad von der Wurzel bis zum Blattknoten, in dem die aktuellste Beobachtung landet:

1. **Wurzel:** Trifft die erste Bedingung zu?
2. Falls ja → linker Ast, falls nein → rechter Ast
3. Weiter mit der nächsten Bedingung, bis ein Blattknoten erreicht ist
4. Die Mehrheitsklasse des Blattknotens ist die Vorhersage

---

### 9.2 Feature Importance (Balkendiagramm)

Das horizontale Balkendiagramm zeigt, welche Features der Entscheidungsbaum als **wichtig** für seine Entscheidungen eingestuft hat.

#### Berechnung der Feature Importance

Die Importance basiert auf der **mittleren Gini-Reduktion** (Mean Decrease in Impurity), die ein Feature über alle Splits im Baum bewirkt:

$$\text{Importance}(f) = \sum_{t \in \text{Splits mit } f} \frac{n_t}{n} \cdot \Delta\text{Gini}(t)$$

- $n_t$ = Anzahl Beobachtungen im Knoten $t$
- $n$ = Gesamtzahl Trainingsbeobachtungen  
- $\Delta\text{Gini}(t)$ = Reduktion des Gini-Koeffizienten durch den Split bei Knoten $t$

Die Importances werden normiert, sodass ihre Summe **1.0** ergibt:

$$\sum_{f} \text{Importance}(f) = 1.0$$

#### Interpretation

| Importance-Wert | Bedeutung |
|---|---|
| 0.0 | Feature wurde für keinen Split verwendet → kein Informationsgehalt für diesen Rohstoff und Zeitraum |
| 0.01–0.05 | Marginale Bedeutung |
| 0.05–0.15 | Moderate Bedeutung |
| > 0.15 | Starke Bedeutung – dieses Feature treibt die Entscheidungen massgeblich |

**Beispiel (Palladium aus dem Screenshot):**

- `Δ Netto MM` (~0.26): Die **Wochenveränderung** der Managed-Money-Netto-Position ist das wichtigste Signal. Wenn MM ihre Positionen stark ausbauen oder abbauen, ist das ein starkes Prognose-Signal für Palladium.
- `Z-Score Netto MM` (~0.22): Extreme Positionierungen (im Verhältnis zur Quartals-Historie) sind ebenfalls hochrelevant.
- `Netto Prod/Merc` (~0.20): Die Netto-Position der Produzenten/Händler enthält ebenfalls wesentliche Information.
- `% MM Long/Short (OI)` (~0.15 / ~0.14): Der relative Anteil am Open Interest hat moderate Bedeutung.
- `Δ % MM Long`, `Netto Swap`, `Netto MM` (~0.0): Diese Features tragen für Palladium kaum zur Entscheidungsfindung bei.

> **Wichtig:** Die Feature Importance ist **modell- und rohstoffspezifisch**. Für Gold können völlig andere Features dominant sein als für Palladium. Die Importances sind nicht als universelle Wahrheit zu verstehen, sondern als Reflexion der historischen Muster in den Daten des jeweiligen Rohstoffs.

---

## 10. Interpretation des Prognosesatzes

### Aufbau des Prognose-Alerts

```
Prognose: Das Entscheidungsbaum-Modell prognostiziert für [Rohstoff]
in der nächsten Woche [steigende / fallende] Preise.
(Modell-Konfidenz: XX.X %, basierend auf CoT-Daten vom TT.MM.JJJJ)
```

### Prognose-Richtung

- **Grüner Alert → steigende Preise:** Der Baum hat die aktuellste Beobachtung in einen Blattknoten geleitet, dessen Mehrheitsklasse "steigt" (y=1) ist.
- **Roter Alert → fallende Preise:** Der Baum hat die aktuellste Beobachtung in einen Blattknoten geleitet, dessen Mehrheitsklasse "fällt" (y=0) ist.

### Modell-Konfidenz

Die Konfidenz ist die **relative Häufigkeit der Mehrheitsklasse im Blattknoten**, in dem die aktuellste Beobachtung landet:

$$\text{Konfidenz} = \frac{\text{Anzahl Trainingsbeobachtungen der Mehrheitsklasse im Blattknoten}}{\text{Gesamtanzahl Trainingsbeobachtungen im Blattknoten}} \times 100$$

**Berechnung im Code:**

```python
proba = clf.predict_proba(last_X)[0]   # [P(fällt), P(steigt)]
conf_pct = proba[pred] * 100           # Wahrscheinlichkeit der Vorhersage-Klasse
```

`predict_proba` gibt für jeden Blattknoten die relativen Häufigkeiten der Klassen zurück, die der Baum bei diesem Blattknoten im Training gesehen hat. Bei `value = [12, 3]` wäre die Konfidenz für "fällt" = 12/15 × 100 = 80 %.

### Beispiel aus dem Screenshot (Palladium)

```
Prognose: Das Entscheidungsbaum-Modell prognostiziert für Palladium
in der nächsten Woche fallende Preise.
(Modell-Konfidenz: 58.7 %, basierend auf CoT-Daten vom 10.03.2026)
```

- **Datum `10.03.2026`:** Der aktuellste vorliegende CoT-Bericht stammt von diesem Datum. Auf Basis dieser Positionierungsdaten wurde die Prognose berechnet.
- **Konfidenz 58.7 %:** Im Blattknoten, in dem die aktuelle Palladium-Beobachtung landet, haben 58.7 % der historischen Trainingsbeobachtungen dieses Knotens auf eine fallende Preisbewegung in der Folgewoche hingedeutet.
- **Interpretation:** Eine Konfidenz von 58.7 % ist nur **leicht über dem Zufallsniveau von 50 %**. Das Signal ist schwach; der Markt befindet sich in einem Bereich, in dem das Modell keine klare Richtung ableiten kann.

### Konfidenz-Referenzwerte

| Konfidenz | Interpretation |
|---|---|
| 50–55 % | Sehr schwaches Signal – nahezu zufällig |
| 56–65 % | Schwaches Signal – leichte Tendenz |
| 66–75 % | Moderates Signal – erkennbare Tendenz |
| 76–85 % | Starkes Signal – klare historische Tendenz |
| > 85 % | Sehr starkes Signal – der Blattknoten ist fast rein |

> **Wichtig:** Eine hohe Konfidenz bedeutet nicht zwingend, dass die Prognose korrekt ist. Sie bedeutet nur, dass der Baum die aktuelle Situation in einen Bereich einordnet, in dem historisch häufig eine bestimmte Preisbewegung folgte.

### Was bedeutet das Datum?

Das Datum im Prognosesatz ist das Datum des **letzten vollständigen CoT-Berichts** im Datensatz. Da CoT-Berichte wöchentlich (dienstags) veröffentlicht werden, liegt dieses Datum typischerweise wenige Tage zurück. Die Prognose bezieht sich auf die Woche **nach diesem Berichtsdatum**.

---

## 11. Wichtige Einschränkungen

### Keine Modellvalidierung dargestellt

Bewusst nicht implementiert sind Confusion Matrix, Accuracy, Precision, Recall und F1-Score. Das Dashboard dient der **Prognose-Darstellung**, nicht der Modellbewertung.

### Look-Ahead-Bias vermieden

Durch die Verwendung von `shift(-1)` für die Zielvariable und das anschliessende Entfernen der letzten Zeile aus dem Training ist sichergestellt, dass das Modell nie Zukunftsinformationen gesehen hat. Die Prognose wird ausschliesslich auf der letzten Zeile durchgeführt, für die die Zukunft unbekannt ist.

### Trainiert auf dem Gesamtdatensatz

Das Modell wird auf **allen verfügbaren historischen Daten** trainiert (kein Train/Test-Split). Dies maximiert die Informationsmenge für das Training, bedeutet aber auch, dass keine unabhängige Testmenge zur Verfügung steht. Die Konfidenz-Werte basieren auf den Blattknoten-Häufigkeiten aus dem Trainingsdatensatz.

### Stationarität und strukturelle Brüche

Entscheidungsbäume gehen implizit davon aus, dass die historischen Muster in den Daten auch in Zukunft gelten. Bei strukturellen Marktveränderungen (Regulierung, neue Marktteilnehmer, geopolitische Schocks) kann die Prognosegüte sinken, ohne dass dies am Modell direkt erkennbar ist.

### Keine Berücksichtigung von Marktpreisen als Feature

Die Futures-Preise werden **nur** für die Zielvariablen-Berechnung verwendet, nicht als Feature. Das Modell basiert ausschliesslich auf Positionierungsdaten.

### Neuberechnung bei Dashboard-Neustart

Die Modelle werden nur beim Start des Dashboards berechnet. Um ein aktualisiertes Modell mit den neuesten CoT-Daten zu erhalten, muss das Dashboard neu gestartet werden (nach einem Pipeline-Run, der neue Daten in die InfluxDB geschrieben hat).
