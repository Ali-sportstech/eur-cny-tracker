#!/usr/bin/env python3
"""
EUR/CNY Tracker Dashboard Generator
Erstellt interaktives HTML Dashboard mit Charts
"""

import json
from datetime import datetime
from pathlib import Path

TRACKER_DIR = Path.home() / ".hermes/eur-cny-tracker"
DATA_DIR = TRACKER_DIR / "data"
FORECAST_FILE = DATA_DIR / "forecasts.jsonl"
ACCURACY_FILE = DATA_DIR / "accuracy.json"
DASHBOARD_FILE = TRACKER_DIR / "dashboard.html"

def load_forecasts():
    """Lädt alle Prognosen"""
    if not FORECAST_FILE.exists():
        return []
    
    forecasts = []
    with open(FORECAST_FILE, 'r') as f:
        for line in f:
            forecasts.append(json.loads(line))
    return forecasts

def load_accuracy():
    """Lädt Accuracy-Daten"""
    if not ACCURACY_FILE.exists():
        return {}
    
    with open(ACCURACY_FILE, 'r') as f:
        return json.load(f)

def generate_dashboard():
    """Generiert HTML Dashboard"""
    forecasts = load_forecasts()
    accuracy = load_accuracy()
    
    if not forecasts:
        return "<html><body><h1>Noch keine Daten vorhanden</h1></body></html>"
    
    # Aktuellste Prognose
    latest = forecasts[-1]
    current_rate = latest.get('current_rate', 'N/A')
    
    # Verlauf der aktuellen Kurse
    rate_history = []
    for f in forecasts:
        if f.get('current_rate'):
            rate_history.append({
                "date": f['timestamp'],
                "rate": f['current_rate']
            })
    
    # Chart-Daten für Prognose vs Reality
    chart_dates = [r['date'] for r in rate_history]
    chart_rates = [r['rate'] for r in rate_history]
    
    # Prognose-Änderungen
    forecast_changes = []
    if len(forecasts) >= 2:
        for i in range(1, min(8, len(forecasts))):
            old = forecasts[-i-1]
            new = forecasts[-i]
            
            # Vergleiche Prognose für gleichen Tag
            if old['daily_forecasts'] and new['daily_forecasts']:
                old_first = old['daily_forecasts'][0]['rate']
                new_first = new['daily_forecasts'][0]['rate']
                change = new_first - old_first
                change_pct = (change / old_first) * 100
                
                forecast_changes.append({
                    "date": new['timestamp'],
                    "old_rate": old_first,
                    "new_rate": new_first,
                    "change": change,
                    "change_pct": change_pct
                })
    
    # Accuracy Statistiken
    avg_error_pct = accuracy.get('avg_error_pct', 'N/A')
    total_checks = accuracy.get('daily_predictions_checked', 0)
    
    # Prognose für nächste 7 Tage
    upcoming = latest.get('daily_forecasts', [])[:7]
    
    # Prognose für nächste 3 Monate
    upcoming_months = latest.get('monthly_forecasts', [])[:3]
    
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EUR/CNY Prognose Tracker</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        h1 {{
            font-size: 2.5em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        
        .card h2 {{
            font-size: 1.2em;
            color: #333;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .stat-big {{
            font-size: 3em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .stat-label {{
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .accuracy {{
            font-size: 2.5em;
            font-weight: bold;
            color: #10b981;
        }}
        
        .accuracy.bad {{
            color: #ef4444;
        }}
        
        .accuracy.medium {{
            color: #f59e0b;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #666;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .change-positive {{
            color: #10b981;
            font-weight: 600;
        }}
        
        .change-negative {{
            color: #ef4444;
            font-weight: 600;
        }}
        
        .chart-container {{
            position: relative;
            height: 400px;
            margin-top: 20px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge-green {{
            background: #d1fae5;
            color: #065f46;
        }}
        
        .badge-red {{
            background: #fee2e2;
            color: #991b1b;
        }}
        
        .badge-yellow {{
            background: #fef3c7;
            color: #92400e;
        }}
        
        .update-time {{
            text-align: center;
            color: white;
            margin-top: 20px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 EUR/CNY Prognose Tracker</h1>
            <p class="subtitle">Tracking der kursprognose.com Vorhersagen vs. Realität</p>
        </header>
        
        <div class="grid">
            <div class="card">
                <h2>💱 Aktueller Kurs</h2>
                <div class="stat-big">{current_rate}</div>
                <div class="stat-label">EUR → CNY</div>
            </div>
            
            <div class="card">
                <h2>🎯 Prognose-Genauigkeit</h2>
                <div class="accuracy {'bad' if isinstance(avg_error_pct, (int, float)) and avg_error_pct > 2 else 'medium' if isinstance(avg_error_pct, (int, float)) and avg_error_pct > 1 else ''}">{avg_error_pct}%</div>
                <div class="stat-label">Durchschnittlicher Fehler ({total_checks} Checks)</div>
            </div>
            
            <div class="card">
                <h2>📈 Datenpunkte</h2>
                <div class="stat-big">{len(forecasts)}</div>
                <div class="stat-label">Tage getrackt</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card" style="grid-column: 1 / -1;">
                <h2>📉 Kursverlauf (Letzte 30 Tage)</h2>
                <div class="chart-container">
                    <canvas id="rateChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🔮 Prognose Nächste 7 Tage</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Datum</th>
                            <th>Prognose</th>
                            <th>Range</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for day in upcoming:
        date_obj = datetime.fromisoformat(day['date'])
        formatted_date = date_obj.strftime('%d.%m.%Y')
        rate = day['rate']
        low = day.get('low', 'N/A')
        high = day.get('high', 'N/A')
        range_str = f"{low} - {high}" if low != 'N/A' else 'N/A'
        
        html += f"""
                        <tr>
                            <td>{formatted_date}</td>
                            <td><strong>{rate}</strong></td>
                            <td>{range_str}</td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h2>📅 Monatsprognosen</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Monat</th>
                            <th>Prognose</th>
                            <th>Range</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for month in upcoming_months:
        date_obj = datetime.fromisoformat(month['date'])
        formatted_month = date_obj.strftime('%B %Y')
        rate = month['rate']
        low = month.get('low', 'N/A')
        high = month.get('high', 'N/A')
        range_str = f"{low} - {high}" if low != 'N/A' else 'N/A'
        
        html += f"""
                        <tr>
                            <td>{formatted_month}</td>
                            <td><strong>{rate}</strong></td>
                            <td>{range_str}</td>
                        </tr>
"""
    
    html += """
                    </tbody>
                </table>
            </div>
        </div>
"""
    
    if forecast_changes:
        html += """
        <div class="card">
            <h2>🔄 Prognose-Änderungen (Letzte 7 Tage)</h2>
            <p style="color: #666; margin-bottom: 15px;">Wie sich die Prognose für den nächsten Tag verändert hat</p>
            <table>
                <thead>
                    <tr>
                        <th>Datum</th>
                        <th>Alte Prognose</th>
                        <th>Neue Prognose</th>
                        <th>Änderung</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for change in forecast_changes:
            change_class = "change-positive" if change['change'] > 0 else "change-negative"
            change_arrow = "↑" if change['change'] > 0 else "↓"
            
            html += f"""
                    <tr>
                        <td>{change['date']}</td>
                        <td>{change['old_rate']}</td>
                        <td>{change['new_rate']}</td>
                        <td class="{change_class}">{change_arrow} {abs(change['change']):.4f} ({change['change_pct']:+.2f}%)</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # Chart-Daten vorbereiten
    chart_labels = json.dumps(chart_dates[-30:])
    chart_data = json.dumps(chart_rates[-30:])
    
    html += f"""
        <div class="update-time">
            Letzte Aktualisierung: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
        </div>
    </div>
    
    <script>
        const ctx = document.getElementById('rateChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {chart_labels},
                datasets: [{{
                    label: 'EUR/CNY Kurs',
                    data: {chart_data},
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        mode: 'index',
                        intersect: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        grid: {{
                            color: 'rgba(0,0,0,0.05)'
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html

def main():
    print("🎨 Generiere Dashboard...")
    
    html = generate_dashboard()
    
    with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Dashboard erstellt: {DASHBOARD_FILE}")
    print(f"\nÖffne im Browser: file://{DASHBOARD_FILE}")

if __name__ == "__main__":
    main()
