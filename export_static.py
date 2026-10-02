"""Write the static dashboard snapshot in site/data/ from the same code that powers the API.

Runs in-process (no server needed):  python export_static.py
"""
import csv
import json
from pathlib import Path

from backend.main import customers_payload, dashboard_payload, init_db

OUT = Path(__file__).resolve().parent / 'site' / 'data'
OUT.mkdir(parents=True, exist_ok=True)


def write_csv(path, rows, fields):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


init_db()
dashboard = dashboard_payload()
customers = customers_payload(limit=5000)

# Human-readable artifacts for inspection.
(OUT / 'dashboard.json').write_text(json.dumps(dashboard, indent=2), encoding='utf-8')
(OUT / 'experiment.json').write_text(json.dumps(dashboard['experiment'], indent=2), encoding='utf-8')
write_csv(OUT / 'weekly.csv', dashboard['weekly'], ['week', 'active_customers', 'calls', 'ai_handling_share', 'ai_adoption_rate'])
write_csv(OUT / 'features.csv', dashboard['features'], ['feature', 'adoption_rate'])
write_csv(OUT / 'cohorts.csv', dashboard['cohorts'], ['cohort', 'customers'] + [f'W{k}' for k in range(8)])

# The page loads this as a <script>, which (unlike fetch) also works when index.html is opened from disk.
snapshot = json.dumps({'dashboard': dashboard, 'customers': customers}, separators=(',', ':'))
(OUT / 'snapshot.js').write_text(f'window.VOICEIQ_SNAPSHOT={snapshot};\n', encoding='utf-8')

print(f"Exported snapshot: {len(customers)} customers, {dashboard['kpis']['calls']} calls -> {OUT}")
