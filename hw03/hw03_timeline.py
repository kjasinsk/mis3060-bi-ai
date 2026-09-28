"""
HW3 — Corporate Events Timeline (Part 4)
============================================

Joins hw03/earnings_history.csv and hw03/executive_events.csv: for
every executive event, finds the nearest earnings filing for the same
company, calculates how many days apart they are, and labels the
event as coming before, after, or in the same week as that earnings
announcement. Saves the combined table to
hw03/corporate_events_timeline.csv and prints a per-company summary.
"""

import csv
import os
from datetime import datetime
from pathlib import Path


# Read/write next to this script, no matter which folder you run it from.
BASE_DIR = Path(__file__).resolve().parent
EARNINGS_PATH = BASE_DIR / "earnings_history.csv"
EVENTS_PATH = BASE_DIR / "executive_events.csv"
OUTPUT_PATH = BASE_DIR / "corporate_events_timeline.csv"

SAME_WEEK_THRESHOLD_DAYS = 7


def read_csv_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def find_nearest_earnings_filing(event_row, earnings_rows):
    """
    Among earnings_rows for the same company as event_row, returns the
    one whose filing_date is closest in time to the event's filing_date,
    along with the signed day gap (positive = earnings came after the
    event, negative = earnings came before the event). Returns
    (None, None) if the company has no earnings rows or the event's
    date can't be parsed.
    """
    event_date = parse_date(event_row["filing_date"])
    if event_date is None:
        return None, None

    same_company = [
        row for row in earnings_rows
        if row.get("ticker") == event_row.get("ticker")
    ]
    if not same_company:
        return None, None

    best_row = None
    best_gap = None
    best_abs_gap = None
    for row in same_company:
        earnings_date = parse_date(row["filing_date"])
        if earnings_date is None:
            continue
        gap = (earnings_date - event_date).days
        abs_gap = abs(gap)
        if best_abs_gap is None or abs_gap < best_abs_gap:
            best_abs_gap = abs_gap
            best_gap = gap
            best_row = row

    return best_row, best_gap


def classify_event_timing(day_gap: int) -> str:
    """
    day_gap is (nearest_earnings_date - event_date).days:
    positive means the earnings filing came AFTER the event,
    negative means it came BEFORE the event.
    """
    if abs(day_gap) <= SAME_WEEK_THRESHOLD_DAYS:
        return "same week"
    elif day_gap > 0:
        # earnings came after the event -> the event came "before earnings"
        return "before earnings"
    else:
        # earnings came before the event -> the event came "after earnings"
        return "after earnings"


def build_timeline(events_rows, earnings_rows):
    timeline_rows = []
    for event in events_rows:
        nearest_earnings, day_gap = find_nearest_earnings_filing(event, earnings_rows)

        combined = {
            "company": event.get("company", "NOT_FOUND"),
            "ticker": event.get("ticker", "NOT_FOUND"),
            "cik": event.get("cik", "NOT_FOUND"),
            "event_filing_date": event.get("filing_date", "NOT_FOUND"),
            "event_type": event.get("event_type", "NOT_FOUND"),
            "person_name": event.get("person_name", "NOT_FOUND"),
            "title": event.get("title", "NOT_FOUND"),
            "effective_date": event.get("effective_date", "NOT_FOUND"),
        }

        if nearest_earnings is None:
            combined.update({
                "earnings_filing_date": "NOT_FOUND",
                "period": "NOT_FOUND",
                "revenue_reported": "NOT_FOUND",
                "eps_diluted": "NOT_FOUND",
                "net_income": "NOT_FOUND",
                "days_to_nearest_earnings": "NOT_FOUND",
                "event_timing": "NOT_FOUND",
            })
        else:
            combined.update({
                "earnings_filing_date": nearest_earnings.get("filing_date", "NOT_FOUND"),
                "period": nearest_earnings.get("period", "NOT_FOUND"),
                "revenue_reported": nearest_earnings.get("revenue_reported", "NOT_FOUND"),
                "eps_diluted": nearest_earnings.get("eps_diluted", "NOT_FOUND"),
                "net_income": nearest_earnings.get("net_income", "NOT_FOUND"),
                "days_to_nearest_earnings": abs(day_gap),
                "event_timing": classify_event_timing(day_gap),
            })

        timeline_rows.append(combined)

    return timeline_rows


def save_csv_rows(rows, path=OUTPUT_PATH):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fieldnames = [
        "company", "ticker", "cik",
        "event_filing_date", "event_type", "person_name", "title", "effective_date",
        "earnings_filing_date", "period", "revenue_reported", "eps_diluted", "net_income",
        "days_to_nearest_earnings", "event_timing",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(timeline_rows):
    by_company = {}
    for row in timeline_rows:
        by_company.setdefault(row["company"], []).append(row)

    print("=== Per-company summary ===")
    if not by_company:
        print("No executive events found for any company — nothing to summarize.")
    for company, rows in by_company.items():
        print(f"\n{company}:")
        for row in rows:
            print(f"  {row['person_name']} ({row['event_type']}, {row['effective_date']}) — "
                  f"{row['event_timing']} (filed {row['event_filing_date']}, "
                  f"nearest earnings filed {row['earnings_filing_date']})")

    before_count = sum(1 for r in timeline_rows if r["event_timing"] == "before earnings")
    after_count = sum(1 for r in timeline_rows if r["event_timing"] == "after earnings")
    same_week_count = sum(1 for r in timeline_rows if r["event_timing"] == "same week")
    not_found_count = sum(1 for r in timeline_rows if r["event_timing"] == "NOT_FOUND")

    print("\n=== Final counts ===")
    print(f"Before earnings: {before_count}")
    print(f"After earnings:  {after_count}")
    print(f"Same week:       {same_week_count}")
    if not_found_count:
        print(f"Could not classify (no matching earnings row): {not_found_count}")


if __name__ == "__main__":
    earnings_rows = read_csv_rows(EARNINGS_PATH)
    events_rows = read_csv_rows(EVENTS_PATH)

    if not events_rows:
        print(f"No rows found in {EVENTS_PATH} — nothing to build a timeline from.")
        save_csv_rows([])
        print(f"\n{OUTPUT_PATH} saved successfully. (0 rows)")
    else:
        timeline_rows = build_timeline(events_rows, earnings_rows)
        save_csv_rows(timeline_rows)
        print_summary(timeline_rows)
        print(f"\n{OUTPUT_PATH} saved successfully. ({len(timeline_rows)} rows)")
