# HW7 Design Plan: Where Did 2024 Growth Come From?

**MIS3060 · Kaitlyn Jasinski**

## 1. Audience and question

- **Audience:** Wildcat Capital's managing director, who reads it in a meeting and has about 10 seconds per page.
- **Question:** Where did 2024 AUM growth come from (markets or new money), and which client segments and regions drove it?
- **10-second takeaway:** AUM grew **$2.08B (+19.6%)** in 2024, but **96% of that came from markets** and only **$77.5M (0.73% organic growth)** from net new money. UHNW clients and the Northeast drove most of the dollars. Retail is the only tier where new money is about half of its growth.

## 2. Wireframes

| Page | File |
|---|---|
| Page 1, Growth Drivers | [`design/wireframe_page1.png`](design/wireframe_page1.png) |
| Page 2, Segment Detail (drill-through) | [`design/wireframe_page2.png`](design/wireframe_page2.png) |

Each box in the wireframe names the visual, its fields and measures, and the question it answers. The canvas is 1280 × 720.

## 3. Visual choices (Week 11 reasoning)

| Visual | Data types | # measures | Analysis type | Why this visual |
|---|---|---|---|---|
| Headline (dynamic text) | 1 text measure | 1 | Summary | The answer in one sentence, before any chart. It changes with the year slicer |
| KPI cards ×4 | Single numbers | 1 each (Ending AUM also shows AUM YoY %) | Status / comparison to last year | One number per card, read left to right: size → new money → markets → organic rate |
| **Waterfall** (firm) | 1 categorical (step) + 1 currency | 2 parts that add to a total | Composition of a **change** | A waterfall shows how two parts build the total change in AUM. The tiny net-flows step next to the huge market step *is* the insight |
| Stacked bar by **tier** | 1 categorical (3) + 2 currency | 2 | Composition, compared across categories | Total bar length = change in AUM; the two colors show the split. Horizontal bars keep the labels readable; sorted largest first |
| Stacked bar by **region** | 1 categorical (5) + 2 currency | 2 | Same as tier | Same chart type as the tier chart on purpose, so the reader learns it once |
| Text box (caveat) | text | – | – | Required caveat: Market Change is a residual, not a pure market return |
| Page 2 cards / KPI strip | single numbers + 1 text | 6 | Status of one segment | Size, clients, profitability (fee yield), performance (alpha + signal) |
| Page 2 line chart | date + currency | 1 | Trend over time | Month-end AUM over time; a line is the right choice for a continuous date axis |
| Page 2 top-10 table | text + currency + 2 ratios | 3 | Ranking + detail | Exact values are needed for names, so a table. Data bars show size, red/green font shows the sign of alpha |

**Week 11 principles applied:** bars start at zero; one accent color (navy = net new money, grey = everything else); sorted bars; insight titles that say the finding instead of naming the chart; numbers shown in $M/$B on the charts; no 3-D, no pie charts, no gridline clutter.

## 4. Interaction plan

- **Slicers:** `dim_date[year]` (dropdown, single select, **saved on 2024**) and `dim_advisor[region]` (dropdown, All).
- **Edited interactions:** none. I kept the default cross-filtering: clicking a tier bar highlights that tier's share in the region chart, and the headline and cards update to that tier too. That's visible on the page (the clicked bar stays highlighted), so it doesn't change a number silently. Clicking the bar again clears it.
- **Drill-through:** Page 2 is a drill-through page on `dim_client[client_tier]` with **Keep all filters = On**. To use it, right-click a bar in the tier chart → **Drill through → Segment Detail**. The year and region slicers carry over. Page 2 has a back button.
- **Tooltips:** default tooltips only.

## 5. Prototype with Claude (before Power BI)

### Extract

`scripts/00_make_extract.py` builds `data/growth_extract.csv` with pandas from `Data/Wildcat_Capital_Clean/`: 75 rows (5 years × 3 tiers × 5 regions). Region comes from `dim_advisor[region]` through each fact row's `advisor_id`, the same path the model uses. `data/README.md` labels each column as a **balance** (`ending_aum`, `ending_aum_ly`) or a **flow** (`net_flows`, `market_change`).

### Prototype options (Claude, from the CSV and its README)

| Option | File | Week 11 assessment |
|---|---|---|
| A. Waterfall (firm) | [`option_a_waterfall.png`](design/prototypes/option_a_waterfall.png) | Best for **"how was the change built?"** Shows start → net flows → market → end. Weak for comparing segments (one waterfall per segment is too many) |
| B. Stacked bars by tier and region | [`option_b_stacked_bars.png`](design/prototypes/option_b_stacked_bars.png) | Best for **comparing segments**: bar length is the total change, colors show the split. The small navy part is hard to read for UHNW, so data labels are needed |
| C. 100% stacked bar by tier | [`option_c_100pct_stacked.png`](design/prototypes/option_c_100pct_stacked.png) | Shows the **share** from new money clearly (Retail ≈ 52%) but hides the size: Retail's $86M looks as big as UHNW's $1.58B |
| D. Clustered columns by region | [`option_d_clustered_region.png`](design/prototypes/option_d_clustered_region.png) | Compares the two parts side by side, but you can't see the total change, and the tiny navy columns are almost invisible next to the grey ones |

