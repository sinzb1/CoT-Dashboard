from dash import dcc, html
import dash_bootstrap_components as dbc


def layout():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H1("Preisprognose – Entscheidungsbaum", className="mt-3"),

                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Der **Entscheidungsbaum** (Decision Tree Classifier) prognostiziert auf Basis der aktuellen
                        CoT-Positionierungsdaten, ob der Futures-Preis eines Rohstoffs in der **nächsten Woche
                        steigen oder fallen** wird.

                        Als **Features** dienen ausschliesslich CoT-Kennzahlen aus der bestehenden Datenbank:
                        die Netto-Positionen der Händlergruppen (Managed Money, Producer/Merchant, Swap Dealer),
                        deren prozentuale Anteile am Gesamt-Open-Interest, Wochenveränderungen sowie der
                        rollende Z-Score der Managed-Money-Netto-Position.

                        Das Modell wird für jeden Rohstoff **separat** auf dem vollständigen verfügbaren Datensatz
                        trainiert. Die Prognose bezieht sich auf die aktuellste vorliegende CoT-Beobachtung.
                        """, mathjax=True),
                    ], title="Beschreibung"),

                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        **Features (X):**

                        | Feature | Formel |
                        |---------|--------|
                        | Netto MM | $\mathrm{MM}_L - \mathrm{MM}_S$ |
                        | Netto Prod/Merc | $\mathrm{PMPU}_L - \mathrm{PMPU}_S$ |
                        | Netto Swap | $\mathrm{SD}_L - \mathrm{SD}_S$ |
                        | % MM Long (OI) | $\frac{\mathrm{MM}_L}{\mathrm{OI}} \cdot 100$ |
                        | % MM Short (OI) | $\frac{\mathrm{MM}_S}{\mathrm{OI}} \cdot 100$ |
                        | Δ Netto MM | $\Delta(\mathrm{MM}_L - \mathrm{MM}_S)$ |
                        | Δ % MM Long | $\Delta\left(\frac{\mathrm{MM}_L}{\mathrm{OI}} \cdot 100\right)$ |
                        | Z-Score Netto MM | $\frac{\mathrm{net\_mm} - \mu_{13W}}{\sigma_{13W}}$ |

                        **Zielvariable (y):**
                        $$
                        y_t = \begin{cases} 1 & \text{wenn } P_{t+1} > P_t \\ 0 & \text{sonst} \end{cases}
                        $$

                        **Modellparameter:** max\_depth = 3, min\_samples\_leaf = 3, random\_state = 42
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                html.Div(id='dt-prediction-text', className='mb-4'),

                html.H2("Entscheidungsbaum", className="mt-2 mb-2"),
                html.Img(
                    id='dt-tree-image',
                    style={'width': '100%', 'maxWidth': '1600px', 'display': 'block'},
                ),

                html.H2("Feature Importance", className="mt-4 mb-2"),
                dcc.Graph(id='dt-feature-importance'),
                html.Br(),
            ], width=12)
        ]),
    ])
