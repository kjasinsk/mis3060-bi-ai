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
USER_AGENT = "MIS3060 Villanova kjasinsk@villanova.edu"
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
    response = requests.get(url, headers=HEADERS, timeout=30)
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
    response = requests.get(url, headers=HEADERS, timeout=30)
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
    # FIX: a director who decides "not to stand for re-election" is leaving
    # the board. The old version only saw the word "election" and called
    # Reid Hoffman's June 2026 Microsoft filing an "appointment".
    re.compile(r"not\s+(?:to\s+)?(?:stand|seek|run)\s+for\s+re-?election", re.IGNORECASE),
    # FIX: "Tim Cook will transition from his role as CEO to Executive Chair"
    # is a departure from one role AND an appointment to another ("both").
    re.compile(r"transition(?:s|ed|ing)?\s+from\s+(?:his|her|their)\s+(?:role|position)", re.IGNORECASE),
]
APPOINTMENT_PATTERNS = [
    re.compile(r"appoint(?:s|ed|ing|ment)?", re.IGNORECASE),
    # "elected"/"election", but NOT "re-elected"/"re-election" or "selected".
    re.compile(r"(?<![A-Za-z-])elect(?:s|ed|ing|ion)\b", re.IGNORECASE),
    # "named CEO", but not the SEC phrase "named executive officers".
    re.compile(r"\bnamed\b(?!\s+executive\s+officer)", re.IGNORECASE),
    re.compile(r"promot(?:e|es|ed|ing|ion)", re.IGNORECASE),
    re.compile(r"will serve as", re.IGNORECASE),
    # FIX: "Art Levinson ... will become Lead Independent Director" and
    # "Mr. Petno will become sole CEO" were missed.
    re.compile(r"will become\s+(?:the\s+|sole\s+|its\s+|[A-Z][A-Za-z]+['’]s\s+)?"
               r"(?:[A-Z]|CEO|Co-|general counsel|chief|president|senior|executive|vice)"),
    # "Ms. Newstead will join Apple as senior vice president"
    re.compile(r"will join\s+(?:[A-Z][A-Za-z]+\s+)?as\b"),
    re.compile(r"transition(?:s|ed|ing)?\s+from\s+(?:his|her|their)\s+(?:role|position)", re.IGNORECASE),
]
# Sentences where "re-election" means leaving, never an appointment.
NOT_STANDING_PATTERN = DEPARTURE_PATTERNS[5]

# A section heading like "Item 5.02. Departure of Directors ..." mentions
# both "departure" and "appointment" language without describing an actual
# event. FIX: we now cut the heading out of the text instead of throwing
# away the whole sentence it is glued to (the heading often has no period,
# so the first real sentence of the item was being thrown away with it).
ITEM_HEADING_TEXT = re.compile(
    r"Item\s+5\.02\.?\s*Departure of Directors or (?:Certain|Principal) Officers;?\s*"
    r"Election of Directors;?\s*Appointment of (?:Certain|Principal) Officers;?\s*"
    r"(?:Compensatory Arrangements of Certain Officers\.?)?",
    re.IGNORECASE,
)
ITEM_HEADING_PATTERN = re.compile(r"item\s+5\.02", re.IGNORECASE)

NAME_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][a-zA-Z'-]+){1,2})\b")

# "Mr. Hoffman", "Ms. McLay", "Dr. Drell", "Mr. Di Sibio"
HONORIFIC_PATTERN = re.compile(r"\b(?:Mr|Ms|Mrs|Dr)\.\s+([A-Z][a-zA-Z'-]+(?:\s+[A-Z][a-zA-Z'-]+)?)")

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
    # Added now that we look for EVERY name in a sentence (not just the first):
    # company, division and job-area words that come in capitalized pairs
    # ("Walmart International", "Investment Bank", "Worldwide Field").
    "Walmart", "International", "Club", "Apple", "Microsoft", "Nvidia", "NVIDIA",
    "JPMorgan", "Chase", "Bank", "Banking", "Investment", "Commercial", "Consumer",
    "Community", "Wealth", "Asset", "Management", "Worldwide", "Field", "Hardware",
    "Engineering", "Supply", "Chain", "Innovation", "Automation", "Product", "Global",
    "Partner", "Solutions", "Sales", "Industry", "Standard", "Index", "Composite",
    "Group", "Regulation", "Audit", "Merchandising", "Consumables", "Lead", "Chair",
    "Co", "Operating", "Business", "Legal", "Technology", "Marketing", "Retail",
    "Stores", "Division", "Segment", "Center", "Data", "Principal", "Controller",
    # Exhibit list boilerplate: "104 Cover Page Interactive Data File (embedded
    # within the Inline XBRL document)" was coming out as two fake "names".
    "Cover", "Page", "Interactive", "Inline", "XBRL", "File", "Document", "Schema",
} | MONTH_NAMES

