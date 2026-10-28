# HW5 — Wildcat Capital as a Star Schema in Power BI

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

Works out how the eight clean Wildcat Capital tables fit together (keys, grain, additivity), proves it in Python, and builds the star schema in Power BI for Assignment 6.

## Folder structure

```
hw05/
├── README.md               ← this file
├── star_design.md          ← Parts A, B, C, E and F
├── scripts/
│   └── hw05_checks.py      ← proves Parts A–C (keys, integrity, grain, measure list)
├── reports/
│   ├── keys_check.csv      ← every PK and FK check, pass/fail
│   ├── grain_check.csv     ← uniqueness at each fact's grain
│   └── measures.csv        ← every numeric fact column and its class
└── powerbi/
    ├── BUILD_STEPS.md      ← exact Power BI settings used for Part D (follows powerbi_guide.md)
    ├── hw05.pbix           ← Part D model (also holds the row-count DAX query)
    ├── model_view.png      ← Part D screenshot: 8 tables, 13 relationships
    └── row_counts.png      ← COUNTROWS for all 8 tables in Power BI vs. the brief
```

## How to run

```bash
python hw05/scripts/hw05_checks.py
# or, against my own HW4 output:
python hw05/scripts/hw05_checks.py --data hw04/data/clean
```

Needs Python 3.9+ and pandas. Runs in about 15 seconds to a minute, depending on the computer. It reads the instructor's release from `Data/Wildcat_Capital_Clean/` by default (the CSVs are git-ignored by the repo-root `.gitignore`; download them from the course site to rerun) and reuses `check_referential_integrity()` and `load_tables()` from `hw04/scripts/03_validate.py`, so HW4 and HW5 measure integrity the same way. It stops with an `AssertionError` if any check fails.

**Data note:** everything (script and Power BI) uses the instructor's `Wildcat Capital Clean` release, as the brief requires. My own HW4 output has identical row counts and passes every check too (`--data hw04/data/clean`); it differs only in its flag columns.

## Results at a glance

| Check | Result |
|---|---|
| Primary keys unique and never blank | 8 of 8 (plus `dim_date[date]` as an alternate key) |
| Foreign keys matching their parent | 13 of 13 at 100%, 0 orphans |
| Fact dates matching `dim_date[date]` / `dim_date[date_id]` | 100% / 0% |
| Blank `security_id` | 101,528 rows, exactly the Deposit, Withdrawal and Advisory Fee rows |
| Fact `advisor_id` = `dim_client.advisor_id` | 100% on all three facts |
| Grain unique | fees: client + month · snapshot: client + month · transactions: txn_id |
| Power BI relationships | 11 active (fact → dimension, \*:1, single) + 2 inactive dimension-to-dimension links |
| Power BI row counts | All 8 tables match the brief exactly (`row_counts.png`, DAX query saved in the .pbix) |
| Date table | `dim_date` marked as the date table on `date` ("Validated successfully") |

## Power BI notes

