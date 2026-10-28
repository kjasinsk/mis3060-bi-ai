# HW5 — Wildcat Capital as a Star Schema in Power BI

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

This assignment looks at how the eight clean Wildcat Capital tables fit together (keys, grain and how each number can be added up), checks it with a Python script, and builds the star schema in Power BI so it's ready for Assignment 6.

## How I used AI

- **Drafting:** Claude (in the Claude app, linked to my computer and my Apporto session) drafted `scripts/hw05_checks.py`, `star_design.md`, this README and `powerbi/BUILD_STEPS.md`. It worked from the assignment, the instructor's `powerbi_guide.md` and my HW4 code.
- **Power BI:** I loaded the eight tables and created the fact-to-dimension relationships. Then I had Claude check the column types and relationships, set the two dimension-to-dimension links to inactive, mark the date table, remove an extra column and table I had added earlier, run the row-count query, arrange the Model view, and save the screenshots and the .pbix into this repo.
- **Review:** I ran the Claude Code review in VS Code (findings below) and asked Claude to apply the fixes. My commits are marked as co-authored with Claude.

## Folder structure

```
hw05/
├── README.md               ← this file
├── star_design.md          ← Parts A, B, C, E and F
├── scripts/
│   └── hw05_checks.py      ← checks Parts A–C (keys, integrity, grain, measures)
├── reports/
│   ├── keys_check.csv      ← every primary and foreign key check, pass/fail
│   ├── grain_check.csv     ← uniqueness at each fact table's grain
│   └── measures.csv        ← every numeric fact column and its class
└── powerbi/
    ├── BUILD_STEPS.md      ← the Power BI settings I used (follows powerbi_guide.md)
    ├── hw05.pbix           ← Part D model (also has the row-count DAX query)
    ├── model_view.png      ← Part D screenshot: 8 tables, 13 relationships
    └── row_counts.png      ← row counts for all 8 tables in Power BI
```

## How to run

```bash
python hw05/scripts/hw05_checks.py
# or, to run it on my own HW4 output:
python hw05/scripts/hw05_checks.py --data hw04/data/clean
```

