from dash import dcc, html
import dash_bootstrap_components as dbc


def layout():
    return html.Div([
        # Sprungnavigation
        html.Div(
            [html.Span("Schnellnavigation: ", className="fw-semibold text-muted me-2 small align-middle")]
            + [html.A(lbl, href=f"#{anc}", className="btn btn-sm btn-outline-secondary me-2 mb-1")
               for lbl, anc in [
                   ("DP Indicator", "section-dp"),
                   ("DP Notional", "section-dp-notional"),
                   ("DP Time", "section-dp-time"),
                   ("DP Price", "section-dp-price"),
                   ("DP Curve", "section-dp-curve"),
                   ("DP Factor (VIX)", "section-dp-vix"),
                   ("DP Factor (DXY)", "section-dp-dxy"),
                   ("DP Currency", "section-dp-currency"),
                   ("DP Fundamental", "section-dp-fundamental"),
                   ("DP Rel. Concentration", "section-dp-rel-concentration"),
                   ("DP Seasonal", "section-dp-seasonal"),
                   ("DP Net", "section-dp-net"),
                   ("DP Position Size", "section-dp-position-size"),
                   ("DP Hedging", "section-dp-hedging"),
                   ("DP Conc./Clustering", "section-dp-conc-clustering"),
               ]],
            className="p-3 mb-4 bg-light border rounded"
        ),

        # DP Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Indicator", id="section-dp"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt die Long- (MML) und Short-Positionen (MMS) der Managed-Money-Gruppe als Punktewolke: Anzahl Trader (X-Achse) gegen Open Interest (Y-Achse).

                        **Interpretation:** Die Lage und Dichte der Punktewolke zeigen, bei welcher Traderanzahl welches OI-Niveau typisch ist. Je weiter rechts der aktuelle Punkt, desto mehr Trader sind beteiligt — je höher, desto grösser das OI.

                        **Ziel:** Einschätzen, ob bestehende Positionen noch ausgebaut werden können (tiefe Traderanzahl = viel „Dry Powder") oder ob sie liquidationsgefährdet sind (hohe Konzentration, wenig Spielraum).

                        **Besonderheit:** MMS-Werte werden negativ dargestellt, um Long- und Short-Seite im selben Chart zu trennen. Je Gruppe wird eine Regressionstrendlinie eingeblendet.

                        **Farbskala:** Keine kontinuierliche Farbskala — Dunkelblau = MML (Long-Seite), Hellblau = MMS (Short-Seite). Schwarzer Punkt = aktuellste Woche.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}
                        $$

                        $$
                        y_{G} = \delta_{G} \times \mathrm{OI}_{G}
                        $$

                        dabei gilt:

                        $$
                        \delta_{G} =
                        \begin{cases}
                        +1 & \text{falls } G = \mathrm{MM}_{L} \\
                        -1 & \text{falls } G = \mathrm{MM}_{S}
                        \end{cases}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM}_{L},\, \mathrm{MM}_{S}\}$: betrachtete Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ (in Kontrakten)
                        - $\delta_{G}$: Vorzeichen ($+1$ für Long, $-1$ für Short)
                        - $y_{G}$: vorzeichenbehaftetes Open Interest (Y-Achse)
                        - **Farbkodierung:** Dunkelblau = $\mathrm{MM}_{L}$-Wolke, Hellblau = $\mathrm{MM}_{S}$-Wolke
                        - **Schwarzer Punkt:** aktuellste Woche

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='dry-powder-indicator-graph'),
            ], width=12)
        ]),

        html.Hr(),

        # DP Notional Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Notional Indicator", id="section-dp-notional"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das aggregierte Dollar-Exposure (Notional) der MML- und MMS-Gruppe: Anzahl Trader $N_G$ (X-Achse) gegen Notional-Exposure in USD Mrd. (Y-Achse).

                        **Interpretation:** Hoher Notional-Wert bei tiefem $N_G$ zeigt, dass wenige Trader ein sehr grosses Marktgewicht halten — ein Zeichen für Konzentration und erhöhte Liquidationsgefahr.

                        **Ziel:** Das absolute finanzielle Marktgewicht einer Tradergruppe sichtbar machen, unabhängig von Kontraktzahl oder Marktstruktur.

                        **Besonderheit:** MMS-Werte werden negativ dargestellt. Die Berechnung nutzt den Front-Month-Futures-Preis (yfinance) und die marktspezifische Kontraktgrösse. Je Gruppe wird eine Regressionstrendlinie eingeblendet.

                        **Farbskala:** Keine kontinuierliche Farbskala — Dunkelblau = MML, Hellblau = MMS. Schwarzer Punkt = aktuellste Woche.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}
                        $$

                        $$
                        y_{G} = NV_{G} = \delta_{G} \times \mathrm{OI}_{G} \times CS \times P
                        $$

                        dabei gilt:

                        $$
                        \delta_{G} =
                        \begin{cases}
                        +1 & \text{falls } G = \mathrm{MM}_{L} \\
                        -1 & \text{falls } G = \mathrm{MM}_{S}
                        \end{cases}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM}_{L},\, \mathrm{MM}_{S}\}$: betrachtete Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $\mathrm{OI}_{G}$: aggregierte Position (Open Interest) der Gruppe $G$ in Kontrakten
                        - $CS$: Kontraktgrösse (Contract Size) des jeweiligen Futures
                        - $P$: Front-Month-Futures-Preis (yfinance)
                        - $\delta_{G}$: Vorzeichen ($+1$ für Long, $-1$ für Short)
                        - $NV_{G}$: Notional Value (Dollar-Exposure) der Gruppe $G$ in USD (Y-Achse)

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='dp-notional-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Time Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Time Indicator", id="section-dp-time"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt die OI-Konzentration (% des Total OI) der MML- und MMS-Gruppe gegen die Anzahl Trader, eingefärbt nach Kalenderjahr.

                        **Interpretation:** Punkte desselben Jahres bilden eine Zeitreihe innerhalb des Charts. Verschiebungen von Jahres-Clustern zeigen, ob sich das Positionierungsmuster der Gruppe über Zeit verändert hat.

                        **Ziel:** Historische Muster und strukturelle Verschiebungen im Trader-Verhalten erkennen und die aktuelle Positionierung zeitlich einordnen.

                        **Besonderheit:** MMS-Konzentration wird negativ dargestellt. Jedes Jahr erhält eine eigene Farbe.

                        **Farbskala:** Keine kontinuierliche Farbskala — Farbe = Kalenderjahr der Beobachtung. Schwarzer Punkt = aktuellste Woche.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}
                        $$

                        $$
                        y_{G} = \frac{\mathrm{OI}_{G}}{\mathrm{OI}_{N}} \times 100 \times \delta_{G}
                        $$

                        dabei gilt:

                        $$
                        \delta_{G} =
                        \begin{cases}
                        +1 & \text{falls } G = \mathrm{MM}_{L} \\
                        -1 & \text{falls } G = \mathrm{MM}_{S}
                        \end{cases}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM}_{L},\, \mathrm{MM}_{S}\}$: betrachtete Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ (in Kontrakten)
                        - $\mathrm{OI}_{N}$: Gesamtes Open Interest des Marktes
                        - $\delta_{G}$: Vorzeichen ($+1$ für Long, $-1$ für Short)
                        - $y_{G}$: OI-Konzentration der Gruppe $G$ in % (Y-Achse)

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='dp-time-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Price Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Price Indicator", id="section-dp-price"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das OI der PMPU-Gruppe (Long oder Short) gegen die Anzahl PMPU-Trader, eingefärbt nach dem 2nd Nearby Futures-Preis.

                        **Interpretation:** Häufungen bei bestimmten Preisniveaus zeigen, bei welchen Marktpreisen die PMPU-Gruppe typischerweise besonders stark oder schwach positioniert ist.

                        **Ziel:** Zusammenhang zwischen Preisniveau und PMPU-Positionierung sichtbar machen — für Einschätzungen zu Hedging-Verhalten und preissensitiven Positionierungsmustern.

                        **Besonderheit:** Graue Punkte erscheinen bei Märkten ohne 2nd-Nearby-Preisdaten (typischerweise Platin und Palladium). Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = 2nd Nearby Futures-Preis (USD). Rot = tiefer Preis, Grün = hoher Preis.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                $$
                x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                $$

                $$
                c = P_{2}
                $$

                **Variablen und Begriffe:**
                - **PMPUL:** Producer/Merchant/Processor/User Long
                - **PMPUS:** Producer/Merchant/Processor/User Short
                - $G \in \{\mathrm{PMPUL},\, \mathrm{PMPUS}\}$: betrachtete Tradergruppe
                - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ in Kontrakten (Y-Achse)
                - $P_{2}$: Schlusskurs des 2nd-Nearby-Futures (Databento)
                - $c$: Farbskala = $P_{2}$

                *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='dp-price-radio',
                    options=[
                        {'label': 'PMPUL', 'value': 'PMPUL'},
                        {'label': 'PMPUS', 'value': 'PMPUS'},
                    ],
                    value='PMPUL',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-price-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Curve Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Curve Indicator", id="section-dp-curve"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das OI der MM-Gruppe (Long oder Short) gegen die Anzahl MM-Trader, eingefärbt nach der Terminstruktur (Curve Range).

                        **Interpretation:** Häufungen roter Punkte bei hohem OI zeigen z.B., ob die MM-Gruppe bevorzugt in Backwardation-Phasen long positioniert ist.

                        **Ziel:** Zusammenhang zwischen Terminstruktur (Contango/Backwardation) und MM-Positionierung erkennen.

                        **Besonderheit:** Hellblaue Punkte erscheinen bei fehlenden 3rd-Nearby-Daten (typischerweise Platin und Palladium). Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = Curve Range (%). Rot = Backwardation (2nd Nearby teurer als 3rd Nearby), Grün = Contango (3rd Nearby teurer als 2nd Nearby).
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                        $$

                        $$
                        c = \frac{P_{3} - P_{2}}{P_{2}} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ in Kontrakten (Y-Achse)
                        - $P_{2}$: Schlusskurs des 2nd-Nearby-Futures (Databento)
                        - $P_{3}$: Schlusskurs des 3rd-Nearby-Futures (Databento)
                        - $c$: Curve Range in % (Farbskala)
                        - **Contango:** $c > 0$ – 3rd Nearby teurer als 2nd Nearby (normale Kurvenstruktur)
                        - **Backwardation:** $c < 0$ – 2nd Nearby teurer als 3rd Nearby (invertierte Kurve)

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='dp-curve-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-curve-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Factor (VIX) Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Factor (VIX) Indicator", id="section-dp-vix"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das OI der MM-Gruppe (Long oder Short) gegen die Anzahl MM-Trader, eingefärbt nach dem VIX-Niveau.

                        **Interpretation:** Häufungen dunkler Punkte bei hohem OI zeigen, ob die Gruppe Positionen bevorzugt in Phasen hoher oder tiefer Marktvolatilität aufbaut.

                        **Ziel:** Zusammenhang zwischen allgemeiner Marktunsicherheit (VIX) und MM-Positionierung sichtbar machen.

                        **Besonderheit:** Der VIX misst die vom Markt erwartete 30-Tages-Volatilität des S&P 500. Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = VIX-Niveau. Hell = tiefe Volatilität, Dunkelrot = hohe Volatilität.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                                $$
                                x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                                $$

                                $$
                                c = \mathrm{VIX}
                                $$

                                **Variablen und Begriffe:**
                                - **MML:** Managed Money Long
                                - **MMS:** Managed Money Short
                                - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                                - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                                - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ in Kontrakten (Y-Achse)
                                - $\mathrm{VIX}$: CBOE Volatility Index (erwartete 30-Tages-Volatilität des S&P 500)
                                - $c$: Farbskala = $\mathrm{VIX}$

                                *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                                """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='dp-vix-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-vix-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Factor (DXY) Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Factor (DXY) Indicator", id="section-dp-dxy"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das OI der MM-Gruppe (Long oder Short) gegen die Anzahl MM-Trader, eingefärbt nach dem DXY-Niveau (US-Dollar-Index).

                        **Interpretation:** Häufungen bei bestimmten DXY-Niveaus zeigen, ob die Gruppe Positionen bevorzugt in Phasen eines starken oder schwachen US-Dollars aufbaut.

                        **Ziel:** Zusammenhang zwischen Dollarstärke und MM-Positionierung sichtbar machen.

                        **Besonderheit:** Der DXY misst die Stärke des USD gegenüber einem Korb wichtiger Währungen. Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = DXY-Niveau. Hell = schwacher Dollar, Dunkelrot = starker Dollar.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                                $$
                                x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                                $$

                                $$
                                c = \mathrm{DXY}
                                $$

                                **Variablen und Begriffe:**
                                - **MML:** Managed Money Long
                                - **MMS:** Managed Money Short
                                - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                                - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                                - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ in Kontrakten (Y-Achse)
                                - $\mathrm{DXY}$: US-Dollar-Index (Stärke des USD ggü. einem Korb wichtiger Währungen)
                                - $c$: Farbskala = $\mathrm{DXY}$

                                *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                                """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='dp-dxy-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-dxy-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Currency Indicator (USD/CHF)
        dbc.Row([
            dbc.Col([
                html.H1("DP Currency Indicator (USD/CHF)", id="section-dp-currency"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das OI der MM-Gruppe (Long oder Short) gegen die Anzahl MM-Trader, eingefärbt nach dem USD/CHF-Wechselkurs.

                        **Interpretation:** Häufungen bei bestimmten USD/CHF-Niveaus zeigen, ob die Gruppe Positionen bevorzugt bei einem starken oder schwachen USD gegenüber dem CHF aufbaut.

                        **Ziel:** Positionierungsmuster aus Schweizer Währungsperspektive beleuchten — besonders relevant, da die betrachteten Rohstoffmärkte in USD notieren.

                        **Besonderheit:** USD/CHF als Währungsfaktor wurde gewählt, da das Dashboard primär für Schweizer Nutzer konzipiert ist. Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = USD/CHF-Kurs. Hell = tiefer Kurs (schwacher USD), Dunkel = hoher Kurs (starker USD).
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                    $$
                    x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                    $$

                    $$
                    c = FX
                    $$

                    **Variablen und Begriffe:**
                    - **MML:** Managed Money Long
                    - **MMS:** Managed Money Short
                    - $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$: betrachtete Tradergruppe
                    - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                    - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ in Kontrakten (Y-Achse)
                    - $FX$: USD/CHF-Wechselkurs
                    - $c$: Farbskala = $FX$

                    *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                    """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='dp-currency-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-currency-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Fundamental Indicator (Crude Oil Inventory)
        dbc.Row([
            dbc.Col([
                html.H1("DP Fundamental Indicator (Crude Oil Inventory)", id="section-dp-fundamental"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt das OI der PMPU-Gruppe (Long oder Short) gegen die Anzahl PMPU-Trader, eingefärbt nach dem US-Rohöl-Lagerbestand (EIA).

                        **Interpretation:** Häufungen bei tiefen Lagerbeständen und hohem PMPU Long OI zeigen typisches Hedging-Verhalten physischer Marktteilnehmer in Knappheitsphasen.

                        **Ziel:** Zusammenhang zwischen fundamentalem Angebotsniveau (Lagerbestände) und PMPU-Hedging-Positionierung sichtbar machen.

                        **Besonderheit:** Ausschliesslich für Crude Oil (WTI) verfügbar. EIA-Daten werden wöchentlich veröffentlicht und auf den CoT-Stichtag (Dienstag) ausgerichtet. Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = EIA-Lagerbestand (Tsd. Barrel). Hell = knappes Angebot, Dunkel = reichliches Angebot.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                    $$
                    x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                    $$

                    $$
                    c = F
                    $$

                    **Variablen und Begriffe:**
                    - **PMPUL:** Producer/Merchant/Processor/User Long
                    - **PMPUS:** Producer/Merchant/Processor/User Short
                    - $G \in \{\mathrm{PMPUL},\, \mathrm{PMPUS}\}$: betrachtete Tradergruppe
                    - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                    - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ in Kontrakten (Y-Achse)
                    - $F$: Fundamentalfaktor — hier US-Rohöl-Lagerbestand (EIA Ending Stocks excl. SPR, in Tsd. Barrel),
                      veröffentlicht wöchentlich durch die EIA; zeitlich auf den CoT-Stichtag (Dienstag) ausgerichtet
                    - $c$: Farbskala = $F$

                    *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                    """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='dp-fundamental-radio',
                    options=[
                        {'label': 'PMPUL', 'value': 'PMPUL'},
                        {'label': 'PMPUS', 'value': 'PMPUS'},
                    ],
                    value='PMPUL',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-fundamental-indicator-graph'),
                html.Br(),
            ], width=12)
        ]),

        html.Hr(),

        # DP Relative Concentration Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Relative Concentration Indicator", id="section-dp-rel-concentration"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt für alle acht Trader-Teilgruppen die relative Netto-Konzentration ($RC$, in Prozentpunkten) gegen die jeweilige Traderanzahl.

                        **Interpretation:** Gruppen mit positivem $RC$-Wert sind netto long-dominant; Gruppen mit negativem $RC$-Wert sind netto short-dominant. Der Abstand vom Nullpunkt zeigt die Stärke der Netto-Positionierung.

                        **Ziel:** Das vollständige Positionierungsprofil aller Tradergruppen in einem Chart darstellen — für direkte Marktvergleiche (z.B. Gold vs. Silber).

                        **Besonderheit:** Jede Gruppe hat eine eigene Farbe. Schwarzer Punkt = aktuellste Woche je Gruppe.

                        **Farbskala:** Keine kontinuierliche Farbskala — Farbe unterscheidet die acht Trader-Teilgruppen (MML, MMS, ORL, ORS, PMPUL, PMPUS, SDL, SDS).
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}, \qquad y_{G} = RC_{G}
                        $$

                        $$
                        RC_{G} = \delta_{G} \times \left( \frac{L_{G}}{\mathrm{OI}_{N}} - \frac{S_{G}}{\mathrm{OI}_{N}} \right) \times 100
                        $$

                        dabei gilt:

                        $$
                        \delta_{G} =
                        \begin{cases}
                        +1 & \text{falls } G \in \{\mathrm{MM}_{L},\, \mathrm{PMPU}_{L},\, \mathrm{SD}_{L},\, \mathrm{OR}_{L}\} \\
                        -1 & \text{falls } G \in \{\mathrm{MM}_{S},\, \mathrm{PMPU}_{S},\, \mathrm{SD}_{S},\, \mathrm{OR}_{S}\}
                        \end{cases}
                        $$

                        **Variablen und Begriffe:**
                        - $G$: betrachtete Trader-Teilgruppe (8 Serien — 4 Tradergruppen × Long/Short)
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $L_{G}$: Long Open Interest der Gruppe $G$
                        - $S_{G}$: Short Open Interest der Gruppe $G$
                        - $\mathrm{OI}_{N}$: gesamtes Open Interest aller offenen Kontrakte
                        - $\delta_{G}$: Vorzeichen ($+1$ für Long-Serien, $-1$ für Short-Serien)
                        - $RC_{G}$: Relative Concentration der Gruppe $G$ (in Prozentpunkten, Y-Achse)
                        - **Schwarzer Punkt:** aktuellste Woche je Gruppe

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='dp-relative-concentration-graph'),
            ], width=12)
        ]),

        html.Hr(),

        # DP Seasonal Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Seasonal Indicator", id="section-dp-seasonal"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt die relative Netto-Konzentration der PMPU-Gruppe ($RC_{\mathrm{PMPU}}$, in %) gegen die Anzahl PMPU Long Trader, eingefärbt nach Quartal (Q1–Q4).

                        **Interpretation:** Quartals-Cluster zeigen, ob sich das PMPU-Hedging-Verhalten saisonal verändert — z.B. ob Produzenten in bestimmten Quartalen systematisch stärker oder schwächer netto short absichern.

                        **Ziel:** Saisonale Muster im Hedging-Verhalten der PMPU-Gruppe erkennen und von strukturellen Verschiebungen abgrenzen.

                        **Besonderheit:** Ausschliesslich die PMPU Long Seite wird dargestellt. Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Keine kontinuierliche Farbskala — Farbe unterscheidet die vier Quartale (Q1–Q4).
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x = N_{\mathrm{PMPU}_{L}}, \qquad y = RC_{\mathrm{PMPU}}
                        $$

                        $$
                        RC_{\mathrm{PMPU}} = \frac{\mathrm{OI}_{\mathrm{PMPU}_{L}} - \mathrm{OI}_{\mathrm{PMPU}_{S}}}{\mathrm{OI}_{N}} \times 100
                        $$

                        $$
                        c = Q
                        $$

                        **Variablen und Begriffe:**
                        - $N_{\mathrm{PMPU}_{L}}$: Anzahl PMPU Long Trader (X-Achse)
                        - $\mathrm{OI}_{\mathrm{PMPU}_{L}}$: Long Open Interest der PMPU-Gruppe
                        - $\mathrm{OI}_{\mathrm{PMPU}_{S}}$: Short Open Interest der PMPU-Gruppe
                        - $\mathrm{OI}_{N}$: gesamtes Open Interest aller offenen Kontrakte
                        - $RC_{\mathrm{PMPU}}$: Relative Netto-Konzentration der PMPU-Gruppe (in %, Y-Achse)
                        - $Q \in \{Q_{1},\, Q_{2},\, Q_{3},\, Q_{4}\}$: Quartal der Beobachtung
                        - $c$: Farbskala = $Q$

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='dp-seasonal-indicator-graph'),
            ], width=12)
        ]),

        html.Hr(),

        # DP Net Indicator with Median
        dbc.Row([
            dbc.Col([
                html.H1("DP Net Indicator with Median", id="section-dp-net"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt die Netto-Positionierung der MM-Gruppe: Netto-Traderzahl (X-Achse) gegen Netto-Open-Interest (Y-Achse), eingefärbt nach Kalenderjahr. Gestrichelte Medianlinien als Referenz.

                        **Interpretation:** Punkte im oberen rechten Quadrant (mehr Long-Trader und mehr Long-OI als Median) zeigen ausgeprägte Netto-Long-Phasen. Abweichungen zwischen X und Y — z.B. viele Long-Trader, aber wenig Netto-OI — weisen auf Spread-Positionen hin.

                        **Ziel:** Netto-Positionierung der MM-Gruppe und historische Extremwerte auf einen Blick erfassbar machen.

                        **Besonderheit:** Farbkodierung nach Jahr, um zeitliche Cluster erkennbar zu machen. Schwarzer Punkt = aktuellste Woche, Roter Punkt = erste Woche im gewählten Zeitraum.

                        **Farbskala:** Keine kontinuierliche Farbskala — Farbe = Kalenderjahr. Gestrichelte Linien = Median-Referenzwerte.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x = N_{\mathrm{MM}}^{\mathrm{Net}} = N_{\mathrm{MM}_{L}} - N_{\mathrm{MM}_{S}}
                        $$

                        $$
                        y = \mathrm{OI}_{\mathrm{MM}}^{\mathrm{Net}} = \mathrm{OI}_{\mathrm{MM}_{L}} - \mathrm{OI}_{\mathrm{MM}_{S}}
                        $$

                        $$
                        c = Y
                        $$

                        **Medians (gestrichelte Referenzlinien):**

                        $$
                        \widetilde{x} = \operatorname{Median}_{t}\!\bigl(N_{\mathrm{MM}}^{\mathrm{Net}}(t)\bigr), \qquad
                        \widetilde{y} = \operatorname{Median}_{t}\!\bigl(\mathrm{OI}_{\mathrm{MM}}^{\mathrm{Net}}(t)\bigr)
                        $$

                        **Variablen und Begriffe:**
                        - $t$: Laufindex über alle Beobachtungswochen im gewählten Datumsbereich (für Medianberechnung)
                        - $N_{\mathrm{MM}_{L}}$: Anzahl MM Long-Trader
                        - $N_{\mathrm{MM}_{S}}$: Anzahl MM Short-Trader
                        - $\mathrm{OI}_{\mathrm{MM}_{L}}$: Long-Open-Interest der MM-Gruppe
                        - $\mathrm{OI}_{\mathrm{MM}_{S}}$: Short-Open-Interest der MM-Gruppe
                        - $N_{\mathrm{MM}}^{\mathrm{Net}}$: Netto-Traderzahl der MM-Gruppe (X-Achse)
                        - $\mathrm{OI}_{\mathrm{MM}}^{\mathrm{Net}}$: Netto-Open-Interest der MM-Gruppe (Y-Achse)
                        - $\widetilde{x},\, \widetilde{y}$: Mediane über den gewählten Zeitraum (gestrichelte Linien)
                        - $Y$: Kalenderjahr der Beobachtung
                        - $c$: Farbskala = $Y$

                        *Alle Variablen (ausser den Medians) beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='dp-net-indicators-graph'),
            ], width=12)
        ]),

        html.Hr(),

        # DP Position Size Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Position Size Indicator", id="section-dp-position-size"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt die durchschnittliche Positionsgrösse (Kontrakte pro Trader) der MML- oder MMS-Gruppe gegen die Anzahl MM-Trader, eingefärbt nach Open Interest.

                        **Interpretation:** Punkte oben links (wenige Trader, grosse Positionen) zeigen hohe Conviction einzelner Trader. Punkte unten rechts (viele Trader, kleine Positionen) deuten auf breit gestreutes Engagement hin.

                        **Ziel:** Zusammenhang zwischen Traderanzahl, Positionsgrösse und Marktvolumen sichtbar machen — für Rückschlüsse auf Conviction und Liquidationsrisiken.

                        **Besonderheit:** Gestrichelte Medianlinien auf beiden Achsen als Referenz. Schwarzer Punkt = aktuellste Woche, Roter Punkt = erste Woche im gewählten Zeitraum.

                        **Farbskala:** Farbe = Open Interest (Kontrakte). Hell = hohes OI, Dunkel = tiefes OI.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}, \qquad y_{G} = \mathrm{Size}_{G} = \frac{\mathrm{OI}_{G}}{N_{G}}
                        $$

                        $$
                        c = \mathrm{OI}_{N}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM}_{L},\, \mathrm{MM}_{S}\}$: betrachtete Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $\mathrm{OI}_{G}$: Open Interest der Gruppe $G$ (in Kontrakten)
                        - $\mathrm{Size}_{G}$: durchschnittliche Positionsgrösse pro Trader in Kontrakten/Trader (Y-Achse)
                        - $\mathrm{OI}_{N}$: gesamtes Open Interest aller offenen Kontrakte
                        - $c$: Farbskala = $\mathrm{OI}_{N}$
                        - **Gestrichelte Linien:** Medianwerte auf X- und Y-Achse als Referenz

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='mm-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='dp-position-size-indicator'),
            ], width=12)
        ]),

        html.Hr(),

        # DP Hedging Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Hedging Indicator", id="section-dp-hedging"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt die OI-Position der MML- oder MMS-Gruppe gegen die Anzahl MM-Trader, eingefärbt nach der Netto-Position der PMPU-Gruppe.

                        **Interpretation:** Hoher positiver Farbwert (PMPU netto long) bei gleichzeitig hohem MM Long OI kann auf gegensätzliche Positionierung zwischen physischen (PMPU) und spekulativen (MM) Tradern hinweisen.

                        **Ziel:** Beziehung zwischen spekulativer (MM) und physischer (PMPU) Tradergruppe sichtbar machen — um einzuschätzen, welche Seite mehr „Dry Powder" hat.

                        **Besonderheit:** Bubble-Grösse variiert proportional zum gesamten Open Interest des Marktes.

                        **Kreisgrösse:** Die Kreisgrösse ist proportional zum gesamten Open Interest des Marktes ($\mathrm{OI}_{\mathrm{total}}$).

                        **Farbskala:** Farbe = PMPU Netto-OI ($\mathrm{OI}_{\mathrm{PMPU}}^L - \mathrm{OI}_{\mathrm{PMPU}}^S$). Positiv = PMPU netto long, Negativ = PMPU netto short.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_{G} = N_{G}, \qquad y_{G} = \mathrm{OI}_{G}
                        $$

                        $$
                        c = \mathrm{OI}_{\mathrm{PMPU}_{L}} - \mathrm{OI}_{\mathrm{PMPU}_{S}}
                        $$

                        **Variablen und Begriffe:**
                        - $G \in \{\mathrm{MM}_{L},\, \mathrm{MM}_{S}\}$: betrachtete MM-Tradergruppe
                        - $N_{G}$: Anzahl Trader der Gruppe $G$ (X-Achse)
                        - $\mathrm{OI}_{G}$: Open Interest der MM-Gruppe $G$ (Y-Achse, in Kontrakten)
                        - $\mathrm{OI}_{\mathrm{PMPU}_{L}}$: Long-Open-Interest der PMPU-Gruppe
                        - $\mathrm{OI}_{\mathrm{PMPU}_{S}}$: Short-Open-Interest der PMPU-Gruppe
                        - $c$: Netto-Position der PMPU-Gruppe (Farbskala) — positiv = Long-Überhang, negativ = Short-Überhang
                        - **Bubble-Grösse:** proportional zum gesamten Open Interest $\mathrm{OI}_{N}$ (Marktliquidität)

                        *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.RadioItems(
                    id='trader-group-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    className='mb-4'
                ),
                dcc.Graph(id='hedging-indicator-graph'),
            ], width=12)
        ]),

        html.Hr(),

        # DP Concentration / Clustering Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Concentration / Clustering Indicator", id="section-dp-conc-clustering"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt für jeden Markt einen Punkt — normierter Clustering-Wert (X-Achse, 0–100) gegen normierten Concentration-Wert (Y-Achse, 0–100) — als Marktvergleichs-Snapshot.

                        **Interpretation:** Märkte oben rechts (hohes Clustering, hohe Concentration) sind doppelt extrem positioniert. Bei einem Preisschock reagieren diese Märkte typischerweise stärker als andere.

                        **Ziel:** Relative Positionierungsextrema über alle Märkte auf einen Blick vergleichen — für die Identifikation von Märkten mit erhöhter Reaktionsstärke.

                        **Besonderheit:** Normierung erfolgt durch globales Min-Max über alle Märkte im gewählten Zeitraum — jeder Punkt repräsentiert einen Markt als Mittelwert über den Zeitraum. Keine Zeitdimension.

                        **Farbskala:** Keine Farbskala — alle Punkte grün mit Marktbezeichnung.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Für jeden Markt $m$ im gewählten Zeitraum werden zunächst die Mittelwerte der Rohwerte gebildet, anschliessend global über alle Märkte min-max-normiert:

                        $$
                        x_{m} = \mathrm{Range}(\overline{K}_{m}), \qquad y_{m} = \mathrm{Range}(\overline{RC}_{m})
                        $$

                        Die Normierung erfolgt jeweils mit der folgenden Range-Formel:

                        $$
                        \mathrm{Range}(v) = \frac{v - \min(v)}{\max(v) - \min(v)} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $m$: betrachteter Markt (ein Punkt pro Markt)
                        - $\overline{K}_{m}$: Mittelwert des Clustering-Werts $K$ für Markt $m$ über den gewählten Zeitraum
                        - $\overline{RC}_{m}$: Mittelwert der relativen Netto-Konzentration $RC$ für Markt $m$ über den gewählten Zeitraum
                        - $v$: Rohwert ($\overline{K}_{m}$ bzw. $\overline{RC}_{m}$)
                        - $\min(v),\, \max(v)$: Minimum bzw. Maximum von $v$ über alle Märkte
                        - $x_{m}$: normierter Clustering-Wert (0–100, X-Achse)
                        - $y_{m}$: normierter Concentration-Wert (0–100, Y-Achse)

                        **Quadranten-Interpretation:**
                        - **Oben rechts** (hoch/hoch): doppelt extrem — Markt tendiert bei Schocks zu stärkeren Preisbewegungen
                        - **Oben links** (tiefes Clustering, hohe Concentration): wenige Trader halten grosse Positionen
                        - **Unten rechts** (hohes Clustering, tiefe Concentration): viele Trader, aber kleine Netto-Positionen

                        *Die zugrundeliegenden Rohdaten beziehen sich je Beobachtung auf denselben Reporting-Zeitpunkt; dargestellt sind Mittelwerte über den gewählten Zeitraum.*
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.DatePickerRange(
                    id='concentration-clustering-date-picker-range',
                    display_format='YYYY-MM-DD',
                    className='mb-4'
                ),
                dcc.RadioItems(
                    id='concentration-clustering-radio',
                    options=[
                        {'label': 'MML', 'value': 'MML'},
                        {'label': 'MMS', 'value': 'MMS'},
                    ],
                    value='MML',
                    inline=True,
                    className='mb-4'
                ),
                dcc.Graph(id='dp-concentration-clustering-graph'),
            ], width=12)
        ]),
    ])
