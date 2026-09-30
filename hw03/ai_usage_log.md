# HW3 — AI Usage Log

## Prompt 1 — Specification A (Earnings Pipeline)

> Please write a Python script that builds a small database of quarterly earnings figures for five companies (Apple, Microsoft, NVIDIA, JPMorgan Chase, and Walmart) by reading their 8-K filings directly from SEC EDGAR.
>
> Every request the script makes to SEC EDGAR must include the header `User-Agent: "MIS3060 Villanova youremail@villanova.edu"` — set this once and reuse it on every single `requests.get()` call, not just the first one, since EDGAR will reject requests that don't identify a real contact.
>
> For each of the five companies (using the exact CIK numbers provided in the assignment), query the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json` and filter the results down to 8-K filings whose `items` field contains `"2.02"` (Results of Operations). From those, take the four most recent matching filings per company, so each company contributes up to one filing per fiscal quarter.
>
> For each of those filings, construct the filing's index URL, fetch it, and identify the earnings press release exhibit (the `.htm` file whose name contains something like `ex99` or `ex-99`). Download that exhibit, strip out the HTML tags with BeautifulSoup to get plain text, and from that text extract four things: the quarterly revenue, the diluted earnings per share, the net income, and a label for which reporting period the filing covers. If any one of those four values can't be found, store the literal string `"NOT_FOUND"` for that field.
>
> As each filing is processed, print its extracted row to the terminal in this exact format: `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`. If the press release exhibit for a filing can't be located, don't crash — print a warning and move on.
>
> Save all the rows to `hw03/earnings_history.csv` with columns: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`.

*(Full text also saved in `specifications.md`.)*

## Prompt 2 — Specification B (Executive Events Pipeline)

> Please write a second, separate Python script that builds a database of executive departures and appointments for the same five companies, again reading directly from SEC EDGAR.
>
> Use the same `User-Agent` header on every request this script makes.
>
> For each of the five companies, query the EDGAR submissions API and filter for 8-K filings where the `items` field contains `"5.02"` **and** the filing's `filingDate` falls within the past 12 months.
>
> For each matching filing, download the full 8-K document's text, strip the HTML, and extract: the event type (`"departure"`, `"appointment"`, or `"both"`), the person's full name, their title, and the effective date. If a single filing describes more than one event, create a separate row for each.
>
> Print each event as it's extracted in this format: `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`. If a company has zero Item 5.02 filings in the past 12 months, print `[Ticker]: No executive events in past 12 months` and continue.
>
> Save all events to `hw03/executive_events.csv` with columns: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`.

*(Full text also saved in `specifications.md`.)*

## Prompt 3 — Timeline Join

> Write a Python script that reads `hw03/earnings_history.csv` and `hw03/executive_events.csv`. Do the following:
>
> 1. For each executive event in the events table, calculate the number of days between the executive event's `filing_date` and the nearest earnings filing date for the same company in the earnings table. Call this `days_to_nearest_earnings`.
> 2. Add a column `event_timing` that categorizes each executive event as: `'before earnings'` if the event came before the nearest earnings filing, `'after earnings'` if it came after, or `'same week'` if within 7 days of an earnings filing.
> 3. Save the combined table to `hw03/corporate_events_timeline.csv` with all columns from both source tables plus `days_to_nearest_earnings` and `event_timing`.
> 4. Print a summary: for each company, list any executive events and whether they occurred before or after the nearest earnings announcement.
> 5. Print a final count: how many events occurred before vs. after an earnings announcement across all five companies.

## Which companies' extractions required iteration

Before I ran anything on real data, testing on sample text caught two bugs. Apple says "net quarterly income" instead of "net income", and the script was counting the 8-K heading "Departure of Directors or Certain Officers" as an actual event.

Once I ran it on the real EDGAR data, almost every company needed at least one fix:
- **NVDA and WMT (earnings):** I got 0 rows for both on the first run. The script was looking for "ex99" in the file name, and NVIDIA's press release is named like `q1fy27pr.htm`. It now reads the EX-99.1 "Type" column on the filing index page instead. After that, the February (Q4) filings were labeled as the next year's Q1 because of the outlook section, so I had it read the headline first.
- **WMT (earnings):** net income was 1,000 times too big because it used the wrong unit. I fixed it by using the "(Amounts in millions)" table header, and added a check that net income can't be bigger than revenue.
- **JPM (earnings):** EPS showed $1.50, which was actually the dividend. It now skips numbers near "dividend" or "book value".
- **MSFT (earnings):** net income showed as "$38.5 million" instead of billion. All values are now stored as plain numbers in millions.
- **AAPL and MSFT (period):** some filings had last year's fiscal year because the script grabbed the year-ago comparison.
- **MSFT, NVDA, WMT (executives):** a lot of fake names like "Advisory Vote", "Fiscal Year", "Covenant Not", and "Censorship Risk Audit", plus duplicates like "Di Sibio" and "Carmine Di Sibio". I fixed these with a bigger stopword list, removing partial names, and skipping shareholder vote sentences.

**Second round (after checking against the real 8-K filings):**
- **JPM (earnings):** EPS for Q4 2025 and Q2 2026 was the "excluding a significant item" number ($5.23 and $6.14) instead of the reported EPS ($4.63 and $7.70). Fixed by checking the reported "net income of $X billion, or $Y per share" first.
- **All five companies (executives):** Hoffman was called an appointment when he was leaving the board, and several people were missing (Cook, Levinson, Rohrbaugh, Puri). Titles were cut short or were the person's old job, and most effective dates were NOT_FOUND. I fixed how the script splits sentences, finds every name in a sentence, decides who is leaving vs. arriving, reads titles, and finds dates in the next sentence. The events went from 21 to 27.
- I also found that my local copy of `hw03_earnings.py` was older than the one on GitHub (it was missing the Walmart and period fixes), so I made sure the newest version is the one committed.

It is important to notice how differently each company words their press releases and filings. One pattern almost never works for all five.

## One thing the script did that I wouldn't have thought to specify

The original earnings script added the unit from the table header to numbers that didn't have one, and it wrote "(unit inferred from filing header)" next to them in the CSV. I never asked for that, but it was actually a smart idea, because press release tables only say "(In millions)" once at the top. It still needed adjusting, though. It put text in the number columns, so you couldn't do math with them, and it sometimes used the wrong unit (Microsoft's "$38.5 million" should have been billions). I changed it so every value is saved as a plain number in millions.

## How I used AI on this assignment

I used Claude (in Cowork) for more than just generating the three scripts. It also helped me debug them when the output was wrong (the NVDA/WMT, JPM, and unit problems above, and the second round of fixes after checking the real filings), look up the official Apple and Walmart sources for validation, and write the yfinance check script. Claude also drafted the write-ups in `analysis.md` and `validation.md` and parts of this log. I reviewed them and checked them against my actual output.
