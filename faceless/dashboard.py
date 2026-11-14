"""The command center page: one self-contained, mobile-first HTML file that shows `overview.build()` and whose buttons each post one
allowlisted action name to the server (`faceless/actions.py`). The page itself changes nothing: a button runs a real command there.

`python -m faceless dashboard` writes `site/command-center/` (gitignored, never deployed: the public site is built by CI from a clean
checkout): index.html with the overview embedded, overview.json, a web manifest, two icons and a small service worker. No framework, no
external request, no cookie. The page asks the server for a fresh overview.json, keeps the last good one in the browser, and shows that
copy with a banner when the server cannot be reached.

Every value reaches the page as JSON and is placed with `textContent`; no state string is ever written into markup.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

from faceless.config import Paths
from faceless.fsutil import write_atomic

OUT = Paths.root / "site" / "command-center"
BG, GOLD = "#0e0f11", "#e3b341"

MANIFEST = {"name": "Quiet Money Command Center", "short_name": "QM Center", "start_url": "./", "scope": "./", "display": "standalone",
            "background_color": BG, "theme_color": BG,
            "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}

# Network first for the page itself; when the server is gone, or answers 401 to a launch from the home screen (no token in that URL),
# the last good copy of the page is shown and it reads its own cached overview. Data requests are never cached here.
SERVICE_WORKER = """const SHELL='qm-cc-shell-v1';
self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{
  if(e.request.mode!=='navigate')return;
  e.respondWith((async()=>{
    const cache=await caches.open(SHELL);
    try{
      const r=await fetch(e.request);
      if(r.ok){cache.put('shell',r.clone());return r;}
      return (await cache.match('shell'))||r;
    }catch(err){
      return (await cache.match('shell'))||new Response('Command center is offline and no copy is saved on this phone yet.',{status:503,headers:{'Content-Type':'text/plain'}});
    }
  })());
});
"""

CSS = """
:root{--bg:#0e0f11;--card:#17191d;--line:#262a30;--ink:#f1efe9;--dim:#9aa0a8;--gold:#e3b341;--ok:#5fbf8a;--warn:#e8a23c;--stop:#e5645a;--info:#7aa7d8}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html{overflow-y:scroll;overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;overflow-x:hidden;overflow-y:visible;-webkit-overflow-scrolling:touch;padding:env(safe-area-inset-top) 0 calc(72px + env(safe-area-inset-bottom));min-height:100vh}
header{padding:14px 16px 6px;display:flex;justify-content:space-between;align-items:baseline;gap:12px}
header h1{font-size:15px;margin:0;letter-spacing:.08em;text-transform:uppercase;color:var(--gold);font-weight:700}
#asof{font-size:12px;color:var(--dim);text-align:right}
#banner{display:none;margin:6px 16px;padding:10px 12px;border-radius:10px;background:#3a2a10;color:#f6d79a;font-size:14px}
#banner.on{display:block}
#pull{height:0;overflow:hidden;text-align:center;color:var(--dim);font-size:13px;transition:height .15s}
main{padding:4px 16px 16px;max-width:560px;margin:0 auto}
h2{font-size:13px;letter-spacing:.07em;text-transform:uppercase;color:var(--dim);margin:20px 0 8px;font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin:0 0 12px;overflow-wrap:anywhere}
.big{font-size:40px;line-height:1.05;font-weight:700;font-variant-numeric:tabular-nums}
.big.ver{font-size:28px;overflow-wrap:anywhere}
.note{color:var(--dim);font-size:14px;margin-top:4px}
.src{color:#6f757d;font-size:11px;margin-top:10px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-top:1px solid var(--line);font-size:15px}
.row:first-of-type{border-top:0}
.row b{font-variant-numeric:tabular-nums;font-weight:600;text-align:right}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.cell{background:#111316;border:1px solid var(--line);border-radius:10px;padding:10px 8px;text-align:center}
.cell b{display:block;font-size:22px;font-variant-numeric:tabular-nums}
.cell span{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em}
.tag{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:2px 7px;border-radius:999px;border:1px solid currentColor;margin-right:6px}
.ok{color:var(--ok)}.warn{color:var(--warn)}.stop{color:var(--stop)}.info{color:var(--info)}.dim{color:var(--dim)}.gold{color:var(--gold)}
.item{padding:10px 0;border-top:1px solid var(--line)}
.item:first-child{border-top:0;padding-top:0}
.item .t{font-size:15px;font-weight:600}
.item .s{font-size:13px;color:var(--dim);margin-top:2px}
.msg{background:#111316;border:1px solid var(--line);border-radius:10px;padding:10px;font-size:15px;margin:8px 0;white-space:pre-wrap}
button{font:inherit;color:var(--bg);background:var(--gold);border:0;border-radius:10px;padding:11px 14px;font-weight:700;min-height:44px}
button.ghost{background:transparent;color:var(--gold);border:1px solid var(--line)}
.btnlink{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:11px 14px;border-radius:10px;background:var(--gold);color:var(--bg);font-weight:700;text-decoration:none}
input[type=search],select{font:inherit;color:var(--ink);background:#111316;border:1px solid var(--line);border-radius:10px;padding:10px 12px;min-height:44px;max-width:100%}
input[type=search]{flex:1 1 220px}
select{max-width:280px}
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;background:#111316;border:1px solid var(--line);border-radius:6px;padding:2px 5px;display:inline-block;max-width:100%}
a{color:var(--gold)}
details summary{color:var(--gold);font-size:14px;padding:8px 0;min-height:36px}
nav{position:fixed;left:0;right:0;bottom:0;display:flex;background:#111316;border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom);z-index:5;overflow-x:auto;overflow-y:hidden;scrollbar-width:none}
nav::-webkit-scrollbar{display:none}
nav button{flex:1 0 auto;background:transparent;color:var(--dim);border-radius:0;padding:10px 2px 12px;font-size:11px;font-weight:600;min-height:56px;min-width:52px;position:relative}
@media (min-width:900px){
  body{padding:0 0 0 224px}
  nav{top:0;right:auto;bottom:0;width:224px;flex-direction:column;padding:14px 10px;border-top:0;border-right:1px solid var(--line);gap:2px;overflow:visible}
  nav button{flex:0 0 auto;width:100%;display:flex;align-items:center;justify-content:flex-start;text-align:left;padding:12px 14px;font-size:14px;border-radius:10px;min-height:44px;min-width:0}
  nav button.on{background:#1b1d22}
  nav button i{display:inline-block;width:24px;font-size:16px;margin-right:8px;line-height:1}
  nav .dot{position:static;margin-left:auto}
  header{padding:20px 28px 8px}
  #banner{margin:6px 28px}
  #strip{margin:4px 28px 8px}
  main{max-width:1180px;padding:8px 28px 40px}
  .grid{grid-template-columns:repeat(4,1fr)}
}
nav button.on{color:var(--gold)}
nav button i{display:block;font-style:normal;font-size:18px;line-height:1.2}
nav .dot{position:absolute;top:6px;right:calc(50% - 22px);min-width:17px;height:17px;border-radius:9px;background:var(--stop);color:#fff;font-size:11px;line-height:17px;padding:0 4px}
.s.dim{font-size:13px}
#strip{display:none;margin:4px 16px 8px;padding:9px 12px;border-radius:10px;background:#14161a;border:1px solid var(--line);font-size:13px;color:var(--dim);cursor:pointer;overflow-wrap:anywhere}
#strip.on{display:block}
#strip b{color:var(--ink);font-weight:600}
button{cursor:pointer}
button[disabled]{opacity:.55;cursor:default}
button.sm{min-height:38px;padding:8px 12px;font-size:13px}
button.arm{background:var(--warn);color:var(--bg)}
.spin{display:inline-block;width:10px;height:10px;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;margin-right:7px;vertical-align:-1px;animation:sp 1s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.detail{background:#111316;border:1px solid var(--line);border-radius:10px;padding:10px;margin-top:8px;font-size:13px}
.detail .l{padding:3px 0;color:var(--dim)}
.detail .l b{color:var(--ink);font-weight:600}
.sw{display:flex;align-items:center;justify-content:space-between;gap:12px}
.sw button{flex:0 0 auto}
pre.out{margin:6px 0 0;font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--dim);background:#0b0c0e;border-radius:8px;padding:8px;max-height:180px;overflow:auto}
input[type=text]{font:inherit;color:var(--ink);background:#111316;border:1px solid var(--line);border-radius:10px;padding:8px 12px;min-height:38px;flex:1 1 160px;max-width:100%}
#toast{position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom));transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:8px 14px;border-radius:999px;font-size:14px;font-weight:600;opacity:0;transition:opacity .2s;pointer-events:none;z-index:9}
#toast.on{opacity:1}
"""

JS = r"""
(function(){
var LS={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
var q=new URLSearchParams(location.search),tok=q.get('t');
try{sessionStorage.removeItem('qm_r')}catch(e){}
if(tok){LS.set('qm_t',tok);try{history.replaceState(null,'',location.pathname+location.hash)}catch(e){}}else{tok=LS.get('qm_t')||''}
var seed=null,cached=null;
try{seed=JSON.parse(document.getElementById('seed').textContent)}catch(e){}
try{cached=JSON.parse(LS.get('qm_overview')||'null')}catch(e){}
var D=(cached&&seed&&cached.generatedAt>seed.generatedAt)?cached:(seed||cached),live=null;
var TABS=[['today','Today','◎'],['money','Money','$'],['dms','DMs','✉'],['jobs','Jobs','▤'],['agents','Agents','✦'],['models','Models','◈'],['alerts','Alerts','!']];
var tab=(location.hash||'').slice(1)||LS.get('qm_tab')||'today';
if(!TABS.some(function(t){return t[0]===tab}))tab='today';
var ACT={running:[],recent:(D&&D.activity)||[]},OPENJ={},NS={on:LS.get('qm_ns')==='1',st:null},dirty=false,polling=null;

function h(tag,attrs){var e=document.createElement(tag),i,c;attrs=attrs||{};
  for(var k in attrs){if(k==='class')e.className=attrs[k];else if(k==='on')e.addEventListener('click',attrs[k]);else if(k.slice(0,2)==='on'&&typeof attrs[k]==='function')e.addEventListener(k.slice(2),attrs[k]);else e.setAttribute(k,attrs[k])}
  for(i=2;i<arguments.length;i++){c=arguments[i];if(c==null||c===false)continue;
    if(Array.isArray(c)){c.forEach(function(x){if(x!=null&&x!==false)e.appendChild(typeof x==='object'?x:document.createTextNode(String(x)))})}
    else e.appendChild(typeof c==='object'?c:document.createTextNode(String(c)))}
  return e}
function card(){var a=[].slice.call(arguments);return h.apply(null,['div',{class:'card'}].concat(a))}
function src(s){return h('div',{class:'src'},'source: '+s)}
function row(label,value){return h('div',{class:'row'},h('span',{},label),h('b',{},value==null?'—':String(value)))}
function cell(n,label){return h('div',{class:'cell'},h('b',{},n==null?'—':String(n)),h('span',{},label))}
function missing(what,where){return card(h('div',{class:'t warn'},what+': source missing'),h('div',{class:'note'},'Nothing is shown rather than a zero that would look real.'),src(where))}
function money(n){return n==null?'—':'$'+Number(n).toFixed(2)}
function when(iso){if(!iso)return'unknown';var d=new Date(iso);return isNaN(d)?iso:d.toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
function ago(iso){var s=Math.max(0,(Date.now()-new Date(iso).getTime())/1000);return isNaN(s)?'':s<90?Math.round(s)+' s ago':s<5400?Math.round(s/60)+' min ago':when(iso)}
function toast(t){var e=document.getElementById('toast');e.textContent=t;e.className='on';setTimeout(function(){e.className=''},1800)}
function typing(){var a=document.activeElement;return !!(a&&/^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName))}
function copy(text){
  function fallback(){var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.top='-999px';document.body.appendChild(ta);ta.select();ta.setSelectionRange(0,text.length);var ok=false;try{ok=document.execCommand('copy')}catch(e){}document.body.removeChild(ta);toast(ok?'Copied':'Press and hold the text to copy')}
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(function(){toast('Copied')},fallback)}else fallback()}
function copyBtn(label,text,ghost){return h('button',{class:(ghost?'ghost ':'')+'sm',type:'button',on:function(){copy(text)}},label)}
function go(t){tab=t;LS.set('qm_tab',tab);try{history.replaceState(null,'','#'+tab)}catch(e){}window.scrollTo(0,0);draw()}
function tabName(t){var x=TABS.filter(function(y){return y[0]===t})[0];return x?x[1]:t}

// ---- actions: every button posts one allowlisted name to the server, which runs the real command and journals the result
function api(path){return fetch(path,{headers:tok?{Authorization:'Bearer '+tok}:{},cache:'no-store',credentials:'omit'}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})}
function post(body){return fetch('action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+tok},body:JSON.stringify(body),cache:'no-store',credentials:'omit'})
  .then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.error||r.status);return j},function(){throw new Error(r.status)})})}
function akey(a){a=a||{};return a.job||a.draft||a.target||a.slug||''}
function isRunning(name,key){return ACT.running.some(function(r){return r.action===name&&akey(r.args)===key})}
function redraw(){if(typing())dirty=true;else draw()}
function settle(res,label){
  if(res.state==='running'){ACT.running=ACT.running.filter(function(r){return r.id!==res.id}).concat([res]);toast(label+': started');poll()}
  else{toast((res.ok?'Done: ':(res.refused?'Refused: ':'Failed: '))+label);ACT.recent=[res].concat(ACT.recent.filter(function(r){return !res.id||r.id!==res.id})).slice(0,15)}
  strip()}
function act(name,args,label){
  toast(label+'…');
  return post({name:name,args:args||{}}).then(function(res){settle(res,label);if(res.state==='running')redraw();else refresh()},
    function(e){settle({action:name,label:label,state:'done',ok:false,exit:null,summary:'The server did not take it: '+(e&&e.message||'error'),at:new Date().toISOString()},label);redraw()})}
function poll(){if(polling)return;polling=setInterval(function(){api('actions.json').then(function(a){
  var was=ACT.running.length;ACT.running=a.running||[];ACT.recent=a.recent||ACT.recent;strip();
  if(!ACT.running.length){clearInterval(polling);polling=null;var l=ACT.recent[0];if(was&&l)toast((l.ok?'Done: ':'Failed: ')+l.label);refresh()}
  else if(tab==='alerts')redraw()},function(){})},2000)}
function strip(){var e=document.getElementById('strip'),r=ACT.running[0],l=ACT.recent[0];e.textContent='';
  if(r){e.appendChild(h('span',{class:'spin'}));e.appendChild(h('b',{},r.label));e.appendChild(document.createTextNode(' running since '+when(r.at)+(ACT.running.length>1?' (+'+(ACT.running.length-1)+' more)':'')))}
  else if(l){e.appendChild(h('span',{class:l.ok?'ok':'stop'},l.ok?'✓ ':'✗ '));e.appendChild(h('b',{},'Last action: '+l.label));
    e.appendChild(document.createTextNode(' · '+(l.summary||'')+((l.exit!=null&&!l.ok)?' (exit '+l.exit+')':'')+' · '+ago(l.at)))}
  else{e.className='';return}
  e.className='on'}
function actBtn(label,name,args,opt){opt=opt||{};var key=opt.key!=null?opt.key:akey(typeof args==='function'?null:args),busy=isRunning(name,key);
  var b=h('button',{class:(opt.ghost?'ghost ':'')+(opt.sm?'sm':''),type:'button'},busy?[h('span',{class:'spin'}),'Running…']:label);
  if(busy){b.disabled=true;return b}
  b.addEventListener('click',function(){
    if(opt.confirm&&!b.armed){b.armed=true;b.textContent='Tap again: '+opt.confirm;b.className+=' arm';
      setTimeout(function(){b.armed=false;b.textContent=label;b.className=b.className.replace(' arm','')},5000);return}
    var a=typeof args==='function'?args():args;if(a===false)return;
    b.disabled=true;b.textContent=label+'…';act(name,a,label)});
  return b}

// ---- one job's own steps, read from its file on request
function fillDetail(box,d){box.textContent='';
  if(d==null){box.appendChild(h('div',{class:'l'},'Loading…'));return}
  if(d.error){box.appendChild(h('div',{class:'l warn'},d.error));return}
  box.appendChild(h('div',{class:'l'},h('b',{},'Status: '+d.status),d.gate?' · gate: '+d.gate:''));
  (d.history||[]).forEach(function(x){box.appendChild(h('div',{class:'l'},(x.from?x.from+' → ':'')+(x.to||'')+' · '+when(x.ts)+(x.score!=null?' · score '+x.score:''),x.error?h('div',{class:'stop'},x.error):null))});
  if(d.report){box.appendChild(h('div',{class:'l'},h('b',{},'Gauntlet: '+d.report.score+(d.report.passed?' (passed)':' (not passed)'))));
    (d.report.failed||[]).forEach(function(g){box.appendChild(h('div',{class:'l'},h('span',{class:'tag '+(g.hard?'stop':'warn')},g.hard?'hard gate':'soft gate'),g.name+': '+g.detail))})}
  (d.notes||[]).forEach(function(n){box.appendChild(h('div',{class:'l'},'Note: '+n))});
  box.appendChild(src(d.source||'the job file'))}
function detail(id){if(!(id in OPENJ))return null;var box=h('div',{class:'detail',id:'d-'+id});fillDetail(box,OPENJ[id]);return box}
function viewBtn(id,label){return h('button',{class:'ghost sm',type:'button',on:function(){
  if(id in OPENJ){delete OPENJ[id];draw();return}
  OPENJ[id]=null;draw();
  api('job.json?id='+encodeURIComponent(id)).then(function(d){if(id in OPENJ)OPENJ[id]=d},function(e){if(id in OPENJ)OPENJ[id]={error:'Could not load this job ('+(e&&e.message||'error')+').'}})
    .then(function(){var b=document.getElementById('d-'+id);if(b&&(id in OPENJ))fillDetail(b,OPENJ[id])})}},(id in OPENJ)?'Hide steps':label)}

// ---- Non-stop: while this page is open and the toggle is on, ask the server every 30 s whether to advance the phone lane
function nsText(){if(!NS.on)return 'Off. When on, this open page asks every 30 s whether the staged phone job was closed, and pushes the next one. state/PAUSE stops it; so does closing this window.';
  return NS.st?(NS.st.state+': '+NS.st.text):'On. First check in a moment…'}
function nsPaint(){var e=document.getElementById('ns-st');if(e)e.textContent=nsText()}
function nsTick(){if(!NS.on)return;
  if(typing()){NS.st={state:'holding',text:'You are typing in a field; nothing runs until you leave it.'};nsPaint();return}
  post({name:'nonstop_tick'}).then(function(r){NS.st={state:r.state||'unknown',text:r.text||''};nsPaint();
      if(r.result){settle(r.result,'Advance phone (non-stop)');if(r.result.state!=='running')refresh()}},
    function(e){NS.st={state:'offline',text:'The server did not answer ('+(e&&e.message||'error')+').'};nsPaint()})}
function nsBox(){
  var b=h('button',{class:NS.on?'':'ghost',type:'button','aria-pressed':NS.on?'true':'false',on:function(){NS.on=!NS.on;LS.set('qm_ns',NS.on?'1':'0');NS.st=null;draw();if(NS.on)nsTick()}},NS.on?'Non-stop: ON':'Non-stop: off');
  return h('div',{class:'detail'},h('div',{class:'sw'},h('div',{},h('b',{},'Non-stop'),h('div',{class:'l',id:'ns-st'},nsText())),b))}

function action(a,i){return h('div',{class:'item'},h('div',{class:'t'},(i+1)+'. '+a.title+' ',h('span',{class:'dim'},'· '+a.minutes+' min')),h('div',{class:'s'},a.how),h('div',{class:'s'},'Why: '+a.why),src(a.source))}
function alertItem(a){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+a.level},a.level),a.text),h('div',{class:'s'},'Fix: '+a.fix),
  h('div',{class:'btns'},a.action?actBtn(a.action.label,a.action.name,a.action.args||{},{sm:true,confirm:a.action.name==='daily'?'starts the batch':null}):null,
    a.tab?h('button',{class:'ghost sm',type:'button',on:function(){go(a.tab)}},'Open '+tabName(a.tab)):null,copyBtn('Copy fix',a.fix,true)),src(a.source))}
function phoneCard(){var p=D.phone;if(!p)return missing('Phone lane','state/phone/jobs');
  var dev=p.device||{},n=p.next;
  return card(h('div',{class:'t'},h('span',{class:'tag '+(n?'ok':'dim')},n?'next':'idle'),n?n.id:'No phone job can run now'),
    n?h('div',{class:'s'},(n.recipe||n.kind)+' · queued for '+n.day):null,
    row('Can run now',p.runnable),p.mediaMissing?row('...of which the media is gone',p.mediaMissing):null,row('Blocked by a gate',p.blockedCount),row('Held',p.heldCount),
    row('Phone on adb',dev.attached==null?'unknown':dev.attached?'attached':'not attached'),
    (!dev.attached&&dev.note)?h('div',{class:'s warn'},dev.note):null,
    p.nextMediaMissing?h('div',{class:'s warn'},'The next job cannot be pushed: its video is no longer on the media branch or this disk. Park holds every job like it, with the reason, so the lane can move.'):null,
    h('div',{class:'btns'},actBtn('Advance phone','phone_next',{},{ghost:!!p.nextMediaMissing}),p.mediaMissing?actBtn('Park jobs with no media','phone_park',{},{ghost:!p.nextMediaMissing}):null),
    h('div',{class:'s dim'},'Runs python -m faceless phone next --push: fetches the next job and puts its files on the phone. The phone driver posts it and records it with phone done.'),
    nsBox(),src(p.source))}
function targetsCard(){var t=D.targets||[];if(!t.length)return null;
  return card(t.map(function(x){return row(x.label,(x.actual==null?'—':x.actual)+' of '+x.target)}),
    h('div',{class:'s dim'},'Only the targets written in studio.toml. There is no revenue target, so none is drawn.'),src(t.map(function(x){return x.source}).join('; ')))}

var V={};
V.today=function(){var j=D.jobs,out=[];
  if(!j)out.push(missing('Daily run','state/jobs'));
  else{
    out.push(card(h('div',{class:'big '+(j.ranToday?'ok':'warn')},j.ranToday?'Ran today':'Not run today'),
      h('div',{class:'note'},j.ranToday?(j.passedToday+' passed, '+j.heldToday+' held, '+j.failedToday+' failed of '+j.madeToday+' made'):('Last run day: '+(j.lastRunDay||'none')+(j.lastRun?' ('+j.lastRun.passed+' passed, '+j.lastRun.held+' held, '+j.lastRun.failed+' failed, '+j.lastRun.unfinished+' unfinished)':''))),
      (!j.ranToday||j.passedToday<5)?h('div',{class:'btns'},actBtn('Run today\'s batch','daily',{},{confirm:'starts the batch'})):null,
      (!j.ranToday||j.passedToday<5)?h('div',{class:'s dim'},'Runs python -m faceless daily --no-publish: it writes, renders, gates and packs. Nothing is uploaded; passed videos reach TikTok through the phone lane.'):null,
      src(j.source)));
    out.push(card(h('div',{class:'grid'},cell(j.passedToday,'passed today'),cell(j.postedToday,'posted today'),cell(j.heldToday,'held today')),
      row('TikTok posts waiting in the phone queue',j.tiktokQueued),row('Last post recorded',j.lastPostAt?when(j.lastPostAt):'none'),src('state/jobs, state/phone/receipts.jsonl, state/phone/jobs')));
  }
  out.push(h('h2',{},'Phone lane'));out.push(phoneCard());
  var tc=targetsCard();if(tc){out.push(h('h2',{},'Targets'));out.push(tc)}
  var need=(D.alerts||[]).filter(function(a){return a.level!=='info'});
  out.push(h('h2',{},'Needs you now'));
  if(D.money&&D.money.actions&&D.money.actions.length)out.push(card(action(D.money.actions[0],0)));
  out.push(need.length?card(need.slice(0,5).map(alertItem)):card(h('div',{class:'t ok'},'Nothing is stopped or warning.'),src('derived from this page\'s own data')));
  return out};
V.money=function(){var c=D.cash,o=D.offers,ob=D.outbound,sp=D.spend,out=[];
  if(!c)out.push(missing('Revenue','state/receipts.jsonl'));
  else out.push(card(h('div',{class:'dim',style:'font-size:13px'},'Revenue this month'),h('div',{class:'big'},money(c.revenueMTD)),
    h('div',{class:'note'},c.note?c.note:(c.receipts+' receipts, '+money(c.netMTD)+' after fees')),
    row('Receipts this month',c.receipts),row('Receipts all time',c.receiptsAllTime),row('Net after fees this month',money(c.netMTD)),
    Object.keys(c.byRail||{}).map(function(k){return row(k,money(c.byRail[k].gross)+' ('+c.byRail[k].receipts+')')}),src(c.source)));
  out.push(h('h2',{},'Next money move'));
  var acts=(D.money&&D.money.actions)||[];
  out.push(card(acts.length?acts.map(action):h('div',{class:'t'},'No action is waiting on you.'),
    D.money&&D.money.brief?h('div',{class:'s dim',style:'margin-top:8px'},'Full brief: '+D.money.brief):null,
    h('div',{class:'btns'},actBtn(D.money&&D.money.brief?'Rewrite today\'s brief':'Write today\'s brief','money_brief',{},{sm:true,ghost:true})),src('faceless/moneybrief.py')));
  out.push(h('h2',{},'Offers'));
  if(!o)out.push(missing('Offers','channel/shop/catalog.json'));
  else out.push(card(h('div',{class:'grid',style:'grid-template-columns:1fr 1fr'},cell(o.live,'live listings'),cell(o.built,'products built')),
    o.items.map(function(i){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+(i.live?'ok':'dim')},i.live?'live':'not listed'),i.name),
      h('div',{class:'s'},i.live?('Listed at '+(i.price===0?'$0+ (free gift)':money(i.price))):('Catalog test price '+money(i.catalogPrice)+'; needs your price')),
      i.live&&i.url?h('div',{class:'s'},h('a',{href:i.url,rel:'noreferrer noopener',target:'_blank'},'Open listing')):null)}),src(o.source)));
  out.push(h('h2',{},'DM funnel'));
  out.push(ob?card(h('div',{class:'grid'},cell(ob.sent,'sent'),cell(ob.replied,'replied'),cell(ob.bought,'bought')),
    h('div',{class:'btns'},h('button',{class:'ghost sm',type:'button',on:function(){go('dms')}},'Open DMs')),src(ob.source)):missing('DM funnel','state/outbound.jsonl'));
  if(sp)out.push(card(row('Spent today',money(sp.todayUsd)),row('Daily ceiling',money(sp.ceilingUsd)),row('Paused',sp.paused||'no'),src(sp.source)));
  return out};
