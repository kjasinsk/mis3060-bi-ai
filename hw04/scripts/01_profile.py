"""
01_profile.py  -  HW4 Part A: audit the raw Wildcat Capital tables.

Plain-English summary:
  * profile_table() works on ANY table. For every column it reports blanks,
    distinct values, the most common value "shapes" (e.g. 9-9-9 for a date,
    9.9% for a percent string), how many values do not parse as the expected
    type, whitespace problems, mixed formats and numeric min/max.
  * Then four groups of checks are added, each finding tagged
    ERROR / WARN / INFO:
        1. column level      - type, allowed values, ranges, key uniqueness
        2. single-table      - duplicates, near-duplicates, row contradictions
        3. referential       - every foreign key must find its parent row
        4. cross-table       - facts that disagree with dimensions or each other
  * Saves reports/profile_raw.csv (one row per column) and
    reports/dq_summary_raw.csv (one row per finding).

All files are read as text (dtype=str, keep_default_na=False) so pandas
cannot silently "fix" anything before we see it.

Run from anywhere:  python hw04/scripts/01_profile.py [folder]
Author: Kaitlyn Jasinski
"""

import importlib
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wildcat_schema as S  # noqa: E402

V = importlib.import_module("03_validate")  # shared check functions


# ===========================================================================
# Generic column profiler (works on any table)
# ===========================================================================
def value_shape(v):
    """Turn a value into its pattern: letters -> A, digit runs -> 9.
    '2020-01-01' -> '9-9-9', '9.28%' -> '9.9%', 'Roth IRA' -> 'A A'."""
    if v == "":
        return "<blank>"
    s = re.sub(r"[A-Za-z]+", "A", v)
    return re.sub(r"\d+", "9", s)


def guess_type(s):
    """Best guess at a column's type when no schema is given."""
    nb = s[s.ne("")]
    if nb.empty:
        return "text"
    for t in ("flag01", "bool", "int", "date", "decimal"):
        if nb.str.match(V.TYPE_PATTERNS[t]).mean() >= 0.95:
            return t
    if pd.to_numeric(nb.str.rstrip("%"), errors="coerce").notna().mean() >= 0.95:
        return "decimal"
    return "text"


def profile_table(df, table_name, expected_types=None):
    """Profile every column of any DataFrame read as text."""
    expected_types = expected_types or {}
    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col].astype(str)
        blank = s.eq("")
        nonblank = s[~blank]
        exp = expected_types.get(col) or guess_type(s)

        shapes = s.map(value_shape).value_counts()
        nb_shapes = shapes.drop("<blank>", errors="ignore")
        dominant = nb_shapes.index[0] if len(nb_shapes) else ""
        # a minus sign is not a different format, so ignore it when judging "mixed"
        unsigned = nonblank.str.lstrip("-").map(value_shape).value_counts()
        minority = int(unsigned.iloc[1:].sum()) if len(unsigned) > 1 else 0

        valid = V.type_valid_mask(s, exp)
        fail_parse = int((~valid & ~blank).sum())

        numeric = pd.to_numeric(nonblank, errors="coerce")
        is_num = exp in ("int", "decimal", "flag01")
        ws_bad = (s != s.str.strip()) | s.str.contains(r"\s{2,}", regex=True)  # each cell once
        literal_null = int(s.str.strip().str.lower().isin(
            {"none", "null", "nan", "n/a", "na", "-"}).sum())

        rows.append({
            "table": table_name,
            "column": col,
            "expected_type": exp,
            "rows": n,
            "null_blank_count": int(blank.sum()),
            "null_blank_pct": round(100 * blank.mean(), 3),
            "literal_null_strings": literal_null,
            "distinct_count": int(s.nunique()),
            "top_shapes": "; ".join(f"{k} ({v})" for k, v in shapes.head(4).items()),
            "dominant_shape": dominant,
            "distinct_shapes": int(len(nb_shapes)),
            "distinct_shapes_ignoring_sign": int(len(unsigned)),
            "rows_not_dominant_shape": minority,
            "fail_parse_count": fail_parse,
            "fail_parse_pct": round(100 * fail_parse / max(len(nonblank), 1), 3),
            "whitespace_issues": int(ws_bad.sum()),
            "mixed_formats": "yes" if (exp != "text" and len(unsigned) > 1) else "no",
            "numeric_min": numeric.min() if is_num and numeric.notna().any() else "",
            "numeric_max": numeric.max() if is_num and numeric.notna().any() else "",
            "example_values": " | ".join(nonblank.drop_duplicates().head(3)),
        })
    return pd.DataFrame(rows)


