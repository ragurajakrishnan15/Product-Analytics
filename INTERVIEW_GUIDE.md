# Interview talking points

### 1. What business problem did you solve?
I built an analytics workflow for an AI-powered customer communications product to understand feature adoption, retention, customer health, and whether an AI Voice Agent changes user behavior.

### 2. Why did you choose A/B testing?
The product question was causal: not only whether treatment users behaved differently, but whether exposure to the new AI feature could plausibly drive a change in adoption. That is why I defined a primary metric and used a randomized treatment/control framing with an explicit statistical test.

### 3. What was the primary experiment metric?
Customer-level AI adoption. I also inspected downstream retention and health as secondary signals so a higher click/adoption rate would not be treated as proof of business value by itself.

### 4. Why a proportion test?
The primary outcome is binary at the customer level: adopted vs. did not adopt. Comparing two independent proportions is appropriate for that metric. In production I would also validate randomization, sample-ratio mismatch, exposure rules, and the pre-specified analysis window.

### 5. What does the p-value tell you?
It measures how inconsistent the observed result would be with the null hypothesis under the assumptions of the test. It does not tell me the probability that the product change is successful, the size of the business impact, or whether the result will replicate.

### 6. How did you define customer health?
I used an explainable score combining retention tendency, usage intensity, feature breadth, resolution quality, AI adoption, and active weeks. The point is prioritization and diagnosis, not claiming the score is a ground-truth churn model.

### 7. Why use synthetic data?
The project is a public portfolio artifact, so synthetic data avoids exposing customer or company information. I designed the data-generating process so the analysis demonstrates realistic product questions while remaining reproducible.

### 8. What would you do in production?
I would replace synthetic ingestion with warehouse event tables, add dbt lineage and tests, validate experiment assignment, establish metric definitions in a semantic layer, and monitor freshness, completeness, and distribution drift.

### 9. What surprised you?
The treatment effect is strongest when the analysis is split by customer segment rather than viewed only at the aggregate level. That is a cue to investigate heterogeneity and onboarding context before generalizing the same product motion to every account.

### 10. What would you build next?
I would connect AI quality metrics to renewal/expansion outcomes, test onboarding interventions, add power calculations before launching experiments, and formalize a semantic layer for self-serve product analytics.
