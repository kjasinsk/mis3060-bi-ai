"""
02_clean.py  -  HW4 Part C: clean the Wildcat Capital tables.

Plain-English summary:
  * Reads the eight RAW files as text. The raw files are never modified.
  * Applies the fixes from decision_log.md ONE AT A TIME. After each fix it
    prints how many rows changed, shows a before/after check, and uses
    `assert` to prove the fix did what it claimed. If any check fails, the
    script stops before writing anything.
  * Repairs are only made when another column or table proves the right
    value ("reconcile instead of guessing"). Suspicious values that cannot be
    proven wrong get a 0/1 flag column instead.
  * Removed rows go to data/audit/quarantine_*.csv, never just deleted, and
    the script proves  raw rows = clean rows + quarantined rows  per table.
  * Writes: data/clean/*.csv (same names, same columns + flag columns),
            data/audit/cleaning_log.csv, data/audit/value_changes.csv,
            data/audit/quarantine_*.csv, data/clean/README_clean.md

Order: quarantine first (no point fixing rows we drop), then value repairs,
then pure format changes, then flags (computed on the final values).

Run from anywhere:  python hw04/scripts/02_clean.py
Author: Kaitlyn Jasinski
"""

import importlib
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wildcat_schema as S  # noqa: E402

V = importlib.import_module("03_validate")  # shared checks (RI function, num, rules)

# ---------------------------------------------------------------------------
# Audit-trail helpers
# ---------------------------------------------------------------------------
CLEANING_LOG = []   # one row per step
VALUE_CHANGES = []  # one row per changed cell
QUARANTINE = {}     # file stem -> (source table, DataFrame)


def log_step(table, issue, action, rows, note=""):
    CLEANING_LOG.append(dict(step=len(CLEANING_LOG) + 1, table=table, issue=issue,
                             action=action, rows_affected=int(rows), note=note))


def record_changes(table, df, mask, column, old, new):
    """Save one value_changes row per changed cell."""
    key = S.PRIMARY_KEYS[table]
    ch = pd.DataFrame({"table": table, "key_column": key, "key": df.loc[mask, key].values,
                       "column": column, "old_value": old[mask].values,
                       "new_value": new[mask].values})
    VALUE_CHANGES.append(ch)


def quarantine(name, table, rows, reason):
    q = rows.copy()
    q.insert(0, "quarantine_reason", reason)
    q.insert(0, "source_table", table)
    QUARANTINE[name] = (table, q)


def header(n, title):
    print(f"\n[{n}] {title}\n" + "-" * 78)


def show(label, before, after):
    print(f"    before: {label} = {before}")
    print(f"    after : {label} = {after}")


def plain_decimal(text):
    """Write a number as a plain decimal: '9.9e-05' -> '0.000099'.
    Uses Decimal so no digits are gained or lost to float rounding."""
    d = Decimal(text)
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ===========================================================================
# Cleaning steps
# ===========================================================================
def step_quarantine_duplicate_clients(tb):
    header(1, "dim_client: quarantine near-duplicate clients (decision #1)")
    c = tb["dim_client"]
    bk = S.BUSINESS_KEYS["dim_client"]
    dup = c.duplicated(bk, keep="first")
    print(f"    rows affected: {dup.sum()}")

    # Evidence checks BEFORE removing anything
    originals = c[~dup].set_index(bk)["client_id"]
    q = c[dup].copy()
    q["original_client_id"] = q.set_index(bk).index.map(originals)
    same_cols = [col for col in c.columns if col not in ("client_id", "last_name")]
    orig_rows = c.set_index("client_id").loc[q["original_client_id"], same_cols].reset_index(drop=True)
    assert (q[same_cols].reset_index(drop=True) == orig_rows).all().all(), \
        "a 'duplicate' differs from its original in more than the last name"
    assert (q["last_name"].values != c.set_index("client_id").loc[q["original_client_id"], "last_name"].values).all()
    used = sum(tb[t]["client_id"].isin(set(q["client_id"])).sum()
               for t in ("fact_fees", "fact_portfolio_snapshot", "fact_transactions"))
    assert used == 0, f"{used} fact rows still point at a duplicate client - cannot quarantine"
    print(f"    verified: every duplicate equals its original on all {len(same_cols)} other "
          f"columns; fact rows using them = {used}")

    before = len(c)
    tb["dim_client"] = c[~dup].reset_index(drop=True)
    after = len(tb["dim_client"])
    show("dim_client rows", before, after)
    assert after == before - dup.sum()
    assert not tb["dim_client"].duplicated(bk).any(), "business-key duplicates remain"
    quarantine("dim_client_duplicates", "dim_client", q,
               "near-duplicate of original_client_id (same person, last name misspelled)")
    ids = q["client_id"].astype(int)   # compare IDs as numbers: as text "9999" > "10000"
    log_step("dim_client", f"{dup.sum()} clients duplicate an existing client (last name misspelled), "
             "unused by facts", "quarantine", dup.sum(), f"IDs {ids.min()}-{ids.max()}")


