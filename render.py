"""Renders HLSA Scout's pages: Scan Report, Opportunity Wire, New Organizations,
Watchlist, About and the downloadable watchlist report. Served live by
app_server.py so the watchlist checkboxes / status / notes save instantly.

The same functions also build the phone edition (site_builder.py): with
STATIC["on"] the pages use relative links, carry the phone-app tags, and
site_assets.STATIC_JS replaces everything that talked to the desktop server."""
import base64
import datetime as dt
import html as html_lib
import json

import config
import geo
import store

CAT = {c["key"]: c for c in config.CATEGORIES}

STATIC = {"on": False, "version_label": "", "scan_label": "", "scan_epoch": 0, "build_id": "", "repo_url": ""}

_STATIC_PATHS = {"/": "index.html", "/wire": "wire.html", "/orgs": "orgs.html", "/watchlist": "watchlist.html",
                 "/about": "about.html", "/diagnostics": "diagnostics.html", "/logo.png": "logo.png"}


def configure_static(**kw):
    STATIC.update(on=True, **kw)


def _u(path: str) -> str:
    """A link that works both on the desktop server and in the static phone site."""
    if not STATIC["on"]:
        return path
    base, _, query = path.partition("?")
    return _STATIC_PATHS.get(base, base.lstrip("/")) + (f"?{query}" if query else "")


def _new_label() -> tuple:
    """(badge tooltip, filter label) for organizations that are new."""
    if STATIC["on"]:
        return "First appeared in the last 7 days", "Only new this week"
    return "First appeared since your previous scan", "Only new since my last scan"