# ===========================================================================
# Findings
# ===========================================================================
def finding(table, column, group, check, severity, dimension, count, rows, example="",
            note=""):
    return dict(table=table, column=column, check_group=group, check=check,
                severity=severity, dimension=dimension, rows_affected=int(count),
                pct_rows=round(100 * count / rows, 4) if rows else 0.0,
                example=example, note=note)


def column_findings(profile, tables):
    """Group 1 (column level) from the profile: type, blanks, whitespace,
    formats, key uniqueness."""
    out = []
    for _, p in profile.iterrows():
        t, c, n = p["table"], p["column"], p["rows"]
        df = tables[t]
        if p["fail_parse_count"]:
            bad = df[c][~V.type_valid_mask(df[c], p["expected_type"])]
            sci = bad.str.match(r"^-?\d+(\.\d+)?[eE][-+]?\d+$")
            if sci.any():  # a real number, just written differently
                out.append(finding(t, c, "1 column", "number written in scientific notation (9.9e-05)",
                                   "WARN", "Consistency", int(sci.sum()), n,
                                   ", ".join(bad[sci].drop_duplicates().head(3)),
                                   "value is correct; format differs from the rest of the column"))
            rest = bad[~sci]
            if len(rest):
                out.append(finding(t, c, "1 column", f"value not written as {p['expected_type']}",
                                   "ERROR", "Validity", len(rest), n,
                                   ", ".join(rest.drop_duplicates().head(4)),
                                   f"shapes seen: {p['top_shapes']}"))
        if p["null_blank_count"]:
            legit = V.expected_blank_mask(tables, t, c)
            blank = df[c].eq("")
            unexplained = int((blank & ~legit).sum())
            explained = int((blank & legit).sum())
            if explained:
                out.append(finding(t, c, "1 column", "blank where blank is correct (legitimate structure)",
                                   "INFO", "Completeness", explained, n, "",
                                   S.CONDITIONAL_BLANKS.get((t, c), "")))
            if unexplained:
                out.append(finding(t, c, "1 column", "blank where a value is required",
                                   "ERROR", "Completeness", unexplained, n))
        if p["literal_null_strings"]:
            lit = df[c][df[c].str.strip().str.lower().isin({"none", "null", "nan", "n/a", "na", "-"})]
            meaning = ("here it means 'no certification', so it is a real value"
                       if (t, c) == ("dim_advisor", "certifications")
                       else "check whether it means 'missing' or is a real value")
            out.append(finding(t, c, "1 column", "literal text 'None'/'null' stored as a value",
                               "INFO", "Validity", p["literal_null_strings"], n,
                               ", ".join(lit.drop_duplicates().head(3)),
                               "Default pd.read_csv would turn this into NaN; " + meaning))
        if p["whitespace_issues"]:
            out.append(finding(t, c, "1 column", "leading/trailing or double spaces",
                               "WARN", "Consistency", p["whitespace_issues"], n))
        if p["mixed_formats"] == "yes" and not p["fail_parse_count"]:
            out.append(finding(t, c, "1 column", "mixed number formats in one column",
                               "INFO", "Consistency", p["rows_not_dominant_shape"], n, "",
                               f"shapes: {p['top_shapes']}"))
        if t == "dim_client" and c == "zip_code":
            lz = int(df[c].str.startswith("0").sum())
            out.append(finding(t, c, "1 column", "ZIP codes with a leading zero (must stay text)",
                               "INFO", "Validity", lz, n, ", ".join(df[c][df[c].str.startswith('0')].head(3)),
                               "Numeric parsing would turn 02068 into 2068"))
    # primary key uniqueness
    for t, pk in S.PRIMARY_KEYS.items():
        d = int(tables[t][pk].duplicated(keep=False).sum())
        out.append(finding(t, pk, "1 column", "primary key unique",
                           "ERROR" if d else "INFO", "Uniqueness", d, len(tables[t]),
                           note="PASS: every key appears once" if not d else ""))
    # mixed formats inside an ID column that pandas would hide
    sid = tables["fact_transactions"]["security_id"]
    dot0 = int(sid.str.endswith(".0").sum())
    if dot0:
        out.append(finding("fact_transactions", "security_id", "1 column",
                           "integer ID stored as a float string ('45.0')", "ERROR",
                           "Validity / Consistency", dot0, len(sid), ", ".join(sid[sid.ne('')].head(3)),
                           "will not join to dim_security.security_id ('45') as text"))
    return out


