# Wildcat Capital — clean data (HW4)

Produced by `scripts/02_clean.py` from `data/raw/`. Raw files are never modified. Every change is listed in `data/audit/cleaning_log.csv` (one row per step) and `data/audit/value_changes.csv` (one row per changed cell).

## Row counts

| Table | Raw rows | Clean rows | Quarantined | Check |
|---|---:|---:|---:|---|
| dim_advisor | 25 | 25 | 0 | raw = clean + quarantined ✔ |
| dim_benchmark | 8 | 8 | 0 | raw = clean + quarantined ✔ |
| dim_client | 2,525 | 2,500 | 25 | raw = clean + quarantined ✔ |
| dim_date | 1,827 | 1,827 | 0 | raw = clean + quarantined ✔ |
| dim_security | 500 | 500 | 0 | raw = clean + quarantined ✔ |
| fact_fees | 122,197 | 122,197 | 0 | raw = clean + quarantined ✔ |
| fact_portfolio_snapshot | 129,547 | 129,547 | 0 | raw = clean + quarantined ✔ |
| fact_transactions | 298,772 | 298,572 | 200 | raw = clean + quarantined ✔ |

## Relationships (star schema for Power BI)

All are many-to-one, from the fact (or child) to the dimension, single direction.

| From (many) | To (one) | Notes |
|---|---|---|
| fact_transactions.client_id | dim_client.client_id | |
| fact_transactions.advisor_id | dim_advisor.advisor_id | |
| fact_transactions.security_id | dim_security.security_id | blank for Deposit/Withdrawal/Advisory Fee — expected |
| fact_transactions.txn_date | dim_date.date | |
| fact_fees.client_id | dim_client.client_id | |
| fact_fees.advisor_id | dim_advisor.advisor_id | |
| fact_fees.fee_date | dim_date.date | monthly, always the 1st |
| fact_portfolio_snapshot.client_id | dim_client.client_id | |
| fact_portfolio_snapshot.advisor_id | dim_advisor.advisor_id | |
| fact_portfolio_snapshot.benchmark_id | dim_benchmark.benchmark_id | |
| fact_portfolio_snapshot.snapshot_date | dim_date.date | monthly, always the 1st |
| dim_client.advisor_id | dim_advisor.advisor_id | snowflake link — the facts also carry advisor_id directly; they agree on 100.00% of fact rows |
| dim_security.benchmark_id | dim_benchmark.benchmark_id | snowflake link |

In the clean data, 13 of 13 relationships match 100% (checked here with `check_referential_integrity`; full detail in `reports/validation_referential_integrity.csv`). `dim_date` joins on `date` (YYYY-MM-DD), not on `date_id`, because no fact table carries `date_id`.

## Column-type settings a BI tool needs

| Set as | Columns | Why |
|---|---|---|
| **Text** | `dim_client.zip_code` | 228 ZIPs start with 0 (02068); a number type drops the zero |
| **Text** | `dim_advisor.certifications` | the value `None` means *no certification*; don't let the tool turn it into blank |
| **Text** | `account_type`, `primary_account_type` | the value `529` is a plan type, not a number |
| **Whole number** | all `*_id` columns (incl. `fact_transactions.security_id`, now `45` not `45.0`), `year`, `month`, `quarter`, `age`, `years_experience`, `aum_target_mm`, all `flag_*` | keys and counts |
| **Date** | `date`, `client_since`, `fee_date`, `snapshot_date`, `txn_date` | ISO `YYYY-MM-DD` |
| **Decimal / currency** | `initial_aum`, `aum`, `aum_basis`, `amount`, `price` | money |
| **Decimal** | `shares`, `bps_charged`, `expense_ratio_bps` | |
| **Decimal, format as %** | `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct` | stored as fractions (0.0928 = 9.28%) |
| **True/False** | `is_active`, `is_etf` | |
| **0/1** | `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day` | |

Blank is a legitimate value in: `dim_security.sector` (ETFs), `dim_security.expense_ratio_bps` (non-ETFs), and `fact_transactions.security_id`/`shares`/`price` (cash flows). Do not fill them.

## Flag columns added (0 = normal, 1 = look at this)

| Table | Column | Rows = 1 | Meaning | What to do in reports |
|---|---|---:|---|---|
| dim_client | flag_risk_profile_inferred | 75 | risk_profile was blank and was filled as 'Balanced' from the client's benchmark | confirm with the advisor before using for suitability |
| fact_transactions | flag_non_trading_day | 40,630 | Buy/Sell dated on a non-trading day (weekend or market holiday) | don't price these against that day's market data |
| fact_transactions | flag_after_client_exit | 2,410 | activity after an inactive client's last month | exclude from 'current client' activity |
| fact_portfolio_snapshot | flag_extreme_return | 977 | return_ytd above +100% or below −100% (driven by deposits/withdrawals) | exclude from average-return measures, or use the median |
| fact_portfolio_snapshot | flag_aum_floor | 420 | aum exactly $1,000 (source-system floor for drained accounts) | treat as ~0 for per-client analysis |

## Known limitations (not fixed, on purpose)

1. **Dividend amounts are not real dividends.** All 53,826 Dividend rows equal shares × price, i.e. the full position value (a 100% yield). It is every row, so it is how the source defines the field, and nothing lets us recompute the true payout. *Do not report dividend income from this column.*
2. **Two fee sources disagree.** Advisory Fee rows in `fact_transactions` ($263.7M) never match `fact_fees` ($204.7M) for the same client-month. Use **`fact_fees`** for fee revenue: its amount reconciles 100% to aum_basis × bps ÷ 12 and its aum_basis matches snapshot AUM 100%. Never add both.
3. **Weekend trade dates are kept.** The true fill date is unknown, so the date was not moved (flagged instead).
4. **300 converted returns have 4 decimal places** (they arrived as 2-dp percents). They reconcile to benchmark + alpha within half a basis point; I did not replace them with the calculated value.
5. **7,350 client-months have a snapshot but no fee row.** Consistent with fee waivers; no fee was invented.
6. **Unused benchmark(s): 6 (MSCI Emerging Markets)** — no client or security uses them. Kept; a dimension may list unused members.
7. **return_ytd mixes market return with cash flows** for the flagged accounts, so it is not a pure time-weighted return. A true TWR would need daily cash-flow-adjusted valuations we don't have.
