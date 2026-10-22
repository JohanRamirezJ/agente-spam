"""Download the confirmed feedback of a running server into a dated JSON file (run it from cron / Task Scheduler).

    python scripts/backup_feedback.py https://tu-servidor.example.com backups/
Reads the optional admin token from the ADMIN_TOKEN environment variable. Restore with the «Importar confirmaciones»
button of the Aprendizaje tab, or POST the file to /feedback/import.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "backups")
    out.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(base + "/feedback/export")
    if os.environ.get("ADMIN_TOKEN"):
        req.add_header("X-Admin-Token", os.environ["ADMIN_TOKEN"])
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    path = out / f"confirmaciones-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(data['items'])} confirmaciones guardadas en {path}")


if __name__ == "__main__":
    main()
