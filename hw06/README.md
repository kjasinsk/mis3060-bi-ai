# HW6: DAX Measure Library (AUM & Performance)

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

For this assignment I built 12 DAX measures on the Wildcat Capital portfolio snapshot, covering how much the firm manages, how it grows, what it earns and how clients do against their benchmarks. Then I checked every number in pandas, answered the four design questions and tested one measure that Claude drafted.

## How I used AI

- **Drafting:** Claude (in the Claude app, connected to my computer and my Apporto session) drafted both scripts, the DAX, `measures.md`, the Part D files and this README. I rewrote the explanations in my own words.
- **Power BI:** Claude opened the starting model in Power BI on Apporto and saved it as `hw06.pbix`. Then it added the `_Measures` table and all 16 measures (with one TMDL script), marked `dim_date` as the date table, built the **Measures** page, and ran the export, metadata and test queries in DAX query view.
- **Part D:** I did the Claude session for `Top 10 Client Share` in the same Claude app chat, not in a separate Claude Desktop window (see `claude/dax_session.md`).
- **Review:** the scripts got reviewed twice. First Claude reviewed them in the app (like in HW5), and then I ran the Claude Code extension in VS Code, which is the review the assignment asks for. The findings and fixes from both are below.

## Folder structure

```
hw06/
├── README.md                         ← this file
├── HW06_DAX_Measure_Library.md       ← the assignment
├── powerbi_dax_guide.md              ← instructor's guide
├── powerbi/
│   ├── hw06.pbix                     ← model + _Measures table + "Measures" page
│   └── measures.md                   ← Part A documentation and Part C answers
├── scripts/
│   ├── 01_reconcile_measures.py      ← Part B: pandas vs Power BI
│   └── 02_design_questions.py        ← Part C: every number quoted in Part C
├── reports/
│   ├── powerbi_values_query.dax      ← the DAX query that exports every Power BI number
│   ├── powerbi_values.csv            ← its result (measure, slice, value)
│   ├── pandas_values.csv             ← the same 91 values computed in pandas
│   ├── measure_reconciliation.csv    ← side by side, 91 of 91 match
│   └── design_questions_output.txt   ← output of 02_design_questions.py
└── claude/
    ├── model_metadata.md             ← the three INFO.VIEW exports
    ├── dax_session.md                ← Part D prompt + Claude's full response
    └── verification.md               ← Part D verification
```

## How to run

```bash
python hw06/scripts/01_reconcile_measures.py
python hw06/scripts/02_design_questions.py
```

You need Python 3.9+ and pandas, and each script takes about 10 seconds. They read the instructor's CSVs from `Data/Wildcat_Capital_Clean/`, which aren't in GitHub (same as HW5). You can use `--data <folder>` to point them somewhere else. `01_reconcile_measures.py` works out every measure in pandas **before** it opens `powerbi_values.csv`, and it stops with an error if a required row is missing or doesn't match.

