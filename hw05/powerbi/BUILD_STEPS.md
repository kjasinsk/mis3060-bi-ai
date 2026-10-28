# Part D — Building the model in Power BI Desktop (Apporto)

About 20 minutes. Use the eight CSVs in the instructor's `Wildcat Capital Clean/` folder (copy in `Data/Wildcat_Capital_Clean/`). Follows the instructor's `powerbi_guide.md`.

## 1. Load the tables
**Home → Get data → Text/CSV**, one file at a time. On each preview, click **Transform Data** (not Load) so you can set types first.

## 2. Set column types (Power Query: right-click column header → Change Type)
If Power Query added a "Changed Type" step by itself, check it against this list.

| Set as | Columns |
|---|---|
| **Text** | `dim_client[zip_code]`, `dim_advisor[certifications]`, `fact_portfolio_snapshot[account_type]`, `dim_client[primary_account_type]` |
| **Whole number** | every `*_id`, `year`, `month`, `quarter`, `week_of_year`, `age`, `years_experience`, `aum_target_mm`, `is_return_suspect`, `is_post_departure_txn`, `is_month_end` / `is_quarter_end` / `is_year_end` / `is_trading_day` |
| **Date** | `dim_date[date]`, `dim_client[client_since]`, `fee_date`, `snapshot_date`, `txn_date` |
| **Fixed decimal (currency)** | `initial_aum`, `aum`, `aum_basis`, both `amount` columns, `price` |
| **Decimal** | `shares`, `bps_charged`, `expense_ratio_bps`, `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct` |
| **True/False** | `dim_client[is_active]`, `dim_security[is_etf]` |

Check: `fact_transactions[security_id]` must show **null** (not 0, not Error) on deposits. Then **Close & Apply**.

## 3. Check row counts (Table view, bottom-left shows rows)
dim_advisor 25 · dim_benchmark 8 · dim_client 2,500 · dim_date 1,827 · dim_security 500 · fact_fees 122,197 · fact_portfolio_snapshot 129,547 · fact_transactions 298,572

## 4. Relationships (Model view)
First **Modeling → Manage relationships** and **delete anything Power BI auto-detected**. Then **New** for each row. All are **Many to one (\*:1)**, **Single** cross-filter direction.

| From (many) | To (one) | Active? |
|---|---|---|
| fact_fees[client_id] | dim_client[client_id] | ✔ |
| fact_fees[advisor_id] | dim_advisor[advisor_id] | ✔ |
| fact_fees[fee_date] | dim_date[date] | ✔ |
| fact_portfolio_snapshot[client_id] | dim_client[client_id] | ✔ |
| fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | ✔ |
| fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | ✔ |
| fact_portfolio_snapshot[snapshot_date] | dim_date[date] | ✔ |
| fact_transactions[client_id] | dim_client[client_id] | ✔ |
| fact_transactions[advisor_id] | dim_advisor[advisor_id] | ✔ |
| fact_transactions[security_id] | dim_security[security_id] | ✔ |
| fact_transactions[txn_date] | dim_date[date] | ✔ |
| dim_client[advisor_id] | dim_advisor[advisor_id] | **untick "Make this relationship active"** |
| dim_security[benchmark_id] | dim_benchmark[benchmark_id] | **untick "Make this relationship active"** |

Inactive relationships show as a dashed line.

## 5. Mark the date table
Select `dim_date` → **Table tools → Mark as date table** → date column **`date`**. It should validate with no errors (dates are unique and continuous, 2020-01-01 to 2024-12-31).

## 6. Hide keys and non-measures (optional, tidier)
Right-click → **Hide in report view** for the `*_id` columns on the fact tables and `fact_portfolio_snapshot[year]`, `[month]`. In the Properties pane set **Summarize by: None** on the dimension numbers from Part C (age, years_experience, aum_target_mm, initial_aum, expense_ratio_bps, year, month, etc.).

## 7. Quick sanity check (then delete the visual)
A card with SUM of `fact_fees[amount]` should show about **$204.7M**.

## 8. Save and screenshot
- **File → Save as** `hw05/powerbi/hw05.pbix`
- Model view → arrange the three facts in the middle with dimensions around them → **Fit to page**, make sure all 8 tables and 13 lines are visible → screenshot (Win+Shift+S) → save as `hw05/powerbi/model_view.png`
