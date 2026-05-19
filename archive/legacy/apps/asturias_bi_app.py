# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template_string


app = Flask(__name__)


DATA = {
    "program": {
        "name": "Especialización en Inteligencia de Negocios",
        "current_credits": 26,
        "target_credits": 24,
        "reduction": 2,
    },
    "benchmark": [
        {
            "name": "UniAsturias",
            "credits": 26,
            "note": "Base actual del programa.",
        },
        {
            "name": "UNIR Colombia",
            "credits": 24,
            "note": "Referencia compacta y competitiva.",
        },
        {
            "name": "UCM",
            "credits": 23,
            "note": "Malla corta, bien enfocada en BI.",
        },
        {
            "name": "UNAC",
            "credits": 30,
            "note": "Más técnica y más pesada.",
        },
        {
            "name": "EIDEC",
            "credits": 29,
            "note": "Enfoque robusto en negocio y tecnología.",
        },
        {
            "name": "UNAD",
            "credits": 22,
            "note": "Demuestra que una especialización compacta sí vende.",
        },
    ],
    "skills": [
        ("SQL", 100),
        ("Power BI", 100),
        ("Python", 85),
        ("ETL / modelado", 82),
        ("Dashboards / storytelling", 78),
        ("Tableau / Qlik / Looker", 70),
        ("Cloud / BigQuery / Fabric / AWS", 58),
        ("Excel / DAX", 55),
    ],
    "proposal": [
        {
            "title": "Unificar innovación y transformación digital",
            "text": "Fusiona Innovación y Cultura Organizativa con Transformación Digital Empresarial en una sola unidad.",
        },
        {
            "title": "Mantener 12 asignaturas de 2 créditos",
            "text": "Cada semestre queda con 6 asignaturas: 4 núcleo, 1 electiva y 1 opción de grado.",
        },
        {
            "title": "Mantener la promesa comercial",
            "text": "El relato no es 'menos créditos', sino 'más foco, menos redundancia y más empleabilidad'.",
        },
    ],
    "curriculum": [
        "Fundamentos BI y toma de decisiones",
        "Arquitectura, bases de datos y modelado",
        "ETL, calidad y gobierno del dato",
        "Visualización, dashboards y storytelling",
        "Electiva I",
        "Opción de grado I",
        "Transformación e innovación organizacional",
        "Analítica aplicada y experimentación digital",
        "BI para e-commerce y mercado digital",
        "Sistemas y plataformas tecnológicas",
        "Electiva II",
        "Opción de grado II",
    ],
}


