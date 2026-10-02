# Interview talking points

### 1. What business problem did you solve?
I built an analytics workflow for an AI-powered customer communications product to understand feature adoption, retention, customer health, and whether an AI Voice Agent changes user behavior.

### 2. Why did you choose A/B testing?
The product question was causal: not only whether treatment users behaved differently, but whether exposure to the new AI feature could plausibly drive a change in adoption. That is why I defined a primary metric and used a randomized treatment/control framing with an explicit statistical test.

### 3. What was the primary experiment metric?
Customer-level AI adoption: whether the account turned on the AI Voice Agent. I pre-defined 8-week retention as a guardrail so a higher adoption rate would not be treated as proof of business value by itself. Treatment lifted adoption from 27.3% to 33.3% (95% CI +3.5 to +8.5 pp); retention moved +1.6 pp but that was not significant.

### 4. Why a proportion test?
The primary outcome is binary at the customer level: adopted vs. did not adopt. Comparing two independent proportions is appropriate for that metric. In production I would also validate randomization, sample-ratio mismatch, exposure rules, and the pre-specified analysis window.

### 5. What does the p-value tell you?
It measures how inconsistent the observed result would be with the null hypothesis under the assumptions of the test. It does not tell me the probability that the product change is successful, the size of the business impact, or whether the result will replicate.

### 6. How did you define customer health?
It is computed in SQL from raw events only: 35% engagement (active weeks over weeks observable), 20% call intensity, 15% feature breadth, 15% resolution rate, 10% AI adoption, 5% recency. I validated it against the outcome: 2% of Critical accounts are retained at 8 weeks vs 93% of Advocates. Separately, a logistic-regression churn model ranks accounts; recency and share of weeks active are its strongest drivers. Its holdout AUC (0.93) is inflated because features and outcome share one window, which I would fix in production by scoring at a cutoff date.

### 7. Why use synthetic data?
The project is a public portfolio artifact, so synthetic data avoids exposing customer or company information. I designed the data-generating process so the analysis demonstrates realistic product questions while remaining reproducible.

### 8. What would you do in production?
I would replace synthetic ingestion with warehouse event tables, add dbt lineage and tests, validate experiment assignment, establish metric definitions in a semantic layer, and monitor freshness, completeness, and distribution drift.

### 9. What surprised you?
The aggregate lift (+22% relative) is significant in SMB and Mid-Market, but Enterprise is inconclusive: n = 534 gives a CI of -9.6 to +6.0 pp and a minimum detectable effect of about 11 pp. The right reading is 'we cannot tell', not 'it does not work there'. I would ramp in stages and size a follow-up test for Enterprise rather than claim harm or roll out to 100%.

### 10. What would you build next?
I would connect AI quality metrics to renewal/expansion outcomes, test onboarding interventions, add power calculations before launching experiments, and formalize a semantic layer for self-serve product analytics.
