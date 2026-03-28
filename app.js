/* ===================================================================
   Indonesia-China Finance Dashboard — App Logic
   CSIS-inspired editorial charts · Plotly.js · Leaflet.js
   =================================================================== */

const C = {
  gold: '#B58900', goldLight: '#D4A517', red: '#D75F5F', green: '#608B4E',
  blue: '#4A7FB5', purple: '#7B68A8', teal: '#2D9C8F', orange: '#D87F33',
  text: '#2E2E2E', muted: '#928374', bg: '#F3F0E0', border: '#D4D0BC',
};

const PALETTE = [C.gold, C.green, C.blue, C.red, C.purple, C.teal, C.orange, '#A0522D', '#6B8E23', '#B8860B', '#708090', '#CD853F', '#4682B4', '#8FBC8F', '#D2691E'];

// Synthetic FDI coordinates: map sectors to known Indonesian industrial zones
const FDI_ZONES = {
  'Metals': [/* Morowali */[-2.85, 121.97], /* Weda Bay */[0.37, 127.83], /* Obi Island */[-1.53, 127.63], /* Pomalaa */[-4.0, 121.6], /* Konawe */[-3.5, 122.1]],
  'Energy': [/* Kalimantan */[-1.2, 116.8], /* Java */[-6.9, 110.4], /* Sumatra */[1.5, 104.4], /* Sulawesi */[-1.5, 121.4], /* NTB */[-8.6, 116.3]],
  'Transport': [/* Jakarta */[-6.2, 106.85], /* Surabaya */[-7.25, 112.75], /* Subang */[-6.57, 107.75], /* Cikarang */[-6.33, 107.16], /* Semarang */[-6.97, 110.42]],
  'Technology': [/* Jakarta */[-6.21, 106.82], /* Bandung */[-6.91, 107.61], /* BSD */[-6.3, 106.64], /* Batam */[1.05, 104.03]],
  'Real Estate': [/* Jakarta */[-6.18, 106.83], /* Bali */[-8.65, 115.22], /* MNC Lido */[-6.74, 106.8], /* Tangerang */[-6.18, 106.63]],
  'Finance': [/* SCBD Jakarta */[-6.23, 106.81], /* Sudirman */[-6.21, 106.82], /* Kuningan */[-6.24, 106.83]],
  'Agriculture': [/* Kalimantan */[-0.5, 117.0], /* Sumatra */[2.0, 99.8], /* Sulawesi */[-1.3, 120.8], /* Java */[-7.5, 110.0]],
  'Logistics': [/* Tanjung Priok */[-6.1, 106.88], /* Tanjung Perak */[-7.2, 112.73], /* Patimban */[-6.4, 107.9], /* Kuala Tanjung */[3.35, 99.42]],
  'Chemicals': [/* Cilegon */[-6.0, 106.05], /* Gresik */[-7.16, 112.65], /* Tuban */[-6.9, 112.05], /* Lhokseumawe */[5.18, 97.15]],
  'Other': [/* Jakarta */[-6.2, 106.85], /* Banten */[-6.4, 106.1], /* Karawang */[-6.3, 107.3]],
};

function normalizeSectorName(sector) {
  if (!sector) return sector;
  return String(sector)
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .replace(/\b[a-z]/g, char => char.toUpperCase());
}

function normalizeProjects(projects) {
  projects.forEach(project => {
    project.sector = normalizeSectorName(project.sector);
  });
}

function assignFDICoords(projects) {
  const counters = {};
  projects.forEach(p => {
    if (p.finance_type !== 'FDI') return;
    const sectorName = normalizeSectorName(p.sector) || 'Other';
    const zones = FDI_ZONES[sectorName] || FDI_ZONES['Other'];
    const key = sectorName;
    counters[key] = (counters[key] || 0);
    const zone = zones[counters[key] % zones.length];
    // Add jitter so markers don't stack exactly
    const jitter = () => (Math.random() - 0.5) * 0.15;
    p.latitude = zone[0] + jitter();
    p.longitude = zone[1] + jitter();
    counters[key]++;
  });
}

const LAYOUT_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: "'Lato', sans-serif", size: 12, color: C.text },
  margin: { t: 20, b: 40, l: 50, r: 20 },
  hovermode: 'x unified',
  hoverlabel: {
    bgcolor: '#F7F5EE',
    bordercolor: C.text,
    font: { family: "'Lato', sans-serif", size: 12, color: C.text },
  },
  dragmode: false,
};

const CFG = {
  displayModeBar: false,
  displaylogo: false,
  responsive: true,
  scrollZoom: false,
  editable: false,
  edits: {
    annotationPosition: false,
    annotationTail: false,
    annotationText: false,
    axisTitleText: false,
    colorbarPosition: false,
    colorbarTitleText: false,
    legendPosition: false,
    legendText: false,
    shapePosition: false,
    titleText: false,
  },
  showAxisDragHandles: false,
  showAxisRangeEntryBoxes: false,
  showTips: false,
  doubleClick: false,
};