V.dms=function(){var ob=D.outbound,d=D.dms,out=[];
  out.push(ob?card(h('div',{class:'grid'},cell(ob.draftedToday,'drafted today'),cell(ob.sent,'sent'),cell(ob.replied,'replied')),
    row('Clicked',ob.clicked),row('Bought',ob.bought),row('Closed without reply',ob.dead),row('Waiting for you to send',ob.blockedOnOwner),row('Follow-ups due',ob.followUpsDue),src(ob.source)):missing('DM record','state/outbound.jsonl'));
  if(D.followUps&&D.followUps.length){out.push(h('h2',{},'Follow-ups due'));
    out.push(card(D.followUps.map(function(f){return h('div',{class:'item'},h('div',{class:'t'},f.draft_id),h('div',{class:'s'},'Sent '+f.days_since_sent+' days ago: send '+f.send.replace(/_/g,' ')),
      h('div',{class:'btns'},actBtn('They replied','dm_log',{draft:f.draft_id,status:'replied'},{sm:true}),actBtn('Close: no reply','dm_log',{draft:f.draft_id,status:'dead'},{sm:true,ghost:true})))}),src('state/outbound.jsonl')))}
  out.push(h('h2',{},'Drafts waiting on you'));
  if(!d){out.push(card(h('div',{class:'t'},'No draft is waiting.'),h('div',{class:'btns'},actBtn('Draft today\'s DMs','dm_draft',{})),
    h('div',{class:'s dim'},'Runs python -m faceless dm. It writes drafts only; nothing is ever sent for you.'),src('outbound/drafts/')));return out}
  out.push(card(h('div',{class:'s'},'You send these by hand. Nothing is sent for you. Replace every [slot] with that person\'s own words first; if you cannot, skip it. After sending, press Sent so the funnel and the follow-ups move.'),src(d.source)));
  d.drafts.forEach(function(m){var hid='hd-'+m.id,sent=m.status==='sent';
    function args(status){return function(){var e=document.getElementById(hid),v=e?e.value.trim():'',a={draft:m.id,status:status};if(v)a.handle=v;return a}}
    function b(label,status,ghost){return actBtn(label,'dm_log',args(status),{sm:true,ghost:ghost,key:m.id})}
    out.push(card(h('div',{class:'t'},h('span',{class:'tag '+(sent?'ok':'warn')},sent?'sent':'to send'),m.id+(m.handle?'  '+m.handle:'')),h('div',{class:'s'},'Why this person: '+m.why),
      (m.open_slots&&m.open_slots.length)?h('div',{class:'s warn'},'Fill before sending: '+m.open_slots.join(', ')):null,
      h('div',{class:'msg'},m.first),
      h('div',{class:'btns'},copyBtn('Copy message',m.first),m.handle?null:h('input',{id:hid,type:'text',placeholder:'@their handle (optional)',autocomplete:'off',autocapitalize:'off',spellcheck:'false'})),
      h('div',{class:'btns'},sent?null:b('Sent','sent'),b('Replied','replied',!sent),b('Bought','bought',true),b('No reply: close','dead',true)),
      h('details',{},h('summary',{},'Follow-ups and the after-reply line'),
        h('div',{class:'s'},'Day 3, only if no reply'),h('div',{class:'msg'},m.follow_up_2),copyBtn('Copy',m.follow_up_2,true),
        h('div',{class:'s',style:'margin-top:10px'},'Day 7, then stop'),h('div',{class:'msg'},m.follow_up_3),copyBtn('Copy',m.follow_up_3,true),
        h('div',{class:'s',style:'margin-top:10px'},'After they reply (the only place a link goes)'),h('div',{class:'msg'},m.after_reply_free),copyBtn('Copy',m.after_reply_free,true),
        m.after_reply_paid?[h('div',{class:'s',style:'margin-top:10px'},'If they ask for more than the checklist'),h('div',{class:'msg'},m.after_reply_paid),copyBtn('Copy',m.after_reply_paid,true)]:null)))});
  return out};
