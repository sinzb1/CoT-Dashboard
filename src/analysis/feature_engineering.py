"""
CoT-DataFrame Anreicherung: Berechnet alle abgeleiteten Spalten aus den Rohdaten.

enrich_cot_dataframe() erwartet einen DataFrame der bereits umbenannte Spalten hat
('time' → 'Date', 'market_names' → 'Market Names') und fügt folgende Spalten hinzu:

Trader-Anteile & Clustering:
  MM_Long_share, MM_Short_share
  Long Clustering, Short Clustering           – MM: Trader-Anteil in % (MM Long/Short / Total)
  PMPU Long/Short Clustering                  – PMPU: Trader-Anteil in %
  SD Long/Short Clustering                    – Swap Dealer: Trader-Anteil in %
  OR Long/Short Clustering                    – Other Reportables: Trader-Anteil in %

Concentration (OI-Anteil je Gruppe):
  PMPU Long/Short Concentration               – PMPU OI / Total OI in %
  SD Long/Short Concentration                 – Swap Dealer OI / Total OI in %
  MM Long/Short Concentration                 – Managed Money OI / Total OI in %
  OR Long/Short Concentration                 – Other Reportables OI / Total OI in %

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

# ---------------------------------------------------------------------------
# Rohe Spaltennamen (aus InfluxDB-Pivot)
# ---------------------------------------------------------------------------
_C_TOTAL_TRADERS   = "Total Traders"
_C_PMPU_L          = "Producer/Merchant/Processor/User Long"
_C_PMPU_S          = "Producer/Merchant/Processor/User Short"
_C_MM_L            = "Managed Money Long"
_C_MM_S            = "Managed Money Short"
_C_SD_L            = "Swap Dealer Long"
_C_SD_S            = "Swap Dealer Short"
_C_OR_L            = "Other Reportables Long"
_C_OR_S            = "Other Reportables Short"
_C_TR_PMPU_L       = "Traders Prod/Merc Long"
_C_TR_PMPU_S       = "Traders Prod/Merc Short"
_C_TR_MM_L         = "Traders M Money Long"
_C_TR_MM_S         = "Traders M Money Short"
_C_TR_SD_L         = "Traders Swap Long"
_C_TR_SD_S         = "Traders Swap Short"
_C_TR_OR_L         = "Traders Other Rept Long"
_C_TR_OR_S         = "Traders Other Rept Short"
_C_TR_MM_SPREAD    = "Traders M Money Spread"
_C_TR_SD_SPREAD    = "Traders Swap Spread"
_C_TR_OR_SPREAD    = "Traders Other Rept Spread"
_C_TOTAL_NUM       = "Total Number of Traders"


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
    df[_C_TOTAL_NUM] = df[_C_TOTAL_TRADERS]

    df["MM_Long_share"]  = df[_C_TR_MM_L] / df[_C_TOTAL_NUM]
    df["MM_Short_share"] = df[_C_TR_MM_S] / df[_C_TOTAL_NUM]

    df["Long Clustering"]  = df["MM_Long_share"]  * 100.0
    df["Short Clustering"] = df["MM_Short_share"] * 100.0

    total_traders = df[_C_TOTAL_NUM].replace(0, np.nan)
    df["PMPU Long Clustering"]  = df[_C_TR_PMPU_L] / total_traders * 100.0
    df["PMPU Short Clustering"] = df[_C_TR_PMPU_S] / total_traders * 100.0
    df["SD Long Clustering"]    = df[_C_TR_SD_L]   / total_traders * 100.0
    df["SD Short Clustering"]   = df[_C_TR_SD_S]   / total_traders * 100.0
    df["OR Long Clustering"]    = df[_C_TR_OR_L]   / total_traders * 100.0
    df["OR Short Clustering"]   = df[_C_TR_OR_S]   / total_traders * 100.0

    # ------------------------------------------------------------------
    # Concentration (OI-Anteil je Gruppe am Total OI)
    # ------------------------------------------------------------------
    total_oi = pd.to_numeric(df["Open Interest"], errors="coerce").replace(0, np.nan)
    df["PMPU Long Concentration"]  = df[_C_PMPU_L] / total_oi * 100.0
    df["PMPU Short Concentration"] = df[_C_PMPU_S] / total_oi * 100.0
    df["SD Long Concentration"]    = df[_C_SD_L]   / total_oi * 100.0
    df["SD Short Concentration"]   = df[_C_SD_S]   / total_oi * 100.0
    df["MM Long Concentration"]    = df[_C_MM_L]   / total_oi * 100.0
    df["MM Short Concentration"]   = df[_C_MM_S]   / total_oi * 100.0
    df["OR Long Concentration"]    = df[_C_OR_L]   / total_oi * 100.0
    df["OR Short Concentration"]   = df[_C_OR_S]   / total_oi * 100.0

    # ------------------------------------------------------------------
    # Rolling Min/Max auf PMPU Long (für Grundlegende-Darstellung)
    # ------------------------------------------------------------------
    df["Rolling Min"] = df[_C_PMPU_L].rolling(365, min_periods=1).min()
    df["Rolling Max"] = df[_C_PMPU_L].rolling(365, min_periods=1).max()

    # ------------------------------------------------------------------
    # Trader-Kategorien
    # ------------------------------------------------------------------
    df["Trader Size"] = pd.cut(
        df[_C_TOTAL_NUM],
        bins=[0, 50, 100, 150],
        labels=["≤ 50 Traders", "51–100 Traders", "101–150 Traders"],
    )

    # ------------------------------------------------------------------
    # Aggregierte Trader-Zähler
    # ------------------------------------------------------------------
    df["Total Long Traders"]  = df[[_C_TR_PMPU_S, _C_TR_SD_L, _C_TR_MM_L]].sum(axis=1)
    df["Total Short Traders"] = df[[_C_TR_PMPU_S, _C_TR_SD_S, _C_TR_MM_S]].sum(axis=1)

    # ------------------------------------------------------------------
    # Positions-Grössen (Kontrakte pro Trader)
    # ------------------------------------------------------------------
    def _div(a: str, b: str) -> pd.Series:
        return (df[a] / df[b]).replace([np.inf, -np.inf], np.nan)

    df["Long Position Size"]      = _div(_C_PMPU_L, _C_TR_PMPU_L)
    df["Short Position Size"]     = _div(_C_PMPU_S, _C_TR_PMPU_S)
    df["MML Position Size"]       = _div(_C_MM_L,   _C_TR_MM_L)
    df["MMS Position Size"]       = _div(_C_MM_S,   _C_TR_MM_S)
    df["Net Short Position Size"] = df["Short Position Size"] - df["Long Position Size"]
    df["PMPUL Position Size"]     = _div(_C_PMPU_L, _C_TR_PMPU_L)
    df["PMPUS Position Size"]     = _div(_C_PMPU_S, _C_TR_PMPU_S)
    df["SDL Position Size"]       = _div(_C_SD_L,   _C_TR_SD_L)
    df["SDS Position Size"]       = _div(_C_SD_S,   _C_TR_SD_S)
    df["ORL Position Size"]       = _div(_C_OR_L,   _C_TR_OR_L)
    df["ORS Position Size"]       = _div(_C_OR_S,   _C_TR_OR_S)

    # ------------------------------------------------------------------
    # OI-Aliase
    # ------------------------------------------------------------------
    df["MML Long OI"]  =  df[_C_MM_L]
    df["MML Short OI"] = -df[_C_MM_S]
    df["MMS Long OI"]  =  df[_C_MM_L]
    df["MMS Short OI"] = -df[_C_MM_S]
    df["MML Traders"]  =  df[_C_TR_MM_L]
    df["MMS Traders"]  =  df[_C_TR_MM_S]

    # ------------------------------------------------------------------
    # Relative Concentrations (Netto-Konzentration in %, normiert durch Total OI)
    # Formel: 100 × (Long-OI − Short-OI) / Total-OI
    # ------------------------------------------------------------------
    df["PMPUL Relative Concentration"] = 100.0 * (df[_C_PMPU_L] - df[_C_PMPU_S]) / total_oi
    df["PMPUS Relative Concentration"] = 100.0 * (df[_C_PMPU_S] - df[_C_PMPU_L]) / total_oi
    df["SDL Relative Concentration"]   = 100.0 * (df[_C_SD_L]   - df[_C_SD_S])   / total_oi
    df["SDS Relative Concentration"]   = 100.0 * (df[_C_SD_S]   - df[_C_SD_L])   / total_oi
    df["MML Relative Concentration"]   = 100.0 * (df[_C_MM_L]   - df[_C_MM_S])   / total_oi
    df["MMS Relative Concentration"]   = 100.0 * (df[_C_MM_S]   - df[_C_MM_L])   / total_oi
    df["ORL Relative Concentration"]   = 100.0 * (df[_C_OR_L]   - df[_C_OR_S])   / total_oi
    df["ORS Relative Concentration"]   = 100.0 * (df[_C_OR_S]   - df[_C_OR_L])   / total_oi

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
    df["PMPUL Traders"] = df[_C_TR_PMPU_L]
    df["PMPUS Traders"] = df[_C_TR_PMPU_S]
    df["SDL Traders"]   = df[_C_TR_SD_L]
    df["SDS Traders"]   = df[_C_TR_SD_S]
    df["ORL Traders"]   = df[_C_TR_OR_L]
    df["ORS Traders"]   = df[_C_TR_OR_S]

    # ------------------------------------------------------------------
    # Temporale Features
    # ------------------------------------------------------------------
    df["Quarter"] = df["Date"].dt.quarter.map({1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"})
    df["Year"]    = df["Date"].dt.year

    # ------------------------------------------------------------------
    # Aggregierte OI/Trader-Grössen für Managed Money
    # ------------------------------------------------------------------
    df["MM Net OI"]      = df[_C_MM_L]    - df[_C_MM_S]
    df["MM Net Traders"] = df[_C_TR_MM_L] - df[_C_TR_MM_S]

    return df
