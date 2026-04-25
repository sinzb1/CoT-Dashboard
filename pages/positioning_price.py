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
                        **Indikator:** Zeigt den Anteil der MML- oder MMS-Positionen am gesamten Markt-Open-Interest über die Zeit, aufgetragen gegen den 2nd Nearby Futures-Preis.

                        **Interpretation:** Hohe Farbwerte zeigen, dass die Gruppe einen grossen Anteil des Markt-OI hält. Häufungen bei bestimmten Preisniveaus zeigen, bei welchen Preisen die Gruppe typischerweise besonders stark positioniert ist.

                        **Ziel:** Marktbedeutung und Dominanz einer Tradergruppe im Zeitverlauf und in Abhängigkeit vom Preisniveau sichtbar machen.

                        **Besonderheit:** Schwarzer Punkt mit rotem Rahmen = aktuellste Woche.

                        **Kreisgrösse:** Die Kreisgrösse ist proportional zum gesamten Open Interest $\mathrm{OI}_{\mathrm{total}}(t)$ (logarithmische Skalierung).

                        **Farbskala:** Farbe = PP Concentration in %. Rot = tiefer Anteil am Markt-OI, Grün = hoher Anteil.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \mathrm{PP\ Concentration}_{G} =
                        \frac{\mathrm{OI}_{G}}{\mathrm{OI}_{\mathrm{total}}} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                        - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ (in Kontrakten)
                        - $\mathrm{OI}_{\mathrm{total}}$: Gesamtes Open Interest aller offenen Kontrakte
                        - $P_{\mathrm{2nd\ Nearby}}$: Schlusskurs des 2nd-Nearby-Futures (Databento, Y-Achse)
                        - Kreisgrösse: $\mathrm{OI}_{\mathrm{total}}$, logarithmisch skaliert

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
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
                        **Indikator:** Zeigt den Anteil der MM-Trader (Long oder Short) an der Gesamtanzahl aller Trader im Markt über die Zeit, aufgetragen gegen den 2nd Nearby Futures-Preis.

                        **Interpretation:** Hohe Farbwerte zeigen, dass ein grosser Anteil aller Trader in dieser Gruppe und Richtung positioniert ist — ein Zeichen für Crowding. Häufungen bei bestimmten Preisniveaus zeigen, bei welchen Preisen das Crowding typischerweise am stärksten ist.

                        **Ziel:** Breite der Marktteilnahme einer Tradergruppe im Zeitverlauf und in Abhängigkeit vom Preisniveau sichtbar machen.

                        **Besonderheit:** Schwarzer Punkt mit rotem Rahmen = aktuellste Woche.

                        **Kreisgrösse:** Die Kreisgrösse ist proportional zum gesamten Open Interest $\mathrm{OI}_{\mathrm{total}}(t)$ (logarithmische Skalierung).

                        **Farbskala:** Farbe = PP Clustering in %. Rot = tiefer Traderanteil, Grün = hoher Traderanteil.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \mathrm{PP\ Clustering}_{G} =
                        \frac{N_{G}}{N} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$
                        - $N$: Gesamtanzahl aller reportablen Trader im Markt
                        - $P_{\mathrm{2nd\ Nearby}}$: Schlusskurs des 2nd-Nearby-Futures (Databento, Y-Achse)
                        - Kreisgrösse: $\mathrm{OI}_{\mathrm{total}}$, logarithmisch skaliert

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
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
                        **Indikator:** Zeigt die durchschnittliche preisgewichtete Positionsgrösse pro Trader (in USD) der MML- oder MMS-Gruppe über die Zeit, aufgetragen gegen den 2nd Nearby Futures-Preis.

                        **Interpretation:** Hohe Farbwerte zeigen, dass einzelne Trader im Durchschnitt grosse Positionen halten — ein Zeichen für hohe Conviction. Häufungen bei bestimmten Preisniveaus zeigen, bei welchen Preisen besonders grosse Einzelpositionen typisch sind.

                        **Ziel:** Intensität des Engagements einzelner Trader im Zeitverlauf und in Abhängigkeit vom Preisniveau sichtbar machen.

                        **Besonderheit:** Die Positionsgrösse wird preisgewichtet in USD ausgewiesen, damit sie über Märkte und Zeitperioden direkt vergleichbar ist. Schwarzer Punkt mit rotem Rahmen = aktuellste Woche.

                        **Kreisgrösse:** Die Kreisgrösse ist proportional zur Anzahl Trader der Gruppe $N_{G}(t)$ (lineare Skalierung).

                        **Farbskala:** Farbe = durchschnittliche Positionsgrösse pro Trader (USD). Rot = kleine Positionen, Grün = grosse Positionen.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        \mathrm{PP\ PositionSize}_{G} =
                        \frac{\mathrm{OI}_{G}}{N_{G}}
                        \times \mathrm{ContractSize} \times P_{\mathrm{2nd\ Nearby}}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                        - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ (in Kontrakten)
                        - $N_{G}$: Anzahl Trader der Gruppe $G$
                        - $\mathrm{ContractSize}$: Kontraktgrösse des betrachteten Futures-Marktes
                        - $P_{\mathrm{2nd\ Nearby}}$: Schlusskurs des 2nd-Nearby-Futures (Databento, Y-Achse)
                        - Kreisgrösse: $N_{G}$, linear skaliert

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
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
