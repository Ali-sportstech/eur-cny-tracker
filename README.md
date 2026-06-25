# EUR/CNY Tracker

Überwacht die EUR/CNY-Prognosen von **kursprognose.com** und prüft sie gegen die Realität.

## Datenquellen
| Zweck | Quelle |
|---|---|
| 🔮 Prognosen (Anbieter) | https://kursprognose.com/eur-cny |
| 🏦 Wahrheits-Anker (Schlusskurs) | EZB Referenzkurs – ecb.europa.eu |

## Was getrackt wird
1. **Tägliche & monatliche Prognosen** (inkl. Sum%-Spalte = kumulierte Veränderung)
2. **ECB-Schlusskurs** – offizieller täglicher Referenzkurs (~16:00 CET fixiert) + 90-Tage-Historie
3. **Revisions-Tracking** – erkennt, wenn der Anbieter Prognosen für ein Datum nachträglich ändert (Manipulations-/Schönungs-Check)
4. **Ehrliche Accuracy** – erste Prognose je Ziel-Datum vs ECB (täglich + monatlich), damit Revisionen die Trefferquote nicht schönen
5. **Zentralbank-Events** – EZB, US Fed (FOMC), PBoC (LPR) Termine mit Erinnerungen

## Scripts
- `scripts/scraper.py` – scraped Prognosen (daily + monthly + Sum%)
- `scripts/truth_check.py` – ECB-Anker, Revisionen, ehrliche Accuracy
- `scripts/events.py` – Zentralbank-Terminkalender
- `scripts/generate_dashboard.py` – HTML-Dashboard
- `scripts/github_upload.py` – Upload zu GitHub Pages
- `~/.hermes/scripts/eur-cny-notifier.py` – täglicher Digest (Cron 10:00)
- `~/.hermes/scripts/eur-cny-event-reminder.py` – Event-Reminder (Cron 8:00, still wenn kein Termin)

## Datendateien
- `data/forecasts.jsonl` – alle Prognose-Snapshots
- `data/ecb_rates.json` – offizielle ECB-Kurse {Datum: Kurs}
- `data/revisions.json` – Revisions-Historie je Ziel-Datum
- `data/truth_accuracy.json` – Accuracy täglich + monatlich
- `data/events.json` – Zentralbank-Termine

## Cron-Jobs
- **10:00** EUR/CNY Prognose Tracker → Daily-Digest (scrape + truth + events + dashboard)
- **08:00** EUR/CNY Event-Reminder → meldet nur wenn heute/morgen ein Zentralbank-Termin

## Live-Dashboard
https://ali-sportstech.github.io/eur-cny-tracker/dashboard.html

## Quellen Zentralbank-Termine
- EZB: https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html
- Fed: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- PBoC LPR: 20. jedes Monats (bzw. nächster Werktag)

> Hinweis: Notenbank-Termine in `events.py` sind bis Ende 2027 hinterlegt.
> Ende 2027 müssen die 2028er-Termine ergänzt werden (sobald EZB/Fed sie veröffentlichen).
