# HW6 Measure Library: AUM & Performance

**MIS3060 Business Intelligence with AI · Kaitlyn Jasinski**

All measures are in the `_Measures` table in `powerbi/hw06.pbix`, and every number below is checked against pandas in `reports/measure_reconciliation.csv` (91 of 91 rows match).

## How the patterns work (from Assignment 5 Part C)

| Pattern | Used for | Rule |
|---|---|---|
| **SUM** | `fact_fees[amount]`, `fact_transactions[amount]` (within one `txn_type`) | Safe to add up across any dimension |
| **Last balance** | `fact_portfolio_snapshot[aum]` | Never add across months. Take the balance at the last snapshot date with data in the current filter (`LASTNONBLANK`). Snapshots are dated the 1st, so `LASTDATE` would land on a day with no rows |
| **Recompute-and-weight** | rates, ratios, `active_alpha_ytd` | Never sum or average a rate. Rebuild it from additive parts (or weight it by `aum`) in each filter |

## Part A: the measures

### Base: `Total Fees`

```DAX
Total Fees =
SUM ( fact_fees[amount] )
```

- **Pattern:** SUM
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** Total fees Wildcat billed in the period. Base measure from ICE 9, reused by Fee Yield.

### Base: `Net Flows`

```DAX
Net Flows =
CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )
    - CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )
```

- **Pattern:** SUM
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** New money clients put in minus money they took out. Base measure from ICE 10, reused by Organic Growth Rate.

### 0. `AUM (naive SUM)`

```DAX
AUM (naive SUM) =
-- WRONG ON PURPOSE: adds the same balance once per month. Never use on a report.
SUM ( fact_portfolio_snapshot[aum] )
```

- **Pattern:** SUM on a balance — **wrong**
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** Not a real number: it adds every month's balance together, so the 5-year total is about 45 times what Wildcat actually manages. Kept only to show the mistake; it is not on the report page.

### 1. `Ending AUM`

```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```

- **Pattern:** Last balance
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** How much money Wildcat manages at the latest month-end snapshot in whatever period or group is selected.

### 2. `Ending Clients`

```DAX
Ending Clients =
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```

- **Pattern:** Last balance
- **Format:** Whole number
- **For a Wildcat manager:** How many clients have money with Wildcat at that same latest snapshot.

### 3. `Avg AUM per Client`

```DAX
Avg AUM per Client =
DIVIDE ( [Ending AUM], [Ending Clients] )
```

- **Pattern:** Recompute-and-weight (ratio of two last balances)
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** The size of a typical relationship; a manager can see which tiers bring big accounts.

### 4. `Ending AUM LY`

```DAX
Ending AUM LY =
CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )
```

- **Pattern:** Last balance (shifted one year)
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** What Ending AUM was at the same point one year earlier, the starting line for growth.

### 4. `AUM YoY %`

```DAX
AUM YoY % =
DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )
```

- **Pattern:** Recompute-and-weight (ratio of two last balances)
- **Format:** Percent, 2 decimals
- **For a Wildcat manager:** How much the managed balance grew over the past year, from markets and new money together.

### 5. `Ending AUM PM`

```DAX
Ending AUM PM =
CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )
```

- **Pattern:** Last balance (shifted one month)
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** What Ending AUM was one month earlier.

### 5. `AUM MoM %`

```DAX
AUM MoM % =
DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
```

- **Pattern:** Recompute-and-weight (ratio of two last balances)
- **Format:** Percent, 2 decimals
- **For a Wildcat manager:** Month-over-month growth, for spotting a sudden jump or drop.

### 6. `Avg Monthly AUM`

```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```

- **Pattern:** Average of balances (sum of balances ÷ number of months)
- **Format:** Currency, 2 decimals
- **For a Wildcat manager:** The typical balance across the months selected; the fair base for anything earned over the whole period, like fees.

### 7. `Fee Yield (bps)`

```DAX
Fee Yield (bps) =
DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_portfolio_snapshot[aum] ) )
```

- **Pattern:** Recompute-and-weight (two fact tables)
- **Format:** Number, 2 decimals (bps)
- **For a Wildcat manager:** What Wildcat earns per year on each dollar it manages: 43 bps means $43 a year per $10,000.

### 8. `Organic Growth Rate`

```DAX
Organic Growth Rate =
DIVIDE ( [Net Flows], [Ending AUM LY] )
```

