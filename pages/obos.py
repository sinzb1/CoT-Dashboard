from dash import dcc, html
import dash_bootstrap_components as dbc


def layout():
    return html.Div([

        # OBOS Concentration Indicator
        dbc.Row([
            dbc.Col([
                html.H1("OBOS Concentration Indicator", className="mt-3"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Indikator:** Zeigt für jeden Markt die normierte MM-Konzentration (X-Achse) gegen die normierte Preisposition im rollierenden Einjahresbereich (Y-Achse), eingefärbt nach der Terminstruktur. Jeder Punkt entspricht einem Markt.

                        **Interpretation:** Märkte rechts oben (hohe MML-Konzentration, hoher Preis) sind potenziell überkauft; Märkte links unten (hohe MMS-Konzentration, tiefer Preis) potenziell überverkauft. Graue Eckzonen markieren Extrembereiche (Range > 75 % bzw. < 25 %).

                        **Ziel:** Overbought/Oversold-Konstellationen marktübergreifend auf einen Blick erkennen — Extrempositionen in Konzentration und Preis gleichzeitig sichtbar machen.

                        **Besonderheit:** Die linke Hälfte zeigt MMS-Konzentration, die rechte Hälfte MML-Konzentration. Alle Werte sind rollierende 52-Wochen-Ranges. Schwarzer Punkt = aktuellste Woche.

                        **Farbskala:** Farbe = Terminstruktur. Blau = Contango ($P_{\mathrm{2nd}} < P_{\mathrm{3rd}}$), Grün = Backwardation ($P_{\mathrm{2nd}} > P_{\mathrm{3rd}}$), Grau = nicht ermittelbar.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dbc.Row([
                            dbc.Col(dcc.Markdown(r"""
                **Für alle Märkte gilt:**

                $$
                x = \mathrm{Range}_{52W}(\mathrm{Concentration}), \qquad y = \mathrm{Range}_{52W}(P_{\mathrm{2nd\ Nearby}})
                $$

                mit der Normierungsformel:

                $$
                \mathrm{Range}_{52W}(v,\, t) = \frac{v(t) - \min_{52W}(v)}{\max_{52W}(v) - \min_{52W}(v)} \times 100
                $$

                und den Konzentrationswerten:

                $$
                \mathrm{MML\ Conc.}(t) = \frac{\mathrm{MM\ Long}(t)}{\mathrm{OI}(t)} \times 100, \qquad
                \mathrm{MMS\ Conc.}(t) = \frac{\mathrm{MM\ Short}(t)}{\mathrm{OI}(t)} \times 100
                $$

                **Variablen und Begriffe:**
                - **$x$:** normierte Concentration (X-Achse); linke Hälfte = MMS-Concentration, rechte Hälfte = MML-Concentration
                - **$y$:** normierte Preisposition im 52-Wochen-Bereich (Y-Achse); 100 = Jahreshoch, 0 = Jahrestief
                - **$v(t)$:** Rohwert zum Reporting-Zeitpunkt $t$ (Preis oder Konzentration)
                - **$\min_{52W}(v)$, $\max_{52W}(v)$:** rollierendes Minimum bzw. Maximum über 52 Wochen
                - **$P_{\mathrm{2nd\ Nearby}}$:** Schlusskurs des 2nd-Nearby-Futures (Databento)
                - **$P_{\mathrm{3rd\ Nearby}}$:** Schlusskurs des 3rd-Nearby-Futures (Databento)
                - **$\mathrm{OI}(t)$:** gesamtes Open Interest des Marktes
                - **$c$:** Terminstruktur (Punktfarbe) — Contango: $P_{\mathrm{2nd}} < P_{\mathrm{3rd}}$, Backwardation: $P_{\mathrm{2nd}} > P_{\mathrm{3rd}}$

                *Alle Variablen beziehen sich auf denselben Reporting-Zeitpunkt.*
                """, mathjax=True), width=12),
                        ], className="mb-2"),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='obos-concentration-graph'),
                html.Br(),

            ], width=12)
        ]),
    ])