def step_quarantine_orphan_transactions(tb):
    header(2, "fact_transactions: quarantine transactions for unknown clients (decision #2)")
    t = tb["fact_transactions"]
    ri = V.check_referential_integrity(t, "client_id", tb["dim_client"], "client_id")
    mask = ri["orphan_mask"]
    print(f"    rows affected: {mask.sum()}  ({ri['distinct_orphan_keys']} distinct client IDs)")
    before = ri["match_rate"]
    quarantine("fact_transactions_orphans", "fact_transactions", t[mask],
               "client_id not found in dim_client")
    tb["fact_transactions"] = t[~mask].reset_index(drop=True)
    after = V.check_referential_integrity(tb["fact_transactions"], "client_id",
                                          tb["dim_client"], "client_id")
    show("client_id match rate", f"{before:.4%}", f"{after['match_rate']:.4%}")
    assert after["orphan_rows"] == 0 and after["match_rate"] == 1.0
    log_step("fact_transactions", "client_id not in dim_client (orphans)", "quarantine",
             mask.sum(), f"client IDs {t.loc[mask, 'client_id'].astype(int).min()}-"
                         f"{t.loc[mask, 'client_id'].astype(int).max()}")


def step_standardize_state(tb):
    header(3, "dim_client.state: full names -> 2-letter codes (decision #3)")
    c = tb["dim_client"]
    old = c["state"].copy()
    mask = old.isin(S.US_STATES)
    print(f"    rows affected: {mask.sum()}  {old[mask].value_counts().to_dict()}")
    new = old.where(~mask, old.map(S.US_STATES))
    c["state"] = new
    record_changes("dim_client", c, mask, "state", old, new)
    show("states not a valid code", (~old.isin(S.ALLOWED_VALUES[('dim_client', 'state')])).sum(),
         (~new.isin(S.ALLOWED_VALUES[('dim_client', 'state')])).sum())
    assert new.isin(S.ALLOWED_VALUES[("dim_client", "state")]).all()
    log_step("dim_client", "state written as full name", "standardize", mask.sum(),
             "mapped with USPS table; one-to-one")


