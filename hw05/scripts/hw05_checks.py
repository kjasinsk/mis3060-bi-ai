"""
hw05_checks.py

HW5 Parts A-C: prove the star-schema design in code before building it in
Power BI.

  Part A  every primary key is unique and never blank;
          every foreign key finds its parent (reuses check_referential_integrity
          from HW4), and blank keys appear only where they are legitimate
  Part B  the grain of each fact table is unique
  Part C  lists every numeric fact column with its additivity class, and
          shows WHY with a small numeric demonstration

Usage (from anywhere):
    python hw05/scripts/hw05_checks.py              # instructor release in Data/Wildcat_Capital_Clean
    python hw05/scripts/hw05_checks.py --data hw04/data/clean   # or my own HW4 output

Writes hw05/reports/keys_check.csv, grain_check.csv, measures.csv.
Stops with an AssertionError if any check fails.

Author: Kaitlyn Jasinski
"""

import argparse
import importlib.util
from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent
REPO = HW_DIR.parent
REPORTS = HW_DIR / "reports"

# Reuse HW4's validator (file name starts with a digit, so load it by path)
_spec = importlib.util.spec_from_file_location(
    "hw04_validate", REPO / "hw04" / "scripts" / "03_validate.py")
V = importlib.util.module_from_spec(_spec)
import sys
sys.path.insert(0, str(REPO / "hw04" / "scripts"))
_spec.loader.exec_module(V)
check_referential_integrity = V.check_referential_integrity

# Row counts given in the HW5 brief
EXPECTED_ROWS = {
    "dim_advisor": 25, "dim_benchmark": 8, "dim_client": 2500, "dim_date": 1827,
    "dim_security": 500, "fact_fees": 122197, "fact_portfolio_snapshot": 129547,
    "fact_transactions": 298572,
}

# ---------------------------------------------------------------------------
# Part A: the design being tested
# ---------------------------------------------------------------------------
PRIMARY_KEYS = {
    "dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id",
    "dim_client": "client_id", "dim_date": "date_id", "dim_security": "security_id",
    "fact_fees": "fee_id", "fact_portfolio_snapshot": "snapshot_id",
    "fact_transactions": "txn_id",
}
# dim_date also has a second unique key, `date`, which is what the facts use
ALTERNATE_KEYS = {"dim_date": "date"}

# (table, column, parent table, parent column, blank allowed?)
FOREIGN_KEYS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id", False),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_fees", "client_id", "dim_client", "client_id", False),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_fees", "fee_date", "dim_date", "date", False),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id", False),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date", False),
    ("fact_transactions", "client_id", "dim_client", "client_id", False),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_transactions", "security_id", "dim_security", "security_id", True),
    ("fact_transactions", "txn_date", "dim_date", "date", False),
]
CASH_FLOW_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}  # no security involved