# A second word that looks like a past-tense/participle verb ("Re-elected",
# "Terminated", "Approved") rather than a surname is a strong sign the match
# is boilerplate governance text, not an actual person's name — this catches
# cases the fixed stopword list above doesn't anticipate. It can occasionally
# reject a real surname that happens to end in "ed" (e.g. "Reed"); that's a
# known, documented trade-off in exchange for cutting out far more noise.
TRAILING_VERB_PATTERN = re.compile(r"^[A-Za-z]{3,}ed$")

# FIX: added CEO/CFO/COO shorthand, Co-President, Executive Chair, Lead
# Independent Director and Principal Accounting Officer. JPM ("Co-Presidents",
# "CEO of CCB") and Apple ("Executive Chair") titles were all NOT_FOUND.
TITLE_CORE = (
    r"(?:Executive |Senior |Interim |Acting )?(?:Chief [A-Z][a-zA-Z]+ Officer"
    r"|President(?: and Chief Executive Officer)?"
    r"|Co-Presidents?|Co-CEOs?|(?:sole )?CEO|CFO|COO"
    r"|Executive Chair(?:man|woman)?|Chair(?:man|woman)?(?: of the Board)?"
    r"|Lead Independent Director"
    r"|Principal (?:Accounting|Financial|Executive) Officer|Controller"
    r"|General Counsel|Secretary|Treasurer"
    r"|Vice President(?: of [A-Za-z ]+)?"
    # Some filings write titles in lowercase ("president and chief executive
    # officer", "general counsel") — FIX: those were missed (Walmart/McMillon,
    # Apple/Newstead).
    r"|(?:executive |senior )?vice president|president and chief executive officer"
    r"|chief [a-z]+ officer|general counsel)"
)
TITLE_PATTERN = re.compile(r"\b(" + TITLE_CORE + r")(?![A-Za-z])")

# After a title, keep going through ", President and Chief Executive Officer,
# Walmart International" so the whole title is captured, not just
# "Executive Vice President" (validation 5B, Kathryn McLay).
TITLE_WORD = r"(?:[A-Z][A-Za-z.&'’-]*|&)"
TITLE_TAIL = re.compile(
    r"^(?:(?:,\s*|\s+and\s+)(?:" + TITLE_CORE + r"|" + TITLE_WORD + r"(?:\s+" + TITLE_WORD + r")*)"
    r"|\s+of\s+(?:the\s+)?" + TITLE_WORD + r"(?:\s+" + TITLE_WORD + r")*)"
)
TITLE_STOP_WORDS = {"Mr.", "Ms.", "Mrs.", "Dr.", "On", "The", "Since", "In", "Effective", "Also"}

# Titles that come right after the words that introduce a NEW role.
NEW_ROLE_LEAD = re.compile(
    r"\b(?:as|become|to|elected|appointed|named|promoted to)\s+(?:the\s+|its\s+|our\s+|a\s+|[A-Z][A-Za-z]+['’]s\s+)?"
)