CSS = """
:root{
  --bg:#F6F5F2; --panel:#fff; --navy:%(navy)s; --navy-dark:%(navy_dark)s; --red:%(red)s; --border:#E2DFD8;
  --text:#1C2230; --muted:#5F6878; --soft:#EEF1F7; --green:#1F9D55; --amber:#B7791F;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;margin:0;padding:0 0 60px}
a{color:var(--navy)}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px 28px}
header.top{background:var(--navy);display:flex;align-items:center;gap:18px;padding:14px 22px;border-bottom:4px solid var(--red)}
header.top img.logo{height:50px;background:#fff;border-radius:8px;padding:5px 10px}
header.top h1{margin:0;font-size:22px;color:#fff;letter-spacing:.2px}
header.top .sub{color:#C9D3E6;font-size:12.5px;margin-top:3px}
header.top .ver{margin-left:auto;color:#AFBBD3;font-size:11px;text-align:right;align-self:flex-start;line-height:1.6}
header.top .ver a{color:#AFBBD3}
nav.tabs{display:flex;gap:2px;padding:0 20px;background:var(--panel);border-bottom:1px solid var(--border);flex-wrap:wrap}
nav.tabs a{color:var(--muted);text-decoration:none;font-size:13.5px;font-weight:600;padding:13px 15px;border-bottom:3px solid transparent}
nav.tabs a.active{color:var(--navy);border-bottom-color:var(--red)}
nav.tabs a:hover{color:var(--navy)}
.disclaimer{background:#FFF8EA;border:1px solid #EFDDB4;color:#6E5417;border-radius:8px;padding:11px 15px;font-size:12px;margin:18px 0;line-height:1.5}
.summary-bar{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 6px}
.stat{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:10px 14px;min-width:130px}
.stat b{display:block;font-size:22px;color:var(--navy)} .stat span{font-size:11.5px;color:var(--muted)}
h2.section{font-size:19px;margin:34px 0 2px;padding-bottom:8px;border-bottom:2px solid var(--border);display:flex;align-items:center;gap:10px}
h2.section .count{margin-left:auto;font-size:11px;font-weight:600;color:var(--muted);background:var(--panel);border:1px solid var(--border);padding:3px 10px;border-radius:20px}
h2.section .count a{text-decoration:none}
p.section-sub{color:var(--muted);font-size:13px;margin:6px 0 14px;max-width:920px;line-height:1.45}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(370px,1fr));gap:10px}
.list{display:flex;flex-direction:column;gap:10px}
.card{background:var(--panel);border:1px solid var(--border);border-left:4px solid var(--navy);border-radius:9px;
      padding:11px 14px 30px;position:relative}
.card .topline{display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:11px}
.card .src{color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.card .date{color:var(--muted)}
.card a.headline{display:block;margin-top:5px;color:var(--text);text-decoration:none;font-weight:650;font-size:14.5px;line-height:1.35}
.card a.headline:hover{color:var(--red)}
.card .summary{color:var(--muted);font-size:12.5px;margin-top:4px;line-height:1.4}
.card .also{font-size:11px;color:var(--muted);margin-top:6px}
.card .also a{color:var(--muted)}
.badge{font-size:10.5px;padding:2px 8px;border-radius:20px;font-weight:650;white-space:nowrap;background:var(--soft);color:var(--navy)}
.badge.place{background:#E8F2EC;color:#1D6B41}
.badge.big{background:#F1ECF8;color:#6A4A9A}
.badge.new{background:var(--red);color:#fff}
.badge.pay{background:#FDF0E1;color:#9A5B12}
.fits{margin-top:7px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;font-size:10.5px;color:var(--muted)}
.fit{border:1px solid var(--border);border-radius:20px;padding:1px 7px;color:var(--navy);background:#fff;font-weight:600}
.fit.nt{border-color:var(--red);color:var(--red)}
.item-actions{position:absolute;bottom:7px;right:10px;display:flex;align-items:center;gap:9px}
.track{cursor:pointer;position:relative}
.track input{position:absolute;opacity:0;width:20px;height:20px;margin:0;cursor:pointer}
.track .mark{display:block;width:17px;height:17px;border:1.5px solid #C9CED8;border-radius:4px;background:var(--bg)}
.track input:checked + .mark{background:var(--red);border-color:var(--red)}
.track input:checked + .mark::after{content:"\\2713";display:block;text-align:center;line-height:16px;font-size:11px;color:#fff;font-weight:700}
.icon-btn{background:none;border:none;cursor:pointer;font-size:14px;line-height:1;padding:1px;opacity:.7}
.icon-btn:hover{opacity:1}
.icon-btn.free{font-size:11px;font-weight:700;color:#9A5B12;opacity:.95;border:1px solid #EBCB9C;border-radius:12px;padding:2px 8px;background:#FFF8EE}
.toast{position:absolute;bottom:24px;right:0;background:var(--navy-dark);color:#fff;font-size:10.5px;padding:3px 8px;border-radius:5px;white-space:nowrap;pointer-events:none}
.free-pop{margin-top:9px;border:1px solid #EBCB9C;background:#FFFBF4;border-radius:8px;padding:9px 11px;font-size:12px}
.free-pop h4{margin:0 0 5px;font-size:12px;color:#9A5B12}
.free-pop ul{margin:0;padding-left:18px} .free-pop li{margin:3px 0}
.free-pop .muted{color:var(--muted);font-size:11px;margin-top:6px}
.filters{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:14px 0}
.filters .lbl{font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-right:2px}
.chip{background:var(--panel);border:1px solid var(--border);color:var(--muted);font-size:11.5px;padding:5px 11px;border-radius:20px;cursor:pointer}
.chip.active{background:var(--navy);color:#fff;border-color:var(--navy);font-weight:600}
.filters input[type=search],.filters select{border:1px solid var(--border);border-radius:20px;padding:6px 12px;font-size:12.5px;background:#fff}
.filters label.tog{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:5px;margin-left:6px}
table.orgs{width:100%%;border-collapse:collapse;background:var(--panel);border:1px solid var(--border);border-radius:10px;overflow:hidden;font-size:12.5px}
table.orgs th{text-align:left;color:var(--muted);font-size:11px;font-weight:700;padding:8px 10px;background:var(--soft);border-bottom:1px solid var(--border);white-space:nowrap}
table.orgs td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top}
table.orgs td.act{position:relative;width:62px} table.orgs td.act .item-actions{position:static;justify-content:flex-end}
table.orgs .nm{font-weight:650} table.orgs .muted{color:var(--muted);font-size:11.5px}
table.orgs .fits{margin-top:3px}
.empty{color:var(--muted);font-size:14px;padding:40px 20px;text-align:center;border:1px dashed var(--border);border-radius:10px;background:var(--panel)}
.page-actions{display:flex;gap:8px;justify-content:flex-end;margin:16px 0 -4px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;background:var(--navy);color:#fff;text-decoration:none;font-size:12.5px;font-weight:600;padding:8px 15px;border-radius:20px;border:none;cursor:pointer}
.btn.red{background:var(--red)} .btn:hover{filter:brightness(1.12)}
.lead{display:flex;gap:10px;align-items:flex-start;margin-top:9px;padding-top:9px;border-top:1px dashed var(--border)}
.lead select{border:1px solid var(--border);border-radius:6px;padding:4px 6px;font-size:12px;background:#fff}
.lead textarea{flex:1;min-height:38px;border:1px solid var(--border);border-radius:6px;padding:5px 8px;font:12px inherit;resize:vertical}
.lead .saved{font-size:10.5px;color:var(--green);min-width:40px}
.meta{color:var(--muted);font-size:11px;margin-top:5px}
footer.foot{color:var(--muted);font-size:11.5px;text-align:center;margin-top:40px}
.note{background:var(--soft);border-radius:8px;padding:10px 14px;font-size:12.5px;color:var(--muted);line-height:1.5;margin:10px 0}
.banner{display:none;margin:14px 0 0;padding:9px 13px;border-radius:8px;font-size:12.5px}
.banner.show{display:block} .banner.warn{background:#FFF4E5;color:#8A4B0F;border:1px solid #F0CFA0}
.banner.info{background:#EAF1FB;color:var(--navy);border:1px solid #C4D4EE}
.banner button{margin-left:8px;border:none;background:var(--navy);color:#fff;border-radius:14px;padding:3px 10px;cursor:pointer}
@media (max-width:700px){
  .wrap{padding:0 12px 24px} .grid{grid-template-columns:1fr} header.top{flex-wrap:wrap;gap:10px;padding:12px 14px}
  header.top h1{font-size:19px} header.top h1 span{display:block;font-size:13px} header.top img.logo{height:38px}
  header.top .sub{display:none} header.top .ver{margin-left:0;text-align:left;width:100%%}
  nav.tabs{padding:0 6px;overflow-x:auto;flex-wrap:nowrap} nav.tabs a{padding:11px 9px;font-size:12.5px;white-space:nowrap}
  .stat{min-width:0;flex:1 1 42%%}
  /* organization table becomes one card per row */
  table.orgs, table.orgs tbody{display:block;border:none;background:none}
  table.orgs thead{display:none}
  table.orgs tr{display:block;position:relative;background:var(--panel);border:1px solid var(--border);border-left:4px solid var(--navy);
    border-radius:9px;margin-bottom:10px;padding:9px 12px 32px}
  table.orgs td{display:block;border:none;padding:2px 0}
  table.orgs td.act{position:absolute;bottom:6px;right:8px;width:auto}
  .filters{flex-wrap:nowrap;overflow-x:auto;padding-bottom:4px} .filters input[type=search]{min-width:170px}
  .filters .chip,.filters label.tog,.filters select{white-space:nowrap;flex-shrink:0}
  .lead{flex-direction:column} .lead textarea{width:100%%}
}
""" % {"navy": config.NAVY, "navy_dark": config.NAVY_DARK, "red": config.RED}

