"""
PPCI-Markt-Konfiguration: Mapping von Marktnamen auf Preisspalten und Kontraktgrössen.

Wird von der Shapley-Owen-Zerlegung, dem Entscheidungsbaum und den PPCI/DP-Callbacks
gemeinsam genutzt.
"""

# Substring im Marktnamen (UPPERCASE) → Feldname in der futures_prices-Tabelle.
# Front-Month-Preis (yfinance, kontinuierlicher Proxy via YFinanceClient).
MARKET_TO_PRICE_COL: dict[str, str] = {
    "GOLD":      "gold_close",
    "SILVER":    "silver_close",
    "COPPER":    "copper_close",
    "PLATINUM":  "platinum_close",
    "PALLADIUM": "palladium_close",
    "CRUDE OIL": "crude_oil_close",
    "WTI":       "crude_oil_close",
}

# Kontraktgrössen in Einheiten pro Kontrakt (für Notional-Berechnungen).
CONTRACT_SIZES: dict[str, float] = {
    "GOLD":      100.0,    # troy ounces
    "SILVER":    5000.0,   # troy ounces
    "PLATINUM":  50.0,     # troy ounces
    "PALLADIUM": 100.0,    # troy ounces
    "COPPER":    25000.0,  # pounds
    "CRUDE OIL": 1000.0,   # barrels
    "WTI":       1000.0,   # barrels
}


# Substring im Marktnamen (UPPERCASE) → Feldname in der futures_deferred_prices-Tabelle.
# Databento 2nd-nearby continuous contract (.c.1).
MARKET_TO_2ND_NEARBY_COL: dict[str, str] = {
    "GOLD":      "gold_2nd_close",
    "SILVER":    "silver_2nd_close",
    "COPPER":    "copper_2nd_close",
    "PLATINUM":  "platinum_2nd_close",
    "PALLADIUM": "palladium_2nd_close",
    "CRUDE OIL": "crude_oil_2nd_close",
    "WTI":       "crude_oil_2nd_close",
}


# Substring im Marktnamen (UPPERCASE) → Feldname in der futures_deferred_prices-Tabelle.
# Databento 3rd-nearby continuous contract (.c.2).
MARKET_TO_3RD_NEARBY_COL: dict[str, str] = {
    "GOLD":      "gold_3rd_close",
    "SILVER":    "silver_3rd_close",
    "COPPER":    "copper_3rd_close",
    "PLATINUM":  "platinum_3rd_close",
    "PALLADIUM": "palladium_3rd_close",
    "CRUDE OIL": "crude_oil_3rd_close",
    "WTI":       "crude_oil_3rd_close",
}


def get_price_col(market_name: str) -> str | None:
    """Gibt den Spaltennamen in df_futures_prices zurück, oder None wenn nicht gefunden."""
    mn = (market_name or "").upper()
    for key, col in MARKET_TO_PRICE_COL.items():
        if key in mn:
            return col
    return None


def get_2nd_nearby_price_col(market_name: str) -> str | None:
    """Gibt den Spaltennamen in df_deferred_prices (Databento .c.1) zurück, oder None."""
    mn = (market_name or "").upper()
    for key, col in MARKET_TO_2ND_NEARBY_COL.items():
        if key in mn:
            return col
    return None


def get_3rd_nearby_price_col(market_name: str) -> str | None:
    """Gibt den Spaltennamen in df_deferred_prices (Databento .c.2) zurück, oder None."""
    mn = (market_name or "").upper()
    for key, col in MARKET_TO_3RD_NEARBY_COL.items():
        if key in mn:
            return col
    return None


def get_contract_size(market_name: str) -> float:
    """Gibt die Kontraktgrösse (Einheiten/Kontrakt) zurück, oder 1.0 als Fallback."""
    mn = (market_name or "").upper()
    for key, size in CONTRACT_SIZES.items():
        if key in mn:
            return size
    return 1.0
