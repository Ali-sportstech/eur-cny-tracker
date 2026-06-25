#!/usr/bin/env python3
"""
EUR/CNY Zentralbank-Events
==========================
Verwaltet die geldpolitischen Termine der drei für EUR/CNY relevanten Notenbanken:

- EZB (Frankfurt)  -> beeinflusst EUR
- US Fed (FOMC)    -> beeinflusst USD (EUR/CNY ist über USD verkettet)
- PBoC (China LPR) -> beeinflusst CNY

Zinsentscheide an diesen Tagen können den EUR/CNY-Kurs stark bewegen.
Das Modul liefert:
- alle kommenden Events (sortiert)
- Events in den nächsten N Tagen (für Erinnerungen)
- Events an einem bestimmten Tag (für Day-of-Reminder)

Quellen:
- EZB:  https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html
- Fed:  https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- PBoC: LPR-Fixing am 20. jedes Monats (bzw. nächster Werktag)
        https://www.global-rates.com (historische Bestätigung)
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path

TRACKER_DIR = Path.home() / ".hermes/eur-cny-tracker"
DATA_DIR = TRACKER_DIR / "data"
EVENTS_FILE = DATA_DIR / "events.json"

DATA_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# EZB - Governing Council monetary policy meetings (Entscheid-Tag = Day 2)
# Quelle: ECB offizieller Sitzungskalender
# ---------------------------------------------------------------------------
ECB_DECISIONS = [
    "2026-07-23", "2026-09-10", "2026-10-29", "2026-12-17",
    "2027-02-04", "2027-03-18", "2027-04-29", "2027-06-10",
    "2027-07-22", "2027-09-09", "2027-10-28", "2027-12-16",
]

# ---------------------------------------------------------------------------
# US Fed - FOMC meetings (Entscheid wird am 2. Sitzungstag verkündet)
# Quelle: Federal Reserve FOMC calendar
# ---------------------------------------------------------------------------
FED_DECISIONS = [
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
    "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09",
    "2027-07-28", "2027-09-15", "2027-10-27", "2027-12-08",
]


def next_business_day(d):
    """Verschiebt auf nächsten Werktag falls Wochenende."""
    while d.weekday() >= 5:  # 5=Sa, 6=So
        d += timedelta(days=1)
    return d


def generate_pboc_lpr_dates(start_year=2026, end_year=2027):
    """PBoC LPR-Fixing: 20. jedes Monats, bzw. nächster Werktag."""
    dates = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            d = date(year, month, 20)
            d = next_business_day(d)
            dates.append(d.isoformat())
    return dates


def build_events():
    """Baut die vollständige Event-Liste."""
    events = []

    for d in ECB_DECISIONS:
        events.append({
            "date": d,
            "bank": "EZB",
            "currency": "EUR",
            "type": "Leitzins-Entscheid",
            "icon": "🇪🇺",
            "impact": "EUR-Seite des Kurses",
            "note": "EZB Governing Council – Zinsentscheid + Pressekonferenz",
        })

    for d in FED_DECISIONS:
        events.append({
            "date": d,
            "bank": "US Fed",
            "currency": "USD",
            "type": "FOMC Zinsentscheid",
            "icon": "🇺🇸",
            "impact": "USD – wirkt über USD-Verkettung auf EUR/CNY",
            "note": "Federal Reserve FOMC – Zinsentscheid (Tag 2)",
        })

    for d in generate_pboc_lpr_dates():
        events.append({
            "date": d,
            "bank": "PBoC",
            "currency": "CNY",
            "type": "LPR-Fixing",
            "icon": "🇨🇳",
            "impact": "CNY-Seite des Kurses",
            "note": "People's Bank of China – Loan Prime Rate Fixing",
        })

    events.sort(key=lambda e: e["date"])
    return events


def save_events():
    events = build_events()
    json.dump({"generated_at": datetime.now().isoformat(), "events": events},
              open(EVENTS_FILE, "w"), indent=2, ensure_ascii=False)
    return events


def load_events():
    if not EVENTS_FILE.exists():
        return save_events()
    try:
        return json.load(open(EVENTS_FILE)).get("events", [])
    except Exception:
        return save_events()


def upcoming_events(days_ahead=None, ref_date=None):
    """Events ab heute (oder ref_date). Optional auf N Tage begrenzt."""
    ref = ref_date or date.today()
    ref_str = ref.isoformat()
    events = load_events()
    out = []
    for e in events:
        if e["date"] < ref_str:
            continue
        if days_ahead is not None:
            delta = (date.fromisoformat(e["date"]) - ref).days
            if delta > days_ahead:
                continue
        out.append(e)
    return out


def events_on(day=None):
    """Events an einem bestimmten Tag (Default: heute)."""
    ref = (day or date.today()).isoformat()
    return [e for e in load_events() if e["date"] == ref]


def format_event_line(e, ref_date=None):
    ref = ref_date or date.today()
    delta = (date.fromisoformat(e["date"]) - ref).days
    if delta == 0:
        when = "**HEUTE**"
    elif delta == 1:
        when = "morgen"
    else:
        when = f"in {delta} Tagen"
    d = datetime.fromisoformat(e["date"]).strftime("%d.%m.%Y")
    return f"{e['icon']} {d} ({when}): {e['bank']} {e['type']} → {e['impact']}"


if __name__ == "__main__":
    events = save_events()
    print(f"✅ {len(events)} Events gespeichert in {EVENTS_FILE}")
    print(f"\n📅 Nächste 5 Events ab heute:")
    for e in upcoming_events()[:5]:
        print("  " + format_event_line(e))
