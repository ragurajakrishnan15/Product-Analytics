const state = { data: null, customers: [], charts: {}, section: 'overview', plan: 'All', size: 'All', search: '', apiMode: false };

const $ = (id) => document.getElementById(id);
const fmtPct = (x) => `${(x * 100).toFixed(1)}%`;
const fmtUSD = (x) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(x);
const fmtNum = (x) => new Intl.NumberFormat('en-US').format(x);
const fmtP = (p) => p < 0.0001 ? '<0.0001' : p.toFixed(4);
const fmtSigned = (x, digits = 1) => `${x >= 0 ? '+' : ''}${x.toFixed(digits)}`;

function setSection(id, smooth = true) {
  state.section = id;
  document.querySelectorAll('.page-section').forEach(s => s.classList.toggle('active-section', s.id === id));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.section === id));
  if (history.replaceState) history.replaceState(null, '', `#${id}`);
  window.scrollTo({ top: 0, behavior: smooth ? 'smooth' : 'auto' });
}

document.querySelectorAll('.nav-item').forEach(btn => btn.addEventListener('click', () => setSection(btn.dataset.section)));
document.querySelectorAll('a[href^="#"]').forEach(a => a.addEventListener('click', (e) => { const id = a.getAttribute('href').slice(1); if ($(id)) { e.preventDefault(); setSection(id) } }));

function loadSnapshotScript() {
  // A <script> tag (unlike fetch) also works when index.html is opened straight from disk.
  if (window.VOICEIQ_SNAPSHOT) return Promise.resolve(window.VOICEIQ_SNAPSHOT);
  return new Promise((resolve, reject) => {
    const tag = document.createElement('script');
    tag.src = 'data/snapshot.js';
    tag.onload = () => window.VOICEIQ_SNAPSHOT ? resolve(window.VOICEIQ_SNAPSHOT) : reject(new Error('Snapshot is empty'));
    tag.onerror = () => reject(new Error('Snapshot unavailable'));
    document.head.appendChild(tag);
  });
}

async function load() {
  // Full-stack mode: FastAPI serves the dashboard and the analytics API from one origin.
  // Static fallback (data/snapshot.js, written by export_static.py) keeps GitHub Pages and file:// working.
  try {
    const [healthRes, dashRes, customersRes] = await Promise.all([fetch('/api/health'), fetch('/api/dashboard'), fetch('/api/customers?limit=5000')]);
    if (!healthRes.ok || !dashRes.ok || !customersRes.ok) throw new Error('API unavailable');
    const health = await healthRes.json();
    state.data = await dashRes.json();
    state.customers = await customersRes.json();
    state.apiMode = true;
    document.querySelector('.sidebar-bottom span').textContent = `Live API • ${health.database.toUpperCase()} database`;
    document.querySelector('.sidebar-bottom strong').textContent = 'Live analytics';
    $('apiDocsLink').style.display = '';
    renderAll();
    return;
  } catch (apiError) {
    console.warn('API mode unavailable; using static portfolio snapshot.', apiError);
  }
  const snapshot = await loadSnapshotScript();
  state.data = snapshot.dashboard; state.customers = snapshot.customers;
  document.querySelector('.sidebar-bottom span').textContent = 'Static snapshot • synthetic data';
  renderAll();
}

