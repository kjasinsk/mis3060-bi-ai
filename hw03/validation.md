# HW3 Validation

## 5A — Known-Answer Check: Earnings

Company and quarter checked: **Apple (AAPL), Q3 fiscal 2026 (quarter ended June 27, 2026)**, 8-K filed 2026-07-30.
Official source: [Apple Newsroom, "Apple reports third quarter results" (July 30, 2026)](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q3 FY2026 Revenue | $109.4 billion ($109,417 million in the release's table) | $109,400 million | Yes (CSV took the rounded "$109.4 billion" from the release text) |
| Apple Q3 FY2026 EPS Diluted | $2.02 | $2.02 | Yes |

Apple matched so I didn't need a regex fix for it. But when I looked through the rest of the CSV I found two other problems that I had to fix:
- **JPMorgan EPS:** my CSV said $1.50 for two quarters, which seemed way too low. It turned out that was JPM's dividend per share, not their EPS. Before, the pattern `\$\s?\d+\.\d{2}\s*per\s+share` just grabbed the first "$X.XX per share" it found. After the fix it skips numbers near the words "dividend" or "book value", and it checks the headline "($X.XX per share)" first. JPM's EPS now shows around $5-6, which makes more sense.
- **Units:** Microsoft's net income showed as "$38.5 million" when it was actually $38.5 billion. The script was adding the "(In millions)" from the table header to every number, even ones already written in billions. Now small decimal numbers like 38.5 get treated as billions, and everything is stored as a plain number in millions.

## 5B — Known-Answer Check: Executive Events

Event checked: **Walmart, filed 2026-01-16, departure, Kathryn McLay, "Executive Vice President"**.
Source: [Walmart corporate news, "Walmart Announces Leadership Changes" (Jan 16, 2026)](https://corporate.walmart.com/news/2026/01/16/walmart-announces-leadership-changes)

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Partly | The name is right. Her full title was EVP and President & CEO of Walmart International, but my script only picked up "Executive Vice President". |
| Event type (departure/appointment) | Yes | Walmart said Chris Nicholas "will succeed Kath McLay as President and CEO of Walmart International", so she is leaving. |
| Effective date | No (script missed it) | My CSV says NOT_FOUND, but the press release says the changes are "effective February 1, 2026". The script only looks for a date in the same sentence as the name, and here the date was in a different sentence. |

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
| `executive_events.csv` row count | At least 0 (document actual) | 21 events (AAPL 2, MSFT 3, NVDA 7, JPM 2, WMT 7) | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes (21 rows, every event matched to an earnings date) | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 | Pass |

**How I got to 20 rows:** my first run only gave me 12 rows because every NVIDIA and Walmart filing got skipped. The script was looking for "ex99" in the file name to find the press release, but NVIDIA names theirs like `q1fy27pr.htm`, so it never found them. The fixed version reads the "Type" column (EX-99.1) on each filing's index page instead, and that brought in NVDA and WMT.

**Other fixes after I looked at the 20 rows:**
- Walmart's net income came out 1,000 times too big (like $6,366,000M). The script picked up "in billions" from the text instead of the "(Amounts in millions)" table header. I fixed that and added a check so net income can never be bigger than revenue.
- The February NVDA and WMT filings were labeled "first quarter fiscal 2027" when they should be the fourth quarter of fiscal 2026. Those releases also talk about next year's outlook, which confused it. Now it reads the headline first.

**Problems I still see in `executive_events.csv`:**
- Some "names" weren't people at all ("Against Abstain Broker", "Shareholder Proposal", "Censorship Risk Audit"). These came from Microsoft's annual meeting vote results. I removed them by having the script skip sentences about shareholder proposals and vote counts.
- One NVDA row (2026-03-06) has a title but no name.
- Most effective dates are NOT_FOUND because the date is usually in a different sentence than the name.

These show up as NOT_FOUND instead of crashing the script, which is what the assignment asks for.