// ── State ──────────────────────────────────────────────────────────
let currentPage = 'home';
let filters = { type: 'all', sector: 'all', status: 'all', yearMin: 2000, yearMax: 2025 };
let dfMap = null, fdiMap = null;
let dfMarkers = [], fdiMarkers = [];

// ── Helpers ────────────────────────────────────────────────────────
const filtered = () => PROJECTS.filter(p => {
  if (filters.type !== 'all' && p.finance_type !== filters.type) return false;
  if (filters.sector !== 'all' && p.sector !== filters.sector) return false;
  if (filters.status !== 'all' && p.status !== filters.status) return false;
  if (p.year < filters.yearMin || p.year > filters.yearMax) return false;
  return true;
});

function fmt$(v) {
  if (v == null || isNaN(v)) return '—';
  const a = Math.abs(v);
  if (a >= 1e12) return '$' + (v / 1e12).toFixed(2) + 'T';
  if (a >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return '$' + (v / 1e6).toFixed(1) + 'M';
  if (a >= 1e3) return '$' + (v / 1e3).toFixed(0) + 'K';
  return '$' + v.toFixed(0);
}
const fmtN = v => v == null ? '—' : v.toLocaleString();
const fmtP = v => v == null || isNaN(v) ? '—' : (v * 100).toFixed(1) + '%';
const sum = (a, k) => a.reduce((s, d) => s + (d[k] || 0), 0);

function groupBy(arr, key) {
  const m = {};
  arr.forEach(d => { const k = d[key] || 'Unknown'; (m[k] = m[k] || []).push(d); });
  return m;
}

function topN(obj, n, fn) {
  return Object.entries(obj).map(([k, v]) => ({ key: k, value: fn(v) }))
    .sort((a, b) => b.value - a.value).slice(0, n);
}

// ── Navigation ─────────────────────────────────────────────────────
function setSidebarOpen(isOpen) {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  sidebar.classList.toggle('open', isOpen);
  document.body.classList.toggle('sidebar-open', isOpen);
}

function navigate(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
  setSidebarOpen(false);
  window.scrollTo({ top: 0, behavior: 'smooth' });
  setTimeout(() => renderPage(page), 80);
}

// ── Filters ────────────────────────────────────────────────────────
function initFilters() {
  const sectors = [...new Set(PROJECTS.map(p => p.sector).filter(Boolean))].sort();
  const sel = document.getElementById('filterSector');
  sectors.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; sel.appendChild(o); });

  const statuses = [...new Set(PROJECTS.map(p => p.status).filter(Boolean))].sort();
  const ssel = document.getElementById('filterStatus');
  statuses.forEach(s => { const o = document.createElement('option'); o.value = s; o.textContent = s; ssel.appendChild(o); });

  const years = [...new Set(PROJECTS.map(p => p.year).filter(Boolean))].sort((a, b) => a - b);
  filters.yearMin = years[0]; filters.yearMax = years[years.length - 1];
  const ymin = document.getElementById('filterYearMin'), ymax = document.getElementById('filterYearMax');
  years.forEach(y => {
    const o1 = document.createElement('option'); o1.value = y; o1.textContent = y; ymin.appendChild(o1);
    const o2 = document.createElement('option'); o2.value = y; o2.textContent = y; ymax.appendChild(o2);
  });
  ymin.value = filters.yearMin; ymax.value = filters.yearMax;

  document.getElementById('filterType').addEventListener('change', e => { filters.type = e.target.value; render(); });
  document.getElementById('filterSector').addEventListener('change', e => { filters.sector = e.target.value; render(); });
  document.getElementById('filterStatus').addEventListener('change', e => { filters.status = e.target.value; render(); });
  ymin.addEventListener('change', e => { filters.yearMin = +e.target.value; render(); });
  ymax.addEventListener('change', e => { filters.yearMax = +e.target.value; render(); });
  document.getElementById('filterReset').addEventListener('click', () => {
    filters = { type: 'all', sector: 'all', status: 'all', yearMin: years[0], yearMax: years[years.length - 1] };
    document.getElementById('filterType').value = 'all';
    document.getElementById('filterSector').value = 'all';
    document.getElementById('filterStatus').value = 'all';
    ymin.value = years[0]; ymax.value = years[years.length - 1];
    render();
  });
}

function render() { renderPage(currentPage); }

function showActiveFilters(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const a = [];
  if (filters.type !== 'all') a.push('Type: ' + filters.type);
  if (filters.sector !== 'all') a.push('Sector: ' + filters.sector);
  if (filters.status !== 'all') a.push('Status: ' + filters.status);
  const yrs = [...new Set(PROJECTS.map(p => p.year).filter(Boolean))].sort((a, b) => a - b);
  if (filters.yearMin > yrs[0] || filters.yearMax < yrs[yrs.length - 1]) a.push(filters.yearMin + '–' + filters.yearMax);
  if (!a.length) { el.style.display = 'none'; return; }
  el.style.display = 'flex';
  el.innerHTML = '<span class="label">Filters:</span>' + a.map(f => `<span class="filter-pill">${f}</span>`).join('');
}