def rule_findings(rules_df):
    """Groups 1, 2 and 4 from the shared rule engine in 03_validate.py."""
    out = []
    for _, r in rules_df.iterrows():
        group = {"column": "1 column", "single_table": "2 single-table",
                 "cross_table": "4 cross-table"}[r["check_group"]]
        sev = r["severity"] if r["rows_failed"] else "INFO"
        out.append(finding(r["table"], r["column"], group, r["check"], sev, r["dimension"],
                           r["rows_failed"], r["rows_checked"], r["example"],
                           "" if r["rows_failed"] else "PASS"))
    return out


def ri_findings(tables):
    """Group 3: every foreign key must point to an existing primary key."""
    out = []
    ri = V.run_all_relationships(tables)
    for _, r in ri.iterrows():
        sev = "ERROR" if r["orphan_rows"] else "INFO"
        out.append(finding(r["fact_table"], r["fact_key"], "3 referential",
                           f"{r['fact_key']} -> {r['dim_table']}.{r['dim_key']}", sev,
                           "Referential Integrity", r["orphan_rows"], r["rows"],
                           r["orphan_examples"],
                           f"text match rate {r['match_rate']:.4%} (by value {r['match_rate_by_value']:.4%}); "
                           f"{r['distinct_orphan_keys']} distinct orphan keys; "
                           f"null-key rate {r['null_key_rate']:.2%}"))
    return out, ri


