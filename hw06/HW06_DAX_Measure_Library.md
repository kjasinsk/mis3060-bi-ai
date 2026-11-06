# HW6: DAX Measure Library — AUM & Performance
## MIS3060 Business Intelligence with AI | Villanova University
### Covers Weeks 9–10: DAX measures, and Claude as a DAX assistant

> **Due:** *(instructor: set date)* | **Weight:** *(set in Brightspace)* | **Individual** 
> **Submission:** push to your `mis3060-bi-ai` repo, folder `hw06/`, and paste the folder URL into Brightspace
> **Tools:** Claude Desktop drafts DAX and scripts · VS Code runs scripts · Claude Code reviews scripts before you commit · Power BI Desktop (Apporto virtual desktop)

---

## Overview

In ICE 9 and ICE 10 you measured Wildcat Capital's **fees and cash flows**. Here you measure the **portfolio snapshot**: how much the firm manages, how it grows, what it earns on it, and how clients perform against their benchmarks. Each measure must use the DAX pattern that matches the additivity class you assigned in Assignment 5 Part C, and every number must be proven in pandas.

You will:
1. Build a library of 12 DAX measures and one report page (Part A)
2. Reconcile every measure to an independent pandas calculation (Part B)
3. Answer four design questions that only make sense if you understand the filter context (Part C)
4. Use Claude to draft one measure from your exported model metadata, and document how you verified it (Part D)

## Data and starting point
- **`Wildcat_Star_Model.pbix`** (posted on Brightspace with this assignment): the Assignment 5 model with the eight `Wildcat Capital Clean` tables, the 11 relationships, and `dim_date` marked as the date table. **Everyone starts from this file**, so all reconciliations use the same model. Save a copy as `powerbi/hw06.pbix` and add your measures there
- The `Wildcat Capital Clean` CSVs, for the pandas side
- `powerbi_dax_guide.md` in this folder: measure patterns, metadata export, and how to get numbers out of Power BI

**Setup.** Keep every measure in a `_Measures` table. You need two base measures from the ICEs; if you do not have them, create them now:
```DAX
Total Fees = SUM ( fact_fees[amount] )
Net Flows  = CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )
           - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )
```

---

## Part A — Measure library (40 points)
| # | Measure | Business meaning | Hint |
|---|---|---|---|
| 0 | `AUM (naive SUM)` | The trap: a plain SUM of `aum` | Keep it only to show what goes wrong; never put it on a report |
| 1 | `Ending AUM` | Balance at the last snapshot in the current filter | Guide §1 (LASTNONBLANK) |
| 2 | `Ending Clients` | Clients in that last snapshot | Same date logic, DISTINCTCOUNT |
| 3 | `Avg AUM per Client` | Ending AUM ÷ Ending Clients | DIVIDE |
| 4 | `Ending AUM LY`, `AUM YoY %` | Balance one year earlier, and growth | SAMEPERIODLASTYEAR around `[Ending AUM]` |
| 5 | `Ending AUM PM`, `AUM MoM %` | Balance one month earlier, and growth | DATEADD |
| 6 | `Avg Monthly AUM` | Average balance over the months in the filter | Σ aum ÷ number of distinct snapshot dates |
| 7 | `Fee Yield (bps)` | Annualized fees per dollar of AUM, from **two fact tables** | `[Total Fees]` × 12 × 10,000 ÷ Σ aum |
| 8 | `Organic Growth Rate` | Net new money as a share of last year's ending balance | `[Net Flows]` ÷ `[Ending AUM LY]` |
| 9 | `AUM-Weighted Alpha` | `active_alpha_ytd` weighted by `aum`, at the last snapshot, excluding `is_return_suspect = 1` | SUMX, plus the last-date filter |
| 10 | `Alpha Signal` | Text: "Outperforming" (≥ +2%), "Lagging" (≤ −2%), otherwise "In line"; blank when alpha is blank | VAR + SWITCH ( TRUE (), … ) |
| 11 | `Top 10 Client Share` | Share of Ending AUM held by the 10 largest clients **within the current filter** | TOPN over `VALUES ( dim_client[client_id] )` |

Format every measure (currency, %, or bps with 1–2 decimals). In `powerbi/measures.md`, give for each: the DAX, the additivity pattern it implements (SUM, last balance, or recompute-and-weight), and one sentence on what it means for a Wildcat manager.

In `powerbi/hw06.pbix`, build one report page named **Measures** (save the file with this page open):
- **Cards:** Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share
- **Table by `dim_date[year]`:** Ending AUM, AUM YoY %, Avg Monthly AUM, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal
- **Table by `dim_client[client_tier]`**, filtered to 2024 with a **visual-level filter** (select the table → **Filters** pane → *Filters on this visual* → drag `dim_date[year]` in and tick 2024): Ending AUM, Avg AUM per Client, AUM YoY %, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal, Top 10 Client Share

