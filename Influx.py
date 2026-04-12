import json
import os
import pandas as pd
from dotenv import load_dotenv
from influxdb_client_3 import InfluxDBClient3, Point
from datetime import date, datetime, timedelta, timezone

from src.services.trades_category_service import TradesCategoryService
from src.services.futures_price_service import FuturesPriceService
from src.services.macro_price_service import MacroPriceService
from src.services.eia_petroleum_service import EIAPetroleumService
from src.services.databento_continuous_service import DatabentoContinuousService

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
with open("config/config.json") as _f:
    _cfg = json.load(_f)

YEARS_BACK = _cfg.get("pipeline", {}).get("years_back", 10)

token = os.environ["INFLUXDB_TOKEN"]
database = os.environ.get("INFLUXDB_DATABASE", "CoT-Data")
host = os.environ.get("INFLUXDB_HOST", "http://localhost:8181")

client = InfluxDBClient3(host=host, token=token, database=database)

# ── Helper: letztes Datum einer Tabelle aus InfluxDB lesen ───────────────────
def get_last_date(measurement: str) -> date | None:
    """Gibt das neueste Datum in der Tabelle zurück, oder None wenn leer."""
    try:
        q = f"SELECT MAX(time) as last FROM \"{measurement}\""
        df = client.query(query=q, language="sql").to_pandas()
        val = df["last"].iloc[0]
        if pd.isna(val):
            return None
        return pd.Timestamp(val).date()
    except Exception:
        return None

# ── Startdatum pro Tabelle bestimmen ─────────────────────────────────────────
today = date.today()
full_start = date(today.year - YEARS_BACK, today.month, today.day)

# Überlappung von 14 Tagen damit Alignment-Logik immer genug Kontext hat
OVERLAP = timedelta(days=14)

last_cot       = get_last_date("cot_data")
last_futures   = get_last_date("futures_prices")
last_macro     = get_last_date("macro_by_date")
last_eia       = get_last_date("eia_petroleum_stocks")
last_deferred  = get_last_date("futures_deferred_prices")

cot_start      = (last_cot      - OVERLAP) if last_cot      else full_start
futures_start  = (last_futures  - OVERLAP) if last_futures  else full_start
macro_start    = (last_macro    - OVERLAP) if last_macro    else full_start
eia_start      = (last_eia      - OVERLAP) if last_eia      else full_start
deferred_start = (last_deferred - OVERLAP) if last_deferred else full_start

mode = "INKREMENTELL" if last_cot else "VOLLSTÄNDIG (erste Ausführung)"

print(f"\n{'='*60}")
print(f"Pipeline: {mode}")
print(f"CoT-Daten ab:      {cot_start}  (letzter DB-Eintrag: {last_cot or 'keiner'})")
print(f"Futures ab:        {futures_start}")
print(f"Macro ab:          {macro_start}")
print(f"EIA ab:            {eia_start}")
print(f"Databento ab:      {deferred_start}")
print(f"{'='*60}\n")

# ── 1. CoT Data ──────────────────────────────────────────────────────────────
service = TradesCategoryService()
tc_df = service.load_dataframe(start_date=cot_start)
tc_df = service.filter_and_rename(tc_df)

print(f"Geladen: {len(tc_df)} CoT-Datenpunkte von Socrata.\n")

if tc_df.empty:
    print("Keine neuen CoT-Daten – Pipeline beendet.")
    client.close()
    exit(0)

# Nur neue Dates (nach letztem DB-Eintrag) schreiben
if last_cot:
    last_cot_ts = pd.Timestamp(last_cot, tz="UTC")
    tc_df_new = tc_df[tc_df["Date"] > last_cot_ts]
else:
    tc_df_new = tc_df

print(f"Davon neu (noch nicht in DB): {len(tc_df_new)} Datenpunkte")

# Alle geladenen CoT-Dates für Alignment der anderen Quellen verwenden
cot_dates = tc_df["Date"].drop_duplicates().sort_values()
print(f"Unique CoT-Dates für Alignment: {len(cot_dates)}")