V.jobs=function(){var j=D.jobs,p=D.phone,out=[];if(!j)return[missing('Jobs','state/jobs')];
  out.push(card(h('div',{class:'big'},j.total),h('div',{class:'note'},'jobs on record'),Object.keys(j.byStatus).map(function(k){return row(k,j.byStatus[k])}),src('state/jobs/*.json')));
  function list(title,rows,total,cls,label,note){out.push(h('h2',{},title+' ('+total+')'));
    out.push(rows.length?card(note?h('div',{class:'s dim',style:'margin-bottom:8px'},note):null,rows.map(function(r){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+cls},r.day),r.title),
      h('div',{class:'s'},'Stopped at: '+r.step+(r.score!=null?' · score '+r.score:'')),r.why?h('div',{class:'s'},r.why):null,h('code',{},r.id),
      h('div',{class:'btns'},actBtn(label,'job_retry',{job:r.id},{sm:true}),viewBtn(r.id,'View steps')),detail(r.id))}),
      total>rows.length?h('div',{class:'s dim',style:'margin-top:8px'},'Showing the newest '+rows.length+' of '+total):null,src('state/jobs/*.json')):card(h('div',{class:'t ok'},'None.'),src('state/jobs/*.json')))}
  list('Failed',j.failed,j.failedCount,'stop','Retry','Retry runs python -m faceless retry <job_id>: the job starts again from where it stopped and is packaged, never uploaded.');
  list('Held for review',j.held,j.heldCount,'warn','Release: re-run gates','Release renders the job again from its files and runs every gate (python -m faceless retry <job_id>). A pass becomes packaged; a fail stays held with the reason recorded. Nothing is uploaded.');
  if(p){
    out.push(h('h2',{},'Phone jobs held ('+p.heldCount+')'));
    out.push(p.held.length?card(p.held.map(function(r){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag warn'},r.kind),r.id),
      r.why?h('div',{class:'s'},'Held because: '+r.why):null,r.gate?h('div',{class:'s warn'},'A release would still be stopped by: '+r.gate):null,
      h('div',{class:'btns'},actBtn('Release','phone_requeue',{job:r.id},{sm:true}),viewBtn(r.id,'View steps')),detail(r.id))}),src(p.source)):card(h('div',{class:'t ok'},'None.'),src(p.source)));
    if(p.blockedCount)out.push(card(h('div',{class:'t'},p.blockedCount+' queued phone job(s) are stopped by a gate'),
      Object.keys(p.blockedWhy||{}).map(function(k){return row(k,p.blockedWhy[k])}),
      h('div',{class:'s dim'},'Display only: each gate is a switch or a daily cap in studio.toml [phone], which only you change.'),src(p.source)))}
  out.push(h('h2',{},'Newest 20'));
  out.push(card(j.newest.map(function(r){var cls=r.status==='failed'?'stop':r.status==='held'?'warn':(r.status==='published'||r.status==='packaged')?'ok':'dim';
    return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+cls},r.status),r.title),h('div',{class:'s'},r.day+' · '+r.pillar+(r.score!=null?' · score '+r.score:'')),
      h('div',{class:'btns'},viewBtn(r.id,'View steps')),detail(r.id))}),src('state/jobs/*.json')));
  return out};
