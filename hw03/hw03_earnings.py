"""
HW3 — Earnings Pipeline (Item 2.02)
======================================

For each of five companies: finds the 4 most recent 8-K filings that
contain Item 2.02 (Results of Operations), downloads the earnings press
release exhibit (EX-99.1), strips it to plain text, and extracts
revenue, diluted EPS, net income, and the reporting period.
Saves everything to hw03/earnings_history.csv.

Output units:
  revenue_reported, net_income  -> plain numbers in MILLIONS of USD
                                   (e.g. 109417.0 = $109.4 billion)
  eps_diluted                   -> plain number in USD per share
  Anything that can't be found  -> the string "NOT_FOUND"

Run from anywhere:  python hw03/hw03_earnings.py
Optional:           python hw03/hw03_earnings.py --debug
                    (saves the first 3,000 characters of each press
                    release to hw03/debug_text/ so you can inspect
                    filings that come back NOT_FOUND)
"""

import csv
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# --- 1. Settings -----------------------------------------------------------
# SEC requires a real contact in the User-Agent. Put your Villanova email here.
USER_AGENT = "MIS3060 Villanova kjasinsk@villanova.edu"
HEADERS = {"User-Agent": USER_AGENT}

FILINGS_PER_COMPANY = 4      # rows we want per company
CANDIDATES_TO_TRY = 8        # look at extra filings in case one gets skipped
PAUSE_SECONDS = 0.2          # SEC allows ~10 requests/second; stay well under

# Save outputs next to this script, no matter which folder you run it from.
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "earnings_history.csv"
DEBUG_DIR = BASE_DIR / "debug_text"
DEBUG = "--debug" in sys.argv

COMPANIES = [
    {"name": "Apple Inc.", "ticker": "AAPL", "cik": "0000320193"},
    {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"name": "NVIDIA Corporation", "ticker": "NVDA", "cik": "0001045810"},
    {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "cik": "0000019617"},
    {"name": "Walmart Inc.", "ticker": "WMT", "cik": "0000104169"},
]

NOT_FOUND = "NOT_FOUND"


def get(url):
    """Every request goes through here, so every request has the User-Agent."""
    time.sleep(PAUSE_SECONDS)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response


# --- 2. Find recent 8-Ks with Item 2.02 --------------------------------------
def get_item_202_filings(cik, limit):
    data = get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    recent = data["filings"]["recent"]
    results = []
    for form, items, date, accession in zip(
        recent["form"], recent["items"], recent["filingDate"], recent["accessionNumber"]
    ):
        if form == "8-K" and "2.02" in items:
            results.append({"filing_date": date, "accession": accession})
            if len(results) >= limit:
                break
    return results


