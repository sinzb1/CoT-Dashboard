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
                Für alle Märkte gilt eine Normierung der Konzentrationswerte und des Preises auf ein rollierendes 52-Wochen-Zeitfenster:

                $$
                x_{S} = \mathrm{Range}(C_{\mathrm{MM}_{S}}), \qquad
                x_{L} = \mathrm{Range}(C_{\mathrm{MM}_{L}}), \qquad
                y = \mathrm{Range}(P_{2})
                $$

                Die Normierung erfolgt jeweils mit der folgenden Range-Formel:

                $$
                \mathrm{Range}(v) = \frac{v - \min(v)}{\max(v) - \min(v)} \times 100
                $$

                und den Konzentrationswerten:

                $$
                C_{\mathrm{MM}_{L}} = \frac{\mathrm{MM}_{L}}{\mathrm{OI}_{N}} \times 100, \qquad
                C_{\mathrm{MM}_{S}} = \frac{\mathrm{MM}_{S}}{\mathrm{OI}_{N}} \times 100
                $$

                **Variablen und Begriffe:**
                - $x_{S}$: normierter Konzentrationswert der Short-Positionen
                - $x_{L}$: normierter Konzentrationswert der Long-Positionen
                - $y$: normierte Preisposition im 52-Wochen-Bereich
                - $v$: Rohwert (Preis oder Konzentration)
                - $\max(v)$: Maximum von $v$ über die letzten 52 Wochen
                - $\min(v)$: Minimum von $v$ über die letzten 52 Wochen
                - $C_{\mathrm{MM}_{L}}$: Konzentration der Long-Positionen der MM-Trader
                - $C_{\mathrm{MM}_{S}}$: Konzentration der Short-Positionen der MM-Trader
                - $\mathrm{MM}_{L}$: Long-Positionen der MM-Trader
                - $\mathrm{MM}_{S}$: Short-Positionen der MM-Trader
                - $\mathrm{OI}_{N}$: gesamtes Open Interest des Marktes
                - $P_{2}$: Schlusskurs des 2nd-Nearby-Futures (Databento)

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
