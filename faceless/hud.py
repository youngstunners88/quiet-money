"""The command center's front page: a head-up display of `instruments.build()`. One self-contained HTML file, no framework, no
external request, no cookie, and no button that changes anything: it only reads `/instruments.json` every five seconds.

The page is built once. After that nothing is re-rendered: each poll updates the text of existing nodes and the stroke of existing
arcs, and CSS eases the needles to their new place (not at all under `prefers-reduced-motion`). A node is added or removed only
when an agent, a waiting item or a feed line appears or goes. Every gauge has an `aria-label` and a text value beside it; a value
that is not known is drawn grey with the word "unknown" and its reason, never as a zero. Every string reaches the page as JSON and
is placed with `textContent`.

Whatever needs the owner links to the action desk (`/desk`, the page with the buttons). A few items carry one button of their own:
re-check the keys, take a silent agent's mission back, send a held mission to its agent (asked twice). Each posts one allowlisted
action name to `POST /action`, the same door the desk uses. Nothing on this page sends a message, posts or uploads.
"""

from __future__ import annotations

from faceless.dashboard import BG

CSS = r"""
:root{--bg:#060a0f;--panel:#0a121a;--line:#173142;--ac:#4fd8ff;--tx:#d9f1fa;--dim:#7d9aa8;--ok:#3ddc84;--warn:#ffb020;--bad:#ff5468;--off:#5b6b74;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--tx);font:14px/1.4 var(--mono);-webkit-text-size-adjust:100%}
body{min-height:100vh;padding:max(10px,env(safe-area-inset-top)) max(10px,env(safe-area-inset-right)) 24px max(10px,env(safe-area-inset-left));
background-image:linear-gradient(rgba(79,216,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(79,216,255,.035) 1px,transparent 1px);background-size:32px 32px;overflow-x:hidden}
a{color:var(--ac)}
h1{font-size:13px;letter-spacing:.22em;margin:0;font-weight:600;color:var(--ac)}
h2{font-size:11px;letter-spacing:.24em;margin:0 0 10px;font-weight:600;color:var(--dim);text-transform:uppercase}
#hud{display:grid;gap:12px;grid-template-columns:minmax(0,1fr);max-width:1500px;margin:0 auto}
.panel{position:relative;background:linear-gradient(180deg,rgba(13,24,34,.92),rgba(8,14,20,.92));border:1px solid var(--line);padding:14px;min-width:0}
.panel:before,.panel:after{content:"";position:absolute;width:14px;height:14px;border:2px solid var(--ac);opacity:.8;pointer-events:none}
.panel:before{left:-1px;top:-1px;border-right:0;border-bottom:0}.panel:after{right:-1px;bottom:-1px;border-left:0;border-top:0}
#top{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center}
#top .brand{display:flex;flex-direction:column;gap:2px;margin-right:auto;min-width:0}
#top .brand a{font-size:11px;letter-spacing:.08em}
.stat{display:flex;flex-direction:column;min-width:0}
.stat .k{font-size:10px;letter-spacing:.18em;color:var(--dim);text-transform:uppercase}
.stat .v{font-size:13px;display:flex;align-items:center;gap:6px;white-space:nowrap}
.dot{width:9px;height:9px;border-radius:50%;background:var(--off);box-shadow:0 0 8px currentColor;color:var(--off);flex:none}
.c-ok{color:var(--ok)}.c-warn{color:var(--warn)}.c-bad{color:var(--bad)}.c-off{color:var(--off)}.c-ac{color:var(--ac)}
.dot.c-ok{background:var(--ok)}.dot.c-warn{background:var(--warn)}.dot.c-bad{background:var(--bad)}.dot.c-ac{background:var(--ac)}
#youlamp{border:1px solid var(--line);padding:6px 12px;text-align:center;min-width:74px}
#youlamp .n{font-size:24px;line-height:1;font-weight:700}
#youlamp.on{border-color:var(--warn);box-shadow:0 0 16px rgba(255,176,32,.25) inset}#youlamp.on .n{color:var(--warn)}
#youlamp.stop{border-color:var(--bad)}#youlamp.stop .n{color:var(--bad)}
#you.on{border-color:var(--warn)}
.yi{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;padding:8px 0;border-top:1px dashed var(--line)}
.yi:first-of-type{border-top:0}
.yi .t{flex:1 1 260px;min-width:0;overflow-wrap:anywhere}
.yi .a{flex:1 1 220px;color:var(--dim);min-width:0;overflow-wrap:anywhere}
.yi .a b{color:var(--tx);font-weight:500}
.yi a{white-space:nowrap}
.yi .act{font:inherit;font-size:12.5px;color:var(--bg);background:var(--ac);border:0;padding:5px 10px;cursor:pointer;min-height:32px}
.yi .act:focus-visible{outline:2px solid var(--tx);outline-offset:2px}
.yi .res{flex:1 1 100%;color:var(--dim);font-size:12.5px;overflow-wrap:anywhere}.yi .res:empty{display:none}
.tag{display:inline-block;font-size:10px;letter-spacing:.1em;padding:1px 6px;border:1px solid currentColor;border-radius:2px;text-transform:uppercase;vertical-align:1px}
.tag.read{color:var(--ok)}.tag.estimate{color:var(--warn)}.tag.unknown{color:var(--off)}
.dials{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.dial{text-align:center;min-width:0}
.dial svg{width:100%;max-width:210px;height:auto;display:block;margin:0 auto}
.dial .lab{font-size:11px;letter-spacing:.2em;color:var(--dim);text-transform:uppercase}
.dial .val{font-size:15px;margin-top:2px;overflow-wrap:anywhere}
.dial .sub{font-size:11.5px;color:var(--dim);overflow-wrap:anywhere}
.arc-bg{fill:none;stroke:#132634;stroke-width:9;stroke-linecap:butt}
.arc{fill:none;stroke:var(--ac);stroke-width:9;stroke-linecap:butt;transition:stroke-dasharray .9s cubic-bezier(.2,.8,.2,1),stroke .4s}
.ring-bg{fill:none;stroke:#0f1e29;stroke-width:3}
.ring{fill:none;stroke:var(--dim);stroke-width:3;transition:stroke-dasharray .9s linear}
.tick{stroke:var(--tx);stroke-width:2;opacity:.75}.tick.t90{stroke:var(--bad);opacity:1}.tick.t70{stroke:var(--warn);opacity:1}
.minor{stroke:#27485c;stroke-width:1}
.needle{transition:transform .9s cubic-bezier(.2,.8,.2,1);transform-origin:100px 100px}
.needle line{stroke:var(--tx);stroke-width:2}
.burn{transition:transform .9s cubic-bezier(.2,.8,.2,1),opacity .4s;transform-origin:100px 100px}
.burn path{fill:var(--warn)}
.big{font:700 30px var(--mono);fill:var(--tx);text-anchor:middle}
.unit{font:11px var(--mono);fill:var(--dim);text-anchor:middle;letter-spacing:.14em}
.unk .arc-bg{stroke-dasharray:3 5;stroke:#33454f}.unk .big{fill:var(--off);font-size:19px}.unk .needle,.unk .burn{opacity:0}
#ring{width:100%;max-width:340px;display:block;margin:0 auto}
#ring .orbit{fill:none;stroke:var(--line);stroke-dasharray:2 6}
#ring .node circle{fill:#0b1620;stroke-width:3;transition:stroke .4s}
#ring .node text{font:600 12px var(--mono);fill:var(--tx);text-anchor:middle}
#ring .node .nm{font-size:10.5px;fill:var(--dim);font-weight:400}
#ring .hand{stroke:var(--ac);stroke-width:2;stroke-dasharray:6 6;fill:none;opacity:.35}
#ring .hand.open{opacity:1;animation:flow 1.2s linear infinite}
#ring .mid{font:600 12px var(--mono);fill:var(--dim);text-anchor:middle;letter-spacing:.2em}
@keyframes flow{to{stroke-dashoffset:-24}}
@keyframes pulse{50%{opacity:.35}}
.dot.live{animation:pulse 1.6s ease-in-out infinite}
.ag{padding:9px 0;border-top:1px dashed var(--line);min-width:0}
.ag .h{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center}
.ag .n{font-weight:600}
.ag .task,.ag .why,.ag .meta{font-size:12.5px;overflow-wrap:anywhere}
.ag .why,.ag .meta{color:var(--dim)}
.lim{display:grid;grid-template-columns:118px minmax(0,1fr);gap:10px;align-items:center;padding:8px 0;border-top:1px dashed var(--line)}
.lim:first-of-type{border-top:0}
.lim svg{width:118px;height:auto;display:block}
.lim .n{font-weight:600}
.lim .l{font-size:12.5px;overflow-wrap:anywhere}
.lim .l.d{color:var(--dim)}
details{font-size:12px;color:var(--dim)}summary{cursor:pointer;color:var(--ac);list-style:none}summary::-webkit-details-marker{display:none}
.rows{display:grid;gap:4px;font-size:12.5px}
.r{display:flex;flex-wrap:wrap;gap:2px 10px;align-items:center;justify-content:space-between;min-width:0}
.r>span:first-child{min-width:0;overflow-wrap:anywhere;display:flex;gap:6px;align-items:center}
.r .d{color:var(--dim)}
.sep{height:1px;background:var(--line);margin:12px 0}
#feed .f{display:grid;grid-template-columns:58px 74px minmax(0,1fr);gap:8px;padding:3px 0;font-size:12.5px;border-top:1px solid rgba(23,49,66,.5)}
#feed .f .w{color:var(--dim)}#feed .f .x{overflow-wrap:anywhere}
.k-claim{color:var(--ac)}.k-skip{color:var(--warn)}.k-handoff{color:#c59bff}.k-key{color:var(--bad)}.k-action{color:var(--tx)}.k-done{color:var(--ok)}.k-blocked{color:var(--bad)}.k-requeue{color:var(--warn)}
.empty{color:var(--dim);font-size:12.5px}
#feedlist{max-height:330px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
#link.lost{color:var(--bad)}
@media(min-width:1000px){
 #hud{grid-template-columns:minmax(0,1fr) minmax(0,1.25fr) minmax(0,1.1fr);grid-template-areas:"top top top" "you you you" "crew core limits" "feed feed feed"}
 #top{grid-area:top}#you{grid-area:you}#core{grid-area:core}#crew{grid-area:crew}#limits{grid-area:limits}#feed{grid-area:feed}
 #feedlist{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);column-gap:28px;align-content:start}
}
@media(max-width:430px){body{font-size:13px}.dials{gap:2px}.big{font-size:32px}.dial .val{font-size:13px}.stat .v{font-size:12.5px}}
@media(prefers-reduced-motion:reduce){.arc,.ring,.needle,.burn{transition:none}#ring .hand.open,.dot.live{animation:none}}
"""

