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

While building `hw03_earnings.py` and `hw03_executives.py`, I could not test against live SEC EDGAR data directly. When I tried ot go onto `data.sec.gov` and `www.sec.gov`, they were blocked by network policy in the environment I was working in. So I validated the extraction logic against realistic synthetic press-release and 8-K text instead, and that testing surfaced (and fixed) two real bugs before the scripts ever touched real data:

- **Earnings extraction:** the first version only looked for the phrase "net income" near a dollar figure, but Apple's actual press-release wording is "net quarterly income" — a real filing would have silently returned `NOT_FOUND` for net income. It is important to notice the differences of company language in the ways that they disclose their statistics. 
- **Executive events extraction:** the first version mis-tagged the Item 5.02 section heading itself ("Departure of Directors or Certain Officers.") as a real event, matched stray words like "On" + a month name as a false "person name," and missed past-tense phrasing like "stepped down" because the keyword list only had "step down"/"stepping down". Fixed by filtering out heading text, adding month names and connector words to the name-matching stopword list, and switching the departure/appointment keyword matching to tense-flexible regex patterns.

**Once you actually run these scripts with live internet access, update this section** with which of the five real companies (AAPL, MSFT, NVDA, JPM, WMT) needed a follow-up regex fix, per the assignment's Part 2/3 instructions (paste the 3,000-character raw text into a new session and ask for a better pattern).

## One thing the script did that I wouldn't have thought to specify

The executive events script automatically merges a departure and an appointment into a single `event_type="both"` row when they name the *same person* in the same filing — for example, someone stepping down as CEO but staying on as Chairman gets one combined row instead of two separate ones. I hadn't explicitly asked for that merge logic in the specification (it only said "if a filing reports multiple events... creates a separate row for each event"), but it followed naturally from the `"both"` value the spec listed as a possible `event_type`. It's correct for the common "same person, changing roles" case, but it's worth double-checking against your real data: if the extraction ever produced two different-but-similar name strings for what's actually the same person (e.g. "Robert Chen" vs. "Mr. Chen"), the merge would fail to catch it and you'd end up with two separate rows instead of one — worth a manual glance at any row where a `departure` and an `appointment` for what looks like the same person didn't get merged.