## Part B — Reconciliation (25 points)
Write `scripts/01_reconcile_measures.py` (Claude Desktop drafts, you run it, Claude Code reviews it). It must:
1. Recompute each measure **independently** in pandas from the CSVs, without reading anything from Power BI
2. Read your Power BI numbers from `reports/powerbi_values.csv` (columns `measure, slice, value`), exported from **DAX query view** or a table visual (guide §3)
3. Write `reports/measure_reconciliation.csv` with columns `measure, slice, powerbi_value, pandas_value, abs_diff, match`. Tolerance: 0.01 for currency, 0.0001 for ratios

Cover at least: every measure at the **grand total**; measures 1, 4, 6–10 **by year**; measures 1, 3, 4, 7–11 **by client tier for 2024**; and measure 5 for **December 2024**. Include `AUM (naive SUM)` and its pandas twin to show both tools make the same mistake. Every row must match. If one did not at first, explain in `README.md` which side was wrong and what you fixed.

## Part C — Design questions (20 points; answer in `powerbi/measures.md`)
- **(a)** With no filters, `Ending AUM` shows one total. `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` shows a larger one. Compute both, explain the difference in dollars, and say which answers "How much do we manage today?"
- **(b)** For 2024, `Fee Yield (bps)` is lower than the ICE 9 `Effective Fee Rate (bps)`. Both are fees per dollar. Use pandas to find the cause, and say which data limitation it reveals
- **(c)** Why must `AUM-Weighted Alpha` be read at the last snapshot only, and why exclude `is_return_suspect = 1`? Report the simple mean of `active_alpha_ytd` for the same rows, and the weighted value with suspects included
- **(d)** Compare Organic Growth Rate by client tier in 2024. What does it say about where Wildcat's growth comes from, and what does it **not** tell you? (Hint: compare it with AUM YoY %)

## Part D — A Claude-assisted measure (15 points)
Use the **Draft → Test → Debug → Review** workflow from Week 10 for **one** of: measure 9 (`AUM-Weighted Alpha`) or measure 11 (`Top 10 Client Share`).
1. **Export your metadata** with the three INFO.VIEW queries (guide §2) and paste the results into `claude/model_metadata.md`
2. **Prompt Claude Desktop** with the metadata **plus** what the metadata cannot say: the grain of `fact_portfolio_snapshot`, that `aum` is a balance and `active_alpha_ytd` is year-to-date, and the exact business definition from the table above. Ask for the measure, an explanation of its filter context, and a DAX test query. Save your prompt(s) and Claude's full response(s) in `claude/dax_session.md`
3. **Verify** and write `claude/verification.md` (about one page):
   - Did Claude's measure run as written? What did its test query return?
   - Which row(s) of `measure_reconciliation.csv` prove it?
   - At least **two edge cases** you checked (for example: the grand total, `dim_date[year]` = 2022, the 2024 tier table)
   - What you changed and why (or why nothing needed changing)
   - One claim Claude made that you **confirmed or refuted** in Power BI or pandas

You may use Claude for other measures too. You must be able to explain the filter context of every measure you submit.

---

## Process requirements
- **Claude Desktop** drafts the script; **you** run it in VS Code; **Claude Code** reviews it before you commit. In `README.md`, list what Claude Code flagged and what you did about it
- Commit at least once with a message that says what changed (e.g. *"HW6 Part B: reconciliation — 61 rows, all match"*)
- Power BI on Apporto: save to the persistent drive and keep a local copy. DAX query view needs a 2024 or later Power BI Desktop; if yours lacks it, use table visuals and **Export data**

## Submission checklist
- [ ] `README.md` (structure, how to run, Claude Code findings, any mismatches and fixes)
- [ ] `powerbi/hw06.pbix`: the posted model with your `_Measures` table and the **Measures** report page (if it exceeds GitHub's 100 MB limit, upload it to Brightspace and say so in `README.md`)
- [ ] `powerbi/measures.md` (Part A documentation and Part C answers)
- [ ] `scripts/01_reconcile_measures.py` · `reports/powerbi_values.csv` · `reports/measure_reconciliation.csv`
- [ ] `claude/model_metadata.md` · `claude/dax_session.md` · `claude/verification.md`

## Grading rubric *(indicative — set final weights in Brightspace)*
| Component | Pts | Full credit |
|---|---:|---|
| A Measure library | 40 | Measures 1–11 correct, formatted and documented (3 each = 33); **Measures** page in the `.pbix` complete (4); naive SUM present and labeled as wrong (3) |
| B Reconciliation | 25 | pandas computed independently (10); all required slices (8); CSV structure and tolerance (4); mismatches explained (3) |
| C Design questions | 20 | (a)–(d), 5 each; (b) requires pandas evidence, not a guess |
| D Claude-assisted measure | 15 | Metadata exported (3); prompt supplies grain, additivity and definition (4); verification is specific, tests edge cases and judges Claude's output (8) |
| **Total** | **100** | |
