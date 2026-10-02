"""Data-quality checks for the raw tables. Run with `python tests/test_data_quality.py` or `pytest tests/`."""
from pathlib import Path

import pandas as pd
from scipy.stats import chisquare

ROOT = Path(__file__).resolve().parents[1]
c = pd.read_csv(ROOT / 'data/customers.csv')
calls = pd.read_csv(ROOT / 'data/calls.csv')
features = pd.read_csv(ROOT / 'data/feature_usage.csv')
FEATURES = ['AI Voice Agent', 'WhatsApp', 'Analytics', 'Call Routing', 'AI Assist', 'Integrations']


def test_customer_primary_key():
    assert c.customer_id.notna().all()
    assert c.customer_id.is_unique


def test_valid_domains():
    assert c.plan.isin(['Starter', 'Professional', 'Business', 'Enterprise']).all()
    assert c.company_size.isin(['SMB', 'Mid-Market', 'Enterprise']).all()
    assert c.experiment_group.isin(['Control', 'Treatment']).all()
    assert c.retained_8w.isin([0, 1]).all()
    assert (c.annual_revenue > 0).all()


def test_experiment_groups_balanced():
    # Sample-ratio mismatch check against the intended 50/50 split.
    counts = c.experiment_group.value_counts()
    _, p = chisquare(counts.to_numpy())
    assert p > 0.001, f'Sample ratio mismatch: {counts.to_dict()} (p={p:.2g})'


def test_calls_reference_customers():
    assert calls.call_id.is_unique
    assert calls.customer_id.isin(c.customer_id).all()
    assert calls[['ai_handled', 'resolved', 'escalated']].isin([0, 1]).all().all()
    assert not (calls.escalated.astype(bool) & calls.resolved.astype(bool)).any(), 'resolved calls cannot escalate'
    assert calls.quality_score.between(1, 5).all()
    assert (calls.duration_sec > 0).all()


def test_every_customer_has_activity():
    assert set(calls.customer_id) == set(c.customer_id)


def test_no_activity_before_signup():
    first = calls.groupby('customer_id').week.min().rename('first_week').reset_index().merge(c, on='customer_id')
    signup_monday = pd.to_datetime(first.signup_date).dt.to_period('W-SUN').dt.start_time
    assert (pd.to_datetime(first.first_week) >= signup_monday).all()


def test_feature_usage_valid():
    assert features.customer_id.isin(c.customer_id).all()
    assert features.feature.isin(FEATURES).all()
    assert not features.duplicated(['customer_id', 'feature']).any()
    assert features.first_used_week.isin(calls.week.unique()).all()


def test_ai_calls_only_after_adoption():
    adopted = features[features.feature == 'AI Voice Agent'].set_index('customer_id').first_used_week
    ai_calls = calls[calls.ai_handled == 1]
    assert ai_calls.customer_id.isin(adopted.index).all(), 'AI-handled calls require AI Voice Agent adoption'
    assert (ai_calls.week >= ai_calls.customer_id.map(adopted)).all()


if __name__ == '__main__':
    for name, check in list(globals().items()):
        if name.startswith('test_'):
            check()
            print(f'PASS {name}')
    print('All data quality checks passed.')
