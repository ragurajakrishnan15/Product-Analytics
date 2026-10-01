from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_confint

ROOT = Path('/mnt/data/aircall-product-analytics')
DATA = ROOT / 'site' / 'data'
DATA.mkdir(parents=True, exist_ok=True)
RAW = ROOT / 'data'
RAW.mkdir(exist_ok=True)

rng = np.random.default_rng(42)
N = 5000
WEEKS = 12
week_starts = pd.date_range('2026-01-05', periods=WEEKS, freq='W-MON')

plans = rng.choice(['Starter','Professional','Business','Enterprise'], size=N, p=[0.32,0.38,0.22,0.08])
industries = rng.choice(['SaaS','Healthcare','E-commerce','Financial Services','Professional Services','Education'], size=N, p=[.27,.15,.15,.15,.14,.14])
sizes = rng.choice(['SMB','Mid-Market','Enterprise'], size=N, p=[.56,.33,.11])
regions = rng.choice(['North America','Europe','APAC','LATAM'], size=N, p=[.54,.25,.13,.08])
experiment = rng.choice(['Control','Treatment'], size=N, p=[.5,.5])
base_propensity = rng.beta(3.2, 3.8, size=N)
plan_mult = pd.Series(plans).map({'Starter':.75,'Professional':1.0,'Business':1.2,'Enterprise':1.4}).to_numpy()
size_mult = pd.Series(sizes).map({'SMB':.82,'Mid-Market':1.08,'Enterprise':1.34}).to_numpy()

# Product adoption: treatment has a real lift, and business/enterprise customers adopt faster.
adopt_prob = np.clip(0.16 + 0.28*base_propensity + 0.06*(experiment=='Treatment') + 0.035*(plans=='Business') + 0.055*(plans=='Enterprise'), .03, .88)
ai_adopted = rng.binomial(1, adopt_prob)
# force more visible treatment effect in downstream behavior
adopted = ai_adopted.astype(bool)
adoption_week = np.where(adopted, rng.integers(1, 10, size=N), 0)

base_calls = np.maximum(3, rng.poisson(12 * plan_mult * size_mult * (.55 + base_propensity), size=N))
activity_noise = rng.lognormal(0, .22, size=N)
calls_12w = np.maximum(1, np.rint(base_calls * activity_noise)).astype(int)

ai_call_share = np.clip(0.10 + .55*adopted + .08*(experiment=='Treatment')*adopted + rng.normal(0,.06,size=N), 0, .95)
ai_calls = np.minimum(calls_12w, rng.binomial(calls_12w, ai_call_share))

aht = np.clip(rng.normal(410 - 75*ai_calls/(calls_12w+1), 55, size=N), 155, 720)
resolution_rate = np.clip(rng.normal(.73 + .08*adopted + .025*(plans=='Enterprise'), .08, size=N), .35, .98)
escalation_rate = np.clip(.16 - .07*adopted + rng.normal(0,.025,N), .02, .35)
feature_count = np.clip(np.rint(1 + 5*base_propensity + 1.2*adopted + rng.normal(0,.9,N)),1,10).astype(int)
active_weeks = np.clip(np.rint(2 + 7*base_propensity + 1.1*adopted + rng.normal(0,1.4,N)),1,12).astype(int)
retention_score = np.clip(.35 + .045*active_weeks + .055*adopted + .035*(calls_12w>120) + rng.normal(0,.07,N), .12,.99)
retained_8w = rng.binomial(1, retention_score)
churn_risk = np.clip(1 - retention_score + rng.normal(0,.05,N), .01,.98)
health_score = np.clip(100*(.45*retention_score + .18*np.minimum(calls_12w/140,1) + .15*resolution_rate + .12*(ai_adopted) + .10*(active_weeks/12)), 15, 99)
revenue = np.select([np.array(plans)=='Starter', np.array(plans)=='Professional', np.array(plans)=='Business', np.array(plans)=='Enterprise'], [1199,2999,7499,15999])
revenue = np.rint(revenue * rng.lognormal(0,.12,N)).astype(int)

customers = pd.DataFrame({
    'customer_id':[f'CUST-{i:05d}' for i in range(1,N+1)],
    'plan':plans,
    'industry':industries,
    'company_size':sizes,
    'region':regions,
    'signup_date':pd.to_datetime('2025-10-01') + pd.to_timedelta(rng.integers(0,160,N), unit='D'),
    'experiment_group':experiment,
    'ai_adopted':ai_adopted,
    'adoption_week':adoption_week,
    'calls_12w':calls_12w,
    'ai_calls_12w':ai_calls,
    'avg_handle_time_sec':np.rint(aht).astype(int),
    'resolution_rate':np.round(resolution_rate,4),
    'escalation_rate':np.round(escalation_rate,4),
    'feature_count':feature_count,
    'active_weeks':active_weeks,
    'retained_8w':retained_8w,
    'churn_risk':np.round(churn_risk,4),
    'health_score':np.rint(health_score).astype(int),
    'annual_revenue':revenue,
})

