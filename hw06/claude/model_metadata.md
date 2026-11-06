# Model metadata (exported from `hw06.pbix`)

I ran the three `INFO.VIEW` queries from guide §2 in DAX query view (they're saved in the file as **Query 3**), copied each result grid and pasted it below. I ran them after adding the `_Measures` table and marking `dim_date` as the date table, so they describe the final model.

**What I left out:** the hidden auto date/time tables Power BI makes by itself (`LocalDateTable_…` and `DateTableTemplate_…`, 14 columns). They aren't part of the star schema. I also shortened the relationship names, which are long auto-generated IDs.

**One quirk:** `INFO.VIEW.COLUMNS` shows a few date columns capitalized (`dim_date[Date]`, `[Year]`, `[Quarter]`, `[Month]` and `fact_portfolio_snapshot[Year]`, `[Month]`), but the Data pane and the CSVs use lower case. DAX doesn't care about case, so `dim_date[date]` and `dim_date[year]` work in every measure.

## 1. Columns

```DAX
EVALUATE
SELECTCOLUMNS (
    FILTER ( INFO.VIEW.COLUMNS (), [DataCategory] <> "RowNumber" ),
    [Table], "Column", [Name], [DataType], "DAX formula", [Expression], [IsHidden]
)
ORDER BY [Table]
```

| Table | Column | DataType | DAX formula | IsHidden |
|---|---|---|---|---|
| _Measures | Value | Integer |  | true |
| dim_advisor | advisor_id | Integer |  | false |
| dim_advisor | certifications | Text |  | false |
| dim_advisor | aum_target_mm | Integer |  | false |
| dim_advisor | years_experience | Integer |  | false |
| dim_advisor | region | Text |  | false |
| dim_advisor | last_name | Text |  | false |
| dim_advisor | first_name | Text |  | false |
| dim_benchmark | name | Text |  | false |
| dim_benchmark | benchmark_id | Integer |  | false |
| dim_benchmark | ticker_proxy | Text |  | false |
| dim_benchmark | asset_class | Text |  | false |
| dim_client | age | Integer |  | false |
| dim_client | last_name | Text |  | false |
| dim_client | first_name | Text |  | false |
| dim_client | client_id | Integer |  | false |
| dim_client | zip_code | Text |  | false |
| dim_client | risk_profile | Text |  | false |
| dim_client | client_tier | Text |  | false |
| dim_client | primary_account_type | Text |  | false |
| dim_client | initial_aum | Number |  | false |
| dim_client | client_since | Date |  | false |
| dim_client | advisor_id | Integer |  | false |
| dim_client | is_active | True/False |  | false |
| dim_client | state | Text |  | false |
| dim_client | city | Text |  | false |
| dim_date | is_quarter_end | Integer |  | false |
| dim_date | date_id | Integer |  | false |
| dim_date | Date | Date |  | false |
| dim_date | Year | Integer |  | false |
| dim_date | Quarter | Integer |  | false |
| dim_date | Month | Integer |  | false |
| dim_date | month_name | Text |  | false |
| dim_date | week_of_year | Integer |  | false |
| dim_date | day_of_week | Text |  | false |
| dim_date | is_month_end | Integer |  | false |
| dim_date | is_year_end | Integer |  | false |
| dim_date | is_trading_day | Integer |  | false |
| dim_security | ticker | Text |  | false |
| dim_security | security_id | Integer |  | false |
| dim_security | expense_ratio_bps | Integer |  | false |
| dim_security | is_etf | True/False |  | false |
| dim_security | benchmark_id | Integer |  | false |
| dim_security | sector | Text |  | false |
| dim_security | asset_class | Text |  | false |
| dim_security | name | Text |  | false |
| fact_fees | aum_basis | Number |  | false |
| fact_fees | fee_type | Text |  | false |
| fact_fees | fee_date | Date |  | false |
| fact_fees | fee_id | Integer |  | false |
| fact_fees | client_id | Integer |  | false |
| fact_fees | advisor_id | Integer |  | false |
| fact_fees | amount | Number |  | false |
| fact_fees | bps_charged | Number |  | false |
| fact_portfolio_snapshot | Year | Integer |  | false |
| fact_portfolio_snapshot | benchmark_return_ytd | Number |  | false |
| fact_portfolio_snapshot | return_ytd | Number |  | false |
| fact_portfolio_snapshot | aum | Number |  | false |
| fact_portfolio_snapshot | Month | Integer |  | false |
| fact_portfolio_snapshot | active_alpha_ytd | Number |  | false |
| fact_portfolio_snapshot | snapshot_date | Date |  | false |
| fact_portfolio_snapshot | benchmark_id | Integer |  | false |
| fact_portfolio_snapshot | advisor_id | Integer |  | false |
| fact_portfolio_snapshot | client_id | Integer |  | false |
| fact_portfolio_snapshot | snapshot_id | Integer |  | false |
| fact_portfolio_snapshot | is_return_suspect | Integer |  | false |
| fact_portfolio_snapshot | account_type | Text |  | false |
| fact_portfolio_snapshot | cash_pct | Number |  | false |
| fact_transactions | txn_id | Integer |  | false |
| fact_transactions | price | Number |  | false |
| fact_transactions | amount | Number |  | false |
| fact_transactions | is_post_departure_txn | Integer |  | false |
| fact_transactions | client_id | Integer |  | false |
| fact_transactions | shares | Number |  | false |
| fact_transactions | advisor_id | Integer |  | false |
| fact_transactions | security_id | Integer |  | false |
| fact_transactions | txn_date | Date |  | false |
| fact_transactions | txn_type | Text |  | false |

## 2. Relationships

```DAX
EVALUATE INFO.VIEW.RELATIONSHIPS ()
```

| Name | IsActive | CrossFilteringBehavior | FromTable | FromColumn | FromCardinality | ToTable | ToColumn | ToCardinality | State |
|---|---|---|---|---|---|---|---|---|---|
| AutoDetected | true | OneDirection | fact_transactions | advisor_id | Many | dim_advisor | advisor_id | One | Ready |
| AutoDetected | true | OneDirection | fact_transactions | client_id | Many | dim_client | client_id | One | Ready |
| AutoDetected | true | OneDirection | fact_transactions | security_id | Many | dim_security | security_id | One | Ready |
| (ID) | true | OneDirection | fact_transactions | txn_date | Many | dim_date | date | One | Ready |
| AutoDetected | true | OneDirection | fact_portfolio_snapshot | advisor_id | Many | dim_advisor | advisor_id | One | Ready |
| AutoDetected | true | OneDirection | fact_portfolio_snapshot | benchmark_id | Many | dim_benchmark | benchmark_id | One | Ready |
| AutoDetected | true | OneDirection | fact_portfolio_snapshot | client_id | Many | dim_client | client_id | One | Ready |
| (ID) | true | OneDirection | fact_portfolio_snapshot | snapshot_date | Many | dim_date | date | One | Ready |
| AutoDetected | true | OneDirection | fact_fees | advisor_id | Many | dim_advisor | advisor_id | One | Ready |
| AutoDetected | true | OneDirection | fact_fees | client_id | Many | dim_client | client_id | One | Ready |
| (ID) | true | OneDirection | fact_fees | fee_date | Many | dim_date | date | One | Ready |
| (ID) | true | OneDirection | dim_client | client_since | Many | LocalDateTable | date | One | Ready |
| (ID) | true | OneDirection | dim_security | benchmark_id | Many | dim_benchmark | benchmark_id | One | Ready |

The 11 fact-to-dimension relationships from Assignment 5 are all there (many-to-one, single direction). There are two extras. `dim_client[client_since] → LocalDateTable` is Power BI's hidden auto date table. `dim_security → dim_benchmark` is active in this starting file (in my HW5 design it was inactive). Neither one affects these measures: `fact_portfolio_snapshot` connects straight to `dim_benchmark`, and the extra link only filters from `dim_benchmark` toward `dim_security`.

## 3. Measures

```DAX
EVALUATE
SELECTCOLUMNS (
    INFO.VIEW.MEASURES (),
    [Table], "Measure", [Name], "DAX formula", [Expression], [FormatString], [State]
)
```

All 16 measures are in `_Measures` and every one has **State = Valid**. The full DAX for each is in `powerbi/measures.md`. The `[FormatString]` column came back blank for all of them, even though the formats are set (the TMDL view shows `formatString: \$#,0.00;(\$#,0.00);\$#,0.00` on `Total Fees`, for example). As far as I can tell, this column only fills in for dynamic format strings.

| Table | Measure | State |
|---|---|---|
| _Measures | Total Fees | Valid |
| _Measures | Net Flows | Valid |
| _Measures | AUM (naive SUM) | Valid |
| _Measures | Ending AUM | Valid |
| _Measures | Ending Clients | Valid |
| _Measures | Avg AUM per Client | Valid |
| _Measures | Ending AUM LY | Valid |
| _Measures | AUM YoY % | Valid |
| _Measures | Ending AUM PM | Valid |
| _Measures | AUM MoM % | Valid |
| _Measures | Avg Monthly AUM | Valid |
| _Measures | Fee Yield (bps) | Valid |
| _Measures | Organic Growth Rate | Valid |
| _Measures | AUM-Weighted Alpha | Valid |
| _Measures | Alpha Signal | Valid |
| _Measures | Top 10 Client Share | Valid |

## 4. What the metadata can't say (added to the prompt by hand)

- **Grain:** `fact_portfolio_snapshot` is one row per client per month, always dated the 1st (2020-01-01 to 2024-12-01). Clients come and go, so the client count per date changes (175 clients left before December 2024). `fact_fees` is also one row per client per month. `fact_transactions` is one row per transaction.
- **Additivity:** `aum` and `aum_basis` are balances (last balance only). `bps_charged`, `return_ytd`, `benchmark_return_ytd` and `active_alpha_ytd` are rates (recompute and weight, never sum). `active_alpha_ytd` is year-to-date. `fact_transactions[amount]` is always positive, so it only adds up within one `txn_type`.
