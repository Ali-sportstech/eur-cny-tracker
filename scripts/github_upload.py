#!/usr/bin/env python3
"""
GitHub Auto-Upload Script
Pusht Dashboard automatisch nach jedem Scraping
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

TRACKER_DIR = Path.home() / ".hermes/eur-cny-tracker"

def run_cmd(cmd):
    """Führt Command aus"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=TRACKER_DIR)
    return result.returncode, result.stdout, result.stderr

def main():
    print("🚀 GitHub Auto-Upload...")
    
    # Git Status
    exit_code, stdout, stderr = run_cmd("git status --porcelain")
    
    if not stdout.strip():
        print("✅ Keine Änderungen - Skip Upload")
        return
    
    print(f"📝 Änderungen gefunden:\n{stdout}")
    
    # Add all changes
    run_cmd("git add dashboard.html data/")
    
    # Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    exit_code, stdout, stderr = run_cmd(f'git commit -m "Auto-update: {timestamp}"')
    
    if exit_code != 0:
        print(f"⚠️  Commit fehlgeschlagen: {stderr}")
        return
    
    # Push
    print("📤 Pushe zu GitHub...")
    exit_code, stdout, stderr = run_cmd("git push origin main")
    
    if exit_code == 0:
        print("✅ Dashboard erfolgreich hochgeladen!")
        print("\n🌐 Live URL:")
        print("   https://ali-sportstech.github.io/eur-cny-tracker/dashboard.html")
    else:
        print(f"❌ Push fehlgeschlagen: {stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
