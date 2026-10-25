"""Static assets for the phone edition: the page script, service worker, web
manifest and app icons. site_builder.py writes them into the published site.

Built on the patterns proven in the HLSA app and TrendScout's phone edition:
network-first pages with a throwaway query param (GitHub Pages' CDN ignores
cache-bypass headers), version.json polling for a "newer scan" banner, and
cache names prefixed with the app's name because every app on
daneathery-cloud.github.io shares one cache store and one localStorage."""
import json
import os
import shutil

import config

# Runs after the shared page script (render.JS) and replaces the parts that talked
# to the desktop server.
STATIC_JS = r"""
const WL_KEY='hlsascout.watchlist.v1', ERR_KEY='hlsascout.errors.v1';
function _lsGet(k,d){try{const v=localStorage.getItem(k);return v===null?d:JSON.parse(v)}catch(e){return d}}
function _lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v));return true}catch(e){return false}}
function logError(m){const l=_lsGet(ERR_KEY,[]);l.push(new Date().toISOString()+' '+String(m).slice(0,300));_lsSet(ERR_KEY,l.slice(-30));}
window.addEventListener('error',e=>logError('error: '+e.message+' @'+String(e.filename||'').split('/').pop()+':'+e.lineno));
window.addEventListener('unhandledrejection',e=>logError('promise: '+((e.reason&&e.reason.message)||e.reason)));

/* ---------- watchlist, saved on this device ---------- */
const wlKey=(t,i)=>t+':'+i, wlLoad=()=>_lsGet(WL_KEY,{}), wlSave=m=>_lsSet(WL_KEY,m);
const STATUSES=['New','Researching','Contacted','Meeting set','Pursuing','Won','Not a fit'];
function applyChecks(){const m=wlLoad();document.querySelectorAll('.track input').forEach(cb=>{cb.checked=!!m[wlKey(cb.dataset.type,cb.dataset.id)]});}
function toggleWatch(el,removeOnUncheck){
  const type=el.dataset.type,id=el.dataset.id,key=wlKey(type,id),m=wlLoad();
  let snap={}; try{snap=JSON.parse(el.dataset.snapshot)}catch(e){}
  if(el.checked){ m[key]=Object.assign({status:'New',notes:''},m[key]||{},{type,id,label:el.dataset.label||id,snapshot:snap,
      added:(m[key]&&m[key].added)||new Date().toISOString(),asof:SCAN_LABEL}); }
  else delete m[key];
  if(!wlSave(m)){el.checked=!el.checked;alert('Could not save on this device (storage full or blocked).');return;}
  toast(el,el.checked?'Saved to Watchlist':'Removed');
  if(removeOnUncheck&&!el.checked){const c=el.closest('.card,tr');if(c){c.style.opacity='0';setTimeout(renderWatchlist,250)}}
}
function saveLead(el){
  const card=el.closest('.card'),key=wlKey(card.dataset.type,card.dataset.id),m=wlLoad();
  if(!m[key])return;
  m[key].status=card.querySelector('select.status').value; m[key].notes=card.querySelector('textarea').value;
  m[key].updated=new Date().toISOString(); card.dataset.status=m[key].status;
  if(wlSave(m)){const s=card.querySelector('.saved');s.textContent='Saved';clearTimeout(s._t);s._t=setTimeout(()=>s.textContent='',1200);
    if(el.tagName==='SELECT')renderChips(wlItems());}
}
function renderChips(items){
  const chips=document.getElementById('wl-chips');if(!chips)return;
  const cur=F.status||'all';
  chips.innerHTML='<span class="lbl">Status</span><button class="chip'+(cur==='all'?' active':'')+'" onclick="setChip(\'status\',\'all\',this)">All ('+items.length+')</button>'+
    STATUSES.map(s=>'<button class="chip'+(cur===s?' active':'')+'" onclick="setChip(\'status\',\''+s+'\',this)">'+s+' ('+items.filter(i=>i.status===s).length+')</button>').join('');
}
const P=window.PARTNERS||{};
function fitsHtml(ps){if(!ps||!ps.length)return '';return '<div class="fits">Could help: '+ps.filter(p=>P[p]).map(p=>
  '<span class="fit'+(p.startsWith('nt_')?' nt':'')+'" title="'+esc(P[p][1])+'">'+esc(P[p][0])+'</span>').join('')+'</div>';}
function fmtDate(ts){try{return new Date(ts*1000).toLocaleDateString(undefined,{month:'short',day:'numeric'})}catch(e){return ''}}
function partnerNames(ps){return (ps||[]).filter(p=>P[p]).map(p=>P[p][0]).join(', ');}
function shareText(it){const s=it.snapshot||{};
  if(it.type==='org') return 'Newly registered '+(s.taxonomy||'healthcare organization')+' in '+s.city+', TX (NPI issued '+s.enumerated+'). '+
     [s.address&&(s.address+', '+s.city+' '+s.zip+'.'),s.phone&&('Phone '+s.phone+'.'),s.official&&('Registered by '+s.official+(s.official_title?', '+s.official_title:'')+(s.official_phone?' ('+s.official_phone+')':'')+'.')].filter(Boolean).join(' ')+
     ' Could be an opportunity for: '+partnerNames(s.partners)+'. (Spotted with HLSA Scout)';
  return (s.source||'')+' - '+fmtDate(s.ts)+'. '+(s.partners&&s.partners.length?'Could be an opportunity for: '+partnerNames(s.partners)+'. ':'')+'(Spotted with HLSA Scout)';}
function itemLink(it){const s=it.snapshot||{};return it.type==='org'?s.registry_link:s.link;}
function itemTitle(it){const s=it.snapshot||{};return it.type==='org'?s.name:s.title;}
function cardHtml(it){
  const s=it.snapshot||{}, opts=STATUSES.map(x=>'<option'+(x===it.status?' selected':'')+'>'+x+'</option>').join('');
  let top,detail;
  if(it.type==='org'){top='<span class="src">New organization · NPI Registry</span><span class="badge place">📍 '+esc(s.city)+'</span>';
    detail=(s.dba?'dba '+esc(s.dba)+' · ':'')+esc(s.taxonomy)+' · NPI issued '+esc(s.enumerated)+' · '+esc(s.address)+', '+esc(s.city)+' '+esc(s.zip)+
      (s.phone?' · '+esc(s.phone):'')+(s.official?' · Registered by '+esc(s.official)+(s.official_title?', '+esc(s.official_title):'')+(s.official_phone?' '+esc(s.official_phone):''):'');}
  else{top='<span class="src">'+esc(s.source)+'</span><span class="date">· '+fmtDate(s.ts)+'</span>'+(s.place?'<span class="badge place">📍 '+esc(s.place)+'</span>':'')+
      (s.paywalled?'<span class="badge pay">Subscription site</span>':'');
    detail=esc(s.summary||'');}
  const free=(it.type!=='org'&&s.paywalled)?'<button type="button" class="icon-btn free" data-title="'+esc(s.title)+'" onclick="findFree(this)">🔓 Free versions</button>':'';
  return '<div class="card" data-filter="1" data-type="'+esc(it.type)+'" data-id="'+esc(it.id)+'" data-status="'+esc(it.status)+'">'+
    '<div class="item-actions">'+free+'<button type="button" class="icon-btn" data-title="'+esc(itemTitle(it))+'" data-text="'+esc(shareText(it))+'" data-link="'+esc(itemLink(it))+'" onclick="shareItem(this)">📤</button>'+
    '<label class="track"><input type="checkbox" checked data-type="'+esc(it.type)+'" data-id="'+esc(it.id)+'" data-label="'+esc(it.label)+'" data-snapshot="'+esc(JSON.stringify(s))+'" onchange="toggleWatch(this,true)"><span class="mark"></span></label></div>'+
    '<div class="topline">'+top+'</div><a class="headline" href="'+esc(itemLink(it))+'" target="_blank" rel="noopener">'+esc(itemTitle(it))+'</a>'+
    (detail?'<div class="summary">'+detail+'</div>':'')+fitsHtml(s.partners)+
    '<div class="meta">Saved '+esc((it.added||'').slice(0,10))+' (from the scan of '+esc(it.asof||'')+')</div>'+
    '<div class="lead"><select class="status" onchange="saveLead(this)">'+opts+'</select>'+
    '<textarea placeholder="Notes - who is following up, contacts, next step..." oninput="saveLead(this)">'+esc(it.notes||'')+'</textarea><span class="saved"></span></div></div>';
}
function wlItems(){return Object.values(wlLoad()).sort((a,b)=>(b.added||'').localeCompare(a.added||''));}
function renderWatchlist(){
  const root=document.getElementById('wl-root'); if(!root)return;
  const items=wlItems(), bar=document.getElementById('wl-bar');
  if(!items.length){root.innerHTML='<div class="empty">Your watchlist on this device is empty.<br><br>Tick the small box in the bottom-right corner of any story or organization to save it here, then track it as a lead with a status and notes.</div>';if(bar)bar.style.display='none';return;}
  if(bar)bar.style.display='';
  renderChips(items);
  root.innerHTML=items.map(cardHtml).join('');
  applyFilters();
}

/* ---------- exports: Excel (CSV) and a report page, via the share sheet when possible ---------- */
function csvCell(v){v=v==null?'':String(v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v;}
function exportCsv(){
  const rows=[['Kind','Title / Organization','Status','Notes','Town','Source / Type','Date','Address','Phone','Registered by',"Official's title","Official's phone",'Could help','Link','Saved']];
  wlItems().forEach(it=>{const s=it.snapshot||{};
    if(it.type==='org') rows.push(['New organization',s.name,it.status,it.notes,s.city,s.taxonomy,s.enumerated,(s.address||'')+' '+(s.zip||''),s.phone,s.official,s.official_title,s.official_phone,partnerNames(s.partners),s.registry_link,it.added]);
    else rows.push(['Story',s.title,it.status,it.notes,s.place,s.source,s.ts?new Date(s.ts*1000).toISOString().slice(0,10):'','','','','','',partnerNames(s.partners),s.link,it.added]);});
  saveFile('﻿'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n'),'HLSA_Scout_Watchlist_'+new Date().toISOString().slice(0,10)+'.csv','text/csv');
}
function exportReport(){
  const items=wlItems(), now=new Date().toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'});
  const rows=items.map(it=>{const s=it.snapshot||{};
    const detail=it.type==='org'?'New organization (NPI issued '+s.enumerated+') · '+s.taxonomy+' · '+s.address+', '+s.city+' '+s.zip+' '+(s.phone||''):(s.source||'')+' · '+fmtDate(s.ts)+' · '+(s.place||'');
    return '<div style="border:1px solid #E2DFD8;border-left:4px solid #1E3864;border-radius:8px;padding:10px 14px;margin:10px 0;background:#fff">'+
      '<div style="font-size:11px;color:#5F6878">'+esc(detail)+'</div><a href="'+esc(itemLink(it))+'" style="font-weight:700;color:#1C2230;font-size:15px;text-decoration:none">'+esc(itemTitle(it))+'</a>'+
      '<div style="font-size:12px;color:#5F6878;margin-top:4px">Could help: '+esc(partnerNames(s.partners))+'</div>'+
      '<div style="font-size:12px;margin-top:4px"><b>Status:</b> '+esc(it.status)+(it.notes?' · <b>Notes:</b> '+esc(it.notes):'')+'</div></div>';}).join('');
  const html='<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>HLSA Scout Watchlist</title></head>'+
    '<body style="font-family:Segoe UI,Arial,sans-serif;background:#F6F5F2;margin:0;padding:16px;color:#1C2230"><div style="max-width:860px;margin:0 auto">'+
    '<div style="background:#1E3864;border-bottom:4px solid #CD2027;padding:14px 18px;border-radius:10px 10px 0 0;color:#fff"><div style="font-size:20px;font-weight:700">HLSA Scout - Watchlist</div>'+
    '<div style="font-size:12px;color:#C9D3E6">'+items.length+' opportunities · '+esc(now)+'</div></div>'+rows+
    '<p style="font-size:11px;color:#5F6878;margin-top:20px">'+esc((document.querySelector('.disclaimer')||{}).textContent||'')+'</p></div></body></html>';
  saveFile(html,'HLSA_Scout_Watchlist_'+new Date().toISOString().slice(0,10)+'.html','text/html');
}
async function saveFile(text,filename,type){
  const blob=new Blob([text],{type:type});
  try{const f=new File([blob],filename,{type:type});
    if(navigator.canShare&&navigator.canShare({files:[f]})){await navigator.share({files:[f],title:'HLSA Scout Watchlist'});return;}}
  catch(e){if(e&&e.name==='AbortError')return;}
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},1500);
}

/* ---------- free versions: looked up when the scan was built ---------- */
let _free=null;
async function findFree(el){
  const card=el.closest('.card,tr');let pop=card.querySelector('.free-pop');if(pop){pop.remove();return;}
  pop=document.createElement('div');pop.className='free-pop';pop.innerHTML='<h4>Looking...</h4>';
  (card.tagName==='TR'?card.querySelector('td'):card).appendChild(pop);
  if(_free===null){try{const r=await fetch('free.json?v='+encodeURIComponent(BUILD_ID));_free=r.ok?await r.json():{}}catch(e){_free={}}}
  const t=el.dataset.title, d=_free[t]||{matches:[],keywords:'',search_url:'https://news.google.com/search?q='+encodeURIComponent(t)+'&hl=en-US&gl=US&ceid=US:en'};
  let h=d.matches&&d.matches.length?'<h4>Coverage from outlets without a hard paywall</h4><ul>'+d.matches.map(m=>'<li><a href="'+esc(m.link)+'" target="_blank" rel="noopener">'+esc(m.title)+'</a> <span class="muted">- '+esc(m.source)+'</span></li>').join('')+'</ul>'
    :'<h4>No free coverage found automatically.</h4>';
  h+='<div class="muted">Matches are by keywords - check it is the same story. <a href="'+esc(d.search_url)+'" target="_blank" rel="noopener">Search Google News yourself</a></div>';
  pop.innerHTML=h;
}

/* ---------- freshness ---------- */
async function checkVersion(){
  try{const r=await fetch('version.json',{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();
    window.__lastVersionCheck=new Date().toISOString()+' - site build '+d.build;
    if(d.build&&d.build!==BUILD_ID)document.getElementById('update-banner').classList.add('show');}
  catch(e){window.__lastVersionCheck=new Date().toISOString()+' - could not check ('+e.message+')';}
}
function checkStale(){
  const h=(Date.now()/1000-SCAN_EPOCH)/3600,b=document.getElementById('stale-banner');if(!b)return;
  if(h>36){b.textContent='This scan is '+(h>=48?Math.floor(h/24)+' days':Math.round(h)+' hours')+' old (scanned '+SCAN_LABEL+'). The automatic refresh may have failed - see Diagnostics.';b.classList.add('show');}
  else b.classList.remove('show');
}
if('serviceWorker' in navigator){
  navigator.serviceWorker.register('sw.js',{updateViaCache:'none'}).then(reg=>{
    document.addEventListener('visibilitychange',()=>{if(!document.hidden){reg.update().catch(()=>{});checkVersion();checkStale();}});
    window.addEventListener('pageshow',e=>{if(e.persisted){reg.update().catch(()=>{});checkVersion();checkStale();}});
  }).catch(e=>logError('service worker: '+e.message));
}

/* ---------- Diagnostics ---------- */
async function renderDiagnostics(){
  const el=document.getElementById('diag');if(!el)return;
  await checkVersion();
  const errs=_lsGet(ERR_KEY,[]);let sw='not supported';
  if('serviceWorker' in navigator){try{const r=await navigator.serviceWorker.getRegistrations();sw=r.length?'registered; controlling: '+!!navigator.serviceWorker.controller:'not registered'}catch(e){sw='error: '+e.message}}
  let persisted='unknown';try{persisted=String(await navigator.storage.persisted())}catch(e){}
  el.textContent=['=== HLSA Scout phone diagnostics ===','Generated:        '+new Date().toString(),'App version:      '+APP_VERSION,
    'Site build:       '+BUILD_ID,'Scan:             '+SCAN_LABEL+'  ('+((Date.now()/1000-SCAN_EPOCH)/3600).toFixed(1)+' hours ago)',
    'Page:             '+location.href,'Online:           '+navigator.onLine,
    'Installed app:    '+(matchMedia('(display-mode: standalone)').matches||navigator.standalone===true),
    'Service worker:   '+sw,'Version check:    '+(window.__lastVersionCheck||'n/a'),
    'Watchlist items on this device: '+Object.keys(wlLoad()).length+'  (kept permanently: '+persisted+')',
    'Browser:          '+navigator.userAgent,'Screen:           '+screen.width+'x'+screen.height+', viewport '+innerWidth+'x'+innerHeight,
    '','--- Recent errors ('+errs.length+') ---'].concat(errs.length?errs:['(none)']).concat(['=== end ===']).join('\n');
}

if(navigator.storage&&navigator.storage.persist){navigator.storage.persist().catch(()=>{});}
applyChecks(); renderWatchlist(); renderDiagnostics(); checkStale(); checkVersion();
"""


