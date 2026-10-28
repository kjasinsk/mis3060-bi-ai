# HW5 — Star Schema Design for Wildcat Capital

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

Built on the instructor's release (`Data/Wildcat_Capital_Clean/`, the same files loaded in Power BI). Every claim below is checked in `scripts/hw05_checks.py`. The script stops with an error if any key, relationship or grain fails. Its output is saved in `reports/keys_check.csv`, `reports/grain_check.csv` and `reports/measures.csv`.

---

## Part A — Keys

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_advisor | Dimension | `advisor_id` | — |
| dim_benchmark | Dimension | `benchmark_id` | — |
| dim_client | Dimension | `client_id` | `advisor_id` → dim_advisor[advisor_id] |
| dim_date | Dimension | `date_id` (also unique: `date`) | — |
| dim_security | Dimension | `security_id` | `benchmark_id` → dim_benchmark[benchmark_id] |
| fact_fees | Fact | `fee_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`fee_date` → dim_date[date] |
| fact_portfolio_snapshot | Fact | `snapshot_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`benchmark_id` → dim_benchmark[benchmark_id]<br>`snapshot_date` → dim_date[date] |
| fact_transactions | Fact | `txn_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`security_id` → dim_security[security_id] *(can be blank)*<br>`txn_date` → dim_date[date] |

**What the script proves**

- All 8 primary keys are unique and never blank. `dim_date[date]` is also unique, so it can be the "one" side of a relationship.
- All 13 foreign keys match their parent 100%, with 0 orphan rows (using `check_referential_integrity` from HW4).
- **The fact dates match `dim_date[date]`, not `dim_date[date_id]`.** Joined on `date_id`, all three fact date columns match 0%. Joined on `date`, they match 100%.

**Keys that can legitimately be blank**

- `fact_transactions.security_id` is blank on 101,528 rows. These are exactly the Deposit, Withdrawal and Advisory Fee rows (100% blank), and never a Buy, Sell or Dividend row (0% blank). A cash flow moves money in or out of the account and involves no security. See Part E(a).
- No other key is ever blank.

---

## Part B — Grain

- **fact_fees:** One row represents the fee charged to one client for one month (`client_id` + `fee_date` is unique; `fee_date` is always the 1st, and each client-month has exactly one fee type).
- **fact_portfolio_snapshot:** One row represents one client's account position (AUM, returns, cash) as of the 1st of one month (`client_id` + `snapshot_date` is unique; each client has one account).
- **fact_transactions:** One row represents one individual transaction event (a buy, sell, dividend, deposit, withdrawal or advisory-fee debit) for one client on one date (`txn_id`; no business-key combination is unique: 1,238 rows share client + security + date + type with another row (622 extra copies), mostly same-day cash flows where `security_id` is blank, plus 188 trades and dividends).

---

## Part C — Measures

**Rule of thumb used:** if I add this column across clients, across months, and across both, does the total still mean something?

### Measures in the fact tables

| Table | Column | Class | What that means for summing or averaging |
|---|---|---|---|
| fact_fees | `amount` | **Additive** | Fee dollars can be summed across clients, advisors and months: the total is fee revenue. |
| fact_fees | `aum_basis` | **Semi-additive** | It is a balance on a date, so it can be summed across clients for one month (firm AUM billed on), but across months you must take the latest or average month, never the sum. |
| fact_fees | `bps_charged` | **Non-additive** | It is a rate, so summing it means nothing; the correct average is weighted by AUM: SUM(amount) × 12 ÷ SUM(aum_basis) × 10,000. |
| fact_portfolio_snapshot | `aum` | **Semi-additive** | Sum across clients for one snapshot date (total AUM on 1 Dec 2024 = $12.73B), but never across months: adding Oct + Nov + Dec 2024 gives a fake $36.80B. Use the last month in the period. |
| fact_portfolio_snapshot | `return_ytd` | **Non-additive** | A percentage, and already cumulative for the year, so it cannot be summed across clients or months; average it weighted by AUM (and exclude `is_return_suspect` rows). |
| fact_portfolio_snapshot | `benchmark_return_ytd` | **Non-additive** | Same as `return_ytd`: a cumulative percentage that is read for one date, never summed. |
| fact_portfolio_snapshot | `active_alpha_ytd` | **Non-additive** | A difference of two percentages (return − benchmark); compare or AUM-weight it, never sum it. |
| fact_portfolio_snapshot | `cash_pct` | **Non-additive** | A share of each account; summing it across clients gave 102.9 (10,290%), which is meaningless; use the AUM-weighted average (4.41% on 1 Dec 2024). |
| fact_transactions | `amount` | **Additive** | Dollar flows can be summed across clients and dates, but **only within one `txn_type`**: every amount is stored as a positive number, so a plain SUM adds withdrawals to deposits. Dividend amounts are not real dividends (all 53,826 equal shares × price, the full position value), so don't report them. |
| fact_transactions | `shares` | **Additive** | Shares traded can be summed across clients and dates, but only for one security and one `txn_type` (100 shares of SPY + 100 of AGG is not "200 of anything"). |
| fact_transactions | `price` | **Non-additive** | A price per share; summing prices means nothing, so use a share-weighted average (SUM(amount) ÷ SUM(shares)) for Buy/Sell rows. |

### Numeric columns in the fact tables that are not measures

| Kind | Columns | Why not |
|---|---|---|
| Keys | `fee_id`, `snapshot_id`, `txn_id`, and every `client_id`, `advisor_id`, `benchmark_id`, `security_id` in a fact | IDs are labels; summing them is meaningless. Use them to join or to COUNT / DISTINCTCOUNT. |
| Date parts | `fact_portfolio_snapshot.year`, `month` | Copies of the snapshot date; slice by `dim_date` instead. |
| Flags | `fact_portfolio_snapshot.is_return_suspect`, `fact_transactions.is_post_departure_txn` | 0/1 markers used to filter rows (3,875 suspect returns; 2,410 transactions after a client left). Summing one only counts flagged rows; it is not a business amount. |

### Numeric attributes in the dimension tables that should never be summed

| Table | Columns | Why |
|---|---|---|
| dim_advisor | `years_experience`, `aum_target_mm` | Describe one advisor. Summed across a region they would count an advisor once per fact row, so average or show them per advisor instead. |
| dim_client | `age`, `initial_aum` | `age` is a description. `initial_aum` is each client's balance on their own start date, so a sum mixes different dates; it is not the firm's AUM. |
| dim_client | `zip_code` | A code stored as text, not a number. |
| dim_security | `expense_ratio_bps` | A rate (blank for non-ETFs). Average it, weighted by holdings if possible. |
| dim_date | `date_id`, `year`, `quarter`, `month`, `week_of_year`, `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day` | Calendar labels and flags for grouping and filtering. |
| All dimensions | every `*_id` | Keys. |

---

## Part E — Relationships and design questions

### The model I built

All relationships are **many-to-one (*:1)**, from the fact to the dimension, with **single** cross-filter direction (the dimension filters the fact).

| From (many) | To (one) | Status |
|---|---|---|
| fact_fees[client_id] | dim_client[client_id] | Active |
| fact_fees[advisor_id] | dim_advisor[advisor_id] | Active |
| fact_fees[fee_date] | dim_date[date] | Active |
| fact_portfolio_snapshot[client_id] | dim_client[client_id] | Active |
| fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | Active |
| fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | Active |
| fact_portfolio_snapshot[snapshot_date] | dim_date[date] | Active |
| fact_transactions[client_id] | dim_client[client_id] | Active |
| fact_transactions[advisor_id] | dim_advisor[advisor_id] | Active |
| fact_transactions[security_id] | dim_security[security_id] | Active |
| fact_transactions[txn_date] | dim_date[date] | Active |
| dim_client[advisor_id] | dim_advisor[advisor_id] | **Inactive** (see b and d) |
| dim_security[benchmark_id] | dim_benchmark[benchmark_id] | **Inactive** (see d) |

`dim_date` is marked as the date table, using its `date` column.

**Conformed dimensions** (shared by more than one fact, so one slicer filters all of them the same way): `dim_date`, `dim_client` and `dim_advisor` connect to all three facts. `dim_benchmark` connects only to the snapshot, and `dim_security` only to transactions.

### (a) Some transaction rows have no `security_id`. Why? Is that a defect?

No, it is not a defect. The blank rows are exactly the Deposit, Withdrawal and Advisory Fee transactions (all 101,528 of them, and 100% of each type), while every Buy, Sell and Dividend has a security. A deposit or a fee is cash moving in or out of the account, so there is no security to point to; that is also why `shares` and `price` are blank on the same rows. In Power BI these rows join to the blank member of `dim_security`, so a visual by security shows them under "(Blank)", which is correct. I did not fill them with a fake "Cash" security, because the brief says not to build new rows or columns.

### (b) `advisor_id` is in `dim_client` and on all three facts. Which relationships are active, and why?

I kept the three **fact → dim_advisor** relationships active and made **dim_client → dim_advisor** inactive. If all four were active, Power BI would have two paths from `dim_advisor` to each fact (directly, and through `dim_client`), which is ambiguous, so it would not allow it. The direct fact links are the standard star design: each fact row records which advisor it belongs to at the time, and a filter on advisor reaches each fact in one step. The script shows the two sources agree on 100% of fact rows today, so nothing is lost. The inactive link is still there if a measure ever needs "the client's current advisor" (with USERELATIONSHIP).

### (c) `dim_date` has its own `date_id`, but the facts store calendar dates. Which column did I join on, and why?

I joined on **`dim_date[date]`**. None of the fact tables carries `date_id`; they store the calendar date itself (`2024-12-01`). The script proves it: the fact dates match `date_id` 0% and `date` 100%. Joining on `date` also lets me **mark `dim_date` as the date table** with a real Date column, which time-intelligence DAX in Assignment 6 needs. Both sides are set to the Date type, not text, so they match exactly.

### (d) Star or snowflake? Does anything connect one dimension to another? Did I keep it?

Two links connect a dimension to another dimension: `dim_client.advisor_id → dim_advisor` and `dim_security.benchmark_id → dim_benchmark`. Keeping them active would make the model a snowflake. I kept both as **inactive** relationships, so the model works as a **star**:

- `dim_client → dim_advisor` is not needed, because every fact already carries `advisor_id` (and it would be ambiguous; see b).
- `dim_security → dim_benchmark` would let a benchmark slicer filter transactions through the security, while it filters snapshots through the client's account. One slicer would then mean two different things ("the client's benchmark" vs. "the security's benchmark") in the same report. Inactive, it is still available on purpose through USERELATIONSHIP.

---

## Part F — Reflection

| # | Fact table | Manager's question | One visual, no DAX workaround? |
|---|---|---|---|
| 1 | fact_fees | "How much fee revenue did each advisor region earn per quarter in 2024?" | **Yes** |
| 2 | fact_portfolio_snapshot | "How has total AUM by client tier changed from quarter to quarter?" | **No** |
| 3 | fact_transactions | "What was each advisor's net new money (deposits minus withdrawals) in 2024?" | **No** |

**1. Fee revenue by region and quarter: yes.** `amount` is fully additive, so a matrix with `dim_advisor[region]` on rows, `dim_date[quarter]` on columns, a 2024 filter and the default SUM of `amount` gives the right answer with no DAX.

**2. AUM by tier by quarter: no.** `aum` is semi-additive. At the month level a SUM is fine, but at the quarter level Power BI adds the three monthly balances and roughly triples the real AUM. The usual fix is to filter to quarter-end, but the snapshots are dated the **1st** of the month, while `dim_date`'s `is_month_end` and `is_quarter_end` flags mark the **last** day. In the data, 0 of 129,547 snapshots fall on a flagged day, so the flag can't be used. Today this needs a DAX measure (e.g. take the last snapshot date in the period). **Schema fix:** add a `is_snapshot_period_close` flag to `dim_date` (or date snapshots at month-end), so a user can filter to the closing snapshot in one visual.

**3. Net new money by advisor: no.** Every `amount` is stored as a positive number, so SUM adds withdrawals to deposits. A `txn_type` filter can show deposits and withdrawals side by side, but not the net, without a DAX measure. **Schema fix:** add a `signed_amount` column (positive for money in, negative for money out), or a small `dim_txn_type` table with a direction column. A related question, "how much dividend income did we earn by sector?", can't be answered at all, because the dividend amounts in the source are full position values, not payouts (every Dividend row equals shares × price); that needs corrected source data, not a schema change.
