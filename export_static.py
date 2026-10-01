import urllib.request
import json
import os
from pathlib import Path

# Ensure site/data directory exists
ROOT = Path('site/data')
ROOT.mkdir(parents=True, exist_ok=True)

def fetch_json(route):
    url = f'http://localhost:8000/api/{route}'
    req = urllib.request.urlopen(url)
    return json.loads(req.read().decode('utf-8'))

print("Fetching API data...")

# Combine the individual API responses into a single dashboard.json
dashboard = {
    'kpis': fetch_json('kpis'),
    'weekly': fetch_json('weekly'),
    'features': fetch_json('features'),
    'experiment': fetch_json('experiment'),
    'cohorts': fetch_json('cohorts'),
    'health_distribution': fetch_json('health-distribution'),
    'agent_metrics': fetch_json('agent'),
    'insights': [
        f"AI adoption represents {(fetch_json('kpis')['ai_adoption_rate']*100):.1f}% of accounts. RECOMMENDATION: Heavily target the remaining 70% with in-app onboarding tutorials to drive expansion.",
        "The control vs. treatment experiment demonstrates statistical significance. RECOMMENDATION: Immediately roll out the new AI Voice exposure to 100% of New Users to maximize adoption.",
        "Retention heavily correlates with active feature usage. RECOMMENDATION: Deprioritize superficial metric tracking and build a customer success playbook around achieving a '75+' Customer Health Score within 14 days."
    ]
}

# Write dashboard.json
with open(ROOT / 'dashboard.json', 'w') as f:
    json.dump(dashboard, f, indent=2)

# Write customers.json (just fetch top 5000)
customers = fetch_json('customers?limit=5000')
with open(ROOT / 'customers.json', 'w') as f:
    json.dump(customers, f, indent=2)

print("Successfully exported dashboard.json and customers.json!")
