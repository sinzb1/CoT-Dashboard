from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc


def layout():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H1("Shapley-Owen Decomposition – Net Positioning", className="mt-3"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
Der **Shapley-Owen Decomposition** Indikator zerlegt die Erklärungskraft ($R^2$) eines
linearen Regressionsmodells in die individuellen Beiträge der vier CFTC-Händlergruppen.

**Modell:**
Die wöchentliche **Preisänderung** $\Delta P_t$ (Zielvariable) wird durch die
**Differenzen der Netto-Positionierungen** $\Delta x_{G,t}$ (Long − Short, jeweils
$t$ vs. $t-1$) der vier Gruppen erklärt:

- **PMPU** – Producer/Merchant/Processor/User
- **SD** – Swap Dealer
- **MM** – Managed Money
- **OR** – Other Reportables

**Interpretation:**
- Ein hoher Shapley-Wert einer Gruppe bedeutet, dass deren Netto-Positionierungs-
  änderung besonders viel zur Erklärung der Preisbewegungen beiträgt.
- Negative Werte treten auf, wenn eine Variable die Erklärungskraft im Zusammenspiel
  mit anderen Variablen *reduziert* (Kollinearität / gegenseitige Überlappung).
- Die Summe aller Shapley-Werte entspricht dem $R^2$ des Vollmodells.

**Rollend:** Die Berechnung erfolgt auf einem gleitenden 52-Wochen-Fenster.
Das Zeitreihendiagramm zeigt, wie sich die Beiträge im Zeitverlauf verändern.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
**Vollständiges Regressionsmodell der wöchentlichen Preisänderung auf die Netto-Position:**

$$
\Delta P_t = \alpha
+ \beta_{\mathrm{PMPU}}\,\Delta x_{\mathrm{PMPU},t}
+ \beta_{\mathrm{SD}}\,\Delta x_{\mathrm{SD},t}
+ \beta_{\mathrm{MM}}\,\Delta x_{\mathrm{MM},t}
+ \beta_{\mathrm{OR}}\,\Delta x_{\mathrm{OR},t}
+ \varepsilon_t
$$

**Allgemeine Form eines Teilmodells $S$ der Shapley-Owen-Zerlegung:**

$$
\Delta P_t = \alpha_S + \sum_{G \in S} \beta_{G,S}\,\Delta x_{G,t} + \varepsilon_{S,t}
$$

**Shapley-Owen-Beitrag einer Variable als gewichtete Summe der marginalen Beiträge:**

$$
\varphi_i = \sum_{S \subseteq V \setminus \{i\}} w_i^{\,S} \cdot \bigl(R^2(S \cup \{i\}) - R^2(S)\bigr)
$$

**Gewichtungsfaktor der marginalen Beiträge (Fakultäts-Darstellung):**

$$
w_i^{\,S} = \frac{K!\,(n - K - 1)!}{n!}
$$

**Gewichtungsfaktor in Binomialkoeffizienten-Darstellung:**

$$
w_i^{\,S} = \frac{1}{n \cdot \binom{n-1}{K}}
$$

**Definition des Binomialkoeffizienten:**

$$
\binom{n-1}{K} = \frac{(n-1)!}{K!\,(n - 1 - K)!}
$$

**Relativer Anteil einer Variable am erklärten Varianzanteil:**

$$
\mathrm{Anteil}_i = \frac{\varphi_i}{R^2(V)} \times 100
$$

**Additivitätseigenschaft — Summe der Shapley-Owen-Werte ergibt das Gesamt-$R^2$:**

$$
\sum_{i \in V} \varphi_i = R^2(V)
$$

**Variablen und Begriffe:**
- $\Delta P_t$: wöchentliche absolute Preisänderung des Front-Month-Futures
- $\Delta x_{G,t}$: wöchentliche Änderung der Netto-Positionierung (Long − Short) der Gruppe $G$
- $V = \{\mathrm{PMPU},\, \mathrm{SD},\, \mathrm{MM},\, \mathrm{OR}\}$: Menge aller Prädiktoren
- $n = |V| = 4$: Anzahl Prädiktoren
- $S \subseteq V \setminus \{i\}$: Teilkoalition der übrigen Prädiktoren
- $K = |S|$: Grösse der Teilkoalition
- $\alpha,\, \alpha_S$: Intercepts des Voll- bzw. Teilmodells
- $\beta_{G},\, \beta_{G,S}$: Regressionskoeffizienten der Gruppe $G$ im Voll- bzw. Teilmodell
- $\varepsilon_t,\, \varepsilon_{S,t}$: Residuen des Voll- bzw. Teilmodells
- $R^2(S)$: Bestimmtheitsmass des Teilmodells mit Prädiktorset $S$
- $R^2(V)$: Bestimmtheitsmass des Vollmodells
- $w_i^{\,S}$: Gewicht der marginalen $R^2$-Differenz
- $\varphi_i$: Shapley-Owen-Beitrag der Variable $i$
- $\mathrm{Anteil}_i$: relativer Anteil von $i$ am erklärten Varianzanteil (in %)

Für $n = 4$ werden alle $2^n = 16$ Koalitionen explizit berechnet (exakter Algorithmus).
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                html.H2("Zeitverlauf der Shapley-Werte (52-Wochen-Fenster)", className="mt-2 mb-2"),
                dcc.Graph(id='shapley-timeseries-chart'),
                html.Br(),

                html.H2("Aktuellste Shapley-Werte (letztes Datum im gewählten Zeitraum)", className="mt-2 mb-2"),
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(id='shapley-bar-chart'),
                    ], width=7),
                    dbc.Col([
                        dash_table.DataTable(
                            id='shapley-table',
                            columns=[
                                {'name': 'Händlergruppe',    'id': 'group'},
                                {'name': 'Shapley-Wert (φ)', 'id': 'phi',   'type': 'numeric',
                                 'format': {'specifier': '.4f'}},
                                {'name': 'Anteil am R² (%)', 'id': 'share', 'type': 'numeric',
                                 'format': {'specifier': '.1f'}},
                            ],
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold',
                            },
                            style_cell={
                                'textAlign': 'left',
                                'padding': '8px',
                                'fontFamily': 'monospace',
                            },
                            style_data_conditional=[
                                {
                                    'if': {'filter_query': '{phi} < 0'},
                                    'color': '#d62728',
                                    'fontWeight': 'bold',
                                },
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(248, 248, 248)',
                                },
                                {
                                    'if': {'filter_query': '{group} = "Gesamt (R²)"'},
                                    'backgroundColor': 'rgb(220, 235, 255)',
                                    'fontWeight': 'bold',
                                },
                            ],
                        ),
                        html.Div(id='shapley-r2-info', className='mt-2',
                                 style={'fontSize': '13px', 'color': '#555'}),
                    ], width=5),
                ]),
                html.Br(),
            ], width=12)
        ]),
    ])
