# HW7: Where Did 2024 Growth Come From? A Two-Page Wildcat Dashboard

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

**Answer in one line:** AUM grew **$2.08B (+19.6%)** in 2024 to **$12.73B**, but **96%** of that was market change ($2.01B). Net new money was only **$77.5M (0.73% organic growth)**. UHNW and the Northeast drove most of the dollars, and Retail is the only tier where new money is about half of its growth.

## How I used AI

- **Claude (Claude app, connected to my computer and my Apporto session)** drafted both scripts, the DAX (measures, dynamic titles, alt text, color measures), the prototypes, the wireframes and the first drafts of the docs. It also built the two report pages in Power BI Desktop on Apporto.
- **Claude Code (VS Code)** reviews both scripts. Findings are below.
- I edit the design plan, critique decisions and executive summary in my own words.

## Folder structure

```
hw07/
├── README.md                     ← this file
├── design_plan.md                ← Part A (+ section 6: formatting measures)
├── executive_summary.md          ← Part F, with the audit table
├── design/
│   ├── wireframe_page1.png
│   ├── wireframe_page2.png
│   └── prototypes/               ← 4 Claude prototypes of the flows-vs-market split
├── scripts/
│   ├── 00_make_extract.py        ← builds data/growth_extract.csv (pandas, from the clean CSVs)
│   └── 01_reconcile_kpis.py      ← Part D: pandas vs Power BI + extract check
├── data/
│   ├── growth_extract.csv        ← 75 rows: year × tier × region
│   └── README.md                 ← balance vs flow for every column
├── dashboard/
│   ├── hw07.pbix
│   ├── page1.png                 ← Growth Drivers, year slicer = 2024, region = All
│   └── page2.png                 ← Segment Detail after drilling through on UHNW
├── reports/
│   ├── powerbi_values_query.dax  ← DAX query that exports the Power BI numbers
│   ├── powerbi_values.csv        ← its result (measure, slice, value), 43 rows
│   ├── kpi_reconciliation.csv    ← pandas vs Power BI, 43 of 43 match
│   └── extract_check.csv         ← extract summed to tier / region vs reconciliation, 32 of 32 match
└── claude/
    ├── design_critique.md        ← Part E log
    ├── before.png
    └── after.png
```

## How to run

```bash
python hw07/scripts/00_make_extract.py        # -> hw07/data/growth_extract.csv (75 rows)
python hw07/scripts/01_reconcile_kpis.py      # -> reports/kpi_reconciliation.csv + extract_check.csv
```

You need Python 3.9+ and pandas. Both scripts read the instructor's CSVs from `Data/Wildcat_Capital_Clean/` (not in GitHub, same as HW5/HW6); use `--data <folder>` to point somewhere else. `01_reconcile_kpis.py` computes every value in pandas **before** it opens `powerbi_values.csv`, and stops with an error if a row is missing or doesn't match.

**Getting the Power BI numbers:** run `reports/powerbi_values_query.dax` in DAX query view (saved in `hw07.pbix` as Query 7; Query 5 is the first version, with the same 43 rows), then **Copy → Entire table** and save it as `reports/powerbi_values.csv` with the header `measure,slice,value`. The query converts every number to text, so no format string can round it.

## Results

| Check | Result |
|---|---|
| Reconciliation (2024): Page 1 cards at firm level, the flows/market split for each of 3 tiers and 5 regions, Page 2 cards for **Retail** | **43 of 43 rows match** (same tolerances as HW6: $0.01, 0.0001, exact for counts and text) |
| Tier rows and region rows add up to the firm totals | Yes, for Ending AUM, Ending AUM LY, Net Flows and Market Change |
| **Extract check:** 2024 rows of `growth_extract.csv` summed to tier and to region vs. the tier/region rows of the reconciliation | **32 of 32 match** (4 measures × 8 members, `reports/extract_check.csv`; largest difference < $0.01) |

Key 2024 values: Ending AUM $12,729,572,078.86 · Ending AUM LY $10,644,971,737.00 · AUM YoY 19.58% · Net Flows $77,513,055.26 · Market Change $2,007,087,286.60 · Organic Growth 0.73% · Retail: 1,394 clients, $382,678 per client, 82.8 bps fee yield, +2.40% alpha (Outperforming).

## Script reviews

### Claude review in the Claude app (while writing them)

