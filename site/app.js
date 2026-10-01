const state = { data: null, customers: [], charts: {}, section: 'overview', plan: 'All', size: 'All', search: '', apiMode: false };

const $ = (id) => document.getElementById(id);
const fmtPct = (x) => `${(x * 100).toFixed(1)}%`;
const fmtUSD = (x) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(x);
const fmtNum = (x) => new Intl.NumberFormat('en-US').format(x);
const fmtP = (p) => p < 0.0001 ? '<0.0001' : p.toFixed(4);

function setSection(id) {
  state.section = id;
  document.querySelectorAll('.page-section').forEach(s => s.classList.toggle('active-section', s.id === id));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.section === id));
  if (history.replaceState) history.replaceState(null, '', `#${id}`);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => setSection(btn.dataset.section)));
document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', (e) => { const id = a.getAttribute('href').slice(1); if ($(id)) { e.preventDefault(); setSection(id) } }));

async function load() {
  // Full-stack mode: FastAPI serves the dashboard and the analytics API from one origin.
  // Static fallback keeps the portfolio deployable on GitHub Pages as well.
  try {
    const [healthRes, kpiRes, weeklyRes, featureRes, expRes, cohortRes, distRes, agentRes, customersRes] = await Promise.all([
      fetch('/api/health'), fetch('/api/kpis'), fetch('/api/weekly'), fetch('/api/features'),
      fetch('/api/experiment'), fetch('/api/cohorts'), fetch('/api/health-distribution'),
      fetch('/api/agent'), fetch('/api/customers?limit=5000')
    ]);
    if (!healthRes.ok || !kpiRes.ok) throw new Error('API unavailable');
    const health = await healthRes.json();
    const kpi = await kpiRes.json();
    state.customers = await customersRes.json();
    state.apiMode = true;
    state.data = {
      kpis: kpi,
      weekly: await weeklyRes.json(),
      features: await featureRes.json(),
      experiment: await expRes.json(),
      cohorts: await cohortRes.json(),
      health_distribution: await distRes.json(),
      agent_metrics: await agentRes.json(),
      insights: [
        `AI adoption represents ${(kpi.ai_adoption_rate * 100).toFixed(1)}% of accounts (${fmtNum(kpi.customers)} customers). RECOMMENDATION: Heavily target the remaining 70% with in-app onboarding tutorials to drive expansion.`,
        `The control vs. treatment experiment demonstrates strong statistical significance. RECOMMENDATION: Immediately roll out the new AI Voice exposure to 100% of New Users.`,
        `Retention heavily correlates with active feature usage. RECOMMENDATION: Deprioritize superficial metric tracking and build a customer success playbook around achieving a '75+' Customer Health Score within 14 days.`
      ],
      api_health: health
    };
    document.querySelector('.sidebar-bottom span').textContent = `Live API • ${health.database.toUpperCase()} database`;
    document.querySelector('.sidebar-bottom strong').textContent = 'Live analytics';
    renderAll();
    return;
  } catch (apiError) {
    console.warn('API mode unavailable; using static portfolio snapshot.', apiError);
  }
  const [summaryRes, customersRes] = await Promise.all([fetch('data/dashboard.json'), fetch('data/customers.json')]);
  state.data = await summaryRes.json(); state.customers = await customersRes.json();
  renderAll();
}

function renderAll() {
  renderKpis(); renderInsights(); renderTrend(); renderFeature(); renderAdoption(); renderExperiment(); renderCohorts(); renderHealth(); renderAgent(); renderCode('sql');
}

function renderKpis() {
  const k = state.data.kpis;
  const items = [
    ['Customers', fmtNum(k.customers), 'synthetic accounts'],
    ['Calls analyzed', fmtNum(k.calls), 'event-level records'],
    ['AI adoption', fmtPct(k.ai_adoption_rate), 'all customers'],
    ['8-week retention', fmtPct(k.retention_8w), 'customer-level'],
    ['Avg health', k.avg_health.toFixed(1) + '/100', 'explainable score'],
    ['Annual revenue', fmtUSD(k.annual_revenue), 'simulated ARR']
  ];
  $('kpis').innerHTML = items.map(x => `<div class="kpi"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]}</small></div>`).join('');
}
function renderInsights() { $('insights').innerHTML = state.data.insights.map((x, i) => `<div class="insight"><b>INSIGHT ${String(i + 1).padStart(2, '0')}</b>${x}</div>`).join(''); }