V.agents=function(){var a=D.agents,m=D.hermes,out=[];
  if(!a){out.push(missing('Agents','installed CLI agents'));return out}
  var clis=a.clis||[],hd=a.herdr||{};
  out.push(card(h('div',{class:'grid'},cell(clis.filter(function(c){return c.installed}).length,'installed'),
    cell((hd.workspaces||[]).length,'herdr workspaces'),cell((hd.agents||[]).length,'live agents')),src(a.source)));
  if(!hd.running)out.push(card(h('div',{class:'t warn'},'herdr is not running'),h('div',{class:'s'},hd.error||''),h('div',{class:'btns'},copyBtn('Copy: herdr server','herdr server',true)),src('herdr api snapshot')));
  else{
    out.push(h('h2',{},'herdr workspaces'));
    out.push(card((hd.workspaces||[]).length?hd.workspaces.map(function(w){return h('div',{class:'item'},
      h('div',{class:'t'},h('span',{class:'tag '+(w.focused?'ok':'dim')},w.focused?'focused':(w.status||'idle')),w.label||w.id),
      h('div',{class:'s'},w.panes+' pane(s)'),h('code',{},w.id),h('div',{class:'btns'},actBtn('Focus in herdr','herdr_focus',{target:w.id},{sm:true,ghost:w.focused})))}):h('div',{class:'t'},'No workspaces.'),src('herdr api snapshot')));
    if((hd.agents||[]).length)out.push(card(h('div',{class:'grid'},cell(hd.agents.length,'live agents')),
      hd.agents.map(function(x){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag ok'},x.status||'unknown'),x.agent||'agent'),
        h('div',{class:'s'},(x.workspace||'')+(x.cwd?' · '+x.cwd:'')),h('code',{},x.id),h('div',{class:'btns'},actBtn('Focus this pane','herdr_focus',{target:x.id},{sm:true})))}),src('herdr api snapshot')));
  }
  out.push(h('h2',{},'Installed agents'));
  out.push(card(clis.map(function(c){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+(c.installed?'ok':'dim')},c.installed?'installed':'missing'),c.name),
    h('div',{class:'s'},(c.version||'version unknown')+(c.default&&c.default.model?' · default '+c.default.model+(c.default.provider?' on '+c.default.provider:''):'')),
    c.installed?h('div',{class:'btns'},copyBtn('Copy: '+c.launch,c.launch,true)):null,h('code',{},c.path||''))}),src(a.source)));
  if(m){out.push(h('h2',{},'Hermes'));
    var gw=(m.gateway&&m.gateway.state)||'unknown';
    out.push(card(h('div',{class:'t'},h('span',{class:'tag '+(m.installed?'ok':'warn')},m.version||'not found'),
      (m.channel||'')+(m.release?' · '+m.release:'')+(m.updateAvailable?' · update available':'')),
      row('Gateway',gw),row('Messaging set up for',(m.messaging&&m.messaging.length)?m.messaging.join(', '):'nothing'),row('Desktop app',m.desktop?'installed':'not installed'),
      h('div',{class:'btns'},m.desktop?h('a',{class:'btnlink',href:m.launch.scheme},'Open Hermes desktop'):null,
        copyBtn('Copy: '+m.launch.command,m.launch.command,true),gw!=='running'&&m.launch.gateway?copyBtn('Copy: '+m.launch.gateway,m.launch.gateway,true):null),src(m.source)));
    out.push(h('h2',{},'Hermes sessions'));
    if(!m.sessions||!m.sessions.length)out.push(card(h('div',{class:'t'},m.sessions?'No sessions yet.':'Session database not readable.'),src('~/.hermes/state.db')));
    else out.push(card(m.sessions.map(function(s){return h('div',{class:'item'},h('div',{class:'t'},s.name||s.id),
      h('div',{class:'s'},(s.source||'source unknown')+(s.model?' · '+s.model:'')+' · '+s.messages+' message'+(s.messages===1?'':'s')),
      h('div',{class:'s'},(s.startedAt?when(s.startedAt):'start unknown')+(s.endedAt?' → '+when(s.endedAt):' · still open')),h('code',{},s.id))}),
      h('div',{class:'s dim',style:'margin-top:8px'},'Display only: the session list is read from the database; message content is never read.'),src('~/.hermes/state.db (sessions, read-only)')));}
  return out};
