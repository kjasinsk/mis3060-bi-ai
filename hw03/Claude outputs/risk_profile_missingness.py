"""
risk_profile_missingness.py

Analyzes the missing values in the risk_profile column of dim_client.

The data-quality review found 155 rows (6.1%) with no risk_profile. Before
choosing a fix, this script asks the key question: are the blanks
random, or do they follow a pattern? The answer decides whether the
'Unknown' category is a safe fix, or whether the gap biases any analysis
that ignores those rows.

What it does:
  1. Counts true blanks AND "disguised" blanks ("", "N/A", "none", "?", ...)
  2. Compares clients WITH vs WITHOUT a risk profile on every other column
     (numbers: age, tenure, AUM ... / categories: state, tier, is_active ...)
     and runs a significance test for each one
  3. Checks whether blanks cluster by client_id order or by client_since year
     (a sign of one bad load or one system change)
  4. Checks whether risk_profile is missing together with other columns
  5. Gives a plain-English verdict: looks random (MCAR) or linked to other
     columns (MAR)
  6. Saves a text report, a CSV of the missing rows, and a chart

Run from the repo root:
    python scripts/risk_profile_missingness.py
    python scripts/risk_profile_missingness.py path/to/dim_client.csv
"""

import os
import sys

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")  # save charts without opening a window
import matplotlib.pyplot as plt
from scipy import stats

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
DATA_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/raw/dim_client.csv"
OUTPUT_DIR = "outputs/risk_profile_missingness"
TARGET = "risk_profile"
ID_COL = "client_id"
ALPHA = 0.05            # significance level for the tests
MAX_CATEGORIES = 30     # skip text columns with more distinct values than this (names, cities)

# Text values that really mean "missing"
DISGUISED_MISSING = {"", "nan", "none", "null", "n/a", "na", "unknown", "?", "-", "--", "missing", "tbd"}

os.makedirs(OUTPUT_DIR, exist_ok=True)
report = []


def log(text=""):
    """Print a line and keep it for the saved report."""
    print(text)
    report.append(str(text))


def section(title):
    log()
    log("=" * 70)
    log(title)
    log("=" * 70)


# ---------------------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------------------
# Read everything as text first so nothing is silently converted
# (e.g. ZIP codes losing leading zeros, "N/A" becoming NaN unnoticed).
raw = pd.read_csv(DATA_PATH, dtype=str, keep_default_na=False)
raw.columns = raw.columns.str.strip()
if TARGET not in raw.columns:
    sys.exit(f"Column '{TARGET}' not found. Columns are: {list(raw.columns)}")

section(f"RISK_PROFILE MISSINGNESS ANALYSIS  ({DATA_PATH})")
log(f"Rows: {len(raw):,}  |  Columns: {raw.shape[1]}")

# De-duplicate on client_id so duplicate rows don't count a missing value twice
# (the DQ review found 20 duplicated client_ids).
if ID_COL in raw.columns:
    dupes = raw[ID_COL].duplicated().sum()
    if dupes:
        log(f"Note: {dupes} duplicate {ID_COL} rows found; keeping the first copy of each.")
        raw = raw.drop_duplicates(subset=ID_COL, keep="first").reset_index(drop=True)
        log(f"Rows after de-duplication: {len(raw):,}")

# ---------------------------------------------------------------------------
# 2. How much is missing? (true blanks vs disguised blanks)
# ---------------------------------------------------------------------------
section("1. HOW MUCH IS MISSING")
values = raw[TARGET]
clean = values.str.strip().str.lower()
is_blank = values.str.strip() == ""
is_disguised = clean.isin(DISGUISED_MISSING) & ~is_blank
is_missing = is_blank | is_disguised

log(f"Empty / blank cells:            {is_blank.sum():>6,}")
log(f"Disguised missing ('N/A', etc): {is_disguised.sum():>6,}"
    + (f"   values: {sorted(values[is_disguised].unique())}" if is_disguised.any() else ""))
log(f"TOTAL missing risk_profile:     {is_missing.sum():>6,}  ({is_missing.mean():.1%} of rows)")

log()
log("Values that ARE filled in:")
counts = values[~is_missing].str.strip().value_counts()
for val, n in counts.items():
    log(f"  {val:<25} {n:>6,}  ({n / len(values):.1%})")
variants = values[~is_missing].str.strip().str.lower().nunique()
if variants < counts.size:
    log(f"  Warning: {counts.size} spellings but only {variants} values ignoring case - clean capitalization too.")

