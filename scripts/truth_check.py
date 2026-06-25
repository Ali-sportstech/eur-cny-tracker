#!/usr/bin/env python3
"""
EUR/CNY Truth-Check Modul
==========================
Schließt zwei Lücken im Tracker:

1. ECB-ANKER (offizieller Tagesschlusskurs):
   Holt den täglichen EZB-Referenzkurs EUR/CNY (~16:00 CET fixiert) plus
   90-Tage-Historie. Das ist der unabhängige "Wahrheits-Kurs", gegen den wir
   die Prognosen des Anbieters tagesgenau prüfen.

2. REVISIONS-TRACKING (Manipulations-Erkennung):
   Der Anbieter könnte seine Prognose für ein bestimmtes Ziel-Datum nachträglich
   verändern, je näher die Realität rückt — und sich so im Nachhinein "schön"
   machen. Wir tracken für jedes Ziel-Datum, wie oft & wie stark der Anbieter
   seine Vorhersage über die Zeit revidiert hat.

Quelle ECB: https://www.ecb.europa.eu/stats/eurofxref/
- eurofxref-daily.xml      (letzter Handelstag)
- eurofxref-hist-90d.xml   (letzte 90 Tage)
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

TRACKER_DIR = Path.home() / ".hermes/eur-cny-tracker"
DATA_DIR = TRACKER_DIR / "data"
FORECAST_FILE = DATA_DIR / "forecasts.jsonl"
ECB_FILE = DATA_DIR / "ecb_rates.json"          # {date: rate} offizielle Schlusskurse
REVISIONS_FILE = DATA_DIR / "revisions.json"    # Revisions-Historie je Ziel-Datum
TRUTH_FILE = DATA_DIR / "truth_accuracy.json"   # Prognose vs ECB-Realität

DATA_DIR.mkdir(exist_ok=True)

ECB_DAILY = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_HIST90 = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"


def run_curl(url):
    result = subprocess.run(["curl", "-s", "-L", url], capture_output=True, text=True)
    return result.stdout


# ---------------------------------------------------------------------------
# 1. ECB-ANKER
# ---------------------------------------------------------------------------
def parse_ecb_xml(xml):
    """Parst ECB eurofxref XML -> dict {date: cny_rate}."""
    out = {}
    # Jeder Tag ist ein <Cube time="YYYY-MM-DD"> ... block mit currency-Cubes
    day_blocks = re.split(r'<Cube\s+time="([0-9-]+)"', xml)
    for i in range(1, len(day_blocks), 2):
        date = day_blocks[i]
        body = day_blocks[i + 1]
        m = re.search(r'currency="CNY"\s+rate="([0-9.]+)"', body)
        if m:
            out[date] = float(m.group(1))
    return out


def update_ecb_rates():
    """Holt ECB-Kurse (daily + 90d Historie) und merged in ecb_rates.json."""
    rates = {}
    if ECB_FILE.exists():
        try:
            rates = json.load(open(ECB_FILE))
        except Exception:
            rates = {}

    # 90-Tage-Historie (füllt Lücken / Backfill)
    hist = parse_ecb_xml(run_curl(ECB_HIST90))
    rates.update(hist)

    # Tageskurs (frischester Wert, überschreibt ggf.)
    daily = parse_ecb_xml(run_curl(ECB_DAILY))
    rates.update(daily)

    rates = {k: v for k, v in sorted(rates.items())}
    json.dump(rates, open(ECB_FILE, "w"), indent=2)
    return rates


# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------
def load_forecasts():
    if not FORECAST_FILE.exists():
        return []
    out = []
    for line in open(FORECAST_FILE):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def clean_daily(forecast):
    """Nur echte EUR->CNY Tagesprognosen (rate > 1), dedupliziert je Datum."""
    seen = {}
    for d in forecast.get("daily_forecasts", []):
        if d.get("rate", 0) >= 1.0:
            seen[d["date"]] = d["rate"]   # letzter gewinnt, aber Liste ist sauber sortiert
    return seen


# ---------------------------------------------------------------------------
# 2. REVISIONS-TRACKING
# ---------------------------------------------------------------------------
def track_revisions():
    """
    Baut je Ziel-Datum die Historie aller Prognosen, die der Anbieter dafür
    über die Zeit abgegeben hat. Erkennt nachträgliche Veränderungen.

    Struktur:
    {
      "2026-07-15": {
         "history": [
            {"forecast_made": "2026-06-23", "predicted": 7.5964},
            {"forecast_made": "2026-06-25", "predicted": 7.5891}, ...
         ],
         "num_revisions": 4,
         "first_predicted": 7.5964,
         "last_predicted": 7.5891,
         "total_drift": -0.0073,        # last - first
         "total_drift_pct": -0.10,
         "max_swing": 0.012             # größter Sprung zwischen 2 aufeinanderfolg. Snapshots
      }, ...
    }
    """
    forecasts = load_forecasts()
    revisions = {}

    for fc in forecasts:
        made = fc.get("timestamp")                 # Tag, an dem Prognose erstellt wurde
        scraped = fc.get("scraped_at", made)
        daily = clean_daily(fc)
        for target_date, predicted in daily.items():
            entry = revisions.setdefault(target_date, {"history": []})
            # Nur protokollieren wenn der Prognose-Tag VOR dem Ziel-Datum liegt
            if made and made < target_date:
                entry["history"].append({
                    "forecast_made": made,
                    "scraped_at": scraped,
                    "predicted": round(predicted, 4),
                })

    # Statistiken berechnen + nur revidierte/relevante behalten
    result = {}
    for target_date, entry in revisions.items():
        hist = entry["history"]
        # Pro Prognose-Tag nur letzten Snapshot behalten (mehrere Läufe/Tag)
        by_day = {}
        for h in hist:
            by_day[h["forecast_made"]] = h
        hist = [by_day[d] for d in sorted(by_day)]
        if len(hist) < 2:
            # zu wenig Snapshots für Revisions-Analyse, aber dennoch speichern
            if hist:
                result[target_date] = {
                    "history": hist,
                    "num_revisions": 0,
                    "first_predicted": hist[0]["predicted"],
                    "last_predicted": hist[0]["predicted"],
                    "total_drift": 0.0,
                    "total_drift_pct": 0.0,
                    "max_swing": 0.0,
                }
            continue

        first = hist[0]["predicted"]
        last = hist[-1]["predicted"]
        swings = [abs(hist[i]["predicted"] - hist[i - 1]["predicted"])
                  for i in range(1, len(hist))]
        max_swing = max(swings) if swings else 0.0
        num_rev = sum(1 for s in swings if s > 0.0001)

        result[target_date] = {
            "history": hist,
            "num_revisions": num_rev,
            "first_predicted": round(first, 4),
            "last_predicted": round(last, 4),
            "total_drift": round(last - first, 4),
            "total_drift_pct": round((last - first) / first * 100, 3) if first else 0.0,
            "max_swing": round(max_swing, 4),
        }

    json.dump(result, open(REVISIONS_FILE, "w"), indent=2)
    return result


def detect_suspicious_revisions(revisions, ecb_rates, swing_threshold=0.01):
    """
    Erkennt verdächtige Muster:
    - Anbieter hat Prognose für ein Datum spät & stark revidiert
    - Besonders verdächtig: Revision DRÜCKT die Prognose RICHTUNG des später
      tatsächlich eingetretenen ECB-Kurses (= nachträgliche Schönung).
    """
    flags = []
    for target_date, r in revisions.items():
        if r["num_revisions"] == 0:
            continue
        if r["max_swing"] < swing_threshold:
            continue

        actual = ecb_rates.get(target_date)
        suspicion = ""
        if actual is not None:
            first_err = abs(r["first_predicted"] - actual)
            last_err = abs(r["last_predicted"] - actual)
            if last_err < first_err - 0.001:
                # Revision brachte Prognose näher an Realität -> potenzielle Schönung
                improve = (first_err - last_err)
                suspicion = (f"Revision rückte Prognose um {improve:.4f} NÄHER an "
                             f"den späteren ECB-Kurs ({actual:.4f}) — mögliche Schönung")
        flags.append({
            "target_date": target_date,
            "first_predicted": r["first_predicted"],
            "last_predicted": r["last_predicted"],
            "total_drift": r["total_drift"],
            "total_drift_pct": r["total_drift_pct"],
            "max_swing": r["max_swing"],
            "num_revisions": r["num_revisions"],
            "actual_ecb": actual,
            "suspicion": suspicion,
        })
    flags.sort(key=lambda x: x["max_swing"], reverse=True)
    return flags


# ---------------------------------------------------------------------------
# 3. PROGNOSE vs ECB-WAHRHEIT (ehrliche Accuracy)
# ---------------------------------------------------------------------------
def monthly_truth(ecb_rates):
    """
    Bewertet die MONATS-Prognosen (Ende-Wert + Sum%) des Anbieters.
    Vergleicht die früheste Monatsprognose je Ziel-Monat gegen den
    tatsächlichen ECB-Monatsschluss (letzter verfügbarer ECB-Kurs im Monat).

    Die Sum%-Spalte des Anbieters ist die kumulierte Veränderung ggü. heute;
    wir prüfen, ob die Richtung & Größenordnung mit der Realität übereinstimmt.
    """
    forecasts = load_forecasts()

    # ECB-Monatsschluss: letzter ECB-Kurs je Monat (YYYY-MM)
    ecb_month_close = {}
    for d in sorted(ecb_rates):
        ecb_month_close[d[:7]] = ecb_rates[d]  # späterer Tag überschreibt -> Monatsende

    # Früheste Monatsprognose je Ziel-Monat
    first_monthly = {}   # "YYYY-MM" -> (made, rate, sum_pct)
    for fc in forecasts:
        made = fc.get("timestamp")
        for m in fc.get("monthly_forecasts", []):
            ym = m["date"][:7]
            if made and made[:7] < ym:  # Prognose vor dem Ziel-Monat
                if ym not in first_monthly or made < first_monthly[ym][0]:
                    first_monthly[ym] = (made, m["rate"], m.get("sum_pct"))

    checks = []
    for ym, (made, rate, sum_pct) in sorted(first_monthly.items()):
        actual = ecb_month_close.get(ym)
        if actual is None:
            continue
        err = abs(rate - actual)
        checks.append({
            "target_month": ym,
            "forecast_made": made,
            "predicted_rate": round(rate, 4),
            "predicted_sum_pct": sum_pct,
            "actual_ecb_close": round(actual, 4),
            "error": round(err, 4),
            "error_pct": round(err / actual * 100, 3),
        })

    if checks:
        avg_err_pct = sum(c["error_pct"] for c in checks) / len(checks)
    else:
        avg_err_pct = 0.0

    return {
        "method": "Früheste Monatsprognose vs ECB-Monatsschluss",
        "months_checked": len(checks),
        "avg_error_pct": round(avg_err_pct, 3),
        "checks": checks,
    }


def truth_accuracy(ecb_rates):
    """
    Vergleicht JEDE Prognose des Anbieters gegen den offiziellen ECB-Kurs
    am Ziel-Datum. Wertet nur die ERSTE (älteste) Prognose je Ziel-Datum,
    damit nachträgliche Revisionen die Accuracy NICHT künstlich verbessern.
    """
    forecasts = load_forecasts()
    # Erste Prognose je Ziel-Datum sammeln (forecast_made < target_date)
    first_pred = {}   # target_date -> (made, predicted)
    for fc in forecasts:
        made = fc.get("timestamp")
        for target_date, predicted in clean_daily(fc).items():
            if not made or made >= target_date:
                continue
            if target_date not in first_pred or made < first_pred[target_date][0]:
                first_pred[target_date] = (made, predicted)

    checks = []
    for target_date, (made, predicted) in sorted(first_pred.items()):
        actual = ecb_rates.get(target_date)
        if actual is None:
            continue
        err = abs(predicted - actual)
        checks.append({
            "target_date": target_date,
            "forecast_made": made,
            "predicted": round(predicted, 4),
            "actual_ecb": round(actual, 4),
            "error": round(err, 4),
            "error_pct": round(err / actual * 100, 3),
            "days_ahead": (datetime.fromisoformat(target_date)
                           - datetime.fromisoformat(made)).days,
        })

    if checks:
        avg_err = sum(c["error"] for c in checks) / len(checks)
        avg_err_pct = sum(c["error_pct"] for c in checks) / len(checks)
    else:
        avg_err = avg_err_pct = 0.0

    out = {
        "last_updated": datetime.now().isoformat(),
        "method": "Erste Prognose je Ziel-Datum vs offizieller ECB-Referenzkurs",
        "predictions_checked": len(checks),
        "avg_error": round(avg_err, 4),
        "avg_error_pct": round(avg_err_pct, 3),
        "checks": checks[-120:],
    }
    json.dump(out, open(TRUTH_FILE, "w"), indent=2)
    return out


# ---------------------------------------------------------------------------
# Orchestrierung
# ---------------------------------------------------------------------------
def run():
    print("🔗 Hole offizielle ECB-Referenzkurse...")
    ecb = update_ecb_rates()
    latest_date = max(ecb) if ecb else None
    print(f"   ECB-Kurse: {len(ecb)} Tage, neuester: {latest_date} = {ecb.get(latest_date)}")

    print("🕵️  Tracke Prognose-Revisionen des Anbieters...")
    revisions = track_revisions()
    flags = detect_suspicious_revisions(revisions, ecb)
    print(f"   Ziel-Daten verfolgt: {len(revisions)}, verdächtige Revisionen: {len(flags)}")

    print("🎯 Berechne ehrliche Accuracy (Prognose vs ECB)...")
    truth = truth_accuracy(ecb)
    print(f"   Täglich geprüft: {truth['predictions_checked']}, Ø-Fehler: {truth['avg_error_pct']}%")

    monthly = monthly_truth(ecb)
    truth["monthly"] = monthly
    json.dump(truth, open(TRUTH_FILE, "w"), indent=2)
    print(f"   Monatlich geprüft: {monthly['months_checked']}, Ø-Fehler: {monthly['avg_error_pct']}%")

    return {"ecb": ecb, "revisions": revisions, "flags": flags, "truth": truth}


if __name__ == "__main__":
    run()
