# HW5 — Star Schema Design for Wildcat Capital

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

I used the instructor's clean data (`Data/Wildcat_Capital_Clean/`), which is the same data I loaded into Power BI. Every number in this file comes from `scripts/hw05_checks.py`. The script stops with an error if a key, relationship or grain check fails, and it saves its results in `reports/keys_check.csv`, `reports/grain_check.csv` and `reports/measures.csv`.

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

**What the script shows:**

- All 8 primary keys are unique and never blank. `dim_date[date]` is also unique, so it can be used to join.
- All 13 foreign keys match their parent table 100%, with no orphan rows. I used the same `check_referential_integrity` function from HW4.
- The fact dates match `dim_date[date]`, not `dim_date[date_id]`. When I join on `date_id`, the fact dates match 0%. When I join on `date`, they match 100%.

**Keys that can be blank:**

- `fact_transactions.security_id` is blank on 101,528 rows. These are all of the Deposit, Withdrawal and Advisory Fee rows, and none of the Buy, Sell or Dividend rows. This makes sense because a deposit or a fee is just cash moving in or out, so there is no security involved. (See Part E(a).)
- No other key is ever blank.

---

## Part B — Grain

- **fact_fees:** One row represents the fee charged to one client for one month. Every `fee_date` is the 1st of the month, and each client only has one fee per month.
- **fact_portfolio_snapshot:** One row represents one client's account (AUM, returns and cash) on the 1st of one month. Each client only has one account.
- **fact_transactions:** One row represents one transaction (a buy, sell, dividend, deposit, withdrawal or advisory fee) for one client on one date. Only `txn_id` makes a row unique. For example, 1,238 rows have the same client, security, date and type as another row (622 extra copies). Most of these are the same cash flow happening twice in one day.

---

## Part C — Measures

To classify each column, I asked myself: if I add this up across clients, across months, or both, does the total still mean something?

### Measures in the fact tables

| Table | Column | Class | What it means for adding or averaging |
|---|---|---|---|
| fact_fees | `amount` | **Additive** | I can add fee dollars across clients, advisors and months, and the total is our fee revenue. |
| fact_fees | `aum_basis` | **Semi-additive** | This is a balance on a date. I can add it across clients for one month, but not across months, so for a quarter I should use the latest month instead of the sum. |
| fact_fees | `bps_charged` | **Non-additive** | This is a rate, so adding it up means nothing. The right average is weighted by AUM: SUM(amount) × 12 ÷ SUM(aum_basis) × 10,000. |
| fact_portfolio_snapshot | `aum` | **Semi-additive** | I can add it across clients for one date (total AUM on Dec 1, 2024 = $12.73B), but not across months. For example, adding Oct + Nov + Dec 2024 gives a fake $36.80B. I should use the last month in the period. |
| fact_portfolio_snapshot | `return_ytd` | **Non-additive** | This is a percentage that already builds up over the year, so it can't be added across clients or months. I should take an AUM-weighted average and leave out the `is_return_suspect` rows. |
| fact_portfolio_snapshot | `benchmark_return_ytd` | **Non-additive** | Same as `return_ytd`. It's a percentage for one date, so it should never be added up. |
| fact_portfolio_snapshot | `active_alpha_ytd` | **Non-additive** | This is the return minus the benchmark, so it's also a percentage. I can compare it or take an AUM-weighted average, but not add it. |
| fact_portfolio_snapshot | `cash_pct` | **Non-additive** | This is the share of each account in cash. Adding it across clients gave 102.9 (10,290%), which doesn't mean anything. The AUM-weighted average is 4.41% on Dec 1, 2024. |
| fact_transactions | `amount` | **Additive** | I can add dollar amounts across clients and dates, but only within one `txn_type`. Every amount is stored as a positive number, so a plain SUM would add withdrawals to deposits. Also, the Dividend amounts are not real dividends: all 53,826 equal shares × price, which is the full position value, so I wouldn't report them. |
| fact_transactions | `shares` | **Additive** | I can add shares across clients and dates, but only for one security and one `txn_type`. For instance, 100 shares of SPY + 100 shares of AGG isn't "200" of anything. |
| fact_transactions | `price` | **Non-additive** | This is a price per share, so adding prices means nothing. For Buy and Sell rows, the right average is SUM(amount) ÷ SUM(shares). |

### Numeric columns in the fact tables that are not measures

| Kind | Columns | Why not |
|---|---|---|
| Keys | `fee_id`, `snapshot_id`, `txn_id`, and every `client_id`, `advisor_id`, `benchmark_id`, `security_id` in a fact | IDs are just labels, so adding them means nothing. They're used to join tables or to count rows. |
| Date parts | `fact_portfolio_snapshot.year`, `month` | These are copies of the snapshot date. I should use `dim_date` to slice by date instead. |
| Flags | `fact_portfolio_snapshot.is_return_suspect`, `fact_transactions.is_post_departure_txn` | These are 0/1 markers for filtering (3,875 suspect returns and 2,410 transactions after a client left). Adding one up only counts the flagged rows. |

### Numeric attributes in the dimension tables that should never be added up