- Loaded from the instructor's `Wildcat Capital Clean` files, following `powerbi_guide.md`. Column types were checked for all 77 columns of the eight files with `INFO.VIEW.COLUMNS()` (it listed 78 at the time, including the `dim_advisor[Advisor]` calculated column I later deleted); Power BI's guesses were already correct (IDs whole number, the five dates Date, ZIP and account types Text).
- No new tables or columns, as the brief requires. The model has one measure, `Total Fees = SUM(fact_fees[amount])` (the guide's optional additive example), stored on `fact_fees`.
- Row counts were reconciled inside Power BI with a DAX query (`EVALUATE {("dim_advisor", COUNTROWS(dim_advisor), 25), …}`) that lists each table's count next to the number in the brief; it is saved in the DAX query view of `hw05.pbix`.

## Review findings and what I did about them

### Caught while drafting and testing

| # | What came up | What I did |
|---|---|---|
| 1 | My first guess for the transaction grain was client + security + date + type, but 1,238 rows share that combination with another row (622 extra copies) | Grain stated as one row per transaction event (`txn_id`); the script prints both counts as evidence |
| 2 | The obvious fix for quarterly AUM is to filter `dim_date[is_quarter_end]`, but snapshots are dated the **1st** and the flag marks the **last** day: 0 of 129,547 snapshots match | Used as the Part F example of a question the schema can't answer in one visual, with a proposed fix |
| 3 | `fact_transactions.amount` has no negative values, so SUM adds withdrawals to deposits | Classified as additive **within one `txn_type`** and used in Part F |
| 4 | The script could silently skip a numeric column I forgot to classify | It now asserts that every numeric fact column appears in the Part C list |

### Claude review before committing

Claude reviewed `scripts/hw05_checks.py`, `star_design.md`, this README and the Power BI model, checking every claim against the script output or the live model. (Run from Claude with access to my repo and the Apporto session, not from the VS Code extension.)

| # | What the review flagged | What I did |
|---|---|---|
| 1 | README said the script also runs on my HW4 output, but it crashed there (`KeyError: 'is_return_suspect'`): the two data versions name their flag columns differently | **Fixed.** Both sets of flag names are listed in Part C; the script checks only the columns present in the folder and still asserts every numeric fact column is classified. Both `--data` options now pass. |
| 2 | The model had a calculated column (`dim_advisor[Advisor]`) and an extra `_Measure` table, but the brief says no new columns or tables | **Fixed.** Deleted the column; moved the measure onto `fact_fees` and deleted `_Measure`. Retook `model_view.png`. |
| 3 | The measure was named `Total Feees` | **Fixed:** renamed `Total Fees`. |
| 4 | Rubric D asks for row counts that reconcile, but they were only checked in Python | **Fixed.** Added the COUNTROWS query in Power BI (`row_counts.png`): all 8 tables match. |
| 5 | `dim_security → dim_benchmark` was active in the model, while `star_design.md` says both dimension-to-dimension links are inactive; `dim_client → dim_advisor` was missing | **Fixed in the model** to match the design (both inactive) |
| 6 | `dim_date` was not marked as a date table, so Power BI was still building hidden auto date tables for it | **Fixed:** marked on `date`; the hidden table for `dim_date` was removed |

### Claude Code review (VS Code)

| # | What Claude Code flagged | What I did |
|---|---|---|
| 1 | The `advisor_id` agreement check (fact vs. `dim_client`) and the one-benchmark-per-client check printed results but never stopped the script, even though Part E(b) relies on them | **Fixed.** Both now assert; the script still passes (100% agreement, 1 benchmark per client). |
| 2 | "622 rows share client + security + date + type" was wrong: `duplicated()` counts only the extra copies. 1,238 rows share a combination; 1,050 of them are cash flows with a blank `security_id` | **Fixed.** The script prints both counts and the cash/trade split; `star_design.md` and finding #1 above now say 1,238 (622 extra copies). |
| 3 | "Every claim below is checked in the script" overstated it: the dividend, flag-count, month-end, bps and price figures were checked separately, not in the script (all correct) | **Fixed.** Added an "Other figures quoted in star_design.md" section that computes each one: 53,826 of 53,826 dividends = shares × price, 3,875 suspect returns, 2,410 post-departure transactions, 0 snapshots on month-end/quarter-end days, bps within 0.60, Buy/Sell amount = shares × price on 100% of rows, expense ratio blank on 281 of 281 non-ETFs. |
| 4 | The blank-`security_id` result was written to the report as a hard-coded `passed: True` | **Fixed.** It is now computed from the two conditions, and asserted with a message. |
| 5 | The "no column forgotten" check could miss a numeric column with one stray text value, and would treat an all-blank column as numeric | **Fixed.** A column now counts as numeric when most of its non-blank values parse as numbers; blank-only columns are skipped. |
| 6 | The grain check didn't strip spaces, unlike the primary-key check | **Fixed.** Values are stripped before testing (no number changes; the data has no stray spaces). |
| 7 | The AUM and cash demos used hard-coded dates and would silently print $0 on data without them | **Fixed.** The script now stops if those snapshot dates are missing. |
| 8 | The date-join assert had no message | **Fixed.** It now names the table and column. |
| 9 | README said "about 20 seconds" (it took 63 s on my laptop), "78 columns" (the files have 77), and the commit plan didn't match the real commit messages | **Fixed** all three. |

Claude Code could not open the .pbix, so the Power BI items (relationships, date table, measure, row counts) rest on the Power BI checks above and `row_counts.png`.

## Commits

1. `HW5 Parts A-C: key, integrity and grain checks - 13/13 FKs 100%, fact dates join on dim_date[date]`
2. `HW5 Parts A-C, E, F: star_design.md and README with review findings`
3. `HW5 Part D: Power BI model - 11 active + 2 inactive relationships, dim_date marked, row counts reconcile`
4. `HW5: Claude Code review - enforce advisor_id agreement check with an assert`
5. `HW5: Claude Code review fixes - assert every check, compute every quoted figure`