var CAT=null,CATERR='',MQ='',MP='';
function fillProviders(){var sel=document.getElementById('mp');if(!sel||!CAT)return;sel.textContent='';sel.appendChild(h('option',{value:''},'All providers'));
  CAT.providers.forEach(function(p){sel.appendChild(h('option',{value:p.id},p.name+' ('+p.count+')'))});sel.value=MP}
function fillModels(){var box=document.getElementById('model-results');if(!box)return;box.textContent='';
  if(CATERR){box.appendChild(h('div',{class:'t warn'},CATERR));return}
  if(!CAT){box.appendChild(h('div',{class:'note'},'Loading the catalog…'));return}
  var q=MQ.trim().toLowerCase(),shown=0,MAX=100,per=q?MAX:8;
  CAT.providers.forEach(function(p){if(MP&&p.id!==MP)return;
    var hits=p.models.filter(function(m){return !q||m.name.toLowerCase().indexOf(q)>=0||m.id.toLowerCase().indexOf(q)>=0});
    if(!hits.length)return;var take=hits.slice(0,Math.min(per,MAX-shown));if(!take.length)return;shown+=take.length;
    box.appendChild(h('div',{class:'item'},h('div',{class:'t'},p.name+' ',h('span',{class:'dim'},'('+p.count+')')),
      take.map(function(mm){return h('div',{class:'s'},mm.name+' ',h('code',{},p.id+'/'+mm.id))})))});
  box.appendChild(h('div',{class:'s dim'},shown?('Showing '+shown+' of '+CAT.totalModels+'. Refine the search to see more.'):'No model matches.'));
}
function loadModels(){api('models.json').then(function(d){CAT=d;CATERR='';fillProviders();fillModels()},function(e){CATERR='Could not load the catalog ('+(e&&e.message||'error')+').';fillModels()})}
V.models=function(){var m=D.models,out=[];
  if(!m)return[missing('Models','model sources')];
  out.push(card(h('div',{class:'grid'},cell(m.catalog?m.catalog.providers:'—','providers'),cell(m.catalog?m.catalog.models:'—','models'),cell((m.ollama&&m.ollama.models||[]).length,'local ollama')),
    h('div',{class:'s dim',style:'margin-top:8px'},'Display only, apart from the search: this tab starts, pulls and switches no model.'),src(m.source)));
  out.push(h('h2',{},'Agent defaults'));
  out.push(card((m.defaults||[]).map(function(d){return h('div',{class:'item'},h('div',{class:'t'},d.agent),
    h('div',{class:'s'},d.model?d.model+(d.provider?' on '+d.provider:''):'not set in this agent\'s config'),src(d.source||'agent config'))}),src('agent config files')));
  out.push(h('h2',{},'Local Ollama'));
  out.push(card(m.ollama&&m.ollama.installed?((m.ollama.models||[]).length?m.ollama.models.map(function(x){return h('div',{class:'item'},h('div',{class:'t'},x.name),h('div',{class:'s'},x.size||''),h('code',{},x.id||''))}):h('div',{class:'t'},'Ollama is installed; no local model is pulled.')):h('div',{class:'t'},'Ollama is not installed.'),src('ollama list')));
  out.push(h('h2',{},'Model catalog'));
  out.push(card(h('div',{class:'s'},'OpenCode provider catalog, read from this machine. Search by model or provider id; the full list loads on this tab only.'),
    h('div',{class:'btns'},h('input',{id:'mq',type:'search',placeholder:'Search models…',value:MQ,oninput:function(e){MQ=e.target.value;fillModels()}}),
      h('select',{id:'mp',onchange:function(e){MP=e.target.value;fillModels()}},h('option',{value:''},'All providers'))),src('~/.cache/opencode/models.json')));
  var box=h('div',{id:'model-results',class:'card'},h('div',{class:'note'},'Loading the catalog…'));
  out.push(box);
  if(!CAT&&!CATERR)loadModels();else setTimeout(function(){fillProviders();fillModels()},0);
  return out};
