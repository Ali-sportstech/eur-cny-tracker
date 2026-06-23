#!/usr/bin/env python3
"""
GitHub Setup Automation für EUR/CNY Tracker
"""

import subprocess
import sys
import time
import json
from pathlib import Path

def run_cmd(cmd):
    """Führt Command aus"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    print("🔐 GitHub Authentication Setup")
    print("=" * 60)
    
    # Interaktiver Login mit gh CLI
    print("\n📝 Öffne Browser für GitHub Login...")
    print("⚠️  WICHTIG: Im Browser mit ali.ahmad@sportstech.de einloggen!")
    
    # Starte interaktiven Login
    result = subprocess.run(
        ["gh", "auth", "login", "-h", "github.com", "-p", "https", "-w"],
        input="",
        text=True
    )
    
    if result.returncode != 0:
        print("❌ Login fehlgeschlagen")
        sys.exit(1)
    
    print("\n✅ Login erfolgreich!")
    
    # Erstelle Repository
    print("\n📦 Erstelle Repository 'eur-cny-tracker'...")
    
    exit_code, stdout, stderr = run_cmd(
        'gh repo create eur-cny-tracker --private --description "EUR/CNY Exchange Rate Forecast Tracker" --confirm'
    )
    
    if exit_code == 0 or "already exists" in stderr:
        print("✅ Repository bereit")
    else:
        print(f"⚠️  {stderr}")
    
    # Clone/Setup Repo
    tracker_dir = Path.home() / ".hermes/eur-cny-tracker"
    git_dir = tracker_dir / ".git"
    
    if not git_dir.exists():
        print("\n🔧 Initialisiere Git Repository...")
        run_cmd(f"cd {tracker_dir} && git init")
        run_cmd(f"cd {tracker_dir} && git branch -M main")
        
        # Remote hinzufügen
        exit_code, stdout, stderr = run_cmd("gh api user --jq .login")
        username = stdout.strip()
        
        run_cmd(f"cd {tracker_dir} && git remote add origin https://github.com/{username}/eur-cny-tracker.git")
        print(f"✅ Remote konfiguriert: {username}/eur-cny-tracker")
    
    # Erstelle .gitignore
    gitignore = tracker_dir / ".gitignore"
    gitignore.write_text("data/\n*.pyc\n__pycache__/\n.DS_Store\n")
    
    # Initial Commit
    print("\n📤 Erstelle Initial Commit...")
    run_cmd(f"cd {tracker_dir} && git add -A")
    run_cmd(f'cd {tracker_dir} && git commit -m "Initial commit: EUR/CNY Tracker" || true')
    
    # Push
    print("\n🚀 Pushe zu GitHub...")
    exit_code, stdout, stderr = run_cmd(f"cd {tracker_dir} && git push -u origin main --force")
    
    if exit_code == 0:
        print("✅ Push erfolgreich!")
    else:
        print(f"⚠️  {stderr}")
    
    # Enable GitHub Pages
    print("\n🌐 Aktiviere GitHub Pages...")
    
    exit_code, stdout, stderr = run_cmd("gh api user --jq .login")
    username = stdout.strip()
    
    # Pages via API aktivieren
    pages_config = json.dumps({
        "source": {
            "branch": "main",
            "path": "/"
        }
    })
    
    run_cmd(f"gh api -X POST repos/{username}/eur-cny-tracker/pages -f source[branch]=main -f source[path]=/")
    
    time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ FERTIG!")
    print("=" * 60)
    print(f"\n🌐 Dashboard URL (verfügbar in ~1 Minute):")
    print(f"   https://{username}.github.io/eur-cny-tracker/dashboard.html")
    print(f"\n📦 Repository:")
    print(f"   https://github.com/{username}/eur-cny-tracker")
    print("\n💡 Der Cron-Job wird das Dashboard ab jetzt täglich hochladen!")

if __name__ == "__main__":
    main()