You need Python 3.9+ and pandas. It takes about 15 seconds to a minute, depending on the computer. By default it reads the instructor's data from `Data/Wildcat_Capital_Clean/`. Those CSVs aren't in GitHub (the repo's `.gitignore` leaves out CSVs), so to rerun it, copy them from the instructor's `Wildcat_Clean` folder on the Apporto desktop. The script reuses `check_referential_integrity()` and `load_tables()` from my HW4 `03_validate.py`, so HW4 and HW5 check the data the same way. If any check fails, it stops with an `AssertionError`.

**Data note:** I used the instructor's `Wildcat Capital Clean` data for both the script and Power BI, like the assignment says. My own HW4 output has the same row counts and passes every check too. The only difference is the names of the flag columns.

## Results at a glance

| Check | Result |
|---|---|
| Primary keys unique and never blank | 8 of 8 (plus `dim_date[date]`) |
| Foreign keys matching their parent | 13 of 13 at 100%, no orphans |
| Fact dates matching `dim_date[date]` / `dim_date[date_id]` | 100% / 0% |
| Blank `security_id` | 101,528 rows, all Deposit, Withdrawal and Advisory Fee rows |
| Fact `advisor_id` matches `dim_client.advisor_id` | 100% on all three fact tables |
| Grain is unique | fees: client + month · snapshot: client + month · transactions: txn_id |
| Power BI relationships | 11 active (fact → dimension, \*:1, single) + 2 inactive dimension-to-dimension links |
| Power BI row counts | All 8 tables match the assignment (`row_counts.png`) |
| Date table | `dim_date` marked as the date table on `date` |

## Power BI notes

- I loaded the instructor's `Wildcat Capital Clean` files and followed `powerbi_guide.md`. All 77 columns were checked with `INFO.VIEW.COLUMNS()`. It showed 78 at the time because of a `dim_advisor[Advisor]` calculated column that was later deleted. Power BI had already picked the right types (whole numbers for IDs, Date for the five date columns, and Text for ZIP and account types).
- There are no new tables or columns, like the assignment says. The model has one measure, `Total Fees = SUM(fact_fees[amount])`, which is the optional example from the guide.
- The row counts were checked in Power BI with a DAX query that lists each table's count next to the number in the assignment. All 8 match, and the query is saved in the DAX query view of `hw05.pbix`.

## Review findings and fixes

### Caught by Claude while drafting and testing

| # | What came up | What was done |
|---|---|---|
| 1 | The script tested if client + security + date + type could be the transaction grain, but 1,238 rows share that combination with another row (622 extra copies), so it can't | The grain is one row per transaction (`txn_id`), and the script prints both counts |
| 2 | The easy way to get quarterly AUM would be to filter on `dim_date[is_quarter_end]`, but snapshots are dated the 1st and the flag is on the last day, so 0 of 129,547 snapshots match | Used as the Part F example of a question that needs DAX, with a schema fix |
| 3 | `fact_transactions.amount` is never negative, so a SUM adds withdrawals to deposits | Classified as additive only within one `txn_type`, and used in Part F |
| 4 | The script could skip a numeric column that hadn't been classified | The script now checks that every numeric fact column is in the Part C list |

### Claude review before committing

Claude reviewed `scripts/hw05_checks.py`, `star_design.md`, this README and the Power BI model, and checked each claim against the script output or the model. (This was done from the Claude app with access to my repo and Apporto, not from the VS Code extension.)

| # | What the review found | What was done |
|---|---|---|
| 1 | The README said the script also works on my HW4 data, but it crashed (`KeyError: 'is_return_suspect'`) because the two versions name their flag columns differently | **Fixed.** The script now handles both sets of flag names, and both `--data` options pass. |
| 2 | The model had a calculated column (`dim_advisor[Advisor]`) and an extra `_Measure` table, but the assignment says no new columns or tables | **Fixed.** Deleted the column, moved the measure onto `fact_fees`, deleted `_Measure`, and retook `model_view.png`. |
| 3 | The measure was spelled `Total Feees` | **Fixed:** renamed to `Total Fees`. |
| 4 | Rubric D asks for row counts that match, but they were only checked in Python | **Fixed.** Added a row-count query in Power BI (`row_counts.png`), and all 8 tables match. |
| 5 | `dim_security → dim_benchmark` was active in Power BI, but `star_design.md` says both dimension-to-dimension links are inactive, and `dim_client → dim_advisor` was missing | **Fixed** in Power BI so it matches the design (both inactive). |
| 6 | `dim_date` wasn't marked as a date table | **Fixed:** marked on `date`. |

### Claude Code review (VS Code)

| # | What Claude Code found | What was done |
|---|---|---|
| 1 | The advisor check and the one-benchmark-per-client check printed results but never stopped the script if they failed, even though Part E(b) depends on them | **Fixed.** Both now stop the script if they fail. It still passes (100% agreement, 1 benchmark per client). |
| 2 | "622 rows share client + security + date + type" was wrong, because `duplicated()` only counts the extra copies. 1,238 rows actually share a combination, and 1,050 of them are cash flows | **Fixed.** The script prints both counts, and `star_design.md` now says 1,238 (622 extra copies). |
| 3 | "Every claim below is checked in the script" wasn't fully true, because some numbers (dividends, flag counts, month-end, bps and price) were checked separately | **Fixed.** Added a section to the script that calculates each of these: 53,826 of 53,826 dividends = shares × price, 3,875 suspect returns, 2,410 post-departure transactions, 0 snapshots on month-end or quarter-end days, bps within 0.60, Buy/Sell amount = shares × price on 100% of rows, and the expense ratio blank on 281 of 281 non-ETFs. |
| 4 | The blank `security_id` check was saved as "passed" without actually being calculated | **Fixed.** It's now calculated and checked. |
| 5 | The "every column is classified" check could miss a numeric column with one bad text value, or count an all-blank column as numeric | **Fixed.** A column now counts as numeric when most of its values are numbers, and blank columns are skipped. |
| 6 | The grain check didn't remove extra spaces like the primary key check does | **Fixed.** Spaces are removed first (no numbers changed). |
| 7 | The AUM and cash examples used fixed dates, so on other data they would quietly print $0 | **Fixed.** The script now stops if those dates are missing. |
| 8 | The date-join check didn't say which table failed | **Fixed.** It now names the table and column. |
| 9 | The README said "about 20 seconds" (it took 63 seconds on my laptop), "78 columns" (the files have 77), and the commit plan didn't match the real commits | **Fixed** all three. |

Claude Code couldn't open the .pbix, so the Power BI parts (relationships, date table, measure and row counts) are backed up by the Power BI checks above and `row_counts.png`.

## Commits

1. `HW5 Parts A-C: key, integrity and grain checks - 13/13 FKs 100%, fact dates join on dim_date[date]`
2. `HW5 Parts A-C, E, F: star_design.md and README with review findings`
3. `HW5 Part D: Power BI model - 11 active + 2 inactive relationships, dim_date marked, row counts reconcile`
4. `HW5: Claude Code review - enforce advisor_id agreement check with an assert`
5. `HW5: Claude Code review fixes - assert every check, compute every quoted figure`
6. `HW5 Part D: model_view.png rearranged as a star (facts center, dimensions around)`
7. `HW5: README wording - say who did what, add How I used AI`
8. `HW5: rewrite star_design.md and README in my own writing style`