cot_points = []
for index, row in tc_df_new.iterrows():
    try:
        point = Point("cot_data") \
            .tag("market_names", row['Market Names']) \
            .field("Open Interest", float(row['Open Interest'])) \
            .field("Producer/Merchant/Processor/User Long", float(row['Producer/Merchant/Processor/User Long'])) \
            .field("Producer/Merchant/Processor/User Short", float(row['Producer/Merchant/Processor/User Short'])) \
            .field("Swap Dealer Long", float(row['Swap_Dealer_Long'])) \
            .field("Swap Dealer Short", float(row['Swap_Dealer_Short'])) \
            .field("Swap Dealer Spread", float(row['Swap_Dealer_Spread'])) \
            .field("Managed Money Long", float(row['Managed_Money_Long'])) \
            .field("Managed Money Short", float(row['Managed_Money_Short'])) \
            .field("Managed Money Spread", float(row['Managed_Money_Spread'])) \
            .field("Other Reportables Long", float(row['Other_Reportables_Long'])) \
            .field("Other Reportables Short", float(row['Other_Reportables_Short'])) \
            .field("Other Reportables Spread", float(row['Other_Reportables_Spread'])) \
            .field("Total Traders", float(row['Total_Traders'])) \
            .field("Traders Prod/Merc Long", float(row['Traders_Prod_Merc_Long'])) \
            .field("Traders Prod/Merc Short", float(row['Traders_Prod_Merc_Short'])) \
            .field("Traders Swap Long", float(row['Traders_Swap_Long'])) \
            .field("Traders Swap Short", float(row['Traders_Swap_Short'])) \
            .field("Traders Swap Spread", float(row['Traders_Swap_Spread'])) \
            .field("Traders M Money Long", float(row['Traders_M_Money_Long'])) \
            .field("Traders M Money Short", float(row['Traders_M_Money_Short'])) \
            .field("Traders M Money Spread", float(row['Traders_M_Money_Spread'])) \
            .field("Traders Other Rept Long", float(row['Traders_Other_Rept_Long'])) \
            .field("Traders Other Rept Short", float(row['Traders_Other_Rept_Short'])) \
            .field("Traders Other Rept Spread", float(row['Traders_Other_Rept_Spread'])) \
            .time(row['Date'])
        cot_points.append(point)
    except Exception as e:
        print(f"Fehler CoT Zeile {index}: {e}")
        continue

if cot_points:
    client.write(record=cot_points)
    print(f"Geschrieben: {len(cot_points)} CoT-Datenpunkte.")
else:
    print("Keine neuen CoT-Datenpunkte zu schreiben.")

# ── 2. Macro Data via yfinance (VIX, USD Index, USD/CHF) ────────────────────
macro_service = MacroPriceService()
macro_df = macro_service.load_aligned(cot_dates=cot_dates, start_date=macro_start)

print(f"\n{len(macro_df)} Macro-Datenpunkte aligned zu CoT-Dates.")

if last_macro:
    last_macro_ts = pd.Timestamp(last_macro, tz="UTC")
    macro_df_new = macro_df[macro_df["date"] > last_macro_ts]
else:
    macro_df_new = macro_df

print(f"Davon neu: {len(macro_df_new)} Datenpunkte")

macro_points = []
for index, row in macro_df_new.iterrows():
    try:
        p = Point("macro_by_date").time(row["date"].to_pydatetime())
        if pd.notna(row.get("vix")):
            p = p.field("vix", float(row["vix"]))
        if pd.notna(row.get("usd_index")):
            p = p.field("usd_index", float(row["usd_index"]))
        if pd.notna(row.get("usd_chf")):
            p = p.field("usd_chf", float(row["usd_chf"]))
        if len(p._fields) > 0:
            macro_points.append(p)
    except Exception as e:
        print(f"Fehler Macro Zeile {index}: {e}")
        continue

if macro_points:
    client.write(record=macro_points)
    print(f"Geschrieben: {len(macro_points)} Macro-Datenpunkte.")
else:
    print("Keine neuen Macro-Datenpunkte zu schreiben.")

# ── 3. Futures Price Data (aligned to CoT dates) ────────────────────────────
futures_service = FuturesPriceService()
futures_df = futures_service.load_aligned(cot_dates=cot_dates, start_date=futures_start)

print(f"\n{len(futures_df)} Futures-Preise aligned zu CoT-Dates.")

if last_futures:
    last_futures_ts = pd.Timestamp(last_futures, tz="UTC")
    futures_df_new = futures_df[futures_df["date"] > last_futures_ts]
else:
    futures_df_new = futures_df

print(f"Davon neu: {len(futures_df_new)} Datenpunkte")