# Call-level events: ~100k rows, with realistic AI handling/quality/resolution.
rows=[]
call_id=1
call_types=['Inbound','Outbound','Follow-up','Support']
for idx,row in customers.iterrows():
    n=int(row.calls_12w)
    weights=np.ones(WEEKS)/WEEKS
    selected_weeks=rng.choice(WEEKS, size=n, p=weights)
    for w in selected_weeks:
        ai = rng.random() < (0.02 + 0.60*row.ai_adopted + 0.08*(row.experiment_group=='Treatment')*row.ai_adopted)
        duration=max(60, int(rng.normal(row.avg_handle_time_sec*(.88 if ai else 1), 45)))
        resolved=rng.random() < np.clip(row.resolution_rate + (.04 if ai else 0), .3,.995)
        escalated=(not resolved) and (rng.random() < row.escalation_rate)
        quality=np.clip(rng.normal(4.1 + (.45 if ai else 0), .35),1,5)
        rows.append((f'CALL-{call_id:07d}', row.customer_id, week_starts[w].date().isoformat(), rng.choice(call_types), int(ai), duration, int(resolved), int(escalated), round(float(quality),2), round(float(max(0,rng.normal(1.8 if ai else 3.4,.65))),2)))
        call_id += 1
calls=pd.DataFrame(rows, columns=['call_id','customer_id','week','call_type','ai_handled','duration_sec','resolved','escalated','quality_score','first_response_min'])

# Week-level product metrics for trend charts.
week_rows=[]
for i,w in enumerate(week_starts):
    # steady product growth with a stronger later-stage adoption curve
    cohort = customers.copy()
    active_prob=np.clip(.52 + .018*i + .02*(cohort.ai_adopted) + rng.normal(0,.02,N), .2,.95)
    active=int(rng.binomial(N, np.mean(active_prob)))
    adoption=np.clip(.235 + .015*i + .008*(cohort.experiment_group=='Treatment').mean()*i, 0,.85)
    week_rows.append({'week':w.strftime('%b %d'),'active_customers':active,'ai_adoption_rate':round(adoption,4),'avg_calls_per_active':round(float(calls[calls.week==w.date().isoformat()].shape[0]/max(active,1)),2)})
weekly=pd.DataFrame(week_rows)

# Feature adoption summary
features=['AI Voice Agent','AI Assist','WhatsApp','Analytics','Call Recording','Power Dialer']
feature_rates=[.384,.272,.511,.618,.744,.429]
feature_df=pd.DataFrame({'feature':features,'adoption_rate':feature_rates})

# Cohort retention by signup month
customers['signup_month']=customers['signup_date'].dt.to_period('M').astype(str)
cohort_sizes=customers.groupby('signup_month').size()
cohort_order=sorted(cohort_sizes.index)[-6:]
cohort_rows=[]
retention_curve=[1.00,.89,.82,.77,.73,.69,.66,.64]
for c in cohort_order:
    adj=(customers.loc[customers.signup_month==c,'health_score'].mean()-60)/1000
    vals=[max(.35, min(.98, x+adj + rng.normal(0,.01))) for x in retention_curve]
    cohort_rows.append([c]+[round(v,3) for v in vals])
cohort_df=pd.DataFrame(cohort_rows, columns=['cohort','W0','W1','W2','W3','W4','W5','W6','W7'])

# Experiment analysis on AI adoption and retention outcomes
exp=customers.groupby('experiment_group').agg(customers=('customer_id','count'), ai_adopted=('ai_adopted','sum'), retained_8w=('retained_8w','sum'), avg_calls=('calls_12w','mean'), avg_health=('health_score','mean')).reset_index()
count=np.array(exp['ai_adopted'])
nobs=np.array(exp['customers'])
z,p=proportions_ztest(count,nobs)
# Map by group for consistent order
ctrl=exp[exp.experiment_group=='Control'].iloc[0]
treat=exp[exp.experiment_group=='Treatment'].iloc[0]
ctrl_rate=ctrl.ai_adopted/ctrl.customers
treat_rate=treat.ai_adopted/treat.customers
abs_lift=treat_rate-ctrl_rate
rel_lift=abs_lift/ctrl_rate
ci_low,ci_high=proportion_confint(treat.ai_adopted,treat.customers,method='wilson')
# treatment vs control difference CI using normal approx
se=math.sqrt(ctrl_rate*(1-ctrl_rate)/ctrl.customers + treat_rate*(1-treat_rate)/treat.customers)
diff_ci=(abs_lift-1.96*se,abs_lift+1.96*se)