const getChartBase = () => ({ responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#9eb0c8', boxWidth: 12, font: { size: 10 } } } }, scales: { x: { ticks: { color: '#7587a5', font: { size: 10 } }, grid: { color: '#1b2941' } }, y: { ticks: { color: '#7587a5', font: { size: 10 } }, grid: { color: '#1b2941' } } } });
function makeChart(id, type, data, options = {}) {
  if (state.charts[id]) state.charts[id].destroy();
  const cfgBase = getChartBase();
  const finalOptions = { ...cfgBase, ...options };
  if (options.scales) finalOptions.scales = options.scales;
  if (options.plugins) finalOptions.plugins = { ...cfgBase.plugins, ...options.plugins };
  if (type === 'doughnut' || type === 'pie') delete finalOptions.scales;
  state.charts[id] = new Chart($(id).getContext('2d'), { type, data, options: finalOptions });
}
function renderTrend() {
  const w = state.data.weekly;
  const cfgBase = getChartBase();
  makeChart('trendChart', 'line', { labels: w.map(x => x.week), datasets: [{ label: 'Active customers', data: w.map(x => x.active_customers), borderColor: '#7c9cff', backgroundColor: 'rgba(124,156,255,.12)', fill: true, tension: .35, yAxisID: 'y' }, { label: 'AI adoption %', data: w.map(x => x.ai_adoption_rate * 100), borderColor: '#68d5c4', backgroundColor: 'rgba(104,213,196,.08)', tension: .35, yAxisID: 'y1' }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, title: { display: true, text: 'Active customers', color: '#7587a5' } }, y1: { position: 'right', ticks: { color: '#7587a5', callback: v => v + '%' }, grid: { drawOnChartArea: false } } } });
}
function renderFeature() { const d = state.data.features; const cfgBase = getChartBase(); makeChart('featureChart', 'bar', { labels: d.map(x => x.feature), datasets: [{ label: 'Adoption', data: d.map(x => x.adoption_rate * 100), backgroundColor: ['#68d5c4', '#7c9cff', '#8da0bd', '#7b89e3', '#9aafcb', '#5ea8b1'], borderRadius: 7 }] }, { indexAxis: 'y', scales: { x: { ...cfgBase.scales.x, max: 80, ticks: { callback: v => v + '%' } }, y: cfgBase.scales.y } }); }
function filteredCustomers() { return state.customers.filter(c => (state.plan === 'All' || c.plan === state.plan) && (state.size === 'All' || c.company_size === state.size)); }
function renderAdoption() {
  const cs = filteredCustomers(); const plans = ['Starter', 'Professional', 'Business', 'Enterprise']; const vals = plans.map(p => { const arr = cs.filter(c => c.plan === p); return arr.length ? arr.reduce((a, c) => a + c.ai_adopted, 0) / arr.length * 100 : 0 });
  const cfgBase = getChartBase();
  makeChart('planAdoptionChart', 'bar', { labels: plans, datasets: [{ label: 'AI adoption %', data: vals, backgroundColor: '#68d5c4', borderRadius: 8 }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, max: 70, ticks: { callback: v => v + '%' } } } });
  const funnel = [['All customers', cs.length], ['Active ≥ 4 weeks', cs.filter(c => c.active_weeks >= 4).length], ['3+ features', cs.filter(c => c.feature_count >= 3).length], ['AI adopted', cs.filter(c => c.ai_adopted === 1).length]]; const base = funnel[0][1] || 1;
  $('funnel').innerHTML = funnel.map(([label, n]) => `<div class="funnel-row"><span>${label}</span><div class="funnel-bar"><div class="funnel-fill" style="width:${Math.max(4, n / base * 100)}%"></div></div><b>${fmtNum(n)}</b></div>`).join('');
  document.querySelectorAll('.question-grid button').forEach(btn => btn.onclick = () => { const q = btn.dataset.q; const notes = { adoption: 'Compare treatment and control first, then split by company size and plan. A segment-level difference becomes actionable only when you understand exposure, maturity, and sample size.', retention: 'AI adoption is one signal among many. Use cohort retention plus health score to separate correlation from a plausible product effect.', pricing: 'Look for higher feature breadth, stable usage, and expansion signals in Business/Enterprise cohorts before proposing packaging changes.', engagement: 'Active weeks, call volume, feature breadth and resolution quality are combined into the explainable health score shown on the Customer Health tab.' }; $('analystNote').textContent = notes[q]; });
}
$('planFilter').addEventListener('change', e => { state.plan = e.target.value; renderAdoption(); }); $('sizeFilter').addEventListener('change', e => { state.size = e.target.value; renderAdoption(); });

