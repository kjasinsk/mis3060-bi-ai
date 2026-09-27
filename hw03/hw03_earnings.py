"""
HW3 — Earnings Pipeline (Item 2.02)
======================================

Builds a small earnings database for five companies by reading their
most recent 8-K "Results of Operations" filings directly from SEC
EDGAR: for each company, finds the 4 most recent Item 2.02 filings,
downloads the attached press release exhibit, strips it to plain text,
and pulls out revenue, diluted EPS, net income, and the reporting
period. Saves everything to hw03/earnings_history.csv.

SEC EDGAR requires every request to carry an identifying User-Agent
header (a name + a real email) or it will reject/rate-limit the
request. That header is set once below and reused on every request.
"""

import os
import re
import csv
import sys
import subprocess
import importlib


# --- 0. Make sure the packages we need are installed ---
def ensure_installed(pip_name, import_name=None):
    import_name = import_name or pip_name
    try:
        importlib.import_module(import_name)
    except ImportError:
        print(f"'{pip_name}' not found — installing it now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
        print(f"'{pip_name}' installed successfully.\n")


ensure_installed("requests")
ensure_installed("beautifulsoup4", import_name="bs4")

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402


# --- 1. Required SEC EDGAR identification header ---
# EDGAR blocks/rate-limits requests that don't identify a real contact.
# Replace the email below with your own Villanova address before submitting.
USER_AGENT = "MIS3060 Villanova youremail@villanova.edu"
HEADERS = {"User-Agent": USER_AGENT}

FILINGS_PER_COMPANY = 4

COMPANIES = [
    {"name": "Apple Inc.", "ticker": "AAPL", "cik": "0000320193"},
    {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"name": "NVIDIA Corporation", "ticker": "NVDA", "cik": "0001045810"},
    {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "cik": "0000019617"},
    {"name": "Walmart Inc.", "ticker": "WMT", "cik": "0000104169"},
]


# --- 2. Find the N most recent 8-K filings with Item 2.02 ---
def get_recent_8ks_with_item(cik: str, item_code: str, limit: int):
    """
    Returns a list of up to `limit` dicts {filing_date, accession_nodash},
    most recent first, for 8-K filings whose 'items' field contains
    `item_code`.
    """
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    recent = data["filings"]["recent"]
    forms = recent["form"]
    items_list = recent.get("items", [""] * len(forms))
    dates = recent["filingDate"]
    accessions = recent["accessionNumber"]

    matches = []
    for form, items, date, accession in zip(forms, items_list, dates, accessions):
        if form == "8-K" and item_code in items:
            matches.append({
                "filing_date": date,
                "accession_nodash": accession.replace("-", ""),
            })
            if len(matches) >= limit:
                break

    return matches


# --- 3. Locate the earnings press release exhibit inside a filing ---
def find_press_release_exhibit_url(cik: str, accession_nodash: str):
    """
    Fetches the filing's index (as JSON) and returns the URL of the
    earnings press release exhibit — the .htm file whose name contains
    "ex99" or "ex-99" — or None if nothing matching is found.
    """
    cik_no_leading_zeros = str(int(cik))
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_nodash}/index.json"
    response = requests.get(index_url, headers=HEADERS)
    response.raise_for_status()
    index_data = response.json()

    for item in index_data.get("directory", {}).get("item", []):
        name = item.get("name", "").lower()
        if name.endswith(".htm") and ("ex99" in name or "ex-99" in name):
            return f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_nodash}/{item['name']}"

    return None