function renderAll() {
  renderKpis(); renderInsights(); renderTrend(); renderFeature(); renderAdoption(); renderExperiment(); renderCohorts(); renderHealth(); renderChurnModel(); renderAgent(); renderCode('sql');
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
function renderFeature() { const d = state.data.features; const cfgBase = getChartBase(); makeChart('featureChart', 'bar', { labels: d.map(x => x.feature), datasets: [{ label: 'Share of customers using the feature', data: d.map(x => x.adoption_rate * 100), backgroundColor: d.map(x => x.feature === 'AI Voice Agent' ? '#68d5c4' : '#7c9cff'), borderRadius: 7 }] }, { indexAxis: 'y', scales: { x: { ...cfgBase.scales.x, max: 80, ticks: { callback: v => v + '%' } }, y: cfgBase.scales.y } }); }
function filteredCustomers() { return state.customers.filter(c => (state.plan === 'All' || c.plan === state.plan) && (state.size === 'All' || c.company_size === state.size)); }
function renderAdoption() {
  const cs = filteredCustomers(); const plans = ['Starter', 'Professional', 'Business', 'Enterprise']; const vals = plans.map(p => { const arr = cs.filter(c => c.plan === p); return arr.length ? arr.reduce((a, c) => a + c.ai_adopted, 0) / arr.length * 100 : 0 });
  const cfgBase = getChartBase();
  makeChart('planAdoptionChart', 'bar', { labels: plans, datasets: [{ label: 'AI adoption %', data: vals, backgroundColor: '#68d5c4', borderRadius: 8 }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, max: 70, ticks: { callback: v => v + '%' } } } });
  const funnel = [['All customers', cs.length], ['Active ≥ 4 weeks', cs.filter(c => c.active_weeks >= 4).length], ['3+ features', cs.filter(c => c.feature_count >= 3).length], ['AI adopted', cs.filter(c => c.ai_adopted === 1).length]]; const base = funnel[0][1] || 1;
  $('funnel').innerHTML = funnel.map(([label, n]) => `<div class="funnel-row"><span>${label}</span><div class="funnel-bar"><div class="funnel-fill" style="width:${Math.max(4, n / base * 100)}%"></div></div><b>${fmtNum(n)}</b></div>`).join('');
  document.querySelectorAll('.question-grid button').forEach(btn => btn.onclick = () => { const q = btn.dataset.q; const notes = { adoption: 'Compare treatment and control first, then split by company size and plan. A segment-level difference becomes actionable only when you understand exposure, maturity, and sample size.', retention: 'AI adoption is one signal among many. Use cohort retention plus health score to separate correlation from a plausible product effect.', pricing: 'Look for higher feature breadth, stable usage, and expansion signals in Business/Enterprise cohorts before proposing packaging changes.', engagement: 'Recent activity and the share of weeks active are the strongest churn signals in the fitted model; see the churn-risk card on the Customer Health tab.' }; $('analystNote').textContent = notes[q]; });
}
$('planFilter').addEventListener('change', e => { state.plan = e.target.value; renderAdoption(); }); $('sizeFilter').addEventListener('change', e => { state.size = e.target.value; renderAdoption(); });

