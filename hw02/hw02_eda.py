"""
hw02_eda.py

Exploratory Data Analysis (EDA) script for Wildcat Capital's transaction
portfolio dataset.

Dataset: data/raw/fact_transactions.csv
Author: [Kaitlyn Jasinski]
Generated: 2026-09-20

This script loads the transaction dataset, profiles its structure and
quality, computes summary statistics and relationships between key
variables, saves three diagnostic charts, and writes a plain-text summary
of the analysis -- all in a single run.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

DATA_PATH = "data/raw/fact_transactions.csv"
CHARTS_DIR = "hw02/charts"
PROFILE_PATH = "hw02/hw02_profile.txt"
EXPECTED_SHAPE = (298772, 9)

os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)

profile_lines = []


def log(text=""):
    """Print a line to the console and also store it for the text summary."""
    print(text)
    profile_lines.append(str(text))


# ---------------------------------------------------------------------------
# 1. Load the data
# ---------------------------------------------------------------------------

df = pd.read_csv(DATA_PATH)

# ---------------------------------------------------------------------------
# 2. Shape
# ---------------------------------------------------------------------------

log("=" * 70)
log("DATASET SHAPE")
log("=" * 70)
log(f"Rows: {df.shape[0]:,}  |  Columns: {df.shape[1]}")
log()

# ---------------------------------------------------------------------------
# 3. Column names and data types
# ---------------------------------------------------------------------------

log("=" * 70)
log("COLUMN NAMES AND DATA TYPES")
log("=" * 70)
for col, dtype in df.dtypes.items():
    log(f"{col:<20} {dtype}")
log()

# ---------------------------------------------------------------------------
# 4. Missing values per column
# ---------------------------------------------------------------------------

log("=" * 70)
log("MISSING VALUES PER COLUMN")
log("=" * 70)
missing = df.isnull().sum()
for col, count in missing.items():
    log(f"{col:<20} {count:,}")
log()

# ---------------------------------------------------------------------------
# 5. Descriptive statistics for numeric columns
# ---------------------------------------------------------------------------

log("=" * 70)
log("DESCRIPTIVE STATISTICS (NUMERIC COLUMNS)")
log("=" * 70)
desc = df.describe().round(2)
log(desc.to_string())
log()

# ---------------------------------------------------------------------------
# 6. txn_type breakdown (value counts and percentages, most to least frequent)
# ---------------------------------------------------------------------------

log("=" * 70)
log("TXN_TYPE BREAKDOWN (COUNT AND PERCENTAGE)")
log("=" * 70)
txn_counts = df["txn_type"].value_counts()
txn_pct = df["txn_type"].value_counts(normalize=True) * 100
for txn_type in txn_counts.index:
    log(f"{txn_type:<15} {txn_counts[txn_type]:>10,}   {txn_pct[txn_type]:>6.2f}%")
log()

# ---------------------------------------------------------------------------
# 7. Unique counts: clients, advisors, securities
# ---------------------------------------------------------------------------

log("=" * 70)
log("UNIQUE ENTITY COUNTS")
log("=" * 70)
log(f"Unique clients:    {df['client_id'].nunique():,}")
log(f"Unique advisors:   {df['advisor_id'].nunique():,}")
log(f"Unique securities: {df['security_id'].nunique():,}")
log()

# ---------------------------------------------------------------------------
# 8. Date range
# ---------------------------------------------------------------------------

log("=" * 70)
log("DATE RANGE")
log("=" * 70)
log(f"Earliest txn_date: {df['txn_date'].min()}")
log(f"Latest txn_date:   {df['txn_date'].max()}")
log()

# ---------------------------------------------------------------------------
# 9. Duplicate txn_id check
# ---------------------------------------------------------------------------

log("=" * 70)
log("DUPLICATE TXN_ID CHECK")
log("=" * 70)
dup_count = df["txn_id"].duplicated().sum()
log(f"Duplicate txn_id count: {dup_count:,}")
log()

# ---------------------------------------------------------------------------
# 10. amount: mean, median, skewness
# ---------------------------------------------------------------------------

log("=" * 70)
log("AMOUNT COLUMN -- MEAN, MEDIAN, SKEWNESS")
log("=" * 70)
amount_mean = df["amount"].mean()
amount_median = df["amount"].median()
amount_skew = df["amount"].skew()
log(f"Mean:     ${amount_mean:,.2f}")
log(f"Median:   ${amount_median:,.2f}")
log(f"Skewness: {amount_skew:.2f}")
log()

# ---------------------------------------------------------------------------
# 11. Grouped amount stats by txn_type (sorted by mean, highest first)
# ---------------------------------------------------------------------------

log("=" * 70)
log("AMOUNT BY TXN_TYPE (COUNT, MEAN, MEDIAN)")
log("=" * 70)
grouped = df.groupby("txn_type")["amount"].agg(["count", "mean", "median"]).round(2)
grouped = grouped.sort_values("mean", ascending=False)
log(grouped.to_string())
log()

# ---------------------------------------------------------------------------
# 12. Correlation matrix: shares, price, amount
# ---------------------------------------------------------------------------

log("=" * 70)
log("CORRELATION MATRIX -- SHARES, PRICE, AMOUNT")
log("=" * 70)
corr = df[["shares", "price", "amount"]].corr().round(2)
log(corr.to_string())
log()

# Identify the three strongest correlations, excluding self-correlation pairs
corr_pairs = []
cols = corr.columns.tolist()
for i in range(len(cols)):
    for j in range(i + 1, len(cols)):
        corr_pairs.append((cols[i], cols[j], corr.iloc[i, j]))
corr_pairs.sort(key=lambda pair: abs(pair[2]), reverse=True)

log("Three strongest correlations:")
for col_a, col_b, value in corr_pairs[:3]:
    log(f"  {col_a} - {col_b}: {value:.2f}")
log()

# ---------------------------------------------------------------------------
# 13. Negative shares by txn_type (min, max, negative count)
# ---------------------------------------------------------------------------

log("=" * 70)
log("SHARES -- MIN, MAX, AND NEGATIVE COUNT BY TXN_TYPE")
log("=" * 70)
shares_by_type = df.groupby("txn_type")["shares"].agg(
    min="min",
    max="max",
    negative_count=lambda s: (s < 0).sum(),
)
log(shares_by_type.to_string())
log()

# ---------------------------------------------------------------------------
# 14. Shape sanity check (not part of the saved text profile -- console only)
# ---------------------------------------------------------------------------

if df.shape != EXPECTED_SHAPE:
    print("=" * 70)
    print("WARNING: DataFrame shape does not match the expected shape!")
    print(f"Expected: {EXPECTED_SHAPE}  |  Actual: {df.shape}")
    print("=" * 70)

# ---------------------------------------------------------------------------
# 15. Charts
# ---------------------------------------------------------------------------

# Histogram of amount with mean/median lines
plt.figure(figsize=(10, 6))
plt.hist(df["amount"], bins=50, color="#4C72B0", edgecolor="white")
plt.axvline(amount_mean, color="red", linestyle="--", linewidth=2,
            label=f"Mean: ${amount_mean:,.2f}")
plt.axvline(amount_median, color="green", linestyle="--", linewidth=2,
            label=f"Median: ${amount_median:,.2f}")
plt.title("Distribution of Transaction Amount")
plt.xlabel("Amount ($)")
plt.ylabel("Frequency")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "hist_amount.png"), dpi=150)
plt.close()

# Horizontal box plot of amount by txn_type
plt.figure(figsize=(10, 6))
txn_order = df.groupby("txn_type")["amount"].median().sort_values(ascending=False).index
data_by_type = [df.loc[df["txn_type"] == t, "amount"] for t in txn_order]
plt.boxplot(data_by_type, labels=txn_order, vert=False)
plt.title("Transaction Amount by Type")
plt.xlabel("Amount ($)")
plt.ylabel("Transaction Type")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "box_amount_by_type.png"), dpi=150)
plt.close()

# Scatter plot of shares vs. amount, colored by txn_type
plt.figure(figsize=(10, 6))
txn_types = df["txn_type"].unique()
colors = plt.cm.tab10(np.linspace(0, 1, len(txn_types)))
for txn_type, color in zip(txn_types, colors):
    subset = df[df["txn_type"] == txn_type]
    plt.scatter(subset["shares"], subset["amount"], s=8, alpha=0.5,
                color=color, label=txn_type)
plt.title("Shares vs. Amount by Transaction Type")
plt.xlabel("Shares")
plt.ylabel("Amount ($)")
plt.legend(markerscale=2, loc="best")
plt.tight_layout()
plt.savefig(os.path.join(CHARTS_DIR, "scatter_shares_amount.png"), dpi=150)
plt.close()

print(f"\nCharts saved to {CHARTS_DIR}/")

# ---------------------------------------------------------------------------
# 16. Save the plain-text summary (items 2-13)
# ---------------------------------------------------------------------------

with open(PROFILE_PATH, "w") as f:
    f.write("\n".join(profile_lines))

print(f"Profile summary saved to {PROFILE_PATH}")
 