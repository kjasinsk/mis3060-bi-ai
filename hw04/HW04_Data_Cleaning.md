# HW4: Cleaning the Wildcat Capital Data
## MIS3060 Business Intelligence with AI | Villanova University
### Covers Weeks 6–8: data cleaning, wrangling, and referential integrity

> **Due:** *(instructor: set date)* | **Weight:** *(set in Brightspace)* | **Individual** | **Estimated effort:** 5–6 hours
> **Submission:** push to your `mis3060-bi-ai` repo, folder `hw04/`, and paste the folder URL into Brightspace
> **Tools:** Claude Desktop drafts every script · VS Code is where every script runs · Claude Code (in VS Code) reviews every script before you commit it

---

## Overview

Wildcat Capital is a wealth manager. Its data warehouse extract arrived as **eight tables**: five dimension tables and three fact tables. The tables come from different systems and have never been checked. Your job is to build Python programs that audit every table, find what is wrong, fix what can be fixed *without inventing data*, and prove the fix worked. Your output is a new, clean copy of all eight tables plus an audit trail.

You will not be given a list of problems. Finding them is part of the assignment, and part of the grade.

> **Coming next:** Assignment 5 builds a star schema in Power BI. It starts from a clean copy of this data, so the habits you build here (decide, verify, document) carry forward.

## Data

Folder: `Wildcat Capital/`. Use **only** these eight files:

| File | Rows | Cols | Role |
|---|---:|---:|---|
| `dim_advisor.csv` | 25 | 7 | Advisors |
| `dim_client.csv` | 2,525 | 14 | Clients |
| `dim_date.csv` | 1,827 | 12 | Calendar, 2020–2024 |
| `dim_security.csv` | 500 | 8 | Securities and ETFs |
| `dim_benchmark.csv` | 8 | 4 | Performance benchmarks |
| `fact_fees.csv` | 122,197 | 8 | Monthly fee charges |
| `fact_portfolio_snapshot.csv` | 129,547 | 13 | Monthly account snapshots |
| `fact_transactions.csv` | 298,772 | 9 | Trades, income, cash flows, fee debits |

Ignore any other file in that folder.

> **Rule for this assignment:** read every file as text (`dtype=str`, `keep_default_na=False`). Default `pd.read_csv` parsing can silently change a column: it drops leading zeros, turns `45` into `45.0`, turns blank cells and the word `None` into `NaN`, and hides `%` and `$` strings. Read as text first, then convert each column on purpose.

---

## Part A — Audit (15 points)
Write `scripts/01_profile.py`. It must work on **any** table (not hard-coded to one file) and report, at minimum, for every column: null/blank count, distinct count, dominant value *shapes*, share of values that fail to parse as the expected type, whitespace problems, mixed formats, and numeric min/max. Then add checks in four groups:

1. **Column level:** type, allowed values, ranges, key uniqueness
2. **Single-table rules:** duplicates, near-duplicates, values that contradict other columns of the same row
3. **Referential integrity:** every foreign key must point to an existing primary key
4. **Cross-table business rules:** facts that disagree with dimensions, or with each other

Tag each finding **ERROR** (wrong, or will break a join or calculation), **WARN** (probably wrong; investigate) or **INFO** (worth knowing). Save `reports/profile_raw.csv` and `reports/dq_summary_raw.csv`.

## Part B — Decision log (15 points)
Write `decision_log.md` **before** you generate cleaning code for an issue. It is your prompt to Claude Desktop, not a retrospective. One entry per issue:

| Field | What to write |
|---|---|
| **Table / column** | |
| **Evidence** | the number or example from your audit that shows the problem |
| **Dimension violated** | Validity, Completeness, Uniqueness, Consistency, Accuracy/Plausibility, or Referential Integrity (more than one is allowed) |
| **Decision** | convert / standardize / fill / flag / quarantine / **leave as is** |
| **Justification** | why this decision, in business terms |
| **Risk** | what goes wrong if you are wrong |

Two things graders look for: (1) whether you separated a **defect** from a **legitimate structure** (not every null needs filling, and not every odd-looking value is an error), and (2) whether you **verified** a fix against other columns or tables instead of assuming it. Issues you decide to leave alone belong in the log too.

