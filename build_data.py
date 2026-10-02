"""Deterministic synthetic dataset generator.

Writes three raw tables, shaped like what a product would actually log:

- data/customers.csv      account attributes, experiment assignment, revenue and the 8-week
                          retention outcome (as a billing system would record it)
- data/calls.csv          one row per call, generated from each account's lifecycle
                          (signup week, weekly activity, churn)
- data/feature_usage.csv  first-use date per account and feature

Nothing derived is stored here: activity, adoption, health score, churn risk and cohort retention
are all computed from these tables by the backend (and the equivalent dbt models).
Run `python export_static.py` afterwards to refresh the static snapshot in site/data/.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Output root defaults to this repository; an alternative directory can be passed as argv[1].
ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
RAW = ROOT / 'data'
RAW.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(42)
N = 5000
WEEKS = 12
week_starts = pd.date_range('2026-01-05', periods=WEEKS, freq='W-MON')

plans = rng.choice(['Starter','Professional','Business','Enterprise'], size=N, p=[0.32,0.38,0.22,0.08])
industries = rng.choice(['SaaS','Healthcare','E-commerce','Financial Services','Professional Services','Education'], size=N, p=[.27,.15,.15,.15,.14,.14])
sizes = rng.choice(['SMB','Mid-Market','Enterprise'], size=N, p=[.56,.33,.11])
regions = rng.choice(['North America','Europe','APAC','LATAM'], size=N, p=[.54,.25,.13,.08])
experiment = rng.choice(['Control','Treatment'], size=N, p=[.5,.5])
treated = experiment == 'Treatment'
base_propensity = rng.beta(3.2, 3.8, size=N)
plan_mult = pd.Series(plans).map({'Starter':.75,'Professional':1.0,'Business':1.2,'Enterprise':1.4}).to_numpy()
size_mult = pd.Series(sizes).map({'SMB':.82,'Mid-Market':1.08,'Enterprise':1.34}).to_numpy()

# Product adoption: treatment has a real lift, and business/enterprise customers adopt faster.
adopt_prob = np.clip(0.16 + 0.28*base_propensity + 0.06*treated + 0.035*(plans=='Business') + 0.055*(plans=='Enterprise'), .03, .88)
adopted = rng.binomial(1, adopt_prob).astype(bool)
adoption_offset = rng.integers(0, 6, size=N)  # weeks after first activity

# Lifecycle. Accounts that signed up before the window are active from week 0.
signup_date = pd.to_datetime('2025-10-01') + pd.to_timedelta(rng.integers(0, 160, N), unit='D')
start_week = np.clip((signup_date - week_starts[0]).days // 7, 0, WEEKS - 1).to_numpy()
signed_up_in_window = np.asarray(signup_date >= week_starts[0])
retention_prob = np.clip(.40 + .38*base_propensity + .06*adopted + .04*np.isin(plans, ['Business', 'Enterprise'])
                         + rng.normal(0, .05, N), .10, .97)
retained_8w = rng.binomial(1, retention_prob)
churn_week = np.where(retained_8w == 1, WEEKS + 99, start_week + rng.integers(2, 9, size=N))
weekly_active_p = np.clip(.50 + .40*base_propensity + .05*adopted, .30, .97)
calls_per_week = .85 * plan_mult * size_mult * (.55 + base_propensity)
adoption_idx = np.minimum(start_week + adoption_offset, WEEKS - 1)
# An account only adopts if it is still a customer when it reaches its adoption week.
adopted &= adoption_idx < np.minimum(WEEKS, churn_week)

# Per-account call-quality baselines.
aht_base = np.clip(rng.normal(410, 40, N), 220, 650)
resolution_base = np.clip(rng.normal(.73 + .025*(plans=='Enterprise'), .07, N), .35, .97)

revenue = np.select([plans=='Starter', plans=='Professional', plans=='Business', plans=='Enterprise'], [1199, 2999, 7499, 15999])
revenue = np.rint(revenue * rng.lognormal(0, .12, N)).astype(int)
customer_ids = np.array([f'CUST-{i:05d}' for i in range(1, N + 1)])

customers = pd.DataFrame({
    'customer_id': customer_ids,
    'plan': plans,
    'industry': industries,
    'company_size': sizes,
    'region': regions,
    'signup_date': signup_date.date,
    'experiment_group': experiment,
    'annual_revenue': revenue,
    'retained_8w': retained_8w,
})

# Call-level events from each account's lifecycle.
call_types = np.array(['Inbound', 'Outbound', 'Follow-up', 'Support'])
week_labels = np.array([w.date().isoformat() for w in week_starts])
rows = []
for i in range(N):
    end = min(WEEKS, churn_week[i])
    span = np.arange(start_week[i], end)
    active = rng.random(len(span)) < weekly_active_p[i]
    if signed_up_in_window[i]:
        active[0] = True  # a new account's signup week is its first activity
    elif not active.any():
        active[rng.integers(len(span))] = True  # every existing account shows up at least once
    for w in span[active]:
        n = 1 + rng.poisson(calls_per_week[i])
        ai = adopted[i] & (w >= adoption_idx[i]) & (rng.random(n) < .62 + .08*treated[i])
        resolved = rng.random(n) < np.clip(resolution_base[i] + .10*ai, .3, .995)
        escalated = ~resolved & (rng.random(n) < np.where(ai, .10, .16))
        duration = np.maximum(60, rng.normal(aht_base[i] * np.where(ai, .80, 1.0), 45)).astype(int)
        quality = np.clip(rng.normal(4.1 + .45*ai, .35), 1, 5).round(2)
        first_response = np.maximum(0, rng.normal(np.where(ai, 1.8, 3.4), .65)).round(2)
        kinds = rng.choice(call_types, size=n)
        for j in range(n):
            rows.append((customer_ids[i], week_labels[w], kinds[j], int(ai[j]), int(duration[j]), int(resolved[j]),
                         int(escalated[j]), float(quality[j]), float(first_response[j])))
calls = pd.DataFrame(rows, columns=['customer_id','week','call_type','ai_handled','duration_sec','resolved','escalated','quality_score','first_response_min'])
calls.insert(0, 'call_id', [f'CALL-{k:07d}' for k in range(1, len(calls) + 1)])

# Feature usage: first-use date per account and feature, within the account's active span.
first_week = calls.groupby('customer_id')['week'].min()
last_week = calls.groupby('customer_id')['week'].max()
week_index = {w: k for k, w in enumerate(week_labels)}
feature_rows = []
feature_base = {'WhatsApp': .48, 'Analytics': .42, 'Call Routing': .36, 'AI Assist': .20, 'Integrations': .18}
for i in range(N):
    cid = customer_ids[i]
    if adopted[i]:
        feature_rows.append((cid, 'AI Voice Agent', week_labels[adoption_idx[i]]))
    lo, hi = week_index[first_week[cid]], week_index[last_week[cid]]
    for feature, base in feature_base.items():
        p = base + .30*(base_propensity[i] - .45)
        p += .15*adopted[i] if feature == 'AI Assist' else 0
        p += .12*(plans[i] == 'Enterprise') if feature == 'Integrations' else 0
        if rng.random() < np.clip(p, .02, .95):
            feature_rows.append((cid, feature, week_labels[rng.integers(lo, hi + 1)]))
feature_usage = pd.DataFrame(feature_rows, columns=['customer_id', 'feature', 'first_used_week'])

customers.to_csv(RAW / 'customers.csv', index=False)
calls.to_csv(RAW / 'calls.csv', index=False)
feature_usage.to_csv(RAW / 'feature_usage.csv', index=False)

print(f'Generated {len(customers)} customers, {len(calls)} calls, {len(feature_usage)} feature-usage rows in {ROOT}')
print('Next: python export_static.py  (refreshes the static dashboard snapshot)')