def step_fill_risk_profile(tb):
    header(4, "dim_client.risk_profile: fill blanks from the client's benchmark (decision #4)")
    c = tb["dim_client"]
    p = tb["fact_portfolio_snapshot"]
    blank = c["risk_profile"].eq("")
    print(f"    rows affected: {blank.sum()}")

    # Re-prove the rule on today's data: profile -> benchmark is always the same
    bench = p.groupby("client_id")["benchmark_id"].agg(lambda s: set(s))
    assert (bench.map(len) == 1).all(), "a client uses more than one benchmark"
    bench = bench.map(lambda s: next(iter(s)))
    known = c[~blank].assign(b=lambda d: d["client_id"].map(bench)).dropna(subset=["b"])
    assert (known["risk_profile"].map(S.RISK_TO_BENCHMARK) == known["b"]).all(), \
        "risk -> benchmark rule does not hold, so it cannot be used to fill blanks"
    # Only a benchmark used by exactly ONE profile can identify the profile
    profiles_per_bench = known.groupby("b")["risk_profile"].agg(lambda s: set(s))
    unique = {b: next(iter(s)) for b, s in profiles_per_bench.items() if len(s) == 1}
    print(f"    benchmarks that identify exactly one profile: {unique}")

    old = c["risk_profile"].copy()
    inferred = c["client_id"].map(bench).map(unique)
    fill = blank & inferred.notna()
    new = old.where(~fill, inferred)
    c["risk_profile"] = new
    c["flag_risk_profile_inferred"] = fill.astype(int)
    record_changes("dim_client", c, fill, "risk_profile", old, new)
    show("blank risk_profile", blank.sum(), c["risk_profile"].eq("").sum())
    assert c["risk_profile"].eq("").sum() == 0, "some blanks could not be proven - left blank"
    assert c["flag_risk_profile_inferred"].sum() == fill.sum()
    log_step("dim_client", "risk_profile blank", "fill + flag", fill.sum(),
             f"filled {new[fill].value_counts().to_dict()} via benchmark; "
             "flag_risk_profile_inferred = 1")


def step_convert_security_id(tb):
    header(5, "fact_transactions.security_id: '45.0' -> '45' (decision #7)")
    t = tb["fact_transactions"]
    old = t["security_id"].copy()
    nonblank = old.ne("")
    assert old[nonblank].str.fullmatch(r"\d+\.0").all(), "a security_id has a real decimal part"
    new = old.where(~nonblank, old.str[:-2])
    mask = new != old
    print(f"    rows affected: {mask.sum()}")
    raw_match = old[nonblank].isin(set(tb["dim_security"]["security_id"])).mean()
    t["security_id"] = new
    record_changes("fact_transactions", t, mask, "security_id", old, new)
    after = V.check_referential_integrity(t, "security_id", tb["dim_security"], "security_id")
    show("text match to dim_security", f"{raw_match:.2%}", f"{after['match_rate']:.2%}")
    assert after["match_rate"] == 1.0 and t["security_id"][nonblank].str.fullmatch(r"\d+").all()
    log_step("fact_transactions", "security_id stored as float text", "convert", mask.sum(),
             "dropped '.0'; text join now matches 100%")


def step_fix_negative_shares(tb):
    header(6, "fact_transactions.shares: remove minus sign on Buys (decision #5)")
    t = tb["fact_transactions"]
    old = t["shares"].copy()
    sh, px, am = V.num(old), V.num(t["price"]), V.num(t["amount"])
    mask = sh < 0
    print(f"    rows affected: {mask.sum()}  {t.loc[mask, 'txn_type'].value_counts().to_dict()}")

    # Reconcile BEFORE changing: |shares| x price must already equal amount
    agree = ((sh[mask].abs() * px[mask] - am[mask]).abs() <= V.RECON_TOL_MONEY)
    assert agree.all(), f"{(~agree).sum()} rows don't reconcile; sign is not the only problem"
    assert t.loc[mask, "txn_type"].eq("Buy").all()

    new = old.where(~mask, old.str.lstrip("-"))
    t["shares"] = new
    record_changes("fact_transactions", t, mask, "shares", old, new)
    sh2 = V.num(t["shares"])
    bad_before = int(((sh * px - am).abs() > V.RECON_TOL_MONEY).sum())
    bad_after = int(((sh2 * px - am).abs() > V.RECON_TOL_MONEY).sum())
    show("rows where shares x price != amount", bad_before, bad_after)
    assert (sh2.dropna() > 0).all() and bad_after == 0
    log_step("fact_transactions", "negative shares on Buy rows", "convert (sign)", mask.sum(),
             "verified |shares| x price = amount for every row before and after")


