"""
00_make_extract.py

HW7 Part A, item 5: build data/growth_extract.csv for prototyping the
"flows vs. market" visuals with Claude BEFORE building them in Power BI.

Built with pandas straight from the Wildcat Capital Clean CSVs (the same files
my Assignment 6 script reads). Nothing comes from Power BI.

Grain: one row per year x client tier x region (5 x 3 x 5 = 75 rows).

  region        dim_advisor[region], reached through each fact row's own
                advisor_id, which is the path the Power BI model uses
                (fact_portfolio_snapshot[advisor_id] -> dim_advisor and
                fact_transactions[advisor_id] -> dim_advisor)
  ending_aum    BALANCE: sum of aum on the December month-end snapshot of the
                year (snapshots are dated the 1st, so Dec = YYYY-12-01)
  ending_aum_ly BALANCE: the same balance one year earlier (blank for 2020)
  net_flows     FLOW: Deposits minus Withdrawals summed over the calendar year
                (same definition as the Net Flows measure)
  market_change ending_aum - ending_aum_ly - net_flows (blank for 2020)

Usage (from anywhere):
    python hw07/scripts/00_make_extract.py
    python hw07/scripts/00_make_extract.py --data path/to/clean/csvs

Author: Kaitlyn Jasinski
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent
REPO = HW_DIR.parent
DEFAULT_DATA = REPO / "Data" / "Wildcat_Capital_Clean"
OUT = HW_DIR / "data" / "growth_extract.csv"

YEARS = [2020, 2021, 2022, 2023, 2024]
TIERS = ["Retail", "HNW", "UHNW"]


def load(data_dir: Path):
    snap = pd.read_csv(data_dir / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
    txn = pd.read_csv(data_dir / "fact_transactions.csv", parse_dates=["txn_date"])
    client = pd.read_csv(data_dir / "dim_client.csv")
    advisor = pd.read_csv(data_dir / "dim_advisor.csv")

    tier = client.set_index("client_id")["client_tier"]
    region = advisor.set_index("advisor_id")["region"]
    for df in (snap, txn):
        df["client_tier"] = df["client_id"].map(tier)
        df["region"] = df["advisor_id"].map(region)
        # an unmatched key would silently drop money out of the extract
        assert df["client_tier"].notna().all(), "fact row with no matching client"
        assert df["region"].notna().all(), "fact row with no matching advisor"
    return snap, txn, sorted(advisor["region"].unique())


def build(snap, txn, regions):
    # the full 75-row grid, so a cell with no data still shows up (and keeps its row)
    grid = pd.MultiIndex.from_product([YEARS, TIERS, regions], names=["year", "client_tier", "region"])
    keys = ["year", "client_tier", "region"]

    # BALANCE: December snapshot of each year
    dec = snap[snap["snapshot_date"].dt.month == 12].copy()
    dec["year"] = dec["snapshot_date"].dt.year
    ending = dec.groupby(keys)["aum"].sum().reindex(grid)

    # BALANCE one year earlier: shift the December balances forward a year
    ly = ending.copy()
    ly.index = ly.index.set_levels(ly.index.levels[0] + 1, level="year")
    ending_ly = ly.reindex(grid)            # 2020 has no 2019 row -> NaN (blank)

    # FLOW: deposits minus withdrawals over the calendar year
    t = txn[txn["txn_type"].isin(["Deposit", "Withdrawal"])].copy()
    t["year"] = t["txn_date"].dt.year
    t["signed"] = np.where(t["txn_type"] == "Deposit", t["amount"], -t["amount"])
    flows = t.groupby(keys)["signed"].sum().reindex(grid)   # no flows at all -> blank, like DAX

    out = pd.DataFrame({"ending_aum": ending, "ending_aum_ly": ending_ly, "net_flows": flows})
    out["market_change"] = out["ending_aum"] - out["ending_aum_ly"] - out["net_flows"]
    out = out.reset_index()
    out["client_tier"] = pd.Categorical(out["client_tier"], TIERS, ordered=True)
    return out.sort_values(keys).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="folder with the clean CSVs")
    args = ap.parse_args()

    snap, txn, regions = load(args.data)
    out = build(snap, txn, regions)

    # checks
    assert len(out) == len(YEARS) * len(TIERS) * len(regions) == 75, f"expected 75 rows, got {len(out)}"
    assert out.loc[out["year"] == 2020, ["ending_aum_ly", "market_change"]].isna().all().all()
    later = out[out["year"] > 2020]
    assert later[["ending_aum", "ending_aum_ly", "net_flows", "market_change"]].notna().all().all(), \
        "a year x tier x region cell has no December balance or no flows"
    # the 75 cells add back up to the firm totals (no row lost or double counted)
    # every year, not just 2024 (Claude Code review finding #3)
    for yr in YEARS:
        dec_total = snap.loc[snap["snapshot_date"] == f"{yr}-12-01", "aum"].sum()
        assert abs(out.loc[out["year"] == yr, "ending_aum"].sum() - dec_total) < 0.01, f"{yr} balance"
        t_yr = txn[(txn["txn_date"].dt.year == yr) & txn["txn_type"].isin(["Deposit", "Withdrawal"])]
        flow_total = (t_yr.loc[t_yr["txn_type"] == "Deposit", "amount"].sum()
                      - t_yr.loc[t_yr["txn_type"] == "Withdrawal", "amount"].sum())
        assert abs(out.loc[out["year"] == yr, "net_flows"].sum() - flow_total) < 0.01, f"{yr} flows"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, float_format="%.2f")
    print(f"wrote {len(out)} rows -> {OUT.relative_to(REPO)}")

    y = out[out["year"] == 2024][["ending_aum", "ending_aum_ly", "net_flows", "market_change"]].sum()
    print("2024 firm totals (sum of the 15 tier x region rows):")
    for k, v in y.items():
        print(f"  {k:<14} ${v:,.2f}")


if __name__ == "__main__":
    main()
