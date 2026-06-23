#!/usr/bin/env python3
"""
EUR/CNY Prognose Tracker - Scraper
Holt täglich die Prognosen von kursprognose.com und vergleicht mit echten Kursen
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys

# Pfade
TRACKER_DIR = Path.home() / ".hermes/eur-cny-tracker"
DATA_DIR = TRACKER_DIR / "data"
FORECAST_FILE = DATA_DIR / "forecasts.jsonl"
ACCURACY_FILE = DATA_DIR / "accuracy.json"

DATA_DIR.mkdir(exist_ok=True)

def run_curl(url, extra_args=None):
    """Führt curl aus und gibt Antwort zurück"""
    cmd = ["curl", "-s", "-L"]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def scrape_forecast():
    """Scraped die Prognose-Tabellen von kursprognose.com"""
    html = run_curl("https://kursprognose.com/eur-cny")
    
    # Datum heute
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Extrahiere aktuellen Kurs
    current_match = re.search(r'Der aktuelle Euro Yuan Wechselkurs ist gleich\s+<strong>\s*(\d+\.?\d*)\s*</strong>', html)
    current_rate = float(current_match.group(1)) if current_match else None
    
    # Extrahiere tägliche Prognosen (nächste 24 Tage)
    daily_forecasts = []
    # Finde alle Zeilen in der täglichen Prognose-Tabelle mit <td class="tb">
    daily_pattern = r'<td class="tb">(\d{2}\.\d{2})</td>\s*<td class="tb">(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)</td>\s*<td class="tb"><strong>(\d+\.\d+)</strong></td>\s*<td class="tb">(\d+\.\d+)</td>\s*<td class="tb">(\d+\.\d+)</td>'
    
    matches = re.findall(daily_pattern, html)
    
    for match in matches[:30]:  # Max 30 Tage
        try:
            date_str = match[0]  # DD.MM
            rate = float(match[1])
            low = float(match[2])
            high = float(match[3])
            
            # Parse Datum (Format: DD.MM)
            day, month = date_str.split('.')
            year = datetime.now().year
            # Wenn Monat kleiner als aktueller Monat, dann nächstes Jahr
            if int(month) < datetime.now().month:
                year += 1
            forecast_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            daily_forecasts.append({
                "date": forecast_date,
                "rate": rate,
                "low": low,
                "high": high
            })
        except:
            continue
    
    # Extrahiere monatliche Prognosen (2026-2030)
    monthly_forecasts = []
    
    # Pattern für Monatsnamen und Werte
    monthly_pattern = r'<td class="tb"><strong>(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)</strong></td>\s*<td class="tb">(\d+\.\d+)-(\d+\.\d+)</td>\s*<td class="tb"><strong>(\d+\.\d+)</strong></td>'
    
    # Pattern für Jahr-Zeilen (z.B. "<td>2026</td>" oder "<td>2028 Fortsetzung</td>")
    year_pattern = r'<td[^>]*>(202[6-9]|2030)(?:\s+Fortsetzung)?</td>'
    
    month_map = {
        'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04',
        'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
        'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12'
    }
    
    # Suche alle Monate OHNE Limit
    month_matches = re.findall(monthly_pattern, html)
    
    # WICHTIG: Die Seite hat 2 Sets von Prognosen:
    # - EUR → CNY (was wir wollen, erste ~50 matches)
    # - CNY → EUR (umgekehrt, zweite ~50 matches)
    # Wir nehmen nur die erste Hälfte
    month_matches = month_matches[:len(month_matches)//2]
    
    # Suche alle Jahre
    year_matches = re.findall(year_pattern, html)
    
    # Baue Liste: Jedes Jahr-Tag startet neuen Jahr-Block
    current_year = datetime.now().year
    month_counter = 0
    
    # Iteriere über Jahr-Tags in der HTML um Jahr-Wechsel zu erkennen
    html_parts = re.split(year_pattern, html)
    
    # Einfachere Logik: Gehe alle Monate durch und weise Jahre sequenziell zu
    current_year = datetime.now().year
    current_month = datetime.now().month
    last_assigned_month = current_month - 1  # Start: Monate ab aktuellem Monat
    
    for match in month_matches:
        try:
            month_str = match[0]
            low = float(match[1])
            high = float(match[2])
            rate = float(match[3])
            
            month_num = int(month_map[month_str])
            
            # Wenn Monat kleiner als letzter Monat → Jahr++
            if month_num < last_assigned_month:
                current_year += 1
            
            last_assigned_month = month_num
            forecast_date = f"{current_year}-{month_num:02d}-01"
            
            monthly_forecasts.append({
                "date": forecast_date,
                "rate": rate,
                "low": low,
                "high": high
            })
        except Exception as e:
            continue
    
    print(f"✅ Erfasst: {len(monthly_forecasts)} monatliche Prognosen (2026-2030)")
    
    return {
        "timestamp": today,
        "scraped_at": datetime.now().isoformat(),
        "current_rate": current_rate,
        "daily_forecasts": daily_forecasts[:30],  # Max 30 Tage
        "monthly_forecasts": monthly_forecasts  # ALLE Monate (2026-2030)
    }

def get_actual_rate(date_str=None):
    """Holt echten EUR/CNY Kurs von ECB oder Forex API"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Versuche exchangerate-api.com (kostenlos)
    try:
        response = run_curl(f"https://api.exchangerate-api.com/v4/latest/EUR")
        data = json.loads(response)
        if 'rates' in data and 'CNY' in data['rates']:
            return data['rates']['CNY']
    except:
        pass
    
    # Fallback: aus der gescrapten aktuellen Rate
    return None