function renderPage(p) {
  if (p === 'home') renderHome();
  else if (p === 'df') renderDF();
  else if (p === 'fdi') renderFDI();
}

// ════════════════════════════════════════════════════════════════════
// HOME
// ════════════════════════════════════════════════════════════════════
function renderHome() {
  const d = filtered();
  const committed = sum(d, 'committed_usd'), disbursed = sum(d, 'disbursed_usd');
  const dfN = d.filter(x => x.finance_type === 'DF').length, fdiN = d.filter(x => x.finance_type === 'FDI').length;
  const rate = committed > 0 ? disbursed / committed : 0;
  const yrs = new Set(d.map(x => x.year));
  const secGrp = groupBy(d, 'sector');
  const top3 = topN(secGrp, 3, a => sum(a, 'committed_usd'));

  document.getElementById('heroStats').innerHTML = [
    ['$' + ((committed / 1e9).toFixed(1)) + 'B', 'Committed'],
    ['$' + ((disbursed / 1e9).toFixed(1)) + 'B', 'Disbursed'],
    [fmtN(d.length), 'Projects'],
    [yrs.size + '', 'Years'],
  ].map(([n, l]) => `<div class="hero-stat-item"><div class="hero-stat-number">${n}</div><div class="hero-stat-label">${l}</div></div>`).join('');

  document.getElementById('homeNarrative').innerHTML = `
    <p class="narrative">
      <strong>Since 2000, <span class="stat">${fmtN(d.length)}</span> Chinese-financed projects</strong> totaling
      <span class="stat">${fmt$(committed)}</span> in commitments have been tracked across Indonesia.
      Of these, ${fmtN(dfN)} are development finance and ${fmtN(fdiN)} are direct investments.
      The overall realization rate — the ratio of disbursed to committed capital — stands at
      <span class="stat">${fmtP(rate)}</span>.
    </p>
    <div class="callout ${rate >= 0.7 ? 'green' : 'red'}">
      <strong>${rate >= 0.7 ? 'Strong delivery:' : 'Delivery gap:'}</strong>
      ${rate >= 0.7
      ? 'The high realization rate suggests that most committed funds have reached their intended recipients.'
      : 'A significant portion of committed capital has not been disbursed, suggesting delivery challenges across the portfolio.'}
    </div>
    <p class="narrative">
      The largest sectors by capital allocation are <strong>${top3.map(s => s.key).join(', ')}</strong>,
      which together account for ${fmtP(top3.reduce((s, x) => s + x.value, 0) / (committed || 1))} of total commitments.
    </p>
  `;

  document.getElementById('homeKpis').innerHTML = [
    ['Total Projects', fmtN(d.length)],
    ['Committed', fmt$(committed)],
    ['Disbursed', fmt$(disbursed)],
    ['Realization', fmtP(rate)],
    ['Sectors', Object.keys(secGrp).length],
  ].map(([l, v]) => `<div class="kpi-card"><div class="kpi-label">${l}</div><div class="kpi-value">${v}</div></div>`).join('');

  // Year chart
  const yg = groupBy(d, 'year');
  const sortY = Object.keys(yg).map(Number).sort((a, b) => a - b);
  Plotly.newPlot('homeYearChart', [{
    x: sortY, y: sortY.map(y => sum(yg[y], 'committed_usd')),
    type: 'bar', marker: { color: C.gold, opacity: .75 },
    hovertemplate: '%{x}: %{customdata}<extra></extra>',
    customdata: sortY.map(y => fmt$(sum(yg[y], 'committed_usd'))),
  }], {
    ...LAYOUT_BASE,
    xaxis: { gridcolor: 'transparent', linecolor: C.border, dtick: 5 },
    yaxis: { gridcolor: C.border, linecolor: C.border, zeroline: false },
  }, CFG);

  // Sector chart — horizontal bar
  const secTop = topN(secGrp, 8, a => sum(a, 'committed_usd'));
  Plotly.newPlot('homeSectorChart', [{
    y: secTop.map(s => s.key).reverse(),
    x: secTop.map(s => s.value).reverse(),
    type: 'bar', orientation: 'h',
    marker: { color: PALETTE.slice(0, secTop.length).reverse(), opacity: .8 },
    hovertemplate: '%{y}<br>%{customdata}<extra></extra>',
    customdata: secTop.map(s => fmt$(s.value)).reverse(),
  }], {
    ...LAYOUT_BASE,
    margin: { t: 10, b: 35, l: 180, r: 20 },
    xaxis: { gridcolor: C.border, zeroline: false },
    yaxis: { automargin: true },
  }, CFG);
}