function activityItem(r,running){var cls=running?'info':r.ok?'ok':r.refused?'warn':'stop',word=running?'running':r.ok?'done':r.refused?'refused':'failed';
  return h('div',{class:'item'},h('div',{class:'t'},running?h('span',{class:'spin'}):null,h('span',{class:'tag '+cls},word),r.label||r.action),
    h('div',{class:'s'},(running?'Started '+when(r.at):when(r.at))+(r.actor&&r.actor!=='owner'?' · by '+r.actor:'')+(r.seconds?' · '+r.seconds+' s':'')+((r.exit!=null&&!running)?' · exit '+r.exit:'')+(akey(r.args)?' · '+akey(r.args):'')),
    (!running&&r.summary)?h('div',{class:'s'},r.summary):null,
    (!running&&!r.ok&&(r.stderr||r.error))?h('pre',{class:'out'},r.stderr||r.error):null)}
V.alerts=function(){var a=D.alerts||[],out=[];
  out.push(h('h2',{},'Activity'));
  out.push((ACT.running.length||ACT.recent.length)?card(ACT.running.map(function(r){return activityItem(r,true)}),ACT.recent.map(function(r){return activityItem(r,false)}),
    src('state/journal.jsonl (CC_ACTION); what is running is held in the server\'s memory only')):card(h('div',{class:'t'},'No button has been pressed yet.'),src('state/journal.jsonl (CC_ACTION)')));
  out.push(h('h2',{},'Alerts'));
  if(!a.length)out.push(card(h('div',{class:'big ok'},'All clear'),h('div',{class:'note'},'No alert is derived from the current state.'),src('derived from this page\'s own data')));
  else{out.push(card(h('div',{class:'s'},'Each alert is a fact from this page\'s data. A gold button runs the fix here; Copy fix is for the ones only a terminal or a decision of yours can do.')));out.push(card(a.map(alertItem)))}
  return out};