const fmtCI = (ci) => `${fmtSigned(ci.low * 100)} to ${fmtSigned(ci.high * 100)} pp`;
const RESULT_LABEL = { positive: 'Significant lift', negative: 'Significant drop', inconclusive: 'Inconclusive' };
function renderExperiment() {
  const e = state.data.experiment; const g = e.retention_guardrail;
  $('ctrlRate').textContent = fmtPct(e.control.rate); $('treatRate').textContent = fmtPct(e.treatment.rate); $('ctrlN').textContent = `n = ${fmtNum(e.control.n)}`; $('treatN').textContent = `n = ${fmtNum(e.treatment.n)}`;
  $('relLift').textContent = fmtSigned(e.relative_lift * 100) + '%'; $('absLift').textContent = fmtSigned(e.absolute_lift * 100, 2) + ' percentage points'; $('pVal').textContent = fmtP(e.p_value);
  $('ciText').textContent = fmtCI(e.difference_ci); $('zText').textContent = e.z_stat.toFixed(2); $('mdeText').textContent = `${(e.mde * 100).toFixed(1)} pp (80% power)`;
  $('sigBadge').textContent = e.p_value < .05 ? 'STATISTICALLY SIGNIFICANT' : 'NOT SIGNIFICANT';
  const unclear = e.segments.filter(s => s.result !== 'positive');
  $('experimentNarrative').innerHTML = [
    ['Hypothesis', 'AI Voice Agent exposure increases customer AI adoption.'],
    ['Primary metric', `AI adoption: ${fmtPct(e.control.rate)} control → ${fmtPct(e.treatment.rate)} treatment.`],
    ['Effect size', `Relative lift of ${fmtSigned(e.relative_lift * 100)}%; absolute lift of ${fmtSigned(e.absolute_lift * 100, 2)} pp (95% CI ${fmtCI(e.difference_ci)}).`],
    ['Guardrail', `8-week retention ${fmtPct(e.control.retention_8w)} → ${fmtPct(e.treatment.retention_8w)} (${fmtCI({ low: g.ci_low, high: g.ci_high })}, p=${fmtP(g.p_value)}): ${g.result === 'inconclusive' ? 'no significant change' : 'significant ' + g.result + ' change'}.`],
    ['Sample ratio', `${fmtPct(e.sample_ratio)} treatment (intended 50%).`],
    ['Next step', unclear.length ? `Segment reads are exploratory. ${unclear.map(s => `${s.segment} is ${RESULT_LABEL[s.result].toLowerCase()} (n=${fmtNum(s.n)}; detectable effect ≈ ${(s.mde * 100).toFixed(0)} pp)`).join('; ')}. Ramp in stages and size a follow-up test before a full rollout.` : 'Ramp exposure in stages, keeping retention as a guardrail metric.']
  ].map(r => `<div class="metric-line"><span>${r[0]}</span><strong>${r[1]}</strong></div>`).join('');
  const cfgBase = getChartBase();
  makeChart('segmentExperimentChart', 'bar', { labels: e.segments.map(s => s.segment), datasets: [{ label: 'Control %', data: e.segments.map(s => s.control_adoption * 100), backgroundColor: '#52627d' }, { label: 'Treatment %', data: e.segments.map(s => s.treatment_adoption * 100), backgroundColor: '#68d5c4' }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, ticks: { callback: v => v + '%' } } } });
  $('segmentTable').innerHTML = '<thead><tr><th>Segment</th><th>n</th><th>Lift (95% CI)</th><th>p</th><th>Read</th></tr></thead><tbody>' + e.segments.map(s => `<tr><td>${s.segment}</td><td>${fmtNum(s.n)}</td><td>${fmtCI(s.diff_ci)}</td><td>${fmtP(s.p_value)}</td><td>${RESULT_LABEL[s.result]}</td></tr>`).join('') + '</tbody>';
}
function renderCohorts() {
  const weeks = ['W0', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'W7'];
  let html = '<thead><tr><th>Signup week</th><th>Customers</th>' + weeks.map(x => `<th>${x}</th>`).join('') + '</tr></thead><tbody>';
  state.data.cohorts.forEach(row => {
    html += `<tr><td>${row.cohort}</td><td>${fmtNum(row.customers)}</td>` + weeks.map(k => { const v = row[k]; if (v === null || v === undefined) return '<td></td>'; const alpha = .10 + v * .75; return `<td><span class="heat" style="background:rgba(104,213,196,${alpha});color:${v > .75 ? '#0b1716' : '#e6f1f2'}">${fmtPct(v)}</span></td>` }).join('') + '</tr>';
  });
  $('cohortTable').innerHTML = html + '</tbody>';
}
function renderChurnModel() {
  const m = state.data.churn_model;
  $('churnModel').innerHTML = `<div class="metric-line"><span>Holdout AUC</span><strong>${m.holdout_auc.toFixed(2)} (n=${fmtNum(m.n_holdout)})</strong></div><div class="metric-line"><span>Base churn rate</span><strong>${fmtPct(m.base_churn_rate)}</strong></div>` + m.drivers.map(d => `<div class="metric-line"><span>${d.feature}</span><strong>OR ${d.odds_ratio_per_sd.toFixed(2)} per SD${d.p_value < .05 ? '' : ' (n.s.)'}</strong></div>`).join('') + `<p class="note-copy">${m.method}. ${m.caveat}</p>`;
  $('bandRetention').innerHTML = state.data.health_distribution.map(b => `<div class="metric-line"><span>${b.band}</span><strong>${fmtNum(b.customers)} accounts · ${b.retention_8w === null ? '–' : fmtPct(b.retention_8w)} retained</strong></div>`).join('');
}

