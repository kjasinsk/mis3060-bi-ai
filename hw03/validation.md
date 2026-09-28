# HW3 Validation

## 5A — Known-Answer Check: Earnings

Company and quarter checked: **Apple (AAPL), Q3 fiscal 2026 (quarter ended June 27, 2026)**, 8-K filed 2026-07-30.
Official source: [Apple Newsroom, "Apple reports third quarter results" (July 30, 2026)](https://www.apple.com/newsroom/2026/07/apple-reports-third-quarter-results/)

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q3 FY2026 Revenue | $109.4 billion ($109,417 million in the release's table) | $109,400 million | Yes (CSV took the rounded "$109.4 billion" from the release text) |
| Apple Q3 FY2026 EPS Diluted | $2.02 | $2.02 | Yes |

No regex fix was needed for Apple. Two other problems showed up while reviewing the full CSV, and I fixed them in the updated `hw03_earnings.py`:
- **JPMorgan EPS:** the CSV showed $1.50 for two quarters. That is JPM's quarterly **dividend** per share, not EPS. Before: the pattern `\$\s?\d+\.\d{2}\s*per\s+share` took the first "$X.XX per share" it saw. After: matches with "dividend" or "book value" nearby are skipped, and the headline format "($X.XX per share)" is checked first.
- **Units:** Microsoft's net income showed as "$38.5 million" when it was really $38.5 billion. Before: the table's "(In millions)" header got attached to every number. After: a small decimal number like 38.5 is treated as billions, and every value is stored as a plain number in millions.

## 5B — Known-Answer Check: Executive Events

Event checked: **Walmart, filed 2026-01-16, departure, Kathryn McLay, "Executive Vice President"**.
Source: [Walmart corporate news, "Walmart Announces Leadership Changes" (Jan 16, 2026)](https://corporate.walmart.com/news/2026/01/16/walmart-announces-leadership-changes)

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Partly | Name is correct. Her full title was Executive Vice President and President & CEO, Walmart International. The script only captured "Executive Vice President". |
| Event type (departure/appointment) | Yes | Walmart said Chris Nicholas "will succeed Kath McLay as President and CEO of Walmart International", so she is leaving that role. |
| Effective date | No (script missed it) | CSV says NOT_FOUND. The press release says the changes are "effective February 1, 2026". The date is in a separate sentence from her name, and the script only looks for a date in the same sentence. |

## 5C — Cross-Validation: Earnings via Yahoo Finance

Prompt used: *"Write Python using yfinance to get the most recent quarterly revenue and net income for AAPL."* Script: `hw03_yfinance_check.py`

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | $109,400 million | $109,417 million | Yes (the $17 million gap is rounding: the 8-K text says "$109.4 billion") |
| Net Income | $29,789 million | $29,789 million | Yes (exact) |
| Diluted EPS (extra check) | $2.02 | $2.02 | Yes (exact) |

yfinance labels this quarter **2026-06-30**, but Apple's quarter actually ended **June 27, 2026**. It is the same quarter: yfinance rounds each fiscal quarter to the nearest calendar month-end, while Apple's fiscal quarters end on the last Saturday of the month. This is a labeling difference, not a period mismatch. Net income and EPS match exactly, and revenue matches after rounding, so the text extraction for Apple is confirmed by two independent sources (Apple's newsroom and Yahoo Finance).

## 5D — Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies × 4 quarters) | 20 (4 per company) | Pass |
| `executive_events.csv` row count | At least 0 (document actual) | 21 events (AAPL 2, MSFT 3, NVDA 7, JPM 2, WMT 7) | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes (21 rows, every event matched to an earnings date) | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 | Pass |

**How the row count got to 20:** the first run produced only 12 rows because every NVIDIA and Walmart filing was skipped. The first version of the script found the press release by looking for "ex99" in the file name, and NVIDIA names its release like `q1fy27pr.htm`. The fixed script reads the "Type" column (EX-99.1) on each filing's index page, which brought in NVDA and WMT.

**Fixes made after reviewing the 20-row output:**
- Walmart's net income came out 1,000× too big, because the unit was read from an "in billions" phrase in the text instead of the table header "(Amounts in millions…)". I fixed the header detection and added a sanity check that net income can't be bigger than revenue.
- The February NVDA and WMT filings were labeled "first quarter fiscal 2027", because those releases also discuss next year's outlook. The script now reads the headline first ("Fourth Quarter and Fiscal 2026", "Q4 FY26").

**Known data-quality issues in `executive_events.csv`:**
- Fake names from shareholder-vote filings ("Against Abstain Broker", "Shareholder Proposal", "Censorship Risk Audit") came from annual-meeting vote results. They were removed by skipping any sentence about shareholder proposals or vote counts.
- One NVDA row (2026-03-06) has a title but no name.
- Most effective dates show NOT_FOUND, because the date usually sits in a different sentence from the name.

These are logged as NOT_FOUND instead of crashing, as the assignment asks.
