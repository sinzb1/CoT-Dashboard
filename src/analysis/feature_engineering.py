"""
CoT-DataFrame Anreicherung: Berechnet alle abgeleiteten Spalten aus den Rohdaten.

enrich_cot_dataframe() erwartet einen DataFrame der bereits umbenannte Spalten hat
('time' → 'Date', 'market_names' → 'Market Names') und fügt folgende Spalten hinzu:

Trader-Anteile & Clustering:
  MM_Long_share, MM_Short_share
  Long Clustering, Short Clustering      – rollende 52-Wochen Min-Max-Normierung

Rolling-Fenster auf PMPU Long:
  Rolling Min, Rolling Max

Trader-Kategorien:
  Trader Size                            – Bins nach Gesamtanzahl Trader

Positions-Grössen (Kontrakte pro Trader):
  MML Position Size, MMS Position Size
  PMPUL/PMPUS/SDL/SDS/ORL/ORS Position Size

OI-Aliase (für Grundlegende-Seite):
  MML Long OI, MML Short OI, MMS Long OI, MMS Short OI
  MML Traders, MMS Traders

Relative Concentrations (Long − Short, netto):
  PMPUL/PMPUS/SDL/SDS/MML/MMS/ORL/ORS Relative Concentration

Netto-Aliase für Shapley-Owen:
  PMPU Net, SD Net, MM Net, OR Net

Trader-Gruppen-Aliase:
  PMPUL/PMPUS/SDL/SDS/MML/MMS/ORL/ORS Traders

Temporale Features:
  Quarter, Year

Aggregierte OI/Trader-Grössen für Managed Money:
  MM Net OI, MM Net Traders
  Total Long Traders, Total Short Traders
  Long Position Size, Short Position Size, Net Short Position Size
"""

import numpy as np
import pandas as pd

from src.analysis.cot_indicators import clustering_0_100


