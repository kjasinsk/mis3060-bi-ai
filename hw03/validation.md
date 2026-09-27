# HW3 Validation

**Important — read before filling this in:** the tables below are ready-made skeletons, but every blank needs a real number from your own run of the three scripts. I can't reach SEC EDGAR or Yahoo Finance from my own environment right now (both are blocked by network policy here), so I can't generate real `earnings_history.csv` / `executive_events.csv` data myself. Run `hw03_earnings.py`, `hw03_executives.py`, and `hw03_timeline.py` yourself in VS Code (real internet access there), then come back and fill these in — or paste me the resulting CSVs and I'll fill the tables in for you.

## 5A — Known-Answer Check: Earnings

Look up the officially reported quarterly revenue for **one** company for **one** specific quarter, from that company's investor relations page or a financial news source.

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| [Company] [Quarter] Revenue | | | |
| [Company] [Quarter] EPS Diluted | | | |

If a value doesn't match or shows `"NOT_FOUND"`: paste the raw press release text excerpt into a new Claude Cowork session and ask for an improved regex pattern. Document the before/after pattern and whether the fix resolved the discrepancy.

## 5B — Known-Answer Check: Executive Events

Pick **one** executive event from your `executive_events.csv`. Verify it against a public news source (Google News, LinkedIn, or the company's own press releases).

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | | |
| Event type (departure/appointment) | | |
| Effective date | | |

## 5C — Cross-Validation: Earnings via Yahoo Finance

For the same company and quarter checked in 5A, use `yfinance` to retrieve quarterly revenue and net income as a second, independent source:

> "Write Python using yfinance to get the most recent quarterly revenue and net income for [ticker]."

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | | | |
| Net Income | | | |

If the two sources disagree, explain the most likely reason (period mismatch, metric definition difference, or extraction error).

## 5D — Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies × 4 quarters) | | |
| `executive_events.csv` row count | At least 0 (document actual) | | |
| `corporate_events_timeline.csv` created | Yes | | |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | | |

For the last row: `"revenue_reported"`, `"eps_diluted"`, and `"net_income"` all showing `"NOT_FOUND"` on the same row usually means the press release exhibit was found but its wording didn't match any of the extraction patterns (rather than the exhibit being empty or missing) — worth opening that one filing's raw text to see what phrasing it actually used, and adjusting the keyword list in `find_dollar_amount_near()` if you want the extraction to catch it.
