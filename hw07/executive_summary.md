# Executive Summary: Where Did 2024 Growth Come From?

Wildcat Capital ended 2024 with **$12.73B** in AUM, up **$2.08B (+19.6%)** from $10.64B a year earlier. Almost all of that growth came from markets. Market change added **$2.01B**, about **96%** of the increase, while net new money added only **$77.5M**, an organic growth rate of **0.73%**.

By client tier, UHNW clients drove the dollars: their AUM rose **$1.58B**, and less than 1% of that came from new money. Retail is the exception. Net flows of **$44.2M** were about **52%** of Retail's $85.7M increase, so Retail is the only tier where clients are adding money at a pace that matters. By region, the Northeast added the most AUM (**$735M**, 96% from markets), followed by the Mid-Atlantic ($621M) and the Southeast ($496M).

The takeaway: 2024 looked strong because markets were strong, not because the firm won much new money. If markets flatten, growth will depend on net new money, which is currently under 1% of last year's AUM.

**Limitation:** Market Change is a leftover: everything that net flows don't explain. It includes investment returns, but also fees taken out of accounts and any other cash movements, so it overstates "pure" market performance and is not the same thing as client returns.

*(199 words, not counting this note)*

## Audit table

Every number in the summary, traced to the measure and the reconciliation row that supports it (`reports/kpi_reconciliation.csv`, all rows match Power BI within tolerance).

| # | Claim in the summary | Measure(s) | Reconciliation row (value) | Status |
|---|---|---|---|---|
| 1 | Ending AUM 2024 = $12.73B | Ending AUM | `Ending AUM`, `year=2024` ($12,729,572,078.86) | Correct |
| 2 | Up $2.08B | Ending AUM − Ending AUM LY | `Ending AUM` − `Ending AUM LY`, `year=2024` ($12,729,572,078.86 − $10,644,971,737.00 = $2,084,600,341.86) | Correct |
| 3 | +19.6% | AUM YoY % | `AUM YoY %`, `year=2024` (0.19583) | Correct |
| 4 | From $10.64B a year earlier | Ending AUM LY | `Ending AUM LY`, `year=2024` ($10,644,971,737.00) | Correct |
| 5 | Market change added $2.01B | Market Change | `Market Change`, `year=2024` ($2,007,087,286.60) | Correct |
| 6 | About 96% of the increase | Market Change ÷ (Ending AUM − Ending AUM LY) | $2,007,087,286.60 ÷ $2,084,600,341.86 = 96.3% | Correct |
| 7 | Net new money $77.5M | Net Flows | `Net Flows`, `year=2024` ($77,513,055.26) | Correct |
| 8 | Organic growth rate 0.73% | Organic Growth Rate | `Organic Growth Rate`, `year=2024` (0.007282) | Correct |
| 9 | UHNW AUM rose $1.58B | Ending AUM − Ending AUM LY | `year=2024\|tier=UHNW`: $9,647,598,426.64 − $8,067,021,937.91 = $1,580,576,488.73 | Correct |
| 10 | Less than 1% of UHNW growth from new money | Net Flows ÷ change | `Net Flows`, `year=2024\|tier=UHNW` ($8,101,601.39) ÷ $1,580,576,488.73 = 0.51% | Correct |
| 11 | Retail net flows $44.2M | Net Flows | `Net Flows`, `year=2024\|tier=Retail` ($44,184,047.61) | Correct |
| 12 | About 52% of Retail's $85.7M increase | Net Flows ÷ change | Retail: $533,452,497.89 − $447,795,648.67 = $85,656,849.22; $44,184,047.61 ÷ $85,656,849.22 = 51.6% | Correct |
| 13 | Northeast added $735M, 96% from markets | Ending AUM − LY; Market Change | `year=2024\|region=Northeast`: $4,530,738,631.38 − $3,795,456,741.84 = $735,281,889.54; Market Change $703,081,496.10 = 95.6% | Correct |
| 14 | Mid-Atlantic $621M | Ending AUM − LY | `region=Mid-Atlantic`: $3,763,923,872.00 − $3,142,940,677.46 = $620,983,194.54 | Correct |
| 15 | Southeast $496M | Ending AUM − LY | `region=Southeast`: $3,064,446,334.69 − $2,568,402,938.22 = $496,043,396.47 | Correct |
| 16 | Net new money is under 1% of last year's AUM | Organic Growth Rate | `Organic Growth Rate`, `year=2024` (0.73%) | Correct |
| 17 | Market Change includes fees and other cash movements | Market Change definition | Assignment caveat; `Market Change = (Ending AUM − Ending AUM LY) − Net Flows` | Correct (stated as a limitation) |

**How I made it:** I gave Claude the verified numbers from `kpi_reconciliation.csv` (pasted, not a screenshot) and asked for a 150–200-word summary. Then I edited it and checked every number against the reconciliation. All 17 claims trace to a row above, so none needed correcting.