function renderHealth() { const d = state.data.health_distribution; makeChart('healthChart', 'doughnut', { labels: d.map(x => x.band), datasets: [{ data: d.map(x => x.customers), backgroundColor: ['#a9546c', '#d48b68', '#b7a66f', '#6e9e9a', '#68d5c4'], borderWidth: 0 }] }, { plugins: { legend: { position: 'right' } } }); renderCustomers(); }
function renderCustomers() { const q = state.search.toLowerCase(); const cs = state.customers.filter(c => (!q || Object.values(c).join(' ').toLowerCase().includes(q))).sort((a, b) => b.churn_risk - a.churn_risk).slice(0, 80); let html = '<thead><tr><th>Customer</th><th>Plan</th><th>Segment</th><th>AI</th><th>Calls</th><th>Health</th><th>Risk</th><th>ARR</th></tr></thead><tbody>'; cs.forEach(c => { html += `<tr class="customer-row" data-customer="${c.customer_id}"><td><button class="link-btn" data-customer="${c.customer_id}">${c.customer_id}</button></td><td>${c.plan}</td><td>${c.company_size}</td><td>${c.ai_adopted ? 'Yes' : 'No'}</td><td>${fmtNum(c.calls_12w)}</td><td>${c.health_score}</td><td>${fmtPct(c.churn_risk)}</td><td>${fmtUSD(c.annual_revenue)}</td></tr>` }); $('customerTable').innerHTML = html + '</tbody>'; document.querySelectorAll('.link-btn').forEach(b => b.onclick = () => openCustomer(b.dataset.customer)); }

function customerProfileHtml(c) {
  return `<div class="drawer-kpis"><div><span>Health</span><b>${c.health_score}/100</b></div><div><span>Risk</span><b>${fmtPct(c.churn_risk)}</b></div><div><span>AI adoption</span><b>${c.ai_adopted ? 'Yes' : 'No'}</b></div><div><span>ARR</span><b>${fmtUSD(c.annual_revenue)}</b></div></div><div class="detail-grid"><div><span>Plan</span><b>${c.plan}</b></div><div><span>Company size</span><b>${c.company_size}</b></div><div><span>Industry</span><b>${c.industry}</b></div><div><span>Region</span><b>${c.region}</b></div><div><span>Active weeks</span><b>${c.active_weeks}/12</b></div><div><span>Feature breadth</span><b>${c.feature_count}</b></div></div>`;
}

