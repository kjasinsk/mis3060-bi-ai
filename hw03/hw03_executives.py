"""
HW3 — Executive Events Pipeline (Item 5.02)
==============================================

Builds a database of executive departures and appointments for five
companies from their 8-K filings on SEC EDGAR: for each company, finds
every Item 5.02 filing from the past 12 months, downloads the full 8-K
text, and extracts each departure/appointment event it describes.
Saves everything to hw03/executive_events.csv.

A note on extraction reliability: pulling a person's name, title, and
effective date out of free-form legal prose with regex is inherently
imperfect — real 8-K language varies a lot filing to filing. Wherever
a field can't be confidently found, this script stores "NOT_FOUND"
rather than guessing, and keeps going rather than crashing.

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
from datetime import datetime, timedelta
from pathlib import Path


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
USER_AGENT = "MIS3060 Villanova youremail@villanova.edu"
HEADERS = {"User-Agent": USER_AGENT}

LOOKBACK_DAYS = 365

COMPANIES = [
    {"name": "Apple Inc.", "ticker": "AAPL", "cik": "0000320193"},
    {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"name": "NVIDIA Corporation", "ticker": "NVDA", "cik": "0001045810"},
    {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "cik": "0000019617"},
    {"name": "Walmart Inc.", "ticker": "WMT", "cik": "0000104169"},
]


# --- 2. Find all 8-K filings with Item 5.02 in the past 12 months ---
def get_recent_8ks_with_item(cik: str, item_code: str, lookback_days: int):
    """
    Returns a list of dicts {filing_date, accession_nodash, primary_document}
    for every 8-K filing whose 'items' field contains `item_code` and whose
    filingDate falls within the past `lookback_days` days.
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
    primary_docs = recent.get("primaryDocument", [""] * len(forms))

    cutoff = datetime.today() - timedelta(days=lookback_days)

    matches = []
    for form, items, date, accession, primary_doc in zip(forms, items_list, dates, accessions, primary_docs):
        if form != "8-K" or item_code not in items:
            continue
        try:
            filing_dt = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            continue
        if filing_dt < cutoff:
            continue
        matches.append({
            "filing_date": date,
            "accession_nodash": accession.replace("-", ""),
            "primary_document": primary_doc,
        })

    return matches


# --- 3. Download the full 8-K document and strip it to plain text ---
def download_plain_text(cik: str, accession_nodash: str, primary_document: str) -> str:
    cik_no_leading_zeros = str(int(cik))
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/{accession_nodash}/{primary_document}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


# --- Extraction helpers ---
# Regex patterns (not plain substrings) so different tenses all match:
# "resign"/"resigned"/"resignation", "stepped down"/"steps down", etc.
DEPARTURE_PATTERNS = [
    re.compile(r"resign(?:s|ed|ing|ation)?", re.IGNORECASE),
    re.compile(r"depart(?:s|ed|ing|ure)?", re.IGNORECASE),
    re.compile(r"retir(?:e|es|ed|ing|ement)", re.IGNORECASE),
    re.compile(r"step(?:s|ped|ping)?\s+down", re.IGNORECASE),
    re.compile(r"ceased to serve", re.IGNORECASE),
]
APPOINTMENT_PATTERNS = [
    re.compile(r"appoint(?:s|ed|ing|ment)?", re.IGNORECASE),
    re.compile(r"elect(?:s|ed|ing|ion)", re.IGNORECASE),
    re.compile(r"\bnamed\b", re.IGNORECASE),
    re.compile(r"promot(?:e|es|ed|ing|ion)", re.IGNORECASE),
    re.compile(r"will serve as", re.IGNORECASE),
]

# A section heading like "Item 5.02. Departure of Directors ..." mentions
# both "departure" and "appointment" language without describing an actual
# event — skip any sentence that's just referencing the item number.
ITEM_HEADING_PATTERN = re.compile(r"item\s+5\.02", re.IGNORECASE)

NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-zA-Z'-]+){1,2})\b")

MONTH_NAMES = {
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
}