DATE_TEXT = r"[A-Z][a-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}"
DATE_PATTERN = re.compile(
    r"effective\s+(?:as of\s+|on\s+)?(?:the close of business(?: on)?\s+)?(" + DATE_TEXT + r")",
    re.IGNORECASE,
)
# "effective as of the Effective Date", "on the Transition Date"
DEFINED_DATE_USE = re.compile(r"(?:effective\s+)?(?:as of|on)\s+the\s+([A-Z][a-z]+ Date)\b")
# 'February 1, 2026 (the "Effective Date")'
DEFINED_DATE_DEF = re.compile(
    r"(" + DATE_TEXT + r")\s*\(the\s+[\"“”]?([A-Z][a-z]+ Date)[\"“”]?\)"
)
ROLE_START_DATE = re.compile(r"\b(?:become|join|joins|begin|begins)\b[^.]{0,80}?\bon\s+(" + DATE_TEXT + r")")
EFFECTIVE_IMMEDIATELY = re.compile(r"effective\s+immediately", re.IGNORECASE)
LEADING_ON_DATE = re.compile(r"\bOn\s+(" + DATE_TEXT + r")")


def clean_title(title: str) -> str:
    words = title.split()
    for i, word in enumerate(words):
        if word in TITLE_STOP_WORDS:
            words = words[:i]
            break
    title = " ".join(words).rstrip(" ,;")
    title = re.sub(r"\bCo-(President|CEO)s\b", r"Co-\1", title)
    # "... of the Company" / "of NVIDIA Corporation" adds nothing to a title.
    title = re.sub(r"\s+of\s+(?:the\s+)?(?:Company|Firm|Registrant|[A-Z][A-Za-z]* (?:Corporation|Inc\.?))$", "", title)
    if title and title == title.lower():
        title = " ".join(w if w in ("and", "of", "the") else w.capitalize() for w in title.split())
    return title[0].upper() + title[1:] if title else title


def title_at(sentence: str, start: int):
    """Match a title starting exactly at `start`, including its tail."""
    m = TITLE_PATTERN.match(sentence, start)
    if not m:
        return None
    end = m.end()
    while True:
        tail = TITLE_TAIL.match(sentence[end:])
        if not tail or not tail.group(0).strip(" ,"):
            break
        end += tail.end()
    return clean_title(sentence[start:end])


def find_title_in_sentence(sentence: str, prefer_new_role: bool = False):
    if prefer_new_role:
        # "will transition from his role as CEO to Executive Chair": the new
        # role is the one after "to".
        moving = re.search(r"transition\w*\s+from\s+.*?\bto\s+(?:the\s+)?", sentence)
        if moving:
            title = title_at(sentence, moving.end())
            if title:
                return title
        # For appointments, use the title that follows "as"/"become"/"to"/
        # "appointed" — i.e. the NEW job. FIX: John Ternus came out as
        # "Senior Vice President of Hardware Engineering" (his old job)
        # instead of "Chief Executive Officer".
        for lead in NEW_ROLE_LEAD.finditer(sentence):
            title = title_at(sentence, lead.end())
            if title:
                return title
    m = TITLE_PATTERN.search(sentence)
    if m:
        return title_at(sentence, m.start())
    # Board seats: "appointed ... to its Board of Directors", "resigned from the Board".
    if re.search(r"\bBoard of Directors\b|\bthe Board\b|\bas a director\b", sentence):
        return "Director"
    return None


def is_real_name(candidate: str) -> bool:
    words = candidate.replace(".", "").split()
    if any(word in NAME_STOPWORDS for word in words):
        return False
    # Skip a trailing word that looks like a past-tense verb rather
    # than a surname (e.g. "Hoffman Re-elected").
    if any(TRAILING_VERB_PATTERN.match(word.replace("-", "")) for word in words[1:]):
        return False
    return True


def find_names_in_sentence(sentence: str, known_names: list) -> list:
    """
    FIX: returns EVERY person in the sentence, not just the first one.
    "Doug Petno, 61, and Troy Rohrbaugh, 56, ... have been elected
    Co-Presidents" is two appointments; the old version only kept Petno.
    "Mr. Petno"/"Dr. Drell" are matched back to the full name used
    elsewhere in the filing.
    """
    found = []  # (position, name)
    for match in NAME_PATTERN.finditer(sentence):
        candidate = match.group(1)
        if is_real_name(candidate):
            found.append((match.start(), candidate))
    for match in HONORIFIC_PATTERN.finditer(sentence):
        surname = match.group(1)
        full = next((n for n in known_names if n == surname or n.endswith(" " + surname)), None)
        if full is None and " " in surname:
            # "Mr. Parker will" -> try just the first word
            first = surname.split()[0]
            full = next((n for n in known_names if n.endswith(" " + first)), None)
        if full:
            found.append((match.start(), full))
    # keep each person once, at their first position, in reading order
    result, seen = [], set()
    for pos, name in sorted(found):
        if name not in seen:
            seen.add(name)
            result.append((pos, name))
    return result