# --- 3. Find the press release exhibit ---------------------------------------
def find_press_release_url(cik, accession):
    """
    WHY THIS CHANGED: the old version read index.json, whose "type" field is
    just an icon name (not "EX-99.1"), so it fell back to guessing from the
    filename. NVIDIA's press release is named like "q1fy27pr.htm" (no "ex99"
    in it), so it was never found. The filing's -index.htm page has a real
    "Type" column (EX-99.1), so we read that instead.
    """
    cik_short = str(int(cik))
    acc_nodash = accession.replace("-", "")
    folder = f"https://www.sec.gov/Archives/edgar/data/{cik_short}/{acc_nodash}"

    # Preferred: the Type column on the filing index page.
    try:
        soup = BeautifulSoup(get(f"{folder}/{accession}-index.htm").text, "html.parser")
        exhibits = []
        for row in soup.select("table.tableFile tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            link = cells[2].find("a")
            doc_type = cells[3].get_text(strip=True).upper()
            if not link:
                continue
            filename = link.get("href", "").split("/")[-1]
            if doc_type.startswith("EX-99") and filename.lower().endswith((".htm", ".html")):
                exhibits.append((doc_type, filename))
        if exhibits:
            exhibits.sort(key=lambda e: (e[0] != "EX-99.1", e[0]))  # EX-99.1 first
            return f"{folder}/{exhibits[0][1]}"
    except Exception as error:
        print(f"    (index page problem: {error}; trying filename guess)")

    # Fallback: guess from filenames in index.json.
    try:
        items = get(f"{folder}/index.json").json()["directory"]["item"]
        hints = ("ex99", "ex-99", "ex_99", "pr.htm", "press", "earn", "release")
        for item in items:
            name = item["name"].lower()
            if name.endswith((".htm", ".html")) and any(h in name for h in hints):
                return f"{folder}/{item['name']}"
    except Exception:
        pass
    return None


def download_plain_text(url):
    soup = BeautifulSoup(get(url).text, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()


# --- 4. Number helpers ---------------------------------------------------------
def table_unit(text):
    """Financial tables say '(In millions, except per share...)' once at the top."""
    # Prefer the table header, e.g. "(Amounts in millions, except per share data)".
    # WHY: Walmart's release says "in billions" in its prose before the table,
    # which made table numbers 1,000x too big.
    m = re.search(r"\((?:[a-z$ ]{0,20})?in\s+(millions|billions|thousands)\b", text, re.IGNORECASE)
    if not m:
        m = re.search(r"in\s+(millions|billions|thousands)\b", text, re.IGNORECASE)
    return m.group(1).lower().rstrip("s") if m else "million"


def to_millions(number_text, unit_word, fallback_unit):
    """
    Turn '$38.5 billion' or table value '29,789' into millions (38500.0 / 29789.0).
    WHY: the old version tacked the table's unit onto numbers that were
    really written in billions (MSFT '$38.5 million').
    """
    value = float(number_text.replace(",", ""))
    unit = (unit_word or "").lower()
    if not unit:
        # A small number with a decimal (38.5) is almost certainly billions.
        unit = "billion" if ("." in number_text and value < 1000) else fallback_unit
    if unit == "billion":
        value *= 1000
    elif unit == "thousand":
        value /= 1000
    return round(value, 1)


NUMBER = r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
UNIT = r"\s*(billion|million)"

# Words that mean "this is a piece of the business, not the total".
SEGMENT_WORDS = (
    "data center", "gaming", "automotive", "professional visualization", "segment",
    "cloud", "processes", "computing", "services", "products", "iphone", "mac",
    "ipad", "wearables", "advertising", "managed", "sam's club", "international",
    "walmart u.s", "ecommerce", "e-commerce", "membership", "net interest",
    "noninterest", "non-gaap", "adjusted", "guidance", "outlook", "expected",
)


def looks_like_segment(text, start, lookback=40):
    before = text[max(0, start - lookback):start].lower()
    return any(word in before for word in SEGMENT_WORDS)


def table_value_after(text, keywords, unit, window=40):
    """Table fallback: 'Total net sales $ 94,036' -> number right after the label."""
    lower = text.lower()
    for keyword in keywords:
        for m in re.finditer(re.escape(keyword), lower):
            if looks_like_segment(text, m.start(), 25):
                continue
            after = text[m.end():m.end() + window]
            n = re.search(r"\$?\s?(\d{1,3}(?:,\d{3})+(?:\.\d+)?)", after)
            if n:
                return to_millions(n.group(1), None, unit)
    return None


# --- 5. Field extractors ----------------------------------------------------
def extract_revenue(text, unit):
    prose = re.compile(
        r"(?:revenues?|net sales)\s+(?:for the [^$]{0,80}?)?"
        r"(?:of|was|were|totaled|reached|(?:increased|grew|rose|decreased)[^$]{0,40}?to)\s+"
        r"(?:a record\s+|record\s+)?" + NUMBER + UNIT,
        re.IGNORECASE,
    )
    for m in prose.finditer(text):
        if not looks_like_segment(text, m.start()):
            return to_millions(m.group(1), m.group(2), unit)
    return table_value_after(
        text, ["total net revenue", "total revenue", "total net sales", "net revenue", "revenue"], unit
    )


def extract_net_income(text, unit):
    prose = re.compile(
        r"net (?:quarterly )?(?:income|earnings)(?: attributable to [A-Za-z .,&]{0,40}?)?"
        r"\s+(?:of|was|were)\s+" + NUMBER + UNIT,
        re.IGNORECASE,
    )
    for m in prose.finditer(text):
        if not looks_like_segment(text, m.start(), 20):
            return to_millions(m.group(1), m.group(2), unit)
    return table_value_after(
        text, ["net income attributable to", "net income", "net earnings", "consolidated net income"], unit
    )


def extract_eps(text):
    """
    WHY THIS CHANGED: JPMorgan's release mentions its $1.50 dividend per share,
    which the old version grabbed as EPS. Now we skip anything near the words
    dividend / book value / adjusted / non-GAAP / "significant item", and we
    look for the reported "net income of $X billion, or $Y per share" first.
    """
    patterns = [
        # Reported (GAAP) headline: "net income of $13.0 billion, or $4.63 per share"
        # or "NET INCOME OF $13.0 BILLION ($4.63 PER SHARE)". Checked first because
        # JPMorgan also reports a second, "excluding a significant item" EPS.
        r"net income (?:of|was)\s+\$\s?[\d.,]+\s*(?:billion|million)\s*(?:,\s*or\s+|\(\s*)\$\s?(\d+\.\d{2})\s+per\s+(?:diluted\s+)?share",
        r"diluted (?:net )?(?:earnings|income) per (?:common )?share[^$]{0,60}?\$\s?(\d+\.\d{2})",
        r"earnings per diluted share[^$]{0,60}?\$\s?(\d+\.\d{2})",
        r"diluted eps[^$]{0,40}?\$\s?(\d+\.\d{2})",
        r"\$\s?(\d+\.\d{2})\s+per\s+diluted\s+share",
        r"\beps (?:of|was)\s+\$\s?(\d+\.\d{2})",
        r"\(\$\s?(\d+\.\d{2})\s+per\s+share\)",
        r"\bdiluted\s+\$\s?(\d+\.\d{2})",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            near = text[max(0, m.start() - 25):m.start()].lower()
            far = text[max(0, m.start() - 60):m.end()].lower()
            if any(w in near for w in ("non-gaap", "adjusted", "excluding")):
                continue
            if any(w in far for w in ("dividend", "book value")):
                continue
            # WHY: JPM's headline gives reported EPS ($4.63) AND EPS "excluding a
            # significant item" ($5.23). The old version returned the adjusted one
            # for Q4 2025 and Q2 2026. Skip any figure tied to "significant item(s)".
            wide = text[max(0, m.start() - 80):m.end()].lower()
            if "significant item" in wide or "excluding" in near:
                continue
            return float(m.group(1))
    return None


QUARTER_NUM = {"first": 1, "second": 2, "third": 3, "fourth": 4}
QUARTER_WORD = {v: k for k, v in QUARTER_NUM.items()}


def extract_period(text, filing_date):
    """
    WHY THIS CHANGED: the old version could pick the year-ago comparison
    ('fourth quarter fiscal 2024' in a 2025 filing). Now we collect every
    quarter mention with a sensible year and keep the LATEST year, since
    the quarter being reported is always the newest one mentioned.
    Handles 'third quarter of fiscal 2026', 'fiscal 2025 fourth quarter',
    'second-quarter 2026', and 'Q2 FY26'.
    """
    filing_year = int(filing_date[:4])

    # 1) Headline first. WHY: a fourth-quarter release also talks about NEXT
    # year's outlook ("first quarter of fiscal 2027"), so "newest year
    # mentioned" picked the wrong quarter for NVDA and WMT February filings.
    headline_patterns = [
        r"results\s+for\s+(?:the\s+)?(first|second|third|fourth)\s+quarter\s+(?:and\s+)?(?:of\s+)?(fiscal\s+(?:year\s+)?)?(\d{4})",
        r"\bQ([1-4])\s*FY\s?'?(\d{4}|\d{2})\b",
    ]
    heads = []
    for i, pat in enumerate(headline_patterns):
        for m in re.finditer(pat, text, re.IGNORECASE):
            if i == 0:
                heads.append((m.start(), QUARTER_NUM[m.group(1).lower()], int(m.group(3)), bool(m.group(2))))
            else:
                y = int(m.group(2))
                heads.append((m.start(), int(m.group(1)), y + 2000 if y < 100 else y, True))
    heads = [h for h in heads if filing_year - 1 <= h[2] <= filing_year + 1]
    if heads:
        _, quarter, year, fiscal = min(heads)
        return f"{QUARTER_WORD[quarter]} quarter {'fiscal ' if fiscal else ''}{year}"

    # 2) Otherwise, the newest year mentioned (skipping outlook sentences).
    found = []  # (year, position, quarter_number, is_fiscal)

    for m in re.finditer(r"\b(first|second|third|fourth)[\s-]+quarter\s+(?:and\s+)?(?:of\s+)?(fiscal\s+(?:year\s+)?)?(\d{4})",
                         text, re.IGNORECASE):
        found.append((int(m.group(3)), m.start(), QUARTER_NUM[m.group(1).lower()], bool(m.group(2))))
    for m in re.finditer(r"\bfiscal\s+(?:year\s+)?(\d{4})\s+(first|second|third|fourth)\s+quarter",
                         text, re.IGNORECASE):
        found.append((int(m.group(1)), m.start(), QUARTER_NUM[m.group(2).lower()], True))
    for m in re.finditer(r"\bQ([1-4])\s*FY\s?'?(\d{4}|\d{2})\b", text):
        year = int(m.group(2))
        found.append((year + 2000 if year < 100 else year, m.start(), int(m.group(1)), True))

    plausible = [f for f in found if filing_year - 1 <= f[0] <= filing_year + 1]
    if plausible:
        latest_year = max(f[0] for f in plausible)
        year, _, quarter, fiscal = min((f for f in plausible if f[0] == latest_year), key=lambda f: f[1])
        return f"{QUARTER_WORD[quarter]} quarter {'fiscal ' if fiscal else ''}{year}"

    m = re.search(r"quarter\s+ended\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})", text)
    if m:
        return f"quarter ended {m.group(1)}"
    return NOT_FOUND


def extract_fields(text, filing_date):
    unit = table_unit(text)
    revenue = extract_revenue(text, unit)
    eps = extract_eps(text)
    net_income = extract_net_income(text, unit)
    # Sanity check: profit can never be bigger than sales. If it is, the unit
    # was misread, so shrink it by 1,000 until it makes sense.
    if revenue and net_income:
        while net_income > revenue:
            net_income = round(net_income / 1000, 1)
    return {
        "period": extract_period(text, filing_date),
        "revenue_reported": revenue if revenue is not None else NOT_FOUND,
        "eps_diluted": eps if eps is not None else NOT_FOUND,
        "net_income": net_income if net_income is not None else NOT_FOUND,
    }


def money(value, suffix="M"):
    return value if value == NOT_FOUND else f"${value:,.2f}" if suffix == "" else f"${value:,.0f}{suffix}"


# --- 6. Main ------------------------------------------------------------------
def main():
    rows = []
    for company in COMPANIES:
        ticker = company["ticker"]
        print(f"\n=== {company['name']} ({ticker}) ===")
        try:
            filings = get_item_202_filings(company["cik"], CANDIDATES_TO_TRY)
        except Exception as error:
            print(f"[{ticker}] WARNING: could not read EDGAR submissions ({error}). Skipping company.")
            continue
        if not filings:
            print(f"[{ticker}] WARNING: no Item 2.02 filings found.")
            continue

        kept = 0
        for filing in filings:
            if kept >= FILINGS_PER_COMPANY:
                break
            date = filing["filing_date"]
            try:
                url = find_press_release_url(company["cik"], filing["accession"])
                if url is None:
                    print(f"[{ticker}] {date}: WARNING: no press release exhibit found. Skipping.")
                    continue
                text = download_plain_text(url)
            except Exception as error:
                print(f"[{ticker}] {date}: WARNING: download failed ({error}). Skipping.")
                continue

            if DEBUG:
                DEBUG_DIR.mkdir(exist_ok=True)
                (DEBUG_DIR / f"{ticker}_{date}.txt").write_text(f"{url}\n\n{text[:3000]}", encoding="utf-8")

            row = {"company": company["name"], "ticker": ticker, "cik": company["cik"],
                   "filing_date": date, **extract_fields(text, date)}
            rows.append(row)
            kept += 1
            print(f"[{ticker}] | {row['period']} | Revenue: {money(row['revenue_reported'])} | "
                  f"EPS: {money(row['eps_diluted'], '')} | Net Income: {money(row['net_income'])}")

        if kept < FILINGS_PER_COMPANY:
            print(f"[{ticker}] NOTE: only {kept} of {FILINGS_PER_COMPANY} filings could be processed.")

    fields = ["company", "ticker", "cik", "filing_date", "period",
              "revenue_reported", "eps_diluted", "net_income"]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSaved {len(rows)} rows to hw03/earnings_history.csv "
          f"(revenue and net income are in millions of USD).")


if __name__ == "__main__":
    main()
