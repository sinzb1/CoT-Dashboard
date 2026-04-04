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

                        Das **Prognose-Modell** wird für jeden Rohstoff separat auf dem **vollständigen verfügbaren
                        Datensatz** trainiert. Die Prognose bezieht sich auf die aktuellste vorliegende CoT-Beobachtung.

                        Zur **Modellvalidierung** wird zusätzlich ein zeitbasierter **70/30-Split** durchgeführt:
                        Die ersten 70 % der Daten dienen als Trainingsset, die letzten 30 % als Out-of-Sample-Testset.
                        Konfusionsmatrix, ROC- und Precision-Recall-Kurve werden ausschliesslich auf diesem Testset berechnet.
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

                        **Train/Test-Split:** Die ersten 70 % der Beobachtungen (chronologisch) bilden das
                        Trainingsset; die letzten 30 % das Out-of-Sample-Testset für die Evaluationsmetriken.
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-4"),

                # ----------------------------------------------------------
                # Prognose-Alert
                # ----------------------------------------------------------
                html.Div(id='dt-prediction-text', className='mb-4'),

                # ----------------------------------------------------------
                # Entscheidungsbaum-Visualisierung
                # ----------------------------------------------------------
                html.H2("Entscheidungsbaum", className="mt-2 mb-2"),
                html.Img(
                    id='dt-tree-image',
                    style={'width': '100%', 'maxWidth': '1600px', 'display': 'block'},
                ),

                # ----------------------------------------------------------
                # Out-of-Sample-Evaluation (70/30 Split)
                # ----------------------------------------------------------
                html.H2("Modellvalidierung – Out-of-Sample-Evaluation (70/30 Zeitbasierter Split)",
                        className="mt-5 mb-2"),

                # Info-Badges: Trainings- und Testset-Grösse
                html.Div(id='dt-eval-info', className='mb-4'),

                # Drei Evaluationsdiagramme nebeneinander
                dbc.Row([

                    # ---- Konfusionsmatrix ----
                    dbc.Col([
                        html.H4("Konfusionsmatrix", className="mb-2"),
                        dbc.Accordion([
                            dbc.AccordionItem([
                                dcc.Markdown(r"""
                                Die **Konfusionsmatrix** zeigt, wie oft das Modell auf dem Out-of-Sample-Testset
                                eine korrekte oder falsche Vorhersage getroffen hat.

                                **Aufbau:**
                                - **Zeilen:** tatsächliche Klasse (gemessen, ex post)
                                - **Spalten:** vorhergesagte Klasse (Modell-Output)
                                - Die **Hauptdiagonale** (oben links / unten rechts) zeigt korrekte Vorhersagen.
                                - Die **Nebendiagonale** zeigt Fehlklassifikationen.

                                **Relevante Fälle im Kontext der Preisprognose:**
                                - **Unten rechts (True Positives):** Modell prognostiziert *steigt* – Preis ist tatsächlich gestiegen.
                                - **Oben links (True Negatives):** Modell prognostiziert *fällt* – Preis ist tatsächlich gefallen.
                                - **Unten links (False Negatives):** Modell prognostiziert *fällt* – Preis ist aber gestiegen (verpasste Aufwärtsbewegung).
                                - **Oben rechts (False Positives):** Modell prognostiziert *steigt* – Preis ist aber gefallen (Fehlsignal).
                                """, mathjax=True),
                            ], title="Beschreibung"),
                        ], start_collapsed=True, flush=True, className="mb-2"),
                        dcc.Graph(id='dt-confusion-matrix'),
                    ], width=12, lg=4, className="mb-4"),

                    # ---- ROC-Kurve ----
                    dbc.Col([
                        html.H4("ROC-Kurve", className="mb-2"),
                        dbc.Accordion([
                            dbc.AccordionItem([
                                dcc.Markdown(r"""
                                Die **ROC-Kurve** (Receiver Operating Characteristic) zeigt den Trade-off zwischen
                                der True Positive Rate (Sensitivität) und der False Positive Rate über alle
                                möglichen Klassifikationsschwellen.

                                **AUC (Area Under the Curve):**
                                - AUC = 1.0 → perfekte Trennung
                                - AUC = 0.5 → kein Informationsgehalt (Zufall)
                                - AUC < 0.5 → schlechter als Zufall

                                **Interpretation im Kontext der Preisprognose:**
                                Eine hohe AUC bedeutet, dass das Modell aufsteigende von fallenden
                                Preiswochen gut unterscheiden kann – unabhängig vom gewählten Schwellenwert.
                                Die gestrichelte Linie repräsentiert einen zufälligen Klassifikator (AUC = 0.5).
                                """, mathjax=True),
                            ], title="Beschreibung"),
                        ], start_collapsed=True, flush=True, className="mb-2"),
                        dcc.Graph(id='dt-roc-curve'),
                    ], width=12, lg=4, className="mb-4"),

                    # ---- Precision-Recall-Kurve ----
                    dbc.Col([
                        html.H4("Precision-Recall-Kurve", className="mb-2"),
                        dbc.Accordion([
                            dbc.AccordionItem([
                                dcc.Markdown(r"""
                                Die **Precision-Recall-Kurve** zeigt den Trade-off zwischen Precision
                                (Genauigkeit bei positiven Vorhersagen) und Recall (Vollständigkeit der
                                gefundenen positiven Fälle) über alle Klassifikationsschwellen.

                                **Interpretation im Kontext der Preisprognose:**
                                - **Precision:** Wie oft war eine Aufwärtsprognose auch tatsächlich richtig?
                                - **Recall:** Welcher Anteil der tatsächlichen Aufwärtswochen wurde erkannt?

                                Die **gestrichelte Basislinie** entspricht dem Anteil der Klasse *steigt*
                                im Testset – sie repräsentiert einen naiven Klassifikator, der immer *steigt*
                                vorhersagt. Ein Modell mit Mehrwert muss über dieser Linie liegen.

                                Die PR-Kurve ist besonders aussagekräftig bei **unbalancierten Datensätzen**
                                (z. B. wenn eine Preisrichtung deutlich häufiger auftritt als die andere).
                                """, mathjax=True),
                            ], title="Beschreibung"),
                        ], start_collapsed=True, flush=True, className="mb-2"),
                        dcc.Graph(id='dt-pr-curve'),
                    ], width=12, lg=4, className="mb-4"),

                ]),

                # ----------------------------------------------------------
                # Feature Importance
                # ----------------------------------------------------------
                html.H2("Feature Importance", className="mt-2 mb-2"),
                dbc.Accordion([
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Die **Feature Importance** zeigt, welche CoT-Kennzahlen das Modell als besonders
                        relevant für seine Entscheidungen eingestuft hat. Je grösser der Balken, desto
                        stärker hat dieses Feature zur Trennleistung des Entscheidungsbaums beigetragen.

                        **Interpretation im Kontext der Preisprognose:**
                        Ein Feature mit hoher Importance wurde an den entscheidenden Knoten des Baums
                        für Splits verwendet. Ein Wert von 0 bedeutet, dass das Feature in keinem Split
                        vorkam und damit keinen Beitrag zur Prognose leistet.

                        Die Importances sind **modell- und rohstoffspezifisch**: Für Gold können völlig
                        andere Features dominieren als für Palladium – je nachdem, welche CoT-Signale
                        historisch den stärksten Zusammenhang mit der Preisrichtung aufweisen.
                        """, mathjax=True),
                    ], title="Beschreibung"),
                    dbc.AccordionItem([
                        dcc.Markdown(r"""
                        Die Feature Importance basiert auf der **mittleren Gini-Reduktion**
                        (Mean Decrease in Impurity), die ein Feature über alle Splits im Baum bewirkt:

                        $$
                        \text{Importance}(f) =
                        \sum_{t \,\in\, \text{Splits mit } f}
                        \frac{n_t}{n} \cdot \Delta\text{Gini}(t)
                        $$

                        - $n_t$: Anzahl Beobachtungen im Knoten $t$
                        - $n$: Gesamtzahl Trainingsbeobachtungen
                        - $\Delta\text{Gini}(t)$: Reduktion des Gini-Koeffizienten durch den Split bei Knoten $t$

                        Die Importances werden so normiert, dass ihre Summe **1.0** ergibt:

                        $$\sum_{f} \text{Importance}(f) = 1.0$$

                        **Gini-Koeffizient** eines Knotens mit Klassenverteilung $(p_0, p_1)$:
                        $$
                        \text{Gini} = 1 - p_0^2 - p_1^2 = 2 \cdot p_0 \cdot p_1
                        $$
                        """, mathjax=True),
                    ], title="Berechnung"),
                ], start_collapsed=True, always_open=True, flush=True, className="mb-3"),
                dcc.Graph(id='dt-feature-importance'),
                html.Br(),

            ], width=12)
        ]),
    ])
