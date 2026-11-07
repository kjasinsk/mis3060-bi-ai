"""
01_reconcile_measures.py

HW6 Part B: recompute every DAX measure in the HW6 library independently in
pandas, straight from the Wildcat Capital Clean CSVs, and compare each one to
the number Power BI shows.

  1. pandas side   built only from the CSVs; nothing is read from Power BI
  2. Power BI side read from hw06/reports/powerbi_values.csv (measure, slice, value),
                   exported from DAX query view (query saved in
                   hw06/reports/powerbi_values_query.dax)
  3. output        hw06/reports/measure_reconciliation.csv
                   (measure, slice, powerbi_value, pandas_value, abs_diff, match)

Tolerance: 0.01 for currency, 0.0001 for ratios / bps, exact for counts and text.
Stops with an AssertionError if any required row is missing or does not match.

How the pandas side copies the DAX filter context
  * "last snapshot" = the latest snapshot_date that has at least one row in the
    slice (what LASTNONBLANK(dim_date[date], COUNTROWS(fact_portfolio_snapshot))
    returns). For the whole model that is 2024-12-01.
  * "LY" / "PM" = the same slice with every date moved back one year / one month,
    keeping only dates that exist in dim_date (2020-01-01 to 2024-12-31). That is
    what SAMEPERIODLASTYEAR and DATEADD do.
  * A client-tier slice filters dim_client, so it filters all three fact tables
    through client_id.

Usage (from anywhere):
    python hw06/scripts/01_reconcile_measures.py
    python hw06/scripts/01_reconcile_measures.py --data path/to/clean/csvs

Author: Kaitlyn Jasinski
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent
REPO = HW_DIR.parent
REPORTS = HW_DIR / "reports"
DEFAULT_DATA = REPO / "Data" / "Wildcat_Capital_Clean"

TOL_CURRENCY = 0.01
TOL_RATIO = 0.0001

# measure name -> kind (decides the tolerance)
MEASURES = {
    "AUM (naive SUM)": "currency",
    "Ending AUM": "currency",
    "Ending Clients": "count",
    "Avg AUM per Client": "currency",
    "Ending AUM LY": "currency",
    "AUM YoY %": "ratio",
    "Ending AUM PM": "currency",
    "AUM MoM %": "ratio",
    "Avg Monthly AUM": "currency",
    "Fee Yield (bps)": "ratio",
    "Organic Growth Rate": "ratio",
    "AUM-Weighted Alpha": "ratio",
    "Alpha Signal": "text",
    "Top 10 Client Share": "ratio",
    # the two base measures from the ICEs, checked so the ratios built on them are trusted
    "Total Fees": "currency",
    "Net Flows": "currency",
}

YEARS = [2020, 2021, 2022, 2023, 2024]
TIERS = ["Retail", "HNW", "UHNW"]

# Required slices (assignment Part B)
BY_YEAR = ["AUM (naive SUM)", "Ending AUM", "Ending AUM LY", "AUM YoY %", "Avg Monthly AUM",
           "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha", "Alpha Signal"]
BY_TIER_2024 = ["Ending AUM", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %",
                "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha",
                "Alpha Signal", "Top 10 Client Share"]
DEC_2024 = ["Ending AUM", "Ending AUM PM", "AUM MoM %"]


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load(data_dir: Path):
    snap = pd.read_csv(data_dir / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
    fees = pd.read_csv(data_dir / "fact_fees.csv", parse_dates=["fee_date"])
    txn = pd.read_csv(data_dir / "fact_transactions.csv", parse_dates=["txn_date"])
    client = pd.read_csv(data_dir / "dim_client.csv")
    dates = pd.read_csv(data_dir / "dim_date.csv", parse_dates=["date"])

    tier = client.set_index("client_id")["client_tier"]
    for df in (snap, fees, txn):
        df["client_tier"] = df["client_id"].map(tier)
        assert df["client_tier"].notna().all(), "fact row with no matching client"
    return snap, fees, txn, client, dates


# ---------------------------------------------------------------------------
# A slice = a set of calendar dates (from dim_date) + an optional client tier
# ---------------------------------------------------------------------------
class Slice:
    def __init__(self, name, dates, tier=None):
        self.name = name
        self.dates = pd.DatetimeIndex(dates)
        self.tier = tier

    def shifted(self, all_dates, years=0, months=0):
        """Move every date back, keep only dates that exist in dim_date
        (SAMEPERIODLASTYEAR / DATEADD behaviour)."""
        moved = self.dates - pd.DateOffset(years=years, months=months)
        moved = moved[moved.isin(all_dates)]
        return Slice(self.name, moved, self.tier)


def rows(df, date_col, sl: Slice):
    out = df[df[date_col].isin(sl.dates)]
    if sl.tier is not None:
        out = out[out["client_tier"] == sl.tier]
    return out


def last_snapshot(snap, sl):
    """Rows of the latest snapshot date that has data in the slice (LASTNONBLANK)."""
    s = rows(snap, "snapshot_date", sl)
    if s.empty:
        return s
    return s[s["snapshot_date"] == s["snapshot_date"].max()]


def div(a, b):
    """DIVIDE(): blank (NaN) when either side is blank or the denominator is 0."""
    if a is None or b is None or pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / b


def growth(cur, prev):
    """DIVIDE([cur] - [prev], [prev]). A blank [cur] counts as 0 in the
    subtraction, because in DAX BLANK - x = -x, so the result is -100%."""
    if pd.isna(prev):
        return np.nan
    return div((0 if pd.isna(cur) else cur) - prev, prev)


# ---------------------------------------------------------------------------
# The measures, one pandas function each
# ---------------------------------------------------------------------------
def naive_sum(snap, sl):
    s = rows(snap, "snapshot_date", sl)
    return s["aum"].sum() if len(s) else np.nan


def ending_aum(snap, sl):
    s = last_snapshot(snap, sl)
    return s["aum"].sum() if len(s) else np.nan


def ending_clients(snap, sl):
    s = last_snapshot(snap, sl)
    return s["client_id"].nunique() if len(s) else np.nan


def total_fees(fees, sl):
    f = rows(fees, "fee_date", sl)
    return f["amount"].sum() if len(f) else np.nan


def net_flows(txn, sl):
    t = rows(txn, "txn_date", sl)
    t = t[t["txn_type"].isin(["Deposit", "Withdrawal"])]
    if t.empty:
        return np.nan                           # DAX: BLANK - BLANK = BLANK, not 0
    dep = t.loc[t["txn_type"] == "Deposit", "amount"].sum()
    wd = t.loc[t["txn_type"] == "Withdrawal", "amount"].sum()
    return dep - wd


def weighted_alpha(snap, sl):
    s = last_snapshot(snap, sl)                 # last date in the slice, all rows
    s = s[s["is_return_suspect"] == 0]          # then drop suspect returns
    if s.empty:
        return np.nan
    return div((s["aum"] * s["active_alpha_ytd"]).sum(), s["aum"].sum())


def alpha_signal(alpha):
    if pd.isna(alpha):
        return ""
    if alpha >= 0.02:
        return "Outperforming"
    if alpha <= -0.02:
        return "Lagging"
    return "In line"


def top10_share(snap, sl):
    s = last_snapshot(snap, sl)
    if s.empty:
        return np.nan
    by_client = s.groupby("client_id")["aum"].sum()
    # keep="all" mirrors DAX TOPN, which returns every client tied at 10th place
    return div(by_client.nlargest(10, keep="all").sum(), by_client.sum())


def compute_all(snap, fees, txn, all_dates, sl: Slice):
    """Every measure for one slice. Returns {measure: value}."""
    ly = sl.shifted(all_dates, years=1)
    pm = sl.shifted(all_dates, months=1)

    s = rows(snap, "snapshot_date", sl)
    v = {}
    v["AUM (naive SUM)"] = naive_sum(snap, sl)
    v["Ending AUM"] = ending_aum(snap, sl)
    v["Ending Clients"] = ending_clients(snap, sl)
    v["Avg AUM per Client"] = div(v["Ending AUM"], v["Ending Clients"])
    v["Ending AUM LY"] = ending_aum(snap, ly)
    v["AUM YoY %"] = growth(v["Ending AUM"], v["Ending AUM LY"])
    v["Ending AUM PM"] = ending_aum(snap, pm)
    v["AUM MoM %"] = growth(v["Ending AUM"], v["Ending AUM PM"])
    v["Avg Monthly AUM"] = div(s["aum"].sum(), s["snapshot_date"].nunique()) if len(s) else np.nan
    v["Total Fees"] = total_fees(fees, sl)
    v["Net Flows"] = net_flows(txn, sl)
    v["Fee Yield (bps)"] = div(v["Total Fees"] * 12 * 10000, s["aum"].sum()) if len(s) else np.nan
    v["Organic Growth Rate"] = div(v["Net Flows"], v["Ending AUM LY"])
    v["AUM-Weighted Alpha"] = weighted_alpha(snap, sl)
    v["Alpha Signal"] = alpha_signal(v["AUM-Weighted Alpha"])
    v["Top 10 Client Share"] = top10_share(snap, sl)
    return v


def build_slices(all_dates):
    out = [("All", Slice("All", all_dates), list(MEASURES))]
    for y in YEARS:
        out.append((f"year={y}", Slice(f"year={y}", all_dates[all_dates.year == y]), BY_YEAR))
    d24 = all_dates[all_dates.year == 2024]
    for t in TIERS:
        name = f"year=2024|tier={t}"
        out.append((name, Slice(name, d24, tier=t), BY_TIER_2024))
    dec = all_dates[(all_dates.year == 2024) & (all_dates.month == 12)]
    out.append(("month=2024-12", Slice("month=2024-12", dec), DEC_2024))
    return out


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------
def to_number(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).strip().replace(",", "").replace("$", "")
    if s == "":
        return np.nan
    return float(s)


def compare(measure, pbi, pdv):
    kind = MEASURES[measure]
    if kind == "text":
        a = "" if pbi is None or pd.isna(pbi) else str(pbi).strip()
        b = "" if pdv is None or pd.isna(pdv) else str(pdv).strip()
        return a, b, (0.0 if a == b else np.nan), a == b
    a, b = to_number(pbi), to_number(pdv)
    if np.isnan(a) and np.isnan(b):
        return a, b, 0.0, True                     # both blank
    if np.isnan(a) or np.isnan(b):
        return a, b, np.nan, False
    diff = abs(a - b)
    tol = {"currency": TOL_CURRENCY, "ratio": TOL_RATIO, "count": 0}[kind]
    return a, b, diff, diff <= tol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="folder with the clean CSVs")
    args = ap.parse_args()

    snap, fees, txn, client, dates = load(args.data)
    all_dates = pd.DatetimeIndex(dates["date"].sort_values())
    assert all_dates.min() == pd.Timestamp("2020-01-01") and all_dates.max() == pd.Timestamp("2024-12-31")

    # 1. pandas side
    pandas_rows = []
    for slice_name, sl, wanted in build_slices(all_dates):
        vals = compute_all(snap, fees, txn, all_dates, sl)
        for m in wanted:
            pandas_rows.append({"measure": m, "slice": slice_name, "pandas_value": vals[m]})
    pdf = pd.DataFrame(pandas_rows)
    REPORTS.mkdir(parents=True, exist_ok=True)
    pdf.to_csv(REPORTS / "pandas_values.csv", index=False)
    print(f"pandas: {len(pdf)} measure/slice values -> reports/pandas_values.csv")

    # 2. Power BI side
    pbi_path = REPORTS / "powerbi_values.csv"
    if not pbi_path.exists():
        sys.exit(f"Missing {pbi_path}. Export it from DAX query view first (see README).")
    pbi = pd.read_csv(pbi_path, dtype={"value": str}, keep_default_na=False)
    pbi["measure"] = pbi["measure"].str.strip()
    pbi["slice"] = pbi["slice"].str.strip()
    dupes = pbi[pbi.duplicated(["measure", "slice"], keep=False)]
    assert dupes.empty, f"duplicate rows in powerbi_values.csv:\n{dupes}"
    unknown = set(pbi["measure"]) - set(MEASURES)
    assert not unknown, f"unknown measure names in powerbi_values.csv: {unknown}"

    merged = pdf.merge(pbi, on=["measure", "slice"], how="left", indicator=True)
    missing = merged[merged["_merge"] == "left_only"]
    assert missing.empty, f"{len(missing)} required rows missing from powerbi_values.csv:\n" \
                          f"{missing[['measure', 'slice']].to_string(index=False)}"

    # 3. compare
    out = []
    for r in merged.itertuples(index=False):
        a, b, diff, ok = compare(r.measure, r.value, r.pandas_value)
        out.append({"measure": r.measure, "slice": r.slice, "powerbi_value": a,
                    "pandas_value": b, "abs_diff": diff, "match": bool(ok)})
    rec = pd.DataFrame(out)
    rec.to_csv(REPORTS / "measure_reconciliation.csv", index=False)

    n_ok = int(rec["match"].sum())
    print(f"reconciliation: {n_ok} of {len(rec)} rows match -> reports/measure_reconciliation.csv")
    bad = rec[~rec["match"]]
    if not bad.empty:
        print(bad.to_string(index=False))
    assert bad.empty, f"{len(bad)} rows do not match"

    # The naive SUM is wrong in BOTH tools by the same amount
    naive = rec[(rec.measure == "AUM (naive SUM)") & (rec.slice == "All")].iloc[0]
    ending = rec[(rec.measure == "Ending AUM") & (rec.slice == "All")].iloc[0]
    print(f"naive SUM ${naive.pandas_value:,.2f} vs Ending AUM ${ending.pandas_value:,.2f} "
          f"({naive.pandas_value / ending.pandas_value:.1f}x too big, same in Power BI and pandas)")


if __name__ == "__main__":
    main()
