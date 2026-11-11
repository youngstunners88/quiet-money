"""The command center page: one self-contained, mobile-first HTML file that shows `overview.build()` and nothing else. Reads only.

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
html,body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;overflow-x:hidden}
body{padding:env(safe-area-inset-top) 0 calc(72px + env(safe-area-inset-bottom));min-height:100vh;overscroll-behavior-y:contain}
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
.btns{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.5px;background:#111316;border:1px solid var(--line);border-radius:6px;padding:2px 5px;display:inline-block;max-width:100%}
a{color:var(--gold)}
details summary{color:var(--gold);font-size:14px;padding:8px 0;min-height:36px}
nav{position:fixed;left:0;right:0;bottom:0;display:flex;background:#111316;border-top:1px solid var(--line);padding-bottom:env(safe-area-inset-bottom);z-index:5}
nav button{flex:1;background:transparent;color:var(--dim);border-radius:0;padding:10px 2px 12px;font-size:12px;font-weight:600;min-height:56px;position:relative}
nav button.on{color:var(--gold)}
nav button i{display:block;font-style:normal;font-size:18px;line-height:1.2}
nav .dot{position:absolute;top:6px;right:calc(50% - 22px);min-width:17px;height:17px;border-radius:9px;background:var(--stop);color:#fff;font-size:11px;line-height:17px;padding:0 4px}
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
var TABS=[['today','Today','\u25CE'],['money','Money','$'],['dms','DMs','\u2709'],['jobs','Jobs','\u25A4'],['alerts','Alerts','!']];
var tab=(location.hash||'').slice(1)||LS.get('qm_tab')||'today';
if(!TABS.some(function(t){return t[0]===tab}))tab='today';

function h(tag,attrs){var e=document.createElement(tag),i,c;attrs=attrs||{};
  for(var k in attrs){if(k==='class')e.className=attrs[k];else if(k==='on')e.addEventListener('click',attrs[k]);else e.setAttribute(k,attrs[k])}
  for(i=2;i<arguments.length;i++){c=arguments[i];if(c==null||c===false)continue;
    if(Array.isArray(c)){c.forEach(function(x){if(x!=null&&x!==false)e.appendChild(typeof x==='object'?x:document.createTextNode(String(x)))})}
    else e.appendChild(typeof c==='object'?c:document.createTextNode(String(c)))}
  return e}
function card(){var a=[].slice.call(arguments);return h.apply(null,['div',{class:'card'}].concat(a))}
function src(s){return h('div',{class:'src'},'source: '+s)}
function row(label,value){return h('div',{class:'row'},h('span',{},label),h('b',{},value==null?'\u2014':String(value)))}
function cell(n,label){return h('div',{class:'cell'},h('b',{},n==null?'\u2014':String(n)),h('span',{},label))}
function missing(what,where){return card(h('div',{class:'t warn'},what+': source missing'),h('div',{class:'note'},'Nothing is shown rather than a zero that would look real.'),src(where))}
function money(n){return n==null?'\u2014':'$'+Number(n).toFixed(2)}
function when(iso){if(!iso)return'unknown';var d=new Date(iso);return isNaN(d)?iso:d.toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
function toast(t){var e=document.getElementById('toast');e.textContent=t;e.className='on';setTimeout(function(){e.className=''},1400)}
function copy(text){
  function fallback(){var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');ta.style.position='fixed';ta.style.top='-999px';document.body.appendChild(ta);ta.select();ta.setSelectionRange(0,text.length);var ok=false;try{ok=document.execCommand('copy')}catch(e){}document.body.removeChild(ta);toast(ok?'Copied':'Press and hold the text to copy')}
  if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(function(){toast('Copied')},fallback)}else fallback()}
function copyBtn(label,text,ghost){return h('button',{class:ghost?'ghost':'',type:'button',on:function(){copy(text)}},label)}
function action(a,i){return h('div',{class:'item'},h('div',{class:'t'},(i+1)+'. '+a.title+' ',h('span',{class:'dim'},'\u00B7 '+a.minutes+' min')),h('div',{class:'s'},a.how),h('div',{class:'s'},'Why: '+a.why),src(a.source))}
function alertItem(a){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+a.level},a.level),a.text),h('div',{class:'s'},'Fix: '+a.fix),src(a.source))}

var V={};
V.today=function(){var j=D.jobs,out=[];
  if(!j)out.push(missing('Daily run','state/jobs'));
  else{
    out.push(card(h('div',{class:'big '+(j.ranToday?'ok':'warn')},j.ranToday?'Ran today':'Not run today'),
      h('div',{class:'note'},j.ranToday?(j.passedToday+' passed, '+j.heldToday+' held, '+j.failedToday+' failed of '+j.madeToday+' made'):('Last run day: '+(j.lastRunDay||'none')+(j.lastRun?' ('+j.lastRun.passed+' passed, '+j.lastRun.held+' held, '+j.lastRun.failed+' failed, '+j.lastRun.unfinished+' unfinished)':''))),
      src(j.source)));
    out.push(card(h('div',{class:'grid'},cell(j.passedToday,'passed today'),cell(j.postedToday,'posted today'),cell(j.heldToday,'held today')),
      row('TikTok posts waiting in the phone queue',j.tiktokQueued),row('Last post recorded',j.lastPostAt?when(j.lastPostAt):'none'),src('state/jobs, state/phone/receipts.jsonl, state/phone/jobs')));
  }
  var need=(D.alerts||[]).filter(function(a){return a.level!=='info'});
  out.push(h('h2',{},'Needs you now'));
  if(D.money&&D.money.actions&&D.money.actions.length)out.push(card(action(D.money.actions[0],0)));
  out.push(need.length?card(need.slice(0,4).map(alertItem)):card(h('div',{class:'t ok'},'Nothing is stopped or warning.'),src('derived from this page\'s own data')));
  return out};
V.money=function(){var c=D.cash,o=D.offers,ob=D.outbound,sp=D.spend,out=[];
  if(!c)out.push(missing('Revenue','state/receipts.jsonl'));
  else out.push(card(h('div',{class:'dim',style:'font-size:13px'},'Revenue this month'),h('div',{class:'big'},money(c.revenueMTD)),
    h('div',{class:'note'},c.note?c.note:(c.receipts+' receipts, '+money(c.netMTD)+' after fees')),
    row('Receipts this month',c.receipts),row('Receipts all time',c.receiptsAllTime),row('Net after fees this month',money(c.netMTD)),
    Object.keys(c.byRail||{}).map(function(k){return row(k,money(c.byRail[k].gross)+' ('+c.byRail[k].receipts+')')}),src(c.source)));
  out.push(h('h2',{},'Next money move'));
  var acts=(D.money&&D.money.actions)||[];
  out.push(acts.length?card(acts.map(action),D.money.brief?h('div',{class:'s dim',style:'margin-top:8px'},'Full brief: '+D.money.brief):null):card(h('div',{class:'t'},'No action is waiting on you.'),src('faceless/moneybrief.py')));
  out.push(h('h2',{},'Offers'));
  if(!o)out.push(missing('Offers','channel/shop/catalog.json'));
  else out.push(card(h('div',{class:'grid',style:'grid-template-columns:1fr 1fr'},cell(o.live,'live listings'),cell(o.built,'products built')),
    o.items.map(function(i){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+(i.live?'ok':'dim')},i.live?'live':'not listed'),i.name),
      h('div',{class:'s'},i.live?('Listed at '+(i.price===0?'$0+ (free gift)':money(i.price))):('Catalog test price '+money(i.catalogPrice)+'; needs your price')),
      i.live&&i.url?h('div',{class:'s'},h('a',{href:i.url,rel:'noreferrer noopener',target:'_blank'},'Open listing')):null)}),src(o.source)));
  out.push(h('h2',{},'DM funnel'));
  out.push(ob?card(h('div',{class:'grid'},cell(ob.sent,'sent'),cell(ob.replied,'replied'),cell(ob.bought,'bought')),src(ob.source)):missing('DM funnel','state/outbound.jsonl'));
  if(sp)out.push(card(row('Spent today',money(sp.todayUsd)),row('Daily ceiling',money(sp.ceilingUsd)),row('Paused',sp.paused||'no'),src(sp.source)));
  return out};
V.dms=function(){var ob=D.outbound,d=D.dms,out=[];
  out.push(ob?card(h('div',{class:'grid'},cell(ob.draftedToday,'drafted today'),cell(ob.sent,'sent'),cell(ob.replied,'replied')),
    row('Clicked',ob.clicked),row('Bought',ob.bought),row('Closed without reply',ob.dead),row('Waiting for you to send',ob.blockedOnOwner),row('Follow-ups due',ob.followUpsDue),src(ob.source)):missing('DM record','state/outbound.jsonl'));
  if(D.followUps&&D.followUps.length){out.push(h('h2',{},'Follow-ups due'));
    out.push(card(D.followUps.map(function(f){return h('div',{class:'item'},h('div',{class:'t'},f.draft_id),h('div',{class:'s'},'Sent '+f.days_since_sent+' days ago: send '+f.send.replace(/_/g,' ')))}),src('state/outbound.jsonl')))}
  out.push(h('h2',{},'Today\'s drafts'));
  if(!d){out.push(card(h('div',{class:'t'},'No drafts for today yet.'),h('div',{class:'s'},'On the computer: '),h('code',{},'python -m faceless dm'),src('outbound/drafts/')));return out}
  out.push(card(h('div',{class:'s'},'You send these by hand. Nothing is sent for you. Replace every [slot] with that person\'s own words first; if you cannot, skip it.'),src(d.source)));
  d.drafts.forEach(function(m){var cmd='python -m faceless dm log '+m.id+' sent'+(m.handle?'':' --handle @theirhandle');
    out.push(card(h('div',{class:'t'},m.id+(m.handle?'  '+m.handle:'')),h('div',{class:'s'},'Why this person: '+m.why),
      (m.open_slots&&m.open_slots.length)?h('div',{class:'s warn'},'Fill before sending: '+m.open_slots.join(', ')):null,
      h('div',{class:'msg'},m.first),h('div',{class:'btns'},copyBtn('Copy message',m.first),copyBtn('Copy log line',cmd,true)),
      h('details',{},h('summary',{},'Follow-ups and the after-reply line'),
        h('div',{class:'s'},'Day 3, only if no reply'),h('div',{class:'msg'},m.follow_up_2),copyBtn('Copy',m.follow_up_2,true),
        h('div',{class:'s',style:'margin-top:10px'},'Day 7, then stop'),h('div',{class:'msg'},m.follow_up_3),copyBtn('Copy',m.follow_up_3,true),
        h('div',{class:'s',style:'margin-top:10px'},'After they reply (the only place a link goes)'),h('div',{class:'msg'},m.after_reply_free),copyBtn('Copy',m.after_reply_free,true),
        m.after_reply_paid?[h('div',{class:'s',style:'margin-top:10px'},'If they ask for more than the checklist'),h('div',{class:'msg'},m.after_reply_paid),copyBtn('Copy',m.after_reply_paid,true)]:null)))});
  return out};
V.jobs=function(){var j=D.jobs,out=[];if(!j)return[missing('Jobs','state/jobs')];
  out.push(card(h('div',{class:'big'},j.total),h('div',{class:'note'},'jobs on record'),Object.keys(j.byStatus).map(function(k){return row(k,j.byStatus[k])}),src('state/jobs/*.json')));
  function list(title,rows,total,cls){out.push(h('h2',{},title+' ('+total+')'));
    out.push(rows.length?card(rows.map(function(r){return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+cls},r.day),r.title),
      h('div',{class:'s'},'Stopped at: '+r.step+(r.score!=null?' \u00B7 score '+r.score:'')),r.why?h('div',{class:'s'},r.why):null,h('code',{},r.id))}),
      total>rows.length?h('div',{class:'s dim',style:'margin-top:8px'},'Showing the newest '+rows.length+' of '+total):null,src('state/jobs/*.json')):card(h('div',{class:'t ok'},'None.'),src('state/jobs/*.json')))}
  list('Failed',j.failed,j.failedCount,'stop');list('Held for review',j.held,j.heldCount,'warn');
  out.push(h('h2',{},'Newest 20'));
  out.push(card(j.newest.map(function(r){var cls=r.status==='failed'?'stop':r.status==='held'?'warn':(r.status==='published'||r.status==='packaged')?'ok':'dim';
    return h('div',{class:'item'},h('div',{class:'t'},h('span',{class:'tag '+cls},r.status),r.title),h('div',{class:'s'},r.day+' \u00B7 '+r.pillar+(r.score!=null?' \u00B7 score '+r.score:'')))}),src('state/jobs/*.json')));
  return out};
V.alerts=function(){var a=D.alerts||[];
  if(!a.length)return[card(h('div',{class:'big ok'},'All clear'),h('div',{class:'note'},'No alert is derived from the current state.'),src('derived from this page\'s own data'))];
  return[card(h('div',{class:'s'},'Each alert is a fact from this page\'s data, with the command that fixes it.')),card(a.map(function(x){return h('div',{class:'item'},alertItem(x).childNodes[0],h('div',{class:'s'},'Fix: '+x.fix),h('div',{class:'btns'},copyBtn('Copy fix',x.fix,true)),src(x.source))}))]};

function draw(){
  var view=document.getElementById('view');view.textContent='';
  if(!D){view.appendChild(card(h('div',{class:'t warn'},'No data yet'),h('div',{class:'note'},'The server has not answered and nothing is saved on this phone.')));return}
  V[tab]().forEach(function(n){view.appendChild(n)});
  var age=(Date.now()-new Date(D.generatedAt).getTime())/36e5,b=document.getElementById('banner'),msg='';
  if(live===false)msg='Server not reachable. Showing the last known state from '+when(D.generatedAt)+'.';
  else if(age>(D.staleAfterHours||24))msg='This state is '+Math.floor(age)+' hours old. On the computer: python -m faceless dashboard';
  b.textContent=msg;b.className=msg?'on':'';
  document.getElementById('asof').textContent=(live?'live \u00B7 ':live===false?'offline \u00B7 ':'')+when(D.generatedAt)+(D.source&&D.source.commit?' \u00B7 '+D.source.commit:'');
  var nav=document.getElementById('nav');nav.textContent='';
  var n=(D.alerts||[]).filter(function(a){return a.level!=='info'}).length;
  TABS.forEach(function(t){nav.appendChild(h('button',{type:'button',class:t[0]===tab?'on':'','aria-label':t[1],on:function(){tab=t[0];LS.set('qm_tab',tab);try{history.replaceState(null,'','#'+tab)}catch(e){}window.scrollTo(0,0);draw()}},h('i',{},t[2]),t[1],(t[0]==='alerts'&&n)?h('span',{class:'dot'},n):null))})}
function refresh(){
  return fetch('overview.json',{headers:tok?{Authorization:'Bearer '+tok}:{},cache:'no-store',credentials:'omit'}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})
    .then(function(d){D=d;live=true;LS.set('qm_overview',JSON.stringify(d));draw()},function(){live=location.protocol==='file:'?null:false;draw()})}
var y0=null,pull=document.getElementById('pull');
addEventListener('touchstart',function(e){y0=(window.scrollY<=0)?e.touches[0].clientY:null},{passive:true});
addEventListener('touchmove',function(e){if(y0==null)return;var dy=e.touches[0].clientY-y0;if(dy>0){pull.style.height=Math.min(48,dy/2)+'px';pull.textContent=dy>120?'Release to refresh':'Pull to refresh'}},{passive:true});
addEventListener('touchend',function(){if(y0==null)return;var go=pull.textContent==='Release to refresh';pull.style.height='0';pull.textContent='';y0=null;if(go){toast('Refreshing');refresh()}},{passive:true});
document.addEventListener('visibilitychange',function(){if(!document.hidden)refresh()});
if('serviceWorker' in navigator&&window.isSecureContext){navigator.serviceWorker.register('sw.js').catch(function(){})}
draw();refresh();
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
            "<div id=\"pull\"></div><header><h1>Quiet Money</h1><div id=\"asof\"></div></header><div id=\"banner\" role=\"status\"></div>"
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