def extra_findings(tables):
    """Investigations that explain WHY a problem exists and whether it can be
    repaired from other columns (the evidence for the decision log)."""
    out = []
    c = tables["dim_client"]
    p = tables["fact_portfolio_snapshot"]
    t = tables["fact_transactions"]
    f = tables["fact_fees"]

    # near-duplicate clients: which original do they copy, and are they used?
    bk = S.BUSINESS_KEYS["dim_client"]
    dup = c[c.duplicated(bk, keep="first")]
    if len(dup):
        orig = c.drop_duplicates(bk, keep="first").set_index(bk)
        pairs = dup.join(orig[["client_id", "last_name"]], on=bk, rsuffix="_original")
        # original = duplicate + extra letters at the end (e.g. 'Taylor' vs 'Taylo')
        trunc = int(pairs.apply(lambda r: len(r["last_name"]) > 0
                                and r["last_name_original"].startswith(r["last_name"])
                                and r["last_name_original"] != r["last_name"], axis=1).sum())
        dup_ids = dup["client_id"].astype(int)  # as numbers: as text "9999" > "10000"
        used = sum(tables[x]["client_id"].isin(set(dup["client_id"])).sum()
                   for x in ("fact_fees", "fact_portfolio_snapshot", "fact_transactions"))
        ex = "; ".join(f"{a} '{b}' copies {o} '{lo}'" for a, b, o, lo in
                       pairs[["client_id", "last_name", "client_id_original", "last_name_original"]]
                       .head(3).itertuples(index=False))
        out.append(finding("dim_client", "client_id", "2 single-table",
                           "near-duplicate client: all fields equal except ID and a misspelled last name",
                           "ERROR", "Uniqueness", len(dup), len(c), ex,
                           f"IDs {dup_ids.min()}-{dup_ids.max()}; {trunc} of {len(dup)} last names are the "
                           f"original with its ending cut off (the rest differ by one letter); fact rows that use these IDs: {used}"))

    # state written as a full name
    full = c["state"].isin(S.US_STATES)
    out.append(finding("dim_client", "state", "1 column", "state written as full name instead of 2-letter code",
                       "ERROR", "Consistency", int(full.sum()), len(c),
                       ", ".join(c.loc[full, "state"].value_counts().index[:4]),
                       "every full name maps to exactly one USPS code"))

    # blank risk profile: can the benchmark tell us the answer?
    blank = c["risk_profile"].eq("")
    bench = p.groupby("client_id")["benchmark_id"].agg(lambda s: ",".join(sorted(set(s))))
    b_of_blank = c.loc[blank, "client_id"].map(bench).value_counts(dropna=False).to_dict()
    known = c.loc[~blank, ["client_id", "risk_profile"]].assign(b=lambda d: d.client_id.map(bench)).dropna()
    rule_holds = (known["risk_profile"].map(S.RISK_TO_BENCHMARK) == known["b"]).mean()
    per_bench = {b: sorted(g.unique()) for b, g in known.groupby("b")["risk_profile"]}
    out.append(finding("dim_client", "risk_profile", "4 cross-table",
                       "blank risk_profile can be inferred from the client's benchmark",
                       "INFO", "Completeness", int(blank.sum()), len(c), "",
                       f"benchmark of blank-profile clients: {b_of_blank}; "
                       f"risk->benchmark rule holds for {rule_holds:.2%} of known clients; "
                       f"profiles using each benchmark: {per_bench}"))

    # orphan clients in transactions: what are they?
    tx_orphan = ~t["client_id"].isin(set(c["client_id"]))
    if tx_orphan.any():
        o = t[tx_orphan]
        seen_elsewhere = int(sum(tables[x]["client_id"].isin(set(o["client_id"])).sum()
                                 for x in ("fact_fees", "fact_portfolio_snapshot")))
        out.append(finding("fact_transactions", "client_id", "3 referential",
                           "orphan transactions profile", "ERROR", "Referential Integrity",
                           len(o), len(t),
                           f"txn_id {o.txn_id.astype(int).min()}-{o.txn_id.astype(int).max()}",
                           f"client_id range {o.client_id.astype(int).min()}-{o.client_id.astype(int).max()} "
                           f"vs dim_client max {c.client_id.astype(int).max()}; "
                           f"{o.client_id.nunique()} distinct client IDs across {len(o)} rows; "
                           f"found in fees/snapshots: {seen_elsewhere}"))

    # negative shares: is the sign the only problem?
    sh, px, am = V.num(t["shares"]), V.num(t["price"]), V.num(t["amount"])
    neg = sh < 0
    fixed_ok = ((sh[neg].abs() * px[neg] - am[neg]).abs() <= V.RECON_TOL_MONEY).mean() if neg.any() else 1
    out.append(finding("fact_transactions", "shares", "2 single-table",
                       "negative shares: does |shares| x price equal amount?", "INFO",
                       "Validity", int(neg.sum()), len(t),
                       f"types: {t.loc[neg, 'txn_type'].value_counts().to_dict()}",
                       f"{fixed_ok:.2%} reconcile exactly once the minus sign is removed"))

    # percent strings: do they reconcile after dividing by 100?
    pct = p["return_ytd"].str.endswith("%")
    val = V.num(p.loc[pct, "return_ytd"].str.rstrip("%")) / 100
    calc = V.num(p.loc[pct, "benchmark_return_ytd"]) + V.num(p.loc[pct, "active_alpha_ytd"])
    ok = ((val - calc).abs() <= V.RECON_TOL_RETURN).mean() if pct.any() else 1
    out.append(finding("fact_portfolio_snapshot", "return_ytd", "2 single-table",
                       "'9.28%' strings: do they equal benchmark + alpha after /100?", "INFO",
                       "Validity", int(pct.sum()), len(p),
                       ", ".join(p.loc[pct, "return_ytd"].head(3)),
                       f"{ok:.2%} reconcile within half a basis point"))

    # snapshots with no fee charged that month
    fk = set(f["client_id"] + "|" + f["fee_date"])
    nofee = ~(p["client_id"] + "|" + p["snapshot_date"]).isin(fk)
    out.append(finding("fact_portfolio_snapshot", "snapshot_date", "4 cross-table",
                       "client-month with an account snapshot but no fee charged", "INFO",
                       "Completeness", int(nofee.sum()), len(p), "",
                       "spread across all months and clients; fee waivers are normal, "
                       "and nothing in the data says what the fee should have been"))

    # inactive clients
    inactive = c[c["is_active"].eq("False") & c["client_id"].isin(set(p["client_id"]))]
    last = p.groupby("client_id")["snapshot_date"].max()
    out.append(finding("dim_client", "is_active", "4 cross-table",
                       "inactive clients' snapshots stop before Dec-2024 (expected)", "INFO",
                       "Consistency", len(inactive), len(c), "",
                       f"last snapshot of inactive clients ranges {last[inactive.client_id].min()} to "
                       f"{last[inactive.client_id].max()}; active clients' last snapshot: "
                       f"{sorted(last[~last.index.isin(set(inactive.client_id))].unique())}"))

    # unused dimension members
    used_b = set(p["benchmark_id"]) | set(tables["dim_security"]["benchmark_id"])
    unused_b = sorted(set(tables["dim_benchmark"]["benchmark_id"]) - used_b)
    out.append(finding("dim_benchmark", "benchmark_id", "3 referential",
                       "dimension rows that no fact or dimension uses", "INFO",
                       "Referential Integrity", len(unused_b), len(tables["dim_benchmark"]),
                       ", ".join(unused_b), "allowed: a dimension may list members not used yet"))
    return out


