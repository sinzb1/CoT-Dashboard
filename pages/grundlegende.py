from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

COL_DIFF_LONG    = 'Difference (Long %)'
COL_DIFF_SHORT   = 'Difference (Short %)'
COL_DIFF_SPREAD  = 'Difference (Spread %)'
COL_NUM_TRADERS  = 'Number of Traders'


def layout():
    return html.Div([
        # Sprungnavigation
        html.Div(
            [html.Span("Schnellnavigation: ", className="fw-semibold text-muted me-2 small align-middle")]
            + [html.A(lbl, href=f"#{anc}", className="btn btn-sm btn-outline-secondary me-2 mb-1")
               for lbl, anc in [
                   ("Market Overview", "section-market-overview"),
                   ("Clustering Indicator", "section-clustering"),
                   ("Position Size Indicator", "section-position-size"),
               ]],
            className="p-3 mb-4 bg-light border rounded"
        ),

        # Übersichtstabelle
        dbc.Row([
            dbc.Col([
                html.H2("Market Overview", className="mt-3 mb-3", id="section-market-overview"),
                dash_table.DataTable(
                    id='overview-table',
                    tooltip_delay=400,
                    tooltip_duration=None,
                    columns=[
                        {'name': 'Trader Group', 'id': 'Trader Group'},
                        {'name': 'Positions (OI)', 'id': 'Positions', 'presentation': 'markdown'},
                        {'name': 'Δ Long %', 'id': COL_DIFF_LONG},
                        {'name': 'Δ Short %', 'id': COL_DIFF_SHORT},
                        {'name': 'Δ Spread %', 'id': COL_DIFF_SPREAD},
                        {'name': 'Total Traders', 'id': 'Total Traders'},
                        {'name': '% of Traders', 'id': '% of Traders'},
                        {'name': COL_NUM_TRADERS, 'id': COL_NUM_TRADERS, 'presentation': 'markdown'},
                    ],
                    markdown_options={"html": True},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    css=[
                        {"selector": f'th[data-dash-column="{COL_NUM_TRADERS}"]',
                         "rule": "white-space: normal;"},
                        {"selector": f'th[data-dash-column="{COL_NUM_TRADERS}"] .column-header-name',
                         "rule": "display: block;"},
                        {"selector": f'th[data-dash-column="{COL_NUM_TRADERS}"]::after',
                         "rule": (
                             "content: 'Long   Short   Spread';"
                             "display: block;"
                             "margin-top: 4px;"
                             "font-size: 11px;"
                             "color: #444;"
                             "line-height: 1.3;"
                             "padding-left: 18px;"
                             "word-spacing: 26px;"
                             "background-image: "
                             "radial-gradient(circle, #2ca02c 0, #2ca02c 100%),"
                             "radial-gradient(circle, #d62728 0, #d62728 100%),"
                             "radial-gradient(circle, #1f77b4 0, #1f77b4 100%);"
                             "background-repeat: no-repeat;"
                             "background-size: 10px 10px, 10px 10px, 10px 10px;"
                             "background-position: 2px 55%, 60px 55%, 120px 55%;"
                         )},
                        {"selector": 'th[data-dash-column="Positions"]',
                         "rule": "white-space: normal;"},
                        {"selector": 'th[data-dash-column="Positions"] .column-header-name',
                         "rule": "display: block;"},
                        {"selector": 'th[data-dash-column="Positions"]::after',
                         "rule": (
                             "content: 'Long   Short   Spread';"
                             "display: block;"
                             "margin-top: 4px;"
                             "font-size: 11px;"
                             "color: #444;"
                             "line-height: 1.3;"
                             "padding-left: 18px;"
                             "word-spacing: 26px;"
                             "background-image: "
                             "radial-gradient(circle, #2ca02c 0, #2ca02c 100%),"
                             "radial-gradient(circle, #d62728 0, #d62728 100%),"
                             "radial-gradient(circle, #1f77b4 0, #1f77b4 100%);"
                             "background-repeat: no-repeat;"
                             "background-size: 10px 10px, 10px 10px, 10px 10px;"
                             "background-position: 2px 55%, 60px 55%, 120px 55%;"
                         )},
                    ],
                    style_cell_conditional=[
                        {'if': {'column_id': 'Positions'},
                         'whiteSpace': 'normal', 'height': 'auto',
                         'minWidth': '260px', 'width': '260px', 'maxWidth': '260px'},
                        {'if': {'column_id': COL_NUM_TRADERS},
                         'whiteSpace': 'normal', 'height': 'auto',
                         'minWidth': '260px', 'width': '260px', 'maxWidth': '260px'}
                    ],
                    style_data_conditional=[
                        {'if': {'filter_query': '{' + COL_DIFF_LONG   + '} < 0', 'column_id': COL_DIFF_LONG},   'color': 'red'},
                        {'if': {'filter_query': '{' + COL_DIFF_LONG   + '} > 0', 'column_id': COL_DIFF_LONG},   'color': 'green'},
                        {'if': {'filter_query': '{' + COL_DIFF_SHORT  + '} < 0', 'column_id': COL_DIFF_SHORT},  'color': 'red'},
                        {'if': {'filter_query': '{' + COL_DIFF_SHORT  + '} > 0', 'column_id': COL_DIFF_SHORT},  'color': 'green'},
                        {'if': {'filter_query': '{' + COL_DIFF_SPREAD + '} < 0', 'column_id': COL_DIFF_SPREAD}, 'color': 'red'},
                        {'if': {'filter_query': '{' + COL_DIFF_SPREAD + '} > 0', 'column_id': COL_DIFF_SPREAD}, 'color': 'green'},
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px',
                        'border': '1px solid grey',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                )
            ], width=12)
        ]),

        html.Hr(),

        # Clustering Indicator
        dbc.Row([
            dbc.Col([
                html.H1("Clustering Indicator", id="section-clustering"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **Clustering Indicator** misst, wie viele Trader eine bestimmte Long- oder Short-Position halten,
                        ausgedrückt als Prozentsatz aller Trader im Markt. Er ist damit ein Indikator für Marktstimmung und „Herdentrieb".

                        Das **Ziel des Indikators** ist es, das Mass an „Crowding" in einem Markt sichtbar zu machen – also wie viele
                        Trader sich in dieselbe Richtung positionieren. Er ist unabhängig von der Positionsgrösse und passt sich dadurch gut an
                        regulatorische Beschränkungen wie Positionslimits oder Diversifikationsauflagen an.

                        **Farbskala:** Die Punktfarbe zeigt den *Clustering-Wert in %*. Dieser Wert zeigt, wie
                        stark sich Trader im Verhältnis zur historischen Bandbreite (ein Jahr) in einer Long- oder Short-Position
                        konzentrieren. Ein hoher Wert bedeutet also, dass sich besonders viele Trader in derselben Richtung
                        positionieren.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Die Berechnung erfolgt in zwei Schritten. **Schritt 1 – Roher Trader-Anteil:**
                        """, mathjax=True),
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                            **Long-Clustering (Money Manager):**

                            $$
                            \mathrm{share}^{\mathrm{(Long)}}_{\mathrm{MM}}(t)=
                            \frac{\mathrm{Traders}^{\mathrm{(Long)}}_{\mathrm{MM}}(t)}
                            {\mathrm{Total\ Traders}(t)}
                            $$
                            """, mathjax=True), width=12, lg=6),

                            dbc.Col(dcc.Markdown(r"""
                            **Short-Clustering (Money Manager):**

                            $$
                            \mathrm{share}^{\mathrm{(Short)}}_{\mathrm{MM}}(t)=
                            \frac{\mathrm{Traders}^{\mathrm{(Short)}}_{\mathrm{MM}}(t)}
                            {\mathrm{Total\ Traders}(t)}
                            $$
                            """, mathjax=True), width=12, lg=6),
                        ], className="mb-2"),

                        dcc.Markdown(r"""
                        **Schritt 2 – Rollende Min-Max-Normierung (52-Wochen-Fenster):**

                        $$
                        \mathrm{Clustering}^{\mathrm{(Long/Short)}}_{\mathrm{MM}}(t)=
                        \frac{\mathrm{share}(t)-\min_{52W}\!\bigl(\mathrm{share}\bigr)}
                             {\max_{52W}\!\bigl(\mathrm{share}\bigr)-\min_{52W}\!\bigl(\mathrm{share}\bigr)}
                        \times 100
                        $$

                        **Variablen und Begriffe:**
                        - **MM:** Money Manager
                        - **$\mathrm{Traders}^{\mathrm{(Long)}}_{\mathrm{MM}}(t)$:** Anzahl MM-Trader mit Long-Positionen am Reportdatum $t$
                        - **$\mathrm{Traders}^{\mathrm{(Short)}}_{\mathrm{MM}}(t)$:** Anzahl MM-Trader mit Short-Positionen am Reportdatum $t$
                        - **$\mathrm{Total\ Traders}(t)$:** Gesamtanzahl aller reportablen Trader im Markt am Reportdatum $t$
                        - **$\min_{52W}$, $\max_{52W}$:** rollierendes Minimum bzw. Maximum über 52 Wochen
                        - **Clustering-Wert:** 0 = historisches Minimum, 100 = historisches Maximum innerhalb der letzten 52 Wochen
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='long-clustering-graph'),
                html.Div([], style={'marginTop': '10px'}),
                dcc.Graph(id='short-clustering-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # Position Size Indicator
        dbc.Row([
            dbc.Col([
                html.H1("Position Size Indicator", id="section-position-size"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **Position Size Indicator** misst die durchschnittliche Grösse der Positionen einzelner Trader,
                        indem die gesamte Positionsgrösse durch die Anzahl der beteiligten Trader geteilt wird. Dadurch wird sichtbar,
                        wie stark die Überzeugung (*conviction*) innerhalb einer Tradergruppe ist.

                        Das **Ziel des Indikators** ist es, die durchschnittliche Positionsgrösse und damit die Intensität des Engagements von Tradern transparenter zu machen.
                        Er kombiniert Daten zu *Open Interest* und *Traderanzahl*, um Rückschlüsse auf die Verteilung von Positionen entlang der Fälligkeiten
                        (*down the curve*) zu ziehen. Zudem lassen sich über Positionslimits erkennen, wie stark Positionen konzentriert sind und welche
                        Auswirkungen ein Abbau dieser Positionen auf Preise und Marktstruktur haben könnte.

                        **Farbskala:** Die Punktfarbe zeigt die *durchschnittliche Positionsgrösse* in der jeweiligen Gruppe.
                        Helle Farben = grössere Positionen pro Trader, dunkle Farben = kleinere Positionen.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \text{Position Size}_{G} =
                        \frac{\text{Open Interest}_{G}}
                        {\text{Number of Traders}_{G}}
                        $$

                        wobei
                        $$
                        G \in \{\mathrm{MM}\text{-}L,\, \mathrm{MM}\text{-}S,\, \mathrm{PMPU}\text{-}L,\, \mathrm{PMPU}\text{-}S,\, \mathrm{SD}\text{-}L,\, \mathrm{SD}\text{-}S,\, \mathrm{OR}\text{-}L,\, \mathrm{OR}\text{-}S\}
                        $$

                        **Variablen und Begriffe:**
                        - **PMPU:** Producer/Merchant/Processor/User
                        - **SD:** Swap Dealer
                        - **MM:** Managed Money
                        - **OR:** Other Reportables
                        - **L:** Long Positionen
                        - **S:** Short Positionen
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),
            ], width=12)
        ]),

        dbc.Row([dbc.Col([html.H2("Producer/Merchant/Processor/User")], width=12)]),
        dbc.Row([
            dbc.Col([dcc.Graph(id='pmpu-long-position-size-graph')],  width=12),
            dbc.Col([dcc.Graph(id='pmpu-short-position-size-graph')], width=12),
        ]),
        dbc.Row([dbc.Col([html.H2("Swap Dealers")], width=12)]),
        dbc.Row([
            dbc.Col([dcc.Graph(id='sd-long-position-size-graph')],  width=12),
            dbc.Col([dcc.Graph(id='sd-short-position-size-graph')], width=12),
        ]),
        dbc.Row([dbc.Col([html.H2("Money Managers")], width=12)]),
        dbc.Row([
            dbc.Col([dcc.Graph(id='long-position-size-graph')],  width=12),
            dbc.Col([dcc.Graph(id='short-position-size-graph')], width=12),
        ]),
        dbc.Row([dbc.Col([html.H2("Other Reportables")], width=12)]),
        dbc.Row([
            dbc.Col([dcc.Graph(id='or-long-position-size-graph')],  width=12),
            dbc.Col([dcc.Graph(id='or-short-position-size-graph')], width=12),
        ]),
    ])
