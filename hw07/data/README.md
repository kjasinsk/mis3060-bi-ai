# `growth_extract.csv`

Built by `scripts/00_make_extract.py` with pandas from `Data/Wildcat_Capital_Clean/` (not from Power BI).

**Grain:** one row per **year × client tier × region** (5 years × 3 tiers × 5 regions = **75 rows**). Region is `dim_advisor[region]`, reached through each fact row's `advisor_id`, which is the same path the Power BI model uses. In this data, every client keeps one advisor the whole time, so going through `dim_client[advisor_id]` would give the same answer.

| Column | Type | Meaning | Can I add it across years? |
|---|---|---|---|
| `year` | key | Calendar year (2020–2024) | — |
| `client_tier` | key | `dim_client[client_tier]` (Retail, HNW, UHNW) | — |
| `region` | key | `dim_advisor[region]` (Mid-Atlantic, Midwest, Northeast, Southeast, West) | — |
| `ending_aum` | **Balance** | Sum of `aum` on the December snapshot (dated `YYYY-12-01`) | **No.** It's a point-in-time snapshot, so adding 2023 + 2024 counts the same money twice. You *can* add it across tiers and regions **within one year** |
| `ending_aum_ly` | **Balance** | The same December balance one year earlier. Blank for 2020 | **No**, same reason |
| `net_flows` | **Flow** | Deposits − Withdrawals summed over the calendar year | **Yes.** Flows add across years, tiers and regions |
| `market_change` | **Flow** (a change over the year) | `ending_aum − ending_aum_ly − net_flows`. Blank for 2020 | **Yes**, it's the change during one year. But it's whatever growth net flows *don't* explain: market performance, plus dividends kept in the account, minus fees taken out |

**How to use it:** filter to one year first. Within a year, every column adds up across tiers and regions to the firm total. For example, the 15 rows for 2024 add up to Ending AUM **$12,729,572,078.86**, which is the same number as the `Ending AUM` measure in Power BI.

**Blank cells:** only the 2020 rows have blanks (`ending_aum_ly` and `market_change`), because the data starts in January 2020. I kept those rows so the grid has all 75 rows.