def find_effective_date(sentences, index, defined_dates):
    """
    Look for the effective date in this sentence first, then (FIX) in the
    next sentence, since filings often say who changed in one sentence and
    when in the next (Walmart/McLay, validation 5B). Also understands
    'effective as of the Effective Date' (a date defined earlier in the
    filing) and 'On June 25, 2026, ... effective immediately'.
    """
    for offset in (0, 1):
        if index + offset >= len(sentences):
            break
        sentence = sentences[index + offset]
        m = DATE_PATTERN.search(sentence)
        if m:
            return m.group(1)
        m = DEFINED_DATE_USE.search(sentence)
        if m and m.group(1) in defined_dates:
            return defined_dates[m.group(1)]
        if offset == 0:
            m = ROLE_START_DATE.search(sentence)
            if m:
                return m.group(1)
        if offset == 0 and EFFECTIVE_IMMEDIATELY.search(sentence):
            on = LEADING_ON_DATE.search(sentence)
            if on:
                return on.group(1)
    return None


# Sub-heading text (e.g. "Departure of Directors or Certain Officers.")
# that echoes the departure/appointment keywords without describing an
# actual event.
HEADING_PHRASES = [
    "departure of directors", "election of directors",
    "appointment of certain officers", "compensatory arrangements of certain officers",
]

# Avoid splitting sentences right after "Mr."/"Ms."/"Dr.", a middle initial
# ("Ajay K. Puri" — FIX: this split made NVIDIA's July 2026 departure come
# out with no name), or abbreviations like "U.S." and "Inc.".
SENTENCE_SPLIT_PATTERN = re.compile(
    r"(?<!Mr\.)(?<!Mrs\.)(?<!Ms\.)(?<!Dr\.)(?<!\s[A-Z]\.)(?<!U\.S\.)(?<!Inc\.)(?<!Corp\.)"
    r"(?<!Co\.)(?<!No\.)(?<=[.!?])\s+"
)


def keyword_flags(text: str):
    dep = any(p.search(text) for p in DEPARTURE_PATTERNS)
    app = any(p.search(text) for p in APPOINTMENT_PATTERNS)
    if NOT_STANDING_PATTERN.search(text):
        app = False
    return dep, app


def assign_roles(sentence, names, is_departure, is_appointment):
    """
    FIX: when one sentence names several people, decide who is leaving and
    who is arriving from the words next to EACH name, not from the whole
    sentence. Before, "Ms. Adams will remain ... until her retirement ...,
    after which it will be led by Ms. Newstead" tagged BOTH women as "both".

    Each name gets the text from its position up to the next name. If that
    piece has no keyword ("Doug Petno, 61, and ..."), the name borrows the
    role of the next name that has one ("... Troy Rohrbaugh ... have been
    elected"), or else the keyword before the first name ("the Board
    appointed X and Y"). A name with no role at all is skipped.
    Returns (name, is_departure, is_appointment, text_piece) tuples.
    """
    if not names:
        return [("NOT_FOUND", is_departure, is_appointment, sentence)]
    if len(names) == 1:
        return [(names[0][1], is_departure, is_appointment, sentence)]

    pieces = []
    for i, (pos, name) in enumerate(names):
        end = names[i + 1][0] if i + 1 < len(names) else len(sentence)
        piece = sentence[pos:end]
        pieces.append((name, *keyword_flags(piece), piece))

    lead_flags = keyword_flags(sentence[:names[0][0]])
    result = []
    for i, (name, dep, app, piece) in enumerate(pieces):
        if not dep and not app:
            later = next(((d, a) for _, d, a, _ in pieces[i + 1:] if d or a), None)
            dep, app = later if later else lead_flags
        if dep or app:
            result.append((name, dep, app, piece))
    return result