**Getting the Power BI numbers:** I opened `reports/powerbi_values_query.dax` in DAX query view (it's also saved in `hw06.pbix` as **Query 2**), ran it, used **Copy → Entire table**, and saved the result as `reports/powerbi_values.csv` with the headers `measure,slice,value`. The query turns every number into text with `CONVERT ( …, STRING )`, so a format string can't round anything.

## Results at a glance

| | |
|---|---|
| Reconciliation | **91 of 91 rows match** (every measure at the grand total; measures 1, 4, 6–10 by year; measures 1, 3, 4, 7–11 by tier for 2024; measure 5 for December 2024; plus the two base measures) |
| Ending AUM (Dec 2024) | $12,729,572,078.86 across 2,325 clients |
| AUM (naive SUM) | $566,681,084,542.48, **44.5× too big**, and wrong by the same amount in both Power BI and pandas |
| AUM YoY % 2024 | 19.58%, but Organic Growth Rate is only 0.73% |
| Fee Yield 2024 | 43.15 bps (vs 45.53 bps Effective Fee Rate, because 6% of client-months have no fee row) |
| AUM-Weighted Alpha 2024 | 1.45% → "In line" |
| Top 10 Client Share | 6.16% firm-wide · 1.83% Retail · 3.14% HNW · 8.13% UHNW |

## Mismatches

**None.** All 91 rows matched the first time I ran it, and the biggest difference on a currency row is $0.0001, which is just rounding. I think two things helped. Both sides use the same "last snapshot date with data" rule, and the export turns numbers into text before copying them, so Power BI's formatting doesn't round anything.

## Power BI notes

- **Starting file.** The HW6 starter `.pbix` from Brightspace (22 MB) was too big to upload to Apporto from the Claude app, so I used my copy of `Wildcat_Star_Model.pbix` that was already in my Apporto Downloads (downloaded Oct 26, same size). In that copy, `dim_date` **wasn't** marked as a date table yet, so I marked it on `dim_date[date]` to match the assignment, and it said "validated successfully." That copy also has `dim_security → dim_benchmark` active (see `claude/model_metadata.md`), but that doesn't affect any of these measures. I re-ran the export after marking the date table and got the exact same 91 values. Later I compared my copy with the posted `Wildcat_Star_Model.pbix` from Brightspace: both have the same 8 tables with the same row counts, the same 12 relationships (including `dim_security → dim_benchmark`), and the same total `aum` ($566,681,084,542.48), so my starting model is identical to the posted one.
- **`_Measures` table.** Instead of using **Enter data**, I made it a small calculated table with one hidden column, using one TMDL script that creates all 16 measures and their formats. It works the same way, since it only holds measures.
- **Measures page.** The two tables show all their values. In Apporto, the four cards showed up as blank boxes, but I think that's a display problem in the virtual desktop, since the tables on the same page show up fine. The cards have the right measures, and their values are the same as the grand-total rows in the reconciliation.
- **Saved DAX queries** in `hw06.pbix`: Query 1 is the measure list, Query 2 is the reconciliation export, Query 3 has the three `INFO.VIEW` metadata queries plus the Part C(a) SUMX check, and Query 4 is the Part D test.

## Review findings and fixes

### Caught by Claude while building

| # | What came up | What was done |
|---|---|---|
| 1 | `dim_date` wasn't marked as a date table in the starting file, even though the assignment says it should be | Marked it on `date`. All 91 values were the same before and after |
| 2 | A paste landed in the wrong DAX query tab and broke the saved export query (Query 2) | Deleted that tab and re-created Query 2 from `powerbi_values_query.dax`. It re-ran with all 91 rows |
| 3 | `INFO.VIEW.MEASURES` shows a blank `FormatString` even though every measure has a format | Checked in TMDL view that the formats are set, and noted it in `model_metadata.md` |

### Claude review of the scripts (before committing)

| # | What the review found | What was done |
|---|---|---|
| 1 | `Net Flows` in pandas returned **0** for a slice with no deposits or withdrawals, but DAX returns **blank** (BLANK − BLANK = BLANK). That would make Organic Growth 0% in pandas and blank in Power BI | **Fixed.** Pandas now returns blank in that case. No required slice was affected |
| 2 | Pandas `nlargest(10)` keeps exactly 10 rows, but DAX `TOPN` keeps every client tied at 10th place | **Fixed:** uses `keep="all"`. No tie exists in this data (#10 is $74.4M, #9 is $77.2M), so nothing changed |
| 3 | For the text measure (Alpha Signal), `abs_diff` was written as an empty string, so the column mixed text and numbers | **Fixed:** 0 when the text matches, blank when it doesn't |
| 4 | Checked that the pandas side never reads anything from Power BI | **OK.** All 91 pandas values are computed and saved to `pandas_values.csv` before `powerbi_values.csv` is opened |
| 5 | Checked that every number quoted in `measures.md` Part C comes from a script | **OK.** All of them are printed by `02_design_questions.py`, and (a) was also run in Power BI (Query 3) |

### Claude Code review in VS Code

Claude Code re-ran both scripts (still 91 of 91 match, and the Part C output was the same) and checked the data assumptions they depend on. It didn't find any bug that changes a number, but it flagged four smaller things:

| # | What Claude Code flagged | What was done |
|---|---|---|
| 1 | `AUM YoY %` and `AUM MoM %`: when `Ending AUM` is blank but last year's isn't, DAX gives −100% (BLANK − x = −x), but pandas gave blank | **Fixed.** Added a `growth()` helper in `01_reconcile_measures.py` that copies the DAX rule. No required slice has this case, so all 91 rows are the same |
| 2 | Part C(d) in `02_design_questions.py` used one "last 2023 date" for all tiers instead of the last date **for each tier**, which is what `LASTNONBLANK` does | **Fixed.** It now finds the last date per tier. Every tier's last date is 2023-12-01 in this data, so the (d) numbers didn't change |
| 3 | Part C(b) merges snapshots and fees on client + month, which double-counts if a client ever has two rows in a month | **Fixed.** Added an `assert` that both tables have one row per client-month (they do: 0 duplicates) |
| 4 | The monthly alpha line printed `np.float64(-0.0001)` instead of `-0.0001` | **Fixed.** Re-ran and saved `design_questions_output.txt`. Only that line changed |

## Commits

1. `HW6 Parts A-D: 16 measures, Measures page, reconciliation 91/91 match, design answers, Claude-assisted Top 10 Client Share`
2. `HW6 Part B: re-ran reconciliation in VS Code - 91/91 match (Windows line endings)`
3. `HW6: Claude Code review — 4 small fixes, still 91/91 match, README updated`
4. `HW6: README - list all commits`
5. `HW6: rewrite measures.md, verification and README notes in my own writing style`