## Part C — Cleaning program (30 points)
Write `scripts/02_clean.py`. It reads the eight raw files and writes a **new set of eight files**. The raw files are never modified.

- **Same file names, same columns.** You may *add* clearly named flag columns (0/1) where a value is suspicious but cannot be corrected without inventing data
- One transformation at a time. After **each**: print rows affected and a before/after check, and `assert` the after-state. The script must stop if a fix did not do what you claimed
- **Reconcile instead of guessing.** Where one column can be recomputed from others, or two tables describe the same fact, use that to confirm a repair
- **Nothing is deleted silently.** Rows you remove go to a quarantine file with enough columns to trace them. Prove `raw rows = clean rows + quarantined rows` for every table
- **Audit trail:** save `data/audit/cleaning_log.csv` (table, issue, action, rows affected, note), `data/audit/value_changes.csv` (table, key column, key, column, old value, new value) and one `data/audit/quarantine_*.csv` per quarantined set
- Save the clean tables in `data/clean/`
- Write `data/clean/README_clean.md`: relationships between tables, column-type settings a BI tool will need, the flag columns you added, and **known limitations** you chose not to fix, each with a reason

## Part D — Referential integrity and validation (25 points)
Write `scripts/03_validate.py` containing:

- **One** reusable function `check_referential_integrity(fact_df, fact_key, dim_df, dim_key)` that returns match rate, orphan rows, distinct orphan keys, and null-key rate. Apply it to **every** relationship between the eight tables (there are ten ID-based ones and three that join to the date table; find them). **Keep this function: you will reuse it in Assignment 5**
- Rule-based checks for every column with a natural business bound (valid ranges, allowed code lists, sign rules)
- At least two **cross-table reconciliations** (for example: a recomputed amount versus the stored amount)
- IQR outlier flags on at least two numeric columns with no natural bound, plus one sentence on whether "flagged" means "wrong"

Run everything on **both** raw and clean tables and save `reports/data_quality_scorecard.csv`: one row per table per stage (raw / clean) with % completeness, % key uniqueness, % type validity, % rule pass, % referential match.

## Part E — Business report (15 points)
Using Claude Desktop, write `reports/cleaning_report.md` (1–2 pages) for the Wildcat Capital portfolio committee. Build it from your **actual** decision log and scorecard: paste the numbers in; do not let Claude invent figures. Required: executive summary, cleaning summary table, at least three key judgment calls with justification and risk, a limitations section, and the footer

`AI-assisted report — reviewed for factual accuracy on [date] by [your name]`

Check every number against your own script output before submitting. **An unverified or fabricated number is a serious deduction, not a rounding error.**

---

## Process requirements

- **Claude Desktop** drafts every script; **you** run and debug it in VS Code; **Claude Code** reviews it before each commit. In `README.md`, list what Claude Code flagged and what you did about it
- Commit at least once per part with a message that says specifically what changed (e.g. *"HW4 Part C: clean fact_transactions — N rows quarantined, amounts reconciled to shares × price"*)
- No AI usage log is required

## Submission checklist

- [ ] `README.md` (structure, how to run, Claude Code findings)
- [ ] `decision_log.md`
- [ ] `scripts/01_profile.py` · `02_clean.py` · `03_validate.py`
- [ ] `data/clean/` (8 files + `README_clean.md`) · `data/audit/` (cleaning log, value changes, quarantine files)
- [ ] `reports/` — `profile_raw.csv`, `dq_summary_raw.csv`, `data_quality_scorecard.csv`, `cleaning_report.md`

## Grading rubric *(indicative — set final weights in Brightspace)*

| Component | Pts | Full credit |
|---|---:|---|
| A Audit | 15 | Generic (not per-table hard-coding); surfaces issues of every type and all four check groups |
| B Decision log | 15 | All real issues found; defects separated from legitimate structure; evidence cited |
| C Cleaning program | 30 | Incremental, asserted, order defended, repairs reconciled; quarantine and audit trail; raw = clean + quarantined |
| D RI + validation + scorecard | 25 | One reusable RI function; every relationship covered; before/after numbers |
| E Business report | 15 | Numbers match script output; judgment calls explained |