NAME_STOPWORDS = {
    "Chief", "Officer", "Officers", "President", "Executive", "Vice", "Senior", "Director",
    "Directors", "Board", "Committee", "Company", "Corporation", "Corp", "Inc", "Item",
    "Results", "Operations", "Securities", "Exchange", "Commission", "Form", "Current",
    "Report", "Section", "Date", "New", "York", "United", "States", "General", "Counsel",
    "Financial", "Accounting", "Human", "Resources", "Chairman", "Chairwoman", "Certain",
    "Election", "Departure", "Appointment", "Effective", "Under", "Pursuant", "Registrant",
    "On", "In", "As", "The", "That", "This", "During", "Following", "Prior", "After",
    "Before", "Mr", "Ms", "Mrs", "Dr", "Also", "However", "Additionally", "Furthermore",
    # Added after seeing real filings: routine governance/proxy boilerplate
    # (annual-meeting director re-elections, auditor mentions, compensation
    # plan language) satisfies the "two capitalized words in a row" name
    # pattern just as well as an actual person's name does, and was showing
    # up as fake "names" like "Hoffman Re-elected" or "Annual Shareholders".
    "Re-elected", "Reelected", "Elected", "Nominee", "Nominees", "Annual", "Meeting",
    "Meetings", "Shareholders", "Stockholders", "Press", "Release", "Touche", "Deloitte",
    "LLP", "PricewaterhouseCoopers", "Ernst", "Young", "KPMG", "Certified", "Public",
    "Accountants", "Auditor", "Auditors", "Firm", "Plan", "Program", "Equity", "Incentive",
    "Compensation", "Base", "Salary", "Bonus", "Severance", "Employment", "Independent",
    "Registered", "Proxy", "Statement", "Target", "Award", "Opportunity", "Agreement",
    "Termination", "Change", "Control", "Named", "Approved", "Ratified",
    # Added after the first real run produced fake names like "Advisory Vote",
    # "Fiscal Year", and "Covenant Not".
    "Advisory", "Vote", "Votes", "Fiscal", "Year", "Quarter", "Covenant", "Covenants",
    "Not", "Non", "Say", "Pay", "Frequency", "Amendment", "Amended", "Bylaws", "Restated",
    "Certificate", "Exhibit", "Stock", "Units", "Restricted", "Performance", "Shares",
    "Holders", "Class", "Common", "Letter", "Offer", "Retention", "Transition", "Services",
    "Against", "Abstain", "Abstentions", "Broker", "Withheld", "For",
    "Shareholder", "Stockholder", "Proposal", "Proposals", "Report", "Policy",
} | MONTH_NAMES

# A second word that looks like a past-tense/participle verb ("Re-elected",
# "Terminated", "Approved") rather than a surname is a strong sign the match
# is boilerplate governance text, not an actual person's name — this catches
# cases the fixed stopword list above doesn't anticipate. It can occasionally
# reject a real surname that happens to end in "ed" (e.g. "Reed"); that's a
# known, documented trade-off in exchange for cutting out far more noise.
TRAILING_VERB_PATTERN = re.compile(r"^[A-Za-z]{3,}ed$")

TITLE_PATTERN = re.compile(
    r"\b((?:Executive |Senior |Interim |Acting )?(?:Chief [A-Z][a-zA-Z]+ Officer"
    r"|President(?: and Chief Executive Officer)?"
    r"|Chief Executive Officer|Chief Financial Officer|Chief Operating Officer"
    r"|Chairman(?: of the Board)?|Chairwoman|General Counsel|Secretary|Treasurer"
    r"|Vice President(?: of [A-Za-z ]+)?))\b"
)

DATE_PATTERN = re.compile(
    r"effective\s+(?:as of\s+|on\s+)?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})",
    re.IGNORECASE,
)


def find_name_in_sentence(sentence: str):
    for match in NAME_PATTERN.finditer(sentence):
        candidate = match.group(1)
        words = candidate.replace(".", "").split()
        if any(word in NAME_STOPWORDS for word in words):
            continue
        # Skip a trailing word that looks like a past-tense verb rather
        # than a surname (e.g. "Hoffman Re-elected") — see comment above
        # TRAILING_VERB_PATTERN.
        if any(TRAILING_VERB_PATTERN.match(word.replace("-", "")) for word in words[1:]):
            continue
        return candidate
    return None


def find_title_in_sentence(sentence: str):
    match = TITLE_PATTERN.search(sentence)
    return match.group(1) if match else None


def find_effective_date_in_sentence(sentence: str):
    match = DATE_PATTERN.search(sentence)
    return match.group(1) if match else None


# Sub-heading text (e.g. "Departure of Directors or Certain Officers.")
# that echoes the departure/appointment keywords without describing an
# actual event.
HEADING_PHRASES = [
    "departure of directors", "certain officers", "election of directors",
    "appointment of certain officers", "compensatory arrangements",
]

# Avoid splitting sentences right after "Mr."/"Mrs."/"Ms."/"Dr." — otherwise
# "Ms. Marshall" gets cut into two separate "sentences".
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<=[.!?])\s+")


