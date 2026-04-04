# Shapley-Owen Decomposition – Technische Dokumentation

**Projekt:** CoT-Dashboard (DIFA InfluxDB v3)
**Datum:** 2026-03-30
**Betrifft:** `src/analysis/shapley_owen.py` · `Dash_Lokal.py` (Sektion am Ende)

---

## Inhaltsverzeichnis

1. [Motivation und Ziel](#1-motivation-und-ziel)
2. [Theoretischer Hintergrund](#2-theoretischer-hintergrund)
   - 2.1 [Kooperative Spieltheorie und Shapley-Werte](#21-kooperative-spieltheorie-und-shapley-werte)
   - 2.2 [Übertragung auf R² (Bestimmtheitsmass)](#22-übertragung-auf-r-bestimmtheitsmass)
   - 2.3 [Mathematische Formel](#23-mathematische-formel)
   - 2.4 [Eigenschaften der Shapley-Zerlegung](#24-eigenschaften-der-shapley-zerlegung)
3. [Daten und Variablen](#3-daten-und-variablen)
   - 3.1 [Zielvariable Y](#31-zielvariable-y)
   - 3.2 [Prädiktoren X (Netto-Positionierungen)](#32-prädiktoren-x-netto-positionierungen)
4. [Implementierung](#4-implementierung)
   - 4.1 [Modulstruktur](#41-modulstruktur)
   - 4.2 [Kernfunktion `_r2_ols`](#42-kernfunktion-_r2_ols)
   - 4.3 [Kernfunktion `_compute_shapley_values`](#43-kernfunktion-_compute_shapley_values)
   - 4.4 [Öffentliche API `compute_rolling_shapley`](#44-öffentliche-api-compute_rolling_shapley)
   - 4.5 [Integration in `Dash_Lokal.py`](#45-integration-in-dash_lokalpy)
5. [Rollende Berechnung (52-Wochen-Fenster)](#5-rollende-berechnung-52-wochen-fenster)
6. [Visualisierungen und deren Interpretation](#6-visualisierungen-und-deren-interpretation)
   - 6.1 [Zeitreihen-Chart](#61-zeitreihen-chart)
   - 6.2 [Balkendiagramm](#62-balkendiagramm)
   - 6.3 [Tabelle](#63-tabelle)
7. [Interpretation der Ergebnisse am Beispiel Gold](#7-interpretation-der-ergebnisse-am-beispiel-gold)
8. [Grenzen und Einschränkungen](#8-grenzen-und-einschränkungen)
9. [Erweiterungsmöglichkeiten](#9-erweiterungsmöglichkeiten)

---

## 1. Motivation und Ziel

Das CoT-Dashboard zeigt Positionierungsdaten der vier CFTC-Händlergruppen (PMPU, SD, MM, OR). Eine naheliegende Folgefrage ist:

> **Welche Händlergruppe erklärt die Preisbewegungen am stärksten – und in welchem Ausmass?**

Die **Shapley-Owen Decomposition** beantwortet genau diese Frage. Sie zerlegt die gesamte Erklärungskraft eines linearen Regressionsmodells (gemessen als R²) fair und eindeutig auf die einzelnen Prädiktoren auf.

Das Ziel ist nicht Prognose, sondern **Attribution**: Welcher Anteil der erklärten Preisvarianz lässt sich welcher Händlergruppe zuschreiben?

---

## 2. Theoretischer Hintergrund

### 2.1 Kooperative Spieltheorie und Shapley-Werte

Die Grundidee stammt aus der **kooperativen Spieltheorie** (Lloyd Shapley, 1953). In einem Koalitionsspiel gibt es:

- eine Menge von **Spielern** (hier: die vier Händlergruppen)
- eine **charakteristische Funktion** `v(S)`, die jeder Koalition (Teilmenge) `S` einen Wert zuordnet (hier: R² der Regression mit diesen Prädiktoren)

Der **Shapley-Wert** eines Spielers ist sein fairer Anteil am Gesamtgewinn, definiert als der gewichtete Durchschnitt seiner **Grenzbeiträge** über alle möglichen Koalitionen.

Die Fairness-Axiome, die Shapley-Werte eindeutig charakterisieren, sind:

| Axiom | Bedeutung |
|-------|-----------|
| **Effizienz** | Die Summe aller Shapley-Werte ist gleich dem Gesamtwert `v(N)` |
| **Symmetrie** | Identische Spieler erhalten identische Werte |
| **Nullspieler** | Ein Spieler, der nichts beiträgt, erhält 0 |
| **Linearität** | Shapley-Werte addieren sich linear über Spiele |

### 2.2 Übertragung auf R² (Bestimmtheitsmass)

In der Regressionsanalyse mit `N` Prädiktoren definieren wir:

- **Spieler** = Händlergruppen {PMPU, SD, MM, OR}
- **Charakteristische Funktion** = `v(S) = R²(Y ~ X_S)`
  d.h. der R²-Wert der OLS-Regression der Preisrenditen auf die Netto-Positionierungen der Teilmenge `S`
- **Leeres Spiel**: `v(∅) = 0` (keine Prädiktoren → kein Modell → kein R²)

Der Shapley-Wert `φ_i` einer Gruppe misst dann ihren **fairen Beitrag zur gesamten Erklärungskraft R²** des Vollmodells.

### 2.3 Mathematische Formel

Für Prädiktor `i` aus der Menge `N = {1, 2, 3, 4}`:

$$
\varphi_i \;=\;
\sum_{S \,\subseteq\, N \setminus \{i\}}
\frac{|S|!\;(N - |S| - 1)!}{N!}
\;\Bigl[\,R^2(S \cup \{i\}) - R^2(S)\,\Bigr]
$$

**Schritt für Schritt erklärt:**

1. **Alle Koalitionen `S`** ohne Spieler `i` werden aufgezählt.
   Bei N=4 gibt es pro Spieler `i` genau **8 solcher Koalitionen** (Teilmengen der 3 übrigen Spieler).

2. **Grenzbeitrag** von `i` in Koalition `S`:
   `R²(S ∪ {i}) − R²(S)` — um wie viel steigt R², wenn Spieler `i` zur Koalition `S` hinzukommt?

3. **Shapley-Gewicht**:
   `|S|! · (N−|S|−1)! / N!`
   Dieses Gewicht entspricht der Wahrscheinlichkeit, dass Spieler `i` an genau der Stelle in einer zufälligen Reihenfolge eintritt, die der Koalition `S` entspricht.

4. **Aufsummierung** über alle Koalitionen `S` ergibt den Shapley-Wert `φ_i`.

**Numerisches Beispiel für N=4 (Gewichte):**

| Koalitionsgrösse \|S\| | Anzahl Koalitionen | Gewicht pro Koalition |
|---|---|---|
| 0 | 1 | `0! · 3! / 4! = 6/24 = 0.250` |
| 1 | 3 | `1! · 2! / 4! = 2/24 = 0.083` |
| 2 | 3 | `2! · 1! / 4! = 2/24 = 0.083` |
| 3 | 1 | `3! · 0! / 4! = 6/24 = 0.250` |

Die grössten Koalitionen (Grösse 0 und 3) haben das höchste Gewicht — sie repräsentieren die «extremsten» Situationen: Spieler `i` tritt entweder als Erster oder als Letzter ein.

### 2.4 Eigenschaften der Shapley-Zerlegung

- **Effizienz (wichtigste Eigenschaft):**
  `φ_PMPU + φ_SD + φ_MM + φ_OR = R²(Vollmodell)`
  Die Summe der vier Shapley-Werte ist exakt gleich dem R² der Regression mit allen vier Prädiktoren.

- **Negative Werte sind möglich:**
  Wenn eine Gruppe in Kombination mit anderen die Erklärungskraft *reduziert* (z.B. durch starke Kollinearität oder Gegenläufigkeit), kann ihr Shapley-Wert negativ sein. Das ist mathematisch korrekt und kein Fehler.

- **Kein R²-Additiv im einfachen Sinne:**
  Die Shapley-Werte sind **nicht** einfach die R²-Werte der einzelnen Einfachregressionen `Y ~ X_i`. Sie berücksichtigen die Überlappungen und Interaktionen zwischen allen Gruppen.

---

## 3. Daten und Variablen

### 3.1 Zielvariable Y

Die **absolute wöchentliche Futures-Preisänderung**:

$$
\Delta P_t = P_t - P_{t-1}
$$

- `P_t` = Schlusskurs des jeweiligen Futures-Kontrakts am CoT-Reportdatum `t` (Dienstag)
- Quelle: `df_futures_prices` (aus InfluxDB / YFinance)
- Preisspalten: `gold_close`, `silver_close`, `copper_close`, `platinum_close`, `palladium_close`
- Preis-Alignment via `merge_asof` (backward, Toleranz 7 Tage) — identisch zum bestehenden PPCI-Muster
- Implementierung: `_dff['_price_change'] = _dff['_close'].diff()`

Der Grund für Preisänderungen (statt Preisniveaus): Niveaus sind nicht-stationär und würden zu Scheinkorrelationen führen (spurious regression).

### 3.2 Prädiktoren X (Änderungen der Netto-Positionierungen)

Die **Änderung der Netto-Positionierung** (First Difference) jeder Händlergruppe:

$$
\Delta \text{Net}_G(t) = \text{Net}_G(t) - \text{Net}_G(t-1)
$$

$$
\text{Net}_G(t) = \text{Long}_G(t) - \text{Short}_G(t)
$$

in Anzahl Kontrakten (Open Interest).

| Kurzname | Gruppe | Berechnung |
|----------|--------|------------|
| `Δ PMPU Net` | Producer/Merchant/Processor/User | Δ(PMPU Long − PMPU Short) |
| `Δ SD Net` | Swap Dealer | Δ(SD Long − SD Short) |
| `Δ MM Net` | Managed Money | Δ(MM Long − MM Short) |
| `Δ OR Net` | Other Reportables | Δ(OR Long − OR Short) |

**Zweistufige Berechnung:**
1. Netto-Niveau: `Net_G(t) = Long_G(t) − Short_G(t)` (aus bestehenden Spalten `PMPUL Relative Concentration` etc.)
2. First Difference: `Δ Net_G(t) = Net_G(t) − Net_G(t−1)` (via `.diff()`)

**Warum First Differences?**
Netto-Positionierungs-Niveaus können Trends aufweisen (nicht-stationär). Die Verwendung von Änderungen stellt sicher, dass die Regression ökonometrisch korrekt ist und keine Scheinkorrelationen durch gemeinsame Trends entstehen. Zudem fragt die wirtschaftliche Logik nach der *Veränderung* der Positionierung: Wer baut Positionen auf oder ab — und geht das mit Preisbewegungen einher?

---

## 4. Implementierung

### 4.1 Modulstruktur

```
c:\DIFA_influxv3\
├── src\
│   └── analysis\
│       ├── __init__.py              # Paket-Marker
│       └── shapley_owen.py          # Berechnungslogik (NEU)
└── Dash_Lokal.py                    # Dashboard (erweitert)
```

Die Berechnungslogik wurde **bewusst ausgelagert** in `src/analysis/`, konsistent mit der bestehenden `src/services/`-Struktur. Vorteile:

- Testbarkeit (Unit-Tests ohne Dashboard)
- Wiederverwendbarkeit (z.B. in `Influx.py` oder Notebooks)
- Lesbarkeit (Dashboard-Datei bleibt auf Visualisierungslogik fokussiert)

### 4.2 Kernfunktion `_r2_ols`

```python
def _r2_ols(y: np.ndarray, X_cols: np.ndarray) -> float:
```

Berechnet das Bestimmtheitsmass R² einer OLS-Regression `y ~ X_cols` (mit Intercept).

**Implementierungsdetails:**

```python
Xc = np.column_stack([np.ones(len(y)), X_cols])   # Intercept hinzufügen
beta, _, _, _ = np.linalg.lstsq(Xc, y, rcond=None)  # Least-Squares-Lösung
y_hat = Xc @ beta                                   # Fitted Values

ss_res = sum((y - y_hat)²)   # Residualquadratsumme
ss_tot = sum((y - mean(y))²) # Gesamtquadratsumme

R² = 1 - ss_res / ss_tot
```

- **`np.linalg.lstsq`**: Robuste Least-Squares-Lösung, funktioniert auch bei fast-singulären Matrizen
- **`rcond=None`**: Nutzt maschinengenauigkeits-basierte Schwellenwerte für Singulärwerte
- **`clip(0, 1)`**: Verhindert numerische Artefakte (R² leicht < 0 oder > 1 durch Rundungsfehler)
- **Leere Teilmenge**: Bei `X_cols.shape[1] == 0` wird direkt `0.0` zurückgegeben

### 4.3 Kernfunktion `_compute_shapley_values`

```python
def _compute_shapley_values(y: np.ndarray, X: np.ndarray) -> np.ndarray:
```

Berechnet die Shapley-Werte für alle N Prädiktoren in einem gegebenen Datenfenster.

**Algorithmus:**

**Schritt 1 — R² aller 2^N Teilmengen vorberechnen (Cache):**

```python
r2_cache: dict[frozenset, float] = {}
for size in range(N + 1):                          # size = 0, 1, 2, 3, 4
    for subset in combinations(range(N), size):    # alle Teilmengen dieser Grösse
        key = frozenset(subset)
        r2_cache[key] = _r2_ols(y, X[:, list(subset)])
```

Für N=4 werden genau `2^4 = 16` R²-Werte berechnet und im Cache gespeichert. Der Cache verhindert redundante Berechnungen: jede Teilmenge wird nur einmal ausgewertet, auch wenn sie in den Shapley-Formeln mehrerer Spieler vorkommt.

**Schritt 2 — Shapley-Werte berechnen:**

```python
for i in range(N):                                  # für jeden Prädiktor i
    others = [j for j in range(N) if j != i]        # die anderen Spieler
    for size in range(N):                            # |S| = 0 bis N-1
        weight = factorial(size) * factorial(N - size - 1) / factorial(N)
        for subset in combinations(others, size):    # alle S ⊆ N\{i} mit |S|=size
            s_set = frozenset(subset)
            marginal = r2_cache[s_set | {i}] - r2_cache[s_set]
            phi[i] += weight * marginal
```

**Komplexität:** Für N=4 ergeben sich pro Schritt:
- 16 R²-Berechnungen (Schritt 1)
- 4 × 8 = 32 Gewichtungsoperationen (Schritt 2)
- Gesamtaufwand pro Zeitfenster: sehr gering

### 4.4 Öffentliche API `compute_rolling_shapley`

```python
def compute_rolling_shapley(
    df: pd.DataFrame,
    x_cols: list,
    y_col: str,
    window: int = 52,
    min_periods: int = 26,
) -> pd.DataFrame:
```

**Rückgabe-DataFrame:**

| Spalte | Typ | Bedeutung |
|--------|-----|-----------|
| `Date` | datetime | Datum des Endpunkts des Fensters |
| `PMPU Net` | float | Shapley-Wert φ_PMPU für dieses Fenster |
| `SD Net` | float | Shapley-Wert φ_SD |
| `MM Net` | float | Shapley-Wert φ_MM |
| `OR Net` | float | Shapley-Wert φ_OR |
| `R2_full` | float | R² des Vollmodells (= Summe der φ_i) |
| `R2_share_PMPU Net` | float | Anteil PMPU in % (φ_PMPU / R²_full × 100) |
| `R2_share_SD Net` | float | Anteil SD in % |
| `R2_share_MM Net` | float | Anteil MM in % |
| `R2_share_OR Net` | float | Anteil OR in % |

**Ablauf pro Datum t:**

```
1. Datenfenster: Zeilen [t - window + 1 .. t]  (max. 52 Beobachtungen)
2. NaN-Zeilen entfernen (fehlende Preise oder Positionsdaten)
3. Prüfung: mind. min_periods = 26 gültige Zeilen → sonst NaN ausgeben
4. _compute_shapley_values(y_window, X_window) → phi[4]
5. R²_full = _r2_ols(y_window, X_window)
6. R²_share_i = phi[i] / R²_full × 100  (falls R²_full > 0)
```

### 4.5 Integration in `Dash_Lokal.py`

**Import:**
```python
from src.analysis.shapley_owen import compute_rolling_shapley
```

**Spalten-Aliase** (nach der Berechnung der Relative-Concentration-Spalten):
```python
df_pivoted['PMPU Net'] = df_pivoted['PMPUL Relative Concentration']
df_pivoted['SD Net']   = df_pivoted['SDL Relative Concentration']
df_pivoted['MM Net']   = df_pivoted['MML Relative Concentration']
df_pivoted['OR Net']   = df_pivoted['ORL Relative Concentration']
```

**Startup-Precomputation** (einmalig beim App-Start, vor `app = dash.Dash(...)`):
```python
_shapley_results: dict = {}  # market_name → DataFrame

for _mkt in df_pivoted['Market Names'].unique():
    _pcol = _ppci_get_price_col(_mkt)          # z.B. 'gold_close'
    # ... merge_asof mit df_futures_prices ...
    _dff['_price_return'] = _dff['_close'].pct_change()
    _result = compute_rolling_shapley(_dff, _SHAPLEY_X_COLS, '_price_return')
    _shapley_results[_mkt] = _result
```

Der Grund für die Precomputation beim Start (statt im Callback): Die Shapley-Berechnung läuft über den gesamten 4-Jahres-Datensatz (~200 Wochen × 32 OLS-Regressionen pro Markt). Dies dauert sekunden-, nicht millisekunden­weise und sollte nicht bei jedem Filterklick neu ausgeführt werden.

**Callback:**
```python
@app.callback(
    [Output('shapley-timeseries-chart', 'figure'),
     Output('shapley-bar-chart',        'figure'),
     Output('shapley-table',            'data'),
     Output('shapley-r2-info',          'children')],
    [Input('market-dropdown',   'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')],
)
def update_shapley(selected_market, start_date, end_date):
    ...
```

Der Callback filtert die **vorberechneten** Shapley-Resultate nach Markt und Datumsbereich und rendert die drei Ausgaben.

---

## 5. Rollende Berechnung (52-Wochen-Fenster)

Die Berechnung erfolgt **rollend** über ein gleitendes Fenster von 52 Wochen (~1 Jahr). Das bedeutet:

- Für jeden Dienstag `t` in den Daten wird **nur** der Zeitraum `[t−51, t]` (die letzten 52 Beobachtungen) für die Regression verwendet.
- Die Shapley-Werte zu Datum `t` beschreiben also, welche Händlergruppe in den **letzten 52 Wochen** die Preisbewegungen am stärksten erklärt hat.
- Frühe Datenpunkte (weniger als `min_periods = 26` gültige Beobachtungen) erhalten `NaN` und erscheinen nicht im Chart.

**Warum 52 Wochen?**

- Konsistent mit dem bestehenden Dashboard (Clustering Indicator, Concentration Indicator verwenden ebenfalls 52-Wochen-Fenster)
- 52 Wochen = genau 1 Handelsjahr für wöchentliche Daten
- Ausreichend Beobachtungen für eine stabile OLS-Schätzung mit 4 Prädiktoren (52 >> 4+1 = 5 Freiheitsgrade)
- Reaktiv genug, um Regimewechsel (z.B. veränderte Marktstruktur) zu erfassen

**Visualisierung des Fensterprinzips:**

```
Zeitachse (wöchentlich):
──────────────────────────────────────────────────────►
         [─────── 52 Wochen ───────]
                  [─────── 52 Wochen ───────]
                           [─────── 52 Wochen ───────]
                  ↑                 ↑                 ↑
                φ(t₁)             φ(t₂)             φ(t₃)
```

Jeder Punkt im Zeitreihen-Chart repräsentiert eine vollständige Shapley-Zerlegung für das Fenster, das zu diesem Datum endet.

---

## 6. Visualisierungen und deren Interpretation

### 6.1 Zeitreihen-Chart

**Was zeigt er?**
Die Shapley-Werte der vier Händlergruppen als Zeitreihen, gefiltert nach dem gewählten Datumsbereich.

**X-Achse:** Datum (Dienstags-CoT-Reportdaten)
**Y-Achse:** Shapley-Wert φ (absolut, in Einheiten von R²)

**Farbzuordnung:**
| Linie | Farbe | Gruppe |
|-------|-------|--------|
| Orange | `#e6550d` | PMPU (Producer/Merchant) |
| Blau | `#3182bd` | SD (Swap Dealer) |
| Grün | `#31a354` | MM (Managed Money) |
| Violett | `#756bb1` | OR (Other Reportables) |

**Interpretation:**

- **Hohe Werte** einer Linie: Diese Gruppe erklärt in diesem Zeitraum überdurchschnittlich viel der Preisbewegungen.
- **Steigende Linie**: Die Erklärungskraft dieser Gruppe nimmt zu — ihre Positionierungsänderungen gehen stärker mit den Preisbewegungen einher.
- **Fallende Linie**: Abnehmender Zusammenhang zwischen der Positionierung dieser Gruppe und den Preisbewegungen.
- **Konvergenz der Linien**: In gewissen Perioden tragen alle Gruppen ähnlich viel bei — kein klarer «Leader».
- **Nulllinie (gestrichelt)**: Werte nahe 0 bedeuten, dass diese Gruppe kaum zur Erklärungskraft beiträgt.
- **Negative Werte** (unter Nulllinie): Die Positionierung dieser Gruppe schadet in Kombination mit anderen der Erklärungskraft (Kollinearität/Überlappung mit anderen Gruppen).

**Wichtig:** Die Werte sind *relativ* zu R² des Vollmodells. Ein Wert von 0.08 für MM bedeutet nicht, dass MM allein 8% der Preisvarianz erklärt, sondern dass MM in der Koalition aller Gruppen durchschnittlich 0.08 Einheiten R² beiträgt.

### 6.2 Balkendiagramm

**Was zeigt er?**
Die Shapley-Werte des **letzten Datums** im gewählten Zeitraum als Balkendiagramm.

**X-Achse:** Händlergruppe
**Y-Achse:** Shapley-Wert φ (absolut)

**Besondere Elemente:**

- **Gestrichelte horizontale Linie**: R² des Vollmodells (Summe aller Balken). Zeigt die gesamte Erklärungskraft des Modells.
- **Beschriftung**: Jeder Balken zeigt seinen φ-Wert auf 4 Dezimalstellen.
- **Farbe**: Standardfarben je Gruppe (wie im Zeitreihen-Chart). Negative Balken erscheinen rot.

**Interpretation:**

- Der **höchste Balken** ist die Gruppe mit dem grössten individuellen Erklärungsbeitrag.
- Die **Gesamthöhe** (Summe aller Balken = R²-Linie) zeigt, wie gut das Modell insgesamt die Preisbewegungen erklärt.
- Ein **niedriges R²** (z.B. 0.05–0.10) ist typisch für Wochendaten in effizienten Märkten — die Positionierungsdaten erklären einen kleinen, aber strukturell relevanten Teil der Preisvarianz.
- **Relative Höhen**: Der Balken-Vergleich ist aussagekräftiger als die absoluten Werte.

### 6.3 Tabelle

**Was zeigt sie?**
Dieselben Daten wie das Balkendiagramm, aber numerisch präzise und mit prozentualem Anteil.

**Spalten:**

| Spalte | Bedeutung |
|--------|-----------|
| **Händlergruppe** | Name der CFTC-Gruppe |
| **Shapley-Wert (φ)** | Absoluter Beitrag zum R² (4 Dezimalstellen) |
| **Anteil am R² (%)** | Prozentualer Anteil: `φ_i / R²_full × 100` |

**Letzte Zeile (Gesamt):**
Zeigt das R² des Vollmodells (= Summe der φ-Werte) und 100% als Summe der Anteile.

**Farbliche Hervorhebung:**
- **Rote Schrift**: Negative Shapley-Werte (φ < 0)
- **Blauer Hintergrund**: Gesamtzeile (R²)
- **Grauer Hintergrund**: Alternierende Zeilen (Lesbarkeit)

**Unter der Tabelle** wird angezeigt: Fenstergrösse · Datum des letzten Werts · R² des Vollmodells.

---

## 7. Interpretation der Ergebnisse am Beispiel Gold

Basierend auf dem Screenshot (Datum: 2026-03-10, 52-Wochen-Fenster):

| Gruppe | φ | Anteil |
|--------|---|--------|
| PMPU | 0.0057 | 7.0% |
| **SD** | **0.0313** | **38.9%** |
| MM | 0.0295 | 36.6% |
| OR | 0.0141 | 17.5% |
| **Gesamt (R²)** | **0.0806** | **100%** |

**Lesart:**

- **R² = 0.0806**: Das Modell erklärt rund **8.1%** der wöchentlichen Goldpreisrenditevarianz mit den vier Netto-Positionierungen. Das ist für Wochendaten in einem effizienten Markt ein realistischer und interpretierbarer Wert — keine Überanpassung.

- **SD (38.9%) und MM (36.6%)** sind mit Abstand die beiden wichtigsten Gruppen in diesem Fenster. Zusammen erklären sie ~75% der gesamten Erklärungskraft. Das bedeutet: Die Netto-Positionierungsänderungen von Swap Dealern und Managed-Money-Fonds gehen im letzten Jahr am stärksten mit den Goldpreisbewegungen einher.

- **OR (17.5%)** leistet einen moderaten, aber nicht vernachlässigbaren Beitrag.

- **PMPU (7.0%)** trägt kaum zur Erklärungskraft bei. Das ist typisch: Producer/Merchants hedgen strukturell und reagieren langsam auf Preisbewegungen — ihre Positionierungsänderungen sind weniger mit kurzfristigen Preisrenditen korreliert.

**Aus dem Zeitreihen-Chart** (2022–2026) ist ersichtlich:

- Bis Mitte 2024 waren die Shapley-Werte aller Gruppen relativ hoch (0.05–0.15) und nahe beieinander — der Markt war erklärbar, und die Erklärungskraft war breiter verteilt.
- Ab Mitte 2024 sanken die Werte aller Gruppen stark, mit einem Minimum um Juli 2025. Dies deutet auf eine Phase hin, in der die Netto-Positionierungen kaum noch mit den Preisbewegungen zusammenhingen — möglicherweise dominierten externe Faktoren (Makro, Geopolitik), die nicht in den CoT-Daten erfasst sind.
- Ab Ende 2025 steigen die Werte wieder leicht an — die Positionierungen gewinnen wieder an Erklärungskraft.

---

## 8. Grenzen und Einschränkungen

| Einschränkung | Erläuterung |
|---------------|-------------|
| **Lineares Modell** | OLS unterstellt einen linearen Zusammenhang zwischen Netto-Positionierungen und Preisrenditen. Nichtlineare Zusammenhänge werden nicht erfasst. |
| **Kausalität** | Shapley-Werte messen Korrelation, keine Kausalität. Ein hoher Beitrag von MM bedeutet nicht, dass MM-Händler die Preise treiben — es kann auch umgekehrt sein. |
| **Kollinearität** | Bei hoher Korrelation zwischen den Netto-Positionierungen verschiedener Gruppen können die Shapley-Werte instabil werden und negative Werte annehmen. Die Summe bleibt korrekt, aber individuelle Werte schwanken stärker. |
| **Stationarität** | Preisrenditen sind stationärer als Preisniveaus, aber absolute Netto-Positionen können Trends aufweisen. Dies kann die Ergebnisse beeinflussen. |
| **R² als Masszahl** | R² misst die lineare Erklärungskraft. Ein tiefes R² (z.B. 0.08) bedeutet nicht, dass die Positionierungen «unwichtig» sind, sondern dass lineare Zusammenhänge mit wöchentlichen Renditen begrenzt sind — was für effiziente Märkte erwartet wird. |
| **52-Wochen-Fenster** | Das Fenster unterstellt, dass die Beziehungen innerhalb von 52 Wochen stabil sind. Bei Regimewechseln innerhalb des Fensters werden vergangenheits- und gegenwartsbezogene Werte vermischt. |

---

## 9. Erweiterungsmöglichkeiten

Die Implementierung ist bewusst generisch gehalten (`x_cols`, `y_col` als Parameter). Mögliche Erweiterungen:

| Erweiterung | Aufwand | Vorgehen |
|-------------|---------|----------|
| **Gross Positioning** (Long/Short separat) | Gering | Weitere Spalten in `_SHAPLEY_X_COLS` definieren und als Prädiktoren übergeben |
| **Andere Zielvariable** (z.B. OI-Veränderung) | Gering | `y_col` in der Precomputation-Schleife ändern |
| **Fenstergrösse wählbar** | Mittel | Radio-Button im Dashboard + `_SHAPLEY_WINDOW`-Parameter anpassen |
| **Makro-Variablen als Prädiktoren** (VIX, DXY) | Mittel | Merge mit `df_macro`, dann Spalten zu `x_cols` hinzufügen |
| **Owen-Zerlegung** (Gruppen von Prädiktoren) | Mittel | In `shapley_owen.py` die Gruppenstruktur als Parameter einführen; Owen-Gewichte anpassen |
| **Bootstrap-Konfidenzintervalle** | Hoch | Pro Fenster mehrfache Bootstrap-Stichproben ziehen und φ-Verteilung schätzen |
| **Andere Fenstergrössen vergleichen** | Mittel | Mehrere `compute_rolling_shapley`-Aufrufe mit verschiedenen `window`-Werten |

---

*Dokumentation erstellt im Rahmen der Shapley-Owen-Integration ins CoT-Dashboard.*