def dedupe_findings(summary):
    """Two checks that flag the same table + column + number of rows are one
    problem seen twice (e.g. '45.0' fails the int-type check AND the join).
    Keep the first as ERROR/WARN; downgrade the repeats to INFO and say which
    finding they repeat, so ERROR counts and row totals are not doubled."""
    summary = summary.copy()
    real = summary["severity"].isin(["ERROR", "WARN"]) & (summary["rows_affected"] > 0)
    key = summary["table"] + "|" + summary["column"] + "|" + summary["rows_affected"].astype(str)
    first = {}
    # when two checks see the same rows, keep the most specific one:
    # referential > column-level (names the root cause, e.g. wrong format) > single-table > cross-table
    priority = {"3 referential": 0, "1 column": 1, "2 single-table": 2, "4 cross-table": 3}
    ordered = sorted(summary.index[real], key=lambda i: (priority[summary.at[i, "check_group"]], i))
    for i in ordered:
        k = key[i]
        if k in first:
            summary.at[i, "note"] = (f"same rows as: '{summary.at[first[k], 'check']}' "
                                     f"(counted once). " + str(summary.at[i, "note"])).strip()
            summary.at[i, "severity"] = "INFO"
        else:
            first[k] = i
    return summary


# ===========================================================================
# Main
# ===========================================================================
def main(folder=S.RAW_DIR):
    S.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    tables = V.load_tables(folder)

    print("Rows / columns read (as text):")
    for t in S.TABLES:
        print(f"  {t:<26} {tables[t].shape[0]:>8,} rows  {tables[t].shape[1]:>3} cols")

    profile = pd.concat([profile_table(tables[t], t, S.COLUMN_TYPES.get(t)) for t in S.TABLES],
                        ignore_index=True)
    profile.to_csv(S.REPORTS_DIR / "profile_raw.csv", index=False)

    _, rules = V.evaluate_rules(tables)
    ri_list, ri = ri_findings(tables)
    findings = (column_findings(profile, tables) + rule_findings(rules) + ri_list
                + extra_findings(tables))
    summary = dedupe_findings(pd.DataFrame(findings))
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    summary = (summary.assign(_s=summary.severity.map(order))
               .sort_values(["_s", "check_group", "table", "column"])
               .drop(columns="_s"))
    summary.to_csv(S.REPORTS_DIR / "dq_summary_raw.csv", index=False)

    pd.set_option("display.width", 200)
    pd.set_option("display.max_colwidth", 70)
    print("\nColumns with something to look at:")
    look = profile[(profile.null_blank_count > 0) | (profile.fail_parse_count > 0)
                   | (profile.mixed_formats == "yes") | (profile.whitespace_issues > 0)]
    print(look[["table", "column", "null_blank_count", "fail_parse_count",
                "mixed_formats", "top_shapes"]].to_string(index=False))

    print("\nFindings by severity and group:")
    print(summary.groupby(["severity", "check_group"]).size().to_string())
    print("\nERROR and WARN findings:")
    print(summary[summary.severity != "INFO"][["severity", "table", "column", "check",
                                               "rows_affected"]].to_string(index=False))
    print(f"\nSaved {S.REPORTS_DIR / 'profile_raw.csv'} ({len(profile)} columns profiled)")
    print(f"Saved {S.REPORTS_DIR / 'dq_summary_raw.csv'} ({len(summary)} findings)")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else S.RAW_DIR)
