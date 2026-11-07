# Part D: Claude session for measure 11, `Top 10 Client Share`

**How I ran this:** I used Claude in the Claude app (the same chat I used for the rest of HW6, which can see my repo and my Apporto session), not a separate Claude Desktop window. Below are the full prompt and Claude's full answer. The prompt has the metadata from `model_metadata.md`, plus the things the metadata can't show: the grain, that `aum` is a balance, that `active_alpha_ytd` is year-to-date, and the exact business definition from the assignment.

---

## Prompt

> I'm building a Power BI semantic model for a wealth-management firm (Wildcat Capital) and need one DAX measure. Below is my exported model metadata (from INFO.VIEW queries in DAX query view), then the things the metadata cannot tell you.
>
> ## Model metadata
>
> ### Relationships (INFO.VIEW.RELATIONSHIPS)
> All are many-to-one, single cross-filter direction, active unless noted:
> - fact_portfolio_snapshot[client_id] -> dim_client[client_id]
> - fact_portfolio_snapshot[advisor_id] -> dim_advisor[advisor_id]
> - fact_portfolio_snapshot[benchmark_id] -> dim_benchmark[benchmark_id]
> - fact_portfolio_snapshot[snapshot_date] -> dim_date[date]
> - fact_fees[client_id] -> dim_client[client_id]; fact_fees[advisor_id] -> dim_advisor[advisor_id]; fact_fees[fee_date] -> dim_date[date]
> - fact_transactions[client_id] -> dim_client[client_id]; fact_transactions[advisor_id] -> dim_advisor[advisor_id]; fact_transactions[security_id] -> dim_security[security_id]; fact_transactions[txn_date] -> dim_date[date]
> - dim_security[benchmark_id] -> dim_benchmark[benchmark_id]
> dim_date is marked as the date table on dim_date[date] (one row per day, 2020-01-01 to 2024-12-31).
>
> ### Columns that matter (INFO.VIEW.COLUMNS)
> | Table | Column | DataType |
> |---|---|---|
> | fact_portfolio_snapshot | snapshot_id | Integer |
> | fact_portfolio_snapshot | client_id | Integer |
> | fact_portfolio_snapshot | advisor_id | Integer |
> | fact_portfolio_snapshot | benchmark_id | Integer |
> | fact_portfolio_snapshot | snapshot_date | Date |
> | fact_portfolio_snapshot | year | Integer |
> | fact_portfolio_snapshot | month | Integer |
> | fact_portfolio_snapshot | aum | Number |
> | fact_portfolio_snapshot | return_ytd | Number |
> | fact_portfolio_snapshot | benchmark_return_ytd | Number |
> | fact_portfolio_snapshot | active_alpha_ytd | Number |
> | fact_portfolio_snapshot | cash_pct | Number |
> | fact_portfolio_snapshot | account_type | Text |
> | fact_portfolio_snapshot | is_return_suspect | Integer |
> | dim_client | client_id | Integer |
> | dim_client | client_tier | Text (Retail, HNW, UHNW) |
> | dim_client | risk_profile | Text |
> | dim_client | is_active | True/False |
> | dim_date | date | Date |
> | dim_date | year | Integer |
> | dim_date | month | Integer |
> | dim_date | quarter | Integer |
>
> ### Existing measures (INFO.VIEW.MEASURES), all in table _Measures, State = Valid
> - Ending AUM = CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )
> - Ending Clients = CALCULATE ( DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ), LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) ) )
> - Total Fees, Net Flows, AUM YoY %, Fee Yield (bps), AUM-Weighted Alpha (others, not needed here)
>
> ## What the metadata cannot tell you
> - Grain of fact_portfolio_snapshot: one row per client per month. Snapshot dates are always the 1st of the month (2020-01-01 ... 2024-12-01). Not every client has a row every month: clients join and leave, so the number of clients per snapshot date changes (175 clients left before the last snapshot and have no rows after they left).
> - aum is a BALANCE (semi-additive): never sum it across months. The right balance for any filter is the one at the last snapshot date that has data in that filter (that is what [Ending AUM] does).
> - active_alpha_ytd is a year-to-date rate (non-additive) - not needed for this measure.
>
> ## The measure I need
> Name: Top 10 Client Share
> Business definition: the share of Ending AUM held by the 10 largest clients WITHIN THE CURRENT FILTER. Example: in a table by dim_client[client_tier] filtered to 2024, the HNW row must show the share of HNW's Ending AUM held by the 10 largest HNW clients (not the 10 largest clients firm-wide). With no filter, it is the share of the firm's Ending AUM held by its 10 largest clients at the last snapshot.
>
> Please give me:
> 1. The DAX for the measure (reuse my existing measures where it makes sense).
> 2. A plain explanation of its filter context: which date it uses, which clients are ranked, and why it works in a tier table and at the grand total.
> 3. A DAX test query I can run in DAX query view to check it (grand total, by year, and by client tier for 2024), plus anything you think I should check by hand.