JS = r"""
function toggleWatch(el, removeOnUncheck){
  let snapshot={}; try{snapshot=JSON.parse(el.dataset.snapshot)}catch(e){}
  const action=el.checked?'add':'remove', prev=el.checked;
  fetch('/api/watchlist/toggle',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({action,type:el.dataset.type,id:el.dataset.id,label:el.dataset.label,snapshot})})
  .then(r=>{if(!r.ok)throw 0; toast(el, prev?'Saved to Watchlist':'Removed');
    if(removeOnUncheck&&!prev){const c=el.closest('.card,tr'); if(c){c.style.opacity='0';setTimeout(()=>c.remove(),250)}}})
  .catch(()=>{el.checked=!prev; alert('Could not update the watchlist. Is HLSA Scout still running?')});
}
function toast(el,msg){const box=el.closest('.item-actions')||el.parentElement; const old=box.querySelector('.toast'); if(old)old.remove();
  const t=document.createElement('span'); t.className='toast'; t.textContent=msg; box.appendChild(t); setTimeout(()=>t.remove(),1500);}
function shareItem(el){
  const title=el.dataset.title||'', text=el.dataset.text||'', link=el.dataset.link||'';
  if(navigator.share){navigator.share({title, text:text||title, url:link||undefined}).catch(()=>{});return;}
  const payload=[title,text,link].filter(Boolean).join('\n');
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(payload).then(()=>toast(el,'Copied - paste into an email or text')).catch(()=>toast(el,"Couldn't copy"));}
  else toast(el,"Couldn't copy");
}
function findFree(el){
  const card=el.closest('.card,tr'); let pop=card.querySelector('.free-pop');
  if(pop){pop.remove();return;}
  pop=document.createElement('div'); pop.className='free-pop'; pop.innerHTML='<h4>Looking for free coverage of this story...</h4>';
  (card.tagName==='TR'?card.querySelector('td'):card).appendChild(pop);
  fetch('/api/free_versions?title='+encodeURIComponent(el.dataset.title)).then(r=>r.json()).then(d=>{
    let h='';
    if(d.matches&&d.matches.length){h='<h4>Coverage from outlets without a hard paywall</h4><ul>'+
      d.matches.map(m=>'<li><a href="'+esc(m.link)+'" target="_blank" rel="noopener">'+esc(m.title)+'</a> <span class="muted">- '+esc(m.source)+'</span></li>').join('')+'</ul>';}
    else h='<h4>No free coverage found automatically.</h4>';
    h+='<div class="muted">Matches are by keywords ('+esc(d.keywords||'')+') - check it is the same story. '+
       '<a href="'+esc(d.search_url)+'" target="_blank" rel="noopener">Search Google News yourself (paywalled sites excluded)</a></div>';
    pop.innerHTML=h;
  }).catch(()=>{pop.innerHTML='<h4>Search failed - is HLSA Scout still running?</h4>'});
}
function esc(s){return String(s||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
// ---- filters (Wire / Organizations / Watchlist)
const F={};
function setChip(group,val,btn){F[group]=val; btn.parentElement.querySelectorAll('.chip').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); applyFilters();}
function applyFilters(){
  const q=(document.getElementById('q')||{}).value||''; const ql=q.toLowerCase();
  const hideBig=(document.getElementById('hideBig')||{}).checked; const onlyNew=(document.getElementById('onlyNew')||{}).checked;
  const partner=(document.getElementById('partner')||{}).value||'';
  let shown=0;
  document.querySelectorAll('[data-filter]').forEach(el=>{
    const d=el.dataset; let ok=true;
    for(const g of ['cat','region','group','status']){ if(F[g]&&F[g]!=='all'){
      if(g==='group'&&F[g]==='noequip'){ if(d.group==='Equipment, pharmacy & labs') ok=false; }
      else if(!(' '+(d[g]||'')+' ').includes(' '+F[g]+' ')) ok=false; } }
    if(hideBig&&d.big==='1') ok=false;
    if(onlyNew&&d.isnew!=='1') ok=false;
    if(partner&&!(' '+(d.partners||'')+' ').includes(' '+partner+' ')) ok=false;
    if(ql&&!el.textContent.toLowerCase().includes(ql)) ok=false;
    el.style.display=ok?'':'none'; if(ok)shown++;
  });
  const c=document.getElementById('shownCount'); if(c)c.textContent=shown;
}
// ---- watchlist lead tracking
let saveTimers={};
function saveLead(el){
  const card=el.closest('.card'); const key=card.dataset.type+'|'+card.dataset.id;
  clearTimeout(saveTimers[key]);
  saveTimers[key]=setTimeout(()=>{
    const status=card.querySelector('select.status').value, notes=card.querySelector('textarea').value;
    card.dataset.status=status;
    fetch('/api/watchlist/update',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({type:card.dataset.type,id:card.dataset.id,status,notes})})
    .then(r=>{if(!r.ok)throw 0; const s=card.querySelector('.saved'); s.textContent='Saved'; setTimeout(()=>s.textContent='',1500)})
    .catch(()=>alert('Could not save. Is HLSA Scout still running?'));
  }, el.tagName==='SELECT'?0:600);
}
"""


def _esc(s) -> str:
    return html_lib.escape(str(s)) if s is not None else ""


def _date(ts) -> str:
    try:
        return dt.datetime.fromtimestamp(float(ts)).strftime("%b %d").replace(" 0", " ")
    except (TypeError, ValueError):
        return ""


def _fits_html(partners: list, label: str = "Could help:") -> str:
    if not partners:
        return ""
    chips = "".join(
        f'<span class="fit{" nt" if p.startswith("nt_") else ""}" title="{_esc(config.PARTNERS[p][1])}">'
        f'{_esc(config.PARTNERS[p][0])}</span>' for p in partners if p in config.PARTNERS)
    return f'<div class="fits">{_esc(label)} {chips}</div>'


