# EUR/CNY Prognose Tracker

Automatisches Tracking der Prognosen von kursprognose.com und Vergleich mit echten Kursen.

## 📊 Features

- ✅ **Täglicher Scraper** (10:00 Uhr) holt Prognosen von kursprognose.com
- ✅ **30 Tage** tägliche Prognosen
- ✅ **12 Monate** monatliche Prognosen
- ✅ **Accuracy-Tracking** - Vergleich Prognose vs. Realität
- ✅ **Interaktives Dashboard** mit Charts
- ✅ **Smart Notifications** - Nur bei Auffälligkeiten

## 🗂 Struktur

```
~/.hermes/eur-cny-tracker/
├── data/
│   ├── forecasts.jsonl          # Alle gescrapten Prognosen (eine pro Zeile)
│   └── accuracy.json             # Berechnete Genauigkeits-Statistiken
├── scripts/
│   ├── scraper.py                # Haupt-Scraper
│   └── generate_dashboard.py    # Dashboard-Generator
└── dashboard.html                # Live Dashboard
```

## 🚀 Verwendung

### Dashboard öffnen

```bash
open ~/.hermes/eur-cny-tracker/dashboard.html
```

Oder direkt im Browser:
```
file:///Users/ailab/.hermes/eur-cny-tracker/dashboard.html
```

### Manuell ausführen

```bash
python3 ~/.hermes/eur-cny-tracker/scripts/scraper.py
```

### Cron-Job verwalten

```bash
# Status prüfen
hermes cron list

# Pausieren
hermes cron pause "EUR/CNY Prognose Tracker"

# Fortsetzen
hermes cron resume "EUR/CNY Prognose Tracker"

# Manuell triggern
hermes cron run 639f6db0a36e
```

## 📈 Dashboard-Inhalte

- **Aktueller Kurs** - Live EUR/CNY Rate
- **Prognose-Genauigkeit** - Durchschnittlicher Fehler in %
- **Kursverlauf** - Chart der letzten 30 Tage
- **7-Tage-Prognose** - Vorhersage für die nächste Woche
- **Monats-Prognosen** - 3-Monats-Ausblick
- **Prognose-Änderungen** - Wie sich die Vorhersage täglich ändert

## 🔔 Benachrichtigungen

Der Cron-Job meldet sich **nur** bei:

- ❌ **Scraping-Fehler**
- 📊 **Starke Kursänderung** (>1.5% zum Vortag)
- 🔮 **Prognose stark geändert** (>2% zum Vortag)
- ⚠️ **Niedrige Accuracy** (>5% Fehler)

Ansonsten: Stille Ausführung im Hintergrund.

## 📊 Daten-Format

### forecasts.jsonl

Jede Zeile ist ein JSON-Objekt:

```json
{
  "timestamp": "2026-06-23",
  "scraped_at": "2026-06-23T12:10:55.123456",
  "current_rate": 7.7394,
  "daily_forecasts": [
    {
      "date": "2026-06-24",
      "rate": 7.7198,
      "low": 7.6040,
      "high": 7.8356
    }
  ],
  "monthly_forecasts": [
    {
      "date": "2026-06-01",
      "rate": 7.6537,
      "low": 7.5275,
      "high": 7.9191
    }
  ]
}
```

### accuracy.json

```json
{
  "last_updated": "2026-06-23T12:10:55",
  "total_forecasts": 45,
  "daily_predictions_checked": 120,
  "avg_error": 0.0523,
  "avg_error_pct": 0.68,
  "daily_errors": [
    {
      "forecast_date": "2026-06-10",
      "target_date": "2026-06-15",
      "predicted": 7.6500,
      "actual": 7.6453,
      "error": 0.0047,
      "error_pct": 0.06,
      "days_ahead": 5
    }
  ]
}
```

## 🛠 Troubleshooting

### Scraper findet keine Prognosen

```bash
# HTML-Struktur prüfen
curl -s "https://kursprognose.com/eur-cny" | grep -A 5 "Euro Yuan Prognose"
```

### Dashboard zeigt keine Daten

```bash
# Prüfe ob Daten vorhanden
cat ~/.hermes/eur-cny-tracker/data/forecasts.jsonl | wc -l

# Dashboard neu generieren
python3 ~/.hermes/eur-cny-tracker/scripts/generate_dashboard.py
```

### Cron-Job läuft nicht

```bash
# Logs prüfen
hermes cron logs

# Status
hermes cron list
```

## 🔧 Anpassungen

### Benachrichtigungs-Schwellwerte ändern

Editiere `~/.hermes/scripts/eur-cny-notifier.py`:

```python
# Zeile ~42 - Kursänderungs-Schwelle
if abs(change_pct) > 1.5:  # ← Hier ändern

# Zeile ~54 - Prognose-Änderungs-Schwelle
if abs(forecast_change_pct) > 2:  # ← Hier ändern

# Zeile ~64 - Accuracy-Schwelle
if avg_error_pct > 5:  # ← Hier ändern
```

### Cron-Zeit ändern

```bash
# 8:00 Uhr statt 10:00
hermes cron update 639f6db0a36e --schedule "0 8 * * *"

# Zweimal täglich (10:00 und 18:00)
hermes cron update 639f6db0a36e --schedule "0 10,18 * * *"
```

## 📝 Hinweise

- **Erste 7 Tage**: Keine Accuracy-Berechnung möglich (Prognosen noch nicht eingetreten)
- **Datengröße**: ~1-2 KB pro Tag → ~730 KB pro Jahr
- **Netzwerk**: Scraper benötigt Internetzugang
- **Performance**: Scraping dauert ~2-5 Sekunden

## 🎯 Nächste Schritte (Optional)

- [ ] Email-Alerts bei kritischen Schwellen
- [ ] Historische Accuracy-Charts
- [ ] Vergleich mehrerer Prognose-Quellen
- [ ] Export als CSV/Excel
- [ ] Telegram-Bot-Integration

---

**Erstellt:** 2026-06-23  
**Letzte Aktualisierung:** 2026-06-23  
**Version:** 1.0