| # | Script | What came up | What was done |
|---|---|---|---|
| 1 | `00_make_extract.py` | An unmatched `client_id` or `advisor_id` would silently drop money from the extract | Added asserts that every fact row maps to a tier and a region |
| 2 | `00_make_extract.py` | A tier × region cell with no data would just disappear, giving fewer than 75 rows | Re-indexed to the full 5 × 3 × 5 grid; 2020 keeps its row with blank LY and Market Change |
| 3 | `00_make_extract.py` | Checked that the 15 rows for 2024 add back to the firm's Dec 2024 balance | Added an assert ($12,729,572,078.86) |
| 4 | `01_reconcile_kpis.py` | Region is reached through each fact's `advisor_id`, but only the snapshot and transaction facts are needed for the split | Region is mapped on those two facts; Fee Yield and Alpha are only computed for slices without a region (they're only shown by tier) |
| 5 | `01_reconcile_kpis.py` | `Market Change` must follow DAX blank rules (BLANK − x = −x) | Copied that rule; blank only when there's no LY balance at all |
| 6 | `01_reconcile_kpis.py` | Extra rows in `powerbi_values.csv` that aren't required would be ignored silently | The script now prints them as a note (none in the final file) |

### Claude Code review in VS Code

*(TO DO, Kaitlyn: open both scripts in VS Code, ask Claude Code to review them, then list what it flagged and what you changed here, the same way as in HW6.)*

| # | Script | What Claude Code flagged | What I changed |
|---|---|---|---|
| | | | |

## Filter audit (Part D.4)

| Page | Level | Filter / interaction | Changes a number silently? |
|---|---|---|---|
| Growth Drivers | Report | None | — |
| Growth Drivers | Page | None (the year and region come from **slicers**, which are visible on the page) | No |
| Growth Drivers | Slicer | `dim_date[year]` = **2024** (saved), single select | No, it's visible, and every title says "In 2024…" |
| Growth Drivers | Slicer | `dim_advisor[region]` = All | No, it's visible. Selecting a region filters every visual on the page **and** carries into Page 2 through Keep all filters; the Page 2 subtitle then adds "\| \<region\> region" |
| Growth Drivers | Visual | None on any visual (the waterfall uses the small `Growth Step` table, not a filter) | No |
| Growth Drivers | Interactions | **Not edited**; default cross-filtering. Clicking a tier bar highlights that tier in the region chart, and the cards and headline update to that tier. The clicked bar stays highlighted, so you can see it; clicking it again clears it | No, the highlight is visible |
| Segment Detail | Drill-through | `dim_client[client_tier]` (from the tier bar you right-click), **Keep all filters = On**, so the year (and region, if selected) carry over | No, the subtitle names the tier and year |
| Segment Detail | Page / visual | None. The top-10 table uses a `RANKX` **measure** (blank outside the top 10), not a Top N visual filter, and the total row is turned off so it can't show the whole tier's AUM under a "top 10" header | No |
| Segment Detail | Interactions | Not edited | No |

When you open Page 2 directly (without drilling through), it shows all tiers and all years ("Segment detail: all tiers clients, all years"). That's expected, and the subtitle says so.

## Power BI notes

- **Starting file.** `ICE12.pbix` showed "Unable to open document… authored with a newer version" on Apporto. My `hw06.pbix` (which already has every ICE12/HW6 measure: Ending AUM, Ending AUM LY, AUM YoY %, Ending Clients, Avg AUM per Client, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal, Top 10 Client Share, Total Fees, Net Flows) opened after the same warning, so I saved it as `hw07.pbix` and built on it. The old "Measures" page from HW6 is still in the file.
- **New measures** (all in `_Measures`): `Market Change`, `AUM Change`, `Growth Step Value`, the dynamic titles (`Page 1 Title`, `Waterfall Title`, `Tier Title`, `Region Title`, `Segment Subtitle`), the color measures (`Net Flows Color`, `Alpha Font Color`), the `Card …` display-text measures, the `Top 10 …` table measures and one `Alt …` measure per visual. Also a calculated column `dim_client[Client Name]` and a calculated table `Growth Step` (for the waterfall's two steps).
- **Cards are table visuals.** The Card and new Card visuals render as blank boxes in Power BI Desktop on Apporto (same problem as HW6), so every "card" is a one-row table showing a formatted text measure. Values are identical to the reconciled measures.
- **Alt text:** every visual's alt text is set with **fx → Field value** to an `Alt …` measure, so the numbers in the alt text change with the slicers. The two slicers and the Page 2 subtitle have static alt text. The caveat text box is read out as its own text, and the back button uses Power BI's default "Back" label.
- **Apporto session:** the Apporto session restarted once while building; everything had been saved and reopened fine.

## Commits

*(to fill in after pushing)*
