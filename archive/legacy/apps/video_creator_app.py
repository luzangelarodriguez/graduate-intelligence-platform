# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template_string


app = Flask(__name__)


INDEX_HTML = r"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Creador de videos</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#05070b;--panel:rgba(14,18,26,.86);--stroke:rgba(255,255,255,.09);--text:#eef3ff;--muted:rgba(238,243,255,.72);--a:#ff6a3d;--b:#18d0c4;--c:#ffd166}
    *{box-sizing:border-box} html,body{height:100%}
    body{margin:0;color:var(--text);font:15px/1.5 "Inter",sans-serif;background:
      radial-gradient(circle at top left,rgba(255,106,61,.18),transparent 28%),
      radial-gradient(circle at top right,rgba(24,208,196,.14),transparent 24%),
      linear-gradient(135deg,#05070b 0%,#090d14 48%,#040507 100%)}
    body:before{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.03) 1px,transparent 1px);background-size:54px 54px;opacity:.25}
    .wrap{width:min(1450px,calc(100% - 24px));margin:0 auto;padding:20px 0 28px;position:relative;z-index:1}
    .hero,.layout{display:grid;gap:16px}.hero{grid-template-columns:1.2fr .8fr;margin-bottom:16px}.layout{grid-template-columns:minmax(0,1.1fr) minmax(360px,.9fr);align-items:start}
    .card{background:var(--panel);border:1px solid var(--stroke);backdrop-filter:blur(16px);box-shadow:0 28px 80px rgba(0,0,0,.42);border-radius:24px}
    .hero-left,.hero-right,.panel,.preview{padding:18px}
    .eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted);margin-bottom:12px}
    h1,h2{margin:0;font-family:"Space Grotesk",sans-serif;letter-spacing:-.04em}
    h1{font-size:clamp(34px,5vw,58px);line-height:.95}
    h2{font-size:22px;margin-bottom:10px}
    .copy{margin:12px 0 0;color:var(--muted);max-width:70ch}
    .chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
    .chip{padding:8px 11px;border-radius:999px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);font-size:13px}
    .stats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
    .stat{padding:14px;border-radius:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08)}
    .stat strong{display:block;font-size:20px;margin-bottom:6px}
    .stat span{color:var(--muted);font-size:13px}
    .grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
    .field{display:grid;gap:6px}.field label{font-size:13px;color:var(--muted)}
    input,select,textarea,button{font:inherit} input,select,textarea{
      width:100%;color:var(--text);background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:11px 13px;outline:0}
    textarea{min-height:110px;resize:vertical;line-height:1.55}
    input:focus,select:focus,textarea:focus{border-color:rgba(255,106,61,.8);box-shadow:0 0 0 4px rgba(255,106,61,.13)}
    .toolbar{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
    .btn{border:0;border-radius:14px;padding:11px 14px;cursor:pointer;font-weight:800;letter-spacing:-.01em;color:#09111a;background:linear-gradient(135deg,var(--a),#ff925d);box-shadow:0 14px 34px rgba(255,106,61,.22)}
    .btn.secondary{color:var(--text);background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);box-shadow:none}.btn.ghost{color:var(--text);background:transparent;border:1px dashed rgba(255,255,255,.2);box-shadow:none}
    .btn:disabled{opacity:.45;cursor:not-allowed}.btn:hover{transform:translateY(-1px)}
    .section{padding-bottom:16px;margin-bottom:16px;border-bottom:1px solid rgba(255,255,255,.08)} .section:last-child{padding-bottom:0;margin-bottom:0;border-bottom:0}
    .hint,.tiny,.status{color:var(--muted)} .hint,.tiny{font-size:12px;line-height:1.45}
    .scene-list{display:grid;gap:12px}.scene{padding:14px;border-radius:18px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);display:grid;gap:10px}
    .scene-head,.scene-foot{display:flex;align-items:center;justify-content:space-between;gap:10px}.scene-head strong{font-size:14px}
    .scene-foot{font-size:12px;color:var(--muted)} .scene-foot input{width:110px}
    .preview{position:sticky;top:16px}
    .stage{border-radius:20px;overflow:hidden;border:1px solid rgba(255,255,255,.08);background:#05070b;min-height:300px;position:relative}
    canvas{display:block;width:100%;height:auto;aspect-ratio:16/9;background:#05070b}
    .badge{position:absolute;right:14px;bottom:14px;padding:7px 10px;border-radius:999px;background:rgba(0,0,0,.42);border:1px solid rgba(255,255,255,.1);font-size:12px;letter-spacing:.08em;text-transform:uppercase}
    .statusbar{display:grid;gap:10px;margin-top:12px}.status{padding:10px 12px;border-radius:12px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);font-size:13px}
    .check{display:flex;align-items:center;gap:10px;color:var(--muted)} .check input{width:18px;height:18px;accent-color:var(--a)}
    @media (max-width:1180px){.hero,.layout{grid-template-columns:1fr}.preview{position:static}}
    @media (max-width:720px){.wrap{width:min(100% - 16px,100%)}.stats,.grid2,.grid3{grid-template-columns:1fr}.toolbar{flex-direction:column}.btn{width:100%}}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="hero">
      <div class="card hero-left">
        <div class="eyebrow">Video builder / browser export</div>
        <h1>Creador de videos para shorts, anuncios y contenido viral</h1>
        <p class="copy">Escribe un guion, separa escenas, previsualiza la animacion y descarga el video desde el navegador. Este MVP usa canvas y MediaRecorder, asi que funciona muy bien para piezas cortas.</p>
        <div class="chips"><span class="chip">Escenas editables</span><span class="chip">Formato 16:9 / 9:16 / 1:1</span><span class="chip">Micro opcional</span><span class="chip">Exportacion WebM</span></div>
      </div>
      <div class="card hero-right">
        <div class="stats">
          <div class="stat"><strong>1</strong><span>Escribe el guion o pega el texto para convertirlo en video.</span></div>
          <div class="stat"><strong>2</strong><span>Divide el contenido en escenas y ajusta duracion y ritmo.</span></div>
          <div class="stat"><strong>3</strong><span>Previsualiza y graba el video con micro si quieres voz.</span></div>
          <div class="stat"><strong>4</strong><span>Descarga el archivo y reutilizalo en YouTube o Shorts.</span></div>
        </div>
      </div>
    </section>
    <section class="layout">
      <article class="card panel">
        <div class="section">
          <h2>Proyecto</h2>
          <div class="grid2">
            <div class="field"><label for="title">Titulo</label><input id="title" type="text" placeholder="Los influencers no te inspiran, te venden humo"></div>
            <div class="field"><label for="subtitle">Subtitulo</label><input id="subtitle" type="text" placeholder="Critica a influencers"></div>
          </div>
          <div class="grid3" style="margin-top:12px">
            <div class="field"><label for="theme">Tema visual</label><select id="theme"><option value="ember">Ember</option><option value="signal">Signal</option><option value="midnight">Midnight</option><option value="sunrise">Sunrise</option></select></div>
            <div class="field"><label for="aspect">Formato</label><select id="aspect"><option value="16:9">16:9 YouTube</option><option value="9:16">9:16 Shorts</option><option value="1:1">1:1 Cuadrado</option></select></div>
            <div class="field"><label for="duration">Duracion por escena</label><input id="duration" type="number" min="3" max="15" step="1" value="6"></div>
          </div>
        </div>
        <div class="section">
          <div class="grid2">
            <div class="field"><label for="script">Guion fuente</label><textarea id="script" placeholder="Pega aqui tu guion. Deja una linea en blanco entre escenas."></textarea><div class="hint">Cada bloque se convertira en una escena editable.</div></div>
            <div>
              <label>Grabacion</label>
              <div class="check" style="margin-top:8px"><input id="mic" type="checkbox" checked><span>Grabar con micro del navegador</span></div>
              <div class="hint" style="margin-top:8px">Si el micro esta apagado, el video se exporta sin voz.</div>
              <div class="toolbar"><button class="btn secondary" id="demo" type="button">Cargar demo</button><button class="btn secondary" id="build" type="button">Construir escenas</button><button class="btn ghost" id="save" type="button">Guardar borrador</button></div>
            </div>
          </div>
          <div class="toolbar">
            <button class="btn" id="record" type="button">Grabar video</button>
            <button class="btn secondary" id="stop" type="button" disabled>Detener y descargar</button>
            <button class="btn secondary" id="json" type="button">Exportar JSON</button>
            <button class="btn ghost" id="reset" type="button">Reset limpio</button>
          </div>
        </div>
        <div class="section">
          <h2>Escenas</h2>
          <p class="hint" style="margin-top:-2px">Edita cada escena con su titulo, texto y duracion.</p>
          <div id="scenes" class="scene-list"></div>
        </div>
      </article>
      <aside class="card preview">
        <h2>Preview en vivo</h2>
        <p class="hint">La vista previa corre sola. Cuando grabes, el navegador capturara este canvas junto al micro.</p>
        <div class="stage"><canvas id="canvas" width="1280" height="720"></canvas><div class="badge" id="badge">16:9</div></div>
        <div class="statusbar"><div class="status" id="status">Listo para construir escenas y grabar.</div><div class="tiny">Salida: WebM via MediaRecorder</div></div>
      </aside>
    </section>
  </main>
  <script>
    const LS="video-builder-draft-v1";
    const DEMO={title:"Los influencers no te inspiran, te venden humo",subtitle:"Critica a influencers",theme:"ember",aspect:"16:9",duration:6,script:"Te venden una vida perfecta, pero muchas veces lo unico perfecto es la edicion, el guion y el patrocinio.\n\nMuchos influencers no construyen valor: construyen apariencia. Todo esta diseñado para verse bien y vender algo.\n\nTe muestran autenticidad, pero casi todo esta calculado. La ropa, la musica, la frase y la emocion tambien son parte del guion.\n\nEl problema no es solo el humo. El problema es que mucha gente confunde seguidores con autoridad y estetica con verdad.\n\n¿Cuantos influencers aportan valor real y cuantos solo venden humo con buena iluminacion?",scenes:[{title:"Gancho",body:"Te venden una vida perfecta, pero muchas veces lo unico perfecto es la edicion, el guion y el patrocinio.",duration:6},{title:"La trampa",body:"Muchos influencers no construyen valor: construyen apariencia. Todo esta diseñado para verse bien y vender algo.",duration:6},{title:"Autenticidad",body:"Te muestran autenticidad, pero casi todo esta calculado. La ropa, la musica, la frase y la emocion tambien son parte del guion.",duration:6},{title:"Comparacion",body:"El problema no es solo el humo. El problema es que mucha gente confunde seguidores con autoridad y estetica con verdad.",duration:6},{title:"CTA",body:"¿Cuantos influencers aportan valor real y cuantos solo venden humo con buena iluminacion?",duration:6}]};
    const THEMES={ember:{a:"#0a0c12",b:"#16101c",x:"#ff6a3d",y:"#ffd166",z:"#18d0c4"},signal:{a:"#05070b",b:"#0c1523",x:"#18d0c4",y:"#8bd3ff",z:"#f8e16c"},midnight:{a:"#06070c",b:"#11131c",x:"#ff5c7a",y:"#ffb74d",z:"#68e0cf"},sunrise:{a:"#101114",b:"#1d1520",x:"#ff8a4c",y:"#ffcf6e",z:"#82d1ff"}};
    const $=id=>document.getElementById(id),els={title:$("title"),subtitle:$("subtitle"),theme:$("theme"),aspect:$("aspect"),duration:$("duration"),script:$("script"),mic:$("mic"),scenes:$("scenes"),canvas:$("canvas"),badge:$("badge"),status:$("status"),record:$("record"),stop:$("stop"),build:$("build"),demo:$("demo"),save:$("save"),json:$("json"),reset:$("reset")};
    const ctx=els.canvas.getContext("2d"); let state={scenes:[]},start=performance.now(),rec=null,audio=null,chunks=[];
    const clamp=(n,min,max)=>Math.max(min,Math.min(max,n)),fmt=s=>`${String(Math.floor(s/60)).padStart(2,"0")}:${String(Math.floor(s%60)).padStart(2,"0")}`;
    const esc=t=>String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
    const setStatus=t=>els.status.textContent=t;
    const dims=a=>a==="9:16"?{w:720,h:1280}:a==="1:1"?{w:1080,h:1080}:{w:1280,h:720};
    const save=()=>localStorage.setItem(LS,JSON.stringify({title:els.title.value,subtitle:els.subtitle.value,theme:els.theme.value,aspect:els.aspect.value,duration:+els.duration.value||6,script:els.script.value,scenes:state.scenes}));
    const load=()=>{try{return JSON.parse(localStorage.getItem(LS)||"null")}catch(e){return null}};
    function apply(p){p=p||DEMO;els.title.value=p.title||"";els.subtitle.value=p.subtitle||"";els.theme.value=p.theme||"ember";els.aspect.value=p.aspect||"16:9";els.duration.value=p.duration||6;els.script.value=p.script||"";state.scenes=(p.scenes&&p.scenes.length?p.scenes:buildScenes(els.script.value));render();size();setStatus("Proyecto listo.");}
    function buildScenes(text){const blocks=String(text||"").split(/\n\s*\n/g).map(s=>s.trim()).filter(Boolean);return (blocks.length?blocks:[""]).map((b,i)=>{const lines=b.split(/\n+/).map(s=>s.trim()).filter(Boolean);let title=`Escena ${i+1}`,body=b.replace(/\n+/g," ");if(lines.length>1){title=lines[0];body=lines.slice(1).join(" ");}else if(b.includes(":")){const p=b.split(":");title=p.shift().trim()||title;body=p.join(":").trim()||body}return {title,body,duration:clamp(+els.duration.value||6,3,15)}})}
    function render(){const arr=state.scenes.length?state.scenes:buildScenes(els.script.value);els.scenes.innerHTML=arr.map((s,i)=>`<article class="scene" data-i="${i}"><div class="scene-head"><strong>Escena ${i+1}</strong><button class="btn secondary" type="button" data-x="del">Eliminar</button></div><div class="field"><label>Titulo</label><input data-f="title" value="${esc(s.title)}"></div><div class="field"><label>Cuerpo</label><textarea data-f="body">${esc(s.body)}</textarea></div><div class="scene-foot"><span>Texto editable</span><input type="number" min="3" max="15" data-f="duration" value="${s.duration}"></div></article>`).join(""); state.scenes=arr}
    function size(){const d=dims(els.aspect.value);els.canvas.width=d.w;els.canvas.height=d.h;els.canvas.style.aspectRatio=`${d.w}/${d.h}`;els.badge.textContent=els.aspect.value}
    function wrap(text,max){const w=text.split(/\s+/),lines=[];let line="";for(const word of w){const t=line?line+" "+word:word;if(ctx.measureText(t).width>max&&line){lines.push(line);line=word}else line=t}if(line)lines.push(line);return lines}
    function drawBg(p,idx,prog){const t=THEMES[p.theme]||THEMES.ember,w=els.canvas.width,h=els.canvas.height;const g=ctx.createLinearGradient(0,0,w,h);g.addColorStop(0,t.a);g.addColorStop(1,t.b);ctx.fillStyle=g;ctx.fillRect(0,0,w,h);const glow=ctx.createRadialGradient(w*(.2+.06*Math.sin(prog*6.28+idx)),h*.24,0,w*.2,h*.24,w*.7);glow.addColorStop(0,`rgba(255,255,255,.0)`);glow.addColorStop(1,t.x+"30");ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);for(let i=0;i<4;i++){ctx.save();ctx.globalAlpha=.08;ctx.strokeStyle=t.y;ctx.lineWidth=2;ctx.beginPath();const x=w*(.15+i*.18+.02*Math.sin(prog*6.28+i));ctx.moveTo(x,h*.06);ctx.lineTo(x+w*.2,h*.92);ctx.stroke();ctx.restore()}}
    function draw(now){const p={title:els.title.value||DEMO.title,subtitle:els.subtitle.value||DEMO.subtitle,theme:els.theme.value,aspect:els.aspect.value,duration:+els.duration.value||6,scenes:state.scenes.length?state.scenes:buildScenes(els.script.value)};const scenes=p.scenes;const total=scenes.reduce((a,s)=>a+s.duration*1000,0)||1000;let t=(now-start)%total,acc=0,idx=0,sc=scenes[0],local=0;for(let i=0;i<scenes.length;i++){const ms=scenes[i].duration*1000;if(t<acc+ms){idx=i;sc=scenes[i];local=t-acc;break}acc+=ms}const prog=local/(sc.duration*1000),theme=THEMES[p.theme]||THEMES.ember;ctx.clearRect(0,0,els.canvas.width,els.canvas.height);drawBg(p,idx,prog);const w=els.canvas.width,h=els.canvas.height,pad=w*.08,cardY=h*.22,cardW=w*.82,cardH=h*.52;ctx.fillStyle="rgba(6,8,12,.84)";roundRect(pad,cardY,cardW,cardH,Math.min(w,h)*.035);ctx.fill();ctx.strokeStyle=theme.x+"55";ctx.lineWidth=Math.max(1,Math.min(w,h)*.002);ctx.stroke();ctx.fillStyle=theme.z;ctx.font=`700 ${Math.max(12,Math.min(w,h)*.016)}px Inter`;ctx.fillText((p.subtitle||"Video builder")+" / ESCENA "+(idx+1),pad+w*.05,cardY+h*.1);ctx.fillStyle="#fff";ctx.font=`900 ${Math.max(30,Math.min(w,h)*.058)}px Space Grotesk`;const titleLines=wrap(sc.title,cardW*.82),bodyLines=wrap(sc.body,cardW*.76);let y=cardY+h*.19;titleLines.slice(0,2).forEach(l=>{ctx.fillText(l,pad+w*.05,y);y+=Math.max(30,Math.min(w,h)*.058)*1.03});ctx.fillStyle="rgba(238,243,255,.9)";ctx.font=`500 ${Math.max(18,Math.min(w,h)*.024)}px Inter`;y+=18;bodyLines.slice(0,5).forEach(l=>{ctx.fillText(l,pad+w*.05,y);y+=Math.max(18,Math.min(w,h)*.024)*1.5});const barY=h*.82,barH=h*.03;ctx.fillStyle="rgba(255,255,255,.08)";roundRect(pad,barY,cardW,barH,barH/2);ctx.fill();ctx.fillStyle=theme.x;roundRect(pad,barY,Math.max(barH,cardW*clamp(prog,0,1)),barH,barH/2);ctx.fill();ctx.fillStyle="#fff";ctx.font=`700 ${Math.max(12,Math.min(w,h)*.015)}px Inter`;ctx.fillText(p.title,pad,h-h*.08);ctx.fillText(`${idx+1} / ${scenes.length}`,w-pad-ctx.measureText(`${idx+1} / ${scenes.length}`).width,h-h*.08);ctx.fillStyle=theme.z;ctx.fillText(`${fmt((local/1000)||0)} / ${fmt(sc.duration)}`,w-pad-ctx.measureText(`${fmt((local/1000)||0)} / ${fmt(sc.duration)}`).width,h-h*.04);requestAnimationFrame(draw)}
    function roundRect(x,y,w,h,r){r=Math.min(r,w/2,h/2);ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
    function download(blob,name){const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},1200)}
    async function record(){if(!window.MediaRecorder){setStatus("MediaRecorder no esta disponible en este navegador.");return}try{const tracks=[...els.canvas.captureStream(30).getVideoTracks()];if(els.mic.checked){audio=await navigator.mediaDevices.getUserMedia({audio:true});tracks.push(...audio.getAudioTracks())}const stream=new MediaStream(tracks),types=["video/webm;codecs=vp9,opus","video/webm;codecs=vp8,opus","video/webm"],mime=types.find(t=>MediaRecorder.isTypeSupported(t))||"";rec=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);chunks=[];rec.ondataavailable=e=>e.data.size&&chunks.push(e.data);rec.onstop=()=>{download(new Blob(chunks,{type:rec.mimeType||"video/webm"}),`${(els.title.value||"video").toLowerCase().replace(/[^a-z0-9]+/g,"-")||"video"}.webm`);stop();setStatus("Video descargado.")};rec.start(1000);els.record.disabled=true;els.stop.disabled=false;setStatus("Grabando video...") }catch(e){setStatus("No se pudo grabar: "+e.message);stop()}}
    function stop(){if(rec&&rec.state!=="inactive"){try{rec.stop()}catch(e){}}if(audio){audio.getTracks().forEach(t=>t.stop());audio=null}rec=null;els.record.disabled=false;els.stop.disabled=true}
    function exportJson(){download(new Blob([JSON.stringify({title:els.title.value,subtitle:els.subtitle.value,theme:els.theme.value,aspect:els.aspect.value,duration:+els.duration.value||6,script:els.script.value,scenes:state.scenes},null,2)],{type:"application/json"}),`${(els.title.value||"project").toLowerCase().replace(/[^a-z0-9]+/g,"-")||"project"}.json`);setStatus("Proyecto exportado.")}
    function syncFromInputs(){state.scenes=state.scenes.length?state.scenes:buildScenes(els.script.value);save();render();size()}
    els.scenes.addEventListener("input",e=>{const card=e.target.closest(".scene"),i=card?+card.dataset.i:-1,f=e.target.dataset.f;if(i<0||!f)return;state.scenes[i][f]=f==="duration"?clamp(+e.target.value||6,3,15):e.target.value;save()});
    els.scenes.addEventListener("click",e=>{const btn=e.target.closest("[data-x='del']");if(!btn)return;const i=+btn.closest(".scene").dataset.i;state.scenes.splice(i,1);if(!state.scenes.length)state.scenes=buildScenes(els.script.value);render();save();setStatus("Escena eliminada.")});
    ["input","change"].forEach(ev=>["title","subtitle","theme","aspect","duration","script","mic"].forEach(id=>$(id).addEventListener(ev,()=>{if(id==="aspect")size();syncFromInputs();setStatus("Cambios guardados.")})));
    els.build.onclick=()=>{state.scenes=buildScenes(els.script.value);render();save();setStatus("Escenas construidas desde el guion.")};
    els.demo.onclick=()=>{apply(DEMO);save();setStatus("Demo cargada.")};
    els.save.onclick=()=>{save();setStatus("Borrador guardado.")};
    els.json.onclick=exportJson;
    els.reset.onclick=()=>{localStorage.removeItem(LS);state.scenes=[];apply({title:"",subtitle:"",theme:"ember",aspect:"16:9",duration:6,script:"",scenes:[]});setStatus("Proyecto limpio.")};
    els.record.onclick=record; els.stop.onclick=stop;
    window.addEventListener("beforeunload",save);
    const saved=load(); apply(saved||DEMO); render(); size(); requestAnimationFrame(draw);
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(INDEX_HTML)


if __name__ == "__main__":
    raise SystemExit("Run with gunicorn -w 4 -b 0.0.0.0:5000 video_creator_app:app")