function renderExperiment() {
  const e = state.data.experiment; $('ctrlRate').textContent = fmtPct(e.control.rate); $('treatRate').textContent = fmtPct(e.treatment.rate); $('ctrlN').textContent = `n = ${fmtNum(e.control.n)}`; $('treatN').textContent = `n = ${fmtNum(e.treatment.n)}`; $('relLift').textContent = '+' + (e.relative_lift * 100).toFixed(1) + '%'; $('absLift').textContent = '+' + (e.absolute_lift * 100).toFixed(2) + ' percentage points'; $('pVal').textContent = fmtP(e.p_value); $('ciText').textContent = `[${(e.difference_ci.low * 100).toFixed(2)}%, ${(e.difference_ci.high * 100).toFixed(2)}%]`; $('zText').textContent = e.z_stat.toFixed(2); $('sigBadge').textContent = e.p_value < .05 ? 'STATISTICALLY SIGNIFICANT' : 'NOT SIGNIFICANT';
  $('experimentNarrative').innerHTML = [['Hypothesis', 'AI Voice Agent exposure increases customer AI adoption.'], ['Primary metric', `AI adoption: ${fmtPct(e.control.rate)} control → ${fmtPct(e.treatment.rate)} treatment.`], ['Effect size', `Relative lift of ${(e.relative_lift * 100).toFixed(1)}%; absolute lift of ${(e.absolute_lift * 100).toFixed(2)} pp.`], ['Uncertainty', `95% CI for the difference: ${(e.difference_ci.low * 100).toFixed(2)}% to ${(e.difference_ci.high * 100).toFixed(2)}%.`], ['Decision rule', `Two-sided proportion test; p=${fmtP(e.p_value)}.`], ['Next step', 'Investigate whether the effect persists across segments and whether adoption translates into retention or revenue.']].map(r => `<div class="metric-line"><span>${r[0]}</span><strong>${r[1]}</strong></div>`).join('');
  const cfgBase = getChartBase();
  makeChart('segmentExperimentChart', 'bar', { labels: e.segments.map(s => s.segment), datasets: [{ label: 'Control %', data: e.segments.map(s => s.control_adoption * 100), backgroundColor: '#52627d' }, { label: 'Treatment %', data: e.segments.map(s => s.treatment_adoption * 100), backgroundColor: '#68d5c4' }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, ticks: { callback: v => v + '%' } } } });
}
function renderCohorts() { const c = state.data.cohorts; let html = '<thead><tr><th>Cohort</th>' + ['W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7'].map(x => `<th>${x}</th>`).join('') + '</tr></thead><tbody>'; c.forEach(row => { html += `<tr><td>${row.cohort}</td>` + ['W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7'].map(k => { const v = row[k]; const alpha = .12 + v * .35; return `<td><span class="heat" style="background:rgba(104,213,196,${alpha});color:${v > .7 ? '#0b1716' : '#d9e8ea'}">${fmtPct(v)}</span></td>` }).join('') + '</tr>' }); $('cohortTable').innerHTML = html + '</tbody>'; }
function renderHealth() { const d = state.data.health_distribution; makeChart('healthChart', 'doughnut', { labels: d.map(x => x.band), datasets: [{ data: d.map(x => x.customers), backgroundColor: ['#a9546c', '#d48b68', '#b7a66f', '#6e9e9a', '#68d5c4'], borderWidth: 0 }] }, { plugins: { legend: { position: 'right' } } }); renderCustomers(); }
function renderCustomers() { const q = state.search.toLowerCase(); const cs = state.customers.filter(c => (!q || Object.values(c).join(' ').toLowerCase().includes(q))).sort((a, b) => b.churn_risk - a.churn_risk).slice(0, 80); let html = '<thead><tr><th>Customer</th><th>Plan</th><th>Segment</th><th>AI</th><th>Calls</th><th>Health</th><th>Risk</th><th>ARR</th></tr></thead><tbody>'; cs.forEach(c => { html += `<tr class="customer-row" data-customer="${c.customer_id}"><td><button class="link-btn" data-customer="${c.customer_id}">${c.customer_id}</button></td><td>${c.plan}</td><td>${c.company_size}</td><td>${c.ai_adopted ? 'Yes' : 'No'}</td><td>${fmtNum(c.calls_12w)}</td><td>${c.health_score}</td><td>${fmtPct(c.churn_risk)}</td><td>${fmtUSD(c.annual_revenue)}</td></tr>` }); $('customerTable').innerHTML = html + '</tbody>'; document.querySelectorAll('.link-btn').forEach(b => b.onclick = () => openCustomer(b.dataset.customer)); }

