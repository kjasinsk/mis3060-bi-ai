"""
clean_dim_client.py

Fixes the data-quality issues found in dim_client (see dq_issues_dim_client.csv),
one issue at a time, with one function per issue. Each function:
  - takes the table in and returns the fixed table,
  - follows the "Fixing Strategy" from the DQ review,
  - prints what it changed, so every fix can be checked.

Order matters: duplicates are removed first, because the corrupted last
names live mostly in the duplicate rows.

Input : data/raw/dim_client.csv
Output: data/clean/dim_client_clean.csv
        data/clean/dim_client_cleaning_log.txt   (what each step changed)

Run from the repo root:
    python scripts/clean_dim_client.py
    python scripts/clean_dim_client.py path/to/dim_client.csv
"""

import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd

RAW_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/raw/dim_client.csv"
CLEAN_DIR = "data/clean"
CLEAN_PATH = os.path.join(CLEAN_DIR, "dim_client_clean.csv")
LOG_PATH = os.path.join(CLEAN_DIR, "dim_client_cleaning_log.txt")

log_lines = []


def log(text=""):
    """Print a line and keep it for the cleaning log."""
    print(text)
    log_lines.append(str(text))


def step(title):
    log()
    log("-" * 70)
    log(title)
    log("-" * 70)


# Values that mean "no data"
MISSING_TOKENS = {"", "nan", "none", "null", "n/a", "na", "?", "-", "--", "missing"}

# A valid name: letters plus spaces, hyphens, apostrophes and periods (O'Brien, Smith-Jones, St. John)
VALID_NAME = re.compile(r"^[A-Za-z][A-Za-z .'\-]*$")

US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
    "puerto rico": "PR",
}
VALID_CODES = set(US_STATES.values())


def is_missing(series):
    """True where a text value really means 'no data'."""
    return series.fillna("").astype(str).str.strip().str.lower().isin(MISSING_TOKENS)


def name_columns(df):
    return [c for c in df.columns if c.endswith("_name")]


def has_valid_names(df):
    """True for rows where every name column passes validation."""
    ok = pd.Series(True, index=df.index)
    for col in name_columns(df):
        ok &= df[col].fillna("").str.strip().str.match(VALID_NAME)
    return ok