# ---------------------------------------------------------------------------
# Part B: grain = the columns that make one row unique
# ---------------------------------------------------------------------------
GRAIN = {
    "fact_fees": ["client_id", "fee_date"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
    "fact_transactions": ["txn_id"],   # no business key is unique; see star_design.md
}

# ---------------------------------------------------------------------------
# Part C: every numeric column in every fact table
#   role: additive | semi-additive | non-additive | key | date part | flag
# ---------------------------------------------------------------------------
FACT_NUMERIC = [
    ("fact_fees", "fee_id", "key"),
    ("fact_fees", "client_id", "key"),
    ("fact_fees", "advisor_id", "key"),
    ("fact_fees", "aum_basis", "semi-additive"),
    ("fact_fees", "bps_charged", "non-additive"),
    ("fact_fees", "amount", "additive"),
    ("fact_portfolio_snapshot", "snapshot_id", "key"),
    ("fact_portfolio_snapshot", "client_id", "key"),
    ("fact_portfolio_snapshot", "advisor_id", "key"),
    ("fact_portfolio_snapshot", "benchmark_id", "key"),
    ("fact_portfolio_snapshot", "year", "date part"),
    ("fact_portfolio_snapshot", "month", "date part"),
    ("fact_portfolio_snapshot", "aum", "semi-additive"),
    ("fact_portfolio_snapshot", "return_ytd", "non-additive"),
    ("fact_portfolio_snapshot", "benchmark_return_ytd", "non-additive"),
    ("fact_portfolio_snapshot", "active_alpha_ytd", "non-additive"),
    ("fact_portfolio_snapshot", "cash_pct", "non-additive"),
    ("fact_portfolio_snapshot", "is_return_suspect", "flag"),        # instructor release
    ("fact_portfolio_snapshot", "flag_extreme_return", "flag"),      # my HW4 output
    ("fact_portfolio_snapshot", "flag_aum_floor", "flag"),           # my HW4 output
    ("fact_transactions", "txn_id", "key"),
    ("fact_transactions", "client_id", "key"),
    ("fact_transactions", "advisor_id", "key"),
    ("fact_transactions", "security_id", "key"),
    ("fact_transactions", "shares", "additive"),
    ("fact_transactions", "price", "non-additive"),
    ("fact_transactions", "amount", "additive"),
    ("fact_transactions", "is_post_departure_txn", "flag"),          # instructor release
    ("fact_transactions", "flag_non_trading_day", "flag"),           # my HW4 output
    ("fact_transactions", "flag_after_client_exit", "flag"),         # my HW4 output
]


def section(title):
    print("\n" + "=" * 70 + f"\n{title}\n" + "=" * 70)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(REPO / "Data" / "Wildcat_Capital_Clean"),
                    help="folder holding the eight clean CSV files")
    args = ap.parse_args()
    data = Path(args.data)
    REPORTS.mkdir(exist_ok=True)

    # Read as text, like HW4, so keys are compared exactly as Power BI would
    tables = V.load_tables(data)
    print(f"Data folder: {data}")

    # ------------------------------------------------------------ row counts
    section("Row counts vs. the HW5 brief")
    for t, n in EXPECTED_ROWS.items():
        got = len(tables[t])
        print(f"  {t:<26}{got:>9,}  expected {n:>9,}  {'OK' if got == n else 'MISMATCH'}")
        assert got == n, f"{t}: {got} rows, brief says {n}"

    # ------------------------------------------------------------ Part A
    section("Part A - primary keys (unique and never blank)")
    rows = []
    for t, k in {**PRIMARY_KEYS, **{f"{t} (alternate)": k for t, k in ALTERNATE_KEYS.items()}}.items():
        tbl = t.replace(" (alternate)", "")
        s = tables[tbl][k].str.strip()
        blanks, dups = int(s.eq("").sum()), int(s.duplicated().sum())
        print(f"  {t:<30}{k:<14} rows={len(s):>7,}  blank={blanks}  duplicates={dups}")
        rows.append({"check": "primary key", "table": t, "column": k, "rows": len(s),
                     "blank": blanks, "duplicates": dups, "passed": blanks == 0 and dups == 0})
        assert blanks == 0 and dups == 0, f"{t}.{k} is not a valid key"

    section("Part A - foreign keys (check_referential_integrity from HW4)")
    for child, ck, parent, pk, blank_ok in FOREIGN_KEYS:
        r = check_referential_integrity(tables[child], ck, tables[parent], pk)
        ok = r["orphan_rows"] == 0 and (blank_ok or r["null_keys"] == 0)
        print(f"  {child}.{ck:<14} -> {parent}[{pk}]  match={r['match_rate']:.2%}  "
              f"orphans={r['orphan_rows']}  blank={r['null_keys']:,}")
        rows.append({"check": "foreign key", "table": child, "column": ck,
                     "points_to": f"{parent}[{pk}]", "rows": r["rows"],
                     "blank": r["null_keys"], "orphans": r["orphan_rows"],
                     "match_rate": r["match_rate"], "passed": ok})
        assert ok, f"{child}.{ck} fails referential integrity"

    # The facts store calendar dates, so joining on dim_date[date_id] would fail
    print("\n  Proof that fact dates match dim_date[date], not dim_date[date_id]:")
    for child, ck in [("fact_fees", "fee_date"), ("fact_portfolio_snapshot", "snapshot_date"),
                      ("fact_transactions", "txn_date")]:
        by_id = check_referential_integrity(tables[child], ck, tables["dim_date"], "date_id")
        by_date = check_referential_integrity(tables[child], ck, tables["dim_date"], "date")
        print(f"    {child}.{ck:<14} vs date_id: {by_id['match_rate']:.0%}   vs date: {by_date['match_rate']:.0%}")
        assert by_id["match_rate"] == 0 and by_date["match_rate"] == 1, f"{child}.{ck} date join"

    # Blank security_id must be exactly the cash-flow rows
    tx = tables["fact_transactions"]
    blank = tx["security_id"].str.strip().eq("")
    by_type = tx.groupby("txn_type")["security_id"].apply(lambda s: s.str.strip().eq("").mean())
    print("\n  Share of rows with blank security_id, by txn_type:")
    for typ, share in by_type.items():
        print(f"    {typ:<14}{share:>7.0%}")
    only_cash = set(tx.loc[blank, "txn_type"]) == CASH_FLOW_TYPES
    all_cash_blank = not tx.loc[tx["txn_type"].isin(CASH_FLOW_TYPES), "security_id"].str.strip().ne("").any()
    rows.append({"check": "blank security_id only on cash flows", "table": "fact_transactions",
                 "column": "security_id", "rows": len(tx), "blank": int(blank.sum()),
                 "passed": only_cash and all_cash_blank})
    assert only_cash and all_cash_blank, "blank security_id is not exactly the cash-flow rows"

    # advisor_id appears twice on every path (fact and dim_client): do they agree?
    cl = tables["dim_client"][["client_id", "advisor_id"]]
    print("\n  Fact advisor_id agrees with dim_client.advisor_id:")
    for f in ["fact_fees", "fact_portfolio_snapshot", "fact_transactions"]:
        m = tables[f][["client_id", "advisor_id"]].merge(cl, on="client_id", suffixes=("", "_client"))
        agree = (m["advisor_id"] == m["advisor_id_client"]).mean()
        print(f"    {f:<26}{agree:.2%}")
        rows.append({"check": "advisor_id agrees with dim_client", "table": f,
                     "column": "advisor_id", "rows": len(m), "match_rate": agree,
                     "passed": agree == 1})
        assert agree == 1, f"{f}.advisor_id disagrees with dim_client"
    # benchmark_id on the snapshot: one per client?
    snap = tables["fact_portfolio_snapshot"]
    bench_per_client = snap.groupby("client_id")["benchmark_id"].nunique().max()
    print(f"\n  Most benchmarks any one client has across snapshots: {bench_per_client}")
    assert bench_per_client == 1, "a client has more than one benchmark"
    pd.DataFrame(rows).to_csv(REPORTS / "keys_check.csv", index=False)

    # ------------------------------------------------------------ Part B
    section("Part B - grain (no duplicate rows at the stated grain)")
    grows = []
    for f, cols in GRAIN.items():
        d = int(tables[f][cols].apply(lambda c: c.str.strip()).duplicated().sum())
        print(f"  {f:<26}{' + '.join(cols):<28} rows={len(tables[f]):>7,}  duplicates={d}")
        grows.append({"table": f, "grain_columns": " + ".join(cols),
                      "rows": len(tables[f]), "duplicates": d, "passed": d == 0})
        assert d == 0, f"{f} is not unique at {cols}"
    # Context for the grain sentences
    fees = tables["fact_fees"]
    print(f"\n  fee_date / snapshot_date day-of-month values: "
          f"{sorted(set(fees['fee_date'].str[-2:]) | set(snap['snapshot_date'].str[-2:]))}")
    print(f"  fee types per client-month (max): "
          f"{fees.groupby(['client_id', 'fee_date'])['fee_type'].nunique().max()}")
    print(f"  account types per client (max): "
          f"{snap.groupby('client_id')['account_type'].nunique().max()}")
    biz = ["client_id", "security_id", "txn_date", "txn_type"]
    shared = tx.duplicated(biz, keep=False)
    cash_shared = int((shared & tx["txn_type"].isin(CASH_FLOW_TYPES)).sum())
    print(f"  fact_transactions rows sharing {' + '.join(biz)} with another row: "
          f"{int(shared.sum()):,} ({int(tx.duplicated(biz).sum()):,} extra copies; "
          f"{cash_shared:,} cash flows, {int(shared.sum()) - cash_shared:,} trades/dividends), "
          f"so txn_id, one event, is the grain")
    pd.DataFrame(grows).to_csv(REPORTS / "grain_check.csv", index=False)

    # ------------------------------------------------------------ Part C
    section("Part C - numeric fact columns and their additivity")
    # The two data versions name their flag columns differently, so only
    # the columns present in this folder are checked and listed.
    present = [(t, c, r) for t, c, r in FACT_NUMERIC if c in tables[t].columns]
    for t, c, role in present:
        s = tables[t][c]
        s = s[s.str.strip().ne("")]
        assert pd.to_numeric(s, errors="coerce").notna().all(), f"{t}.{c} is not numeric"
        print(f"  {t:<26}{c:<24}{role}")
    # every numeric fact column is listed (no column forgotten)
    classified = {(a, b) for a, b, _ in FACT_NUMERIC}
    for t in ["fact_fees", "fact_portfolio_snapshot", "fact_transactions"]:
        for c in tables[t].columns:
            s = tables[t][c].str.strip()
            s = s[s.ne("")]
            # "mostly numeric", so one stray text value can't hide a column,
            # and an all-blank column is not treated as numeric
            if len(s) and pd.to_numeric(s, errors="coerce").notna().mean() > 0.5:
                assert (t, c) in classified, f"{t}.{c} not classified"
    pd.DataFrame(present, columns=["table", "column", "class"]).to_csv(
        REPORTS / "measures.csv", index=False)

    # Small demonstrations of why semi- and non-additive columns cannot be summed
    s = snap.assign(aum=pd.to_numeric(snap["aum"]),
                    cash_pct=pd.to_numeric(snap["cash_pct"]))
    dec = s[s["snapshot_date"] == "2024-12-01"]
    q4 = s[s["snapshot_date"].isin(["2024-10-01", "2024-11-01", "2024-12-01"])]
    assert len(dec) and q4["snapshot_date"].nunique() == 3, "demo snapshot dates not in this data"
    print("\n  aum is semi-additive:")
    print(f"    total AUM on 2024-12-01 (sum across clients, valid):  ${dec['aum'].sum():>16,.0f}")
    print(f"    sum of Oct+Nov+Dec 2024 (sum across months, WRONG):   ${q4['aum'].sum():>16,.0f}")
    print("  cash_pct is non-additive:")
    print(f"    sum across clients on 2024-12-01 (meaningless):       {dec['cash_pct'].sum():>16.1f}")
    print(f"    simple average:                                        {dec['cash_pct'].mean():>16.2%}")
    print(f"    AUM-weighted average (the firm's real cash share):     "
          f"{(dec['cash_pct'] * dec['aum']).sum() / dec['aum'].sum():>16.2%}")
    t2 = tx.assign(amount=pd.to_numeric(tx["amount"]))
    print("  fact_transactions.amount is stored unsigned for every txn_type:")
    print(f"    minimum amount: {t2['amount'].min():,.2f} (no negatives), so a withdrawal adds to a sum")

    # ------------------------------------------------------------ other figures
    section("Other figures quoted in star_design.md")
    num = lambda col: pd.to_numeric(col, errors="coerce")
    dv = tx[tx["txn_type"] == "Dividend"]
    print(f"  Dividend rows equal to shares x price: "
          f"{int(((num(dv['amount']) - num(dv['shares']) * num(dv['price'])).abs() < 0.01).sum()):,} of {len(dv):,}")
    bs = tx[tx["txn_type"].isin(["Buy", "Sell"])]
    print(f"  Buy/Sell rows where amount = shares x price: "
          f"{((num(bs['amount']) - num(bs['shares']) * num(bs['price'])).abs() < 0.01).mean():.0%}")
    implied = num(fees["amount"]) * 12 / num(fees["aum_basis"]) * 10000
    print(f"  bps_charged vs amount x 12 / aum_basis x 10,000, max difference: "
          f"{(implied - num(fees['bps_charged'])).abs().max():.2f} bps")
    print(f"  Total fee revenue (SUM of fact_fees.amount): ${num(fees['amount']).sum():,.0f}")
    for t, c in [("fact_portfolio_snapshot", "is_return_suspect"),
                 ("fact_transactions", "is_post_departure_txn")]:
        if c in tables[t].columns:
            print(f"  {c} = 1: {int(tables[t][c].str.strip().eq('1').sum()):,} rows")
    dd = tables["dim_date"]
    for flag in ["is_month_end", "is_quarter_end"]:
        on = int(snap["snapshot_date"].isin(dd.loc[dd[flag].str.strip() == "1", "date"]).sum())
        print(f"  snapshots dated on an {flag} day: {on:,} of {len(snap):,}")
    sec = tables["dim_security"]
    etf = sec["is_etf"].str.strip().str.lower().eq("true")      # stored as True / False
    blank_er = sec["expense_ratio_bps"].str.strip().eq("")
    print(f"  expense_ratio_bps blank: {int((blank_er & ~etf).sum())} of {int((~etf).sum())} non-ETFs, "
          f"{int((blank_er & etf).sum())} of {int(etf.sum())} ETFs")

    print("\nAll HW5 checks passed.")


if __name__ == "__main__":
    main()