- **Pattern:** Recompute-and-weight (flows ÷ last year's balance)
- **Format:** Percent, 2 decimals
- **For a Wildcat manager:** Growth that came only from clients adding money, with market gains taken out.

### 9. `AUM-Weighted Alpha`

```DAX
AUM-Weighted Alpha =
VAR LastSnap = LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnap,
        fact_portfolio_snapshot[is_return_suspect] = 0
    )
```

- **Pattern:** Recompute-and-weight (at the last balance)
- **Format:** Percent, 2 decimals
- **For a Wildcat manager:** How far ahead of or behind their benchmarks clients are this year, with big accounts counting more, leaving out returns flagged as suspect.

### 10. `Alpha Signal`

```DAX
Alpha Signal =
VAR a = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( a ), BLANK (),
        a >= 0.02, "Outperforming",
        a <= -0.02, "Lagging",
        "In line"
    )
```

- **Pattern:** Label on a recomputed rate
- **Format:** Text
- **For a Wildcat manager:** A plain-English flag for the alpha number, so a manager sees at a glance if a group is ahead (≥ +2%), behind (≤ −2%) or in line.

### 11. `Top 10 Client Share`

```DAX
Top 10 Client Share =
VAR LastSnap = LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
VAR Top10 =
    CALCULATE (
        SUMX ( TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM] ), [Ending AUM] ),
        LastSnap
    )
RETURN
    DIVIDE ( Top10, CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnap ) )
```

- **Pattern:** Recompute-and-weight (at the last balance)
- **Format:** Percent, 2 decimals
- **For a Wildcat manager:** How concentrated the book is: the share of the selected group's money held by its 10 largest clients. A high number means losing one client would hurt.


## Measures page (in `hw06.pbix`)

The page is named **Measures** and the file is saved with it open.
- **Cards** across the top: Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share
- **Table by `dim_date[year]`**: Ending AUM, AUM YoY %, Avg Monthly AUM, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal
- **Table by `dim_client[client_tier]`**, filtered to 2024 with a visual-level filter on `dim_date[year]`: Ending AUM, Avg AUM per Client, AUM YoY %, Fee Yield (bps), Organic Growth Rate, AUM-Weighted Alpha, Alpha Signal, Top 10 Client Share

`AUM (naive SUM)` is in the model but is **not** on the page, on purpose.

---

## Part C: Design questions

All numbers below come from `scripts/02_design_questions.py` (output saved in `reports/design_questions_output.txt`). Where it says "Power BI" I also ran the number in DAX query view.

### (a) `Ending AUM` vs `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )`

| | Value |
|---|---:|
| `Ending AUM` (no filters) | **$12,729,572,078.86** |
| `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` | **$13,149,297,713.80** |
| Difference | **$419,725,634.94** |

Both numbers are the same in Power BI and pandas.

**Why they're different:** `Ending AUM` finds one date for the whole filter, the last snapshot (2024-12-01), and adds up every balance on that date. The SUMX version runs `[Ending AUM]` **once per client**, so each client gets their *own* last snapshot. For the 2,325 clients still with Wildcat that is December 2024 either way. But 175 clients left between December 2022 and November 2023 (all 175 have `is_active = False`). The SUMX version still counts each of them at their final balance, and those old balances add up to exactly the $419,725,634.94 difference.

**Which one answers "How much do we manage today?"** `Ending AUM`, the $12.73B. The extra $0.42B is money that already left the firm. The SUMX version would be like counting the balance of an account that was closed a year ago.

### (b) Why 2024 `Fee Yield (bps)` is lower than the ICE 9 `Effective Fee Rate (bps)`

| 2024 | Formula | Value |
|---|---|---:|
| Fee Yield | fees × 12 × 10,000 ÷ Σ snapshot `aum` | **43.15 bps** |
| Effective Fee Rate (ICE 9) | fees × 12 × 10,000 ÷ Σ fee `aum_basis` | **45.53 bps** |

Same fees on top, so the difference has to be the bottom of the fraction. The snapshot `aum` adds up to $135.46B for 2024, but `aum_basis` only adds up to $128.39B.

What pandas shows when you match the two tables on client + month:
- 27,900 snapshot rows in 2024, but only **26,216 have a fee row**. **1,684 client-months (6.0%) have AUM but no fee at all.**
- Every fee row has a matching snapshot (0 left over), and where both exist, `aum_basis` equals `aum` exactly (biggest difference $0.00).
- The 1,684 no-fee months hold **$7.07B** of summed AUM, which is **5.2% of the Fee Yield denominator**.
- If I compute Fee Yield on only the months that have a fee, I get **45.53 bps**, exactly the Effective Fee Rate.
- It's spread out, not a few accounts: 1,082 of 2,325 clients are missing at least one month, and no client is missing all 12. It happens every year too (1,139 / 1,505 / 1,365 / 1,657 / 1,684 missing months from 2020 to 2024).

**Cause:** Fee Yield divides by all the money Wildcat manages, but about 6% of client-months never got a fee row, so that AUM is in the denominator with nothing on top. Effective Fee Rate only looks at months that were billed.

**Data limitation it shows:** the fee table is incomplete. It's missing about 6% of client-months, and the data can't tell us *why*. A missing row could be a waived fee, a billing gap, or a record that never got loaded. So Effective Fee Rate overstates what Wildcat earns on its whole book, and Fee Yield understates the rate it actually charges on billed accounts. The true "price" is somewhere in between depending on what the missing rows really are.

### (c) Why `AUM-Weighted Alpha` is read at the last snapshot, and why suspects are excluded

**Last snapshot only:** `active_alpha_ytd` is year-to-date, so each month already includes all the months before it. The December row is the full-year number, while January's is just one month. If you mix the months together you're averaging a one-month number with a twelve-month number. In pandas the weighted alpha for 2024 climbs month by month, from −0.01% in January to 1.45% in December. Blending all twelve 2024 months gives 0.32%, which isn't the alpha of any real period.

**Excluding `is_return_suspect = 1`:** at the last snapshot, 148 of 2,325 rows are flagged. Their alphas run from −120.9% to **+7,133.8%** (one return is +7,152.9% for the year), which isn't believable for a client portfolio. A few rows like that can swing the whole number.

| At 2024-12-01 | Suspects excluded | Suspects included |
|---|---:|---:|
| **AUM-weighted** (the measure) | **1.45%** | 1.67% |
| Simple mean of `active_alpha_ytd` | 0.88% | 15.56% |

The simple mean with suspects is 15.56%, more than 10 times the real answer, because each tiny account with a crazy return counts as much as a $80M account. Weighting by AUM shrinks that damage (suspect accounts are small, about $105K on average), but they still push the answer from 1.45% to 1.67%, enough to move it toward the "Outperforming" line. The simple mean without suspects (0.88%) is lower than the weighted one, which means the bigger accounts did better than the smaller ones.

### (d) Organic Growth Rate by client tier, 2024

| Tier | Net flows | AUM Dec 2023 | AUM Dec 2024 | Organic Growth | AUM YoY % | Share of growth from new money |
|---|---:|---:|---:|---:|---:|---:|
| Retail | $44.2M | $447.8M | $533.5M | **9.87%** | 19.13% | 52% |
| HNW | $25.2M | $2,130.2M | $2,548.5M | **1.18%** | 19.64% | 6% |
| UHNW | $8.1M | $8,067.0M | $9,647.6M | **0.10%** | 19.59% | 0.5% |
| Firm | $77.5M | $10,645.0M | $12,729.6M | **0.73%** | 19.58% | 4% |

**What it says:** all three tiers grew almost the same amount (about 19–20%), but for very different reasons. For HNW and UHNW, almost all of the growth came from the markets, not from clients adding money. Retail is the only tier where net new money is a big part of the story: about half of Retail's growth came from deposits. Retail also brings in the most new money in dollars ($44.2M of the firm's $77.5M), even though it's the smallest tier. The client counts didn't change in 2024 (1,394 / 687 / 244 in both Decembers), so none of this came from winning or losing clients.

**What it does not tell you:**
- **It isn't profit.** Retail pays much higher fees (82.81 bps vs 61.39 HNW and 36.14 UHNW in 2024), so a dollar of Retail flow earns more than twice as much as a dollar of UHNW flow. Organic growth doesn't show that.
- **The rest isn't proven to be market returns.** AUM YoY minus organic growth is everything else: market gains, dividends left in the account, and fees taken out. The data doesn't split those.
- **It's net, so it hides churn.** Retail clients deposited $245.3M and withdrew $201.1M. That's a lot of money moving for $44.2M of net growth.
- **It doesn't say who.** One big deposit or many small ones look the same. You'd need to break it down by client or advisor.
- **It's one year.** One year of flows doesn't make a trend, and with UHNW at 0.10%, a single large withdrawal could flip it negative next year.