# Build a working copy with proper types for the comparisons
df = raw.replace({"": np.nan})
df[TARGET + "_missing"] = is_missing.astype(int)
MISS = TARGET + "_missing"

# Make helpful extra columns when the source columns exist
if "client_since" in df.columns:
    iso = pd.to_datetime(df["client_since"], format="%Y-%m-%d", errors="coerce")
    slash = pd.to_datetime(df["client_since"], format="%m/%d/%Y", errors="coerce")
    df["client_since_date"] = iso.fillna(slash)
    df["client_since_year"] = df["client_since_date"].dt.year
    df["tenure_years"] = (pd.Timestamp.today() - df["client_since_date"]).dt.days / 365.25
if "age" in df.columns:
    age = pd.to_numeric(df["age"], errors="coerce")
    df["age"] = age.where(age.between(18, 110))  # -5, 0, 999 are invalid (see DQ review)
if "is_active" in df.columns:
    df["is_active"] = df["is_active"].str.strip().str.lower().map(
        {"true": "True", "yes": "True", "1": "True", "false": "False", "no": "False", "0": "False"})
if "state" in df.columns:
    df["state"] = df["state"].str.strip()

# ---------------------------------------------------------------------------
# 3. Do clients WITH and WITHOUT a risk profile look different?
# ---------------------------------------------------------------------------
section("2. MISSING vs NOT MISSING - COMPARISON BY OTHER COLUMNS")
log("If risk_profile is missing at random, both groups should look the same.")
log(f"A p-value below {ALPHA} means the column is linked to the missingness.")

skip = {TARGET, MISS, ID_COL, "client_since", "client_since_date"}
findings = []  # (column, test, p_value, summary)

for col in df.columns:
    if col in skip or "zip" in col.lower() or col.lower().endswith("_id"):
        continue  # codes and IDs are labels, not quantities
    as_num = pd.to_numeric(df[col], errors="coerce")
    numeric = as_num.notna().mean() > 0.9  # mostly numbers -> treat as numeric

    if numeric:
        a = as_num[df[MISS] == 1].dropna()
        b = as_num[df[MISS] == 0].dropna()
        if len(a) < 5 or len(b) < 5:
            continue
        p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
        summary = f"median missing={a.median():,.1f} vs filled={b.median():,.1f}"
        findings.append((col, "Mann-Whitney", p, summary))
        log()
        log(f"[numeric] {col}: {summary}  ->  p = {p:.4f}{'  ** SIGNIFICANT' if p < ALPHA else ''}")
    else:
        cats = df[col].fillna("(blank)").astype(str).str.strip()
        if cats.nunique() > MAX_CATEGORIES or cats.nunique() < 2:
            continue  # names, cities, free text - too many groups to test
        table = pd.crosstab(cats, df[MISS])
        if table.shape[1] < 2:
            continue
        chi2, p, dof, expected = stats.chi2_contingency(table)
        rate = (table[1] / table.sum(axis=1)).sort_values(ascending=False)
        top = ", ".join(f"{k}: {v:.1%}" for k, v in rate.head(3).items())
        summary = f"highest missing rates -> {top}"
        findings.append((col, "Chi-square", p, summary))
        log()
        log(f"[category] {col}: p = {p:.4f}{'  ** SIGNIFICANT' if p < ALPHA else ''}")
        log(f"  Missing rate by {col}:")
        for k, v in rate.items():
            log(f"    {k:<20} {v:6.1%}  ({table.loc[k, 1]} of {table.loc[k].sum()})")
        if (expected < 5).any():
            log("  (Some groups are small, so read this p-value with caution.)")

# ---------------------------------------------------------------------------
# 4. Are the blanks bunched together? (one bad batch / system change)
# ---------------------------------------------------------------------------
section("3. ARE THE BLANKS BUNCHED TOGETHER?")
if ID_COL in df.columns:
    order = df.assign(_id=pd.to_numeric(df[ID_COL], errors="coerce")).sort_values("_id")
    miss_seq = order[MISS].to_numpy()
    runs = np.diff(np.concatenate([[0], miss_seq, [0]]))
    run_lengths = np.where(runs == -1)[0] - np.where(runs == 1)[0]
    longest = run_lengths.max() if run_lengths.size else 0
    # Chance of a run this long if blanks were scattered at random
    rate = miss_seq.mean()
    log(f"Longest streak of consecutive missing rows (by {ID_COL}): {longest}")
    log(f"With a {rate:.1%} missing rate, random streaks are usually 1-3 rows long.")
    deciles = pd.qcut(order["_id"].rank(method="first"), 10, labels=[f"D{i}" for i in range(1, 11)])
    by_decile = order.groupby(deciles, observed=True)[MISS].mean()
    log(f"Missing rate by {ID_COL} range (lowest 10% of IDs = D1):")
    log("  " + "  ".join(f"{k}:{v:.1%}" for k, v in by_decile.items()))

