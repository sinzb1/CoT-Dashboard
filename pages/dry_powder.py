from dash import dcc, html
import dash_bootstrap_components as dbc


def layout():
    return html.Div([

        # DP Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **DP (Dry Powder)** ist eine Methode zur Visualisierung der Positionierung in Rohstoffmärkten.
                        Dabei wird die Grösse der Long- und Short-Positionen (*Open Interest*) mit der Anzahl der Trader
                        in einer bestimmten Gruppe (z. B. Money Manager) in Beziehung gesetzt.

                        Das **Ziel des Indikators** ist es, einschätzen zu können, ob bestehende Positionen noch ausgebaut werden
                        können oder ob sie anfällig für Liquidationen sind. DP-Indikatoren werden in Diagrammen dargestellt
                        und können direkt als Handelssignale genutzt werden, um Marktchancen und Risiken besser zu bewerten.
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
                html.H1("DP Notional Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Notional Indicator** misst die aggregierte Long- bzw. Short-Exponierung
                        einer bestimmten Tradergruppe in Notional-Dollar, indem das Open Interest der Gruppe mit der
                        Kontraktgrösse und dem zugrunde liegenden Futures-Preis multipliziert wird. Dadurch wird sichtbar,
                        wie gross das gesamte finanzielle Exposure einer Gruppe im Markt ist und wie stark sie kapitalmässig engagiert ist.

                        Das **Ziel des Indikators** ist es, die absolute Markt-Exponierung einer Tradergruppe in USD sichtbar
                        zu machen. Er hilft zu beurteilen, ob Veränderungen im Engagement einer Gruppe primär auf eine veränderte
                        Anzahl Trader oder auf ein höheres bzw. tieferes aggregiertes Positionsvolumen zurückzuführen sind.
                        Dadurch lassen sich Rückschlüsse auf die finanzielle Bedeutung und das Marktgewicht einzelner Tradergruppen ziehen.

                        **Farbskala:** Die Punktfarbe unterscheidet die jeweilige Tradergruppe. In der dargestellten Ausprägung
                        steht dunkelblau für Managed Money Long (MML) und hellblau für Managed Money Short (MMS).
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
                html.H1("DP Time Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Time Indicator** zeigt, wie sich die Long- bzw. Short-Konzentration
                        einer bestimmten Tradergruppe in Abhängigkeit von der Anzahl Trader über die Zeit entwickelt.
                        Dadurch wird sichtbar, wie stark eine Gruppe relativ zum gesamten Markt positioniert ist und
                        wie sich diese Positionierung im historischen Verlauf verändert.

                        Das **Ziel des Indikators** ist es, die zeitliche Entwicklung der Marktpositionierung einer
                        Tradergruppe sichtbar zu machen. Er hilft zu beurteilen, ob sich Konzentrationsmuster in Phasen
                        mit vielen oder wenigen Tradern wiederholen und wie sich die aktuelle Positionierung im Vergleich
                        zu früheren Jahren einordnen lässt. Dadurch lassen sich historische Muster, Verschiebungen in der
                        Marktstruktur und mögliche Extremphasen erkennen.

                        **Farbskala:** Die Punktfarbe codiert das jeweilige Jahr der Beobachtung. Dadurch wird sichtbar,
                        aus welcher Zeitperiode ein Punkt stammt und wie sich die Positionierung über die Jahre entwickelt.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                            **Für Managed Money Long (MML):**

                            $$
                            \mathrm{DP\ Time}_{\mathrm{MML}}=
                            \frac{\mathrm{Open\ Interest}_{\mathrm{MML}}}
                            {\mathrm{Total\ Open\ Interest}} \cdot 100
                            $$
                            """, mathjax=True), width=12, lg=6),

                            dbc.Col(dcc.Markdown(r"""
                            **Für Managed Money Short (MMS):**

                            $$
                            \mathrm{DP\ Time}_{\mathrm{MMS}}=
                            -\,\frac{\mathrm{Open\ Interest}_{\mathrm{MMS}}}
                            {\mathrm{Total\ Open\ Interest}} \cdot 100
                            $$
                            """, mathjax=True), width=12, lg=6),
                        ], className="mb-2"),

                        dcc.Markdown(r"""
                        **Variablen und Begriffe:**
                        - **MML:** Managed Money Long
                        - **MMS:** Managed Money Short
                        - **$\mathrm{OI}_{\mathrm{MML}}(t)$:** Open Interest der Managed-Money-Long-Positionen
                        - **$\mathrm{OI}_{\mathrm{MMS}}(t)$:** Open Interest der Managed-Money-Short-Positionen
                        - **$\mathrm{OI}(t)$:** gesamtes Open Interest des betrachteten Futures-Marktes
                        - **Negatives Vorzeichen bei MMS:** dient der separaten Darstellung der Short-Seite im Plot
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
                html.H1("DP Price Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Price Indicator** zeigt, wie sich das Long- bzw. Short-Open Interest
                        einer bestimmten Tradergruppe in Abhängigkeit von der Anzahl Trader und dem zugrunde
                        liegenden Preisniveau verteilt. Dadurch wird sichtbar, bei welchen Preisniveaus eine
                        Gruppe besonders stark oder schwach positioniert ist und wie sich diese Positionierung
                        im Verhältnis zur Zahl der beteiligten Trader verändert.

                        Das **Ziel des Indikators** ist es, die Positionierung einer Tradergruppe im Zusammenhang
                        mit dem Marktpreis sichtbar zu machen. Er hilft zu beurteilen, ob hohe oder tiefe Long-
                        bzw. Short-Positionierungen eher bei bestimmten Preisniveaus auftreten und ob diese von
                        vielen oder wenigen Tradern getragen werden. Dadurch lassen sich typische Preisbereiche
                        identifizieren, in denen eine Gruppe besonders aktiv ist.

                        **Farbskala:** Die Punktfarbe zeigt das jeweilige Preisniveau des Continuous Front-Month Futures
                        (2nd Nearby). Helle Farben stehen für tiefere Preise, dunklere Farben für höhere Preise.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                **Für die Long-Seite und die Short-Seite gilt:**

                $$
                c(t)=\mathit{Price}_{\mathrm{Front\ Month}}(t)
                $$

                **Variablen und Begriffe:**
                - *PMPUL:** Producer/Merchant/Processor/User Long
                - **PMPUS:** Producer/Merchant/Processor/User Short
                - **$\mathrm{OI}_G(t)$:** Open Interest der betrachteten Gruppe $G$ zum Zeitpunkt $t$
                - **$N_G(t)$:** Anzahl Trader der betrachteten Gruppe $G$ zum Zeitpunkt $t$
                - **Punktfarbe:** $c(t)$, d. h. das Preisniveau des Front-Month Futures zum Zeitpunkt $t$
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

        # DP Factor (VIX) Indicator
        dbc.Row([
            dbc.Col([
                html.H1("DP Factor (VIX) Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Factor (VIX) Indicator** zeigt, wie sich das Long- bzw.
                        Short-Open-Interest einer bestimmten Tradergruppe in Abhängigkeit von der Anzahl
                        Trader und einem externen Risikofaktor verteilt. Als externer Faktor wird der
                        **Volatility Index (VIX)** verwendet, der die vom Markt erwartete Schwankungsintensität
                        des S&P 500 für die nächsten 30 Tage abbildet. Dadurch wird sichtbar, ob eine Tradergruppe
                        ihre Positionen eher in Phasen tiefer oder hoher erwarteter Marktvolatilität aufbaut.

                        Das **Ziel des Indikators** ist es, die Positionierung einer Tradergruppe im Zusammenhang
                        mit dem allgemeinen Marktunsicherheitsniveau sichtbar zu machen. Er hilft zu beurteilen,
                        ob hohe oder tiefe Long- bzw. Short-Positionierungen eher in Phasen erhöhter oder reduzierter
                        Risikoaversion auftreten und ob diese von vielen oder wenigen Tradern getragen werden. Dadurch
                        lassen sich mögliche Zusammenhänge zwischen externer Marktunsicherheit und der Positionierung
                        im jeweiligen Rohstoffmarkt erkennen.

                        **Farbskala:** Die Punktfarbe zeigt das jeweilige Niveau des VIX. Helle Farben stehen für
                        eine tiefere erwartete Volatilität, dunkelrote Farben für eine höhere erwartete Volatilität.
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
                html.H1("DP Factor (DXY) Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Factor (DXY) Indicator** zeigt, wie sich das Long- bzw.
                        Short-Open-Interest einer bestimmten Tradergruppe in Abhängigkeit von der Anzahl
                        Trader und einem externen Währungsfaktor verteilt. Als externer Faktor wird der
                        **US-Dollar-Index (DXY)** verwendet, der die Stärke des US-Dollars gegenüber einem
                        Korb wichtiger Währungen abbildet. Dadurch wird sichtbar, ob eine Tradergruppe ihre
                        Positionen eher in Phasen eines schwächeren oder stärkeren US-Dollars aufbaut.

                        Das **Ziel des Indikators** ist es, die Positionierung einer Tradergruppe im Zusammenhang
                        mit der allgemeinen Dollarstärke sichtbar zu machen. Er hilft zu beurteilen, ob hohe oder
                        tiefe Long- bzw. Short-Positionierungen eher in Phasen eines starken oder schwachen
                        US-Dollars auftreten und ob diese von vielen oder wenigen Tradern getragen werden. Dadurch
                        lassen sich mögliche Zusammenhänge zwischen Wechselkursumfeld und Positionierung im
                        jeweiligen Rohstoffmarkt erkennen.

                        **Farbskala:** Die Punktfarbe zeigt das jeweilige Niveau des DXY. Helle Farben stehen für
                        einen tieferen Dollarindex, dunkelrote Farben für einen höheren Dollarindex bzw. einen
                        stärkeren US-Dollar.
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
                html.H1("DP Currency Indicator (USD/CHF)"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Currency Indicator** zeigt, wie sich das Long- bzw.
                        Short-Open-Interest einer bestimmten Tradergruppe in Abhängigkeit von der Anzahl
                        Trader und einem relevanten Wechselkurs verteilt. Als Währungsfaktor wird der
                        **USD/CHF-Wechselkurs** verwendet. Dadurch wird sichtbar, ob eine Tradergruppe
                        ihre Positionen eher in Phasen eines schwächeren oder stärkeren US-Dollars
                        gegenüber dem Schweizer Franken aufbaut.

                        Das **Ziel des Indikators** ist es, die Positionierung einer Tradergruppe im
                        Zusammenhang mit dem Wechselkursumfeld sichtbar zu machen. Er hilft zu beurteilen,
                        ob hohe oder tiefe Long- bzw. Short-Positionierungen eher bei bestimmten USD/CHF-Niveaus
                        auftreten und ob diese von vielen oder wenigen Tradern getragen werden. Der Wechselkurs
                        USD/CHF wird verwendet, da das Dashboard primär in der Schweiz eingesetzt wird und die
                        betrachteten Rohstoffmärkte überwiegend in US-Dollar notieren. Dadurch wird die
                        Positionierung aus einer für Schweizer Nutzer:innen besonders relevanten
                        Währungsperspektive interpretiert.

                        **Farbskala:** Die Punktfarbe zeigt das jeweilige Niveau des USD/CHF-Wechselkurses.
                        Helle Farben stehen für ein tieferes USD/CHF-Niveau, dunklere Farben für ein höheres
                        USD/CHF-Niveau.
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
                html.H1("DP Fundamental Indicator (Crude Oil Inventory)"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Fundamental Indicator** zeigt, wie sich das Long- bzw.
                        Short-Open-Interest der Gruppe **Producer/Merchant/Processor/User (PMPU)**
                        in Abhängigkeit von der Anzahl Trader und dem fundamentalen Rohöl-Lagerbestand
                        verteilt. Als externer Faktor werden die wöchentlichen **US-Rohöl-Lagerbestände
                        (Ending Stocks excl. SPR)** der U.S. Energy Information Administration (EIA)
                        verwendet.

                        Die PMPU-Gruppe umfasst physische Marktteilnehmer – Produzenten, Händler,
                        Verarbeiter und Endverbraucher. Ihre Positionierung spiegelt daher direkt das
                        operative Hedging-Verhalten gegenüber dem physischen Rohölmarkt wider.
                        Ein Zusammenspiel zwischen der PMPU-Positionierung und dem Lagerbestandsniveau
                        lässt Rückschlüsse auf Angebotserwartungen, Hedging-Druck und mögliche
                        Trendwenden im physischen Markt zu.

                        **Dieser Indikator ist ausschliesslich für Crude Oil (WTI) verfügbar.**

                        **Farbskala:** Die Punktfarbe zeigt das jeweilige Niveau des US-Rohöl-Lagerbestands
                        in Tausend Barrel. Helle Farben stehen für tiefere Lagerbestände
                        (knappes Angebot), dunklere Farben für höhere Lagerbestände (reichliches Angebot).
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
                html.H1("DP Relative Concentration Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Relative Concentration Indicator** normalisiert Positionen
                        anhand des Open Interest und stellt die Konzentration der Gruppen dar. Dadurch lassen sich verschiedene Märkte
                        oder Gruppen innerhalb eines Marktes direkt vergleichen.

                        Das **Ziel des Indikators** ist es, die Positionierungsprofile von Märkten vollständig zu visualisieren und Unterschiede
                        sichtbar zu machen – etwa zwischen verwandten Rohstoffen wie Gold und Silber oder zwischen Platin und Palladium.
                        Dadurch können Rückschlüsse auf zukünftige Marktbewegungen, Hedging-Verhalten und potenzielle Spreadausweitungen
                        gezogen werden.
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
                html.H1("DP Seasonal Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Seasonal Indicator** ist ein spezieller DP-Indikator, der saisonale Muster im Traderverhalten
                        sichtbar macht. Dabei werden Positionen nicht nur nach Grösse und Anzahl der Trader, sondern zusätzlich
                        nach Zeitabschnitten (z. B. Monate oder Quartale) dargestellt.

                        Das **Ziel des Indikators** ist es, saisonale Hedging-Muster oder Abweichungen davon zu erkennen.
                        So lassen sich etwa typische Verhaltensweisen von Produzenten oder Konsumenten in bestimmten Jahreszeiten
                        aufzeigen (z. B. stärkere Hedging-Aktivität im Winter bei Heizöl). Gleichzeitig hilft er, potenzielle
                        Anomalien oder Unterabsicherungen zu identifizieren, die ein Risiko für Preisbewegungen darstellen könnten.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        $$
                        x_q(t) = N_q(t), \qquad y_q(t) = RC_q(t)
                        $$

                        wobei

                        - $N_q(t)$: Anzahl der Trader im Quartal $q$ zum Zeitpunkt $t$
                        - $RC_q(t)$: *Relative Concentration* der Tradergruppe im Quartal $q$
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
                html.H1("DP Net Indicator with Median"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Net Indicator** kombiniert Informationen zu Netto-Open-Interest und Netto-Anzahl von Tradern.
                        Dadurch lassen sich Abweichungen zwischen Positionsgrösse und Traderanzahl sichtbar machen, die Hinweise
                        auf mögliche Wendepunkte im Markt geben können.

                        Das **Ziel des Indikators** ist es, ein klareres Bild der Netto-Positionierung zu liefern und Extremwerte
                        besser einzuordnen. So können Situationen erkannt werden, in denen z. B. das Open Interest eine Long-Position
                        zeigt, die Mehrheit der Trader aber Short positioniert ist. Zudem lassen sich auch Spread-Positionen analysieren,
                        um einzuschätzen, ob diese sich in extremeren Marktphasen (z. B. Contango oder Backwardation) verstärken könnten.
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
                html.H1("DP Position Size Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Position Size Indicator** verknüpft die durchschnittliche Positionsgrösse von Tradern
                        mit der Preisentwicklung eines Rohstoffs. Dabei wird die Positionsgrösse (y-Achse) gegen die Anzahl der Trader
                        (x-Achse) dargestellt, wobei die Farben die jeweilige Preisrange markieren.

                        Das **Ziel des Indikators** ist es, Zusammenhänge zwischen Positionsgrössen und Marktpreisen sichtbar zu machen.
                        So lassen sich Muster erkennen, etwa dass Long-Trader bei tieferen Preisen grössere Positionen halten
                        (stärkeres Engagement), während bei höheren Preisen die Traderzahl sinkt. Auf der Short-Seite hingegen treten
                        oft uneinheitlichere Muster auf, was auf unterschiedliche Handelsstrategien wie Spread- oder
                        Relative-Value-Trading hinweist.

                        Insgesamt hilft der Indikator, Unterschiede im Verhalten von Long- und Short-Tradern zu analysieren
                        und Rückschlüsse auf ihre Handelsmotive (z. B. direktional vs. relative Value) zu ziehen.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Achsen (Zeitpunkt $t$):
                        $$
                        x_G(t)=N_G(t), \qquad y_G(t)=\mathrm{PS}_G(t)
                        $$

                        Farbcodierung (Zeitpunkt $t$):
                        $$
                        \text{color}_G(t)\;\propto\;\mathrm{OI}_G(t)
                        $$

                        **Variablen und Begriffe:**
                        - $N_G(t)$: Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - $\mathrm{PS}_G(t)$: durchschnittliche Positionsgrösse je Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - $\mathrm{OI}_G(t)$: Open Interest der Gruppe $G$ zum Zeitpunkt $t$
                        - Die **Punktfarbe** zeigt, wie hoch das Open Interest in der jeweiligen Woche war
                          (je heller/gelber, desto höher das Open Interest)
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
                html.H1("DP Hedging Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Hedging Indicator** erweitert die klassische DP-Analyse, indem er mehrere Tradergruppen
                        gleichzeitig betrachtet – typischerweise Money Manager (MM) und Producer/Merchant/Processor/User (PMPU).
                        So wird sichtbar, wie viel „Dry Powder" (Spielraum für zusätzliche Positionen) eine Gruppe im Verhältnis
                        zu einer anderen noch hat.

                        Das **Ziel des Indikators** ist es, ein vollständigeres Bild der Marktpositionierung zu geben und besser
                        einzuschätzen, ob Preise noch weiter steigen oder fallen können. Besonders die PMPU-Gruppe
                        (Producer/Merchant/Processor/User) liefert wertvolle Hinweise, da deren Hedging-Verhalten oft eine starke
                        Verbindung zur physischen Marktlage hat.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Achsen (Zeitpunkt $t$):
                        $$
                        x_G(t) = N_G(t), \qquad y_G(t) = \mathrm{OI}_G(t)
                        $$

                        mit $G \in \{\mathrm{MML},\, \mathrm{MMS}\}$

                        Farbcodierung – Hedging-Kraft der PMPU (Zeitpunkt $t$):
                        $$
                        \text{Color}_G(t)
                        \;=\;
                        \frac{\mathrm{OI}_{\mathrm{PMPU}}(t) - \min\!\big(\mathrm{OI}_{\mathrm{PMPU}}\big)}
                             {\max\!\big(\mathrm{OI}_{\mathrm{PMPU}}\big) - \min\!\big(\mathrm{OI}_{\mathrm{PMPU}}\big)}
                        $$

                        **Variablen und Begriffe:**
                        - $N_G(t)$: Anzahl Trader der Gruppe $G$ zum Zeitpunkt $t$
                        - $\mathrm{OI}_G(t)$: Open Interest der Gruppe $G$ (MM Long oder Short) zum Zeitpunkt $t$
                        - $\mathrm{OI}_{\mathrm{PMPU}}(t)$: Open Interest der PMPU-Gruppe zum Zeitpunkt $t$
                        - **PMPU(L/S):** Producer/Merchant/Processor/User, je nach Auswahl Long (PMPUL) oder Short (PMPUS)
                        - **Bubble-Grösse:** proportional zum gesamten Open Interest (Marktliquidität bzw. Marktgewicht)
                        - **Punktfarbe:** normiertes OI der PMPU-Gruppe; zeigt die aktuelle Position relativ zu historischem Minimum und Maximum
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
                html.H1("DP Concentration / Clustering Indicator"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **DP Concentration / Clustering Indicator** kombiniert die Konzepte von Konzentration
                        (Open Interest-Anteil) und Clustering (Anzahl Trader) in einem DP-Chart. Er zeigt, wie extrem die
                        Positionierung einer Tradergruppe im Vergleich zu ihrer historischen Spanne ist.

                        Das **Ziel des Indikators** ist es, relative Handelschancen zwischen ähnlichen Märkten oder Rohstoffen
                        aufzuzeigen, indem Positionierungsunterschiede sichtbar gemacht werden. Befinden sich z. B. beide
                        Kennzahlen in einem Extrembereich, steigt die Wahrscheinlichkeit, dass ein Markt im Falle eines
                        Preisschocks stärker reagiert als ein anderer.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **1) Clustering je Zeitpunkt $t$**

                        Rohanteil der Gruppe $G$ an allen Futures-Tradern:
                        $$
                        \mathrm{ClustShare}^{\mathrm{raw}}_G(m,t)=\frac{T_G(m,t)}{TT_F(m,t)}
                        $$

                        Rolling-Normierung (1-Jahresfenster $\mathcal{W}_{365}$):
                        $$
                        \mathrm{ClustShare}^{\mathrm{roll}}_G(m,t)=
                        \frac{\mathrm{ClustShare}^{\mathrm{raw}}_G(m,t)-\min_{\tau\in\mathcal{W}_{365}}\mathrm{ClustShare}^{\mathrm{raw}}_G(m,\tau)}
                        {\max_{\tau\in\mathcal{W}_{365}}\mathrm{ClustShare}^{\mathrm{raw}}_G(m,\tau)-\min_{\tau\in\mathcal{W}_{365}}\mathrm{ClustShare}^{\mathrm{raw}}_G(m,\tau)}\cdot100
                        $$

                        **2) Concentration je Zeitpunkt $t$**

                        $$
                        \mathrm{RelConc}^{\mathrm{raw}}_G(m,t)=\mathrm{OI}^{L}_G(m,t)-\mathrm{OI}^{S}_G(m,t)
                        $$

                        **3) Range-Normalisierung über alle Märkte (0–100)**

                        $$
                        x_m=\mathrm{ClusteringRange}_G(m),\qquad
                        y_m=\mathrm{ConcentrationRange}_G(m)
                        $$

                        **Interpretation:**
                        - **Clustering hoch ($x$ nahe 100)**: Im Vergleich zu Historie & anderen Märkten stark von Gruppe $G$ „gecrowded"
                        - **Concentration hoch ($y$ nahe 100)**: Markt zeigt einen hohen Netto-Kontrakt-Überhang zugunsten der Gruppe $G$
                        - **Oben rechts** (hoch/hoch): doppelt extrem → Markt tendiert bei Schocks zu stärkeren Moves
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