TEMPLATE = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ program.name }} | Demo comercial</title>
  <style>
    :root{
      --bg:#07111c;
      --bg2:#0d1d2f;
      --panel:rgba(14,31,51,.84);
      --line:rgba(160,187,214,.18);
      --text:#ecf2f7;
      --muted:#a9bbca;
      --accent:#63d2c6;
      --accent2:#f4b860;
      --accent3:#8fb8ff;
      --radius:22px;
      --shadow:0 20px 50px rgba(0,0,0,.35);
    }
    *{box-sizing:border-box}
    html{scroll-behavior:smooth}
    body{
      margin:0;
      color:var(--text);
      font-family:"Aptos","Segoe UI","Trebuchet MS",sans-serif;
      background:
        radial-gradient(circle at top left, rgba(99,210,198,.18), transparent 32%),
        radial-gradient(circle at top right, rgba(244,184,96,.15), transparent 28%),
        linear-gradient(180deg, #09111b 0%, #0b1725 38%, #06111c 100%);
      min-height:100vh;
    }
    body::before{
      content:"";
      position:fixed;inset:0;pointer-events:none;
      background-image:
        linear-gradient(rgba(255,255,255,.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.02) 1px, transparent 1px);
      background-size:48px 48px;
      mask-image:linear-gradient(180deg, rgba(0,0,0,.85), transparent 100%);
      opacity:.55;
    }
    .wrap{width:min(1240px, calc(100% - 32px)); margin:0 auto; padding:22px 0 48px; position:relative}
    .topbar{
      display:flex; justify-content:space-between; align-items:center; gap:16px;
      margin-bottom:18px; padding:8px 2px; position:sticky; top:0; backdrop-filter:blur(10px); z-index:5;
    }
    .brand{display:flex; flex-direction:column; gap:4px}
    .brand small{color:var(--muted); letter-spacing:.06em; text-transform:uppercase; font-size:.75rem}
    .brand strong{font-size:1rem; font-weight:700}
    .actions{display:flex; gap:10px; flex-wrap:wrap; justify-content:flex-end}
    .btn{
      appearance:none; border:1px solid var(--line); background:rgba(255,255,255,.04); color:var(--text);
      padding:10px 14px; border-radius:999px; cursor:pointer; text-decoration:none; font-size:.92rem;
      transition:transform 180ms ease, background 180ms ease, border-color 180ms ease;
    }
    .btn:hover{transform:translateY(-1px); background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.22)}
    .panel{
      background:linear-gradient(180deg, rgba(18,36,58,.92), rgba(9,20,33,.96));
      border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); overflow:hidden;
    }
    .hero{display:grid; grid-template-columns:1.6fr 1fr; gap:18px; align-items:stretch}
    .hero-main{padding:30px; min-height:420px; position:relative}
    .hero-main::after{
      content:""; position:absolute; inset:auto -80px -90px auto; width:260px; height:260px; border-radius:50%;
      background:radial-gradient(circle, rgba(99,210,198,.42), transparent 62%); filter:blur(8px); pointer-events:none;
    }
    .eyebrow{
      display:inline-flex; align-items:center; gap:8px; padding:7px 12px; border-radius:999px;
      background:rgba(99,210,198,.12); color:#bff4ee; border:1px solid rgba(99,210,198,.24);
      font-size:.82rem; letter-spacing:.04em; text-transform:uppercase;
    }
    h1{margin:18px 0 10px; font-size:clamp(2rem, 4vw, 3.65rem); line-height:.98; letter-spacing:-.04em; max-width:14ch}
    .lede{font-size:1.04rem; color:#d8e4ee; line-height:1.6; max-width:68ch}
    .hero-meta{display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:24px}
    .stat{padding:14px 16px; border-radius:16px; background:rgba(255,255,255,.04); border:1px solid var(--line)}
    .stat span{display:block; color:var(--muted); font-size:.8rem; margin-bottom:6px}
    .stat strong{font-size:1.45rem; letter-spacing:-.03em}
    .hero-side{padding:22px; display:grid; gap:14px; align-content:start}
    .card{background:rgba(255,255,255,.035); border:1px solid var(--line); border-radius:18px; padding:18px}
    .card h3{margin:0 0 8px; font-size:1rem}
    .card p{margin:0; color:var(--muted); line-height:1.55; font-size:.95rem}
    .grid-2{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; margin-top:18px}
    .section{padding:22px}
    .section h2{margin:0 0 8px; font-size:1.35rem; letter-spacing:-.02em}
    .section .sub{margin:0 0 18px; color:var(--muted); line-height:1.55}
    .table-wrap{overflow-x:auto; border-radius:18px; border:1px solid var(--line)}
    table{width:100%; border-collapse:collapse; background:rgba(255,255,255,.02); min-width:760px}
    th, td{text-align:left; padding:14px; vertical-align:top; border-bottom:1px solid rgba(160,187,214,.12); font-size:.94rem}
    th{color:#d9e8f4; background:rgba(255,255,255,.04); font-weight:700}
    .badge{display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; font-size:.78rem; color:#d9e8f4; background:rgba(255,255,255,.03); margin-right:8px; margin-bottom:8px; border:1px solid rgba(255,255,255,.12)}
    .badge.good{border-color:rgba(130,224,170,.25); color:#c8f2d8; background:rgba(130,224,170,.08)}
    .badge.warn{border-color:rgba(244,184,96,.25); color:#ffe2b1; background:rgba(244,184,96,.08)}
    .bars{display:grid; gap:14px}
    .bar-row{display:grid; grid-template-columns:180px 1fr 64px; gap:12px; align-items:center}
    .bar-label{color:#d9e8f4; font-size:.95rem}
    .bar-track{position:relative; height:14px; border-radius:999px; background:rgba(255,255,255,.06); overflow:hidden; border:1px solid rgba(255,255,255,.07)}
    .bar-fill{position:absolute; inset:0 auto 0 0; border-radius:999px; background:linear-gradient(90deg, var(--accent), var(--accent3)); box-shadow:0 0 22px rgba(99,210,198,.22)}
    .bar-value{text-align:right; color:var(--muted); font-variant-numeric:tabular-nums}
    .pill-grid{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px}
    .pill{border:1px solid var(--line); border-radius:18px; padding:16px; background:rgba(255,255,255,.03)}
    .pill h4{margin:0 0 8px; font-size:1rem}
    .pill p{margin:0; color:var(--muted); line-height:1.55; font-size:.93rem}
    .proposal{display:grid; gap:12px}
    .proposal-item{border-left:4px solid var(--accent); padding:14px 16px; background:rgba(255,255,255,.03); border-radius:14px}
    .proposal-item strong{display:block; margin-bottom:6px}
    .proposal-item span{color:var(--muted); font-size:.92rem; line-height:1.5; display:block}
    .smallcaps{text-transform:uppercase; letter-spacing:.08em; font-size:.74rem; color:var(--muted)}
    .footer{padding:22px; margin-top:18px; color:var(--muted); font-size:.88rem; line-height:1.6}
    .note{margin-top:12px; padding:12px 14px; border-radius:14px; background:rgba(244,184,96,.09); border:1px solid rgba(244,184,96,.22); color:#ffe7bf; line-height:1.55}
    @media (max-width:980px){
      .hero,.grid-2,.pill-grid,.bar-row{grid-template-columns:1fr}
      .hero-main{min-height:unset}
      .hero-meta{grid-template-columns:1fr}
      .bar-value{text-align:left}
      .actions{justify-content:flex-start}
    }
    @media print{
      body{background:white;color:black}
      body::before,.topbar,.actions{display:none !important}
      .panel{box-shadow:none !important}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="brand">
        <small>Demo comercial para vicerrectoría</small>
        <strong>{{ program.name }}</strong>
      </div>
      <div class="actions">
        <a class="btn" href="#comparacion">Benchmark</a>
        <a class="btn" href="#skills">Skills</a>
        <a class="btn" href="#propuesta">Propuesta 24</a>
        <button class="btn" onclick="window.print()">PDF</button>
      </div>
    </div>

    <section class="hero">
      <div class="panel hero-main">
        <div class="eyebrow">UniAsturias | inteligencia de negocios | venta académica</div>
        <h1>Una app para vender la reducción de 26 a 24 créditos.</h1>
        <p class="lede">
          Esta versión convierte el análisis en una experiencia interactiva: compara el programa con universidades
          de referencia, muestra skills reales del mercado y presenta una propuesta clara de ajuste curricular.
        </p>
        <div class="hero-meta">
          <div class="stat"><span>Créditos actuales</span><strong>{{ program.current_credits }}</strong></div>
          <div class="stat"><span>Créditos propuestos</span><strong>{{ program.target_credits }}</strong></div>
          <div class="stat"><span>Reducción</span><strong>{{ program.reduction }}</strong></div>
        </div>
        <div class="note">
          <strong>Mensaje de venta:</strong> no se trata de recortar por recortar, sino de hacer más legible la propuesta,
          eliminar redundancias y dejar una malla más alineada con el mercado.
        </div>
      </div>
      <aside class="panel hero-side">
        <div class="card">
          <h3>Qué resuelve</h3>
          <p>Ayuda a explicar por qué 24 créditos es una mejor historia comercial y académica que 26.</p>
        </div>
        <div class="card">
          <h3>Cómo se vende</h3>
          <p>Con lenguaje de empleabilidad, benchmark, foco y simplificación, no solo con argumentos curriculares.</p>
        </div>
        <div class="card">
          <h3>Qué muestra</h3>
          <p>Benchmark, demanda laboral, propuesta de malla y un discurso rector listo para tomar decisiones.</p>
        </div>
      </aside>
    </section>

    <section id="comparacion" class="panel section" style="margin-top:18px;">
      <h2>Benchmark de programas</h2>
      <p class="sub">La comparación deja una idea simple: 24 créditos está dentro de una banda competitiva para una especialización de este tipo.</p>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Institución</th><th>Créditos</th><th>Lectura</th></tr>
          </thead>
          <tbody id="benchmark-body"></tbody>
        </table>
      </div>
    </section>

    <div class="grid-2">
      <section id="skills" class="panel section">
        <h2>Skills del mercado</h2>
        <p class="sub">Lo que más aparece en ofertas recientes para BI y data roles.</p>
        <div class="bars" id="skill-bars"></div>
      </section>
      <section class="panel section">
        <h2>Historia de venta</h2>
        <div class="pill-grid">
          <div class="pill"><h4>1. Problema</h4><p>La malla actual tiene solapes que confunden el valor percibido.</p></div>
          <div class="pill"><h4>2. Oportunidad</h4><p>El mercado premia perfiles que conectan datos, negocio y visualización.</p></div>
          <div class="pill"><h4>3. Solución</h4><p>Reducir a 24 créditos con una sola fusión fuerte y estructura de 12 cursos.</p></div>
          <div class="pill"><h4>4. Resultado</h4><p>Una especialización más fácil de explicar, vender y operar académicamente.</p></div>
        </div>
      </section>
    </div>

    <section id="propuesta" class="panel section" style="margin-top:18px;">
      <h2>Propuesta curricular</h2>
      <p class="sub">Cada semestre: 6 asignaturas de 2 créditos, incluyendo una electiva y una opción de grado.</p>
      <div class="grid-2">
        <div class="proposal">
          {% for item in proposal %}
          <div class="proposal-item">
            <strong>{{ item.title }}</strong>
            <span>{{ item.text }}</span>
          </div>
          {% endfor %}
        </div>
        <div class="panel" style="padding:18px; background:rgba(255,255,255,.025);">
          <div class="smallcaps">12 cursos de 2 créditos</div>
          <h3 style="margin:10px 0 10px;">24 créditos totales</h3>
          <div class="bars" id="curriculum-bars"></div>
        </div>
      </div>
    </section>

    <section class="panel footer">
      <div class="smallcaps">Uso recomendado</div>
      <p style="margin-top:10px">
        Esta app funciona como demo comercial en reuniones con vicerrectoría. Si quieres, el siguiente paso puede ser
        convertirla en una app con menú lateral, filtros por microcurrículo y botón para exportar un resumen ejecutivo.
      </p>
    </section>
  </div>
  <script>
    const benchmark = {{ benchmark | tojson }};
    const skills = {{ skills | tojson }};
    const curriculum = {{ curriculum | tojson }};

    function renderBenchmark() {
      const root = document.getElementById("benchmark-body");
      root.innerHTML = "";
      benchmark.forEach(item => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><strong>${item.name}</strong></td><td><span class="badge good">${item.credits}</span></td><td>${item.note}</td>`;
        root.appendChild(tr);
      });
    }

    function renderBars(targetId, data, valueIndex = 1) {
      const root = document.getElementById(targetId);
      const max = Math.max(...data.map(d => d[valueIndex]), 100);
      root.innerHTML = "";
      data.forEach(item => {
        const row = document.createElement("div");
        row.className = "bar-row";
        const label = document.createElement("div");
        label.className = "bar-label";
        label.innerHTML = `<strong>${item[0]}</strong>`;
        const track = document.createElement("div");
        track.className = "bar-track";
        const fill = document.createElement("div");
        fill.className = "bar-fill";
        fill.style.width = Math.max((item[valueIndex] / max) * 100, 8) + "%";
        track.appendChild(fill);
        const value = document.createElement("div");
        value.className = "bar-value";
        value.textContent = item[valueIndex] + "%";
        row.appendChild(label);
        row.appendChild(track);
        row.appendChild(value);
        root.appendChild(row);
      });
    }

    function renderCurriculum() {
      const root = document.getElementById("curriculum-bars");
      root.innerHTML = "";
      curriculum.forEach((name, idx) => {
        const row = document.createElement("div");
        row.className = "bar-row";
        row.style.gridTemplateColumns = "1fr 72px";
        row.innerHTML = `<div><strong>${idx + 1}. ${name}</strong></div><div class="bar-value"><span class="badge good" style="margin:0">2 cr</span></div>`;
        root.appendChild(row);
      });
    }

    renderBenchmark();
    renderBars("skill-bars", skills);
    renderCurriculum();
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(TEMPLATE, **DATA)


if __name__ == "__main__":
    raise SystemExit("Run with gunicorn -w 4 -b 0.0.0.0:5000 asturias_bi_app:app")