---

## Claude's response

### 1. The measure

```DAX
Top 10 Client Share =
VAR LastSnap =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
VAR Top10 =
    CALCULATE (
        SUMX ( TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM] ), [Ending AUM] ),
        LastSnap
    )
RETURN
    DIVIDE ( Top10, CALCULATE ( SUM ( fact_portfolio_snapshot[aum] ), LastSnap ) )
```

Format it as a percentage (`0.00%`).

### 2. Filter context, in plain terms

- **Which date.** `LastSnap` finds the latest day in the current filter that has snapshot rows, using the same rule as your `[Ending AUM]`. With no filter that is 2024-12-01. In a `dim_date[year] = 2022` row it is 2022-12-01. Because your snapshots are on the 1st of the month, `LASTDATE` or `ENDOFMONTH` would land on a day with no rows, so `LASTNONBLANK` is the right choice.
- **Which clients are ranked.** `VALUES ( dim_client[client_id] )` returns the clients that are visible in the current filter. In a tier table's HNW row, only HNW clients are visible, so the top 10 are the 10 largest HNW clients. That is the "within the current filter" part of your definition. If you used `ALL ( dim_client )` instead, every row would rank the firm-wide top 10, and the share in small tiers could go above 100%.
- **How each client is valued.** Inside `TOPN` and `SUMX`, `[Ending AUM]` is evaluated once per client (context transition). The outer `CALCULATE ( …, LastSnap )` pins every client to the same snapshot date, so the top-10 numerator and the denominator use the same day.
- **Why the date pin matters.** Without the `LastSnap` filter around `SUMX`, each client's `[Ending AUM]` would use that client's own last snapshot. A client who left in 2023 has no December 2024 row, so `LASTNONBLANK` would find their last 2023 balance. That stale balance could then be ranked into the top 10 and counted in the numerator, while the denominator (December 2024 only) leaves it out. The share would be overstated.
- **Grand total.** With no filter the same logic applies: the date is 2024-12-01, all 2,325 clients still present are ranked, and the denominator equals `[Ending AUM]`.
- **Blanks.** If a filter has no snapshot rows, `LastSnap` is empty, both parts are blank, and `DIVIDE` returns blank instead of an error.

### 3. Test query (DAX query view)

```DAX
// (a) Grand total: the share, its parts, and the client count
EVALUATE
VAR LastSnap = LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
RETURN ROW (
    "Last snapshot", LastSnap,
    "Top 10 Client Share", [Top 10 Client Share],
    "Top 10 AUM", CALCULATE ( SUMX ( TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM] ), [Ending AUM] ), LastSnap ),
    "Ending AUM", [Ending AUM],
    "Ending Clients", [Ending Clients]
)

// (b) By year: the share should move from year to year, not repeat one number
EVALUATE
SUMMARIZECOLUMNS ( dim_date[year], "Top 10 Client Share", [Top 10 Client Share], "Ending Clients", [Ending Clients] )

// (c) By tier for 2024: each tier ranks only its own clients
EVALUATE
CALCULATETABLE (
    SUMMARIZECOLUMNS ( dim_client[client_tier], "Top 10 Client Share", [Top 10 Client Share], "Ending AUM", [Ending AUM], "Ending Clients", [Ending Clients] ),
    dim_date[year] = 2024
)

// (d) Hand check: the 10 clients being counted at the last snapshot
EVALUATE
TOPN (
    10,
    CALCULATETABLE (
        ADDCOLUMNS ( VALUES ( dim_client[client_id] ), "AUM", [Ending AUM] ),
        LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
    ),
    [AUM], DESC
)
ORDER BY [AUM] DESC
```

What to check by hand:
- In (a), Top 10 AUM ÷ Ending AUM should equal the share, and the 10 rows in (d) should add up to Top 10 AUM.
- In (c), each tier's share should be larger than you'd get by dividing the firm-wide top 10 by that tier (a smaller pool means the top 10 hold more of it), and none should exceed 100%.
- Recompute the grand total in pandas: take the rows at the latest `snapshot_date`, sort `aum` by client, add up the top 10 and divide by the total.
- Ties: `TOPN` can return more than 10 rows if two clients tie at the 10th place. With balances stored to the cent this is very unlikely, but it is worth knowing.