// ════════════════════════════════════════════════════════════════════
// DEVELOPMENT FINANCE
// ════════════════════════════════════════════════════════════════════
function renderDF() {
  const d = filtered().filter(x => x.finance_type === 'DF');
  showActiveFilters('dfActiveFilters');

  const committed = sum(d, 'committed_usd'), disbursed = sum(d, 'disbursed_usd');
  const rate = committed > 0 ? disbursed / committed : 0;
  const statusGrp = groupBy(d, 'status');
  const done = (statusGrp['Completion'] || []).length;

  document.getElementById('dfKpis').innerHTML = [
    ['Projects', fmtN(d.length)],
    ['Committed', fmt$(committed)],
    ['Disbursed', fmt$(disbursed)],
    ['Realization', fmtP(rate), rate >= 0.7 ? 'positive' : 'negative'],
    ['Completed', fmtN(done), 'neutral', d.length > 0 ? fmtP(done / d.length) + ' of total' : ''],
  ].map(([l, v, cls, delta]) => `<div class="kpi-card"><div class="kpi-label">${l}</div><div class="kpi-value">${v}</div>${delta ? `<div class="kpi-delta ${cls || ''}">${delta}</div>` : ''}</div>`).join('');

  // Narrative
  const peakYear = d.length ? (() => {
    const yg = groupBy(d, 'year');
    let max = 0, my = 0;
    Object.entries(yg).forEach(([y, arr]) => { const s = sum(arr, 'committed_usd'); if (s > max) { max = s; my = y; } });
    return { year: my, val: max };
  })() : { year: 0, val: 0 };

  document.getElementById('dfNarrative').innerHTML = `
    <div class="callout">
      <strong>Peak year: ${peakYear.year}</strong> with ${fmt$(peakYear.val)} in new commitments.
      The portfolio spans ${Object.keys(groupBy(d, 'sector')).length} sectors, with
      ${fmtN(done)} of ${fmtN(d.length)} projects reaching completion.
    </div>
  `;

  // ═══ Committed vs Disbursed trend — area chart ═══
  const yg = groupBy(d, 'year');
  const years = Object.keys(yg).map(Number).sort((a, b) => a - b);
  Plotly.newPlot('dfTrendChart', [
    {
      x: years, y: years.map(y => sum(yg[y], 'committed_usd')), name: 'Committed',
      type: 'scatter', mode: 'lines', fill: 'tozeroy',
      line: { color: C.gold, width: 2 }, fillcolor: 'rgba(181,137,0,.12)',
      hovertemplate: '%{x}: %{customdata}<extra>Committed</extra>',
      customdata: years.map(y => fmt$(sum(yg[y], 'committed_usd'))),
    },
    {
      x: years, y: years.map(y => sum(yg[y], 'disbursed_usd')), name: 'Disbursed',
      type: 'scatter', mode: 'lines', fill: 'tozeroy',
      line: { color: C.green, width: 2 }, fillcolor: 'rgba(96,139,78,.12)',
      hovertemplate: '%{x}: %{customdata}<extra>Disbursed</extra>',
      customdata: years.map(y => fmt$(sum(yg[y], 'disbursed_usd'))),
    },
  ], {
    ...LAYOUT_BASE, margin: { t: 10, b: 40, l: 55, r: 20 },
    xaxis: { gridcolor: 'transparent', linecolor: C.border },
    yaxis: { gridcolor: C.border, zeroline: false },
    legend: { orientation: 'h', y: 1.08, x: 0.5, xanchor: 'center', font: { size: 11 } },
  }, CFG);

  // ═══ Sector bar ═══
  const secGrp = groupBy(d, 'sector');
  const secTop = topN(secGrp, 10, a => sum(a, 'committed_usd'));
  Plotly.newPlot('dfSectorBar', [{
    y: secTop.map(s => s.key).reverse(),
    x: secTop.map(s => s.value).reverse(),
    type: 'bar', orientation: 'h',
    marker: { color: PALETTE.slice(0, secTop.length).reverse(), opacity: .8 },
    hovertemplate: '%{y}<br>%{customdata}<extra></extra>',
    customdata: secTop.map(s => fmt$(s.value)).reverse(),
  }], {
    ...LAYOUT_BASE, margin: { t: 10, b: 35, l: 190, r: 20 },
    xaxis: { gridcolor: C.border, zeroline: false },
    yaxis: { automargin: true },
  }, CFG);

  // ═══ Sector pie ═══
  Plotly.newPlot('dfSectorPie', [{
    labels: secTop.map(s => s.key), values: secTop.map(s => s.value),
    type: 'pie', hole: .42,
    marker: { colors: PALETTE },
    textinfo: 'percent', textfont: { size: 10 },
    hovertemplate: '%{label}<br>%{value:$,.0f}<br>%{percent}<extra></extra>',
  }], {
    ...LAYOUT_BASE, margin: { t: 10, b: 10, l: 10, r: 10 },
    legend: { font: { size: 9 }, orientation: 'h', y: -0.2 },
  }, CFG);

  // ═══ Status bar ═══
  const statNames = Object.keys(statusGrp).sort();
  const statColors = statNames.map(s =>
    s === 'Completion' ? C.green : s.includes('Pipeline') ? C.gold : s === 'Implementation' ? C.blue : s === 'Suspended' ? C.red : C.muted
  );
  Plotly.newPlot('dfStatusChart', [{
    y: statNames, x: statNames.map(s => statusGrp[s].length),
    type: 'bar', orientation: 'h',
    marker: { color: statColors, opacity: .8 },
    text: statNames.map(s => statusGrp[s].length), textposition: 'outside',
    textfont: { size: 11, color: C.text },
    hovertemplate: '%{y}: %{x} projects<extra></extra>',
  }], {
    ...LAYOUT_BASE, margin: { t: 10, b: 35, l: 155, r: 45 },
    xaxis: { gridcolor: C.border, zeroline: false },
    yaxis: { automargin: true },
  }, CFG);

  // ═══ Status × Year — STACKED BAR (replacing heatmap) ═══
  const statusOrder = ['Completion', 'Implementation', 'Pipeline: Commitment', 'Pipeline: Pledge', 'Suspended'];
  const statusColorsMap = { 'Completion': C.green, 'Implementation': C.blue, 'Pipeline: Commitment': C.gold, 'Pipeline: Pledge': '#D4A517', 'Suspended': C.red };
  const traces = statusOrder.filter(s => statusGrp[s]).map(s => ({
    x: years, y: years.map(y => d.filter(p => p.status === s && p.year === y).length),
    name: s, type: 'bar',
    marker: { color: statusColorsMap[s] || C.muted, opacity: .8 },
    hovertemplate: s + '<br>%{x}: %{y} projects<extra></extra>',
  }));
  Plotly.newPlot('dfStatusYearChart', traces, {
    ...LAYOUT_BASE, margin: { t: 10, b: 40, l: 40, r: 20 },
    barmode: 'stack',
    xaxis: { gridcolor: 'transparent', linecolor: C.border, dtick: 5 },
    yaxis: { gridcolor: C.border, zeroline: false, title: 'Projects' },
    legend: { font: { size: 9 }, orientation: 'h', y: 1.12, x: .5, xanchor: 'center' },
  }, CFG);

  // ═══ Spatial narrative ═══
  const topProv = [...DF_REPORT_PROVINCES].sort((a, b) => b.project_value_2024_usd_b - a.project_value_2024_usd_b);
  const topPC = [...DF_REPORT_PROVINCES].sort((a, b) => b.per_capita_2024_usd - a.per_capita_2024_usd);
  document.getElementById('dfSpatialNarrative').innerHTML = `
    <p class="narrative">
      By dollar value, <strong>${topProv[0]?.province_name}</strong> leads with
      <span class="stat">$${topProv[0]?.project_value_2024_usd_b.toFixed(1)}B</span>,
      followed by ${topProv[1]?.province_name} and ${topProv[2]?.province_name}.
      But on a per-capita basis, the picture shifts —
      <strong>${topPC[0]?.province_name}</strong> tops the list at
      <span class="stat">$${topPC[0]?.per_capita_2024_usd.toFixed(0)}</span> per person.
    </p>
  `;

  // ═══ Map ═══
  renderDFMap();

  // ═══ Region bar ═══
  const regionGrp = {};
  DF_REPORT_PROVINCES.forEach(p => {
    if (!regionGrp[p.region]) regionGrp[p.region] = { count: 0, value: 0 };
    regionGrp[p.region].count += p.project_count;
    regionGrp[p.region].value += p.project_value_2024_usd_b;
  });
  const regions = Object.entries(regionGrp).sort((a, b) => b[1].value - a[1].value);
  Plotly.newPlot('dfRegionBar', [{
    x: regions.map(([r]) => r), y: regions.map(([, v]) => v.value),
    type: 'bar',
    marker: { color: PALETTE.slice(0, regions.length), opacity: .8 },
    text: regions.map(([, v]) => '$' + v.value.toFixed(1) + 'B'), textposition: 'outside',
    textfont: { size: 10, color: C.text },
    hovertemplate: '%{x}<br>%{text}<br>%{customdata} projects<extra></extra>',
    customdata: regions.map(([, v]) => v.count),
  }], {
    ...LAYOUT_BASE,
    xaxis: { gridcolor: 'transparent' },
    yaxis: { gridcolor: C.border, zeroline: false, title: 'Value (USD B)' },
  }, CFG);

  // ═══ Province table ═══
  renderDFTable();

  // ═══ Sector × Year — STACKED AREA (replacing heatmap) ═══
  const topSectors = topN(secGrp, 6, a => sum(a, 'committed_usd')).map(s => s.key);
  const areaTraces = topSectors.map((sec, i) => ({
    x: years,
    y: years.map(y => sum(d.filter(p => p.sector === sec && p.year === y), 'committed_usd')),
    name: sec, type: 'scatter', mode: 'lines', stackgroup: 'one',
    line: { color: PALETTE[i], width: 0 },
    fillcolor: PALETTE[i] + 'AA',
    hovertemplate: sec + '<br>%{x}: %{customdata}<extra></extra>',
    customdata: years.map(y => fmt$(sum(d.filter(p => p.sector === sec && p.year === y), 'committed_usd'))),
  }));
  Plotly.newPlot('dfSectorTrendChart', areaTraces, {
    ...LAYOUT_BASE, margin: { t: 10, b: 40, l: 55, r: 20 },
    xaxis: { gridcolor: 'transparent', linecolor: C.border },
    yaxis: { gridcolor: C.border, zeroline: false, title: 'USD' },
    legend: { font: { size: 10 }, orientation: 'h', y: 1.12, x: .5, xanchor: 'center' },
  }, CFG);
}

