"""
PPCI-Markt-Konfiguration: Mapping von Marktnamen auf Preisspalten und Kontraktgrössen.

Wird von der Shapley-Owen-Zerlegung, dem Entscheidungsbaum und den PPCI/DP-Callbacks
gemeinsam genutzt.
"""

# Substring im Marktnamen (UPPERCASE) → Feldname in der futures_prices-Tabelle.
# Continuous-Contract-Proxy für den 2nd-Nearby-Preis.
MARKET_TO_PRICE_COL: dict[str, str] = {
    "GOLD":      "gold_close",
    "SILVER":    "silver_close",
    "COPPER":    "copper_close",
    "PLATINUM":  "platinum_close",
    "PALLADIUM": "palladium_close",
}

# Kontraktgrössen in Einheiten pro Kontrakt (für Notional-Berechnungen).
CONTRACT_SIZES: dict[str, float] = {
    "GOLD":      100.0,    # troy ounces
    "SILVER":    5000.0,   # troy ounces
    "PLATINUM":  50.0,     # troy ounces
    "PALLADIUM": 100.0,    # troy ounces
    "COPPER":    25000.0,  # pounds
}


def get_price_col(market_name: str) -> str | None:
    """Gibt den Spaltennamen in df_futures_prices zurück, oder None wenn nicht gefunden."""
    mn = (market_name or "").upper()
    for key, col in MARKET_TO_PRICE_COL.items():
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