JS = r"""
(function(){
'use strict';
var LS={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
var q=new URLSearchParams(location.search),tok=q.get('t');
if(tok){LS.set('qm_t',tok);try{history.replaceState(null,'',location.pathname+location.hash)}catch(e){}}else{tok=LS.get('qm_t')||''}
var NS='http://www.w3.org/2000/svg',S=null,lastOk=0,$=function(id){return document.getElementById(id)};
function h(tag,attrs){var e=document.createElement(tag),k,i,c;for(k in (attrs||{})){if(k==='class')e.className=attrs[k];else e.setAttribute(k,attrs[k])}
  for(i=2;i<arguments.length;i++){c=arguments[i];if(c==null)continue;e.appendChild(typeof c==='object'?c:document.createTextNode(String(c)))}return e}
function s(tag,attrs){var e=document.createElementNS(NS,tag),k;for(k in (attrs||{}))e.setAttribute(k,attrs[k]);for(var i=2;i<arguments.length;i++)if(arguments[i]!=null)e.appendChild(typeof arguments[i]==='object'?arguments[i]:document.createTextNode(String(arguments[i])));return e}
function txt(e,v){v=v==null?'':String(v);if(e.textContent!==v)e.textContent=v}
function cls(e,v){if(e.getAttribute('class')!==v)e.setAttribute('class',v)}
function attr(e,k,v){if(e.getAttribute(k)!==String(v))e.setAttribute(k,v)}
function n(v,d){if(v==null)return '—';var a=Math.abs(v);return a>=1e9?(v/1e9).toFixed(2)+'B':a>=1e6?(v/1e6).toFixed(2)+'M':a>=1e4?(v/1e3).toFixed(1)+'k':(d!=null?Number(v).toFixed(d):Number(v).toLocaleString())}
function usd(v){return v==null?'—':'$'+(v<1&&v>0?Number(v).toFixed(4):Number(v).toFixed(2))}
function dur(sec){if(sec==null||isNaN(sec))return '—';sec=Math.max(0,Math.round(sec));var d=Math.floor(sec/86400),hh=Math.floor(sec%86400/3600),m=Math.floor(sec%3600/60);
  return d?d+'d '+hh+'h':hh?hh+'h'+(m<10?'0':'')+m+'m':m?m+'m':sec+'s'}
function until(iso){return iso?(new Date(iso).getTime()-Date.now())/1000:null}
function since(iso){return iso?(Date.now()-new Date(iso).getTime())/1000:null}
function hm(iso){var d=new Date(iso);return isNaN(d)?'':('0'+d.getUTCHours()).slice(-2)+':'+('0'+d.getUTCMinutes()).slice(-2)}
function tone(p){return p==null?'off':p>=90?'bad':p>=70?'warn':'ok'}
var COL={ok:'var(--ok)',warn:'var(--warn)',bad:'var(--bad)',off:'var(--off)',ac:'var(--ac)'};
var LAMP={live:['ok','LIVE'],idle:['ac','IDLE'],stale:['warn','STALE'],dormant:['bad','DORMANT'],blocked:['bad','BLOCKED'],benched:['off','BENCHED'],'key-rejected':['bad','KEY REJECTED'],'not-installed':['off','NOT INSTALLED']};

// ---- one arc gauge: a 270 degree sweep, ticks, a needle, an inner reset ring and a burn marker. Built once; set() only moves things.
var A0=135,SWEEP=270;
function pt(r,deg){var a=deg*Math.PI/180;return [100+r*Math.cos(a),100+r*Math.sin(a)]}
function arcPath(r){var a=pt(r,A0),b=pt(r,A0+SWEEP);return 'M'+a[0].toFixed(2)+' '+a[1].toFixed(2)+' A'+r+' '+r+' 0 1 1 '+b[0].toFixed(2)+' '+b[1].toFixed(2)}
function gauge(opts){
  opts=opts||{};var svg=s('svg',{viewBox:'0 0 200 178',role:'img','aria-label':opts.label||''}),i,a,b;
  svg.appendChild(s('path',{class:'arc-bg',d:arcPath(80)}));
  for(i=0;i<=10;i++){a=pt(88,A0+SWEEP*i/10);b=pt(93,A0+SWEEP*i/10);svg.appendChild(s('line',{class:'minor',x1:a[0],y1:a[1],x2:b[0],y2:b[1]}))}
  var arc=s('path',{class:'arc',d:arcPath(80),pathLength:100,'stroke-dasharray':'0 100'});svg.appendChild(arc);
  (opts.ticks||[]).forEach(function(t){a=pt(72,A0+SWEEP*t/100);b=pt(95,A0+SWEEP*t/100);svg.appendChild(s('line',{class:'tick t'+t,x1:a[0],y1:a[1],x2:b[0],y2:b[1]}))});
  var ring=null;if(opts.ring){svg.appendChild(s('path',{class:'ring-bg',d:arcPath(62)}));ring=s('path',{class:'ring',d:arcPath(62),pathLength:100,'stroke-dasharray':'0 100'});svg.appendChild(ring)}
  var needle=s('g',{class:'needle'},s('line',{x1:100+66,y1:100,x2:100+92,y2:100}));svg.appendChild(needle);
  var burn=null;if(opts.burn){burn=s('g',{class:'burn',style:'opacity:0'},s('path',{d:'M197 100 L205 95 L205 105 Z'}));svg.appendChild(burn)}
  var big=s('text',{class:'big',x:100,y:106}),unit=s('text',{class:'unit',x:100,y:126});svg.appendChild(big);svg.appendChild(unit);
  needle.style.transform='rotate('+A0+'deg)';
  return {el:svg,set:function(v){
    var p=v.pct==null?null:Math.max(0,Math.min(100,v.pct));
    cls(svg,p==null?'unk':'');attr(svg,'aria-label',v.aria||'');
    attr(arc,'stroke-dasharray',(p==null?0:p)+' 100');arc.style.stroke=COL[v.tone||tone(p)];
    needle.style.transform='rotate('+(A0+SWEEP*(p==null?0:p)/100)+'deg)';
    if(ring)attr(ring,'stroke-dasharray',(v.ring==null?0:Math.max(0,Math.min(100,v.ring)))+' 100');
    if(burn){if(v.burn==null||p==null){burn.style.opacity=0}else{burn.style.opacity=1;burn.style.transform='rotate('+(A0+SWEEP*Math.max(0,Math.min(100,v.burn))/100)+'deg)'}}
    txt(big,v.big);txt(unit,v.unit||'')}}}

// ---- a keyed list: nodes are kept, moved, added or removed; never rebuilt
function sync(box,items,key,make,update){
  var have={},i,k,node;for(i=box.children.length-1;i>=0;i--){node=box.children[i];if(node.dataset&&node.dataset.k!=null)have[node.dataset.k]=node}
  var prev=null;items.forEach(function(it){k=String(key(it));node=have[k];if(!node){node=make(it);node.dataset.k=k}delete have[k];update(node,it);
    var want=prev?prev.nextSibling:box.firstChild;if(node!==want)box.insertBefore(node,want);prev=node});
  for(k in have)box.removeChild(have[k])}
function srcTag(src){var e=h('span',{class:'tag '+(src||'unknown')},src||'unknown');return e}
function setTag(e,src){src=src||'unknown';cls(e,'tag '+src);txt(e,src)}

// ---- build once
var core={spend:gauge({ticks:[70,90],label:'Spend today'}),load:gauge({label:'Autopilot load'}),queue:gauge({label:'Queue'})};
function dialBox(g,label,id){return h('div',{class:'dial'},g.el,h('div',{class:'lab'},label),h('div',{class:'val',id:id+'v'}),h('div',{class:'sub',id:id+'s'}))}
$('dials').appendChild(dialBox(core.spend,'Spend today','sp'));$('dials').appendChild(dialBox(core.load,'Autopilot load','ld'));$('dials').appendChild(dialBox(core.queue,'Posted today','qu'));

function stat(k,id){var v=h('div',{class:'v',id:id});$('stats').appendChild(h('div',{class:'stat'},h('div',{class:'k'},k),v));return v}
var T={ap:stat('Autopilot','s-ap'),pause:stat('Pause file','s-pa'),srv:stat('Server','s-sv'),clock:stat('UTC','s-ck'),yt:stat('YouTube quota resets','s-yt'),day:stat('Spend day resets','s-dy'),link:stat('Link','s-ln')};
function lamp(e,toneName,text,live){if(!e._d){e._d=h('span',{class:'dot'});e._t=h('span',{});e.appendChild(e._d);e.appendChild(e._t)}
  cls(e._d,'dot c-'+toneName+(live?' live':''));e._d.style.color=COL[toneName];txt(e._t,text)}

function drawTop(d){
  var sy=d.system,ap=sy.autopilot;
  lamp(T.ap,ap.state==='on'?'ok':ap.state==='paused'?'bad':'off',ap.state.toUpperCase()+' · timer '+ap.timer);attr(T.ap,'title',ap.source);
  lamp(T.pause,sy.pause?'bad':'ok',sy.pause?('PAUSED: '+sy.pause).slice(0,40):'none');attr(T.pause,'title',sy.pause||sy.pauseSource);
  var sv=sy.server||{};lamp(T.srv,sv.state==='up'?'ok':'off',sv.state==='up'?'up '+dur(since(sv.startedAt)):(sv.state||'unknown'));attr(T.srv,'title',sv.reason||'this page is served by it');
  var yl=$('youlamp'),stop=d.you.some(function(y){return y.level==='stop'});cls(yl,d.youCount?(stop?'on stop':'on'):'');txt($('youn'),d.youCount);
  attr(yl,'aria-label',d.youCount+' item'+(d.youCount===1?'':'s')+' waiting for you')}
function tickClocks(){
  if(!S)return;var now=new Date();txt(T.clock,('0'+now.getUTCHours()).slice(-2)+':'+('0'+now.getUTCMinutes()).slice(-2)+':'+('0'+now.getUTCSeconds()).slice(-2));
  var r=S.system.clocks.resets;txt(T.yt,'in '+dur(until(r[0].at))+' · '+hm(r[0].at)+' UTC');attr(T.yt,'title',r[0].rule+' ('+r[0].source+')');
  txt(T.day,'in '+dur(until(r[1].at)));attr(T.day,'title',r[1].rule+' ('+r[1].source+')');
  var age=(Date.now()-lastOk)/1000,lost=age>20;
  lamp(T.link,lost?'bad':'ok',lost?'LOST · last data '+dur(since(S.generatedAt))+' ago':'live · overview '+(S.slow.ageSec==null?'warming':dur(S.slow.ageSec+age)+' old'),!lost);
  [].forEach.call(document.querySelectorAll('[data-since]'),function(e){var v=e.getAttribute('data-since');txt(e,v?(e.getAttribute('data-pre')||'')+dur(since(v))+' ago':e.getAttribute('data-none')||'')});
  [].forEach.call(document.querySelectorAll('[data-until]'),function(e){var v=e.getAttribute('data-until'),u=until(v);txt(e,v?(e.getAttribute('data-pre')||'')+(u<=0?'now':dur(u)):e.getAttribute('data-none')||'')})}

// ---- the only writes this page makes: a YOU item's own button, one allowlisted action name posted to the action desk
var SAFE={keys_probe:1,crew_reap:1,mission:1};
function press(bt){
  var d=bt._do,res=bt.parentNode.lastChild;if(!d||bt._busy||!SAFE[d.name])return;
  if(d.confirm&&!bt._armed){bt._armed=true;txt(bt,'Confirm: '+d.label);setTimeout(function(){bt._armed=false;if(!bt._busy&&bt._do)txt(bt,bt._do.label)},6000);return}
  bt._armed=false;bt._busy=true;txt(bt,'Working…');txt(res,'');
  fetch('action',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+tok},body:JSON.stringify({name:d.name,args:d.args||{}}),cache:'no-store',credentials:'omit'})
   .then(function(r){return r.json()}).then(function(j){txt(res,j.error?('Refused: '+j.error):j.state==='running'?'Started.':(j.ok?'Done: ':(j.refused?'Refused: ':'Failed: '))+(j.summary||j.refused||''))})
   .catch(function(){txt(res,'Could not reach the server.')}).then(function(){bt._busy=false;if(bt._do)txt(bt,bt._do.label);setTimeout(poll,1500)})}
function drawYou(d){
  cls($('you'),'panel'+(d.youCount?' on':''));txt($('younone'),d.youCount?'':'Nothing waits for you.');
  sync($('youlist'),d.you,function(y){return y.id},function(){
    var btn=h('button',{type:'button',class:'act'});btn.addEventListener('click',function(){press(btn)});
    var e=h('div',{class:'yi'},h('span',{class:'dot'}),h('div',{class:'t'}),h('div',{class:'a'},'Do: ',h('b',{})),h('a',{}),btn,h('span',{class:'res',role:'status'}));return e},
  function(e,y){var c=y.level==='stop'?'bad':y.level==='info'?'ac':'warn';cls(e.children[0],'dot c-'+c);e.children[0].style.color=COL[c];txt(e.children[1],y.text);txt(e.children[2].lastChild,y.action);attr(e,'title','source: '+y.source);
    var bt=e.children[4];bt._do=y.do||null;bt.style.display=y.do?'':'none';if(y.do&&!bt._busy&&!bt._armed)txt(bt,y.do.label);
    var a=e.children[3];if(y.href){attr(a,'href',y.href);txt(a,'Open the desk →');a.style.display=''}else{a.removeAttribute('href');txt(a,'');a.style.display='none'}})}

function drawCore(d){
  var sp=d.core.spend,ld=d.core.load,qu=d.core.queue;
  core.spend.set({pct:sp.pct,big:sp.pct==null?'unknown':Math.round(sp.pct)+'%',unit:'OF CEILING',aria:'Spend today: '+usd(sp.usd)+' of '+usd(sp.ceilingUsd)+' ceiling, '+sp.pct+' percent ('+sp.source+')'});
  txt($('spv'),usd(sp.usd)+' of '+usd(sp.ceilingUsd));
  txt($('sps'),'counted from the ledger (estimate) · '+(sp.burnPerHour==null?'burn unknown':'burn '+usd(sp.burnPerHour)+'/h'+(sp.projectedEmptyAt?' · ceiling in '+dur(until(sp.projectedEmptyAt)):'')));
  attr($('sps'),'title',sp.burnReason||sp.from);
  var lp=ld.running==null?null:100*ld.running/Math.max(1,ld.maxParallel);
  core.load.set({pct:lp,tone:lp==null?'off':lp>=100?'warn':'ac',big:ld.running==null?'unknown':ld.running+'/'+ld.maxParallel,unit:'IN MOTION',aria:'Autopilot load: '+(ld.running==null?'unknown, '+ld.reason:ld.running+' of '+ld.maxParallel+' missions in motion')});
  txt($('ldv'),ld.running==null?'unknown':ld.running+' running, max '+ld.maxParallel);
  txt($('lds'),ld.running==null?ld.reason:(ld.missions.map(function(m){return m.title+' ('+(m.agent||'?')+')'}).join(' · ')||'nothing in motion'));
  var qp=qu.posted==null||!qu.target?null:100*qu.posted/qu.target;
  core.queue.set({pct:qp,tone:qp==null?'off':qp>=100?'ok':'ac',big:qu.posted==null?'unknown':qu.posted+'/'+qu.target,unit:'POSTED',aria:'Queue: '+(qu.posted==null?'unknown, '+qu.reason:qu.posted+' posted of a target of '+qu.target+', '+qu.ready+' ready, '+qu.held+' held')});
  txt($('quv'),qu.posted==null?'unknown':'ready '+qu.ready+' · held '+qu.held+' · posted '+qu.posted);
  txt($('qus'),qu.posted==null?qu.reason:'target '+qu.target+' a day · '+qu.made+' started today');attr($('qus'),'title',qu.from);
  txt($('engnone'),d.engine.length?'':'No engine lane has reported today.');
  sync($('eng'),d.engine,function(e){return e.agent},function(){return h('div',{class:'r'},h('span',{},h('span',{class:'dot'}),h('span',{})),h('span',{class:'d'}))},
  function(e,x){var c=x.status==='running'||x.status==='refreshing'?'ok':x.status==='stale'?'warn':x.status==='error'||x.status==='blocked'?'bad':'off';
    cls(e.firstChild.firstChild,'dot c-'+c);e.firstChild.firstChild.style.color=COL[c];txt(e.firstChild.lastChild,x.agent+' · '+x.status+(x.task?' · '+x.task:'').slice(0,96));attr(e,'title',x.task||'');
    attr(e.lastChild,'data-since',x.lastBeatAt||'');attr(e.lastChild,'data-none','')});
  txt($('heldnone'),d.held.length?'':'');
  sync($('held'),d.held,function(x){return x.mission},function(){return h('div',{class:'r'},h('span',{}),h('span',{class:'d'}))},
  function(e,x){txt(e.firstChild,'HELD '+x.title);txt(e.lastChild,'because '+x.reason)})}

// ---- crew ring
var ringNodes={},ringLines=$('ringlines'),ringG=$('ringnodes');
function pos(i,total){var a=(-90+360*i/Math.max(1,total))*Math.PI/180;return [170+112*Math.cos(a),150+112*Math.sin(a)]}
function drawCrew(d){
  var total=d.crew.length,P={};
  d.crew.forEach(function(a,i){P[a.id]=pos(i,total)});
  sync(ringG,d.crew,function(a){return a.id},function(a){
    return s('g',{class:'node',role:'img'},s('circle',{r:24}),s('text',{y:4}),s('text',{class:'nm',y:42}))},
  function(g,a){var p=P[a.id],L=LAMP[a.lamp]||['off',a.lamp];attr(g,'transform','translate('+p[0].toFixed(1)+','+p[1].toFixed(1)+')');
    g.firstChild.style.stroke=COL[L[0]];txt(g.children[1],a.name.split(/\s+/).map(function(w){return w[0]}).join('').slice(0,2).toUpperCase());txt(g.children[2],a.name);
    attr(g,'aria-label',a.name+': '+L[1].toLowerCase()+'. '+a.lampReason)});
  var hs=d.handoffs.filter(function(x){return x.from&&x.to&&P[x.from]&&P[x.to]});
  sync(ringLines,hs,function(x){return x.mission},function(){return s('path',{class:'hand'})},
  function(e,x){var a=P[x.from],b=P[x.to];attr(e,'d','M'+a[0].toFixed(1)+' '+a[1].toFixed(1)+' Q170 150 '+b[0].toFixed(1)+' '+b[1].toFixed(1));cls(e,'hand'+(x.open?' open':''))});
  var live=d.crew.filter(function(a){return a.lamp==='live'}).length;txt($('ringmid'),live+' LIVE');txt($('ringmid2'),total+' ON THE CREW');
  attr($('ring'),'aria-label','Crew ring: '+d.crew.map(function(a){return a.name+' '+a.lamp}).join(', ')+'. '+hs.length+' handoff'+(hs.length===1?'':'s')+' drawn.');
  sync($('crewlist'),d.crew,function(a){return a.id},function(){
    return h('div',{class:'ag'},h('div',{class:'h'},h('span',{class:'dot'}),h('span',{class:'n'}),h('span',{class:'lampw'}),h('span',{class:'tag'}),h('span',{class:'d meta'})),
      h('div',{class:'task'}),h('div',{class:'why'}),h('div',{class:'meta'}))},
  function(e,a){var L=LAMP[a.lamp]||['off',a.lamp],hd=e.firstChild;
    cls(hd.children[0],'dot c-'+L[0]+(a.lamp==='live'?' live':''));hd.children[0].style.color=COL[L[0]];txt(hd.children[1],a.name);
    cls(hd.children[2],'lampw c-'+L[0]);txt(hd.children[2],L[1]);cls(hd.children[3],'tag c-ac');txt(hd.children[3],'plan: '+a.plan);attr(hd.children[3],'title',a.planDetail?a.planDetail.text+' ('+a.planDetail.from+')':'crew.toml');
    attr(hd.children[4],'data-since',a.lastBeatAt||'');attr(hd.children[4],'data-pre','last beat ');attr(hd.children[4],'data-none',a.installed?'no beat yet':'');
    txt(e.children[1],a.task?'▸ '+a.task:(a.claims&&a.claims.length?'▸ holds '+a.claims.map(function(c){return c.mission}).join(', '):''));
    txt(e.children[2],a.lamp==='idle'||a.lamp==='live'?'':a.lampReason);attr(e,'title',a.lampReason);
    txt(e.children[3],a.tokensIn==null?'no gauges until it is installed':'today: '+(a.requests==null?'':n(a.requests)+' replies · ')+'in '+n(a.tokensIn)+' · out '+n(a.tokensOut)+' tokens · '+usd(a.usd)+' ('+a.usageSource+')'+(a.model?' · '+a.model:'')+(a.key?' · key '+a.key.state:'')+(a.planDetail?' · account: '+a.planDetail.text+' (read)':''));
    attr(e.children[3],'title',a.usageFrom||'')});
  var hl=d.handoffs.slice().reverse();txt($('handnone'),hl.length?'':'No handoffs in the last 48 hours.');
  sync($('hands'),hl,function(x){return x.mission},function(){return h('div',{class:'r'},h('span',{}),h('span',{class:'d'}))},
  function(e,x){var nm=function(id){var a=d.crew.filter(function(c){return c.id===id})[0];return a?a.name:(id||'someone')};
    txt(e.firstChild,nm(x.from)+' → '+(x.to?nm(x.to):'nobody')+' ['+x.tag+'] '+x.note);txt(e.lastChild,x.open?'open':'closed')})}

// ---- limits
var LG={};
function drawLimits(d){
  var rows=[];d.crew.forEach(function(a){(a.limits||[]).forEach(function(L){rows.push({k:a.id+':'+L.id,a:a,L:L})})});
  sync($('limlist'),rows,function(r){return r.k},function(r){
    var g=gauge({ticks:[70,90],ring:true,burn:true});LG[r.k]=g;
    return h('div',{class:'lim'},g.el,h('div',{},h('div',{},h('span',{class:'n'}),' ',h('span',{class:'tag'})),h('div',{class:'l'}),h('div',{class:'l d'}),h('div',{class:'l d'}),
      h('details',{},h('summary',{},'why?'),h('div',{}))))},
  function(e,r){var a=r.a,L=r.L,g=LG[r.k],b=e.lastChild,known=L.limit!=null&&L.pct!=null,pc=L.unit==='percent',u=L.unit==='usd'?usd:pc?function(v){return v==null?'—':v+'%'}:n;
    var ringPct=null;if(L.resetAt&&L.windowHours){ringPct=100*(1-Math.max(0,until(L.resetAt))/(L.windowHours*3600))}
    var resetTxt=L.resetAt?'resets in '+dur(until(L.resetAt)):'reset unknown',emptyTxt=L.projectedEmptyAt?'empty in '+dur(until(L.projectedEmptyAt)):null;
    var usedTxt=L.used==null?'use unknown':u(L.used)+' '+(L.unit==='usd'||pc?'':L.unit+' ')+'used '+L.usedScope;
    g.set({pct:known?L.pct:null,big:known?Math.round(L.pct)+'%':'unknown',unit:known?'OF LIMIT':'LIMIT',ring:ringPct,burn:L.projectedPctAtReset,
      aria:a.name+' '+L.label+': '+(known?L.pct+' percent used, '+u(L.used)+' of '+u(L.limit)+' '+L.unit+', '+resetTxt+(emptyTxt?', '+emptyTxt:'')+' ('+L.source+')':'unknown. '+(L.reason||'')+' '+usedTxt+' ('+L.usedSource+')')});
    txt(b.children[0].firstChild,a.name+' · '+L.label);setTag(b.children[0].lastChild,L.source);
    txt(b.children[1],known?(pc?u(L.used)+' used, as the provider reports it':u(L.used)+' of '+u(L.limit)+' '+L.unit):usedTxt+' ('+L.usedSource+')');
    txt(b.children[2],L.burnPerHour==null?'burn unknown':'burn '+u(L.burnPerHour)+'/h (estimate)'+(emptyTxt?' · '+emptyTxt:'')+(L.readAt?' · read '+dur(since(L.readAt))+' ago':''));
    txt(b.children[3],(known||L.resetAt)?resetTxt+(L.resetAt?' ('+L.resetSource+')':''):'window '+L.window+' · '+resetTxt);
    var why=[L.reason,L.usedReason,L.resetReason,L.error,'used: '+L.usedFrom].filter(Boolean).join(' ');txt(b.children[4].lastChild,why);attr(e,'title',why)});
  sync($('keys'),d.keys,function(k){return k.id},function(){return h('div',{class:'r'},h('span',{},h('span',{class:'dot'}),h('span',{})),h('span',{class:'d'}))},
  function(e,k){var c=k.state==='ok'?'ok':k.state==='present'?'ac':k.state==='unknown'?'warn':'bad';cls(e.firstChild.firstChild,'dot c-'+c);e.firstChild.firstChild.style.color=COL[c];
    txt(e.firstChild.lastChild,k.label);txt(e.lastChild,k.state+(k.checkedAt?' · checked '+hm(k.checkedAt)+' UTC':''));attr(e,'title',k.var+': '+k.detail)});
  var m=d.ledger.models.map(function(x){return {k:'m:'+x.model,name:x.model,plan:x.plan,a:x.calls+' calls · in '+n(x.tokensIn)+' · out '+n(x.tokensOut)+' · '+usd(x.usd)}})
    .concat(d.ledger.providers.map(function(x){var un=Object.keys(x.units||{}).map(function(k){return n(x.units[k])+' '+k}).join(', ');return {k:'p:'+x.provider,name:x.provider,plan:x.plan,a:x.calls+' calls'+(un?' · '+un:'')+' · '+usd(x.usd)}}));
  txt($('lednone'),m.length?'':'No provider call in today’s ledger yet.');
  sync($('ledger'),m,function(x){return x.k},function(){return h('div',{class:'r'},h('span',{},h('span',{}),h('span',{class:'tag c-ac'})),h('span',{class:'d'}))},
  function(e,x){txt(e.firstChild.firstChild,x.name);txt(e.firstChild.lastChild,x.plan);cls(e.firstChild.lastChild,'tag '+(x.plan==='unknown'?'unknown':'c-ac'));txt(e.lastChild,x.a)})}

function drawFeed(d){
  txt($('feednone'),d.feed.length?'':'Nothing has happened between the crew yet today.');
  sync($('feedlist'),d.feed,function(f){return f.id},function(){return h('div',{class:'f'},h('span',{class:'w'}),h('span',{}),h('span',{class:'x'}))},
  function(e,f){txt(e.children[0],hm(f.t));cls(e.children[1],'k-'+f.kind);txt(e.children[1],f.kind);txt(e.children[2],f.text+(f.count>1?'  (×'+f.count+' since '+hm(f.firstT)+')':''))})}

function draw(d){S=d;drawTop(d);drawYou(d);drawCore(d);drawCrew(d);drawLimits(d);drawFeed(d);tickClocks()}
function poll(){
  fetch('instruments.json',{headers:tok?{Authorization:'Bearer '+tok}:{},cache:'no-store',credentials:'omit'}).then(function(r){
    if(r.status===401){txt($('gate'),'This page needs its token: open the link with ?t=… once (the QR code carries it).');throw new Error('401')}
    if(!r.ok)throw new Error(r.status);return r.json()}).then(function(d){lastOk=Date.now();txt($('gate'),'');LS.set('qm_instr',JSON.stringify(d));draw(d)}).catch(function(){tickClocks()})}
try{var c=JSON.parse(LS.get('qm_instr')||'null');if(c&&c.crew)draw(c)}catch(e){}
poll();setInterval(function(){if(!document.hidden)poll()},5000);setInterval(tickClocks,1000);
document.addEventListener('visibilitychange',function(){if(!document.hidden)poll()});
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(function(){})}
})();
"""