futures_points = []
for index, row in futures_df_new.iterrows():
    try:
        p = Point("futures_prices").time(row["date"].to_pydatetime())
        if pd.notna(row.get("gold")):
            p = p.field("gold_close", float(row["gold"]))
        if pd.notna(row.get("silver")):
            p = p.field("silver_close", float(row["silver"]))
        if pd.notna(row.get("copper")):
            p = p.field("copper_close", float(row["copper"]))
        if pd.notna(row.get("platinum")):
            p = p.field("platinum_close", float(row["platinum"]))
        if pd.notna(row.get("palladium")):
            p = p.field("palladium_close", float(row["palladium"]))
        if pd.notna(row.get("crude_oil_wti")):
            p = p.field("crude_oil_close", float(row["crude_oil_wti"]))
        if len(p._fields) > 0:
            futures_points.append(p)
    except Exception as e:
        print(f"Fehler Futures Zeile {index}: {e}")
        continue

if futures_points:
    client.write(record=futures_points)
    print(f"Geschrieben: {len(futures_points)} Futures-Preise.")
else:
    print("Keine neuen Futures-Preise zu schreiben.")

# ── 4. EIA Crude Oil Inventory Data ─────────────────────────────────────────
eia_service = EIAPetroleumService()
eia_df = eia_service.load_aligned(cot_dates=cot_dates, start_date=eia_start)

print(f"\n{len(eia_df)} EIA-Inventarpunkte aligned zu CoT-Dates.")

if last_eia:
    last_eia_ts = pd.Timestamp(last_eia, tz="UTC")
    eia_df_new = eia_df[eia_df["date"] > last_eia_ts]
else:
    eia_df_new = eia_df

print(f"Davon neu: {len(eia_df_new)} Datenpunkte")

eia_points = []
for index, row in eia_df_new.iterrows():
    try:
        p = Point("eia_petroleum_stocks").time(row["date"].to_pydatetime())
        if pd.notna(row.get("crude_oil_stocks_kb")):
            p = p.field("crude_oil_stocks_kb", float(row["crude_oil_stocks_kb"]))
        if len(p._fields) > 0:
            eia_points.append(p)
    except Exception as e:
        print(f"Fehler EIA Zeile {index}: {e}")
        continue

if eia_points:
    client.write(record=eia_points)
    print(f"Geschrieben: {len(eia_points)} EIA-Inventarpunkte.")
else:
    print("Keine neuen EIA-Datenpunkte zu schreiben.")

# ── 5. Databento Deferred Futures Prices (2nd & 3rd nearby) ─────────────────
databento_service = DatabentoContinuousService()
deferred_df = databento_service.load_aligned(cot_dates=cot_dates, start_date=deferred_start)

print(f"\n{len(deferred_df)} Databento-Preise aligned zu CoT-Dates.")

if last_deferred:
    last_deferred_ts = pd.Timestamp(last_deferred, tz="UTC")
    deferred_df_new = deferred_df[deferred_df["date"] > last_deferred_ts]
else:
    deferred_df_new = deferred_df

print(f"Davon neu: {len(deferred_df_new)} Datenpunkte")

deferred_fields = [
    "gold_2nd_close",      "gold_3rd_close",
    "silver_2nd_close",    "silver_3rd_close",
    "copper_2nd_close",    "copper_3rd_close",
    "platinum_2nd_close",  "platinum_3rd_close",
    "palladium_2nd_close", "palladium_3rd_close",
    "crude_oil_2nd_close", "crude_oil_3rd_close",
]

deferred_points = []
for index, row in deferred_df_new.iterrows():
    try:
        p = Point("futures_deferred_prices").time(row["date"].to_pydatetime())
        for field in deferred_fields:
            if pd.notna(row.get(field)):
                p = p.field(field, float(row[field]))
        if len(p._fields) > 0:
            deferred_points.append(p)
    except Exception as e:
        print(f"Fehler Databento Zeile {index}: {e}")
        continue

if deferred_points:
    client.write(record=deferred_points)
    print(f"Geschrieben: {len(deferred_points)} Databento-Preise.")
else:
    print("Keine neuen Databento-Datenpunkte zu schreiben.")

# ── Cleanup ──────────────────────────────────────────────────────────────────
client.close()
print("\nInfluxDB v3 client geschlossen. Pipeline abgeschlossen!")
