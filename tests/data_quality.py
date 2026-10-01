from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
c = pd.read_csv(ROOT/'data/customers.csv')
assert c.customer_id.is_unique
assert c.customer_id.notna().all()
assert c.plan.isin(['Starter','Professional','Business','Enterprise']).all()
assert c.experiment_group.isin(['Control','Treatment']).all()
assert c.ai_adopted.isin([0,1]).all()
assert c.retained_8w.isin([0,1]).all()
assert c.health_score.between(0,100).all()
assert c.churn_risk.between(0,1).all()
assert c.resolution_rate.between(0,1).all()
print('All data quality checks passed.')
