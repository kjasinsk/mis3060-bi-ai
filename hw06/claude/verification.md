# Part D: Verifying Claude's `Top 10 Client Share`

**Draft → Test → Debug → Review.** Prompt and full response are in `dax_session.md`. Claude's test query, plus two variants I added to test its claims, is saved in `hw06.pbix` as **Query 4** in DAX query view.

## Did it run as written? What did the test query return?

Yes. I added the measure with no changes, and `INFO.VIEW.MEASURES` shows it as **Valid**. Claude's test query returned:

| Check | Power BI result |
|---|---|
| (a) Grand total | Last snapshot **2024-12-01**, share **6.1589%**, Top 10 AUM **$784,005,019.49**, Ending AUM **$12,729,572,078.86**, Ending Clients **2,325** |
| (b) By year | 2020 7.0411% · 2021 6.3754% · 2022 5.5309% · 2023 6.0379% · 2024 6.1589% |
| (c) By tier, 2024 | Retail **1.8348%** · HNW **3.1397%** · UHNW **8.1264%** |
| (d) Top 10 clients | 1001, 2361, 1331, 2281, 2183, 1245, 1885, 679, 1855, 796 (from $82.39M down to $74.42M) |

Claude's own consistency checks pass: $784,005,019.49 ÷ $12,729,572,078.86 = 6.1589%, and the 10 balances in (d) add up to exactly $784,005,019.49.

## Which rows of `measure_reconciliation.csv` prove it?

`Top 10 Client Share` at slices **`All`**, **`year=2024|tier=Retail`**, **`year=2024|tier=HNW`** and **`year=2024|tier=UHNW`**. All four match pandas to about 1e-17. Pandas finds the same top 10 client IDs and the same $784,005,019.49. I also checked the by-year numbers in (b) against pandas (not a required row): all five years match to 6 decimals.

## Edge cases I checked

1. **Grand total (no filter):** ranks all 2,325 clients still with the firm at 2024-12-01. Matches pandas.
2. **`dim_date[year]` = 2022:** the date moves to 2022-12-01, when all 2,500 clients were still there. The share (5.5309%) is different from every other year, so the year filter is really reaching the measure and isn't being removed.
3. **2024 tier table:** each tier only ranks its own clients. UHNW (244 big clients) is the most concentrated at 8.13%, and Retail (1,394 small clients) is the least at 1.83%. All are under 100%.
4. **Ties:** `TOPN` can return more than 10 rows on a tie. There's no tie at 10th place ($74,424,366.68 vs $77,214,969.90 for 9th). The pandas side uses `nlargest(10, keep="all")` so it would behave the same way if there were one.

## What I changed and why

**Nothing.** The measure matched every required slice the first time, and the two claims I tested below hold up. The only change was on the pandas side: I made the top-10 use `keep="all"` so a tie would be handled the same way as DAX `TOPN`.

## A claim I confirmed, and one I partly refuted

**Confirmed:** Claude said that if `ALL ( dim_client )` were used instead of `VALUES ( dim_client[client_id] )`, every row would rank the firm-wide top 10 and small tiers could go over 100%. I ran that version in Query 4: **Retail 2024 = 146.97%** and HNW = 30.76%, against the correct 1.83% and 3.14%. The firm-wide top 10 ($784.0M) hold more money than the whole Retail tier ($533.5M), so the share goes over 100%, just as Claude said.

**True in theory, but no effect on this data:** Claude said that without the `LastSnap` pin around `SUMX`, clients who left could be ranked at their old balances and overstate the share. I ran that version too, and it gives **exactly the same numbers** for the grand total, 2022, 2023 and all three 2024 tiers. Pandas explains why: the largest client who left had a last balance of $43.4M, well below the #10 client's $74.4M, so no departed client could ever get into the top 10. The pin is still the right design, because a big client leaving would break the unpinned version. But on this dataset the bug Claude warned about doesn't actually change any number.
