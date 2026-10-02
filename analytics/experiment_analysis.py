from pathlib import Path
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest, proportion_confint

ROOT = Path(__file__).resolve().parents[1]
customers = pd.read_csv(ROOT / 'data' / 'customers.csv')
features = pd.read_csv(ROOT / 'data' / 'feature_usage.csv')
# Primary metric: the account turned on the AI Voice Agent (a feature-usage event).
adopters = features.loc[features.feature == 'AI Voice Agent', 'customer_id']
customers['ai_adopted'] = customers.customer_id.isin(adopters).astype(int)

g = customers.groupby('experiment_group').agg(
    customers=('customer_id','count'),
    adopters=('ai_adopted','sum'),
    retention=('retained_8w','mean'),
).loc[['Control','Treatment']]

counts = g['adopters'].to_numpy()
nobs = g['customers'].to_numpy()
# (treatment, control) order so a positive z means treatment > control, matching the API.
z_stat, p_value = proportions_ztest(counts[::-1], nobs[::-1])

control_rate = counts[0] / nobs[0]
treatment_rate = counts[1] / nobs[1]
absolute_lift = treatment_rate - control_rate
relative_lift = absolute_lift / control_rate

ci_ctrl = proportion_confint(counts[0], nobs[0], method='wilson')
ci_treat = proportion_confint(counts[1], nobs[1], method='wilson')

print('=== VoiceIQ A/B experiment ===')
print(g)
print(f'Control adoption:   {control_rate:.3%}')
print(f'Treatment adoption: {treatment_rate:.3%}')
print(f'Absolute lift:      {absolute_lift:.3%}')
print(f'Relative lift:      {relative_lift:.2%}')
print(f'z statistic:        {z_stat:.3f}')
print(f'p-value:            {p_value:.6g}')
print(f'Control 95% CI:     [{ci_ctrl[0]:.3%}, {ci_ctrl[1]:.3%}]')
print(f'Treatment 95% CI:   [{ci_treat[0]:.3%}, {ci_treat[1]:.3%}]')
print('\nInterpretation: report the effect size and uncertainty, then validate heterogeneity and downstream retention before scaling a product change.')