// ════════════════════════════════════════════════════════════════════
// FDI
// ════════════════════════════════════════════════════════════════════
function renderFDI() {
  const d = filtered().filter(x => x.finance_type === 'FDI');
  showActiveFilters('fdiActiveFilters');

  const total = sum(d, 'committed_usd');
  const avg = d.length > 0 ? total / d.length : 0;
  const secGrp = groupBy(d, 'sector');
  const topSec = topN(secGrp, 1, a => sum(a, 'committed_usd'))[0];

  document.getElementById('fdiKpis').innerHTML = [
    ['Deals', fmtN(d.length)],
    ['Total Value', fmt$(total)],
    ['Avg Deal', fmt$(avg)],
    ['Top Sector', topSec ? topSec.key : '—'],
    ['Sectors', Object.keys(secGrp).length],
  ].map(([l, v]) => `<div class="kpi-card"><div class="kpi-label">${l}</div><div class="kpi-value" ${l === 'Top Sector' ? 'style="font-size:1rem"' : ''}>${v}</div></div>`).join('');

  const topDeal = d.length ? [...d].sort((a, b) => (b.committed_usd || 0) - (a.committed_usd || 0))[0] : null;
  document.getElementById('fdiNarrative').innerHTML = `
    <div class="callout">
      ${topDeal ? `The largest single deal is <strong>${topDeal.project_name}</strong> (${topDeal.year}) at <strong>${fmt$(topDeal.committed_usd)}</strong> in the ${topDeal.sector} sector.` : 'No deals match current filters.'}
    </div>
  `;

  // ═══ Map ═══
  renderFDIMap(d);

  // ═══ Sector bar ═══
  const secTop = topN(secGrp, 10, a => sum(a, 'committed_usd'));
  Plotly.newPlot('fdiSectorChart', [{
    y: secTop.map(s => s.key).reverse(),
    x: secTop.map(s => s.value).reverse(),
    type: 'bar', orientation: 'h',
    marker: { color: PALETTE.slice(0, secTop.length).reverse(), opacity: .8 },
    text: secTop.map(s => fmt$(s.value)).reverse(), textposition: 'outside', textfont: { size: 10 },
    hovertemplate: '%{y}<br>%{customdata}<extra></extra>',
    customdata: secTop.map(s => fmt$(s.value)).reverse(),
  }], {
    ...LAYOUT_BASE, margin: { t: 10, b: 35, l: 100, r: 70 },
    xaxis: { gridcolor: C.border, zeroline: false },
    yaxis: { automargin: true },
  }, CFG);

  // ═══ Year dual-axis ═══
  const yg = groupBy(d, 'year');
  const years = Object.keys(yg).map(Number).sort((a, b) => a - b);
  Plotly.newPlot('fdiYearChart', [
    {
      x: years, y: years.map(y => yg[y].length), name: 'Deals', type: 'bar',
      marker: { color: C.gold, opacity: .6 }, yaxis: 'y',
      hovertemplate: '%{x}: %{y} deals<extra>Count</extra>',
    },
    {
      x: years, y: years.map(y => sum(yg[y], 'committed_usd')), name: 'Value', type: 'scatter',
      mode: 'lines+markers', line: { color: C.green, width: 2.5 }, marker: { size: 4 },
      yaxis: 'y2',
      hovertemplate: '%{x}: %{customdata}<extra>Value</extra>',
      customdata: years.map(y => fmt$(sum(yg[y], 'committed_usd'))),
    },
  ], {
    ...LAYOUT_BASE,
    xaxis: { gridcolor: 'transparent', linecolor: C.border },
    yaxis: { gridcolor: C.border, zeroline: false, title: 'Deals', side: 'left' },
    yaxis2: { overlaying: 'y', side: 'right', zeroline: false, gridcolor: 'transparent', title: 'USD' },
    legend: { orientation: 'h', y: 1.1, x: .5, xanchor: 'center', font: { size: 11 } },
  }, CFG);

  // ═══ Sector evolution — stacked area (replaces heatmap) ═══
  const topSectors = topN(secGrp, 6, a => sum(a, 'committed_usd')).map(s => s.key);
  const areaTraces = topSectors.map((sec, i) => ({
    x: years,
    y: years.map(y => sum(d.filter(p => p.sector === sec && p.year === y), 'committed_usd')),
    name: sec, type: 'scatter', mode: 'lines', stackgroup: 'one',
    line: { color: PALETTE[i], width: 0 },
    fillcolor: PALETTE[i] + 'AA',
    hovertemplate: sec + '<br>%{x}: %{customdata}<extra></extra>',
    customdata: years.map(y => fmt$(sum(d.filter(p => p.sector === sec && p.year === y), 'committed_usd'))),
  }));
  Plotly.newPlot('fdiSectorTrendChart', areaTraces, {
    ...LAYOUT_BASE, margin: { t: 10, b: 40, l: 55, r: 20 },
    xaxis: { gridcolor: 'transparent', linecolor: C.border },
    yaxis: { gridcolor: C.border, zeroline: false, title: 'USD' },
    legend: { font: { size: 10 }, orientation: 'h', y: 1.12, x: .5, xanchor: 'center' },
  }, CFG);

  // ═══ Deals table ═══
  renderFDITable(d);

  // ═══ Region bar ═══
  renderFDIRegion(d);

  // ═══ Top deals narrative ═══
  const top3 = [...d].sort((a, b) => (b.committed_usd || 0) - (a.committed_usd || 0)).slice(0, 3);
  document.getElementById('fdiDealsNarrative').innerHTML = top3.length ? `
    <p class="narrative">
      The three largest deals account for
      <span class="stat">${fmt$(top3.reduce((s, x) => s + (x.committed_usd || 0), 0))}</span>
      — ${fmtP(top3.reduce((s, x) => s + (x.committed_usd || 0), 0) / (total || 1))} of total FDI value.
      ${top3[0].sector === 'Metals' ? 'Metals dominates the top tier, reflecting Indonesia\'s nickel processing boom.' : ''}
    </p>
  ` : '';
}

