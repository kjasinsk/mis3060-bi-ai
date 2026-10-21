# HW4 — Cleaning the Wildcat Capital Data

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

The project audits eight Wildcat Capital tables, documents a decision for every issue, cleans them without inventing data, and proves the result with referential-integrity checks, business rules, reconciliations and a raw-vs-clean scorecard.

## Folder structure

```
hw04/
├── README.md                  ← this file
├── decision_log.md            ← Part B: one entry per issue (written before the cleaning code)
├── scripts/
│   ├── wildcat_schema.py      ← shared metadata: types, keys, relationships, allowed values, ranges
│   ├── 01_profile.py          ← Part A: generic profiler + 4 check groups
│   ├── 02_clean.py            ← Part C: step-by-step cleaning with asserts + audit trail
│   └── 03_validate.py         ← Part D: check_referential_integrity(), rules, reconciliations, IQR, scorecard
├── data/
│   ├── raw/                   ← the 8 original files (never modified)
│   ├── clean/                 ← 8 clean files + README_clean.md
│   └── audit/                 ← cleaning_log.csv, value_changes.csv, quarantine_*.csv
└── reports/
    ├── profile_raw.csv              ← one row per column (75 columns)
    ├── dq_summary_raw.csv           ← one row per finding, tagged ERROR / WARN / INFO
    ├── data_quality_scorecard.csv   ← one row per table per stage (raw / clean)
    ├── validation_*.csv             ← detail behind the scorecard (RI, rules, reconciliations, IQR)
    └── cleaning_report.md           ← Part E: report for the portfolio committee
```

## How to run

From the repo root (or anywhere: the scripts find their own folders):

```bash
python hw04/scripts/01_profile.py    # ~30 s  → reports/profile_raw.csv, dq_summary_raw.csv
python hw04/scripts/02_clean.py      # ~10 s  → data/clean/, data/audit/
python hw04/scripts/03_validate.py   # ~60 s  → reports/data_quality_scorecard.csv
```

Needs Python 3.9+ and pandas. Run them in order: 03 compares raw with clean, so 02 has to run first. `02_clean.py` stops with an `AssertionError` if any fix does not do what it claims, and it writes nothing until every check passes. `03_validate.py` ends by asserting that the clean data has 0 orphan keys and 0 hard-rule failures.

## Design choices worth knowing

- **Everything is read as text** (`dtype=str, keep_default_na=False`) and converted on purpose. This is how the audit caught `45.0` security IDs, `9.28%` returns, ZIP codes starting with 0, and the word `None` meaning "no certification".
- **One source of truth for rules.** `wildcat_schema.py` holds the facts about the data, and the check functions live in `03_validate.py`. `01_profile.py` and `02_clean.py` import them, so the audit, the cleaner and the validator all measure a problem the same way.
- **`check_referential_integrity(fact_df, fact_key, dim_df, dim_key)`** compares keys exactly as stored, like a text join in Power BI. It returns match rate, orphan rows, distinct orphan keys and null-key rate. Blank keys are counted as nulls, not orphans (a deposit has no security). It is run on all 13 relationships: 10 ID joins + 3 date joins. **Reused in Assignment 5.**
- **Fix, flag or quarantine.** A value is changed only when another column or table proves the right answer. Suspicious values that can't be proven wrong get a `flag_*` column, and rows that can't be kept go to `data/audit/quarantine_*.csv`.

## Results at a glance

| | Raw | Clean |
|---|---:|---:|
| fact_transactions rows joining to every dimension | 33.982% | 100% |
| fact_transactions type validity | 91.73% | 100% |
| dim_client rule pass | 93.069% | 100% |
| fact_portfolio_snapshot rule pass | 99.768% | 100% |
| dim_client key uniqueness | 99.01% | 100% |
| Rows quarantined | — | 225 (25 clients, 200 transactions) |
| Cells changed (logged in value_changes.csv) | — | 199,222 |

## Review findings and what I did about them

### Caught while drafting and testing the scripts

These came up while the scripts were being written and run, before the formal review:

| # | Script | What the review flagged | What I did |
|---|---|---|---|
| 1 | 03_validate.py | `check_referential_integrity` turned `45.0` into `45` before comparing, so the raw security-ID join showed 100% and **hid** the type defect | Made the default comparison exact (text), like Power BI. Added an optional `normalize_ids=True` and a `match_rate_by_value` column to separate "wrong format" from "missing key". Raw security-ID match now correctly shows 0%. |
| 2 | 03_validate.py | Return reconciliation used a tolerance of exactly 0.00005. One converted "%" value sat right on the boundary and failed from float rounding | Tolerance set to 0.0000501 (half a basis point plus float noise), with a comment explaining why |
| 3 | 01_profile.py | "Mixed formats" flagged any column with negative numbers (`-9.9` vs `9.9`), which was noise | The minus sign is ignored when judging format. Scientific notation is reported separately as WARN (correct value, different format), not ERROR |
| 4 | decision_log.md / 02_clean.py | A fee total typed into the decision log ($128.1M) did not match the data ($204.7M) | Corrected it. README_clean.md now **computes** every number it quotes instead of typing it |
| 5 | 03_validate.py | All rules ran twice per stage (once for the rule report, again inside the scorecard) | The scorecard reuses the first result. Fee totals are vectorized instead of using a per-group `lambda` |