def extract_events(text: str) -> list:
    """
    Splits the filing text into sentences, tags each one as
    departure-related and/or appointment-related based on keyword
    matches, and pulls every name plus a title/effective date out of each
    tagged sentence. A departure and an appointment for the same person
    are merged into a single event_type="both" row (e.g. someone stepping
    down as CEO but staying on as Executive Chair). Fields that can't be
    found are stored as "NOT_FOUND" rather than guessed.
    """
    text = ITEM_HEADING_TEXT.sub(" ", text)
    sentences = SENTENCE_SPLIT_PATTERN.split(text)

    # Dates the filing defines once and then refers to by name.
    defined_dates = {label: date for date, label in DEFINED_DATE_DEF.findall(text)}

    # Every full name in the filing, so "Mr. Hoffman" can be matched to "Reid Hoffman".
    known_names = []
    for match in NAME_PATTERN.finditer(text):
        if is_real_name(match.group(1)) and match.group(1) not in known_names:
            known_names.append(match.group(1))

    departure_candidates = []
    appointment_candidates = []

    for index, sentence in enumerate(sentences):
        lower = sentence.lower()
        if ITEM_HEADING_PATTERN.search(sentence) or any(phrase in lower for phrase in HEADING_PHRASES):
            # Just a section heading or a cross-reference to Item 5.02 —
            # not a description of an actual event.
            continue

        # Skip shareholder-vote sentences (annual meeting results). Their
        # proposal titles ("Censorship Risk Audit", "Advisory Vote") look like
        # names but are not people.
        if any(w in lower for w in ("proposal", "broker non-vote", "votes cast", "abstain", "withheld", "votes for")):
            continue

        is_departure = any(p.search(sentence) for p in DEPARTURE_PATTERNS)
        is_appointment = any(p.search(sentence) for p in APPOINTMENT_PATTERNS)
        if NOT_STANDING_PATTERN.search(sentence):
            is_appointment = False
        if not is_departure and not is_appointment:
            continue

        if "xbrl" in lower or "cover page" in lower:
            continue  # exhibit list, not an event

        effective_date = find_effective_date(sentences, index, defined_dates) or "NOT_FOUND"
        old_title = find_title_in_sentence(sentence) or "NOT_FOUND"
        new_title = find_title_in_sentence(sentence, prefer_new_role=True) or "NOT_FOUND"

        for name, is_departure, is_appointment, part in assign_roles(
                sentence, find_names_in_sentence(sentence, known_names), is_departure, is_appointment):
            if name == "NOT_FOUND" and old_title == "NOT_FOUND":
                # Neither a name nor a title — just a sentence that happens to
                # contain a keyword. It adds nothing as a row.
                continue
            if is_departure:
                departure_candidates.append({
                    "person_name": name, "title": find_title_in_sentence(part) or old_title,
                    "effective_date": effective_date,
                })
            if is_appointment:
                appointment_candidates.append({
                    "person_name": name,
                    "title": find_title_in_sentence(part, prefer_new_role=True) or new_title,
                    "effective_date": effective_date,
                })

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

    # One row per person per event type. When the same fact is restated in
    # several sentences, keep the first row but fill in any NOT_FOUND
    # fields from the later mentions.
    merged = {}
    order = []
    for event in events:
        key = (event["event_type"], event["person_name"])
        if key not in merged:
            merged[key] = dict(event)
            order.append(key)
            continue
        for field in ("title", "effective_date"):
            if merged[key][field] == "NOT_FOUND" and event[field] != "NOT_FOUND":
                merged[key][field] = event[field]
    deduped = [merged[key] for key in order]

    # A person tagged "both" should not ALSO get a separate departure or
    # appointment row from another sentence.
    both_names = {e["person_name"] for e in deduped if e["event_type"] == "both"}
    deduped = [e for e in deduped if e["event_type"] == "both" or e["person_name"] not in both_names]

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

    # A row with no name is only kept if the filing produced no named rows
    # at all (then it is the only record that something happened).
    if any(e["person_name"] != "NOT_FOUND" for e in cleaned):
        cleaned = [e for e in cleaned if e["person_name"] != "NOT_FOUND"]

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
