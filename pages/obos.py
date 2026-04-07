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
                        Der **OBOS Concentration Indicator** (Overbought/Oversold) zeigt, ob einzelne Märkte
                        auf Basis der Managed-Money-Konzentration und der Preisposition im rollierenden
                        Einjahresbereich überkauft oder überverkauft sind.

                        Jeder Datenpunkt repräsentiert einen **Markt** (dargestellt durch sein Ticker-Kürzel).
                        Der Indikator vereint alle verfügbaren Märkte in einer gemeinsamen Übersicht, sodass
                        Extrempositionen marktübergreifend auf einen Blick erkennbar sind.

                        **Linke Hälfte – MM Short Concentration:** Wie hoch ist der Anteil der Managed-Money-Short-Position
                        am gesamten Open Interest? Ein hoher Wert (links aussen) bedeutet historisch hohe Short-Konzentration.

                        **Rechte Hälfte – MM Long Concentration:** Entsprechend für die Long-Seite. Ein hoher Wert
                        (rechts aussen) bedeutet historisch hohe Long-Konzentration.

                        **Y-Achse – Preis (2nd Nearby):** Wie hoch ist der aktuelle Preis im Vergleich zum rollierenden
                        Einjahreshöchst- und -tiefstkurs? 100 = Jahreshoch, 0 = Jahrestief.

                        **Farbkodierung:**
                        - **Blau** = Contango (2nd Nearby < 3rd Nearby, Terminmarkt steigt mit Laufzeit)
                        - **Grün** = Backwardation (2nd Nearby > 3rd Nearby, Terminmarkt fällt mit Laufzeit)
                        - **Grau** = Kurvenstruktur nicht ermittelbar (kein 3rd-Nearby-Preis verfügbar)

                        **Graue Eckzonen** markieren Bereiche extremer Overbought/Oversold-Konstellationen
                        (Preis- und Konzentrations-Range > 75 % bzw. < 25 %).
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Alle drei Achswerte werden als **rollierender Einjahresbereich (52 Wochen)** normiert:

                        $$
                        \mathrm{Range}(t) =
                        \frac{x(t) - \min_{52W}(x)}{\max_{52W}(x) - \min_{52W}(x)} \times 100
                        $$

                        **Variablen und Begriffe:**
                        - **$x(t)$:** aktueller Wert (Preis 2nd Nearby, MML- oder MMS-Konzentration) zum Reportdatum $t$
                        - **$\min_{52W}(x)$, $\max_{52W}(x)$:** rollierendes Minimum bzw. Maximum über 52 Wochen
                        - **$\mathrm{MML\ Concentration}(t) = \frac{\text{Managed Money Long}(t)}{\text{Open Interest}(t)} \times 100$**
                        - **$\mathrm{MMS\ Concentration}(t) = \frac{\text{Managed Money Short}(t)}{\text{Open Interest}(t)} \times 100$**
                        - **Contango/Backwardation:** Vorzeichen von $P_{\mathrm{2nd}}(t) - P_{\mathrm{3rd}}(t)$
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                dcc.Graph(id='obos-concentration-graph'),
                html.Br(),

            ], width=12)
        ]),
    ])