def step_convert_percent_returns(tb):
    header(7, "fact_portfolio_snapshot.return_ytd: '9.28%' -> 0.0928 (decision #6)")
    p = tb["fact_portfolio_snapshot"]
    old = p["return_ytd"].copy()
    mask = old.str.strip().str.endswith("%")
    print(f"    rows affected: {mask.sum()}")
    new = old.copy()
    new[mask] = old[mask].str.strip().str.rstrip("%").map(
        lambda v: plain_decimal(str(Decimal(v) / Decimal(100))))

    # Reconcile: converted value must equal benchmark + alpha
    calc = V.num(p["benchmark_return_ytd"]) + V.num(p["active_alpha_ytd"])
    gap = (pd.to_numeric(new[mask]) - calc[mask]).abs()
    print(f"    reconciliation: largest gap vs benchmark + alpha = {gap.max():.7f}")
    assert (gap <= V.RECON_TOL_RETURN).all(), "converted percent does not reconcile"

    p["return_ytd"] = new
    record_changes("fact_portfolio_snapshot", p, mask, "return_ytd", old, new)
    show("values that are not numbers", V.num(old).isna().sum(), V.num(new).isna().sum())
    assert V.num(p["return_ytd"]).notna().all()
    log_step("fact_portfolio_snapshot", "return_ytd stored as percent text", "convert",
             mask.sum(), f"divided by 100; all reconcile to benchmark+alpha within "
                         f"{V.RECON_TOL_RETURN}")


SCI = r"^-?\d+(\.\d+)?[eE][-+]?\d+$"   # e.g. 9.9e-05


def step_plain_decimals(tb):
    header(8, "All decimal columns: scientific notation -> plain decimals (decision #8)")
    # Checks EVERY decimal column in every table, not just the two that have
    # the problem today, so new data with 1e-05 in another column is caught too.
    for table, types in S.COLUMN_TYPES.items():
        df = tb[table]
        for col, col_type in types.items():
            if col_type != "decimal":
                continue
            old = df[col].copy()
            mask = old.str.strip().str.match(SCI)
            if not mask.any():
                continue
            new = old.copy()
            new[mask] = old[mask].str.strip().map(plain_decimal)
            assert (pd.to_numeric(new[mask]) == pd.to_numeric(old[mask])).all(), "value changed"
            df[col] = new
            record_changes(table, df, mask, col, old, new)
            print(f"    {table}.{col}: rows affected {mask.sum()}")
            show(f"{col} in scientific notation", mask.sum(), df[col].str.match(SCI).sum())
            log_step(table, f"{col} written in scientific notation",
                     "standardize format", mask.sum(), "value unchanged (asserted equal)")
    # after-state: no decimal column anywhere still holds scientific notation
    for table, types in S.COLUMN_TYPES.items():
        for col, col_type in types.items():
            if col_type == "decimal":
                assert not tb[table][col].str.strip().str.match(SCI).any(), f"{table}.{col}"


def step_add_flags(tb):
    header(9, "Flags for suspicious values that cannot be proven wrong (decisions #9-#12)")
    t, p = tb["fact_transactions"], tb["fact_portfolio_snapshot"]
    # key by (table, rule name): the same name can exist in two tables
    rules = {(r["table"], r["name"]): r["func"] for r in V.ALL_RULES}

    flags = [
        (t, "fact_transactions", "flag_non_trading_day",
         "Buy/Sell dated on a non-trading day (markets closed)"),
        (t, "fact_transactions", "flag_after_client_exit",
         "activity after an inactive client's last month on the books"),
        (p, "fact_portfolio_snapshot", "flag_extreme_return", "|return_ytd| above 100% in one year"),
        (p, "fact_portfolio_snapshot", "flag_aum_floor",
         "aum stuck at exactly $1,000.00 (system floor)"),
    ]
    for df, table, col, rule_name in flags:
        m = rules[(table, rule_name)](tb).fillna(False).astype(bool)
        df[col] = m.astype(int)
        print(f"    {table}.{col}: {m.sum():,} rows flagged")
        assert df[col].isin([0, 1]).all() and df[col].sum() == m.sum()
        log_step(table, rule_name, f"flag ({col} = 1)", m.sum(), "value kept unchanged")