# --- 4. Download a page and strip it down to plain text ---
def download_plain_text(url: str) -> str:
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# --- Extraction helpers ---
def find_dollar_amount_near(text: str, keywords, window: int = 120):
    """
    Looks for the dollar amount (e.g. "$38.3 billion", "$1.25") that sits
    CLOSEST to any occurrence of the given keywords, searching up to
    `window` characters on either side. Picking the nearest match (rather
    than just the first one in reading order) matters because a filing
    often has an unrelated dollar figure from a different sentence sitting
    inside that window too. Returns the amount as a string, or None.
    """
    dollar_pattern = re.compile(
        r"\$\s?-?[\d,]+(?:\.\d+)?\s?(?:billion|million|thousand)?",
        re.IGNORECASE,
    )
    lower_text = text.lower()

    for keyword in keywords:
        best_amount = None
        best_distance = None
        for kw_match in re.finditer(re.escape(keyword.lower()), lower_text):
            window_start = max(0, kw_match.start() - window)
            window_end = min(len(text), kw_match.end() + window)
            for dollar_match in dollar_pattern.finditer(text, window_start, window_end):
                if dollar_match.start() >= kw_match.end():
                    distance = dollar_match.start() - kw_match.end()
                else:
                    distance = kw_match.start() - dollar_match.end()
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_amount = dollar_match.group(0).strip()
        if best_amount is not None:
            return best_amount

    return None


def extract_period_label(text: str, filing_date: str) -> str:
    """
    Best-effort guess at which fiscal quarter the press release covers,
    e.g. "fourth quarter fiscal 2024". Falls back to the filing date if
    no clear quarter language is found.
    """
    match = re.search(
        r"(first|second|third|fourth)\s+quarter\s+(?:of\s+)?(?:fiscal\s+(?:year\s+)?)?(\d{4})",
        text, re.IGNORECASE,
    )
    if match:
        return f"{match.group(1).lower()} quarter fiscal {match.group(2)}"

    match = re.search(r"quarter\s+ended\s+([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})", text, re.IGNORECASE)
    if match:
        return f"quarter ended {match.group(1)}"

    return f"unknown quarter (filed {filing_date})"


def extract_earnings_fields(text: str, filing_date: str) -> dict:
    revenue = find_dollar_amount_near(text, ["total revenue", "net revenue", "revenue"])
    eps_diluted = find_dollar_amount_near(text, ["diluted earnings per share", "diluted eps"])
    net_income = find_dollar_amount_near(text, ["net income", "net quarterly income", "net earnings"])
    period = extract_period_label(text, filing_date)

    return {
        "period": period,
        "revenue_reported": revenue if revenue else "NOT_FOUND",
        "eps_diluted": eps_diluted if eps_diluted else "NOT_FOUND",
        "net_income": net_income if net_income else "NOT_FOUND",
    }


# --- 5. Save all rows to CSV ---
def save_csv_rows(rows, path: str = "hw03/earnings_history.csv"):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fieldnames = ["company", "ticker", "cik", "filing_date", "period",
                  "revenue_reported", "eps_diluted", "net_income"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    all_rows = []

    for company in COMPANIES:
        print(f"\n=== {company['name']} ({company['ticker']}) ===")
        try:
            filings = get_recent_8ks_with_item(company["cik"], "2.02", FILINGS_PER_COMPANY)
        except Exception as error:
            print(f"[{company['ticker']}]: Failed to query EDGAR submissions ({error}). Skipping company.")
            continue

        if not filings:
            print(f"[{company['ticker']}]: No Item 2.02 filings found.")
            continue

        for filing in filings:
            try:
                exhibit_url = find_press_release_exhibit_url(company["cik"], filing["accession_nodash"])
            except Exception as error:
                print(f"[{company['ticker']}] {filing['filing_date']}: Failed to fetch filing index ({error}). Skipping.")
                continue

            if exhibit_url is None:
                print(f"[{company['ticker']}] {filing['filing_date']}: No press release exhibit (ex-99) found. Skipping.")
                continue

            try:
                press_release_text = download_plain_text(exhibit_url)
            except Exception as error:
                print(f"[{company['ticker']}] {filing['filing_date']}: Failed to download press release ({error}). Skipping.")
                continue

            fields = extract_earnings_fields(press_release_text, filing["filing_date"])

            row = {
                "company": company["name"],
                "ticker": company["ticker"],
                "cik": company["cik"],
                "filing_date": filing["filing_date"],
                **fields,
            }
            all_rows.append(row)

            print(f"[{row['ticker']}] | {row['period']} | "
                  f"Revenue: {row['revenue_reported']} | "
                  f"EPS: {row['eps_diluted']} | "
                  f"Net Income: {row['net_income']}")

    save_csv_rows(all_rows)
    print(f"\nhw03/earnings_history.csv saved successfully. ({len(all_rows)} rows)")
