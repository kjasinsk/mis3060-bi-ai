# HW3 Specifications

## Specification A — Earnings Pipeline (`hw03_earnings.py`)

Please write a Python script that builds a small database of quarterly earnings figures for five companies (Apple, Microsoft, NVIDIA, JPMorgan Chase, and Walmart) by reading their 8-K filings directly from SEC EDGAR.

Every request the script makes to SEC EDGAR must include the header `User-Agent: "MIS3060 Villanova youremail@villanova.edu"` — set this once and reuse it on every single `requests.get()` call, not just the first one, since EDGAR will reject requests that don't identify a real contact.

For each of the five companies (using the exact CIK numbers provided in the assignment), query the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json` and filter the results down to 8-K filings whose `items` field contains `"2.02"` (Results of Operations — this is the item code for earnings announcements). From those, take the four most recent matching filings per company, so each company contributes up to one filing per fiscal quarter.

For each of those filings, construct the filing's index URL, fetch it, and identify the earnings press release exhibit (the `.htm` file whose name contains something like `ex99` or `ex-99`). Download that exhibit, strip out the HTML tags with BeautifulSoup to get plain text, and from that text extract four things: the quarterly revenue (as a dollar figure, in millions or billions), the diluted earnings per share, the net income, and a label for which reporting period the filing covers (for example, "fourth quarter fiscal 2024"). If any one of those four values can't be found in the text, store the literal string `"NOT_FOUND"` for that field instead of leaving it blank or storing `None` — a blank cell and a confirmed "we looked and it wasn't there" are different things and should look different in the data.

As each filing is processed, print its extracted row to the terminal in this exact format: `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`. If the press release exhibit for a filing can't be located at all, don't let the script crash — print a warning naming the company and filing, and move on to the next one.

When everything is processed, save all the rows to `hw03/earnings_history.csv` with these exact columns, in this order: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`.

## Specification B — Executive Events Pipeline (`hw03_executives.py`)

Please write a second, separate Python script that builds a database of executive departures and appointments for the same five companies, again reading directly from SEC EDGAR.

Use the same `User-Agent` header (`"MIS3060 Villanova youremail@villanova.edu"`) on every request this script makes, for the same reason as above.

For each of the five companies, query the EDGAR submissions API and filter for 8-K filings where the `items` field contains `"5.02"` (Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers) **and** the filing's `filingDate` falls within the past 12 months. Only keep filings that satisfy both conditions.

For each matching filing, download the full 8-K document's text (not just an exhibit — Item 5.02 events are usually described in the body of the 8-K itself), strip the HTML, and extract: the event type (`"departure"`, `"appointment"`, or `"both"` if the filing describes one of each), the person's full name, their title or role, and the effective date of the change. If a single filing describes more than one event — for example, one executive departing and a different one being appointed — create a separate output row for each event rather than combining them into one row.

As each event is extracted, print it to the terminal in this exact format: `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`. If a company has zero Item 5.02 filings in the past 12 months, don't treat that as an error or skip it silently — print `[Ticker]: No executive events in past 12 months` and continue; the absence of executive turnover is itself a meaningful, valid result.

Save all extracted events to `hw03/executive_events.csv` with these exact columns, in this order: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`.