BODY = """<div id="hud">
<section class="panel" id="top" aria-label="System state">
 <div class="brand"><h1>QUIET MONEY // COMMAND CENTER</h1><a href="desk">Action desk (the buttons) →</a><span id="gate" class="c-bad" role="status"></span></div>
 <div id="stats" style="display:contents"></div>
 <div id="youlamp" role="status"><div class="n" id="youn">—</div><div class="k" style="font-size:10px;letter-spacing:.2em;color:var(--dim)">YOU</div></div>
</section>
<section class="panel" id="you" aria-label="Waiting for you"><h2>You · what waits for a person</h2><div id="youlist"></div><div class="empty" id="younone"></div></section>
<section class="panel" id="core" aria-label="Core dials"><h2>Core</h2><div class="dials" id="dials"></div>
 <div class="sep"></div><h2>Engine lanes today</h2><div class="rows" id="eng"></div><div class="empty" id="engnone"></div>
 <div class="rows" id="held" style="margin-top:10px"></div><div class="empty" id="heldnone"></div></section>
<section class="panel" id="crew" aria-label="The crew"><h2>The crew</h2>
 <svg id="ring" viewBox="0 0 340 320" role="img" aria-label="Crew ring"><circle class="orbit" cx="170" cy="150" r="112"></circle><g id="ringlines"></g><g id="ringnodes"></g>
 <text class="mid" id="ringmid" x="170" y="148"></text><text class="mid" id="ringmid2" x="170" y="166" style="font-size:9px"></text></svg>
 <div id="crewlist"></div><div class="sep"></div><h2>Handoffs</h2><div class="rows" id="hands"></div><div class="empty" id="handnone"></div></section>
<section class="panel" id="limits" aria-label="Limits"><h2>Limits</h2><div class="empty" style="margin:-4px 0 8px">Ticks at 70% and 90%. Inner ring: time to reset. Amber marker: where the current burn lands by the reset.</div><div id="limlist"></div>
 <div class="sep"></div><h2>Keys</h2><div class="rows" id="keys"></div>
 <div class="sep"></div><h2>Models and providers today <span class="tag estimate">estimate</span></h2><div class="rows" id="ledger"></div><div class="empty" id="lednone"></div></section>
<section class="panel" id="feed" aria-label="Event feed"><h2>Feed · claims, skips, handoffs, key failures, actions</h2><div id="feedlist"></div><div class="empty" id="feednone"></div></section>
</div>"""


def render() -> str:
    """The page. It carries no data: the first poll fills it, so nothing can be shown that the server did not just report."""
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            "<meta name=\"robots\" content=\"noindex,nofollow,noarchive\"><meta name=\"referrer\" content=\"no-referrer\">"
            f"<meta name=\"theme-color\" content=\"{BG}\"><meta name=\"mobile-web-app-capable\" content=\"yes\">"
            "<link rel=\"manifest\" href=\"manifest.webmanifest\"><link rel=\"icon\" href=\"icon-192.png\"><link rel=\"apple-touch-icon\" href=\"icon-192.png\">"
            f"<title>Quiet Money Command Center</title><style>{CSS}</style></head><body>{BODY}<script>{JS}</script></body></html>\n")