# ---------------------------------------------------------------------------
# 0. Load
# ---------------------------------------------------------------------------
def load_raw(path):
    """Read every column as text so nothing is changed on the way in
    (e.g. ZIP '03897' would otherwise become the number 3897)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = df.columns.str.strip()
    log(f"Loaded {path}: {len(df):,} rows, {df.shape[1]} columns")
    log(f"Columns: {list(df.columns)}")
    return df


# ---------------------------------------------------------------------------
# 1. client_id - duplicate rows
# ---------------------------------------------------------------------------
def fix_duplicate_client_ids(df):
    """Keep one row per client_id: the copy whose names pass validation.
    If no copy (or more than one) is clean, keep the first one."""
    step("1. client_id: remove duplicate rows")
    df["client_id"] = df["client_id"].str.strip()
    dup_mask = df["client_id"].duplicated(keep=False)
    log(f"client_id values that appear more than once: {df.loc[dup_mask, 'client_id'].nunique()}")
    log(f"Extra rows to remove: {df['client_id'].duplicated().sum()}")

    # Sort so the clean copy comes first inside each client_id, then keep the first.
    df = df.assign(_valid=has_valid_names(df), _order=np.arange(len(df)))
    df = df.sort_values(["client_id", "_valid", "_order"], ascending=[True, False, True])
    removed = df[df["client_id"].duplicated()]
    df = df[~df["client_id"].duplicated()]
    df = df.sort_values("_order").drop(columns=["_valid", "_order"]).reset_index(drop=True)

    if len(removed):
        examples = removed.head(3)
        for _, r in examples.iterrows():
            names = ", ".join(f"{c}='{r[c]}'" for c in name_columns(df))
            log(f"  dropped copy of client_id {r['client_id']}: {names}")
    log(f"Rows now: {len(df):,}  |  duplicate client_ids left: {df['client_id'].duplicated().sum()}")
    return df


# ---------------------------------------------------------------------------
# 2. last_name - invalid characters
# ---------------------------------------------------------------------------
def fix_last_name(df):
    """Most bad names were removed with the duplicates. Any that remain are
    FLAGGED for manual review, not auto-corrected (0->o could create a wrong name)."""
    step("2. last_name: flag names with digits/symbols")
    df["last_name"] = df["last_name"].str.strip()
    bad = ~df["last_name"].str.match(VALID_NAME)
    df["name_review_flag"] = bad
    log(f"Invalid last names remaining after de-duplication: {bad.sum()}")
    if bad.any():
        log(f"  examples (flagged, NOT changed): {df.loc[bad, 'last_name'].head(5).tolist()}")
    return df


# ---------------------------------------------------------------------------
# 3. age - impossible values
# ---------------------------------------------------------------------------
def fix_age(df, low=18, high=110):
    """Set ages outside 18-110 (e.g. -5, 0, 999) to null and flag them.
    No imputation - a blank is more honest than an invented age."""
    step(f"3. age: null out values outside {low}-{high}")
    age = pd.to_numeric(df["age"].str.strip(), errors="coerce")
    bad = age.notna() & ~age.between(low, high)
    log(f"Out-of-range ages: {bad.sum()}  values: {sorted(age[bad].unique().tolist())}")
    df["age_flag"] = bad
    df["age"] = age.where(~bad).astype("Int64")  # Int64 = whole numbers that allow blanks
    log(f"Ages now outside {low}-{high}: {(~df['age'].dropna().between(low, high)).sum()}")
    return df


# ---------------------------------------------------------------------------
# 4. city - extra spaces and ALL CAPS
# ---------------------------------------------------------------------------
def fix_city(df):
    """Strip spaces (also double spaces inside) and use Title Case."""
    step("4. city: trim spaces and convert to Title Case")
    before = df["city"].copy()
    df["city"] = (df["city"].str.strip()
                  .str.replace(r"\s+", " ", regex=True)
                  .str.title())
    changed = (before != df["city"]).sum()
    log(f"Cities changed: {changed}")
    for b, a in list(zip(before[before != df["city"]], df["city"][before != df["city"]]))[:3]:
        log(f"  '{b}' -> '{a}'")
    return df


# ---------------------------------------------------------------------------
# 5. state - full names instead of 2-letter codes
# ---------------------------------------------------------------------------
def fix_state(df):
    """Map full state names to 2-letter USPS codes with a lookup dictionary."""
    step("5. state: convert full names to 2-letter codes")
    raw = df["state"].str.strip()
    full_name = raw.str.lower().isin(US_STATES)
    log(f"Full state names found: {full_name.sum()}")
    df["state"] = raw.str.lower().map(US_STATES).fillna(raw.str.upper())
    unknown = ~df["state"].isin(VALID_CODES) & ~is_missing(df["state"])
    log(f"States not a valid 2-letter code after fix: {unknown.sum()}"
        + (f"  values: {df.loc[unknown, 'state'].unique().tolist()[:10]}" if unknown.any() else ""))
    return df


# ---------------------------------------------------------------------------
# 6. zip_code - lost leading zeros
# ---------------------------------------------------------------------------
def fix_zip_code(df):
    """Pad ZIPs to 5 digits with leading zeros and keep them as text."""
    step("6. zip_code: restore leading zeros")
    z = df["zip_code"].str.strip().str.replace(r"\.0$", "", regex=True)  # '3897.0' -> '3897'
    short = z.str.fullmatch(r"\d{1,4}")
    log(f"ZIPs shorter than 5 digits: {short.sum()}  "
        f"lengths: {z[short].str.len().value_counts().sort_index().to_dict()}")
    df["zip_code"] = z.where(~short, z.str.zfill(5))
    not_five = ~df["zip_code"].str.fullmatch(r"\d{5}(-\d{4})?")
    log(f"ZIPs not exactly 5 digits after fix: {not_five.sum()}")
    # Spot-check: Northeast states should mostly have ZIPs starting with 0
    padded = df[short]
    if len(padded) and "state" in df.columns:
        log(f"  padded ZIPs by state (spot-check, 0xxxx = Northeast): "
            f"{padded['state'].value_counts().head(6).to_dict()}")
    return df


# ---------------------------------------------------------------------------
# 7. risk_profile - missing values
# ---------------------------------------------------------------------------
def fix_risk_profile(df):
    """Fill missing risk profiles with the explicit category 'Unknown'.
    Do NOT infer it from age or tier - it is a regulatory attribute."""
    step("7. risk_profile: fill missing with 'Unknown'")
    missing = is_missing(df["risk_profile"])
    log(f"Missing risk profiles: {missing.sum()} ({missing.mean():.1%})")
    df["risk_profile"] = df["risk_profile"].str.strip().str.title().where(~missing, "Unknown")
    log(f"Values now: {df['risk_profile'].value_counts().to_dict()}")
    return df


# ---------------------------------------------------------------------------
# 8. client_since - mixed date formats
# ---------------------------------------------------------------------------
def fix_client_since(df):
    """Parse each format explicitly (YYYY-MM-DD and MM/DD/YYYY) and store as ISO dates.
    Ambiguous slash dates (both parts <= 12) are flagged because they rely on
    the MM/DD assumption."""
    step("8. client_since: convert all dates to YYYY-MM-DD")
    s = df["client_since"].str.strip()
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    slash = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    is_slash = iso.isna() & slash.notna()
    parts = s[is_slash].str.split("/", expand=True)
    ambiguous = pd.Series(False, index=df.index)
    if len(parts):
        ambiguous.loc[is_slash] = (parts[0].astype(int) <= 12) & (parts[1].astype(int) <= 12)
    log(f"ISO dates: {iso.notna().sum()}  |  slash dates: {is_slash.sum()} "
        f"(ambiguous, flagged: {ambiguous.sum()})")
    parsed = iso.fillna(slash)
    unparsed = parsed.isna() & ~is_missing(s)
    log(f"Dates that could not be parsed: {unparsed.sum()}"
        + (f"  values: {s[unparsed].head(5).tolist()}" if unparsed.any() else ""))
    future = parsed > pd.Timestamp(datetime.today().date())
    if future.any():
        log(f"  warning: {future.sum()} dates are in the future")
    df["client_since"] = parsed.dt.strftime("%Y-%m-%d")
    df["client_since_ambiguous"] = ambiguous
    return df


# ---------------------------------------------------------------------------
# 9. is_active - inconsistent true/false values
# ---------------------------------------------------------------------------
def fix_is_active(df):
    """Map True/yes/1 -> True and False/no/0 -> False. Anything else -> blank."""
    step("9. is_active: convert to True/False")
    raw = df["is_active"].str.strip().str.lower()
    log(f"Values before: {df['is_active'].value_counts().to_dict()}")
    mapping = {"true": True, "yes": True, "y": True, "1": True, "t": True,
               "false": False, "no": False, "n": False, "0": False, "f": False}
    df["is_active"] = raw.map(mapping).astype("boolean")
    unknown = df["is_active"].isna() & ~is_missing(raw)
    after = {str(k): int(v) for k, v in df["is_active"].value_counts(dropna=False).items()}
    log(f"Values after:  {after}")
    log(f"Unrecognized values set to blank: {unknown.sum()}")
    return df


# ---------------------------------------------------------------------------
# 10. Final check - is every issue gone?
# ---------------------------------------------------------------------------
def validate(df):
    step("10. FINAL CHECK")
    checks = {
        "no duplicate client_id": df["client_id"].duplicated().sum() == 0,
        "no invalid last names (unflagged)": (~df["last_name"].str.match(VALID_NAME) & ~df["name_review_flag"]).sum() == 0,
        "all ages 18-110 or blank": df["age"].dropna().between(18, 110).all(),
        "no city with extra spaces": (df["city"] != df["city"].str.strip()).sum() == 0,
        "no ALL-CAPS city": (df["city"].str.len().gt(3) & (df["city"] == df["city"].str.upper())).sum() == 0,
        "all states are 2-letter codes": df["state"].dropna().isin(VALID_CODES).all(),
        "all ZIPs are 5 digits (text)": df["zip_code"].str.fullmatch(r"\d{5}(-\d{4})?").all(),
        "no blank risk_profile": (~is_missing(df["risk_profile"])).all(),
        "all dates YYYY-MM-DD": df["client_since"].dropna().str.fullmatch(r"\d{4}-\d{2}-\d{2}").all(),
        "is_active only True/False/blank": set(df["is_active"].dropna().unique()) <= {True, False},
    }
    for name, passed in checks.items():
        log(f"  {'PASS' if passed else 'FAIL'}  {name}")
    return all(checks.values())


def save(df):
    os.makedirs(CLEAN_DIR, exist_ok=True)
    df.to_csv(CLEAN_PATH, index=False)
    log()
    log(f"Saved cleaned file: {CLEAN_PATH}  ({len(df):,} rows, {df.shape[1]} columns)")
    log("New columns added: name_review_flag, age_flag, client_since_ambiguous")
    log("Note: open the CSV with Power BI or pandas (dtype zip_code=str). If you open it in")
    log("Excel, import zip_code as Text or Excel will drop the leading zeros again.")
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print(f"Saved cleaning log:  {LOG_PATH}")


def main():
    df = load_raw(RAW_PATH)
    df = fix_duplicate_client_ids(df)   # first: removes most corrupted names
    df = fix_last_name(df)
    df = fix_age(df)
    df = fix_city(df)
    df = fix_state(df)
    df = fix_zip_code(df)
    df = fix_risk_profile(df)
    df = fix_client_since(df)
    df = fix_is_active(df)
    all_passed = validate(df)
    save(df)
    if not all_passed:
        print("\nSome checks FAILED - see the log above before using this file.")


if __name__ == "__main__":
    main()
