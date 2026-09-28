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

Before any live data: testing on sample press-release text caught two bugs. Apple says "net quarterly income" instead of "net income", and the 8-K section heading "Departure of Directors or Certain Officers" was being read as an event.

After running against live EDGAR data:
- **NVDA and WMT (earnings):** returned 0 rows on the first run. The script looked for "ex99" in file names, but NVIDIA names its press release like `q1fy27pr.htm`. Fixed by reading the EX-99.1 "Type" column on the filing index page. After a second fix, the February (Q4) filings were mislabeled as the next fiscal year's Q1 because of outlook language. Fixed by reading the headline first.
- **WMT (earnings):** net income came out 1,000× too big because the wrong unit ("billions" from the text) was applied to table numbers. Fixed by reading the "(Amounts in millions…)" table header and adding a "net income can't exceed revenue" check.
- **JPM (earnings):** EPS came back as $1.50 for several quarters, which is JPM's dividend per share, not EPS. Fixed by skipping numbers near "dividend" or "book value". EPS now reads $5–6.
- **MSFT (earnings):** net income showed as "$38.5 million" instead of $38.5 billion. Fixed by treating small decimal numbers as billions and storing all values as plain numbers in millions.
- **AAPL and MSFT (period):** some filings were labeled with the prior fiscal year, e.g. "fourth quarter fiscal 2024" for an October 2025 filing, because the year-ago comparison was picked. Fixed by preferring the newest year mentioned.
- **MSFT, NVDA, WMT (executives):** fake "names" like "Advisory Vote", "Fiscal Year", "Covenant Not", "Against Abstain Broker" and "Shareholder Proposal", plus partial duplicates like "Di Sibio" next to "Carmine Di Sibio". Fixed with a larger stopword list and partial-name removal.

## One thing the script did that I wouldn't have thought to specify

The executive events script automatically merges a departure and an appointment into a single `event_type="both"` row when they name the *same person* in the same filing — for example, someone stepping down as CEO but staying on as Chairman gets one combined row instead of two separate ones. I hadn't explicitly asked for that merge logic in the specification (it only said "if a filing reports multiple events... creates a separate row for each event"), but it followed naturally from the `"both"` value the spec listed as a possible `event_type`. It's correct for the common "same person, changing roles" case, but it's worth double-checking against your real data: if the extraction ever produced two different-but-similar name strings for what's actually the same person (e.g. "Robert Chen" vs. "Mr. Chen"), the merge would fail to catch it and you'd end up with two separate rows instead of one — worth a manual glance at any row where a `departure` and an `appointment` for what looks like the same person didn't get merged.
