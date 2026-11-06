# Power BI DAX Guide — Measures, Metadata for Claude, and Reconciliation
### MIS3060 HW6 | Power BI Desktop on the Apporto virtual desktop

## 0. Start
Download `Wildcat_Star_Model.pbix` from Brightspace, open it, and **File → Save as** `hw06.pbix` in your `hw06/powerbi/` folder. Check the model before you start: Model view shows 11 relationships (many-to-one, single direction) and `dim_date` is marked as the date table. Create a `_Measures` table (**Home → Enter data**, name it `_Measures`, **Load**), then right-click it → **New measure** for every measure. Delete the empty `Column1` after your first measure.

## 1. Measure patterns: one per additivity class
**Additive** — safe to sum across any dimension:
```DAX
Total Fees = SUM ( fact_fees[amount] )
```

**Semi-additive** (balances) — summing across months is wrong. Take the balance at the last date that has data in the current filter. Snapshot dates fall on the **first** day of each month, so `LASTDATE`, `ENDOFMONTH` or `CLOSINGBALANCEMONTH` would return a date with no data; use `LASTNONBLANK`:
```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
Build `Ending AUM` first and check it against pandas for December 2024. Then build the time-shifted versions on top of it: `CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )` works because LASTNONBLANK runs inside the shifted dates.

**Non-additive** (rates, ratios, returns) — never sum or average them. Recompute from additive parts, with a weight:
```DAX
Effective Fee Rate (bps) =
DIVIDE ( SUM ( fact_fees[amount] ) * 12 * 10000, SUM ( fact_fees[aum_basis] ) )
```
For a row-by-row weight (e.g., `aum × alpha`), use an iterator: `SUMX ( table, a * b ) / SUM ( b )`.

## 2. Exporting model metadata for Claude
Claude cannot see your `.pbix`. Invented table or column names are the most common AI error. In **DAX query view**, run each query, copy the result grid, and paste it into your prompt (and into `claude/model_metadata.md`):
```DAX
EVALUATE
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.COLUMNS (), [DataCategory] <> "RowNumber" ),
    [Table], "Column", [Name], [DataType], "DAX formula", [Expression], [IsHidden]
)
ORDER BY [Table]

EVALUATE INFO.VIEW.RELATIONSHIPS ()

EVALUATE
SELECTCOLUMNS (
    INFO.VIEW.MEASURES (),
    [Table], "Measure", [Name], "DAX formula", [Expression], [FormatString], [State]
)
```
**What you get:** every column with its data type (calculated columns include their DAX formula; imported columns show a blank); every relationship (from/to columns, cardinality, cross-filter direction, active or inactive); every existing measure with its DAX, format string and State (valid or error), so Claude can reuse `[Total Fees]` instead of re-inventing it.

**What it does not include, so add it yourself:** the grain of each fact table, and the additivity of each column (`aum` is a balance; `bps_charged` and `active_alpha_ytd` are rates; snapshot and fee dates are the 1st of the month).

Formulas appear only if you can edit the model (your own `.pbix`: yes; a live connection to a published model: blank). Alternative: **File → Save as → Power BI Project (.pbip)** stores the model as readable TMDL text files.

## 3. Getting Power BI numbers out for reconciliation
1. In **DAX query view**, write a query, for example:
```DAX
EVALUATE
SUMMARIZECOLUMNS (
    dim_date[year],
    "Ending AUM", [Ending AUM],
    "AUM YoY %", [AUM YoY %],
    "Fee Yield (bps)", [Fee Yield (bps)]
)
```
2. Run it, copy the result grid, and paste it into `reports/powerbi_values.csv` (reshape to `measure, slice, value`).
3. For a filtered slice (e.g., tiers in 2024), wrap it: `CALCULATETABLE ( SUMMARIZECOLUMNS ( dim_client[client_tier], … ), dim_date[year] = 2024 )`.
4. No DAX query view on your Apporto version? Build a table visual with the same fields and use **… → Export data**.

> Copy the numbers unrounded. A value formatted as `$12.73B` cannot be reconciled to the cent.

## 4. Troubleshooting
| Symptom | Likely cause |
|---|---|
| `Ending AUM` is blank | `LASTDATE` / `ENDOFMONTH` used; snapshots are on the 1st of the month. Use `LASTNONBLANK` |
| AUM in the hundreds of billions | A plain SUM of `aum` across months |
| A measure shows the same value on every row | A `CALCULATE` filter, `ALL`, or `REMOVEFILTERS` removes the row's filter |
| Top 10 Client Share > 100% in a tier table | `TOPN` over `ALL ( dim_client )` instead of `VALUES ( dim_client[client_id] )` |
| 2020 growth shows 0% | `DIVIDE ( …, 0 )` hides a missing prior year; omit the 0 |
| Time intelligence blank or wrong | `dim_date` not marked, or a fact's own date/year column is on the visual |
| "A single value for column … cannot be determined" | A bare column inside a measure; aggregate it or use an iterator |