def _checkbox(item_type, item_id, label, snapshot, checked, remove_on_uncheck=False) -> str:
    return (f'<label class="track" title="Save to Watchlist"><input type="checkbox" {"checked" if checked else ""} '
            f'data-type="{_esc(item_type)}" data-id="{_esc(item_id)}" data-label="{_esc(label)}" '
            f'data-snapshot="{_esc(json.dumps(snapshot))}" '
            f'onchange="toggleWatch(this,{"true" if remove_on_uncheck else "false"})"><span class="mark"></span></label>')


def _share_btn(title, text, link) -> str:
    return (f'<button type="button" class="icon-btn" title="Share (email, text, Teams...) or copy" '
            f'data-title="{_esc(title)}" data-text="{_esc(text)}" data-link="{_esc(link)}" '
            f'onclick="shareItem(this)">\U0001F4E4</button>')


def _free_btn(title) -> str:
    return (f'<button type="button" class="icon-btn free" title="Behind a paywall? Look for the same story at free outlets" '
            f'data-title="{_esc(title)}" onclick="findFree(this)">\U0001F513 Free versions</button>')


def _partner_names(partners) -> str:
    return ", ".join(config.PARTNERS[p][0] for p in partners if p in config.PARTNERS)


# ---------------------------------------------------------------- stories
def story_snapshot(s: dict) -> dict:
    return {k: s.get(k) for k in ("id", "title", "summary", "link", "source", "ts", "place", "region",
                                  "category", "categories", "partners", "big_system", "paywalled", "also")}


def story_card(s: dict, watchlisted: set, remove_on_uncheck=False, show_cat=True, extra="", attrs=None) -> str:
    cat = CAT.get(s.get("category"), config.CATEGORIES[0])
    checked = ("story", s["id"]) in watchlisted
    region_short = geo.REGIONS.get(s.get("region"), ("", ""))[1]
    where = s.get("place") or region_short
    share_text = (f"{s['source']} - {_date(s.get('ts'))}. "
                  + (f"Could be an opportunity for: {_partner_names(s.get('partners', []))}. " if s.get("partners") else "")
                  + "(Spotted with HLSA Scout)")
    badges = [f'<span class="src">{_esc(s["source"])}</span>', f'<span class="date">· {_date(s.get("ts"))}</span>']
    if where:
        badges.append(f'<span class="badge place">\U0001F4CD {_esc(where)}</span>')
    if show_cat:
        badges.append(f'<span class="badge" style="color:{cat["color"]}">{cat["icon"]} {_esc(cat["label"])}</span>')
    if s.get("big_system"):
        badges.append('<span class="badge big" title="Large health system / national chain">Big system</span>')
    if s.get("paywalled"):
        badges.append('<span class="badge pay" title="Subscription outlet: only its public headline is shown">Subscription site</span>')
    also = ""
    if s.get("also"):
        links = ", ".join(f'<a href="{_esc(a["link"])}" target="_blank" rel="noopener">{_esc(a["source"])}</a>'
                          for a in s["also"][:4])
        also = f'<div class="also">Also covered by: {links}</div>'
    free = _free_btn(s["title"]) if s.get("paywalled") else ""
    actions = (f'<div class="item-actions">{free}{_share_btn(s["title"], share_text, s["link"])}'
               f'{_checkbox("story", s["id"], s["title"], story_snapshot(s), checked, remove_on_uncheck)}</div>')
    filt = (f'data-filter="1" data-cat="{_esc(" ".join(s.get("categories") or [s.get("category", "")]))}" '
            f'data-region="{_esc(s.get("region", ""))}" data-big="{1 if s.get("big_system") else 0}" '
            f'data-partners="{_esc(" ".join(s.get("partners", [])))}"')
    return f"""<div class="card" style="border-left-color:{cat['color']}" {attrs or filt}>
      {actions}
      <div class="topline">{''.join(badges)}</div>
      <a class="headline" href="{_esc(s['link'])}" target="_blank" rel="noopener">{_esc(s['title'])}</a>
      {f'<div class="summary">{_esc(s["summary"])}</div>' if s.get('summary') else ''}
      {_fits_html(s.get('partners', []))}{also}{extra}
    </div>"""


# ---------------------------------------------------------------- organizations
def org_snapshot(o: dict) -> dict:
    return {k: o.get(k) for k in ("npi", "npis", "count", "name", "dba", "enumerated", "taxonomy", "group", "city",
                                  "county", "region", "address", "zip", "phone", "fax", "official", "official_title", "official_phone",
                                  "big_system", "partners", "registry_link")}


def _org_share_text(o: dict) -> str:
    bits = [f"Newly registered {o['taxonomy'] or 'healthcare organization'} in {o['city']}, TX "
            f"(NPI issued {o['enumerated']})."]
    if o.get("address"):
        bits.append(f"{o['address']}, {o['city']} {o['zip']}.")
    if o.get("phone"):
        bits.append(f"Phone {o['phone']}.")
    if o.get("official"):
        bits.append(f"Registered by {o['official']}{', ' + o['official_title'] if o.get('official_title') else ''}"
                    f"{' (' + o['official_phone'] + ')' if o.get('official_phone') else ''}.")
    bits.append(f"Could be an opportunity for: {_partner_names(o.get('partners', []))}. (Spotted with HLSA Scout)")
    return " ".join(bits)


