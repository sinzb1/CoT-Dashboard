from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

_GRP_PMPU = "Producer/Merchant/Processor/User"
_GRP_SD   = "Swap Dealers"
_GRP_MM   = "Money Managers"
_GRP_OR   = "Other Reportables"

COL_DIFF_LONG    = 'Difference (Long %)'
COL_DIFF_SHORT   = 'Difference (Short %)'
COL_DIFF_SPREAD  = 'Difference (Spread %)'
COL_NUM_TRADERS  = 'Number of Traders'
COL_OPEN_INT     = 'Open Interest'
COL_PCT_LONG     = '% Long'
COL_PCT_SHORT    = '% Short'
COL_PCT_SPREAD   = '% Spread'


def layout():
    return html.Div([
        # Sprungnavigation
        html.Div(
            [html.Span("Schnellnavigation: ", className="fw-semibold text-muted me-2 small align-middle")]
            + [html.A(lbl, href=f"#{anc}", className="btn btn-sm btn-outline-secondary me-2 mb-1")
               for lbl, anc in [
                   ("Market Overview", "section-market-overview"),
                   ("Concentration Indicator", "section-concentration"),
                   ("Clustering Indicator", "section-clustering"),
                   ("Position Size Indicator", "section-position-size"),
               ]],
            className="p-3 mb-4 bg-light border rounded"
        ),

        # Übersichtstabelle
        dbc.Row([
            dbc.Col([
                html.H2("Market Overview", className="mt-3 mb-3", id="section-market-overview"),
                html.P(id='table-date-label', className='text-muted small mb-2'),
                dash_table.DataTable(
                    id='overview-table',
                    tooltip_delay=400,
                    tooltip_duration=None,
                    columns=[
                        {'name': ['',             'Trader Group'], 'id': 'Trader Group'},
                        {'name': [COL_OPEN_INT, 'Total'],       'id': COL_OPEN_INT},
                        {'name': [COL_OPEN_INT, 'Positionen'],  'id': 'Positions', 'presentation': 'markdown'},
                        {'name': [COL_OPEN_INT, 'Δ Long %'],    'id': COL_DIFF_LONG},
                        {'name': [COL_OPEN_INT, 'Δ Short %'],   'id': COL_DIFF_SHORT},
                        {'name': [COL_OPEN_INT, 'Δ Spread %'],  'id': COL_DIFF_SPREAD},
                        {'name': ['Traders',       'Total'],       'id': 'Total Traders'},
                        {'name': ['Traders',       '% Long'],      'id': COL_PCT_LONG},
                        {'name': ['Traders',       '% Short'],     'id': COL_PCT_SHORT},
                        {'name': ['Traders',       '% Spread'],    'id': COL_PCT_SPREAD},
                        {'name': ['Traders',       'Verteilung'],  'id': COL_NUM_TRADERS, 'presentation': 'markdown'},
                    ],
                    merge_duplicate_headers=True,
                    markdown_options={"html": True},
                    style_header={
                        'backgroundColor': '#dae8f5',
                        'fontWeight': 'bold',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    css=[
                        {"selector": "tr:nth-child(1) th",
                         "rule": "background-color: #b8d0e8 !important; text-align: center !important;"},
                        {"selector": f'th[data-dash-column="{COL_NUM_TRADERS}"]',
                         "rule": "white-space: normal;"},
                        {"selector": f'th[data-dash-column="{COL_NUM_TRADERS}"] .column-header-name',
                         "rule": "display: block;"},
                        {"selector": f'tr:nth-child(2) th[data-dash-column="{COL_NUM_TRADERS}"]::after',
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
                        {"selector": 'tr:nth-child(2) th[data-dash-column="Positions"]::after',
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
                         'minWidth': '260px', 'width': '260px', 'maxWidth': '260px'},
                        {'if': {'column_id': COL_OPEN_INT},
                         'minWidth': '110px', 'width': '110px', 'maxWidth': '110px', 'textAlign': 'right'},
                        {'if': {'column_id': COL_PCT_LONG},
                         'minWidth': '80px', 'width': '80px', 'maxWidth': '80px', 'textAlign': 'right'},
                        {'if': {'column_id': COL_PCT_SHORT},
                         'minWidth': '80px', 'width': '80px', 'maxWidth': '80px', 'textAlign': 'right'},
                        {'if': {'column_id': COL_PCT_SPREAD},
                         'minWidth': '80px', 'width': '80px', 'maxWidth': '80px', 'textAlign': 'right'},
                    ],
                    style_data_conditional=[
                        {'if': {'filter_query': '{' + COL_DIFF_LONG   + '} < 0', 'column_id': COL_DIFF_LONG},   'color': 'red'},
                        {'if': {'filter_query': '{' + COL_DIFF_LONG   + '} > 0', 'column_id': COL_DIFF_LONG},   'color': 'green'},
                        {'if': {'filter_query': '{' + COL_DIFF_SHORT  + '} < 0', 'column_id': COL_DIFF_SHORT},  'color': 'red'},
                        {'if': {'filter_query': '{' + COL_DIFF_SHORT  + '} > 0', 'column_id': COL_DIFF_SHORT},  'color': 'green'},
                        {'if': {'filter_query': '{' + COL_DIFF_SPREAD + '} < 0', 'column_id': COL_DIFF_SPREAD}, 'color': 'red'},
                        {'if': {'filter_query': '{' + COL_DIFF_SPREAD + '} > 0', 'column_id': COL_DIFF_SPREAD}, 'color': 'green'},
                        {'if': {'filter_query': '{Trader Group} = "Markt gesamt"'},
                         'backgroundColor': '#c8dff0', 'fontWeight': 'bold',
                         'borderTop': '2px solid #7aabcf'},
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

        # Concentration Indicator
        dbc.Row([
            dbc.Col([
                html.H1("Concentration Indicator", id="section-concentration"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Misst den Anteil des Open Interests einer Tradergruppe am gesamten Markt-Open-Interest.

                        **Interpretation:** Ein hoher Wert zeigt, dass eine Gruppe einen überproportional grossen Teil des Marktes hält und damit strukturell dominant ist.

                        **Ziel:** Marktbedeutung und Dominanz einzelner Tradergruppen sichtbar machen.

                        **Besonderheit:** Unabhängig von der absoluten Marktgrösse – der Indikator normiert das Open Interest relativ zum Gesamtmarkt.

                        **Kreisgrösse:** Die Kreisgrösse entspricht der Gesamtanzahl aller reportablen Trader im Markt ($N$).

                        **Farbskala:** Die Farbe zeigt den Concentration-Wert in %. Helle Farben = hoher Anteil am Gesamtmarkt.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \mathrm{Concentration}_{G}^{(L/S)}(\%) =
                        \frac{\mathrm{OI}_{G}^{(L/S)}}{\mathrm{OI}_{\mathrm{total}}} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM},\, \mathrm{PMPU},\, \mathrm{SD},\, \mathrm{OR}\}$: betrachtete Tradergruppe
                        - $\mathrm{OI}_{G}^{(L/S)}$: Open Interest der Gruppe $G$ (Long oder Short)
                        - $\mathrm{OI}_{\mathrm{total}}$: Gesamtes Open Interest aller offenen Kontrakte

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='grundlegende-concentration-radio',
                    options=[
                        {'label': 'Long', 'value': 'Long'},
                        {'label': 'Short', 'value': 'Short'},
                    ],
                    value='Long',
                    className='mb-4'
                ),
            ], width=12)
        ]),

        dbc.Row([dbc.Col([html.H2(_GRP_PMPU)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='pmpu-concentration-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_SD)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='sd-concentration-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_MM)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='mm-concentration-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_OR)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='or-concentration-graph')], width=12)]),

        html.Hr(),

        # Clustering Indicator
        dbc.Row([
            dbc.Col([
                html.H1("Clustering Indicator", id="section-clustering"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Misst den Anteil der Trader einer Gruppe an der Gesamtanzahl aller reportablen Trader im Markt.

                        **Interpretation:** Ein hoher Wert zeigt, dass sich besonders viele Trader in dieselbe Richtung positionieren – ein Zeichen für Herdentrieb oder starkes Crowding.

                        **Ziel:** Das Mass an Crowding in einem Markt sichtbar machen – unabhängig von der Positionsgrösse.

                        **Besonderheit:** Da der Indikator auf Traderzahlen basiert, reagiert er nicht auf Positionslimits oder Diversifikationsauflagen – er misst das Verhalten der Marktteilnehmer, nicht die Grösse ihrer Positionen.

                        **Kreisgrösse:** Die Kreisgrösse entspricht der Gesamtanzahl aller reportablen Trader im Markt ($N$).

                        **Farbskala:** Die Farbe zeigt den Clustering-Wert in %. Helle Farben = hoher Traderanteil (hohes Crowding).
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \mathrm{Clustering}_{G}^{(L/S)}(\%) =
                        \frac{N_{G}^{(L/S)}}{N} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM},\, \mathrm{PMPU},\, \mathrm{SD},\, \mathrm{OR}\}$: betrachtete Tradergruppe
                        - $N_{G}^{(L/S)}$: Anzahl Trader der Gruppe $G$ mit Long- bzw. Short-Position
                        - $N$: Gesamtanzahl aller reportablen Trader im Markt

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='grundlegende-clustering-radio',
                    options=[
                        {'label': 'Long', 'value': 'Long'},
                        {'label': 'Short', 'value': 'Short'},
                    ],
                    value='Long',
                    className='mb-4'
                ),
            ], width=12)
        ]),

        dbc.Row([dbc.Col([html.H2(_GRP_PMPU)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='pmpu-clustering-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_SD)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='sd-clustering-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_MM)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='mm-clustering-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_OR)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='or-clustering-graph')], width=12)]),

        html.Hr(),

        # Position Size Indicator
        dbc.Row([
            dbc.Col([
                html.H1("Position Size Indicator", id="section-position-size"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Misst die durchschnittliche Positionsgrösse pro Trader einer Gruppe (Kontrakte pro Trader).

                        **Interpretation:** Ein hoher Wert zeigt, dass die Trader einer Gruppe grosse Einzelpositionen halten – ein Indikator für hohe Überzeugung (*conviction*) oder konzentrierte Positionierung.

                        **Ziel:** Die Intensität des Engagements einer Tradergruppe sichtbar machen, unabhängig davon, wie viele Trader beteiligt sind.

                        **Besonderheit:** In Kombination mit dem Clustering Indicator lässt sich unterscheiden, ob ein hoher OI-Anteil auf viele kleine oder wenige grosse Positionen zurückgeht – relevant für die Einschätzung von Liquidationsrisiken.

                        **Kreisgrösse:** Die Kreisgrösse entspricht der Anzahl Trader der jeweiligen Gruppe ($N_{G}^{(L/S)}$).

                        **Farbskala:** Die Farbe zeigt die durchschnittliche Positionsgrösse (Kontrakte pro Trader). Helle Farben = grössere Positionen pro Trader.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \mathrm{PositionSize}_{G}^{(L/S)} =
                        \frac{\mathrm{OI}_{G}^{(L/S)}}{N_{G}^{(L/S)}}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM},\, \mathrm{PMPU},\, \mathrm{SD},\, \mathrm{OR}\}$: betrachtete Tradergruppe
                        - $\mathrm{OI}_{G}^{(L/S)}$: Open Interest der Gruppe $G$ (Long oder Short)
                        - $N_{G}^{(L/S)}$: Anzahl Trader der Gruppe $G$ mit Long- bzw. Short-Position

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='grundlegende-position-size-radio',
                    options=[
                        {'label': 'Long', 'value': 'Long'},
                        {'label': 'Short', 'value': 'Short'},
                    ],
                    value='Long',
                    className='mb-4'
                ),
            ], width=12)
        ]),

        dbc.Row([dbc.Col([html.H2(_GRP_PMPU)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='pmpu-position-size-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_SD)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='sd-position-size-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_MM)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='mm-position-size-graph')], width=12)]),
        dbc.Row([dbc.Col([html.H2(_GRP_OR)], width=12)]),
        dbc.Row([dbc.Col([dcc.Graph(id='or-position-size-graph')], width=12)]),
    ])