// ════════════════════════════════════════════════════════════════════
// MAPS
// ════════════════════════════════════════════════════════════════════
function renderDFMap() {
  if (!dfMap) {
    dfMap = L.map('dfMap', { center: [-2.5, 118], zoom: 5, zoomControl: true, scrollWheelZoom: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap', maxZoom: 12
    }).addTo(dfMap);
  }
  dfMarkers.forEach(m => dfMap.removeLayer(m)); dfMarkers = [];

  DF_REPORT_PROVINCES.forEach(p => {
    const c = PROVINCE_COORDS[p.province_name]; if (!c) return;
    const r = Math.max(6, Math.sqrt(p.project_value_2024_usd_b * 1e9) / 18000);
    const m = L.circleMarker(c, {
      radius: Math.min(r, 32), fillColor: C.gold, color: '#8B6914',
      weight: 1, opacity: .8, fillOpacity: .45,
    }).addTo(dfMap);
    m.bindPopup(`<strong>${p.province_name}</strong><br><span style="color:${C.muted}">${p.region}</span><br>${p.project_count} projects · $${p.project_value_2024_usd_b.toFixed(2)}B<br>$${p.per_capita_2024_usd.toFixed(0)} per capita`);
    dfMarkers.push(m);
  });
  setTimeout(() => dfMap.invalidateSize(), 200);
}