if "client_since_year" in df.columns:
    log()
    log("Missing rate by year the client joined:")
    by_year = df.groupby("client_since_year")[MISS].agg(["mean", "sum", "count"])
    for yr, r in by_year.iterrows():
        bar = "#" * int(round(r["mean"] * 200))
        log(f"  {int(yr)}  {r['mean']:6.1%}  ({int(r['sum'])} of {int(r['count'])})  {bar}")

# ---------------------------------------------------------------------------
# 5. Missing together with other columns?
# ---------------------------------------------------------------------------
section("4. IS RISK_PROFILE MISSING TOGETHER WITH OTHER COLUMNS?")
other_missing = raw.drop(columns=[TARGET]).apply(
    lambda s: s.str.strip().str.lower().isin(DISGUISED_MISSING))
any_hits = False
for col in other_missing.columns:
    both = (other_missing[col] & is_missing).sum()
    if other_missing[col].sum():
        any_hits = True
        log(f"  {col:<20} missing in {other_missing[col].sum():>5} rows; "
            f"{both} of those also lack risk_profile")
if not any_hits:
    log("  No other column has blank values, so risk_profile is missing on its own.")

# ---------------------------------------------------------------------------
# 6. Verdict
# ---------------------------------------------------------------------------
section("5. VERDICT")
significant = [f for f in findings if f[2] < ALPHA]
if significant:
    log("Missingness is NOT completely random (evidence of MAR - Missing At Random,")
    log("i.e. linked to other columns). Linked columns:")
    for col, test, p, summary in sorted(significant, key=lambda f: f[2]):
        log(f"  - {col} ({test}, p = {p:.4f}): {summary}")
    log()
    log("What this means: dropping or ignoring the missing rows would bias risk-based")
    log("analyses toward the groups above. Keep 'Unknown' as its own category, report")
    log("results with and without it, and send these specific clients back to advisors.")
else:
    log("No column is significantly linked to the missing values. The blanks look")
    log("MISSING COMPLETELY AT RANDOM (MCAR) based on the data we have.")
    log()
    log("What this means: filling with 'Unknown' and excluding those rows from")
    log("risk-based analyses should not bias the results much. (MNAR - missing because")
    log("of the risk profile itself - can't be ruled out from this data alone.)")
if len(findings) >= 10:
    log(f"(Note: {len(findings)} tests were run, so about {len(findings) * ALPHA:.1f} could be "
        "'significant' by chance alone.)")

# ---------------------------------------------------------------------------
# 7. Save outputs
# ---------------------------------------------------------------------------
missing_rows_path = os.path.join(OUTPUT_DIR, "risk_profile_missing_rows.csv")
raw[is_missing].to_csv(missing_rows_path, index=False)

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
counts_all = values.where(~is_missing, "MISSING").str.strip().value_counts()
colors = ["#d62728" if k == "MISSING" else "#1f77b4" for k in counts_all.index]
axes[0].bar(counts_all.index, counts_all.values, color=colors)
axes[0].set_title("risk_profile values (missing in red)")
axes[0].set_ylabel("Clients")
axes[0].tick_params(axis="x", rotation=30)

if "client_since_year" in df.columns and df["client_since_year"].notna().any():
    by_year = df.groupby("client_since_year")[MISS].mean() * 100
    axes[1].plot(by_year.index.astype(int), by_year.values, marker="o")
    axes[1].axhline(is_missing.mean() * 100, color="gray", linestyle="--", label="overall rate")
    axes[1].set_title("Missing rate by year client joined")
    axes[1].set_xlabel("client_since year")
    axes[1].legend()
else:
    axes[1].bar(["missing", "filled"], [is_missing.sum(), (~is_missing).sum()], color=["#d62728", "#1f77b4"])
    axes[1].set_title("Missing vs filled")
axes[1].set_ylabel("% missing")
plt.tight_layout()
chart_path = os.path.join(OUTPUT_DIR, "risk_profile_missingness.png")
plt.savefig(chart_path, dpi=150)
plt.close()

report_path = os.path.join(OUTPUT_DIR, "risk_profile_missingness_report.txt")
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print()
print(f"Saved: {report_path}")
print(f"Saved: {missing_rows_path}")
print(f"Saved: {chart_path}")
