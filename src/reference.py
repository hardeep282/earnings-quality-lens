

"""Reference data (dimensions) decided in Phase 1. One place, imported everywhere."""

# Business-model grouping by cost structure (Phase 1 decision; differs from GICS on purpose)
BUSINESS_GROUP = {
    "NVDA": "Semiconductors", "AVGO": "Semiconductors", "TSM": "Semiconductors",
    "MSFT": "Software & internet", "GOOG": "Software & internet", "META": "Software & internet",
    "ORCL": "Software & internet", "PLTR": "Software & internet", "NFLX": "Software & internet",
    "AAPL": "Consumer hardware & e-commerce", "AMZN": "Consumer hardware & e-commerce",
    "BABA": "Consumer hardware & e-commerce", "TSLA": "Consumer hardware & e-commerce",
    "WMT": "Retail", "COST": "Retail", "HD": "Retail",
    "JPM": "Financials & payments", "BRK-B": "Financials & payments",
    "V": "Financials & payments", "MA": "Financials & payments",
    "LLY": "Pharma", "JNJ": "Pharma",
    "XOM": "Energy",
}

# Companies whose income statement does not follow the Revenue - COGS = Gross profit logic
FINANCIALS = {"JPM", "BRK-B", "V", "MA"}

# Non-US filers (used as the comparison group for the 2017 US tax-reform test, H7)
NON_US = {"TSM", "BABA"}