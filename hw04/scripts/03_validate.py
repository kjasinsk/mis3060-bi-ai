"""
03_validate.py  -  HW4 Part D: referential integrity, rules, reconciliations,
                   outliers and the data quality scorecard.

What it does, in plain terms:
  1. check_referential_integrity(): ONE reusable function that answers
     "does every key in the fact table point at a real row in the dimension?"
     It is run on all 13 relationships (10 ID joins + 3 joins to the calendar).
  2. Rule checks: every column with a natural business limit (ranges, allowed
     code lists, sign rules) plus row-level and cross-table business rules.
  3. Cross-table reconciliations: recompute a number from other columns or
     another table and compare it with the stored number.
  4. IQR outlier flags on numeric columns that have no natural limit.
  5. Runs all of the above on BOTH the raw and the clean tables and saves
     reports/data_quality_scorecard.csv (one row per table per stage).

The check functions in this file are also imported by 01_profile.py, so the
audit and the validation measure problems in exactly the same way.

Run from anywhere:  python hw04/scripts/03_validate.py
Author: Kaitlyn Jasinski
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wildcat_schema as S  # noqa: E402

RECON_TOL_RETURN = 0.0000501  # half a basis point (+ float noise): covers values stored as 2-dp percents
RECON_TOL_MONEY = 0.011     # one cent plus float noise


# ===========================================================================
# Loading
# ===========================================================================
def load_tables(folder):
    """Read all eight tables as TEXT so nothing is silently converted."""
    return {
        t: pd.read_csv(Path(folder) / f"{t}.csv", dtype=str, keep_default_na=False)
        for t in S.TABLES
    }


def num(s):
    """Text -> number. Anything that is not a plain number becomes NaN."""
    return pd.to_numeric(s.str.strip(), errors="coerce")


def unreadable(s):
    """True where a cell is NOT blank but cannot be read as a number
    (e.g. '9.28%'). Math checks count these as FAILURES, not passes:
    comparing NaN to anything gives False, which would hide them."""
    return s.str.strip().ne("") & num(s).isna()


def int_key(s):
    """Normalise an ID for joining: '45', '45.0' and ' 45 ' all become '45'.
    Blank stays blank. Anything that is not a whole number stays as written,
    so it will NOT match and will show up as an orphan."""
    s = s.astype(str).str.strip()
    as_num = pd.to_numeric(s, errors="coerce")
    whole = as_num.notna() & (as_num == np.floor(as_num))
    out = s.copy()
    out[whole] = as_num[whole].astype("int64").astype(str)
    return out


# ===========================================================================
# 1. Referential integrity  (THE reusable function - keep for Assignment 5)
# ===========================================================================
def check_referential_integrity(fact_df, fact_key, dim_df, dim_key, normalize_ids=False):
    """Check that every value in fact_df[fact_key] exists in dim_df[dim_key].

    Keys are compared EXACTLY as stored (after trimming spaces), the way a
    text join in Power BI would compare them, so '45.0' does NOT match '45'.
    Pass normalize_ids=True to compare whole-number IDs by value instead
    (useful for asking "would this join once the type is fixed?").

    Blank keys are NOT counted as orphans: they are reported separately as the
    null-key rate, because a blank key can be legitimate (a deposit has no
    security) while a key that points nowhere never is.

    Returns a dict:
        rows              rows in the fact table
        null_keys         rows whose key is blank
        null_key_rate     null_keys / rows
        matched_rows      non-blank keys that found a parent
        match_rate        matched_rows / non-blank rows (1.0 = perfect)
        orphan_rows       non-blank keys with no parent
        distinct_orphan_keys   how many different bad key values
        orphan_examples   up to 5 bad key values
        orphan_mask       boolean Series, True on each orphan row
    """
    f = fact_df[fact_key].astype(str).str.strip()
    d = dim_df[dim_key].astype(str).str.strip()
    if normalize_ids:
        f, d = int_key(f), int_key(d)

    rows = len(f)
    is_null = f.eq("")
    non_null = ~is_null
    found = f.isin(set(d))
    orphan_mask = non_null & ~found
    n_non_null = int(non_null.sum())
    orphans = f[orphan_mask]
    return {
        "rows": rows,
        "null_keys": int(is_null.sum()),
        "null_key_rate": round(is_null.mean(), 6) if rows else 0.0,
        "matched_rows": int((non_null & found).sum()),
        "match_rate": round((non_null & found).sum() / n_non_null, 6) if n_non_null else 1.0,
        "orphan_rows": int(orphan_mask.sum()),
        "distinct_orphan_keys": int(orphans.nunique()),
        "orphan_examples": ", ".join(sorted(orphans.unique(), key=lambda x: (len(x), x))[:5]),
        "orphan_mask": orphan_mask,
    }


def run_all_relationships(tables):
    """Apply check_referential_integrity to all 13 relationships.
    Also reports the match rate by VALUE, which separates 'wrong format'
    (fixable) from 'key really missing' (orphan)."""
    out = []
    for child, ckey, parent, pkey in S.RELATIONSHIPS:
        r = check_referential_integrity(tables[child], ckey, tables[parent], pkey)
        r = {k: v for k, v in r.items() if k != "orphan_mask"}
        by_value = check_referential_integrity(tables[child], ckey, tables[parent], pkey,
                                               normalize_ids="date" not in ckey)
        out.append({"fact_table": child, "fact_key": ckey,
                    "dim_table": parent, "dim_key": pkey, **r,
                    "match_rate_by_value": by_value["match_rate"],
                    "orphan_rows_by_value": by_value["orphan_rows"]})
    return pd.DataFrame(out)


# ===========================================================================
# 2. Type validity
# ===========================================================================
TYPE_PATTERNS = {
    "int": r"^-?\d+$",
    "decimal": r"^-?\d+(\.\d+)?$",       # plain number: no %, $, commas or 1e-05
    "date": r"^\d{4}-\d{2}-\d{2}$",
    "bool": r"^(True|False)$",
    "flag01": r"^[01]$",
}


def type_valid_mask(s, col_type):
    """True where a NON-BLANK value is written as its expected type.
    Blank cells return True here (completeness is measured separately)."""
    if col_type == "text":
        return pd.Series(True, index=s.index)
    ok = s.str.match(TYPE_PATTERNS[col_type])
    if col_type == "date":
        ok = ok & pd.to_datetime(s, format="%Y-%m-%d", errors="coerce").notna()
    return ok | s.eq("")


# ===========================================================================
# 3. Expected blanks (legitimate structure vs missing data)
# ===========================================================================
def expected_blank_mask(tables, table, col):
    """True on rows where a blank in `col` is CORRECT (not missing data)."""
    df = tables[table]
    if table == "dim_security" and col == "sector":
        return df["is_etf"].eq("True")
    if table == "dim_security" and col == "expense_ratio_bps":
        return df["is_etf"].eq("False")
    if table == "fact_transactions" and col in ("security_id", "shares", "price"):
        return df["txn_type"].isin(S.CASH_FLOW_TYPES)
    return pd.Series(False, index=df.index)


# ===========================================================================
# 4. Row-level rules
# ===========================================================================
# Each rule returns a boolean Series indexed like its table: True = row FAILS.
# severity: ERROR = wrong / breaks a join or calculation
#           WARN  = probably wrong, investigate (kept + flagged, not fixed)
#           INFO  = worth knowing
# group:    column | single_table | cross_table   (referential integrity is
#           handled by check_referential_integrity above)

def _rules_column_level():
    """Range and allowed-value rules, generated from the schema."""
    rules = []
    for (t, c), (lo, hi) in S.RANGES.items():
        def f(tb, t=t, c=c, lo=lo, hi=hi):
            v = num(tb[t][c])
            bad = pd.Series(False, index=tb[t].index)
            if lo is not None:
                bad |= v < lo
            if hi is not None:
                bad |= v > hi
            return bad & v.notna()
        sign = c == "shares" or (lo is not None and lo > 0 and hi is None)
        rules.append(dict(table=t, column=c, group="column", severity="ERROR",
                          dimension="Validity",
                          name=f"{c} {'sign rule' if sign else 'range'} [{lo}, {hi}]",
                          func=f))
    for (t, c), allowed in S.ALLOWED_VALUES.items():
        def f(tb, t=t, c=c, allowed=allowed):
            s = tb[t][c]
            return s.ne("") & ~s.isin(allowed)
        rules.append(dict(table=t, column=c, group="column", severity="ERROR",
                          dimension="Validity / Consistency",
                          name=f"{c} in allowed code list", func=f))
    return rules


def _client_lookup(tb, col):
    return tb["dim_client"].set_index("client_id")[col]


def _rules_business():
    R = []

    def add(table, column, group, severity, dimension, name, func):
        R.append(dict(table=table, column=column, group=group, severity=severity,
                      dimension=dimension, name=name, func=func))

    # ----- dim_client -------------------------------------------------------
    def near_dup_client(tb):
        df = tb["dim_client"]
        return df.duplicated(S.BUSINESS_KEYS["dim_client"], keep="first")
    add("dim_client", "client_id", "single_table", "ERROR", "Uniqueness",
        "near-duplicate client (same person, second ID)", near_dup_client)

    def blank_risk(tb):
        return tb["dim_client"]["risk_profile"].eq("")
    add("dim_client", "risk_profile", "single_table", "ERROR", "Completeness",
        "risk_profile is blank", blank_risk)

    def tier_vs_aum(tb):
        df = tb["dim_client"]
        a = num(df["initial_aum"])
        bad = pd.Series(False, index=df.index)
        for tier, (lo, hi) in S.TIER_AUM.items():
            m = df["client_tier"].eq(tier)
            bad |= m & ((a < lo) | ((a >= hi) if hi else False))
        return bad
    add("dim_client", "client_tier", "single_table", "ERROR", "Consistency",
        "client_tier disagrees with initial_aum band", tier_vs_aum)

    # ----- dim_date ---------------------------------------------------------
    def date_parts(tb):
        df = tb["dim_date"]
        d = pd.to_datetime(df["date"], errors="coerce")
        return ((d.dt.year != num(df["year"])) | (d.dt.month != num(df["month"]))
                | (d.dt.quarter != num(df["quarter"]))
                | (d.dt.day_name() != df["day_of_week"])
                | (d.dt.month_name() != df["month_name"])
                | (d.dt.is_month_end.astype(int) != num(df["is_month_end"]))
                | (d.dt.is_quarter_end.astype(int) != num(df["is_quarter_end"]))
                | (d.dt.is_year_end.astype(int) != num(df["is_year_end"]))
                | (d.dt.isocalendar().week.astype("int64") != num(df["week_of_year"]))
                # a weekend can never be a trading day; a weekday CAN be non-trading
                # (market holidays), so only the weekend direction is an error
                | ((d.dt.dayofweek >= 5) & df["is_trading_day"].eq("1")))
    add("dim_date", "date", "single_table", "ERROR", "Consistency",
        "calendar attributes disagree with the date", date_parts)

    # ----- dim_security -----------------------------------------------------
    def etf_fields(tb):
        df = tb["dim_security"]
        etf = df["is_etf"].eq("True")
        return ((etf & (df["sector"].ne("") | df["expense_ratio_bps"].eq("")))
                | (~etf & (df["sector"].eq("") | df["expense_ratio_bps"].ne(""))))
    add("dim_security", "is_etf", "single_table", "ERROR", "Consistency",
        "sector / expense_ratio blank pattern contradicts is_etf", etf_fields)

    # ----- fact_fees --------------------------------------------------------
    def fee_math(tb):
        df = tb["fact_fees"]
        calc = num(df["aum_basis"]) * num(df["bps_charged"]) / 10000 / 12
        bad_text = unreadable(df["aum_basis"]) | unreadable(df["bps_charged"]) | unreadable(df["amount"])
        return bad_text | ((calc - num(df["amount"])).abs() > RECON_TOL_MONEY)
    add("fact_fees", "amount", "single_table", "ERROR", "Accuracy",
        "amount != aum_basis x bps / 10,000 / 12", fee_math)

    # ----- fact_portfolio_snapshot -----------------------------------------
    def ret_recon(tb):
        df = tb["fact_portfolio_snapshot"]
        r, b, a = num(df["return_ytd"]), num(df["benchmark_return_ytd"]), num(df["active_alpha_ytd"])
        bad_text = (unreadable(df["return_ytd"]) | unreadable(df["benchmark_return_ytd"])
                    | unreadable(df["active_alpha_ytd"]))
        return bad_text | ((r - (b + a)).abs() > RECON_TOL_RETURN)
    add("fact_portfolio_snapshot", "return_ytd", "single_table", "ERROR", "Accuracy",
        "return_ytd != benchmark_return_ytd + active_alpha_ytd", ret_recon)

    def snap_period(tb):
        df = tb["fact_portfolio_snapshot"]
        d = pd.to_datetime(df["snapshot_date"], errors="coerce")
        return (d.dt.year != num(df["year"])) | (d.dt.month != num(df["month"])) | (d.dt.day != 1)
    add("fact_portfolio_snapshot", "snapshot_date", "single_table", "ERROR", "Consistency",
        "year/month columns disagree with snapshot_date", snap_period)

    def extreme_return(tb):
        df = tb["fact_portfolio_snapshot"]
        return num(df["return_ytd"]).abs() > 1.0
    add("fact_portfolio_snapshot", "return_ytd", "single_table", "WARN",
        "Accuracy/Plausibility", "|return_ytd| above 100% in one year", extreme_return)

    def aum_floor(tb):
        df = tb["fact_portfolio_snapshot"]
        return num(df["aum"]).eq(1000.0)
    add("fact_portfolio_snapshot", "aum", "single_table", "WARN",
        "Accuracy/Plausibility", "aum stuck at exactly $1,000.00 (system floor)", aum_floor)

    # ----- fact_transactions ------------------------------------------------
    def txn_shape(tb):
        df = tb["fact_transactions"]
        cash = df["txn_type"].isin(S.CASH_FLOW_TYPES)
        sec = df["txn_type"].isin(S.SECURITY_TYPES)
        filled = df[["security_id", "shares", "price"]].ne("")
        return (cash & filled.any(axis=1)) | (sec & ~filled.all(axis=1))
    add("fact_transactions", "txn_type", "single_table", "ERROR", "Consistency",
        "security/shares/price blank pattern contradicts txn_type", txn_shape)

    def txn_math(tb):
        df = tb["fact_transactions"]
        sh, px, am = num(df["shares"]), num(df["price"]), num(df["amount"])
        m = df["shares"].ne("") & df["price"].ne("")   # rows that SHOULD reconcile
        bad_text = unreadable(df["shares"]) | unreadable(df["price"]) | unreadable(df["amount"])
        return m & (bad_text | ((sh * px - am).abs() > RECON_TOL_MONEY))
    add("fact_transactions", "amount", "single_table", "ERROR", "Accuracy",
        "amount != shares x price", txn_math)

    def dividend_full_value(tb):
        df = tb["fact_transactions"]
        d = df["txn_type"].eq("Dividend")
        sh, px, am = num(df["shares"]), num(df["price"]), num(df["amount"])
        return d & ((sh.abs() * px - am).abs() <= RECON_TOL_MONEY)
    add("fact_transactions", "amount", "single_table", "INFO", "Accuracy/Plausibility",
        "Dividend amount equals the full position value (100% yield)", dividend_full_value)

    # ----- cross-table ------------------------------------------------------
    for t in ("fact_fees", "fact_portfolio_snapshot", "fact_transactions"):
        def adv(tb, t=t):
            df = tb[t]
            exp = df["client_id"].map(_client_lookup(tb, "advisor_id"))
            return exp.notna() & (int_key(df["advisor_id"]) != int_key(exp.fillna("")))
        add(t, "advisor_id", "cross_table", "ERROR", "Consistency",
            "advisor_id differs from the client's advisor in dim_client", adv)

        datecol = {"fact_fees": "fee_date", "fact_portfolio_snapshot": "snapshot_date",
                   "fact_transactions": "txn_date"}[t]

        def before_start(tb, t=t, datecol=datecol):
            df = tb[t]
            since = df["client_id"].map(_client_lookup(tb, "client_since"))
            # monthly facts are dated the 1st, so compare at month level for them
            if t == "fact_transactions":
                return since.notna() & (df[datecol] < since.fillna(""))
            return since.notna() & (df[datecol] < since.fillna("").str[:7] + "-01")
        add(t, datecol, "cross_table", "ERROR", "Consistency",
            "activity dated before the client relationship began", before_start)

    def acct_type(tb):
        df = tb["fact_portfolio_snapshot"]
        exp = df["client_id"].map(_client_lookup(tb, "primary_account_type"))
        return exp.notna() & (df["account_type"] != exp)
    add("fact_portfolio_snapshot", "account_type", "cross_table", "ERROR", "Consistency",
        "account_type differs from client's primary_account_type", acct_type)

    def bench_vs_risk(tb):
        df = tb["fact_portfolio_snapshot"]
        risk = df["client_id"].map(_client_lookup(tb, "risk_profile"))
        exp = risk.map(S.RISK_TO_BENCHMARK)
        return exp.notna() & (int_key(df["benchmark_id"]) != exp)
    add("fact_portfolio_snapshot", "benchmark_id", "cross_table", "ERROR", "Consistency",
        "benchmark_id does not match the client's risk profile", bench_vs_risk)

    def fee_vs_snapshot(tb):
        f = tb["fact_fees"]
        p = tb["fact_portfolio_snapshot"]
        aum = p.set_index(p["client_id"] + "|" + p["snapshot_date"])["aum"]
        aum = aum[~aum.index.duplicated()]
        exp = (f["client_id"] + "|" + f["fee_date"]).map(aum)
        return exp.isna() | ((num(f["aum_basis"]) - num(exp.fillna(""))).abs() > RECON_TOL_MONEY)
    add("fact_fees", "aum_basis", "cross_table", "ERROR", "Accuracy",
        "aum_basis != snapshot aum for the same client and month", fee_vs_snapshot)

    def trade_non_trading_day(tb):
        df = tb["fact_transactions"]
        td = tb["dim_date"].set_index("date")["is_trading_day"]
        return df["txn_type"].isin(S.TRADE_TYPES) & df["txn_date"].map(td).eq("0")
    add("fact_transactions", "txn_date", "cross_table", "WARN", "Accuracy/Plausibility",
        "Buy/Sell dated on a non-trading day (markets closed)", trade_non_trading_day)

    def after_exit(tb):
        df = tb["fact_transactions"]
        c = tb["dim_client"]
        inactive = set(c.loc[c["is_active"].eq("False"), "client_id"])
        snaps = tb["fact_portfolio_snapshot"]
        last = snaps.groupby("client_id")["snapshot_date"].max().str[:7] + "-31"
        m = df["client_id"].isin(inactive)
        return m & (df["txn_date"] > df["client_id"].map(last).fillna("9999"))
    add("fact_transactions", "txn_date", "cross_table", "WARN", "Accuracy/Plausibility",
        "activity after an inactive client's last month on the books", after_exit)

    return R


ALL_RULES = _rules_column_level() + _rules_business()


def evaluate_rules(tables):
    """Run every rule. Returns {table: DataFrame of fail flags} and a summary."""
    masks = {t: pd.DataFrame(index=tables[t].index) for t in S.TABLES}
    rows = []
    for r in ALL_RULES:
        bad = r["func"](tables).fillna(False).astype(bool)
        label = f"{r['severity']}: {r['name']}"
        masks[r["table"]][label] = bad
        n = len(bad)
        ex = ""
        if bad.any():
            pk = S.PRIMARY_KEYS[r["table"]]
            sample = tables[r["table"]].loc[bad].head(3)
            ex = "; ".join(f"{pk}={row[pk]} {r['column']}={row[r['column']]!r}"
                           for _, row in sample.iterrows())
        rows.append(dict(table=r["table"], column=r["column"], check_group=r["group"],
                         check=r["name"], severity=r["severity"], dimension=r["dimension"],
                         rows_checked=n, rows_failed=int(bad.sum()),
                         pct_failed=round(100 * bad.mean(), 4) if n else 0.0, example=ex))
    return masks, pd.DataFrame(rows)


# ===========================================================================
# 5. Cross-table reconciliations (recompute and compare)
# ===========================================================================
def reconciliations(tables):
    out = []
    f, p, t = tables["fact_fees"], tables["fact_portfolio_snapshot"], tables["fact_transactions"]

    # (a) fee amount recomputed from aum_basis x bps / 12
    calc = num(f["aum_basis"]) * num(f["bps_charged"]) / 10000 / 12
    diff = (calc - num(f["amount"])).abs()
    out.append(dict(reconciliation="fact_fees.amount vs aum_basis x bps/10,000/12",
                    rows=len(f), rows_agree=int((diff <= RECON_TOL_MONEY).sum()),
                    total_stored=round(num(f["amount"]).sum(), 2),
                    total_compared=round(calc.sum(), 2)))

    # (b) fee aum_basis vs portfolio snapshot aum (two tables, same fact)
    bad = [r for r in ALL_RULES if r["name"].startswith("aum_basis != snapshot")][0]["func"](tables)
    out.append(dict(reconciliation="fact_fees.aum_basis vs fact_portfolio_snapshot.aum (same client-month)",
                    rows=len(f), rows_agree=int((~bad).sum()),
                    total_stored=round(num(f["aum_basis"]).sum(), 2), total_compared=np.nan))

    # (c) trade amount recomputed as shares x price
    m = t["shares"].ne("") & t["price"].ne("")
    calc = num(t.loc[m, "shares"]) * num(t.loc[m, "price"])
    diff = (calc - num(t.loc[m, "amount"])).abs()
    out.append(dict(reconciliation="fact_transactions.amount vs shares x price (Buy/Sell/Dividend)",
                    rows=int(m.sum()), rows_agree=int((diff <= RECON_TOL_MONEY).sum()),
                    total_stored=round(num(t.loc[m, "amount"]).sum(), 2),
                    total_compared=round(calc.sum(), 2)))

    # (d) return_ytd recomputed as benchmark + alpha
    r = num(p["return_ytd"])
    calc = num(p["benchmark_return_ytd"]) + num(p["active_alpha_ytd"])
    out.append(dict(reconciliation="snapshot.return_ytd vs benchmark_return_ytd + active_alpha_ytd",
                    rows=len(p), rows_agree=int(((r - calc).abs() <= RECON_TOL_RETURN).sum()),
                    total_stored=np.nan, total_compared=np.nan))

    # (e) advisory-fee cash debits vs the fee table, per client-month
    af = t[t["txn_type"].eq("Advisory Fee")].copy()
    af["ym"] = af["txn_date"].str[:7]
    af["amt"] = num(af["amount"])
    a = af.groupby(["client_id", "ym"])["amt"].sum()
    ff = f.copy()
    ff["ym"] = ff["fee_date"].str[:7]
    ff["amt"] = num(ff["amount"])
    b = ff.groupby(["client_id", "ym"])["amt"].sum()
    j = pd.concat([a.rename("txn"), b.rename("fee")], axis=1).dropna()
    out.append(dict(reconciliation="Advisory Fee debits (transactions) vs fact_fees, same client-month",
                    rows=len(j), rows_agree=int(((j["txn"] - j["fee"]).abs() <= RECON_TOL_MONEY).sum()),
                    total_stored=round(num(af["amount"]).sum(), 2),
                    total_compared=round(num(f["amount"]).sum(), 2)))

    df = pd.DataFrame(out)
    # total_stored = the stored column; total_compared = what it is checked against
    # (a recomputed value, or for the advisory-fee check, the fact_fees total)
    df["agree_pct"] = (100 * df["rows_agree"] / df["rows"]).round(4)
    return df


# ===========================================================================
# 6. IQR outliers (numeric columns with no natural upper bound)
# ===========================================================================
IQR_COLUMNS = [
    ("fact_transactions", "amount"),
    ("fact_fees", "amount"),
    ("fact_portfolio_snapshot", "aum"),
]


def iqr_outliers(tables, k=1.5):
    rows = []
    for t, c in IQR_COLUMNS:
        v = num(tables[t][c]).dropna()
        q1, q3 = v.quantile(0.25), v.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - k * iqr, q3 + k * iqr
        n_out = int(((v < lo) | (v > hi)).sum())
        rows.append(dict(table=t, column=c, q1=round(q1, 2), q3=round(q3, 2),
                         lower_fence=round(lo, 2), upper_fence=round(hi, 2),
                         outliers=n_out, outlier_pct=round(100 * n_out / len(v), 2)))
    return pd.DataFrame(rows)


IQR_NOTE = ("Flagged does not mean wrong: Wildcat serves Retail, HNW and UHNW clients, so "
            "money columns are heavily right-skewed and most IQR 'outliers' are simply the "
            "firm's largest (UHNW) accounts; they are kept and only reviewed.")


# ===========================================================================
# 7. Scorecard
# ===========================================================================
def scorecard(tables, stage, masks=None):
    if masks is None:
        masks, _ = evaluate_rules(tables)
    rows = []
    for t in S.TABLES:
        df = tables[t]
        types = S.COLUMN_TYPES[t]
        n = len(df)
        cols = list(types)  # original columns only (flag columns are extra)

        # completeness: a blank counts as complete only where it is legitimate
        filled = 0
        for c in cols:
            ok = df[c].ne("") | expected_blank_mask(tables, t, c)
            filled += int(ok.sum())
        completeness = 100 * filled / (n * len(cols))

        # key uniqueness: primary key unique AND no business-key duplicates
        pk = S.PRIMARY_KEYS[t]
        dup = df[pk].duplicated(keep=False) | df.duplicated(S.BUSINESS_KEYS[t], keep="first")
        key_unique = 100 * (1 - dup.mean())

        # type validity: share of non-blank cells written as their expected type
        good = total = 0
        for c in cols:
            nonblank = df[c].ne("")
            good += int((type_valid_mask(df[c], types[c]) & nonblank).sum())
            total += int(nonblank.sum())
        type_valid = 100 * good / total

        m = masks[t]
        err_cols = [c for c in m.columns if c.startswith("ERROR")]
        warn_cols = [c for c in m.columns if c.startswith("WARN")]
        rule_pass = 100 * (1 - m[err_cols].any(axis=1).mean()) if err_cols else 100.0
        warn_pass = 100 * (1 - m[warn_cols].any(axis=1).mean()) if warn_cols else 100.0

        # referential match: rows whose every foreign key finds a parent
        rels = [r for r in S.RELATIONSHIPS if r[0] == t]
        if rels:
            orphan_any = pd.Series(False, index=df.index)
            for child, ck, parent, pkey in rels:
                orphan_any |= check_referential_integrity(df, ck, tables[parent], pkey)["orphan_mask"]
            ref = 100 * (1 - orphan_any.mean())
        else:
            ref = np.nan  # this table has no foreign keys

        rows.append(dict(table=t, stage=stage, rows=n,
                         pct_completeness=round(completeness, 3),
                         pct_key_uniqueness=round(key_unique, 3),
                         pct_type_validity=round(type_valid, 3),
                         pct_rule_pass=round(rule_pass, 3),
                         pct_plausibility_pass=round(warn_pass, 3),
                         pct_referential_match=round(ref, 3) if rels else "n/a (no FKs)"))
    return pd.DataFrame(rows)


# ===========================================================================
# Main
# ===========================================================================
def main():
    S.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    results = {}
    for stage, folder in (("raw", S.RAW_DIR), ("clean", S.CLEAN_DIR)):
        if not (Path(folder) / "fact_transactions.csv").exists():
            sys.exit(f"Missing {folder}. Run 02_clean.py first.")
        tb = load_tables(folder)
        print(f"\n{'=' * 78}\nSTAGE: {stage.upper()}  ({folder})\n{'=' * 78}")

        ri = run_all_relationships(tb)
        print("\n-- Referential integrity (13 relationships) --")
        print(ri[["fact_table", "fact_key", "dim_table", "match_rate", "orphan_rows",
                  "distinct_orphan_keys", "null_key_rate", "match_rate_by_value"]]
              .to_string(index=False))

        masks, rules = evaluate_rules(tb)
        print("\n-- Rules that failed at least one row --")
        print(rules[rules.rows_failed > 0][["table", "check", "severity", "rows_failed"]]
              .to_string(index=False))

        rec = reconciliations(tb)
        print("\n-- Reconciliations --")
        print(rec[["reconciliation", "rows", "rows_agree", "agree_pct"]].to_string(index=False))

        iqr = iqr_outliers(tb)
        print("\n-- IQR outliers --")
        print(iqr.to_string(index=False))
        print("Note:", IQR_NOTE)

        sc = scorecard(tb, stage, masks)
        results[stage] = dict(ri=ri, rules=rules, rec=rec, iqr=iqr, sc=sc)

    card = pd.concat([results["raw"]["sc"], results["clean"]["sc"]])
    card = card.sort_values(["table", "stage"], ascending=[True, False])
    card.to_csv(S.REPORTS_DIR / "data_quality_scorecard.csv", index=False)

    # supporting detail (both stages side by side)
    for key, name in (("ri", "referential_integrity"), ("rules", "rule_checks"),
                      ("rec", "reconciliations"), ("iqr", "iqr_outliers")):
        both = pd.concat([results[s][key].assign(stage=s) for s in ("raw", "clean")])
        both.to_csv(S.REPORTS_DIR / f"validation_{name}.csv", index=False)

    print(f"\n{'=' * 78}\nDATA QUALITY SCORECARD (raw vs clean)\n{'=' * 78}")
    print(card.to_string(index=False))
    print(f"\nSaved {S.REPORTS_DIR / 'data_quality_scorecard.csv'} and validation_*.csv")

    # The clean data must pass every hard rule and every join.
    clean = results["clean"]
    assert (clean["ri"]["orphan_rows"] == 0).all(), "clean data still has orphan keys"
    hard = clean["rules"][(clean["rules"].severity == "ERROR") & (clean["rules"].rows_failed > 0)]
    assert hard.empty, f"clean data still fails hard rules:\n{hard}"
    print("PASS: clean tables have 0 orphan keys and 0 hard-rule failures.")


if __name__ == "__main__":
    main()
