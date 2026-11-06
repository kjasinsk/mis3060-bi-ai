"""
02_design_questions.py

HW6 Part C: the pandas evidence behind the four design answers in
powerbi/measures.md. Every number quoted in Part C is printed here.

Usage:  python hw06/scripts/02_design_questions.py [--data path/to/clean/csvs]

Author: Kaitlyn Jasinski
"""

import argparse
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = REPO / "Data" / "Wildcat_Capital_Clean"


def wavg(df):
    return (df["aum"] * df["active_alpha_ytd"]).sum() / df["aum"].sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    d = ap.parse_args().data

    snap = pd.read_csv(d / "fact_portfolio_snapshot.csv", parse_dates=["snapshot_date"])
    fees = pd.read_csv(d / "fact_fees.csv", parse_dates=["fee_date"])
    txn = pd.read_csv(d / "fact_transactions.csv", parse_dates=["txn_date"])
    client = pd.read_csv(d / "dim_client.csv")
    tier = client.set_index("client_id")["client_tier"]
    snap["client_tier"] = snap["client_id"].map(tier)
    txn["client_tier"] = txn["client_id"].map(tier)
    last_date = snap["snapshot_date"].max()

    # ------------------------------------------------------------------ (a)
    print("(a) Ending AUM vs SUMX over clients")
    ending = snap.loc[snap["snapshot_date"] == last_date, "aum"].sum()
    own_last = snap.loc[snap.groupby("client_id")["snapshot_date"].idxmax()]
    sumx = own_last["aum"].sum()
    gone = own_last[own_last["snapshot_date"] < last_date]
    active = client.set_index("client_id").loc[gone["client_id"], "is_active"]
    print(f"    Ending AUM (one date, {last_date.date()}):       ${ending:,.2f}")
    print(f"    SUMX(VALUES(client_id), [Ending AUM]):     ${sumx:,.2f}")
    print(f"    difference:                                ${sumx - ending:,.2f}")
    print(f"    clients whose last snapshot is before {last_date.date()}: {len(gone)} "
          f"(last seen {gone['snapshot_date'].min().date()} to {gone['snapshot_date'].max().date()}), "
          f"their final balances sum to ${gone['aum'].sum():,.2f}; is_active=False for {int((~active).sum())} of them")
    assert abs((sumx - ending) - gone["aum"].sum()) < 0.01

    # ------------------------------------------------------------------ (b)
    print("\n(b) 2024 Fee Yield vs Effective Fee Rate")
    s24 = snap[snap["snapshot_date"].dt.year == 2024]
    f24 = fees[fees["fee_date"].dt.year == 2024]
    fee_yield = f24["amount"].sum() * 12 * 10000 / s24["aum"].sum()
    eff_rate = f24["amount"].sum() * 12 * 10000 / f24["aum_basis"].sum()
    print(f"    Fee Yield (bps)          = {fee_yield:.2f}   (denominator: snapshot aum ${s24['aum'].sum():,.2f})")
    print(f"    Effective Fee Rate (bps) = {eff_rate:.2f}   (denominator: fee aum_basis ${f24['aum_basis'].sum():,.2f})")
    m = s24.merge(f24, left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"],
                  how="left", indicator=True)
    both, nofee = m[m["_merge"] == "both"], m[m["_merge"] == "left_only"]
    print(f"    snapshot rows 2024: {len(s24):,}; with a fee row: {len(both):,}; with NO fee row: {len(nofee):,} "
          f"({len(nofee) / len(s24):.1%})")
    print(f"    fee rows with no snapshot: {len(f24) - len(both)}")
    print(f"    where both exist, max |aum - aum_basis| = {(both['aum'] - both['aum_basis']).abs().max():.2f}")
    print(f"    summed aum of snapshot rows with no fee: ${nofee['aum'].sum():,.2f} "
          f"({nofee['aum'].sum() / s24['aum'].sum():.1%} of the Fee Yield denominator)")
    print(f"    clients affected: {nofee['client_id'].nunique():,} of {s24['client_id'].nunique():,}; "
          f"clients with no fee in ALL 12 months: {(nofee.groupby('client_id').size() == 12).sum()}")
    print(f"    Fee Yield on matched rows only = "
          f"{both['amount'].sum() * 12 * 10000 / both['aum'].sum():.2f} bps (= Effective Fee Rate)")
    yr = snap.merge(fees, left_on=["client_id", "snapshot_date"], right_on=["client_id", "fee_date"],
                    how="left", indicator=True)
    print("    snapshot rows with no fee, by year:",
          yr[yr["_merge"] == "left_only"].groupby("year").size().to_dict())

    # ------------------------------------------------------------------ (c)
    print("\n(c) AUM-Weighted Alpha at the last snapshot")
    last = snap[snap["snapshot_date"] == last_date]
    clean = last[last["is_return_suspect"] == 0]
    sus = last[last["is_return_suspect"] == 1]
    print(f"    rows at {last_date.date()}: {len(last):,}; suspect: {len(sus)}")
    print(f"    weighted, suspects excluded (the measure): {wavg(clean):.4%}")
    print(f"    simple mean, suspects excluded:            {clean['active_alpha_ytd'].mean():.4%}")
    print(f"    weighted, suspects included:               {wavg(last):.4%}")
    print(f"    simple mean, suspects included:            {last['active_alpha_ytd'].mean():.4%}")
    print(f"    suspect rows: alpha from {sus['active_alpha_ytd'].min():.1%} to {sus['active_alpha_ytd'].max():.1%}, "
          f"return_ytd up to {sus['return_ytd'].max():.1%}")
    s24c = s24[s24["is_return_suspect"] == 0]
    print(f"    if every 2024 month is mixed in (wrong): {wavg(s24c):.4%}")
    print("    weighted alpha by 2024 month (YTD builds up):",
          {mo: round(wavg(g), 4) for mo, g in s24c.groupby("month")})

    # ------------------------------------------------------------------ (d)
    print("\n(d) 2024 Organic Growth Rate vs AUM YoY %, by tier")
    t24 = txn[txn["txn_date"].dt.year == 2024]
    prev = snap["snapshot_date"][snap["snapshot_date"].dt.year == 2023].max()
    rows = []
    for t in ["Retail", "HNW", "UHNW"]:
        tt = t24[t24["client_tier"] == t]
        net = tt.loc[tt["txn_type"] == "Deposit", "amount"].sum() - tt.loc[tt["txn_type"] == "Withdrawal", "amount"].sum()
        ly = snap.loc[(snap["snapshot_date"] == prev) & (snap["client_tier"] == t), "aum"].sum()
        end = snap.loc[(snap["snapshot_date"] == last_date) & (snap["client_tier"] == t), "aum"].sum()
        n_ly = snap.loc[(snap["snapshot_date"] == prev) & (snap["client_tier"] == t), "client_id"].nunique()
        n_end = snap.loc[(snap["snapshot_date"] == last_date) & (snap["client_tier"] == t), "client_id"].nunique()
        rows.append({"tier": t, "net_flows_$M": net / 1e6, "aum_ly_$M": ly / 1e6, "aum_end_$M": end / 1e6,
                     "aum_change_$M": (end - ly) / 1e6, "change_not_from_flows_$M": (end - ly - net) / 1e6,
                     "organic_growth": net / ly, "aum_yoy": (end - ly) / ly,
                     "flows_share_of_change": net / (end - ly), "clients_ly": n_ly, "clients_end": n_end})
    df = pd.DataFrame(rows).set_index("tier")
    pd.set_option("display.width", 200)
    print(df.round(4).to_string())
    print(f"    all tiers: net flows ${df['net_flows_$M'].sum():,.1f}M of ${df['aum_change_$M'].sum():,.1f}M AUM change")


if __name__ == "__main__":
    main()
