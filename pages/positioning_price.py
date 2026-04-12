from dash import dcc, html
import dash_bootstrap_components as dbc


def layout():
    return html.Div([
        # Sprungnavigation
        html.Div(
            [html.Span("Schnellnavigation: ", className="fw-semibold text-muted me-2 small align-middle")]
            + [html.A(lbl, href=f"#{anc}", className="btn btn-sm btn-outline-secondary me-2 mb-1")
               for lbl, anc in [
                   ("PP Concentration", "section-pp-concentration"),
                   ("PP Clustering", "section-pp-clustering"),
                   ("PP Position Size", "section-pp-position-size"),
               ]],
            className="p-3 mb-4 bg-light border rounded"
        ),

        # PP Concentration Indicator
        dbc.Row([
            dbc.Col([
                html.H1("PP Concentration Indicator", className="mt-3", id="section-pp-concentration"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **Positioning Price Concentration Indicator** misst, wie gross der Anteil der Positionen
                        einer Tradergruppe am gesamten Markt ist. Dadurch wird sichtbar, wie stark eine Gruppe auf
                        der Long- oder Short-Seite im Verhältnis zum gesamten Open Interest vertreten ist. Eine hohe
                        Konzentration deutet darauf hin, dass ein grosser Teil des Marktes von dieser Gruppe gehalten wird.

                        Das **Ziel des Indikators** ist es, die Marktbedeutung und Dominanz einer Tradergruppe sichtbar
                        zu machen. Er zeigt, wie stark die Positionierung einer Gruppe relativ zum Gesamtmarkt ausfällt
                        und hilft damit, Phasen hoher Konzentration zu erkennen. Dadurch lassen sich Rückschlüsse darauf
                        ziehen, in welchen Marktphasen einzelne Gruppen besonders stark engagiert sind und wo potenzielle
                        Risiken durch einen späteren Positionsabbau bestehen könnten.

                        **Farbskala:** Die Punktfarbe zeigt die Konzentration der Positionen der jeweiligen Gruppe am
                        gesamten Open Interest.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Visuelle Kodierung (Zeitpunkt $t$):**
                        - **X-Achse:** $t$ (Reportdatum)
                        - **Y-Achse:** $P_{\mathrm{2nd\ Nearby}}(t)$ (Schlusskurs des 2nd-Nearby-Futures, Databento)
                        - **Punktgrösse:** proportional zum gesamten Open Interest $\mathrm{OI}(t)$ (logarithmisch skaliert)
                        - **Punktfarbe:** $\mathrm{PP\ Concentration}_G(t)$ (Farbskala RdYlGn, in %)

                        **Farbformel:**
                        $$
                        \mathrm{PP\ Concentration}_{G}(t)=
                        \frac{\mathrm{Position}_{G}(t)}
                        {\mathrm{OI}(t)} \times 100
                        $$
                        """, mathjax=True),
                        dcc.Markdown(r"""
                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$G$:** betrachtete Gruppe mit $G \in \{\mathrm{MML}, \mathrm{MMS}\}$
                        - **$\mathrm{OI}(t)$:** gesamtes Open Interest aller offenen Kontrakte im Markt
                        - **$\mathrm{Position}_G(t)$:** Position der betrachteten Gruppe $G$ am Reportdatum $t$ (in Kontrakten)
                        - **Concentration:** Anteil der Positionen einer Gruppe am gesamten Markt-OI (in Prozent)
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='ppci-mm-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='positioning-price-concentration-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # PP Clustering Indicator
        dbc.Row([
            dbc.Col([
                html.H1("PP Clustering Indicator", id="section-pp-clustering"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **Positioning Price Clustering Indicator** misst, wie gross der Anteil der Trader
                        einer bestimmten Tradergruppe an allen Long- bzw. Short-Tradern im Markt ist. Dadurch
                        wird sichtbar, wie breit oder eng eine Positionierung innerhalb einer Gruppe abgestützt ist.
                        Eine hohe Clustering-Ausprägung bedeutet, dass ein grosser Anteil der Trader
                        auf der jeweiligen Marktseite dieser Gruppe zuzuordnen ist.

                        Das **Ziel des Indikators** ist es, die Breite der Marktteilnahme einer Tradergruppe sichtbar
                        zu machen. Er zeigt, ob eine Positionierung von vielen oder nur von wenigen Tradern getragen
                        wird und macht damit die Struktur der Marktteilnahme transparenter. Dadurch lassen sich Phasen
                        erkennen, in denen sich Positionierungen innerhalb einer Gruppe besonders stark verdichten oder verbreitern.

                        **Farbskala:** Die Punktfarbe zeigt das Clustering der jeweiligen Gruppe.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Visuelle Kodierung (Zeitpunkt $t$):**
                        - **X-Achse:** $t$ (Reportdatum)
                        - **Y-Achse:** $P_{\mathrm{2nd\ Nearby}}(t)$ (Schlusskurs des 2nd-Nearby-Futures, Databento)
                        - **Punktgrösse:** proportional zum gesamten Open Interest $\mathrm{OI}(t)$ (logarithmisch skaliert)
                        - **Punktfarbe:** $\mathrm{PP\ Clustering}_G(t)$ (Farbskala RdYlGn, Werte 0–100)

                        Die Berechnung erfolgt in zwei Schritten.

                        **Schritt 1 – Roher Trader-Anteil:**
                        $$
                        \mathrm{share}_{G}(t)=
                        \frac{\mathrm{Traders}_{G}(t)}
                        {\mathrm{Total\ Traders}(t)}
                        $$

                        **Schritt 2 – Rollende Min-Max-Normierung (52-Wochen-Fenster):**
                        $$
                        \mathrm{PP\ Clustering}_{G}(t)=
                        \frac{\mathrm{share}_{G}(t)-\min_{52W}\!\bigl(\mathrm{share}_{G}\bigr)}
                             {\max_{52W}\!\bigl(\mathrm{share}_{G}\bigr)-\min_{52W}\!\bigl(\mathrm{share}_{G}\bigr)}
                        \times 100
                        $$
                        """, mathjax=True),
                        dcc.Markdown(r"""
                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$G$:** betrachtete Gruppe mit $G \in \{\mathrm{MML}, \mathrm{MMS}\}$
                        - **$\mathrm{Traders}_G(t)$:** Anzahl Trader der betrachteten Gruppe $G$ am Reportdatum $t$
                        - **$\mathrm{Total\ Traders}(t)$:** Gesamtanzahl aller reportablen Trader im Markt am Reportdatum $t$
                        - **$\min_{52W}$, $\max_{52W}$:** rollierendes Minimum bzw. Maximum über 52 Wochen
                        - **PP Clustering:** 0 = historisches Minimum, 100 = historisches Maximum innerhalb der letzten 52 Wochen
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='ppci-clustering-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='pp-clustering-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # PP Position Size Indicator
        dbc.Row([
            dbc.Col([
                html.H1("PP Position Size Indicator", id="section-pp-position-size"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **Positioning Price Position Size Indicator** misst die durchschnittliche Grösse
                        der Positionen einzelner Trader innerhalb einer bestimmten Tradergruppe. Dazu wird die
                        Position der betrachteten Gruppe mit dem Preis multipliziert und durch die Anzahl der
                        Trader dieser Gruppe geteilt. Dadurch wird sichtbar, wie gross die durchschnittliche
                        preisgewichtete Position pro Trader ist und wie stark einzelne Trader innerhalb
                        der Gruppe engagiert sind.

                        Das **Ziel des Indikators** ist es, die durchschnittliche Positionsgrösse pro Trader und
                        damit die Intensität des Engagements innerhalb einer Tradergruppe sichtbar zu machen. Er
                        hilft zu beurteilen, ob Veränderungen im Open Interest eher durch eine steigende Zahl von
                        Tradern oder durch grössere durchschnittliche Positionen pro Trader entstehen. Dadurch
                        lassen sich Rückschlüsse auf die Stärke und Überzeugung der Trader innerhalb
                        einer Gruppe ziehen.

                        **Farbskala:** Die Punktfarbe zeigt die durchschnittliche Positionsgrösse der jeweiligen Gruppe.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Visuelle Kodierung (Zeitpunkt $t$):**
                        - **X-Achse:** $t$ (Reportdatum)
                        - **Y-Achse:** $P_{\mathrm{2nd\ Nearby}}(t)$ (Schlusskurs des 2nd-Nearby-Futures, Databento)
                        - **Punktgrösse:** proportional zur Anzahl Trader $\mathrm{Traders}_G(t)$ (linear skaliert)
                        - **Punktfarbe:** $\mathrm{PP\ PositionSize}_G(t)$ (in USD)

                        **Farbformel:**
                        $$
                        \mathrm{PP\ PositionSize}_{G}(t)=
                        \frac{\mathrm{Position}_{G}(t)\times \mathrm{ContractSize}\times P_{\mathrm{2nd\ Nearby}}(t)}
                        {\mathrm{Traders}_{G}(t)}
                        $$
                        """, mathjax=True),
                        dcc.Markdown(r"""
                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$G$:** betrachtete Gruppe mit $G \in \{\mathrm{MML}, \mathrm{MMS}\}$
                        - **$\mathrm{Position}_G(t)$:** Position der betrachteten Gruppe $G$ am Reportdatum $t$ (in Kontrakten)
                        - **$\mathrm{ContractSize}$:** Kontraktgrösse des betrachteten Futures-Marktes
                        - **$P_{\mathrm{2nd\ Nearby}}(t)$:** Schlusskurs des 2nd-Nearby-Futures am Reportdatum $t$ (Databento)
                        - **$\mathrm{Traders}_G(t)$:** Anzahl Trader der betrachteten Gruppe $G$ am Reportdatum $t$
                        - **Position Size:** durchschnittliche preisgewichtete Positionsgrösse pro Trader (in USD)
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='ppci-position-size-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='pp-position-size-graph'),
                html.Br(),
            ], width=12)
        ]),
    ])