function renderFDIMap(data) {
  if (!fdiMap) {
    fdiMap = L.map('fdiMap', { center: [-2.5, 118], zoom: 5, zoomControl: true, scrollWheelZoom: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap', maxZoom: 12
    }).addTo(fdiMap);
  }
  fdiMarkers.forEach(m => fdiMap.removeLayer(m)); fdiMarkers = [];

  // Sector color mapping for FDI map markers
  const sectorColors = {
    'Metals': '#608B4E', 'Energy': '#D75F5F', 'Transport': '#4A7FB5',
    'Technology': '#7B68A8', 'Finance': '#B58900', 'Real Estate': '#2D9C8F',
    'Agriculture': '#6B8E23', 'Logistics': '#D87F33', 'Chemicals': '#A0522D', 'Other': '#928374'
  };

  data.forEach(d => {
    if (d.latitude == null || d.latitude > 90 || d.latitude < -90) return;
    const v = d.committed_usd || 0;
    const r = Math.max(5, Math.min(Math.sqrt(v) / 12000, 28));
    const col = sectorColors[d.sector] || C.green;
    const m = L.circleMarker([d.latitude, d.longitude || 0], {
      radius: r, fillColor: col, color: col,
      weight: 1.5, opacity: .9, fillOpacity: .5,
    }).addTo(fdiMap);
    m.bindPopup(`<strong style="font-size:12px">${d.project_name || 'Unnamed'}</strong><br><span style="color:${C.muted}">${d.sector || ''} · ${d.year}</span><br>Value: ${fmt$(v)}<br>Status: ${d.status || '—'}`);
    fdiMarkers.push(m);
  });
  setTimeout(() => fdiMap.invalidateSize(), 200);
}

// ════════════════════════════════════════════════════════════════════
// TABLES
// ════════════════════════════════════════════════════════════════════
function renderDFTable() {
  const tbody = document.getElementById('dfProvinceTableBody');
  const sorted = [...DF_REPORT_PROVINCES].sort((a, b) => b.project_value_2024_usd_b - a.project_value_2024_usd_b);
  tbody.innerHTML = sorted.map(p => `<tr>
    <td>${p.region}</td><td><strong>${p.province_name}</strong></td>
    <td class="number">${p.project_count}</td>
    <td class="number">$${p.project_value_2024_usd_b.toFixed(2)}B</td>
    <td class="number">$${p.per_capita_2024_usd.toFixed(0)}</td>
  </tr>`).join('');
}

