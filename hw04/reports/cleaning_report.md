# Wildcat Capital — Data Cleaning Report

**To:** Portfolio Committee · **From:** Kaitlyn Jasinski, MIS3060 · **Scope:** 8 warehouse tables, 2020–2024

## Executive summary

The warehouse extract is usable for reporting after cleaning, but three things in the raw data would have quietly produced wrong numbers:

1. **Two out of three raw transactions could not join to the security table.** Security IDs were stored as `45.0` instead of `45`, so a text join matched **0%** of the 197,175 trades and dividends, and only **33.98%** of transactions joined to every dimension. After the fix, it's **100%**.
2. **Some records didn't belong.** There were 25 duplicate clients (the same person entered twice, with a one-letter typo in the last name) and 200 transactions for client IDs that don't exist (**$10.9M** of activity). These rows were moved to quarantine files, not deleted.
3. **Two fee sources disagree.** Fee debits in the transaction table total **$263.7M**, while the fee table totals **$204.7M**, and they match for only 1 of 28,746 client-months. **Use `fact_fees` for fee revenue.** It reconciles 100% to AUM × fee rate, and its AUM matches the account snapshots 100%.

After cleaning, every table scores **100%** on completeness, key uniqueness, type validity, hard-rule pass and referential match. No value was invented. Every change is traceable to one row in `value_changes.csv` (199,222 changed cells), and **raw rows = clean rows + quarantined rows** for all eight tables.

## What was cleaned

| # | Table / column | Problem | Action | Rows | How the fix was verified |
|---|---|---|---|---:|---|
| 1 | dim_client | Same client entered twice, last name misspelled | Quarantine | 25 | Matches original on all 12 other columns; 0 fact rows use these IDs |
| 2 | fact_transactions.client_id | Client ID not in client table | Quarantine | 200 | Client-ID match rate 99.93% → 100% |
| 3 | dim_client.state | Full name instead of code ("Pennsylvania") | Standardize | 77 | All states now valid 2-letter codes |
| 4 | dim_client.risk_profile | Blank | Fill "Balanced" + flag | 75 | Benchmark 3 is used only by Balanced clients (rule holds for 100% of 2,425 known clients) |
| 5 | fact_transactions.security_id | `45.0` instead of `45` | Convert | 197,044 | Text match to dim_security 0% → 100% |
| 6 | fact_transactions.shares | Negative shares on Buys | Remove minus sign | 835 | \|shares\| × price = amount for every row |
| 7 | fact_portfolio_snapshot.return_ytd | Stored as text "9.28%" | Divide by 100 | 300 | Equals benchmark + alpha within half a basis point |
| 8 | snapshot return / alpha | Scientific notation (9.9e-05) | Plain decimal | 891 | Value asserted unchanged |
| 9 | fact_transactions | Buy/Sell on a weekend | Flag only | 40,630 | — kept as recorded |
| 10 | fact_transactions | Activity after client left | Flag only | 2,410 | — kept as recorded |
| 11 | fact_portfolio_snapshot | YTD return beyond ±100% | Flag only | 977 | — kept as recorded |
| 12 | fact_portfolio_snapshot.aum | Stuck at exactly $1,000 | Flag only | 420 | — kept as recorded |

**Data quality scorecard (raw → clean)** — only tables that changed are shown; the other four were already 100% on every measure.

| Table | Completeness | Key uniqueness | Type validity | Rule pass | Referential match |
|---|---|---|---|---|---|
| dim_client | 99.785% → 100% | 99.01% → 100% | 100% → 100% | 93.069% → 100% | 100% → 100% |
| fact_portfolio_snapshot | 100% → 100% | 100% → 100% | 99.929% → 100% | 99.768% → 100% | 100% → 100% |
| fact_transactions | 100% → 100% | 100% → 100% | 91.73% → 100% | 99.72% → 100% | **33.982% → 100%** |

The plausibility score (rows with no flags) stays at 85.70% for transactions and 98.92% for snapshots. That's on purpose: those rows are flagged, not changed.

## Key judgment calls

**1. Fill blank risk profiles, but only because another table proves the answer.**
In the snapshot table, every risk profile uses exactly one benchmark, and benchmark 3 (60/40 Blend) belongs only to "Balanced" clients. All 75 blank-profile clients use benchmark 3, so they were filled as Balanced and marked `flag_risk_profile_inferred = 1`. *Why:* 75 clients (3% of the book) in a "(blank)" bucket would distort every suitability and allocation report. *Risk:* if the benchmark was assigned by default when the profile was missing, these clients may not really be Balanced. The flag lets compliance confirm all 75 with their advisors.

**2. Flag weekend trades instead of moving them to Monday.**
40,630 buys and sells (28.4% of trades) are dated on a Saturday or Sunday, almost exactly the weekend share of the calendar. That suggests the dates are when orders were entered, not when they filled. *Why not fix:* nothing in the data gives the real fill date, and moving it would invent one. *Risk:* pricing these trades against that day's market data would find no price. Analysts should filter on `flag_non_trading_day`.

**3. Keep extreme returns, but flag them.**
977 snapshots show a year-to-date return above +100% or below −100% (the largest is +9,467%). Each one equals benchmark + alpha exactly, so it isn't a typo. The "return" swings with deposits and withdrawals, so it isn't a pure investment return. *Why:* deleting them would remove real accounts; leaving them unmarked would let one row wreck an average. *Risk:* average-return measures are badly skewed unless flagged rows are excluded or a median is used.

**4. Quarantine instead of guessing an owner for orphan transactions.**
Each of the 200 orphan rows has a different unknown client ID, and each advisor serves 81–118 clients, so the true client can't be worked out. *Risk:* if these are real clients missing from the client file, activity is understated by 0.07% of rows. The quarantine file keeps every column so they can be restored.

## Limitations (known, not fixed)

- **Dividend amounts are not real dividends.** All 53,826 dividend rows equal the full position value (a 100% yield). Don't report dividend income from this column until the source system is checked.
- **Fee revenue exists in two systems that disagree** ($263.7M vs $204.7M). Use `fact_fees`, and never add both.
- **7,350 client-months have a snapshot but no fee.** That's consistent with fee waivers, so no fee was invented.
- **300 converted returns carry 4 decimal places** instead of 6, because they arrived rounded.
- **420 drained accounts show AUM of $1,000** (a system floor). Immaterial to the ~$12.7B book, but it overstates those accounts.
- **Rows flagged as IQR outliers are not errors.** 10.24% of AUM values and 9.28% of fee amounts sit above the outlier fence, but they are the firm's large HNW/UHNW accounts. They were kept and reviewed, not removed.

---
*AI-assisted report — reviewed for factual accuracy on [10/20/2026] by Kaitlyn Jasinski*