def partners_js() -> str:
    return "window.PARTNERS=" + json.dumps({k: list(v) for k, v in config.PARTNERS.items()}) + ";"


def sw_js(build_id: str) -> str:
    return f"""const CACHE = "hlsascout-{build_id}";
function bust(url) {{ return url + (url.indexOf("?") === -1 ? "?" : "&") + "_sw=" + Date.now(); }}
const SHELL = ["./", "./index.html", "./wire.html", "./orgs.html", "./watchlist.html", "./about.html",
  "./diagnostics.html", "./manifest.webmanifest", "./free.json", "./logo.png",
  "./icons/icon-192.png", "./icons/icon-512.png", "./icons/apple-touch-icon.png", "./icons/favicon-32.png"];
self.addEventListener("install", (e) => {{
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
}});
self.addEventListener("activate", (e) => {{
  // This github.io address is shared with other apps (HLSA, TrendScout): only clear our own old caches.
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("hlsascout-") && k !== CACHE)
    .map((k) => caches.delete(k)))).then(() => self.clients.claim()));
}});
self.addEventListener("fetch", (e) => {{
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.endsWith("version.json")) {{ e.respondWith(fetch(bust(req.url), {{ cache: "no-store" }})); return; }}
  const fresh = req.mode === "navigate" || /\\.(html|json|webmanifest)$/.test(url.pathname);
  if (fresh) {{
    const key = req.url.split("#")[0].split("?")[0];
    e.respondWith(fetch(bust(req.url), {{ cache: "no-store" }}).then((r) => {{
        if (r.ok) {{ const copy = r.clone(); caches.open(CACHE).then((c) => c.put(key, copy)); }}
        return r;
      }}).catch(() => caches.match(key).then((hit) => hit || caches.match("./index.html"))));
    return;
  }}
  e.respondWith(caches.match(req).then((cached) => {{
    const net = fetch(req).then((r) => {{ if (r.ok) {{ const copy = r.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }} return r; }})
      .catch(() => cached);
    return cached || net;
  }}));
}});
"""


def manifest_json() -> str:
    return json.dumps({
        "name": "HLSA Scout", "short_name": "HLSA Scout",
        "description": "Local healthcare business opportunities for HLSA's referral partners and NT Partnership.",
        "start_url": "./index.html", "scope": "./", "display": "standalone", "orientation": "any",
        "background_color": config.NAVY, "theme_color": config.NAVY,
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icons/maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, indent=2)


def copy_static_files(out_dir: str) -> None:
    """Logo and the app icons (drawn once by make_icons.py and kept in assets/icons)."""
    shutil.copy(config.LOGO_PATH, os.path.join(out_dir, "logo.png"))
    shutil.copytree(config.resource_path(os.path.join("assets", "icons")), os.path.join(out_dir, "icons"))
