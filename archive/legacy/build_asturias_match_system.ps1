param(
    [string]$DataPath = (Join-Path $PSScriptRoot 'asturias_scraped_comparison.json'),
    [string]$OutputPath = (Join-Path $PSScriptRoot 'asturias_match_system.html')
)

$ErrorAcciónPreference = 'Stop'

if (-not (Test-Path -LiteralPath $DataPath)) {
    throw "Data file not found: $DataPath"
}

$json = Get-Content -LiteralPath $DataPath -Raw -Encoding UTF8
$json = $json -replace '</script>', '<\/script>'

$template = @'
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Sistema de coincidencia Asturias</title>
  <style>
    :root{
      --bg:#07131f;
      --panel:rgba(13,27,44,.94);
      --line:rgba(160,187,214,.16);
      --text:#ecf3f9;
      --muted:#a8b9c9;
      --accent:#61d1c7;
      --accent2:#8fb8ff;
      --good:#82e0aa;
      --warn:#ffd27d;
      --shadow:0 18px 45px rgba(0,0,0,.32);
      --radius:20px;
    }
    *{box-sizing:border-box}
    body{margin:0;font-family:Segoe UI,Aptos,sans-serif;color:var(--text);background:radial-gradient(circle at top,rgba(97,209,199,.10),transparent 28%),linear-gradient(180deg,#09111b 0,#0b1725 42%,#06111c 100%);min-height:100vh}
    .wrap{width:min(1380px,calc(100% - 24px));margin:0 auto;padding:18px 0 40px}
    .top{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;position:sticky;top:0;backdrop-filter:blur(10px);padding:8px 0;z-index:10}
    .brand small{display:block;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-size:.75rem}
    .brand strong{font-size:1rem}
    .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
    .btn,.chip,.ex{border:1px solid var(--line);background:rgba(255,255,255,.04);color:var(--text);border-radius:999px;padding:9px 12px;text-decoration:none;cursor:pointer}
    .btn:hover,.ex:hover{background:rgba(255,255,255,.08)}
    .panel{background:linear-gradient(180deg,rgba(20,38,60,.92),rgba(9,20,33,.96));border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow)}
    .hero{padding:22px;margin-bottom:16px}
    .hero h1{margin:14px 0 8px;font-size:clamp(2rem,4vw,3.45rem);line-height:1;letter-spacing:-.05em;max-width:14ch}
    .hero p{margin:0;color:#d7e3ed;line-height:1.6;max-width:82ch}
    .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}
    .stat{padding:13px 14px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.04)}
    .stat span{display:block;color:var(--muted);font-size:.77rem;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
    .stat strong{font-size:1.15rem}
    .grid{display:grid;grid-template-columns:320px 1fr;gap:16px}
    .side{padding:16px;position:sticky;top:74px;height:max-content}
    .field{margin-bottom:12px}
    .field label{display:block;margin-bottom:6px;font-size:.9rem;color:#d9e8f4}
    input,select{width:100%;padding:11px 12px;border-radius:14px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);color:var(--text)}
    .note{margin-top:12px;padding:12px 14px;border:1px solid rgba(244,184,96,.22);background:rgba(244,184,96,.08);border-radius:14px;color:#ffe7bf;line-height:1.55}
    .main{display:grid;gap:16px}
    .results{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}
    .card{padding:16px;border-radius:16px;background:rgba(255,255,255,.035);border:1px solid var(--line)}
    .card h2,.card h3{margin:0 0 8px}
    .muted{color:var(--muted)}
    .badge{display:inline-block;padding:6px 10px;border-radius:999px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.12);font-size:.78rem;margin:0 6px 6px 0}
    .good{border-color:rgba(130,224,170,.26);background:rgba(130,224,170,.08)}
    .warn{border-color:rgba(244,184,96,.26);background:rgba(244,184,96,.08)}
    .info{border-color:rgba(143,184,255,.26);background:rgba(143,184,255,.08)}
    .score{display:flex;gap:12px;align-items:center;margin-top:10px}
    .ring{--p:0;width:88px;height:88px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--accent) calc(var(--p)*1%),rgba(255,255,255,.08) 0)}
    .ring span{width:66px;height:66px;border-radius:50%;display:grid;place-items:center;background:#0f1b2b;font-weight:700}
    .bars{display:grid;gap:10px}
    .bar{display:grid;grid-template-columns:190px 1fr 60px;gap:10px;align-items:center}
    .track{height:12px;border-radius:999px;background:rgba(255,255,255,.06);overflow:hidden;border:1px solid rgba(255,255,255,.08)}
    .fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
    .two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    .three{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
    .pill{padding:12px;border:1px solid var(--line);border-radius:14px;background:rgba(255,255,255,.03)}
    .list{display:grid;gap:10px}
    .item{padding:12px 14px;border-left:4px solid var(--accent);border-radius:12px;background:rgba(255,255,255,.03)}
    .item strong{display:block;margin-bottom:4px}
    .item span{color:var(--muted);font-size:.92rem;line-height:1.5}
    table{width:100%;border-collapse:collapse;min-width:1100px}
    th,td{padding:10px 12px;border-bottom:1px solid rgba(160,187,214,.12);text-align:left;vertical-align:top;font-size:.93rem}
    th{background:rgba(255,255,255,.04)}
    td small{color:var(--muted)}
    .examples{display:flex;gap:8px;flex-wrap:wrap}
    .footer-note{font-size:.86rem;color:var(--muted);margin-top:8px}
    @media(max-width:1040px){
      .grid,.results,.two,.three,.stats{grid-template-columns:1fr}
      .side{position:relative;top:auto}
    }
  </style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="brand">
      <small>Sistema de coincidencia Asturias</small>
      <strong>Mapeo curricular, benchmarking y comparacion</strong>
    </div>
    <div class="row">
      <button class="btn" id="refresh">Actualizar vista</button>
      <button class="btn" id="print">Imprimir</button>
    </div>
  </div>

  <section class="panel hero">
    <div class="badge info">Cargado automaticamente</div>
    <h1>Busca una asignatura o un programa y obten su coincidencia curricular.</h1>
    <p>
      El sistema compara la especializacion de Asturias contra universidades de referencia,
      muestra las asignaturas y programas mas cercanos, y sugiere si conviene conservar,
      actualizar, fusionar o mover una asignatura a electiva.
    </p>
    <div class="stats" id="stats"></div>
  </section>

  <div class="grid">
    <aside class="panel side">
      <div class="field">
        <label>Buscar asignatura o programa</label>
        <input id="q" placeholder="Ejemplo: Transformacion digital">
      </div>
      <div class="field">
        <label>Modo</label>
        <select id="mode">
          <option value="auto">Auto</option>
          <option value="subject">Asignatura</option>
          <option value="program">Programa</option>
        </select>
      </div>
      <div class="field">
        <label>Ambito de comparacion</label>
        <select id="scope">
          <option value="both">Todo</option>
          <option value="local">Solo local</option>
          <option value="uni">Solo universidades</option>
        </select>
      </div>
      <div class="row">
        <button class="btn" id="go">Buscar</button>
        <button class="btn" id="clear">Limpiar</button>
      </div>
      <div class="row" style="margin-top:8px">
        <span class="badge info" id="dataState">Datos cargados</span>
        <span class="badge" id="jsonState">Datos embebidos</span>
      </div>

      <div class="field" style="margin-top:14px">
        <label>Ejemplos rapidos</label>
        <div class="examples">
          <button class="ex" data-x="Transformacion digital">Transformacion digital</button>
          <button class="ex" data-x="Inteligencia de Negocios">Inteligencia de Negocios</button>
          <button class="ex" data-x="Big Data">Big Data</button>
          <button class="ex" data-x="Mercadeo">Mercadeo</button>
          <button class="ex" data-x="Estrategia">Estrategia</button>
        </div>
      </div>
    </aside>

    <main class="main">
      <section class="panel card">
        <h2>Mejor coincidencia</h2>
        <div class="results">
          <div class="card">
            <h3 id="bestT">Sin bÃºsqueda</h3>
            <p class="muted" id="bestS">Escribe una consulta para empezar.</p>
            <div class="score">
              <div class="ring" id="ring"><span id="pct">0%</span></div>
              <div>
                <div id="badges"></div>
                <div class="muted" id="narr" style="margin-top:8px">La recomendacion aparecerÃ¡ aquÃ­.</div>
              </div>
            </div>
          </div>
          <div class="card">
            <h3>Recomendacion</h3>
            <div class="list" id="rec"></div>
          </div>
        </div>
      </section>

      <div class="two">
        <section class="panel card">
          <h2>Universidades mas cercanas</h2>
          <div class="bars" id="uniBars"></div>
        </section>
        <section class="panel card">
          <h2>Asignaturas mas cercanas</h2>
          <div class="list" id="localList"></div>
        </section>
      </div>

      <section class="panel card">
        <h2>Comparacion por universidad</h2>
        <div style="overflow:auto;border:1px solid var(--line);border-radius:14px">
          <table>
            <thead>
              <tr>
                <th>Universidad</th>
                <th>Programa</th>
                <th>Créditos</th>
                <th>Orientacion</th>
                <th>Señales</th>
                <th>Asignaturas top</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody id="uniTable"></tbody>
          </table>
        </div>
      </section>

      <section class="panel card">
        <h2>Matriz de ajuste por asignatura</h2>
        <div style="overflow:auto;border:1px solid var(--line);border-radius:14px">
          <table>
            <thead>
              <tr>
                <th>Asignatura</th>
                <th>Lectura</th>
                <th>Ajuste</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody id="adj"></tbody>
          </table>
        </div>
      </section>

      <section class="panel card">
        <h2>Skills del mercado</h2>
        <div class="three" id="skills"></div>
      </section>

      <section class="panel card">
        <h2>Valor diferencial</h2>
        <div class="three" id="differentials"></div>
      </section>

      <section class="panel card">
        <h2>Como funciona la coincidencia</h2>
        <div class="three">
          <div class="pill">
            <strong>1. Nombre</strong>
            <p class="muted">Cruza la consulta con los nombres de las asignaturas y de los programas.</p>
          </div>
          <div class="pill">
            <strong>2. Temas</strong>
            <p class="muted">Busca BI, analitica, estrategia, transformaciÃ³n digital y Big Data.</p>
          </div>
          <div class="pill">
            <strong>3. Decision</strong>
            <p class="muted">Sugiere conservar, actualizar, fusionar o mover a electiva.</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</div>

<script id="dataset" type="application/json">__DATA__</script>
<script>
const RAW_DATA = JSON.parse(document.getElementById('dataset').textContent);

function repairText(value){
  if (typeof value !== 'string') return value;
  try { return decodeURIComponent(escape(value)); } catch (e) { return value; }
}

function repairObject(value){
  if (Array.isArray(value)) return value.map(repairObject);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = repairObject(v);
    return out;
  }
  return repairText(value);
}

const DATA = repairObject(RAW_DATA);
const LOCAL = DATA.localProgram || {};
const PROGRAMS = DATA.benchmarkPrograms || [];

const SUBJECTS = (LOCAL.subjects || []).map(s => ({
  ...s,
  text: [s.title, s.type, s.semester, s.note || ''].join(' '),
  tags: subjectTags([s.title, s.type, s.note || ''].join(' '))
}));

function esc(v){
  return String(v ?? '')
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#39;');
}

function norm(s){
  return String(s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g,' ')
    .trim();
}

function tokens(s){
  const n = norm(s);
  const aliases = [
    ['bigdata', 'big data'],
    ['businessintelligence', 'business intelligence'],
    ['inteligenciadenegocios', 'inteligencia de negocios'],
    ['transformaciondigital', 'transformacion digital'],
    ['mercadedigital', 'mercadeo digital'],
    ['comercioelectronico', 'comercio electronico'],
    ['gobiernodato', 'gobierno dato']
  ];
  let expanded = n;
  for (const [from, to] of aliases) {
    expanded = expanded.replaceAll(from, to);
  }
  return expanded.split(/\s+/).filter(Boolean);
}

function overlap(a, b){
  const A = new Set(tokens(a));
  const B = new Set(tokens(b));
  let hit = 0;
  for (const t of A) if (B.has(t)) hit++;
  return hit / Math.max(new Set([...A, ...B]).size, 1);
}

function subjectTags(text){
  const n = norm(text);
  const tags = [];
  if (/business intelligence|\\bbi\\b|inteligencia de negocios/.test(n)) tags.push('BI');
  if (/analitica|analisis|data|datos/.test(n)) tags.push('Analytics');
  if (/big data|etl|data lake|cloud|computacion distribuida/.test(n)) tags.push('Big Data');
  if (/transformacion|digital|innovacion/.test(n)) tags.push('Digital');
  if (/estrategia|gerencia|proyecto|competitiva|negocio/.test(n)) tags.push('Strategy');
  if (/mercadeo|marketing|e-commerce|comercio/.test(n)) tags.push('Market');
  if (/gobierno|etica|seguridad|calidad/.test(n)) tags.push('Governance');
  if (/programacion|bases de datos|sql|python|java|lenguajes/.test(n)) tags.push('Technical');
  if (/investigacion|seminario/.test(n)) tags.push('Research');
  return tags.length ? tags : ['General'];
}

function queryTags(q){
  const n = norm(q).replaceAll('bigdata', 'big data').replaceAll('businessintelligence', 'business intelligence').replaceAll('inteligenciadenegocios', 'inteligencia de negocios').replaceAll('transformaciondigital', 'transformacion digital').replaceAll('mercadedigital', 'mercadeo digital').replaceAll('comercioelectronico', 'comercio electronico');
  const tags = [];
  if (/business|bi|negocio/.test(n)) tags.push('BI');
  if (/analit|data|datos/.test(n)) tags.push('Analytics');
  if (/big/.test(n) && /data/.test(n)) tags.push('Big Data');
  if (/digital|transform/.test(n)) tags.push('Digital');
  if (/strategy|estrateg|gerencia|proyecto/.test(n)) tags.push('Strategy');
  if (/market|mercadeo|marketing|e-commerce|comercio/.test(n)) tags.push('Market');
  if (/gobierno|dato|quality|etica|seguridad/.test(n)) tags.push('Governance');
  if (/program|sql|python|java|database/.test(n)) tags.push('Technical');
  return tags.length ? tags : tokens(q).slice(0,4);
}

function tagScore(q, tags){
  const A = new Set(queryTags(q));
  const B = new Set(tags || []);
  let hit = 0;
  for (const t of A) if (B.has(t)) hit++;
  return hit / Math.max(Math.max(A.size, B.size), 1);
}

function subjectScore(q, s){
  const nq = norm(q);
  const nt = norm(s.title || '');
  const aliasBoost = [
    ['bigdata', 'big data'],
    ['transformaciondigital', 'transformacion digital'],
    ['inteligenciadenegocios', 'inteligencia de negocios'],
    ['mercadedigital', 'mercadeo digital']
  ].some(([from, to]) => nq.includes(from) && nt.includes(to)) ? 0.25 : 0;
  return (
    overlap(q, s.title) * 0.45 +
    overlap(q, s.text) * 0.35 +
    tagScore(q, s.tags) * 0.20 +
    aliasBoost
  );
}

function programTags(p){
  const parts = [
    p.university, p.program, p.summary, p.orientation, p.practiceStyle,
    ...(p.skills || []).map(x => x.skill || x.name || ''),
    ...(p.themes || []).map(x => x.theme || x.name || ''),
    ...(p.subjects || []).map(x => x.title || '')
  ].join(' ');
  return subjectTags(parts);
}

function programScore(q, p){
  const topAsignatura = (p.subjects || []).reduce((m, s) => Math.max(m, subjectScore(q, { title: s.title, text: s.title, tags: subjectTags(s.title) })), 0);
  const creditScore = Math.max(0, 1 - Math.abs((p.credits || 24) - 24) / 10);
  const nq = norm(q);
  const np = norm(p.program || '');
  const aliasBoost = [
    ['bigdata', 'big data'],
    ['transformaciondigital', 'transformacion digital'],
    ['inteligenciadenegocios', 'inteligencia de negocios']
  ].some(([from, to]) => nq.includes(from) && np.includes(to)) ? 0.2 : 0;
  return (
    overlap(q, p.program) * 0.28 +
    overlap(q, [p.program, p.summary, p.orientation, p.practiceStyle].join(' ')) * 0.32 +
    tagScore(q, programTags(p)) * 0.20 +
    topAsignatura * 0.15 +
    creditScore * 0.05 +
    aliasBoost
  );
}

function inferMode(q){
  const n = norm(q);
  if (/programa|especializacion|specialization|posgrado/.test(n)) return 'program';
  if (/asignatura|subject|materia/.test(n)) return 'subject';
  return 'auto';
}

function decisionForAsignatura(s){
  const n = norm(s.title);
  if (/innovacion/.test(n) && /transformacion/.test(n)) return ['Merge', 'Overlap with digital transformation'];
  if (/transformacion/.test(n)) return ['Update', 'Keep content but tighten outcomes'];
  if (/tendencias/.test(n)) return ['Update', 'Good as elective or transversal'];
  if (/economia colaborativa/.test(n)) return ['Elective', 'Peripheral to the core BI line'];
  return ['Update', 'Keep core and refine emphasis on analysis'];
}

function bestAsignaturas(q, items, limit){
  return items
    .map(item => ({ item, score: subjectScore(q, item) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function bestPrograms(q, items, limit){
  return items
    .map(item => ({ item, score: programScore(q, item) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

function renderStats(){
  const stats = [
    ['Asignaturas locales', SUBJECTS.length],
    ['Universidades', PROGRAMS.length],
    ['Asignaturas benchmark', PROGRAMS.reduce((acc, p) => acc + (p.subjects || []).length, 0)],
    ['Créditos base', LOCAL.credits || 26]
  ];
  document.getElementById('stats').innerHTML = stats.map(([k, v]) => `<div class="stat"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
}

function renderSkills(){
  const items = (LOCAL.skills || []).slice(0, 6).map(x => ({
    label: repairText(x.skill || x.name || ''),
    count: x.count || 0
  }));
  document.getElementById('skills').innerHTML = items.map(x => `
    <div class="pill">
      <strong>${esc(x.label)}</strong>
      <div class="muted" style="margin-top:4px">${esc(x.count)} senales</div>
    </div>
  `).join('') || '<div class="item">No hay datos de skills del mercado.</div>';
}

function competitivenessIndex(){
  const uniqueTags = new Set(SUBJECTS.flatMap(s => s.tags || []));
  const marketSignals = (LOCAL.skills || []).length;
  const benchmarkCount = PROGRAMS.length;
  const credits = LOCAL.credits || 26;
  const score = 35
    + Math.min(20, uniqueTags.size * 2)
    + Math.min(20, marketSignals * 2)
    + Math.min(10, benchmarkCount * 2)
    + (credits <= 24 ? 15 : credits <= 26 ? 12 : 8);
  return Math.min(100, Math.round(score));
}

function renderDifferentials(){
  const cci = competitivenessIndex();
  const cards = [
    { title: 'Comparacion con el mercado laboral', text: 'Cruza la malla con skills y tendencias de vacantes para responder que tanto se alinea con lo que pide el mercado hoy.' },
    { title: 'Índice de competitividad curricular', text: `CCI estimado: ${cci}/100. Resume cobertura temática, señal de mercado y compactación del plan.` },
    { title: 'Benchmarking inteligente', text: 'No solo muestra similitud. También sugiere que agregar, que retirar y dónde hay mejor práctica.' },
    { title: 'Redundancias y vacíos', text: 'Detecta temas repetidos y competencias no cubiertas para optimizar la propuesta curricular.' },
    { title: 'Simulación de impacto', text: 'Permite evaluar cómo cambia el índice si se ajusta una asignatura, se fusiona o se agrega una electiva.' },
    { title: 'Microcurrículo granular', text: 'Trabaja a nivel de temas, resultados de aprendizaje y evaluación, no solo a nivel de programa.' },
    { title: 'Dashboard ejecutivo', text: 'Presenta la información en una vista lista para comité, decanatura y vicerrectoría.' }
  ];
  document.getElementById('differentials').innerHTML = cards.map((c, i) => `
    <div class="pill">
      <strong>${esc(c.title)}</strong>
      <p class="muted" style="margin:8px 0 0;line-height:1.55">${esc(c.text)}</p>
    </div>
  `).join('');
}

function renderMatrix(){
  document.getElementById('adj').innerHTML = SUBJECTS.map(s => {
    const [action, reason] = decisionForAsignatura(s);
    const cls = action === 'Merge' ? 'warn' : action === 'Elective' ? 'info' : 'good';
    return `
      <tr>
        <td><strong>${esc(repairText(s.title))}</strong><br><small>${esc(s.credits || '')} créditos · ${esc(repairText(s.semester || ''))}</small></td>
        <td>${esc(repairText(s.type || ''))}</td>
        <td>${esc(reason)}</td>
        <td><span class="badge ${cls}" style="margin:0">${esc(action)}</span></td>
      </tr>
    `;
  }).join('');
}

function renderUniversityTable(results){
  document.getElementById('uniTable').innerHTML = results.map(r => {
    const p = r.item;
    const señales = (p.skills || []).slice(0, 3).map(x => repairText(x.skill || x.name || '')).join(' · ');
    const subjects = (p.subjects || []).slice(0, 3).map(x => repairText(x.title || '')).join('<br>');
    return `
      <tr>
        <td><strong>${esc(repairText(p.university))}</strong><br><small>${esc(p.url || '')}</small></td>
        <td>${esc(repairText(p.program))}</td>
        <td>${esc(p.credits || '')}</td>
        <td>${esc(repairText(p.orientation || ''))}<br><small>${esc(repairText(p.practiceStyle || ''))}</small></td>
        <td>${esc(señales || 'Sin señales')}</td>
        <td>${subjects || '<small>No disponible</small>'}</td>
        <td><span class="badge ${r.score >= .75 ? 'good' : r.score >= .55 ? 'info' : 'warn'}" style="margin:0">${Math.round(r.score * 100)}%</span></td>
      </tr>
    `;
  }).join('');
}

function renderLists(q, scope){
  const local = bestAsignaturas(q, SUBJECTS, 5);
  const programs = bestPrograms(q, PROGRAMS, 6);
  const allBenchAsignaturas = PROGRAMS.flatMap(p => (p.subjects || []).map(s => ({ ...s, university: p.university, program: p.program, tags: subjectTags(s.title), text: s.title })));
  const benchAsignaturas = bestAsignaturas(q, allBenchAsignaturas, 6);

  const bestLocal = local[0];
  const bestProgram = programs[0];
  const mode = inferMode(q);

  document.getElementById('bestT').textContent = bestLocal ? repairText(bestLocal.item.title) : 'Sin coincidencia';
  document.getElementById('bestS').textContent = bestLocal
    ? `${repairText(bestLocal.item.type || 'Asignatura')} · ${repairText(bestLocal.item.semester || '')} · ${bestLocal.item.credits || 0} créditos`
    : 'Escribe una consulta para empezar.';

  const pct = Math.round((bestLocal ? bestLocal.score : 0) * 100);
  document.getElementById('pct').textContent = `${pct}%`;
  document.getElementById('ring').style.setProperty('--p', pct);

  const badgeList = [
    `<span class="badge info">${esc(mode === 'auto' ? 'Auto' : mode)}</span>`,
    `<span class="badge info">${esc(q ? queryTags(q).join(', ') : 'General')}</span>`,
    `<span class="badge info">${esc(scope === 'both' ? 'Todo' : scope === 'local' ? 'Solo local' : 'Solo universidades')}</span>`
  ];
  document.getElementById('badges').innerHTML = badgeList.join('');

  document.getElementById('narr').textContent = bestProgram
    ? `La universidad más cercana es ${repairText(bestProgram.item.university)} y la asignatura benchmark más cercana es ${repairText(benchAsignaturas[0]?.item.title || '')}.`
    : 'No se encontró un referente externo fuerte.';

  document.getElementById('rec').innerHTML = [
    `<div class="item"><strong>Interpretación</strong><span>${bestLocal ? `La consulta se parece a ${repairText(bestLocal.item.title)}.` : 'No se encontró una asignatura local clara.'}</span></div>`,
    `<div class="item"><strong>Referencia externa</strong><span>${bestProgram ? `${repairText(bestProgram.item.university)} · ${repairText(bestProgram.item.program)} (${Math.round(bestProgram.score * 100)}%)` : 'No hay coincidencia de programa.'}</span></div>`,
    `<div class="item"><strong>Acción</strong><span>${bestLocal ? `${decisionForAsignatura(bestLocal.item)[0]} la asignatura local.` : 'Revisar primero el benchmark.'}</span></div>`
  ].join('');

  document.getElementById('localList').innerHTML = scope === 'uni'
    ? '<div class="item">El modo solo universidades está activo.</div>'
    : local.map(x => `
    <div class="item">
      <strong>${esc(repairText(x.item.title))}</strong>
      <div class="muted" style="margin-bottom:6px">${esc(repairText(x.item.type || ''))} · ${esc(repairText(x.item.semester || ''))} · ${esc(x.item.credits || '')} cr</div>
      <span>${esc(decisionForAsignatura(x.item)[1])}</span>
    </div>
  `).join('');

  document.getElementById('uniBars').innerHTML = programs.map(x => `
    <div class="bar">
      <div>
        <strong>${esc(repairText(x.item.university))}</strong>
        <div class="muted" style="font-size:.82rem;margin-top:3px">${esc(repairText(x.item.program))}</div>
      </div>
      <div class="track"><div class="fill" style="width:${Math.max(x.score * 100, 8)}%"></div></div>
      <div class="muted" style="text-align:right">${Math.round(x.score * 100)}%</div>
    </div>
  `).join('');

  document.getElementById('uniTable').innerHTML = scope === 'local'
    ? '<tr><td colspan="7">El modo solo local está activo.</td></tr>'
    : (programs.length ? '' : '<tr><td colspan="7">No hay universidades disponibles.</td></tr>');

  if (scope !== 'local') renderUniversityTable(programs);
  if (scope !== 'uni') {
    document.getElementById('localList').insertAdjacentHTML('beforeend',
      benchAsignaturas.map(x => `
      <div class="item">
        <strong>${esc(repairText(x.item.title || ''))}</strong>
        <div class="muted" style="margin-bottom:6px">${esc(repairText(x.item.university || ''))} · ${esc(repairText(x.item.program || ''))}</div>
        <span>Coincidencia de asignatura benchmark: ${Math.round(x.score * 100)}%</span>
      </div>
    `).join('')
    );
  }
}

function run(){
  const q = document.getElementById('q').value.trim() || 'Business Intelligence';
  const scope = document.getElementById('scope').value;
  document.getElementById('dataState').textContent = 'Datos cargados';
  document.getElementById('jsonState').textContent = `Actualizado ${repairText(DATA.generatedAt || '')}`.trim();
  renderStats();
  renderSkills();
  renderDifferentials();
  renderMatrix();
  renderLists(q, scope);
}

document.getElementById('go').addEventListener('click', run);
document.getElementById('clear').addEventListener('click', () => {
  document.getElementById('q').value = '';
  document.getElementById('mode').value = 'auto';
  document.getElementById('scope').value = 'both';
  run();
});
document.getElementById('refresh').addEventListener('click', run);
document.getElementById('print').addEventListener('click', () => window.print());
document.querySelectorAll('.ex').forEach(btn => btn.addEventListener('click', () => {
  document.getElementById('q').value = btn.dataset.x;
  run();
}));
document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') run(); });

renderStats();
run();
</script>
</body>
</html>
'@

$html = $template.Replace('__DATA__', $json)
Set-Content -LiteralPath $OutputPath -Value $html -Encoding UTF8
Write-Host "Created $OutputPath"




