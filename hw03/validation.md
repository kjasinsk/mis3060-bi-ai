# HW3 Validation

## 5A — Known-Answer Check: Earnings

Company and quarter checked: **Apple (AAPL), Q3 fiscal 2026 (quarter ended June 27, 2026)**, 8-K filed 2026-07-30.
Official source: [Apple Newsroom, "Apple reports third quarter results" (July 30, 2026)](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q3 FY2026 Revenue | $109.4 billion ($109,417 million in the release's table) | $109,400 million | Yes (CSV took the rounded "$109.4 billion" from the release text) |
| Apple Q3 FY2026 EPS Diluted | $2.02 | $2.02 | Yes |

Apple matched so I didn't need a regex fix for it. But when I looked through the rest of the CSV I found two other problems that I had to fix:
- **JPMorgan EPS (fix 1):** my CSV said $1.50 for two quarters, which seemed way too low. It turned out that was JPM's dividend per share, not their EPS. Before, the pattern `\$\s?\d+\.\d{2}\s*per\s+share` just grabbed the first "$X.XX per share" it found. After the fix it skips numbers near the words "dividend" or "book value", and it checks the headline "($X.XX per share)" first.
- **JPMorgan EPS (fix 2):** when I checked JPM against its actual 8-K, two quarters were still wrong. JPM reports two EPS numbers in its headline, the reported one and one "excluding a significant item". My CSV had $5.23 for Q4 2025 and $6.14 for Q2 2026, which were the "excluding" numbers. The real reported EPS is **$4.63** and **$7.70**. I added a new first pattern, `net income (?:of|was) \$X billion, or \$Y per share` / `($Y per share)`, and made the script skip any EPS within 80 characters of "significant item". The CSV now has $4.63 and $7.70.
- **Units:** Microsoft's net income showed as "$38.5 million" when it was actually $38.5 billion. The script was adding the "(In millions)" from the table header to every number, even ones already written in billions. Now small decimal numbers like 38.5 get treated as billions, and everything is stored as a plain number in millions.

## 5B — Known-Answer Check: Executive Events

Event checked: **Walmart, filed 2026-01-16, departure, Kathryn McLay, "Executive Vice President, President and Chief Executive Officer, Walmart International", effective January 31, 2026**.
Source: [Walmart corporate news, "Walmart Announces Leadership Changes" (Jan 16, 2026)](https://corporate.walmart.com/news/2026/01/16/walmart-announces-leadership-changes)

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Yes (after fix) | The name is right. At first my script only picked up "Executive Vice President". After the fix the CSV has her full title, "Executive Vice President, President and Chief Executive Officer, Walmart International", which matches the 8-K. |
| Event type (departure/appointment) | Yes | Walmart said Chris Nicholas "will succeed Kath McLay as President and CEO of Walmart International", so she is leaving. |
| Effective date | Yes (after fix) | At first my CSV said NOT_FOUND because the date was in a different sentence than her name. The script now also checks the next sentence, and the CSV says January 31, 2026. The 8-K says she stays in her role until "the close of business January 31, 2026", and the press release says her successor starts February 1, 2026, so this matches. |

## 5C — Cross-Validation: Earnings via Yahoo Finance

Prompt used: *"Write Python using yfinance to get the most recent quarterly revenue and net income for AAPL."* Script: `hw03_yfinance_check.py`

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | $109,400 million | $109,417 million | Yes (the $17 million gap is rounding: the 8-K text says "$109.4 billion") |
| Net Income | $29,789 million | $29,789 million | Yes (exact) |
| Diluted EPS (extra check) | $2.02 | $2.02 | Yes (exact) |

At first I thought the dates didn't match because yfinance says the quarter ended **2026-06-30** and Apple says **June 27, 2026**. But it's the same quarter: Apple's quarters end on the last Saturday of the month, and yfinance just rounds it to the end of the month. Net income and EPS match exactly, and revenue is only off because of rounding, so I'm confident the Apple numbers my script pulled are correct.

## 5D — Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies × 4 quarters) | 20 (4 per company) | Pass |
| `executive_events.csv` row count | At least 0 (document actual) | 27 events (AAPL 6, MSFT 2, NVDA 6, JPM 4, WMT 9) | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes (27 rows, every event matched to an earnings date) | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 | Pass |

**How I got to 20 rows:** my first run only gave me 12 rows because every NVIDIA and Walmart filing got skipped. The script was looking for "ex99" in the file name to find the press release, but NVIDIA names theirs like `q1fy27pr.htm`, so it never found them. The fixed version reads the "Type" column (EX-99.1) on each filing's index page instead, and that brought in NVDA and WMT.

**Other fixes after I looked at the 20 rows:**
- Walmart's net income came out 1,000 times too big (like $6,366,000M). The script picked up "in billions" from the text instead of the "(Amounts in millions)" table header. I fixed that and added a check so net income can never be bigger than revenue.
- The February NVDA and WMT filings were labeled "first quarter fiscal 2027" when they should be the fourth quarter of fiscal 2026. Those releases also talk about next year's outlook, which confused it. Now it reads the headline first.

**Second round of fixes to `executive_events.csv`:** I checked my events against the actual 8-K text on EDGAR and found several real errors, which I fixed:
- **Wrong event type:** Reid Hoffman (Microsoft) was listed as an "appointment" because the filing mentions "re-election", but he decided *not to stand* for re-election, so it is a departure.
- **Missing people:** Tim Cook (CEO to Executive Chair, now my "both" example), Art Levinson (Lead Independent Director), Troy Rohrbaugh (JPM's second Co-President) and Ajay K. Puri (NVIDIA). Puri's row had no name because the script split the sentence at the "K." in his name. The script also only kept the first name in each sentence.
- **Wrong titles:** John Ternus had his old title instead of "Chief Executive Officer", and board members said NOT_FOUND instead of "Director".
- **Wrong "both" rows:** Kate Adams and Jennifer Newstead (Apple) were both tagged "both" because they were in the same sentence. Now Adams is a departure and Newstead is an appointment (General Counsel, March 1, 2026).
- **Fake names:** "Cover Page Interactive" and "Inline XBRL" came from the list of exhibits at the end of a Walmart filing. They are now skipped.
- **Old fake names:** the Microsoft shareholder-vote names ("Against Abstain Broker", "Censorship Risk Audit") are still removed.

**Problems I still see:**
- Doug McMillon (Walmart, 2025-11-14) is tagged "both" with the title "Director". He is really retiring as President and CEO, but he stays on the board until June 2026, which is probably why the script also saw an appointment.
- Kate Adams and Scott Gawel have no title, and 6 events have no effective date. For most of these, the filing gives no calendar date (for example "upon the commencement of his employment" or "late 2026"), so NOT_FOUND is correct.

These show up as NOT_FOUND instead of crashing the script, which is what the assignment asks for.