# ===========================================================================
# README for the clean folder
# ===========================================================================
def write_readme(tb, raw_counts, q_counts):
    t_, f_, p_, c_ = (tb["fact_transactions"], tb["fact_fees"],
                      tb["fact_portfolio_snapshot"], tb["dim_client"])
    n_div = int(t_["txn_type"].eq("Dividend").sum())
    fee_txn = V.num(t_.loc[t_["txn_type"].eq("Advisory Fee"), "amount"]).sum() / 1e6
    fee_tbl = V.num(f_["amount"]).sum() / 1e6
    fee_keys = set(f_["client_id"] + "|" + f_["fee_date"])
    n_nofee = int((~(p_["client_id"] + "|" + p_["snapshot_date"]).isin(fee_keys)).sum())
    n_zip0 = int(c_["zip_code"].str.startswith("0").sum())
    n_pct = int(sum(1 for ch in VALUE_CHANGES for v in ch.loc[ch["column"].eq("return_ytd"), "old_value"]
                    if str(v).endswith("%")))
    used_b = set(p_["benchmark_id"]) | set(tb["dim_security"]["benchmark_id"])
    unused = tb["dim_benchmark"][~tb["dim_benchmark"]["benchmark_id"].isin(used_b)]
    unused_b = ", ".join(f"{r.benchmark_id} ({r.name})" for r in unused.itertuples()) or "none"
    adv_map = c_.set_index("client_id")["advisor_id"]
    adv_rows = pd.concat([d[["client_id", "advisor_id"]] for d in (t_, f_, p_)])
    adv_agree = (adv_rows["client_id"].map(adv_map) == adv_rows["advisor_id"]).mean()
    ri_ok = sum(V.check_referential_integrity(tb[a], b, tb[c], d)["match_rate"] == 1.0
                for a, b, c, d in S.RELATIONSHIPS)
    lines = [
        "# Wildcat Capital — clean data (HW4)",
        "",
        "Produced by `scripts/02_clean.py` from `data/raw/`. Raw files are never modified. "
        "Every change is listed in `data/audit/cleaning_log.csv` (one row per step) and "
        "`data/audit/value_changes.csv` (one row per changed cell).",
        "",
        "## Row counts",
        "",
        "| Table | Raw rows | Clean rows | Quarantined | Check |",
        "|---|---:|---:|---:|---|",
    ]
    for t in S.TABLES:
        lines.append(f"| {t} | {raw_counts[t]:,} | {len(tb[t]):,} | {q_counts[t]:,} | "
                     f"raw = clean + quarantined ✔ |")
    lines += [
        "",
        "## Relationships (star schema for Power BI)",
        "",
        "All are many-to-one, from the fact (or child) to the dimension, single direction.",
        "",
        "| From (many) | To (one) | Notes |",
        "|---|---|---|",
        "| fact_transactions.client_id | dim_client.client_id | |",
        "| fact_transactions.advisor_id | dim_advisor.advisor_id | |",
        "| fact_transactions.security_id | dim_security.security_id | blank for Deposit/Withdrawal/Advisory Fee — expected |",
        "| fact_transactions.txn_date | dim_date.date | |",
        "| fact_fees.client_id | dim_client.client_id | |",
        "| fact_fees.advisor_id | dim_advisor.advisor_id | |",
        "| fact_fees.fee_date | dim_date.date | monthly, always the 1st |",
        "| fact_portfolio_snapshot.client_id | dim_client.client_id | |",
        "| fact_portfolio_snapshot.advisor_id | dim_advisor.advisor_id | |",
        "| fact_portfolio_snapshot.benchmark_id | dim_benchmark.benchmark_id | |",
        "| fact_portfolio_snapshot.snapshot_date | dim_date.date | monthly, always the 1st |",
        f"| dim_client.advisor_id | dim_advisor.advisor_id | snowflake link — the facts also carry advisor_id directly; they agree on {adv_agree:.2%} of fact rows |",
        "| dim_security.benchmark_id | dim_benchmark.benchmark_id | snowflake link |",
        "",
        f"In the clean data, {ri_ok} of 13 relationships match 100% (checked here with "
        "`check_referential_integrity`; full detail in `reports/validation_referential_integrity.csv`). "
        "`dim_date` joins on `date` (YYYY-MM-DD), not on `date_id`, because no fact table carries `date_id`.",
        "",
        "## Column-type settings a BI tool needs",
        "",
        "| Set as | Columns | Why |",
        "|---|---|---|",
        f"| **Text** | `dim_client.zip_code` | {n_zip0} ZIPs start with 0 (02068); a number type drops the zero |",
        "| **Text** | `dim_advisor.certifications` | the value `None` means *no certification*; don't let the tool turn it into blank |",
        "| **Text** | `account_type`, `primary_account_type` | the value `529` is a plan type, not a number |",
        "| **Whole number** | all `*_id` columns (incl. `fact_transactions.security_id`, now `45` not `45.0`), `year`, `month`, `quarter`, `age`, `years_experience`, `aum_target_mm`, all `flag_*` | keys and counts |",
        "| **Date** | `date`, `client_since`, `fee_date`, `snapshot_date`, `txn_date` | ISO `YYYY-MM-DD` |",
        "| **Decimal / currency** | `initial_aum`, `aum`, `aum_basis`, `amount`, `price` | money |",
        "| **Decimal** | `shares`, `bps_charged`, `expense_ratio_bps` | |",
        "| **Decimal, format as %** | `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct` | stored as fractions (0.0928 = 9.28%) |",
        "| **True/False** | `is_active`, `is_etf` | |",
        "| **0/1** | `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day` | |",
        "",
        "Blank is a legitimate value in: `dim_security.sector` (ETFs), `dim_security.expense_ratio_bps` "
        "(non-ETFs), and `fact_transactions.security_id`/`shares`/`price` (cash flows). Do not fill them.",
        "",
        "## Flag columns added (0 = normal, 1 = look at this)",
        "",
        "| Table | Column | Rows = 1 | Meaning | What to do in reports |",
        "|---|---|---:|---|---|",
        f"| dim_client | flag_risk_profile_inferred | {tb['dim_client']['flag_risk_profile_inferred'].sum():,} | risk_profile was blank and was filled as 'Balanced' from the client's benchmark | confirm with the advisor before using for suitability |",
        f"| fact_transactions | flag_non_trading_day | {tb['fact_transactions']['flag_non_trading_day'].sum():,} | Buy/Sell dated on a non-trading day (weekend or market holiday) | don't price these against that day's market data |",
        f"| fact_transactions | flag_after_client_exit | {tb['fact_transactions']['flag_after_client_exit'].sum():,} | activity after an inactive client's last month | exclude from 'current client' activity |",
        f"| fact_portfolio_snapshot | flag_extreme_return | {tb['fact_portfolio_snapshot']['flag_extreme_return'].sum():,} | return_ytd above +100% or below −100% (driven by deposits/withdrawals) | exclude from average-return measures, or use the median |",
        f"| fact_portfolio_snapshot | flag_aum_floor | {tb['fact_portfolio_snapshot']['flag_aum_floor'].sum():,} | aum exactly $1,000 (source-system floor for drained accounts) | treat as ~0 for per-client analysis |",
        "",
        "## Known limitations (not fixed, on purpose)",
        "",
        f"1. **Dividend amounts are not real dividends.** All {n_div:,} Dividend rows equal shares × price, "
        "i.e. the full position value (a 100% yield). It is every row, so it is how the source defines the "
        "field, and nothing lets us recompute the true payout. *Do not report dividend income from this column.*",
        f"2. **Two fee sources disagree.** Advisory Fee rows in `fact_transactions` (${fee_txn:,.1f}M) never match "
        f"`fact_fees` (${fee_tbl:,.1f}M) for the same client-month. Use **`fact_fees`** for fee revenue: its amount "
        "reconciles 100% to aum_basis × bps ÷ 12 and its aum_basis matches snapshot AUM 100%. Never add both.",
        "3. **Weekend trade dates are kept.** The true fill date is unknown, so the date was not moved (flagged instead).",
        f"4. **{n_pct} converted returns have 4 decimal places** (they arrived as 2-dp percents). They reconcile to "
        "benchmark + alpha within half a basis point; I did not replace them with the calculated value.",
        f"5. **{n_nofee:,} client-months have a snapshot but no fee row.** Consistent with fee waivers; no fee was invented.",
        f"6. **Unused benchmark(s): {unused_b}** — no client or security uses them. Kept; a dimension may list unused members.",
        "7. **return_ytd mixes market return with cash flows** for the flagged accounts, so it is not a pure "
        "time-weighted return. A true TWR would need daily cash-flow-adjusted valuations we don't have.",
    ]
    (S.CLEAN_DIR / "README_clean.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ===========================================================================
# Main
# ===========================================================================
def main():
    print("Reading raw tables as text from", S.RAW_DIR)
    tb = V.load_tables(S.RAW_DIR)
    raw_counts = {t: len(df) for t, df in tb.items()}
    raw_columns = {t: list(df.columns) for t, df in tb.items()}

    step_quarantine_duplicate_clients(tb)
    step_quarantine_orphan_transactions(tb)
    step_standardize_state(tb)
    step_fill_risk_profile(tb)
    step_convert_security_id(tb)
    step_fix_negative_shares(tb)
    step_convert_percent_returns(tb)
    step_plain_decimals(tb)
    step_add_flags(tb)

    # ---- Prove nothing was lost: raw = clean + quarantined -----------------
    header(10, "Row reconciliation: raw = clean + quarantined")
    q_counts = {t: 0 for t in S.TABLES}
    for name, (table, q) in QUARANTINE.items():
        q_counts[table] += len(q)
    for t in S.TABLES:
        ok = raw_counts[t] == len(tb[t]) + q_counts[t]
        print(f"    {t:<26} raw {raw_counts[t]:>8,} = clean {len(tb[t]):>8,} "
              f"+ quarantined {q_counts[t]:>4,}   {'OK' if ok else 'MISMATCH'}")
        assert ok, f"{t}: rows lost or created"
        # same columns, in the same order; only flag_* columns may be added
        extra = [c for c in tb[t].columns if c not in raw_columns[t]]
        assert list(tb[t].columns[:len(raw_columns[t])]) == raw_columns[t]
        assert all(c.startswith("flag_") for c in extra)
        # IDs from the clean file and the quarantine file never overlap
        pk = S.PRIMARY_KEYS[t]
        qids = set().union(*[set(q[pk]) for tbl, q in QUARANTINE.values() if tbl == t])
        assert not (set(tb[t][pk]) & qids)

    # ---- Write everything --------------------------------------------------
    S.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    S.AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    for t, df in tb.items():
        df.to_csv(S.CLEAN_DIR / f"{t}.csv", index=False)
    for name, (_, q) in QUARANTINE.items():
        q.to_csv(S.AUDIT_DIR / f"quarantine_{name}.csv", index=False)
    pd.DataFrame(CLEANING_LOG).to_csv(S.AUDIT_DIR / "cleaning_log.csv", index=False)
    changes = pd.concat(VALUE_CHANGES, ignore_index=True)
    changes.to_csv(S.AUDIT_DIR / "value_changes.csv", index=False)
    write_readme(tb, raw_counts, q_counts)

    # Re-read what was written, as text, to prove the files say what we meant
    for t in S.TABLES:
        back = pd.read_csv(S.CLEAN_DIR / f"{t}.csv", dtype=str, keep_default_na=False)
        assert back.shape == tb[t].shape, f"{t} changed shape on write"
        assert back.equals(tb[t].astype(str)), f"{t} changed content on write"

    print("\nCleaning log:")
    print(pd.DataFrame(CLEANING_LOG)[["step", "table", "action", "rows_affected"]].to_string(index=False))
    print(f"\nvalue_changes.csv: {len(changes):,} changed cells")
    print("Changed cells by table/column:")
    print(changes.groupby(["table", "column"]).size().to_string())
    print(f"\nWrote clean tables to {S.CLEAN_DIR}")
    print(f"Wrote audit trail to  {S.AUDIT_DIR}")
    print("DONE: every assert passed.")


if __name__ == "__main__":
    main()