function renderFDITable(data) {
  const tbody = document.getElementById('fdiDealsTableBody');
  const sorted = [...data].sort((a, b) => (b.committed_usd || 0) - (a.committed_usd || 0));
  tbody.innerHTML = sorted.map(d => `<tr>
    <td class="number">${d.year || '—'}</td>
    <td>${d.project_name || 'Unnamed'}</td>
    <td>${d.sector || '—'}</td>
    <td class="number"><strong>${fmt$(d.committed_usd)}</strong></td>
    <td>${d.status || '—'}</td>
  </tr>`).join('');
}

function renderFDIRegion(data) {
  const rm = {};
  data.forEach(d => {
    if (d.latitude == null || d.latitude > 90 || d.latitude < -90) return;
    let region = 'Other';
    const lat = d.latitude, lng = d.longitude || 0;
    if (lat > -7 && lat < 7 && lng < 108) region = 'Sumatra';
    else if (lat > -9 && lat < -5 && lng >= 105 && lng < 115) region = 'Java';
    else if (lat > -5 && lat < 5 && lng >= 108 && lng < 118) region = 'Kalimantan';
    else if (lat > -6 && lat < 3 && lng >= 118 && lng < 128) region = 'Sulawesi';
    else if (lat > -10 && lat < -7 && lng >= 115 && lng < 125) region = 'Nusa Tenggara';
    else if (lng >= 125 && lng < 136) region = 'Maluku';
    else if (lng >= 136) region = 'Papua';
    if (!rm[region]) rm[region] = [];
    rm[region].push(d);
  });
  const regions = Object.keys(rm).sort((a, b) => sum(rm[b], 'committed_usd') - sum(rm[a], 'committed_usd'));
  if (!regions.length) return;
  Plotly.newPlot('fdiRegionChart', [{
    x: regions, y: regions.map(r => sum(rm[r], 'committed_usd')),
    type: 'bar',
    marker: { color: PALETTE.slice(0, regions.length), opacity: .8 },
    text: regions.map(r => rm[r].length + ' deals'), textposition: 'outside', textfont: { size: 10 },
    hovertemplate: '%{x}<br>%{customdata}<extra></extra>',
    customdata: regions.map(r => fmt$(sum(rm[r], 'committed_usd'))),
  }], {
    ...LAYOUT_BASE,
    xaxis: { gridcolor: 'transparent' },
    yaxis: { gridcolor: C.border, zeroline: false, title: 'USD' },
  }, CFG);
}

// ════════════════════════════════════════════════════════════════════
// TABLE SORTING
// ════════════════════════════════════════════════════════════════════
function initSorting() {
  document.querySelectorAll('.data-table').forEach(table => {
    table.querySelectorAll('thead th[data-sort]').forEach(th => {
      th.addEventListener('click', () => {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const idx = Array.from(th.parentElement.children).indexOf(th);
        const asc = th.classList.contains('sort-asc');
        table.querySelectorAll('th').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
        th.classList.add(asc ? 'sort-desc' : 'sort-asc');
        const dir = asc ? -1 : 1;
        rows.sort((a, b) => {
          let va = a.children[idx]?.textContent.trim() || '';
          let vb = b.children[idx]?.textContent.trim() || '';
          const na = parseFloat(va.replace(/[$,BT%]/g, ''));
          const nb = parseFloat(vb.replace(/[$,BT%]/g, ''));
          if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
          return va.localeCompare(vb) * dir;
        });
        rows.forEach(r => tbody.appendChild(r));
      });
    });
  });
}

// ════════════════════════════════════════════════════════════════════
// UI
// ════════════════════════════════════════════════════════════════════
function toggleCollapsible(trigger) {
  trigger.classList.toggle('open');
  trigger.nextElementSibling.classList.toggle('open');
}

function initScroll() {
  const bar = document.getElementById('scrollProgress');
  window.addEventListener('scroll', () => {
    const pct = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.transform = `scaleX(${pct > 0 ? window.scrollY / pct : 0})`;
  });
}

// ════════════════════════════════════════════════════════════════════
// INIT
// ════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-item').forEach(i => i.addEventListener('click', () => navigate(i.dataset.page)));
  document.querySelectorAll('.cta-card[data-nav]').forEach(c => c.addEventListener('click', () => navigate(c.dataset.nav)));
  document.getElementById('sidebarToggle').addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    setSidebarOpen(!sidebar.classList.contains('open'));
  });
  document.getElementById('mainContent').addEventListener('click', () => {
    if (window.innerWidth <= 900) setSidebarOpen(false);
  });

  normalizeProjects(PROJECTS);
  assignFDICoords(PROJECTS);
  initFilters();
  initSorting();
  initScroll();

  const hash = location.hash.replace('#', '');
  if (['home', 'df', 'fdi'].includes(hash)) navigate(hash);
  else renderHome();
});
