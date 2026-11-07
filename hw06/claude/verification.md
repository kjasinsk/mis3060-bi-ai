# Part D: Checking Claude's `Top 10 Client Share`

I used the **Draft → Test → Debug → Review** steps. The prompt and Claude's full answer are in `dax_session.md`. Claude's test query, plus two versions I added to test what Claude said, is saved in `hw06.pbix` as **Query 4** in DAX query view.

## Did it run as written? What did the test query return?

Yes. I added the measure without changing anything, and `INFO.VIEW.MEASURES` shows it as **Valid**. Here's what Claude's test query returned:

| Check | Power BI result |
|---|---|
| (a) Grand total | Last snapshot **Dec 1, 2024**, share **6.1589%**, Top 10 AUM **$784,005,019.49**, Ending AUM **$12,729,572,078.86**, Ending Clients **2,325** |
| (b) By year | 2020 7.0411% · 2021 6.3754% · 2022 5.5309% · 2023 6.0379% · 2024 6.1589% |
| (c) By tier, 2024 | Retail **1.8348%** · HNW **3.1397%** · UHNW **8.1264%** |
| (d) Top 10 clients | 1001, 2361, 1331, 2281, 2183, 1245, 1885, 679, 1855, 796 (from $82.39M down to $74.42M) |

The checks Claude suggested work out. $784,005,019.49 ÷ $12,729,572,078.86 = 6.1589%, and the 10 balances in (d) add up to exactly $784,005,019.49.

## Which rows of `measure_reconciliation.csv` prove it?

The `Top 10 Client Share` rows for **`All`**, **`year=2024|tier=Retail`**, **`year=2024|tier=HNW`** and **`year=2024|tier=UHNW`**. All four match pandas (the differences are around 1e-17). Pandas also finds the same top 10 client IDs and the same $784,005,019.49. I checked the by-year numbers in (b) against pandas too, even though they aren't required rows, and all five years match to 6 decimals.

## Edge cases I checked

1. **Grand total (no filter):** it ranks all 2,325 clients who are still with the firm on Dec 1, 2024, and it matches pandas.
2. **`dim_date[year]` = 2022:** the date moves to Dec 1, 2022, when all 2,500 clients were still there. The share (5.5309%) is different from every other year, so I know the year filter is actually reaching the measure.
3. **2024 tier table:** each tier only ranks its own clients. UHNW (244 big clients) is the most concentrated at 8.13%, and Retail (1,394 small clients) is the least at 1.83%. None of them go over 100%.
4. **Ties:** `TOPN` can return more than 10 rows if there's a tie. There's no tie at 10th place here ($74,424,366.68 vs $77,214,969.90 for 9th). I made pandas use `nlargest(10, keep="all")` so it would handle a tie the same way if there ever was one.

## What I changed and why

**Nothing.** The measure matched every required slice on the first try, and the two claims I tested below held up. The only change was on the pandas side, where I made the top 10 use `keep="all"` so a tie would work the same way as `TOPN`.

## A claim I confirmed, and one I partly refuted

**Confirmed:** Claude said that if I used `ALL ( dim_client )` instead of `VALUES ( dim_client[client_id] )`, every row would rank the firm-wide top 10, so small tiers could go over 100%. I ran that version in Query 4 and got **146.97% for Retail in 2024** and 30.76% for HNW, compared to the correct 1.83% and 3.14%. The firm-wide top 10 ($784.0M) have more money than the whole Retail tier ($533.5M), so the share goes over 100%, just like Claude said.

**True in theory, but it doesn't change anything here:** Claude said that without the `LastSnap` filter around `SUMX`, clients who left could get ranked at their old balances and make the share too high. I ran that version too, and it gave **exactly the same numbers** for the grand total, 2022, 2023 and all three 2024 tiers. Pandas shows why. The largest client who left had a last balance of $43.4M, which is way below the #10 client's $74.4M, so a departed client could never make the top 10. I still think the filter is the right way to do it, since a big client leaving would break the version without it. But in this data, the problem Claude warned about doesn't actually change any number.
