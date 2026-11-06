# HW6: DAX Measure Library (AUM & Performance)

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

This assignment builds 12 DAX measures on the Wildcat Capital portfolio snapshot (how much the firm manages, how it grows, what it earns and how clients do against their benchmarks). It then proves every number in pandas, answers four design questions, and tests one Claude-drafted measure.

## How I used AI

- **Drafting:** Claude (in the Claude app, linked to my computer and my Apporto session) drafted both scripts, the DAX, `measures.md`, the Part D files and this README.
- **Power BI:** Claude opened the starting model in Power BI on Apporto, saved it as `hw06.pbix`, added the `_Measures` table and all 16 measures (in one TMDL script), marked `dim_date` as the date table, built the **Measures** page, and ran the export, metadata and test queries in DAX query view.
- **Part D:** the Claude session for `Top 10 Client Share` was in the same Claude app chat, not a separate Claude Desktop window (see `claude/dax_session.md`).
- **Review:** the script review was also done by Claude in the app, like in HW5, not by the Claude Code extension in VS Code. The findings and fixes are below.

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

You need Python 3.9+ and pandas. Each one takes about 10 seconds. They read the instructor's CSVs from `Data/Wildcat_Capital_Clean/` (not in GitHub, same as HW5). Use `--data <folder>` to point somewhere else. `01_reconcile_measures.py` computes every measure in pandas **before** it opens `powerbi_values.csv`, and it stops with an error if any required row is missing or doesn't match.

**Getting the Power BI numbers:** open `reports/powerbi_values_query.dax` in DAX query view (it's also saved in `hw06.pbix` as **Query 2**), run it, then **Copy → Entire table** and save the result as `reports/powerbi_values.csv` with headers `measure,slice,value`. The query converts every number to text with `CONVERT ( …, STRING )`, so nothing gets rounded by a format string.

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

**None.** All 91 rows matched on the first run, and the biggest difference on a currency row is $0.0001 (from floating-point rounding). Two things helped. Both sides use the same "last snapshot date with data" rule. And the export converts to text before copying, so Power BI's formatting doesn't round anything.

## Power BI notes

- **Starting file.** The HW6 starter `.pbix` from Brightspace (22 MB) was too big to upload to Apporto from the Claude app, so I used my copy of `Wildcat_Star_Model.pbix` that was already in my Apporto Downloads (downloaded Oct 26, same size). In that copy `dim_date` was **not** marked as a date table yet, so I marked it on `dim_date[date]` to match the assignment ("validated successfully"). It also has `dim_security → dim_benchmark` active (see `claude/model_metadata.md`). That doesn't affect any of these measures. I re-ran the export after marking the date table and got exactly the same 91 values.
- **`_Measures` table.** Instead of **Enter data**, I created it as a small calculated table with one hidden column, using one TMDL script that defines all 16 measures and their formats. It works the same way: it only holds measures.
- **Measures page.** The two tables render with all values. In the Apporto session the four cards drew as blank boxes (that seems to be a display problem in the virtual desktop, since tables on the same page draw fine). The cards are set up with the right measures, and their values are the same as the grand-total rows in the reconciliation.
- **Saved DAX queries** in `hw06.pbix`: Query 1 = measure list, Query 2 = reconciliation export, Query 3 = the three `INFO.VIEW` metadata queries + the Part C(a) SUMX check, Query 4 = Part D test.

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

## Commits

1. `HW6 Parts A-D: 16 measures, Measures page, reconciliation 91/91 match, design answers, Claude-assisted Top 10 Client Share`