def calculate_accuracy():
    """Berechnet die Accuracy der Prognosen"""
    if not FORECAST_FILE.exists():
        return {}
    
    # Lade alle gespeicherten Prognosen
    forecasts = []
    with open(FORECAST_FILE, 'r') as f:
        for line in f:
            forecasts.append(json.loads(line))
    
    if len(forecasts) < 2:
        return {"message": "Zu wenig Daten für Accuracy-Berechnung"}
    
    daily_errors = []
    monthly_errors = []
    
    # Für jede vergangene Prognose
    for forecast in forecasts[:-7]:  # Ignoriere letzte 7 Tage (noch nicht eingetreten)
        forecast_date = datetime.fromisoformat(forecast['scraped_at'])
        
        # Prüfe tägliche Prognosen
        for daily in forecast.get('daily_forecasts', []):
            target_date = daily['date']
            predicted_rate = daily['rate']
            
            # Finde echten Kurs an diesem Datum
            actual = None
            for later_forecast in forecasts:
                if later_forecast['timestamp'] == target_date:
                    actual = later_forecast.get('current_rate')
                    break
            
            if actual:
                error = abs(predicted_rate - actual)
                error_pct = (error / actual) * 100
                days_ahead = (datetime.fromisoformat(target_date) - forecast_date).days
                
                daily_errors.append({
                    "forecast_date": forecast['timestamp'],
                    "target_date": target_date,
                    "predicted": predicted_rate,
                    "actual": actual,
                    "error": error,
                    "error_pct": error_pct,
                    "days_ahead": days_ahead
                })
    
    # Statistiken
    if daily_errors:
        avg_error = sum(e['error'] for e in daily_errors) / len(daily_errors)
        avg_error_pct = sum(e['error_pct'] for e in daily_errors) / len(daily_errors)
    else:
        avg_error = 0
        avg_error_pct = 0
    
    accuracy = {
        "last_updated": datetime.now().isoformat(),
        "total_forecasts": len(forecasts),
        "daily_predictions_checked": len(daily_errors),
        "avg_error": round(avg_error, 4),
        "avg_error_pct": round(avg_error_pct, 2),
        "daily_errors": daily_errors[-100:],  # Letzte 100
        "monthly_errors": monthly_errors
    }
    
    return accuracy

def save_forecast(data):
    """Speichert Prognose in JSONL Datei"""
    with open(FORECAST_FILE, 'a') as f:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')

def save_accuracy(data):
    """Speichert Accuracy-Daten"""
    with open(ACCURACY_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    print(f"🔄 EUR/CNY Prognose Tracker - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Scrape Prognose
    print("📊 Scrape Prognosen von kursprognose.com...")
    forecast_data = scrape_forecast()
    
    if forecast_data['current_rate']:
        print(f"✅ Aktueller Kurs: {forecast_data['current_rate']}")
        print(f"✅ Tägliche Prognosen: {len(forecast_data['daily_forecasts'])}")
        print(f"✅ Monatliche Prognosen: {len(forecast_data['monthly_forecasts'])}")
    else:
        print("❌ Fehler beim Scraping")
        return
    
    # 2. Speichere Prognose
    save_forecast(forecast_data)
    print(f"💾 Prognose gespeichert in {FORECAST_FILE}")
    
    # 3. Berechne Accuracy
    print("\n📈 Berechne Prognose-Genauigkeit...")
    accuracy = calculate_accuracy()
    
    if 'avg_error_pct' in accuracy:
        print(f"✅ Durchschnittlicher Fehler: {accuracy['avg_error_pct']}%")
        print(f"✅ Geprüfte Prognosen: {accuracy['daily_predictions_checked']}")
    
    save_accuracy(accuracy)
    print(f"💾 Accuracy gespeichert in {ACCURACY_FILE}")
    
    # 4. Trigger Dashboard Generation
    print("\n🎨 Generiere Dashboard...")
    dashboard_script = TRACKER_DIR / "scripts/generate_dashboard.py"
    if dashboard_script.exists():
        subprocess.run([sys.executable, str(dashboard_script)])
    
    # 5. Upload to GitHub
    print("\n📤 Lade zu GitHub hoch...")
    upload_script = TRACKER_DIR / "scripts/github_upload.py"
    if upload_script.exists():
        subprocess.run([sys.executable, str(upload_script)])
    
    print("\n✅ Fertig!")
    print(f"Dashboard local: ~/.hermes/eur-cny-tracker/dashboard.html")
    print(f"Dashboard online: https://ali-sportstech.github.io/eur-cny-tracker/dashboard.html")

if __name__ == "__main__":
    main()