def enrich_cot_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Berechnet alle abgeleiteten Spalten aus dem CoT-Rohdatensatz.

    Parameters
    ----------
    df : Roher df_pivoted mit umbenannten Spalten ('Date', 'Market Names').

    Returns
    -------
    Angereicherter DataFrame (neue Spalten in-place hinzugefügt).
    """
    df = df.sort_values(["Market Names", "Date"])

    # ------------------------------------------------------------------
    # Trader-Anteile & Clustering
    # ------------------------------------------------------------------
    df["Total Number of Traders"] = df["Total Traders"]

    df["MM_Long_share"]  = df["Traders M Money Long"]  / df["Total Number of Traders"]
    df["MM_Short_share"] = df["Traders M Money Short"] / df["Total Number of Traders"]

    df["Long Clustering"] = (
        df.groupby("Market Names")["MM_Long_share"]
        .transform(lambda s: clustering_0_100(s, window=52))
    )
    df["Short Clustering"] = (
        df.groupby("Market Names")["MM_Short_share"]
        .transform(lambda s: clustering_0_100(s, window=52))
    )

    # ------------------------------------------------------------------
    # Rolling Min/Max auf PMPU Long (für Grundlegende-Darstellung)
    # ------------------------------------------------------------------
    df["Rolling Min"] = df["Producer/Merchant/Processor/User Long"].rolling(365, min_periods=1).min()
    df["Rolling Max"] = df["Producer/Merchant/Processor/User Long"].rolling(365, min_periods=1).max()

    # ------------------------------------------------------------------
    # Trader-Kategorien
    # ------------------------------------------------------------------
    df["Trader Size"] = pd.cut(
        df["Total Number of Traders"],
        bins=[0, 50, 100, 150],
        labels=["≤ 50 Traders", "51–100 Traders", "101–150 Traders"],
    )

    # ------------------------------------------------------------------
    # Aggregierte Trader-Zähler
    # ------------------------------------------------------------------
    df["Total Long Traders"]  = df[["Traders Prod/Merc Short", "Traders Swap Long", "Traders M Money Long"]].sum(axis=1)
    df["Total Short Traders"] = df[["Traders Prod/Merc Short", "Traders Swap Short", "Traders M Money Short"]].sum(axis=1)

    # ------------------------------------------------------------------
    # Positions-Grössen (Kontrakte pro Trader)
    # ------------------------------------------------------------------
    def _div(a: str, b: str) -> pd.Series:
        return (df[a] / df[b]).replace([np.inf, -np.inf], np.nan)

    df["Long Position Size"]       = df["Producer/Merchant/Processor/User Long"]
    df["Short Position Size"]      = df["Producer/Merchant/Processor/User Short"]
    df["MML Position Size"]        = _div("Managed Money Long",                          "Traders M Money Long")
    df["MMS Position Size"]        = _div("Managed Money Short",                         "Traders M Money Short")
    df["Net Short Position Size"]  = df["Short Position Size"] - df["Long Position Size"]
    df["PMPUL Position Size"]      = _div("Producer/Merchant/Processor/User Long",       "Traders Prod/Merc Long")
    df["PMPUS Position Size"]      = _div("Producer/Merchant/Processor/User Short",      "Traders Prod/Merc Short")
    df["SDL Position Size"]        = _div("Swap Dealer Long",                            "Traders Swap Long")
    df["SDS Position Size"]        = _div("Swap Dealer Short",                           "Traders Swap Short")
    df["ORL Position Size"]        = _div("Other Reportables Long",                      "Traders Other Rept Long")
    df["ORS Position Size"]        = _div("Other Reportables Short",                     "Traders Other Rept Short")

    # ------------------------------------------------------------------
    # OI-Aliase
    # ------------------------------------------------------------------
    df["MML Long OI"]  =  df["Managed Money Long"]
    df["MML Short OI"] = -df["Managed Money Short"]
    df["MMS Long OI"]  =  df["Managed Money Long"]
    df["MMS Short OI"] = -df["Managed Money Short"]
    df["MML Traders"]  =  df["Traders M Money Long"]
    df["MMS Traders"]  =  df["Traders M Money Short"]

    # ------------------------------------------------------------------
    # Relative Concentrations (Netto-Position: Long − Short)
    # ------------------------------------------------------------------
    df["PMPUL Relative Concentration"] = df["Producer/Merchant/Processor/User Long"]  - df["Producer/Merchant/Processor/User Short"]
    df["PMPUS Relative Concentration"] = df["Producer/Merchant/Processor/User Short"] - df["Producer/Merchant/Processor/User Long"]
    df["SDL Relative Concentration"]   = df["Swap Dealer Long"]                        - df["Swap Dealer Short"]
    df["SDS Relative Concentration"]   = df["Swap Dealer Short"]                       - df["Swap Dealer Long"]
    df["MML Relative Concentration"]   = df["Managed Money Long"]                      - df["Managed Money Short"]
    df["MMS Relative Concentration"]   = df["Managed Money Short"]                     - df["Managed Money Long"]
    df["ORL Relative Concentration"]   = df["Other Reportables Long"]                  - df["Other Reportables Short"]
    df["ORS Relative Concentration"]   = df["Other Reportables Short"]                 - df["Other Reportables Long"]

    # ------------------------------------------------------------------
    # Netto-Aliase für Shapley-Owen
    # ------------------------------------------------------------------
    df["PMPU Net"] = df["PMPUL Relative Concentration"]
    df["SD Net"]   = df["SDL Relative Concentration"]
    df["MM Net"]   = df["MML Relative Concentration"]
    df["OR Net"]   = df["ORL Relative Concentration"]

    # ------------------------------------------------------------------
    # Trader-Gruppen-Aliase
    # ------------------------------------------------------------------
    df["PMPUL Traders"] = df["Traders Prod/Merc Long"]
    df["PMPUS Traders"] = df["Traders Prod/Merc Short"]
    df["SDL Traders"]   = df["Traders Swap Long"]
    df["SDS Traders"]   = df["Traders Swap Short"]
    df["ORL Traders"]   = df["Traders Other Rept Long"]
    df["ORS Traders"]   = df["Traders Other Rept Short"]

    # ------------------------------------------------------------------
    # Temporale Features
    # ------------------------------------------------------------------
    df["Quarter"] = df["Date"].dt.quarter.map({1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"})
    df["Year"]    = df["Date"].dt.year

    # ------------------------------------------------------------------
    # Aggregierte OI/Trader-Grössen für Managed Money
    # ------------------------------------------------------------------
    df["MM Net OI"]      = df["Managed Money Long"]    - df["Managed Money Short"]
    df["MM Net Traders"] = df["Traders M Money Long"]  - df["Traders M Money Short"]

    return df
