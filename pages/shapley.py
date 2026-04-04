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
Der **Shapley-Owen Decomposition** Indikator zerlegt die Erklärungskraft (R²) eines
linearen Regressionsmodells in die individuellen Beiträge der vier CFTC-Händlergruppen.

**Modell:**
Die wöchentliche Preisrendite (Zielvariable Y) wird durch die **Netto-Positionierungen**
(Long − Short) der vier Gruppen erklärt:

- **PMPU** – Producer/Merchant/Processor/User
- **SD** – Swap Dealer
- **MM** – Managed Money
- **OR** – Other Reportables

**Interpretation:**
- Ein hoher Shapley-Wert einer Gruppe bedeutet, dass deren Netto-Positionierung
  besonders viel zur Erklärung der Preisbewegungen beiträgt.
- Negative Werte treten auf, wenn eine Variable die Erklärungskraft im Zusammenspiel
  mit anderen Variablen *reduziert* (Kollinearität / gegenseitige Überlappung).
- Die Summe aller Shapley-Werte entspricht dem R² des Vollmodells.

**Rollend:** Die Berechnung erfolgt auf einem gleitenden 52-Wochen-Fenster.
Das Zeitreihendiagramm zeigt, wie sich die Beiträge im Zeitverlauf verändern.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
**Shapley-Wert für Prädiktor** $i$ (exakte Formel):

$$
\varphi_i \;=\;
\sum_{S \subseteq N \setminus \{i\}}
\frac{|S|!\;(N-|S|-1)!}{N!}
\Bigl[R^2\!\bigl(S \cup \{i\}\bigr) - R^2(S)\Bigr]
$$

**Variablen:**
- $N$ – Anzahl Prädiktoren ($N = 4$)
- $S$ – Teilmenge der übrigen Prädiktoren (Koalition)
- $R^2(S)$ – Bestimmtheitsmass der linearen Regression $Y \sim X_S$
- $Y$ – wöchentliche Futures-Preisrendite: $r_t = \frac{P_t - P_{t-1}}{P_{t-1}}$
- $X_i$ – Netto-Positionierung der Gruppe $i$: $\text{Long}_i - \text{Short}_i$

**Eigenschaft:** $\sum_{i=1}^{N} \varphi_i = R^2(Y \sim X_1, \ldots, X_N)$

Für $N = 4$ werden alle $2^4 = 16$ Koalitionen explizit berechnet (exakter Algorithmus).
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