def extract_events(text: str) -> list:
    """
    Splits the filing text into sentences, tags each one as
    departure-related and/or appointment-related based on keyword
    matches, and pulls a name/title/effective-date out of each tagged
    sentence. A departure and an appointment that name the same person
    are merged into a single event_type="both" row (e.g. someone
    stepping down as CEO but staying on as Chairman). Fields that
    can't be found are stored as "NOT_FOUND" rather than guessed.
    """
    sentences = SENTENCE_SPLIT_PATTERN.split(text)

    departure_candidates = []
    appointment_candidates = []

    for sentence in sentences:
        lower = sentence.lower()
        if ITEM_HEADING_PATTERN.search(sentence) or any(phrase in lower for phrase in HEADING_PHRASES):
            # Just a section heading ("Item 5.02. Departure of Directors
            # or Certain Officers.") — not a description of an actual event.
            continue

        # Skip shareholder-vote sentences (annual meeting results). Their
        # proposal titles ("Censorship Risk Audit", "Advisory Vote") look like
        # names but are not people.
        if any(w in lower for w in ("proposal", "broker non-vote", "votes cast", "abstain", "withheld", "votes for")):
            continue

        is_departure = any(p.search(sentence) for p in DEPARTURE_PATTERNS)
        is_appointment = any(p.search(sentence) for p in APPOINTMENT_PATTERNS)
        if not is_departure and not is_appointment:
            continue

        candidate = {
            "person_name": find_name_in_sentence(sentence) or "NOT_FOUND",
            "title": find_title_in_sentence(sentence) or "NOT_FOUND",
            "effective_date": find_effective_date_in_sentence(sentence) or "NOT_FOUND",
        }
        if candidate["person_name"] == "NOT_FOUND" and candidate["title"] == "NOT_FOUND":
            # Neither a name nor a title could be pulled out of this
            # sentence — it just happened to contain a departure/appointment
            # keyword (e.g. a generic disclosure sentence), so it wouldn't
            # add any real information as a row. Real filings produced a lot
            # of these NOT_FOUND/NOT_FOUND rows sitting right alongside a
            # second, more complete row for what was clearly the same
            # underlying event — dropping the empty one keeps the real row
            # without losing anything.
            continue
        if is_departure:
            departure_candidates.append(candidate)
        if is_appointment:
            appointment_candidates.append(candidate)

    events = []
    used_appointment_idxs = set()

    for dep in departure_candidates:
        matched_idx = None
        if dep["person_name"] != "NOT_FOUND":
            for i, app in enumerate(appointment_candidates):
                if i in used_appointment_idxs:
                    continue
                if app["person_name"] == dep["person_name"]:
                    matched_idx = i
                    break

        if matched_idx is not None:
            app = appointment_candidates[matched_idx]
            used_appointment_idxs.add(matched_idx)
            events.append({
                "event_type": "both",
                "person_name": dep["person_name"],
                "title": app["title"] if app["title"] != "NOT_FOUND" else dep["title"],
                "effective_date": dep["effective_date"] if dep["effective_date"] != "NOT_FOUND" else app["effective_date"],
            })
        else:
            events.append({
                "event_type": "departure",
                "person_name": dep["person_name"],
                "title": dep["title"],
                "effective_date": dep["effective_date"],
            })

    for i, app in enumerate(appointment_candidates):
        if i in used_appointment_idxs:
            continue
        events.append({
            "event_type": "appointment",
            "person_name": app["person_name"],
            "title": app["title"],
            "effective_date": app["effective_date"],
        })

    # De-duplicate identical events that might arise from the same fact
    # being restated in more than one sentence.
    seen = set()
    deduped = []
    for event in events:
        key = (event["event_type"], event["person_name"], event["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)

    # Drop partial-name duplicates from the same filing, e.g. "Di Sibio" when
    # "Carmine Di Sibio" was also found, or "Nora Johnson" vs "Suzanne Nora Johnson".
    names = [e["person_name"] for e in deduped if e["person_name"] != "NOT_FOUND"]
    cleaned = []
    for event in deduped:
        name = event["person_name"]
        is_partial = name != "NOT_FOUND" and any(
            other != name and other.endswith(" " + name) for other in names
        )
        if not is_partial:
            cleaned.append(event)

    return cleaned


# --- 4. Save all rows to CSV ---
OUTPUT_PATH = Path(__file__).resolve().parent / "executive_events.csv"


def save_csv_rows(rows, path=OUTPUT_PATH):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fieldnames = ["company", "ticker", "cik", "filing_date", "event_type",
                  "person_name", "title", "effective_date"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    all_rows = []

    for company in COMPANIES:
        print(f"\n=== {company['name']} ({company['ticker']}) ===")
        try:
            filings = get_recent_8ks_with_item(company["cik"], "5.02", LOOKBACK_DAYS)
        except Exception as error:
            print(f"[{company['ticker']}]: Failed to query EDGAR submissions ({error}). Skipping company.")
            continue

        if not filings:
            print(f"[{company['ticker']}]: No executive events in past 12 months")
            continue

        company_had_event = False
        for filing in filings:
            try:
                text = download_plain_text(company["cik"], filing["accession_nodash"], filing["primary_document"])
            except Exception as error:
                print(f"[{company['ticker']}] {filing['filing_date']}: Failed to download filing ({error}). Skipping.")
                continue

            events = extract_events(text)
            if not events:
                continue

            for event in events:
                company_had_event = True
                row = {
                    "company": company["name"],
                    "ticker": company["ticker"],
                    "cik": company["cik"],
                    "filing_date": filing["filing_date"],
                    **event,
                }
                all_rows.append(row)
                print(f"[{row['ticker']}] | {row['filing_date']} | {row['event_type']} | "
                      f"{row['person_name']} | {row['title']}")

        if not company_had_event:
            print(f"[{company['ticker']}]: No executive events in past 12 months")

    save_csv_rows(all_rows)
    print(f"\nhw03/executive_events.csv saved successfully. ({len(all_rows)} rows)")