def org_row(o: dict, watchlisted: set, remove_on_uncheck=False) -> str:
    checked = ("org", o["npi"]) in watchlisted
    badges = ""
    if o.get("new_since_last"):
        badges += f' <span class="badge new" title="{_new_label()[0]}">NEW</span>'
    if o.get("big_system"):
        badges += ' <span class="badge big">Big system / public</span>'
    if o.get("count", 1) > 1:
        badges += f' <span class="badge" title="This organization registered several NPIs">×{o["count"]}</span>'
    official = (f"{_esc(o['official'])}<div class='muted'>{_esc(o.get('official_title', ''))}</div>"
                f"<div class='muted'>{_esc(o.get('official_phone', ''))}</div>") if o.get("official") else ""
    actions = (f'<div class="item-actions">{_share_btn(o["name"], _org_share_text(o), o["registry_link"])}'
               f'{_checkbox("org", o["npi"], o["name"], org_snapshot(o), checked, remove_on_uncheck)}</div>')
    filt = (f'data-filter="1" data-group="{_esc(o["group"])}" data-region="{_esc(o["region"])}" '
            f'data-big="{1 if o.get("big_system") else 0}" data-isnew="{1 if o.get("new_since_last") else 0}" '
            f'data-partners="{_esc(" ".join(o.get("partners", [])))}"')
    return f"""<tr {filt}>
      <td><a class="nm" href="{_esc(o['registry_link'])}" target="_blank" rel="noopener" title="Open the official NPI Registry record">{_esc(o['name'])}</a>{badges}
        {f"<div class='muted'>dba {_esc(o['dba'])}</div>" if o.get('dba') else ''}
        <div class="muted">{_esc(o['taxonomy'])}</div>{_fits_html(o.get('partners', []), '')}</td>
      <td>{_esc(o['city'])}<div class="muted">{_esc(o['county'])} County</div></td>
      <td>{_esc(o.get('address', ''))}<div class="muted">{_esc(o.get('phone', ''))}{(' · fax ' + _esc(o['fax'])) if o.get('fax') else ''}</div></td>
      <td>{official}</td>
      <td style="white-space:nowrap">{_esc(o['enumerated'])}</td>
      <td class="act">{actions}</td>
    </tr>"""


def org_table(orgs: list, watchlisted: set, remove_on_uncheck=False) -> str:
    rows = "".join(org_row(o, watchlisted, remove_on_uncheck) for o in orgs)
    return f"""<table class="orgs"><thead><tr><th>Organization &amp; type</th><th>Town</th><th>Practice address / phone</th>
      <th>Registered by (authorized official)</th><th>NPI issued</th><th></th></tr></thead><tbody>{rows}</tbody></table>"""


# ---------------------------------------------------------------- page shell
def _shell(active: str, body: str, title: str = "") -> str:
    tabs = [("scan", "/", "\U0001F4CA Scan Report"), ("wire", "/wire", "\U0001F4F0 Opportunity Wire"),
            ("orgs", "/orgs", "\U0001F195 New Organizations"), ("watch", "/watchlist", "⭐ Watchlist"),
            ("about", "/about", "ℹ️ About")]
    if not STATIC["on"]:    # NT Partnership's plan stays off the public phone edition
        tabs.insert(4, ("market", "/market", "\U0001F4C8 Market & Plan"))
    nav ="".join(f'<a href="{_u(p)}" class="{"active" if k == active else ""}">{l}</a>' for k, p, l in tabs)
    st = STATIC
    if st["on"]:
        import site_assets
        head_extra = f"""<meta name="theme-color" content="{config.NAVY}">
<meta name="robots" content="noindex, nofollow">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="HLSA Scout">"""
        ver = (f'Version {config.APP_VERSION} · phone edition<br>Scanned {_esc(st["scan_label"])}<br>'
               f'<a href="{_u("/diagnostics")}">Diagnostics</a> · <a href="#" onclick="location.reload();return false">⟳ Refresh</a>')
        banners = ('<div id="stale-banner" class="banner warn"></div>'
                   '<div id="update-banner" class="banner info">A newer scan is available. '
                   '<button type="button" onclick="location.reload()">Load it</button></div>')
        scripts = (f'<script>const BUILD_ID={json.dumps(st["build_id"])}, SCAN_EPOCH={st["scan_epoch"]}, '
                   f'SCAN_LABEL={json.dumps(st["scan_label"])}, APP_VERSION={json.dumps(config.APP_VERSION)};</script>'
                   f'<script>{site_assets.partners_js()}</script>'
                   f'<script>{JS}</script><script>{site_assets.STATIC_JS}</script>')
    else:
        head_extra, banners = "", ""
        phone = (f' · <a href="{_esc(config.PHONE_URL)}" target="_blank" rel="noopener" '
                 f'title="Open the phone edition (works on any phone or tablet)">\U0001F4F1 Phone version</a>'
                 if config.PHONE_URL else "")
        ver = f'Version {config.APP_VERSION} · {config.APP_VERSION_DATE}<br><a href="/diagnostics">Diagnostics</a>{phone}'
        scripts = f"<script>{JS}</script>"
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">{head_extra}
<title>{config.APP_NAME}{(' - ' + title) if title else ''}</title><style>{CSS}</style></head><body>
<header class="top"><img class="logo" src="{_u('/logo.png')}" alt="Healthcare Leaders of San Antonio">
  <div><h1>{config.APP_NAME} <span style="font-weight:400;opacity:.8">— {config.APP_SUBTITLE}</span></h1>
  <div class="sub">Business opportunities for HLSA's Trusted Referral Partners &amp; NT Partnership · San Antonio, Bexar-adjacent counties, I-35 Corridor &amp; rural ring</div></div>
  <div class="ver">{ver}</div>
