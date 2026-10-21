"""
wildcat_schema.py

Shared metadata for the Wildcat Capital tables: what type each column
SHOULD be, which column is the key, which columns point at other tables,
and the business rules each column must follow.

This file holds facts ABOUT the data, not code that processes it. The
profiler (01), the cleaner (02) and the validator (03) all read it, so a
rule is written once and every script agrees on it.

Author: Kaitlyn Jasinski
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folders (relative to the hw04 folder, so the scripts run from anywhere)
# ---------------------------------------------------------------------------
HW_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = HW_DIR / "data" / "raw"
CLEAN_DIR = HW_DIR / "data" / "clean"
AUDIT_DIR = HW_DIR / "data" / "audit"
REPORTS_DIR = HW_DIR / "reports"

TABLES = [
    "dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
    "fact_fees", "fact_portfolio_snapshot", "fact_transactions",
]

# ---------------------------------------------------------------------------
# Expected type of every column
#   int      whole number written as digits only (no ".0")
#   decimal  plain number (no %, $ or commas)
#   date     ISO date YYYY-MM-DD
#   bool     True / False
#   flag01   0 / 1
#   text     free text
# ---------------------------------------------------------------------------
COLUMN_TYPES = {
    "dim_advisor": {
        "advisor_id": "int", "first_name": "text", "last_name": "text",
        "region": "text", "years_experience": "int", "aum_target_mm": "int",
        "certifications": "text",
    },
    "dim_benchmark": {
        "benchmark_id": "int", "name": "text", "asset_class": "text",
        "ticker_proxy": "text",
    },
    "dim_client": {
        "client_id": "int", "first_name": "text", "last_name": "text",
        "age": "int", "city": "text", "state": "text", "zip_code": "text",
        "risk_profile": "text", "client_tier": "text",
        "primary_account_type": "text", "initial_aum": "decimal",
        "client_since": "date", "advisor_id": "int", "is_active": "bool",
    },
    "dim_date": {
        "date_id": "int", "date": "date", "year": "int", "quarter": "int",
        "month": "int", "month_name": "text", "week_of_year": "int",
        "day_of_week": "text", "is_month_end": "flag01",
        "is_quarter_end": "flag01", "is_year_end": "flag01",
        "is_trading_day": "flag01",
    },
    "dim_security": {
        "security_id": "int", "ticker": "text", "name": "text",
        "asset_class": "text", "sector": "text", "benchmark_id": "int",
        "is_etf": "bool", "expense_ratio_bps": "decimal",
    },
    "fact_fees": {
        "fee_id": "int", "client_id": "int", "advisor_id": "int",
        "fee_date": "date", "fee_type": "text", "aum_basis": "decimal",
        "bps_charged": "decimal", "amount": "decimal",
    },
    "fact_portfolio_snapshot": {
        "snapshot_id": "int", "client_id": "int", "advisor_id": "int",
        "benchmark_id": "int", "snapshot_date": "date", "year": "int",
        "month": "int", "aum": "decimal", "return_ytd": "decimal",
        "benchmark_return_ytd": "decimal", "active_alpha_ytd": "decimal",
        "cash_pct": "decimal", "account_type": "text",
    },
    "fact_transactions": {
        "txn_id": "int", "client_id": "int", "advisor_id": "int",
        "security_id": "int", "txn_date": "date", "txn_type": "text",
        "shares": "decimal", "price": "decimal", "amount": "decimal",
    },
}

# Primary key of each table
PRIMARY_KEYS = {
    "dim_advisor": "advisor_id",
    "dim_benchmark": "benchmark_id",
    "dim_client": "client_id",
    "dim_date": "date_id",
    "dim_security": "security_id",
    "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id",
    "fact_transactions": "txn_id",
}

# Business key: the columns that describe "the same real-world thing".
# Two rows with the same business key are duplicates even if their IDs differ.
# dim_client leaves out last_name on purpose so that a typo in the name
# does not hide a duplicate person.
BUSINESS_KEYS = {
    "dim_advisor": ["first_name", "last_name", "region"],
    "dim_benchmark": ["ticker_proxy"],
    "dim_client": ["first_name", "zip_code", "age", "client_since",
                   "initial_aum"],
    "dim_date": ["date"],
    "dim_security": ["ticker"],
    "fact_fees": ["client_id", "fee_date", "fee_type"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
    "fact_transactions": ["client_id", "txn_date", "txn_type", "security_id",
                          "shares", "price", "amount"],
}

# Every relationship: (child table, child column, parent table, parent column)
# Ten ID-based relationships + three that join to the calendar.
RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]

# Columns where a blank is the CORRECT value for some rows (legitimate
# structure, not missing data). Value = plain-English reason.
CONDITIONAL_BLANKS = {
    ("dim_security", "sector"): "ETFs hold many sectors, so sector is blank when is_etf = True",
    ("dim_security", "expense_ratio_bps"): "only funds charge an expense ratio, so blank when is_etf = False",
    ("fact_transactions", "security_id"): "cash flows (Deposit, Withdrawal, Advisory Fee) involve no security",
    ("fact_transactions", "shares"): "cash flows (Deposit, Withdrawal, Advisory Fee) involve no shares",
    ("fact_transactions", "price"): "cash flows (Deposit, Withdrawal, Advisory Fee) involve no price",
}

# ---------------------------------------------------------------------------
# Allowed values (code lists)
# ---------------------------------------------------------------------------
US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT",
    "Delaware": "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME",
    "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
}

ALLOWED_VALUES = {
    ("dim_advisor", "region"): {"Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West"},
    ("dim_advisor", "aum_target_mm"): {"50", "75", "100", "150", "200"},
    ("dim_client", "state"): set(US_STATES.values()),
    ("dim_client", "risk_profile"): {"Conservative", "Moderately Conservative", "Balanced",
                                     "Moderately Aggressive", "Aggressive"},
    ("dim_client", "client_tier"): {"Retail", "HNW", "UHNW"},
    ("dim_client", "primary_account_type"): {"Taxable", "IRA", "Roth IRA", "Trust", "529"},
    ("dim_client", "is_active"): {"True", "False"},
    ("dim_security", "asset_class"): {"Equity", "Fixed Income", "Alternative", "Cash Equivalent"},
    ("dim_security", "is_etf"): {"True", "False"},
    ("fact_fees", "fee_type"): {"Management", "Advisory", "Custodial", "Performance"},
    ("fact_portfolio_snapshot", "account_type"): {"Taxable", "IRA", "Roth IRA", "Trust", "529"},
    ("fact_transactions", "txn_type"): {"Buy", "Sell", "Dividend", "Deposit", "Withdrawal",
                                        "Advisory Fee"},
}

# Natural business bounds: (min, max). None = no bound on that side.
RANGES = {
    ("dim_advisor", "years_experience"): (0, 50),
    ("dim_client", "age"): (18, 110),
    ("dim_client", "initial_aum"): (0.01, None),
    ("dim_date", "quarter"): (1, 4),
    ("dim_date", "month"): (1, 12),
    ("dim_date", "week_of_year"): (1, 53),
    ("dim_security", "expense_ratio_bps"): (0, 300),
    ("fact_fees", "aum_basis"): (0.01, None),
    ("fact_fees", "bps_charged"): (0, 300),
    ("fact_fees", "amount"): (0.01, None),
    ("fact_portfolio_snapshot", "month"): (1, 12),
    ("fact_portfolio_snapshot", "aum"): (0.01, None),
    ("fact_portfolio_snapshot", "return_ytd"): (-1.0, None),   # cannot lose more than 100%
    ("fact_portfolio_snapshot", "benchmark_return_ytd"): (-1.0, None),
    ("fact_portfolio_snapshot", "cash_pct"): (0, 1),
    ("fact_transactions", "shares"): (0.0000001, None),        # sign rule: shares are always positive
    ("fact_transactions", "price"): (0.01, None),
    ("fact_transactions", "amount"): (0.01, None),             # direction comes from txn_type
}

CASH_FLOW_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}
TRADE_TYPES = {"Buy", "Sell"}
SECURITY_TYPES = {"Buy", "Sell", "Dividend"}

# Each risk profile is benchmarked against exactly one benchmark.
# (Verified in the raw data: every client with a known profile follows it.)
RISK_TO_BENCHMARK = {
    "Aggressive": "1", "Moderately Aggressive": "1",
    "Balanced": "3",
    "Moderately Conservative": "8", "Conservative": "8",
}

# Client tiers by starting assets (verified in the raw data)
TIER_AUM = {"Retail": (0, 500_000), "HNW": (500_000, 5_000_000), "UHNW": (5_000_000, None)}