async function openCustomer(customerId) {
  const panel = $('customerDrawer');
  if (!panel) { return; }
  panel.classList.add('open');
  if (!state.apiMode) {
    const c = state.customers.find(x => x.customer_id === customerId);
    $('customerDrawerBody').innerHTML = c ? customerProfileHtml(c) + '<div class="drawer-loading">The call-level timeline is served by the live API. Run the FastAPI app to see it.</div>' : '<div class="drawer-loading">Customer not found.</div>';
    return;
  }
  $('customerDrawerBody').innerHTML = '<div class="drawer-loading">Loading customer detail…</div>';
  try {
    const res = await fetch(`/api/customers/${encodeURIComponent(customerId)}`);
    if (!res.ok) throw new Error('Customer detail unavailable');
    const d = await res.json();
    $('customerDrawerBody').innerHTML = customerProfileHtml(d.customer) + `<h4>Features used</h4><p class="note-copy">${d.features.length ? d.features.map(f => `${f.feature} (since ${f.first_used_week})`).join(' · ') : 'None yet'}</p><h4>Call timeline</h4><div class="table-wrap compact"><table><thead><tr><th>Week</th><th>Type</th><th>AI</th><th>Resolved</th><th>Escalated</th><th>Quality</th></tr></thead><tbody>${d.calls.slice(-20).reverse().map(x => `<tr><td>${x.week}</td><td>${x.call_type}</td><td>${x.ai_handled ? 'Yes' : 'No'}</td><td>${x.resolved ? 'Yes' : 'No'}</td><td>${x.escalated ? 'Yes' : 'No'}</td><td>${Number(x.quality_score).toFixed(2)}</td></tr>`).join('')}</tbody></table></div>`;
  } catch (err) { $('customerDrawerBody').innerHTML = `<div class="drawer-loading">${err.message}</div>`; }
}
$('customerSearch').addEventListener('input', e => { state.search = e.target.value; renderCustomers(); });
function renderAgent() {
  const m = state.data.agent_metrics; const h = m.human_baseline;
  const items = [['AI calls', fmtNum(m.ai_calls), 'handled by AI'], ['Resolution rate', fmtPct(m.resolution_rate), 'AI-handled calls'], ['Escalation rate', fmtPct(m.escalation_rate), 'AI-handled calls'], ['Quality score', m.avg_quality_score.toFixed(2) + '/5', 'post-call evaluation']];
  $('agentMetrics').innerHTML = items.map(x => `<div class="kpi"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]}</small></div>`).join('');
  const cfgBase = getChartBase();
  makeChart('agentChart', 'bar', { labels: ['Resolution rate %', 'Escalation rate %', 'Quality (% of 5)'], datasets: [{ label: 'AI-handled', data: [m.resolution_rate * 100, m.escalation_rate * 100, m.avg_quality_score * 20], backgroundColor: '#68d5c4', borderRadius: 8 }, { label: `Human-handled (${fmtNum(h.calls)} calls)`, data: [h.resolution_rate * 100, h.escalation_rate * 100, h.avg_quality_score * 20], backgroundColor: '#52627d', borderRadius: 8 }] }, { scales: { x: cfgBase.scales.x, y: { ...cfgBase.scales.y, max: 100 } } });
  $('agentNote').textContent = `Handle time: ${Math.round(m.avg_handle_time_sec)}s AI vs ${Math.round(h.avg_handle_time_sec)}s human. First response: ${m.avg_first_response_min.toFixed(1)} min vs ${h.avg_first_response_min.toFixed(1)} min. Observational: AI calls are not randomly assigned.`;
}
const code = {
  sql: `-- sql/00_customer_metrics.sql (excerpt): health score from raw events only\nSELECT base.*,\n       ROUND(100 * (\n           0.35 * active_week_share                       -- engagement\n         + 0.20 * LEAST(calls_per_active_week / 3, 1)     -- intensity\n         + 0.15 * feature_count / 6.0                     -- breadth\n         + 0.15 * resolution_rate                         -- quality\n         + 0.10 * ai_adopted                              -- AI adoption\n         + 0.05 * recently_active                         -- recency\n       )) AS health_score\nFROM base;  -- base = calls + feature_usage aggregated per customer`,
  python: `# backend/main.py: churn-risk model\nX = standardise(metrics[CHURN_FEATURES])\ntrain = rng.random(len(X)) < 0.7\nmodel = sm.Logit(churned[train], sm.add_constant(X)[train]).fit()\nrisk = model.predict(sm.add_constant(X))\nholdout_auc = auc(churned[~train], risk[~train])\n\n# A/B readout: lift, Wald CI, z-test, MDE, per-segment CIs\ntest = two_proportion_test(x_control, n_control, x_treat, n_treat)`,
  dbt: `-- dbt/models/fct_product_metrics.sql\n{{ config(materialized='table') }}\n\nselect\n  plan,\n  company_size,\n  count(*)             as customers,\n  avg(ai_adopted)      as ai_adoption_rate,\n  avg(calls_12w)       as avg_calls_12w,\n  avg(resolution_rate) as resolution_rate,\n  avg(health_score)    as avg_health,\n  avg(retained_8w)     as retention_8w\nfrom {{ ref('stg_customers') }}\ngroup by 1, 2\n\n-- models/schema.yml tests: unique + not_null customer_id, accepted_values experiment_group`,
  airflow: `# airflow/dags/product_analytics_daily.py\nwith DAG('product_analytics_daily', schedule='0 7 * * *', catchup=False) as dag:\n    ingest = BashOperator(task_id='ingest_events', bash_command='python build_data.py', cwd=PROJECT_DIR)\n    quality = BashOperator(task_id='data_quality', bash_command='python tests/test_data_quality.py', cwd=PROJECT_DIR)\n    transform = BashOperator(task_id='dbt_build', bash_command='dbt build', cwd=DBT_DIR)  # models + tests\n    refresh = BashOperator(task_id='refresh_dashboard_snapshot', bash_command='python export_static.py', cwd=PROJECT_DIR)\n    ingest >> quality >> transform >> refresh`
};
function renderCode(type) { $('codeBlock').textContent = code[type]; document.querySelectorAll('.code-tab').forEach(b => b.classList.toggle('active', b.dataset.code === type)); }
document.querySelectorAll('.code-tab').forEach(b => b.addEventListener('click', () => renderCode(b.dataset.code)));

const initialHash = location.hash.replace('#', ''); if (initialHash && $(initialHash)) setSection(initialHash, false);
load().catch(err => { console.error(err); document.querySelector('.main').insertAdjacentHTML('afterbegin', '<div class="notice"><span class="pill">DATA LOAD ERROR</span><span>Dashboard data could not be loaded. Run <code>python export_static.py</code> to create site/data/snapshot.js, or start the API with <code>python -m uvicorn backend.main:app</code>.</span></div>'); });