function draw(){
  var view=document.getElementById('view');view.textContent='';dirty=false;
  if(!D){view.appendChild(card(h('div',{class:'t warn'},'No data yet'),h('div',{class:'note'},'The server has not answered and nothing is saved on this phone.')));return}
  V[tab]().forEach(function(n){view.appendChild(n)});
  var age=(Date.now()-new Date(D.generatedAt).getTime())/36e5,b=document.getElementById('banner'),msg='';
  if(live===false)msg='Server not reachable. Showing the last known state from '+when(D.generatedAt)+'. Buttons need the server.';
  else if(age>(D.staleAfterHours||24))msg='This state is '+Math.floor(age)+' hours old. On the computer: python -m faceless dashboard';
  b.textContent=msg;b.className=msg?'on':'';
  document.getElementById('asof').textContent=(live?'live · ':live===false?'offline · ':'')+when(D.generatedAt)+(D.source&&D.source.commit?' · '+D.source.commit:'');
  var nav=document.getElementById('nav');nav.textContent='';
  var n=(D.alerts||[]).filter(function(a){return a.level!=='info'}).length;
  TABS.forEach(function(t){nav.appendChild(h('button',{type:'button',class:t[0]===tab?'on':'','aria-label':t[1],on:function(){go(t[0])}},h('i',{},t[2]),t[1],(t[0]==='alerts'&&n)?h('span',{class:'dot'},n):null))});
  strip()}