async function openCustomer(customerId) {
  const panel = $('customerDrawer');
  if (!panel) { return; }
  panel.classList.add('open');
  $('customerDrawerBody').innerHTML = '<div class="drawer-loading">Loading customer detail…</div>';
  try {
    const res = await fetch(`/api/customers/${encodeURIComponent(customerId)}`);
    if (!res.ok) throw new Error('Customer detail unavailable');
    const d = await res.json(); const c = d.customer;
    $('customerDrawerBody').innerHTML = `<div class="drawer-kpis"><div><span>Health</span><b>${c.health_score}/100</b></div><div><span>Risk</span><b>${fmtPct(c.churn_risk)}</b></div><div><span>AI adoption</span><b>${c.ai_adopted ? 'Yes' : 'No'}</b></div><div><span>ARR</span><b>${fmtUSD(c.annual_revenue)}</b></div></div><div class="detail-grid"><div><span>Plan</span><b>${c.plan}</b></div><div><span>Company size</span><b>${c.company_size}</b></div><div><span>Industry</span><b>${c.industry}</b></div><div><span>Region</span><b>${c.region}</b></div><div><span>Active weeks</span><b>${c.active_weeks}/12</b></div><div><span>Feature breadth</span><b>${c.feature_count}</b></div></div><h4>Call timeline</h4><div class="table-wrap compact"><table><thead><tr><th>Week</th><th>Type</th><th>AI</th><th>Resolved</th><th>Escalated</th><th>Quality</th></tr></thead><tbody>${d.calls.slice(-20).reverse().map(x => `<tr><td>${x.week}</td><td>${x.call_type}</td><td>${x.ai_handled ? 'Yes' : 'No'}</td><td>${x.resolved ? 'Yes' : 'No'}</td><td>${x.escalated ? 'Yes' : 'No'}</td><td>${Number(x.quality_score).toFixed(2)}</td></tr>`).join('')}</tbody></table></div>`;
  } catch (err) { $('customerDrawerBody').innerHTML = `<div class="drawer-loading">${err.message}</div>`; }
}
$('customerSearch').addEventListener('input', e => { state.search = e.target.value; renderCustomers(); });
function renderAgent() { const m = state.data.agent_metrics; const items = [['AI calls', fmtNum(m.ai_calls), 'handled by AI'], ['Resolution rate', fmtPct(m.resolution_rate), 'AI-handled calls'], ['Escalation rate', fmtPct(m.escalation_rate), 'AI-handled calls'], ['Quality score', m.avg_quality_score.toFixed(2) + '/5', 'post-call evaluation']]; $('agentMetrics').innerHTML = items.map(x => `<div class="kpi"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]}</small></div>`).join(''); const cfgBase = getChartBase(); makeChart('agentChart', 'bar', { labels: ['Resolution rate', 'Quality score / 5', 'Avg handle time (scaled)'], datasets: [{ label: 'AI Agent', data: [m.resolution_rate * 100, m.avg_quality_score * 20, Math.max(10, 100 - m.avg_handle_time_sec / 8)], backgroundColor: '#68d5c4', borderRadius: 8 }, { label: 'Illustrative baseline', data: [73, 82, 52], backgroundColor: '#52627d', borderRadius: 8 }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, max: 100 } } }); }
const code = {
  sql: `-- Feature adoption and customer health\nWITH customer_usage AS (\n  SELECT customer_id,\n         COUNT(*) AS calls_12w,\n         AVG(quality_score) AS avg_quality,\n         AVG(CASE WHEN ai_handled=1 THEN 1.0 ELSE 0 END) AS ai_share\n  FROM calls\n  GROUP BY customer_id\n)\nSELECT c.plan,\n       COUNT(*) AS customers,\n       AVG(c.ai_adopted) AS ai_adoption_rate,\n       AVG(c.health_score) AS avg_health\nFROM customers c\nJOIN customer_usage u USING (customer_id)\nGROUP BY c.plan\nORDER BY ai_adoption_rate DESC;`,
  python: `# A/B test — two-sided difference in proportions\nfrom statsmodels.stats.proportion import proportions_ztest\n\ncounts = [control_adopters, treatment_adopters]\nnobs   = [control_customers, treatment_customers]\nz, p_value = proportions_ztest(counts, nobs)\n\nabsolute_lift = treatment_rate - control_rate\nrelative_lift = absolute_lift / control_rate\n# Report effect size + CI + p-value, not just significance.`,
  dbt: `-- dbt model: fct_customer_health.sql\nselect\n  c.customer_id,\n  c.plan,\n  c.company_size,\n  c.ai_adopted,\n  c.active_weeks,\n  c.feature_count,\n  c.retention_8w,\n  round(100 * (\n      0.45 * c.retention_score\n    + 0.18 * least(c.calls_12w / 140.0, 1)\n    + 0.15 * c.resolution_rate\n    + 0.12 * c.ai_adopted\n    + 0.10 * c.active_weeks / 12.0\n  ), 1) as health_score\nfrom {{ ref('stg_customers') }} c;`,
  airflow: `# airflow/dags/product_analytics_daily.py\nwith DAG('product_analytics_daily', schedule='0 7 * * *', catchup=False) as dag:\n    ingest = PythonOperator(task_id='ingest_events', ...)\n    transform = BashOperator(task_id='dbt_build', bash_command='dbt build')\n    tests = BashOperator(task_id='data_quality', bash_command='dbt test')\n    refresh = PythonOperator(task_id='refresh_dashboard_dataset', ...)\n    ingest >> transform >> tests >> refresh`
};
function renderCode(type) { $('codeBlock').textContent = code[type]; document.querySelectorAll('.code-tab').forEach(b => b.classList.toggle('active', b.dataset.code === type)); }
document.querySelectorAll('.code-tab').forEach(b => b.addEventListener('click', () => renderCode(b.dataset.code)));

const initialHash = location.hash.replace('#', ''); if (initialHash && $(initialHash)) setSection(initialHash);
load().catch(err => { console.error(err); document.querySelector('.main').insertAdjacentHTML('afterbegin', '<div class="notice"><span class="pill">DATA LOAD ERROR</span><span>Run the site through a local web server (for example: python3 -m http.server 8080 --directory site) rather than opening index.html directly.</span></div>'); });