| Table | Columns | Why |
|---|---|---|
| dim_advisor | `years_experience`, `aum_target_mm` | These describe one advisor. If I added them up across a region, an advisor would be counted once for every fact row, so I should average them or show them per advisor. |
| dim_client | `age`, `initial_aum` | Age just describes the client. `initial_aum` is each client's balance on the day they joined, so adding them mixes different dates and isn't the firm's AUM. |
| dim_client | `zip_code` | This is a code stored as text, not a number. |
| dim_security | `expense_ratio_bps` | This is a rate (and it's blank for non-ETFs), so it should be averaged, not added. |
| dim_date | `date_id`, `year`, `quarter`, `month`, `week_of_year`, `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day` | These are calendar labels and flags for grouping and filtering. |
| All dimensions | every `*_id` | These are keys. |

---

## Part E — Relationships and design questions

### The model I built

Every relationship is **many-to-one (*:1)** from the fact to the dimension, with **single** cross-filter direction, so the dimension filters the fact.

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

I marked `dim_date` as the date table using its `date` column.

**Conformed dimensions:** `dim_date`, `dim_client` and `dim_advisor` connect to all three fact tables, so one slicer on any of them filters all three the same way. `dim_benchmark` only connects to the snapshot table, and `dim_security` only connects to transactions.

### (a) Some transaction rows have no `security_id`. Why? Is that a defect?

No, I don't think it's a defect. The blank rows are exactly the Deposit, Withdrawal and Advisory Fee transactions (all 101,528 of them), and every Buy, Sell and Dividend has a security. A deposit or a fee is just cash moving in or out of the account, so there is no security to link to. That's also why `shares` and `price` are blank on those same rows. In Power BI, these rows show up under "(Blank)" in a visual by security, which is correct. I didn't fill them in with a fake "Cash" security, because the assignment says to use the tables as they are, without adding new tables or columns.

### (b) `advisor_id` is in `dim_client` and on all three facts. Which relationships did I keep active, and why?

I kept the three fact → dim_advisor relationships active and made dim_client → dim_advisor inactive. If all four were active, Power BI would have two different paths from `dim_advisor` to each fact (one directly and one through `dim_client`), and it doesn't allow that because it's ambiguous. I chose the direct fact links because that's the normal star design, and each fact row already says which advisor it belongs to. The script also shows that the two advisor columns agree on 100% of fact rows, so I'm not losing anything. I kept the inactive link in case a measure ever needs "the client's current advisor" (using USERELATIONSHIP).

### (c) `dim_date` has its own `date_id`, but the facts store calendar dates. Which column did I join on, and why?

I joined on `dim_date[date]`. None of the fact tables have a `date_id` column. They store the actual date (like 2024-12-01). The script proves this: the fact dates match `date_id` 0% of the time and `date` 100% of the time. Joining on `date` also lets me mark `dim_date` as the date table, which I'll need for the time-intelligence DAX in Assignment 6. Both sides are set to the Date type, so they match exactly.

### (d) Star or snowflake? Does anything connect one dimension to another? Did I keep it?

Yes, two links connect one dimension to another: `dim_client.advisor_id → dim_advisor` and `dim_security.benchmark_id → dim_benchmark`. If they were active, the model would be a snowflake. I kept both of them but made them inactive, so the model works as a star.

- I don't need `dim_client → dim_advisor`, because every fact table already has `advisor_id` (and it would be ambiguous, see b).
- If `dim_security → dim_benchmark` were active, a benchmark slicer would filter transactions by the security's benchmark but filter snapshots by the client's benchmark. One slicer would mean two different things in the same report, which would be confusing. Since it's inactive, it's still there if I need it with USERELATIONSHIP.

---

## Part F — Reflection

| # | Fact table | Manager's question | One visual, no DAX workaround? |
|---|---|---|---|
| 1 | fact_fees | "How much fee revenue did each advisor region earn per quarter in 2024?" | **Yes** |
| 2 | fact_portfolio_snapshot | "How has total AUM by client tier changed from quarter to quarter?" | **No** |
| 3 | fact_transactions | "What was each advisor's net new money (deposits minus withdrawals) in 2024?" | **No** |

**1. Fee revenue by region and quarter: yes.** Fee `amount` is fully additive, so I can make a matrix with `dim_advisor[region]` on the rows, `dim_date[quarter]` on the columns, a 2024 filter and the SUM of `amount`. That gives the right answer without any DAX.

**2. AUM by tier by quarter: no.** AUM is semi-additive. At the month level a SUM works, but at the quarter level Power BI would add up three months of balances and almost triple the real AUM. Normally I would just filter to the end of the quarter, but the snapshots are dated the 1st of each month, while the `is_month_end` and `is_quarter_end` flags in `dim_date` are on the last day. 0 of the 129,547 snapshots land on a flagged day, so the flag doesn't help. Right now I would need a DAX measure that takes the last snapshot in the period. To fix the schema, I would add a flag to `dim_date` for the last snapshot date of each period (or date the snapshots at month-end), so the user could just filter to it in one visual.

**3. Net new money by advisor: no.** Every `amount` is stored as a positive number, so a SUM adds withdrawals to deposits. I could filter `txn_type` to show deposits and withdrawals next to each other, but not the net, without a DAX measure. To fix the schema, I would add a `signed_amount` column (positive for money in, negative for money out), or a small `dim_txn_type` table with a direction column. A related question, "how much dividend income did we earn by sector?", can't be answered at all, because the dividend amounts are full position values and not real payouts (every Dividend row equals shares × price). That would need better source data, not just a schema change.