# Experiment by segment
seg=customers.groupby(['company_size','experiment_group']).agg(customers=('customer_id','count'),adopters=('ai_adopted','sum'),retained=('retained_8w','sum')).reset_index()
seg_rows=[]
for size in ['SMB','Mid-Market','Enterprise']:
    s=seg[seg.company_size==size].set_index('experiment_group')
    cr=s.loc['Control','adopters']/s.loc['Control','customers']
    tr=s.loc['Treatment','adopters']/s.loc['Treatment','customers']
    seg_rows.append({'segment':size,'control_adoption':round(cr,4),'treatment_adoption':round(tr,4),'relative_lift':round((tr-cr)/cr,4),'customers':int(s['customers'].sum())})
segment_experiment=pd.DataFrame(seg_rows)

# AI agent performance
ai_calls=calls[calls.ai_handled==1]
agent_metrics={
    'ai_calls':int(len(ai_calls)),
    'resolution_rate':round(float(ai_calls.resolved.mean()),4),
    'escalation_rate':round(float(ai_calls.escalated.mean()),4),
    'avg_handle_time_sec':round(float(ai_calls.duration_sec.mean()),1),
    'avg_quality_score':round(float(ai_calls.quality_score.mean()),2),
    'avg_first_response_min':round(float(ai_calls.first_response_min.mean()),2),
}

# Customer health distribution and top opportunities
health_bins=pd.cut(customers.health_score,[0,39,59,74,89,100],labels=['Critical','At Risk','Watch','Healthy','Excellent'],include_lowest=True)
health_dist=health_bins.value_counts().reindex(['Critical','At Risk','Watch','Healthy','Excellent']).fillna(0).astype(int)
opp=customers.sort_values(['churn_risk','annual_revenue'],ascending=[False,False]).head(20)

# Executive insights, generated from actual calculations
insights=[
    f"Treatment AI adoption is {treat_rate:.1%} vs {ctrl_rate:.1%} for control, a {rel_lift:.1%} relative lift (z-test p={p:.3g}).",
    f"AI-handled calls resolve at {agent_metrics['resolution_rate']:.1%} with an average quality score of {agent_metrics['avg_quality_score']:.2f}/5.",
    f"{health_dist.loc['At Risk'] + health_dist.loc['Critical']:,} customers fall into Critical or At Risk health bands, creating a focused retention opportunity.",
]

summary={
    'generated_at':'2026-10-01',
    'dataset':{'customers':N,'calls':int(len(calls)),'weeks':WEEKS},
    'kpis':{
        'customers':N,
        'calls':int(len(calls)),
        'ai_adoption_rate':round(float(customers.ai_adopted.mean()),4),
        'retention_8w':round(float(customers.retained_8w.mean()),4),
        'avg_health':round(float(customers.health_score.mean()),1),
        'annual_revenue':int(customers.annual_revenue.sum()),
    },
    'weekly':weekly.to_dict(orient='records'),
    'features':feature_df.to_dict(orient='records'),
    'cohorts':cohort_df.to_dict(orient='records'),
    'experiment':{
        'control':{'n':int(ctrl.customers),'adopters':int(ctrl.ai_adopted),'rate':round(float(ctrl_rate),4)},
        'treatment':{'n':int(treat.customers),'adopters':int(treat.ai_adopted),'rate':round(float(treat_rate),4)},
        'absolute_lift':round(float(abs_lift),4),
        'relative_lift':round(float(rel_lift),4),
        'p_value':float(p),
        'z_stat':float(z),
        'difference_ci':{'low':round(float(diff_ci[0]),4),'high':round(float(diff_ci[1]),4)},
        'treatment_rate_ci':{'low':round(float(ci_low),4),'high':round(float(ci_high),4)},
        'segments':segment_experiment.to_dict(orient='records'),
    },
    'agent_metrics':agent_metrics,
    'health_distribution':[{'band':k,'customers':int(v)} for k,v in health_dist.items()],
    'insights':insights,
    'top_opportunities':opp[['customer_id','plan','company_size','annual_revenue','health_score','churn_risk','ai_adopted','calls_12w']].to_dict(orient='records'),
}

# Save raw data (small enough for portfolio repo)
customers.to_csv(RAW/'customers.csv',index=False)
calls.to_csv(RAW/'calls.csv',index=False)

# Save browser data
(DATA/'dashboard.json').write_text(json.dumps(summary,indent=2,default=str))
customers[['customer_id','plan','industry','company_size','region','experiment_group','ai_adopted','calls_12w','ai_calls_12w','resolution_rate','health_score','churn_risk','annual_revenue']].to_json(DATA/'customers.json',orient='records')

# Save compact CSVs useful in browser and for inspection
weekly.to_csv(DATA/'weekly.csv',index=False)
feature_df.to_csv(DATA/'features.csv',index=False)
cohort_df.to_csv(DATA/'cohorts.csv',index=False)

# Save experiment results as a machine-readable artifact
(Path(DATA/'experiment.json')).write_text(json.dumps(summary['experiment'],indent=2))

print('Generated', len(customers), 'customers and', len(calls), 'calls')
print('Control adoption', ctrl_rate, 'Treatment', treat_rate, 'relative lift', rel_lift, 'p', p)
