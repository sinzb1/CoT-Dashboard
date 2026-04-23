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
                        Achsen (Zeitpunkt $t$):
                        $$
                        x_G(t) = N_G(t), \qquad y_G(t) = \mathrm{OI}_G(t)
                        $$

                        mit $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$; $y_{\mathrm{MMS}}(t)$ wird im Plot negativ dargestellt.

                        **Variablen und Begriffe:**
                        - $\mathrm{OI}_G(t)$: Open Interest der Gruppe $G$ zum Zeitpunkt $t$ (Long bzw. Short)
                        - $N_G(t)$: Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - **Farbkodierung:** Dunkelblau = MML-Wolke (Long-Seite), Hellblau = MMS-Wolke (Short-Seite)
                        - **Schwarzer Punkt:** jeweils die **aktuellste Woche**
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
                        **Indikator:** Zeigt das aggregierte Dollar-Exposure (Notional) der MML- und MMS-Gruppe: Anzahl Trader (X-Achse) gegen Notional-Exposure in USD Mrd. (Y-Achse).

                        **Interpretation:** Hoher Notional-Wert bei tiefer Traderanzahl zeigt, dass wenige Trader ein sehr grosses Marktgewicht halten — ein Zeichen für Konzentration und erhöhte Liquidationsgefahr.

                        **Ziel:** Das absolute finanzielle Marktgewicht einer Tradergruppe sichtbar machen, unabhängig von Kontraktzahl oder Marktstruktur.

                        **Besonderheit:** MMS-Werte werden negativ dargestellt. Die Berechnung nutzt den Front-Month-Futures-Preis (yfinance) und die marktspezifische Kontraktgrösse. Je Gruppe wird eine Regressionstrendlinie eingeblendet.

                        **Farbskala:** Keine kontinuierliche Farbskala — Dunkelblau = MML, Hellblau = MMS. Schwarzer Punkt = aktuellste Woche.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_G(t) = \mathrm{Traders}_G(t)
                        $$

                        $$
                        y_G(t) = \mathrm{DP\ Notional}_G(t)
                        = \mathrm{Position}_G(t)\times \mathrm{ContractSize}\times \mathrm{Price}(t)
                        $$

                        **Variablen und Begriffe:**
                        - **$G$:** betrachtete Tradergruppe, $\mathrm{MML}$ oder $\mathrm{MMS}$
                        - **$\mathrm{Traders}_G(t)$:** Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - **$\mathrm{Position}_G(t)$:** aggregierte Position der Gruppe $G$ zum Zeitpunkt $t$ (in Kontrakten)
                        - **$\mathrm{ContractSize}$:** Kontraktgrösse des jeweiligen Futures
                        - **$\mathrm{Price}(t)$:** Futures-Preis zum Zeitpunkt $t$
                        - **$\mathrm{DP\ Notional}_G(t)$:** aggregiertes Notional-Exposure der Gruppe $G$ in USD
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
                        Achsen (Zeitpunkt $t$), mit $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$:
                        $$
                        x_G(t) = N_G(t), \qquad
                        y_G(t) = \sigma_G \cdot \frac{\mathrm{OI}_G(t)}{\mathrm{OI}_{\mathrm{total}}(t)} \cdot 100
                        $$

                        wobei $\sigma_{\mathrm{MML}} = +1$ und $\sigma_{\mathrm{MMS}} = -1$ (MMS-Seite wird negativ dargestellt).

                        **Variablen und Begriffe:**
                        - $N_G(t)$: Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$ (X-Achse)
                        - $\mathrm{OI}_G(t)$: Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                        - $\mathrm{OI}_{\mathrm{total}}(t)$: Gesamtes Open Interest des Marktes zum Zeitpunkt $t$
                        - $y_G(t)$: OI-Konzentration der Gruppe $G$ in % (Y-Achse)
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
                **Für die Long-Seite und die Short-Seite gilt:**

                $$
                x_G(t) = N_G(t), \qquad y_G(t) = \mathrm{OI}_G(t)
                $$

                $$
                c(t)=P_{\mathrm{2nd\ Nearby}}(t)
                $$

                **Variablen und Begriffe:**
                - **PMPUL:** Producer/Merchant/Processor/User Long
                - **PMPUS:** Producer/Merchant/Processor/User Short
                - **$G$:** betrachtete Gruppe mit $G \in \{\mathrm{PMPUL},\, \mathrm{PMPUS}\}$
                - **$N_G(t)$:** Anzahl Trader der betrachteten Gruppe $G$ zum Zeitpunkt $t$ (X-Achse)
                - **$\mathrm{OI}_G(t)$:** Open Interest der betrachteten Gruppe $G$ zum Zeitpunkt $t$ (Y-Achse)
                - **$P_{\mathrm{2nd\ Nearby}}(t)$:** Schlusskurs des 2nd-Nearby-Futures am Reportdatum $t$ (Databento, Punktfarbe)
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
                        **Für Managed Money Long (MML) und Managed Money Short (MMS) gilt:**

                        $$
                        c(t) = \frac{P_{\text{3rd Nearby}}(t) - P_{\text{2nd Nearby}}(t)}{P_{\text{2nd Nearby}}(t)} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$N_G(t)$:** Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - **$\mathrm{OI}_G(t)$:** Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                        - **Punktfarbe:** $c(t)$, d. h. die Curve Range (%) zum Zeitpunkt $t$
                        - **Contango:** $c(t) > 0$ – 3rd Nearby teurer als 2nd Nearby (normale Kurvenstruktur)
                        - **Backwardation:** $c(t) < 0$ – 2nd Nearby teurer als 3rd Nearby (invertierte Kurve)
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
                                **Für Managed Money Long (MML) und Managed Money Short (MMS) gilt:**

                                $$
                                c(t)=\mathrm{VIX}(t)
                                $$
                                """, mathjax=True), width=12),
                        ], className="mb-2"),
                        dcc.Markdown(r"""
                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$N_G(t)$:** Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - **$\mathrm{OI}_G(t)$:** Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                        - **Punktfarbe:** $c(t)$, d. h. das Niveau des VIX zum Zeitpunkt $t$
                        """, mathjax=True),
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
                                **Für Managed Money Long (MML) und Managed Money Short (MMS) gilt:**

                                $$
                                c(t)=\mathrm{DXY}(t)
                                $$
                                """, mathjax=True), width=12),
                        ], className="mb-2"),
                        dcc.Markdown(r"""
                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$N_G(t)$:** Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - **$\mathrm{OI}_G(t)$:** Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                        - **Punktfarbe:** $c(t)$, d. h. das Niveau des DXY zum Zeitpunkt $t$
                        """, mathjax=True),
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
                    **Für Managed Money Long (MML) und Managed Money Short (MMS) gilt:**

                    $$
                    c(t)=FX(t)
                    $$

                    **Variablen und Begriffe:**
                    - **MML:** Managed Money Long
                    - **MMS:** Managed Money Short
                    - **$N_G(t)$:** Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                    - **$\mathrm{OI}_G(t)$:** Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                    - **$FX(t)$:** FX-Wert zum Zeitpunkt $t$
                    - **Punktfarbe:** $c(t)$, Niveau des USD/CHF-Wechselkurses zum Zeitpunkt $t$
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
                    **Für PMPU Long (PMPUL) und PMPU Short (PMPUS) gilt:**

                    $$
                    x_G(t) = N_G(t), \qquad y_G(t) = \mathrm{OI}_G(t)
                    $$

                    $$
                    c(t) = \mathrm{Inventory}_{\mathrm{EIA}}(t)
                    $$

                    **Variablen und Begriffe:**
                    - **$G$:** betrachtete Tradergruppe, $\mathrm{PMPUL}$ oder $\mathrm{PMPUS}$
                    - **$N_G(t)$:** Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                    - **$\mathrm{OI}_G(t)$:** Open Interest der Gruppe $G$ zum Zeitpunkt $t$ (in Kontrakten)
                    - **$\mathrm{Inventory}_{\mathrm{EIA}}(t)$:** US-Rohöl-Lagerbestand (Ending Stocks excl. SPR) in Tausend Barrel,
                      veröffentlicht wöchentlich durch die EIA; zeitlich auf den CoT-Stichtag (Dienstag) ausgerichtet
                    - **Punktfarbe:** $c(t)$, d. h. das Lagerbestandsniveau zum Zeitpunkt $t$
                    - **Schwarzer Punkt:** aktuellste verfügbare Woche
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
                        Achsen (Zeitpunkt $t$):
                        $$
                        x_G(t) = N_G(t), \qquad y_G(t) = RC_G(t)
                        $$

                        mit

                        $$
                        RC_G(t) = 100 \cdot \sigma_G \left( \frac{L_G(t)}{OI(t)} - \frac{S_G(t)}{OI(t)} \right)
                        $$

                        wobei
                        $$
                        G \in \{\mathrm{MM}\text{-}L,\, \mathrm{MM}\text{-}S,\, \mathrm{PMPU}\text{-}L,\, \mathrm{PMPU}\text{-}S,\, \mathrm{SD}\text{-}L,\, \mathrm{SD}\text{-}S,\, \mathrm{OR}\text{-}L,\, \mathrm{OR}\text{-}S\}
                        $$

                        und
                        - $L_G(t)$: Long Open Interest der Gruppe $G$
                        - $S_G(t)$: Short Open Interest der Gruppe $G$
                        - $OI(t)$: Gesamtes Open Interest zum Zeitpunkt $t$
                        - $N_G(t)$: Anzahl Trader (Long oder Short) der Gruppe $G$
                        - $\sigma_G = +1$ für Long-Serien (MM-L, OR-L, PMPU-L, SD-L)
                        - $\sigma_G = -1$ für Short-Serien (MM-S, OR-S, PMPU-S, SD-S)

                        **Variablen und Begriffe:**
                        - $\mathrm{OI}(t)$: gesamtes Open Interest aller offenen Kontrakte zum Zeitpunkt $t$
                        - $N_G(t)$: Anzahl Trader in Gruppe $G$ zum Zeitpunkt $t$
                        - $RC_G(t)$: Relative Concentration (in Prozentpunkten) einer Gruppe zum Zeitpunkt $t$
                        - **Schwarzer Punkt:** markiert den Wert der **aktuellsten Woche** je Gruppe
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
                        x(t) = N_{\mathrm{PMPU}}^L(t), \qquad y(t) = RC_{\mathrm{PMPU}}(t)
                        $$

                        $$
                        RC_{\mathrm{PMPU}}(t) = \frac{\mathrm{OI}_{\mathrm{PMPU}}^L(t) - \mathrm{OI}_{\mathrm{PMPU}}^S(t)}{\mathrm{OI}_{\mathrm{total}}(t)} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $N_{\mathrm{PMPU}}^L(t)$: Anzahl PMPU Long Trader zum Zeitpunkt $t$ (X-Achse)
                        - $\mathrm{OI}_{\mathrm{PMPU}}^L(t)$: Long Open Interest der PMPU-Gruppe
                        - $\mathrm{OI}_{\mathrm{PMPU}}^S(t)$: Short Open Interest der PMPU-Gruppe
                        - $\mathrm{OI}_{\mathrm{total}}(t)$: Gesamtes Open Interest des Marktes
                        - $RC_{\mathrm{PMPU}}(t)$: Relative Netto-Konzentration der PMPU-Gruppe in % (Y-Achse)
                        - Farbe: Quartal der Beobachtung (Q1–Q4)
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
                        Achsen (Zeitpunkt $t$):
                        $$
                        x(t)=N^{\text{Net}}(t)=N^{\text{Long}}(t)-N^{\text{Short}}(t),
                        \qquad
                        y(t)=\mathrm{OI}^{\text{Net}}(t)=\mathrm{OI}^{\text{Long}}(t)-\mathrm{OI}^{\text{Short}}(t)
                        $$

                        **Medians (gestrichelte Referenzlinien):**
                        $$
                        \widetilde{N}^{\text{Net}}=\operatorname{Median}_t\!\big(N^{\text{Net}}(t)\big),
                        \qquad
                        \widetilde{\mathrm{OI}}^{\text{Net}}=\operatorname{Median}_t\!\big(\mathrm{OI}^{\text{Net}}(t)\big)
                        $$

                        **Variablen und Begriffe:**
                        - $t$: Kalenderwoche/Beobachtungszeitpunkt innerhalb des gewählten Datumsbereichs
                        - $N^{\text{Long}}(t)$: Anzahl Long-Trader (MM) zum Zeitpunkt $t$
                        - $N^{\text{Short}}(t)$: Anzahl Short-Trader (MM) zum Zeitpunkt $t$
                        - $N^{\text{Net}}(t)$: Netto-Traderzahl $=\;N^{\text{Long}}(t)-N^{\text{Short}}(t)$
                        - $\mathrm{OI}^{\text{Long}}(t)$: Long-Open-Interest (MM) zum Zeitpunkt $t$
                        - $\mathrm{OI}^{\text{Short}}(t)$: Short-Open-Interest (MM) zum Zeitpunkt $t$
                        - $\mathrm{OI}^{\text{Net}}(t)$: Netto-Open-Interest $=\;\mathrm{OI}^{\text{Long}}(t)-\mathrm{OI}^{\text{Short}}(t)$
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
                        dcc.Markdown(r"""
                        Achsen (Zeitpunkt $t$), mit $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$:
                        $$
                        x_G(t) = N_G(t), \qquad y_G(t) = \mathrm{PS}_G(t) = \frac{\mathrm{OI}_G(t)}{N_G(t)}
                        $$

                        Farbcodierung:
                        $$
                        \mathrm{color}_G(t) \propto \mathrm{OI}_{\mathrm{total}}(t)
                        $$

                        **Variablen und Begriffe:**
                        - $N_G(t)$: Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$ (X-Achse)
                        - $\mathrm{PS}_G(t)$: durchschnittliche Positionsgrösse je Trader (Kontrakte/Trader; Y-Achse)
                        - $\mathrm{OI}_G(t)$: Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                        - $\mathrm{OI}_{\mathrm{total}}(t)$: Gesamtes Open Interest des Marktes (Punktfarbe)
                        - Gestrichelte Linien: Medianwerte auf X- und Y-Achse als Referenz
                        """, mathjax=True),
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
                        Achsen (Zeitpunkt $t$):
                        $$
                        x_G(t) = N_G(t), \qquad y_G(t) = \mathrm{OI}_G(t)
                        $$

                        mit $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$

                        Farbcodierung – Netto-Positionierung der PMPU (Zeitpunkt $t$):
                        $$
                        \mathrm{Color}_G(t)
                        \;=\;
                        \mathrm{OI}^L_{\mathrm{PMPU}}(t) - \mathrm{OI}^S_{\mathrm{PMPU}}(t)
                        $$

                        **Variablen und Begriffe:**
                        - $N_G(t)$: Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - $\mathrm{OI}_G(t)$: Open Interest der Gruppe $G$ (MM Long oder Short) zum Zeitpunkt $t$
                        - $\mathrm{OI}^L_{\mathrm{PMPU}}(t)$: Long-Open-Interest der PMPU-Gruppe zum Zeitpunkt $t$
                        - $\mathrm{OI}^S_{\mathrm{PMPU}}(t)$: Short-Open-Interest der PMPU-Gruppe zum Zeitpunkt $t$
                        - **PMPU(L/S):** Producer/Merchant/Processor/User, je nach Auswahl Long (PMPUL) oder Short (PMPUS)
                        - **Bubble-Grösse:** proportional zum gesamten Open Interest (Marktliquidität bzw. Marktgewicht)
                        - **Punktfarbe:** rohe Netto-Position der PMPU-Gruppe; positiv = Long-Überhang, negativ = Short-Überhang
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
                        Für jeden Markt $m$ im gewählten Zeitraum wird der Mittelwert der Rohdaten berechnet, dann global normiert:

                        $$
                        x_m = \frac{\overline{\mathrm{Clustering}}_m - \min_m \overline{\mathrm{Clustering}}_m}{\max_m \overline{\mathrm{Clustering}}_m - \min_m \overline{\mathrm{Clustering}}_m} \times 100
                        $$

                        $$
                        y_m = \frac{\overline{RC}_m - \min_m \overline{RC}_m}{\max_m \overline{RC}_m - \min_m \overline{RC}_m} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - $m$: betrachteter Markt (ein Punkt pro Markt)
                        - $\overline{\mathrm{Clustering}}_m$: Mittelwert des Clustering-Werts für Markt $m$ über den gewählten Zeitraum
                        - $\overline{RC}_m$: Mittelwert der relativen Netto-Konzentration ($RC$) für Markt $m$ über den gewählten Zeitraum
                        - $x_m$: normierter Clustering-Wert (0–100, X-Achse)
                        - $y_m$: normierter Concentration-Wert (0–100, Y-Achse)

                        **Quadranten-Interpretation:**
                        - **Oben rechts** (hoch/hoch): doppelt extrem — Markt tendiert bei Schocks zu stärkeren Preisbewegungen
                        - **Oben links** (tiefes Clustering, hohe Concentration): wenige Trader halten grosse Positionen
                        - **Unten rechts** (hohes Clustering, tiefe Concentration): viele Trader, aber kleine Netto-Positionen
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