</header><nav class="tabs">{nav}</nav>
<div class="wrap">{banners}{body}
<footer class="foot">{config.APP_NAME} v{config.APP_VERSION} · Healthcare Leaders of San Antonio · healthcareleaderssa.com</footer></div>
{scripts}</body></html>"""


def empty_scan_page() -> str:
    return _shell("scan", f"""<div class="disclaimer">{_esc(config.DISCLAIMER)}</div>
      <div class="empty">No scan yet. Click <b>Scan Now</b> in the HLSA Scout window (about a minute).<br><br>
      New here? Start with the <a href="{_u('/about')}">About</a> tab.</div>""")


def _region_counts(stories, orgs) -> str:
    cells = []
    for key, (label, short) in geo.REGIONS.items():
        n_s = sum(1 for s in stories if s.get("region") == key)
        n_o = sum(1 for o in orgs if o.get("region") == key)
        cells.append(f'<div class="stat"><b>{n_s} · {n_o}</b><span>{_esc(label)}<br>stories · new orgs</span></div>')
    return "".join(cells)


def scan_page(data: dict, watchlisted: set) -> str:
    stories, orgs = data["stories"], data["orgs"]
    gen = data["generated_at"].strftime("%A, %B %d, %Y at %I:%M %p").replace(" 0", " ")
    new_orgs = [o for o in orgs if o.get("new_since_last")]
    top = [s for s in stories if not s.get("big_system")][:config.TOP_COUNT]
    if len(top) < config.TOP_COUNT:
        top += [s for s in stories if s.get("big_system")][:config.TOP_COUNT - len(top)]
    body = [f"""<div class="disclaimer">{_esc(config.DISCLAIMER)}</div>
      <div class="meta">Scanned {gen} · {data['news_stats']['searches']} local news searches + {len(config.NEWS_FEEDS)} feeds
       + NPI Registry ({data['npi_stats']['searches']} searches) · {data['seconds']} s</div>
      <div class="summary-bar">
        <div class="stat"><b>{len(stories)}</b><span>opportunity stories<br>(last {config.MAX_NEWS_AGE_DAYS} days)</span></div>
        <div class="stat"><b>{len(orgs)}</b><span>new healthcare orgs<br>(last {config.NPI_WINDOW_DAYS} days)</span></div>
        <div class="stat"><b>{len(new_orgs)}</b><span>{'new orgs<br>this week' if STATIC['on'] else 'orgs new since<br>your last scan'}</span></div>
        {_region_counts(stories, orgs)}
      </div>"""]
    body.append(f"""<h2 class="section">⭐ Top Opportunities<span class="count"><a href="{_u('/wire')}">all {len(stories)} stories →</a></span></h2>
      <p class="section-sub">The freshest, clearest opportunities across every category - boutique and small-town items rank ahead of
      the big systems (those are still in their sections and on the Wire).</p>
      <div class="grid">{''.join(story_card(s, watchlisted) for s in top) or '<div class="empty">No stories this scan.</div>'}</div>""")

    show_orgs = [o for o in orgs if not o.get("big_system") and o["group"] != "Equipment, pharmacy & labs"][:15]
    body.append(f"""<h2 class="section">\U0001F195 Newly Registered Healthcare Organizations
        <span class="count"><a href="{_u('/orgs')}">all {len(orgs)} →</a></span></h2>
      <p class="section-sub">Every new clinic, practice or agency must get a federal NPI number - usually weeks before it opens and
      often without any news coverage. These are the newest in the territory (NPI Registry, free public data). The Registry record
      lists the practice address, phone and the person who registered it.</p>
      {org_table(show_orgs, watchlisted) if show_orgs else '<div class="empty">NPI Registry data unavailable this scan.</div>'}""")

    for cat in config.CATEGORIES:
        items = [s for s in stories if cat["key"] in (s.get("categories") or [])][:config.SECTION_COUNT]
        total = sum(1 for s in stories if cat["key"] in (s.get("categories") or []))
        cards = "".join(story_card(s, watchlisted, show_cat=False) for s in items)
        body.append(f"""<h2 class="section" style="border-bottom-color:{cat['color']}33">{cat['icon']} {_esc(cat['label'])}
            <span class="count"><a href="{_u('/wire?cat=' + cat['key'])}">{total} on the Wire →</a></span></h2>
          <p class="section-sub">{_esc(cat['sub'])}</p>
          <div class="grid">{cards or '<div class="empty">Nothing new in this category this scan.</div>'}</div>""")
    return _shell("scan", "".join(body))


def wire_page(data: dict | None, watchlisted: set, cat: str = "all") -> str:
    if not data:
        return empty_scan_page().replace('class="active">\U0001F4CA', 'class="">\U0001F4CA')
    stories = data["stories"]
    cat_chips = ['<button class="chip%s" onclick="setChip(\'cat\',\'all\',this)">All</button>' % (" active" if cat == "all" else "")]
    for c in config.CATEGORIES:
        n = sum(1 for s in stories if c["key"] in (s.get("categories") or []))
        cat_chips.append(f'<button class="chip{" active" if cat == c["key"] else ""}" data-chip="{c["key"]}" '
                         f'onclick="setChip(\'cat\',\'{c["key"]}\',this)">{c["icon"]} {_esc(c["label"])} ({n})</button>')
    region_chips = ['<button class="chip active" onclick="setChip(\'region\',\'all\',this)">All areas</button>'] + [
        f'<button class="chip" onclick="setChip(\'region\',\'{k}\',this)">{_esc(v[1])}</button>' for k, v in geo.REGIONS.items()]
    partner_opts = '<option value="">Any partner</option>' + "".join(
        f'<option value="{k}">{_esc(v[0])}</option>' for k, v in config.PARTNERS.items())
    body = f"""<div class="disclaimer">{_esc(config.DISCLAIMER)}</div>
      <div class="filters"><span class="lbl">Category</span>{''.join(cat_chips)}</div>
      <div class="filters"><span class="lbl">Area</span>{''.join(region_chips)}
        <select id="partner" onchange="applyFilters()" title="Show stories that could matter to this partner">{partner_opts}</select>
        <input type="search" id="q" placeholder="Search (town, practice, word...)" oninput="applyFilters()">
        <label class="tog"><input type="checkbox" id="hideBig" onchange="applyFilters()"> Hide big systems</label></div>
      <p class="meta">Showing <b id="shownCount">{len(stories)}</b> of {len(stories)} stories, best opportunities first.</p>
      <div class="list">{''.join(story_card(s, watchlisted) for s in stories) or '<div class="empty">No stories.</div>'}</div>
      <script>document.addEventListener('DOMContentLoaded',()=>{{
        // ?cat=... picks a category (the phone edition has no server to do it)
        const want=new URLSearchParams(location.search).get('cat')||{json.dumps(cat)};
        const chip=document.querySelector('.chip[data-chip="'+want+'"]');
        if(chip) setChip('cat',want,chip); else {{F.cat='all'; applyFilters();}}
      }});</script>"""
    return _shell("wire", body, "Opportunity Wire")


def orgs_page(data: dict | None, watchlisted: set) -> str:
    if not data:
        return empty_scan_page()
    orgs, st = data["orgs"], data["npi_stats"]
    groups = [g for g in __import__("scanners.npi", fromlist=["GROUP_ORDER"]).GROUP_ORDER
              if any(o["group"] == g for o in orgs)]
    chips = ['<button class="chip active" onclick="setChip(\'group\',\'noequip\',this)" '
             'title="Everything except equipment suppliers, pharmacies and labs">Practices &amp; agencies</button>',
             '<button class="chip" onclick="setChip(\'group\',\'all\',this)">Everything</button>']
    chips += [f'<button class="chip" onclick="setChip(\'group\',{_esc(json.dumps(g))},this)">{_esc(g)} '
              f'({sum(1 for o in orgs if o["group"] == g)})</button>' for g in groups]
    region_chips = ['<button class="chip active" onclick="setChip(\'region\',\'all\',this)">All areas</button>'] + [
        f'<button class="chip" onclick="setChip(\'region\',\'{k}\',this)">{_esc(v[1])}</button>' for k, v in geo.REGIONS.items()]
    partner_opts = '<option value="">Any partner</option>' + "".join(
        f'<option value="{k}">{_esc(v[0])}</option>' for k, v in config.PARTNERS.items())
    fetched = st.get("fetched_at", "")[:16].replace("T", " ")
    body = f"""<p class="section-sub" style="margin-top:20px">Healthcare organizations that received a federal NPI number in the last
      {st['window_days']} days with a practice address in the territory - the earliest public sign of a new practice, clinic or agency.
      Source: the free <a href="https://npiregistry.cms.hhs.gov/" target="_blank" rel="noopener">CMS NPI Registry</a>
      (checked {fetched}). Click a name for the official record.</p>
      <div class="note">Worth knowing: an NPI is issued when an organization <i>applies</i> - some are new businesses, some are existing
      practices registering a new location or a new legal entity, and a few never open. A brand-new LLC with a person's name and a
      residential address is usually a solo practitioner starting out. "Equipment, pharmacy &amp; labs" is hidden by default: that
      group is full of tiny medical-supply LLCs that are rarely real opportunities.</div>
      <div class="filters"><span class="lbl">Type</span>{''.join(chips)}</div>
      <div class="filters"><span class="lbl">Area</span>{''.join(region_chips)}
        <select id="partner" onchange="applyFilters()">{partner_opts}</select>
        <input type="search" id="q" placeholder="Search (name, town, type...)" oninput="applyFilters()">
        <label class="tog"><input type="checkbox" id="hideBig" checked onchange="applyFilters()"> Hide big systems / public</label>
        <label class="tog"><input type="checkbox" id="onlyNew" onchange="applyFilters()"> {_new_label()[1]}</label></div>
      <p class="meta">Showing <b id="shownCount">{len(orgs)}</b> of {len(orgs)}.</p>
      {org_table(orgs, watchlisted) if orgs else '<div class="empty">No NPI Registry data this scan.</div>'}
      <script>document.addEventListener('DOMContentLoaded',()=>{{F.group='noequip'; applyFilters();}});</script>"""
    return _shell("orgs", body, "New Organizations")


def _lead_box(item: dict) -> str:
    opts = "".join(f'<option{" selected" if s == item["status"] else ""}>{_esc(s)}</option>' for s in store.STATUSES)
    return f"""<div class="lead"><select class="status" onchange="saveLead(this)" title="Where this lead stands">{opts}</select>
      <textarea placeholder="Notes - who's following up, contacts, next step..." oninput="saveLead(this)">{_esc(item['notes'])}</textarea>
      <span class="saved"></span></div>"""


def watchlist_page(items: list) -> str:
    if not items:
        return _shell("watch", """<div class="empty" style="margin-top:24px">Your watchlist is empty.<br><br>
          Tick the small box in the bottom-right corner of any story or organization to save it here, then track it as a lead
          with a status and notes.</div>""", "Watchlist")
    cards = []
    for it in items:
        snap = it["snapshot"]
        added = (it.get("added_at") or "")[:16].replace("T", " ")
        attrs = (f'data-filter="1" data-type="{_esc(it["type"])}" data-id="{_esc(it["id"])}" '
                 f'data-status="{_esc(it["status"])}"')
        extra = f'<div class="meta">Saved {added}</div>{_lead_box(it)}'
        if it["type"] != "org":
            cards.append(story_card(snap, {("story", it["id"])}, remove_on_uncheck=True, extra=extra, attrs=attrs))
            continue
        o = snap
        inner = f"""<div class="topline"><span class="src">New organization · NPI Registry</span>
            <span class="badge place">\U0001F4CD {_esc(o.get('city', ''))}</span></div>
          <a class="headline" href="{_esc(o.get('registry_link', ''))}" target="_blank" rel="noopener">{_esc(o.get('name', ''))}</a>
          <div class="summary">{('dba ' + _esc(o['dba']) + ' · ') if o.get('dba') else ''}{_esc(o.get('taxonomy', ''))} · NPI issued {_esc(o.get('enumerated', ''))} ·
            {_esc(o.get('address', ''))}, {_esc(o.get('city', ''))} {_esc(o.get('zip', ''))} {('· ' + _esc(o['phone'])) if o.get('phone') else ''}
            {('· Registered by ' + _esc(o['official']) + ((', ' + _esc(o['official_title'])) if o.get('official_title') else '')
              + ((' ' + _esc(o['official_phone'])) if o.get('official_phone') else '')) if o.get('official') else ''}</div>{_fits_html(o.get('partners', []))}"""
        actions = (f'<div class="item-actions">{_share_btn(o.get("name", ""), _org_share_text(o), o.get("registry_link", ""))}'
                   f'{_checkbox("org", it["id"], it["label"], snap, True, True)}</div>')
        cards.append(f'<div class="card" {attrs}>{actions}{inner}{extra}</div>')
    chips = ['<button class="chip active" onclick="setChip(\'status\',\'all\',this)">All</button>'] + [
        f'<button class="chip" onclick="setChip(\'status\',{_esc(json.dumps(s))},this)">{_esc(s)} '
        f'({sum(1 for i in items if i["status"] == s)})</button>' for s in store.STATUSES]
    body = f"""<div class="page-actions">
        <a class="btn red" href="/export/watchlist" title="A self-contained page you can email or post in Teams">\U0001F4E4 Share Watchlist as Report</a>
        <a class="btn" href="/export/watchlist.csv" title="Opens in Excel">⬇ Download for Excel (CSV)</a>
        <a class="btn" href="/export/pipeline.json" title="Load this file in HLSA Pipeline &gt; Scout Leads">➜ Send to HLSA Pipeline</a></div>
      <div class="filters"><span class="lbl">Status</span>{''.join(chips)}
        <input type="search" id="q" placeholder="Search watchlist..." oninput="applyFilters()"></div>
      <p class="meta">{len(items)} saved. Status and notes save automatically as you type.</p>
      <div class="list">{''.join(cards)}</div>"""
    return _shell("watch", body, "Watchlist")


def _logo_b64() -> str:
    try:
        with open(config.LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except OSError:
        return ""


def watchlist_export_html(items: list) -> str:
    """Standalone report (logo inlined, no scripts) to email or post."""
    now = dt.datetime.now().strftime("%B %d, %Y").replace(" 0", " ")
    rows = []
    for it in items:
        s = it["snapshot"]
        if it["type"] == "org":
            title, link = s.get("name", ""), s.get("registry_link", "")
            detail = (f"New organization (NPI issued {s.get('enumerated', '')}) · {s.get('taxonomy', '')} · "
                      f"{s.get('address', '')}, {s.get('city', '')} {s.get('zip', '')} {s.get('phone', '')} · Registered by {s.get('official', '')} {s.get('official_phone', '')}")
        else:
            title, link = s.get("title", ""), s.get("link", "")
            detail = f"{s.get('source', '')} · {_date(s.get('ts'))} · {s.get('place') or ''}"
        rows.append(f"""<div style="border:1px solid #E2DFD8;border-left:4px solid {config.NAVY};border-radius:8px;padding:10px 14px;margin:10px 0;background:#fff">
          <div style="font-size:11px;color:#5F6878">{_esc(detail)}</div>
          <a href="{_esc(link)}" style="font-weight:700;color:#1C2230;font-size:15px;text-decoration:none">{_esc(title)}</a>
          <div style="font-size:12px;color:#5F6878;margin-top:4px">Could help: {_esc(_partner_names(s.get('partners') or []))}</div>
          <div style="font-size:12px;margin-top:4px"><b>Status:</b> {_esc(it['status'])}{(' · <b>Notes:</b> ' + _esc(it['notes'])) if it['notes'] else ''}</div>
        </div>""")
    logo = _logo_b64()
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>HLSA Scout Watchlist - {now}</title></head>
<body style="font-family:Segoe UI,Arial,sans-serif;background:#F6F5F2;margin:0;padding:24px;color:#1C2230">
<div style="max-width:860px;margin:0 auto">
<div style="background:{config.NAVY};border-bottom:4px solid {config.RED};padding:14px 18px;border-radius:10px 10px 0 0;display:flex;align-items:center;gap:14px">
{f'<img src="data:image/png;base64,{logo}" style="height:46px;background:#fff;border-radius:6px;padding:4px 8px">' if logo else ''}
<div style="color:#fff"><div style="font-size:20px;font-weight:700">HLSA Scout - Watchlist</div>
<div style="font-size:12px;color:#C9D3E6">{len(items)} opportunities · {now}</div></div></div>
{''.join(rows)}
<p style="font-size:11px;color:#5F6878;margin-top:20px">{_esc(config.DISCLAIMER)}</p></div></body></html>"""


def about_page(readme_html: str) -> str:
    # The README is a full document; embed just its <body>.
    body = readme_html.split("<body>", 1)[-1].rsplit("</body>", 1)[0] if "<body>" in readme_html else readme_html
    style = ""
    if "<style>" in readme_html:
        style = "<style>" + readme_html.split("<style>", 1)[1].split("</style>", 1)[0] + "</style>"
    return _shell("about", f'{style}<div class="readme">{body}</div>', "About")


def diagnostics_page(report: str) -> str:
    return _shell("", f"""<h2 class="section">Diagnostics</h2>
      <p class="section-sub">If something looks wrong, click Copy and paste this into an email or chat - it shows versions, where the data
      lives, the last scan and the recent log. It contains no passwords.</p>
      <p><button class="btn" onclick="navigator.clipboard.writeText(document.getElementById('diag').textContent).then(()=>this.textContent='Copied!')">Copy</button></p>
      <pre id="diag" style="background:#fff;border:1px solid var(--border);border-radius:8px;padding:12px;font-size:11.5px;white-space:pre-wrap">{_esc(report)}</pre>""",
                  "Diagnostics")
