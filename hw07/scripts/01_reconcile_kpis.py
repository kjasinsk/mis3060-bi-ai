"""
01_reconcile_kpis.py

HW7 Part D: extend my Assignment 6 reconciliation (hw06/scripts/01_reconcile_measures.py)
to the numbers shown on the two-page growth dashboard, for 2024.

  1. pandas side   built only from the Wildcat Capital Clean CSVs; nothing from Power BI
  2. Power BI side read from hw07/reports/powerbi_values.csv (measure, slice, value),
                   exported from DAX query view (query in reports/powerbi_values_query.dax)
  3. output        hw07/reports/kpi_reconciliation.csv
                   (measure, slice, powerbi_value, pandas_value, abs_diff, match)
                   same columns and tolerances as Assignment 6
  4. extract check the 2024 rows of data/growth_extract.csv, summed to tier and to region,
                   must equal the tier and region rows of the reconciliation

What is reconciled (2024)
  * Page 1 cards, firm level: Ending AUM, Ending AUM LY, AUM YoY %, Net Flows,
    Market Change, Organic Growth Rate
  * the flows / market split for each client tier and each region:
    Ending AUM, Ending AUM LY, Net Flows, Market Change
  * Page 2 cards for one tier (Retail): Ending AUM, Ending Clients, Avg AUM per Client,
    Fee Yield (bps), AUM-Weighted Alpha, Alpha Signal

New compared with Assignment 6
  * a Slice can also carry a region. Region is dim_advisor[region], reached through each
    fact row's own advisor_id (fact_portfolio_snapshot[advisor_id] and
    fact_transactions[advisor_id] -> dim_advisor), the same path as the Power BI model
  * Market Change = (Ending AUM - Ending AUM LY) - Net Flows

Tolerance: 0.01 for currency, 0.0001 for ratios / bps, exact for counts and text.
Stops with an AssertionError if any required row is missing or does not match.

Usage (from the repo root or anywhere):
    python hw07/scripts/01_reconcile_kpis.py
    python hw07/scripts/01_reconcile_kpis.py --data path/to/clean/csvs

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
EXTRACT = HW_DIR / "data" / "growth_extract.csv"
DEFAULT_DATA = REPO / "Data" / "Wildcat_Capital_Clean"

TOL_CURRENCY = 0.01
TOL_RATIO = 0.0001

MEASURES = {
    "Ending AUM": "currency",
    "Ending AUM LY": "currency",
    "AUM YoY %": "ratio",
    "Net Flows": "currency",
    "Market Change": "currency",
    "Organic Growth Rate": "ratio",
    "Ending Clients": "count",
    "Avg AUM per Client": "currency",
    "Fee Yield (bps)": "ratio",
    "AUM-Weighted Alpha": "ratio",
    "Alpha Signal": "text",
}

TIERS = ["Retail", "HNW", "UHNW"]
PAGE2_TIER = "Retail"

FIRM_CARDS = ["Ending AUM", "Ending AUM LY", "AUM YoY %", "Net Flows", "Market Change",
              "Organic Growth Rate"]
SPLIT = ["Ending AUM", "Ending AUM LY", "Net Flows", "Market Change"]
PAGE2_CARDS = ["Ending AUM", "Ending Clients", "Avg AUM per Client", "Fee Yield (bps)",
               "AUM-Weighted Alpha", "Alpha Signal"]


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load(data_dir: Path):
    snap = pd.read_csv(data_dir / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
    fees = pd.read_csv(data_dir / "fact_fees.csv", parse_dates=["fee_date"])
    txn = pd.read_csv(data_dir / "fact_transactions.csv", parse_dates=["txn_date"])
    client = pd.read_csv(data_dir / "dim_client.csv")
    advisor = pd.read_csv(data_dir / "dim_advisor.csv")
    dates = pd.read_csv(data_dir / "dim_date.csv", parse_dates=["date"])

    tier = client.set_index("client_id")["client_tier"]
    region = advisor.set_index("advisor_id")["region"]
    for df in (snap, fees, txn):
        df["client_tier"] = df["client_id"].map(tier)
        assert df["client_tier"].notna().all(), "fact row with no matching client"
    for df in (snap, txn):                      # the two facts the region visuals use
        df["region"] = df["advisor_id"].map(region)
        assert df["region"].notna().all(), "fact row with no matching advisor"
    return snap, fees, txn, sorted(advisor["region"].unique()), dates


# ---------------------------------------------------------------------------
# A slice = a set of dim_date dates + an optional client tier + an optional region
# ---------------------------------------------------------------------------
class Slice:
    def __init__(self, name, dates, tier=None, region=None):
        self.name = name
        self.dates = pd.DatetimeIndex(dates)
        self.tier = tier
        self.region = region

    def shifted(self, all_dates, years=0):
        """SAMEPERIODLASTYEAR: move the dates back, keep only dates in dim_date."""
        moved = self.dates - pd.DateOffset(years=years)
        moved = moved[moved.isin(all_dates)]
        return Slice(self.name, moved, self.tier, self.region)


def rows(df, date_col, sl: Slice):
    out = df[df[date_col].isin(sl.dates)]
    if sl.tier is not None:
        out = out[out["client_tier"] == sl.tier]
    if sl.region is not None:
        assert "region" in out.columns, "region slice used on a fact without advisor_id"
        out = out[out["region"] == sl.region]
    return out


def last_snapshot(snap, sl):
    """Rows of the latest snapshot date with data in the slice (LASTNONBLANK)."""
    s = rows(snap, "snapshot_date", sl)
    return s if s.empty else s[s["snapshot_date"] == s["snapshot_date"].max()]


def div(a, b):
    if a is None or b is None or pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / b


def growth(cur, prev):
    if pd.isna(prev):
        return np.nan
    return div((0 if pd.isna(cur) else cur) - prev, prev)


def ending_aum(snap, sl):
    s = last_snapshot(snap, sl)
    return s["aum"].sum() if len(s) else np.nan


def net_flows(txn, sl):
    t = rows(txn, "txn_date", sl)
    t = t[t["txn_type"].isin(["Deposit", "Withdrawal"])]
    if t.empty:
        return np.nan
    return (t.loc[t["txn_type"] == "Deposit", "amount"].sum()
            - t.loc[t["txn_type"] == "Withdrawal", "amount"].sum())


def weighted_alpha(snap, sl):
    s = last_snapshot(snap, sl)
    s = s[s["is_return_suspect"] == 0]
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


def compute_all(snap, fees, txn, all_dates, sl: Slice):
    ly = sl.shifted(all_dates, years=1)
    v = {}
    v["Ending AUM"] = ending_aum(snap, sl)
    last = last_snapshot(snap, sl)
    v["Ending Clients"] = last["client_id"].nunique() if len(last) else np.nan
    v["Avg AUM per Client"] = div(v["Ending AUM"], v["Ending Clients"])
    v["Ending AUM LY"] = ending_aum(snap, ly)
    v["AUM YoY %"] = growth(v["Ending AUM"], v["Ending AUM LY"])
    v["Net Flows"] = net_flows(txn, sl)
    # DAX: (BLANK - x) - y works like 0 - x - y; with no LY the visuals show it, so keep NaN only
    # when there is no LY balance at all (the measure is not shown for 2020)
    v["Market Change"] = (np.nan if pd.isna(v["Ending AUM LY"]) else
                          (0 if pd.isna(v["Ending AUM"]) else v["Ending AUM"]) - v["Ending AUM LY"]
                          - (0 if pd.isna(v["Net Flows"]) else v["Net Flows"]))
    v["Organic Growth Rate"] = div(v["Net Flows"], v["Ending AUM LY"])
    if sl.region is None:                       # fees and alpha are only shown without a region
        f = rows(fees, "fee_date", sl)
        s = rows(snap, "snapshot_date", sl)
        total_fees = f["amount"].sum() if len(f) else np.nan
        v["Fee Yield (bps)"] = div(total_fees * 12 * 10000, s["aum"].sum()) if len(s) else np.nan
        v["AUM-Weighted Alpha"] = weighted_alpha(snap, sl)
        v["Alpha Signal"] = alpha_signal(v["AUM-Weighted Alpha"])
    return v


def build_slices(all_dates, regions):
    d24 = all_dates[all_dates.year == 2024]
    out = [("year=2024", Slice("year=2024", d24), FIRM_CARDS)]
    for t in TIERS:
        name = f"year=2024|tier={t}"
        wanted = list(dict.fromkeys(SPLIT + (PAGE2_CARDS if t == PAGE2_TIER else [])))
        out.append((name, Slice(name, d24, tier=t), wanted))
    for r in regions:
        name = f"year=2024|region={r}"
        out.append((name, Slice(name, d24, region=r), SPLIT))
    return out


# ---------------------------------------------------------------------------
# Compare (same rules as Assignment 6)
# ---------------------------------------------------------------------------
def to_number(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).strip().replace(",", "").replace("$", "")
    return np.nan if s == "" else float(s)


def compare(measure, pbi, pdv):
    kind = MEASURES[measure]
    if kind == "text":
        a = "" if pbi is None or pd.isna(pbi) else str(pbi).strip()
        b = "" if pdv is None or pd.isna(pdv) else str(pdv).strip()
        return a, b, (0.0 if a == b else np.nan), a == b
    a, b = to_number(pbi), to_number(pdv)
    if np.isnan(a) and np.isnan(b):
        return a, b, 0.0, True
    if np.isnan(a) or np.isnan(b):
        return a, b, np.nan, False
    diff = abs(a - b)
    tol = {"currency": TOL_CURRENCY, "ratio": TOL_RATIO, "count": 0}[kind]
    return a, b, diff, diff <= tol


def extract_check(rec):
    """2024 rows of growth_extract.csv summed to tier and to region must match the
    reconciled tier / region rows (pandas side, which already matches Power BI)."""
    ext = pd.read_csv(EXTRACT)
    e24 = ext[ext["year"] == 2024]
    col = {"Ending AUM": "ending_aum", "Ending AUM LY": "ending_aum_ly",
           "Net Flows": "net_flows", "Market Change": "market_change"}
    checks = []
    for dim, key in (("client_tier", "tier"), ("region", "region")):
        sums = e24.groupby(dim)[list(col.values())].sum()
        for member, row in sums.iterrows():
            for m, c in col.items():
                target = rec[(rec.measure == m) & (rec.slice == f"year=2024|{key}={member}")]
                assert len(target) == 1, f"no reconciliation row for {m} {key}={member}"
                diff = abs(row[c] - float(target.iloc[0].powerbi_value))
                checks.append({"level": key, "member": member, "measure": m,
                               "extract_sum": row[c], "reconciled_value": target.iloc[0].powerbi_value,
                               "abs_diff": diff, "match": diff <= TOL_CURRENCY})
    chk = pd.DataFrame(checks)
    chk.to_csv(REPORTS / "extract_check.csv", index=False)
    print(f"extract check: {int(chk['match'].sum())} of {len(chk)} tier/region sums match "
          f"-> reports/extract_check.csv")
    assert chk["match"].all(), chk[~chk["match"]].to_string(index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="folder with the clean CSVs")
    args = ap.parse_args()

    snap, fees, txn, regions, dates = load(args.data)
    all_dates = pd.DatetimeIndex(dates["date"].sort_values())
    assert len(regions) == 5, f"expected 5 regions, got {regions}"

    # 1. pandas side
    prow = []
    for name, sl, wanted in build_slices(all_dates, regions):
        vals = compute_all(snap, fees, txn, all_dates, sl)
        prow += [{"measure": m, "slice": name, "pandas_value": vals[m]} for m in wanted]
    pdf = pd.DataFrame(prow)
    print(f"pandas: {len(pdf)} measure/slice values")

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
    extra = pbi.merge(pdf, on=["measure", "slice"], how="left", indicator=True)
    extra = extra[extra["_merge"] == "left_only"]
    if not extra.empty:
        print(f"note: {len(extra)} Power BI rows not reconciled (not required):")
        print(extra[["measure", "slice"]].to_string(index=False))

    # 3. compare
    out = []
    for r in merged.itertuples(index=False):
        a, b, diff, ok = compare(r.measure, r.value, r.pandas_value)
        out.append({"measure": r.measure, "slice": r.slice, "powerbi_value": a,
                    "pandas_value": b, "abs_diff": diff, "match": bool(ok)})
    rec = pd.DataFrame(out)
    REPORTS.mkdir(parents=True, exist_ok=True)
    rec.to_csv(REPORTS / "kpi_reconciliation.csv", index=False)
    print(f"reconciliation: {int(rec['match'].sum())} of {len(rec)} rows match "
          f"-> reports/kpi_reconciliation.csv")
    bad = rec[~rec["match"]]
    if not bad.empty:
        print(bad.to_string(index=False))
    assert bad.empty, f"{len(bad)} rows do not match"

    # the parts add back up: tiers and regions each sum to the firm
    for m in SPLIT:
        firm = float(rec[(rec.measure == m) & (rec.slice == "year=2024")].pandas_value.iloc[0]) \
            if m in FIRM_CARDS else None
        for key in ("tier", "region"):
            parts = rec[(rec.measure == m) & rec.slice.str.contains(f"\\|{key}=")]
            if firm is not None:
                assert abs(parts.pandas_value.astype(float).sum() - firm) < TOL_CURRENCY, \
                    f"{m}: {key} rows do not add up to the firm total"
    print("tier rows and region rows each add up to the firm totals")

    # 4. extract check
    extract_check(rec)


if __name__ == "__main__":
    main()