function refresh(){
  return api('overview.json').then(function(d){D=d;live=true;LS.set('qm_overview',JSON.stringify(d));if(!polling&&d.activity)ACT.recent=d.activity;redraw()},
    function(){live=location.protocol==='file:'?null:false;redraw()})}
var y0=null,pull=document.getElementById('pull');
addEventListener('touchstart',function(e){y0=(window.scrollY<=0)?e.touches[0].clientY:null},{passive:true});
addEventListener('touchmove',function(e){if(y0==null)return;var dy=e.touches[0].clientY-y0;if(dy>0){pull.style.height=Math.min(48,dy/2)+'px';pull.textContent=dy>120?'Release to refresh':'Pull to refresh'}},{passive:true});
addEventListener('touchend',function(){if(y0==null)return;var go2=pull.textContent==='Release to refresh';pull.style.height='0';pull.textContent='';y0=null;if(go2){toast('Refreshing');refresh()}},{passive:true});
document.addEventListener('visibilitychange',function(){if(!document.hidden)refresh()});
document.addEventListener('focusout',function(){if(dirty)setTimeout(function(){if(dirty&&!typing())draw()},80)});
document.getElementById('strip').addEventListener('click',function(){go('alerts')});
setInterval(function(){if(!document.hidden&&!typing())refresh()},60000);
setInterval(nsTick,30000);if(NS.on)setTimeout(nsTick,1500);
if('serviceWorker' in navigator&&window.isSecureContext){navigator.serviceWorker.register('sw.js').catch(function(){})}
draw();refresh();
if(location.protocol!=='file:')api('actions.json').then(function(a){ACT.running=a.running||[];if(a.recent)ACT.recent=a.recent;strip();if(ACT.running.length){poll();redraw()}},function(){});
})();
"""


def render(doc: dict) -> str:
    seed = json.dumps(doc, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            "<meta name=\"robots\" content=\"noindex,nofollow,noarchive\"><meta name=\"referrer\" content=\"no-referrer\">"
            f"<meta name=\"theme-color\" content=\"{BG}\"><meta name=\"apple-mobile-web-app-capable\" content=\"yes\">"
            "<meta name=\"mobile-web-app-capable\" content=\"yes\"><meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\">"
            "<link rel=\"manifest\" href=\"manifest.webmanifest\"><link rel=\"icon\" href=\"icon-192.png\"><link rel=\"apple-touch-icon\" href=\"icon-192.png\">"
            f"<title>Quiet Money Command Center</title><style>{CSS}</style></head><body>"
            "<div id=\"pull\"></div><header><h1>Quiet Money</h1><div id=\"asof\"></div></header><div id=\"banner\" role=\"status\"></div><div id=\"strip\" role=\"status\" title=\"Open the activity log\"></div>"
            "<main id=\"view\"></main><nav id=\"nav\" aria-label=\"Sections\"></nav><div id=\"toast\" role=\"status\"></div>"
            f"<script id=\"seed\" type=\"application/json\">{seed}</script><script>{JS}</script></body></html>\n")


def icon(size: int) -> bytes:
    """The home-screen icon, drawn in code: a gold ring and bar on the page's black."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)
    r, w = int(size * 0.27), max(3, int(size * 0.075))
    c = size // 2
    d.ellipse((c - r, c - r, c + r, c + r), outline=GOLD, width=w)
    d.line((c + int(r * 0.35), c + int(r * 0.35), c + int(r * 1.05), c + int(r * 1.05)), fill=GOLD, width=w)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def assets() -> dict[str, tuple[str, bytes]]:
    """The static files beside the page: path -> (content type, bytes). None of them holds state."""
    return {"manifest.webmanifest": ("application/manifest+json", json.dumps(MANIFEST).encode()),
            "sw.js": ("text/javascript; charset=utf-8", SERVICE_WORKER.encode()),
            "icon-192.png": ("image/png", icon(192)), "icon-512.png": ("image/png", icon(512))}


def write(doc: dict | None = None, out: Path | None = None) -> dict:
    from faceless import overview
    doc = doc or overview.write()
    out = Path(out or OUT)
    out.mkdir(parents=True, exist_ok=True)
    html = render(doc)
    write_atomic(out / "index.html", html)
    write_atomic(out / "overview.json", json.dumps(doc, ensure_ascii=False))
    total = len(html.encode("utf-8"))
    for name, (_, data) in assets().items():
        (out / name).write_bytes(data)
        total += len(data)
    return {"dir": str(out), "bytes": total, "generatedAt": doc["generatedAt"]}