### Claude Code review (VS Code, before committing)

I asked Claude Code to review all four scripts for bugs or anything that could produce wrong numbers. It found **no bug that changed the clean data**, but flagged the items below. After the fixes I re-ran all three scripts: the clean tables and audit trail are unchanged, and two raw-side numbers moved (shown in the table).

| # | What Claude Code flagged | What I did |
|---|---|---|
| 1 | The raw findings counted several problems twice (e.g. `45.0` failed both the int-type check and the join check), so the summary showed 14 ERRORs for about 8 real problems | **Fixed.** Added `dedupe_findings()` in 01_profile.py: when two checks flag the same table, column and row count, the first stays ERROR/WARN and the repeats become INFO with "same rows as: …". ERRORs went **14 → 8**. Negative shares and amount ≠ shares × price both stay ERROR because they are on different columns, though they share a cause. |
| 2 | Values that can't be read as numbers (e.g. `9.28%`) became NaN and quietly **passed** the math checks | **Fixed.** Added `unreadable()` in 03_validate.py; the fee, return and trade reconciliations now count an unreadable cell as a failure. Raw snapshot rule pass went **100% → 99.768%** (more honest). Range rules still skip them, because the type-validity check already counts those cells. |
| 3 | The flag step looked rules up by name only, and some names repeat across tables | **Fixed.** Lookup key is now (table, rule name). |
| 4 | Some ID ranges took min/max of text, where "9999" sorts after "10000" | **Fixed.** IDs are converted to numbers before min/max (01_profile.py and 02_clean.py). |
| 5 | Several claims were typed in rather than calculated ("dim_client max 2525", "benchmark 3 is used only by Balanced", "both agree 100%", "every relationship matches 100%", "300 converted returns", "25 clients") | **Fixed.** Each one is now computed from the data. README_clean.md runs `check_referential_integrity` itself before stating the match result. |
| 6 | The scientific-notation fix only looked at two columns | **Fixed.** It now checks every decimal column in every table, and asserts none are left. (Only the same two columns had it, so the output didn't change.) |
| 7 | The truncated-last-name test was looser than its note | **Fixed.** It now requires original = duplicate + extra letters at the end. The stricter test showed only **23 of 25** are truncations; the other 2 have an extra letter ("Leen" for "Lee", "Pacen" for "Pace"). They still match their original on every other column, so the quarantine decision stands, but I corrected the wording in the decision log, report and quarantine reason from "truncated" to "misspelled". |
| 8 | The "None" note always said "means no certification", for any column | **Fixed.** That wording is used only for `dim_advisor.certifications`. |
| 9 | Whitespace issues could count one cell twice | **Fixed.** Each cell is counted once. |
| 10 | README said "dated on a weekend" but the rule checks `is_trading_day = 0` | **Fixed** wording to "non-trading day (weekend or market holiday)". |
| 11 | The calendar check only caught a weekend marked as trading, not a weekday marked non-trading, and never checked `week_of_year` | **Partly fixed.** Added the ISO `week_of_year` check (all 1,827 days pass). **Left** weekday non-trading days allowed on purpose: market holidays fall on weekdays, so that direction is not an error. |
| 12 | The advisory-fee reconciliation's `total_recomputed` column was really the fee-table total | **Fixed.** Renamed to `total_compared`, with a comment saying what it holds for each check. |
| 13 | Filling risk profiles from the benchmark makes the benchmark-vs-risk check pass automatically for those 75 clients | **Left as is (not a bug).** I don't use that check as confirmation of the filled values. The `flag_risk_profile_inferred` column is what marks them for follow-up. |

## Commit plan (one per part)

1. `HW4 Part A: generic profiler + 4 check groups — 8 ERROR, 6 WARN, 83 INFO findings (duplicates counted once)`
2. `HW4 Part B: decision log — 21 entries (8 fixes, 4 flags, 7 legitimate structures, 2 known limitations)`
3. `HW4 Part C: clean 8 tables — 225 rows quarantined, 199,222 cells changed, shares reconciled to amount ÷ price`
4. `HW4 Part D: RI on 13 relationships, 5 reconciliations, IQR, scorecard — transactions referential match 33.98% → 100%`
5. `HW4 Part E: committee report from scorecard and decision log`

## Note on Git and CSV files

The repo-level `.gitignore` ignores `*.csv` (except files directly inside `hw*/`), which would leave out the clean data and the reports. `hw04/.gitignore` re-includes CSVs in this folder so the submission is complete.

## Note on commit history

The decision log (Part B) was committed in `0c6824a`, before any cleaning code, but the commit message was mislabeled "Part C" by mistake. The actual Part C commit is `e7b42d8`.