**What I built:** **A for the firm** (the main answer) plus **B for tier and region** (who drove it). C's share idea went into the **dynamic tier title** instead ("New money matters most for Retail clients: 52% of their growth vs. 4% overall"), so the reader gets the share without losing the dollar sizes. D was dropped.

**What Claude got wrong in the prototypes:** *(TO DO, Kaitlyn: upload `growth_extract.csv` + `data/README.md` to Claude Desktop, ask for 3+ options, and note here anything it gets wrong. The classic trap to check for is adding `ending_aum` across years, which double-counts a balance.)* In the prototypes above, which were made in the Claude app session, the one real problem was that Option B's legend sat on top of the UHNW bar, so the market-change label was hidden. I moved the legend to the region panel. All four prototypes use only the 2024 rows, so no balance is added across years.

## 6. Claude-assisted formatting measures (added after building Page 1)

I used two kinds of formatting measures: **Field value color** measures and **dynamic insight titles / display text**. Claude drafted all of them in the Claude app, and they were pasted into the model with TMDL scripts. Below are the ones where Claude's draft had to change.

### a) Field value color: `Net Flows Color` and `Alpha Font Color`

```DAX
Net Flows Color  = IF ( [Net Flows] < 0, "#B03A2E", "#1F4E79" )            -- Page 1, Net Flows card font
Alpha Font Color = IF ( [Top 10 Client Alpha] < 0, "#B03A2E", "#1E7B34" )  -- Page 2, top-10 alpha column
```

Applied with **Format → Values → Font color → fx → Field value** (card) and **Conditional formatting → Font color → Field value** (table). The card uses the page's one accent (navy) for positive flows and dark red only as a warning. The table uses red/green, but the +/− sign is printed next to every number, so color isn't the only cue (Week 11 accessibility).

### b) Display-text measures for the Page 2 KPI strip (Claude's draft → final)

**Claude's draft**

```DAX
Card Ending Clients     = FORMAT ( [Ending Clients], "#,0" )
Card Avg AUM per Client = FORMAT ( [Avg AUM per Client] / 1e3, "$#,0" ) & "K"
```

**Final DAX**

```DAX
Card Ending Clients     = FORMAT ( [Ending Clients], "0" ) & " clients"
Card Avg AUM per Client = FORMAT ( [Avg AUM per Client] / 1e6, "$0.00" ) & "M"
```

**What I changed and why:** on the Apporto machine the draft showed **"2.325"** clients and **"$5.475K"** per client. The `,` in the format string turned into a period, so 2,325 clients looked like 2.3 clients and $5.475 million looked like $5 thousand. That's a silent, 1,000× misreading. The final version has no thousands separator, adds a unit word ("clients"), and shows average AUM in millions, which is the right scale here ($5.48M firm-wide, $0.38M for Retail, $39.54M for UHNW).

### c) Dynamic insight title for the tier chart (`Tier Title`)

**Final DAX**

```DAX
Tier Title =
VAR tbl =
    ADDCOLUMNS (
        ALLSELECTED ( dim_client[client_tier] ),
        "@share", DIVIDE ( [Net Flows], [AUM Change] )
    )
VAR topT = TOPN ( 1, tbl, [@share], DESC )
RETURN
    "New money matters most for " & MAXX ( topT, dim_client[client_tier] )
        & " clients: " & FORMAT ( MAXX ( topT, [@share] ), "0%" )
        & " of their growth vs. " & FORMAT ( DIVIDE ( [Net Flows], [AUM Change] ), "0%" )
        & " overall"
```

**Why it's built this way:** it ranks tiers by the **share** of their growth that came from new money (`Net Flows ÷ AUM Change`), not by dollars of net flows, because the chart's point is the split. `ALLSELECTED` keeps all three tiers in the comparison even when someone clicks a bar. The firm-wide share ("vs. 4% overall") gives the number a comparison.

**One fix while building:** the first TMDL script put these measures in a display folder, and the **fx → Field value** picker in Power BI on Apporto didn't list measures inside display folders. I re-created them without a display folder, and then they showed up.

The other dynamic titles follow the same idea: `Page 1 Title` (headline), `Waterfall Title`, `Region Title` and `Segment Subtitle`. Each one reads the year slicer, so the titles stay true if the year changes (for 2020, which has no prior year, the headline says to pick a year from 2021 on).
