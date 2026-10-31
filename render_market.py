"""The Market & Plan tab: NT Partnership's market analysis and business plan,
built from the market data (scanners/market.py) plus HLSA Scout's own scan
(new organizations from the NPI Registry and the regional stories).

Desktop only - the business plan is NT Partnership's, so it is never published
to the public phone edition."""
import datetime as dt
import json

import config
import geo
import render
from render import _esc

REG_LABEL = {k: v[0] for k, v in geo.REGIONS.items()}

MARKET_CSS = """
.mk h2.section{margin-top:30px}
.mk .lede{font-size:14px;color:var(--text);max-width:950px;line-height:1.55}
.mk .tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:10px;margin:14px 0}
.mk .tile{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:11px 14px}
.mk .tile b{display:block;font-size:24px;color:var(--navy);line-height:1.15}
.mk .tile span{font-size:11.5px;color:var(--muted)}
.mk .two{display:grid;grid-template-columns:repeat(auto-fit,minmax(460px,1fr));gap:16px}
.mk .panel{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.mk .panel h3{margin:0 0 4px;font-size:15px}
.mk .panel .note{margin:6px 0 10px}
.bars{display:flex;flex-direction:column;gap:5px;margin-top:8px}
.bar-row{display:grid;grid-template-columns:minmax(140px,38%) 1fr 54px;gap:8px;align-items:center;font-size:12px}
.bar-row .lbl{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text)}
.bar-row .lbl small{color:var(--muted)}
.bar-track{height:14px;background:transparent;border-radius:4px;position:relative}
.bar-fill{height:14px;background:var(--navy);border-radius:0 4px 4px 0;min-width:2px}
.bar-row.other .bar-fill{background:#9AA6BD}
.bar-row .val{text-align:right;color:var(--text);font-variant-numeric:tabular-nums}
.bar-row:hover .bar-fill{filter:brightness(1.25)}
table.mt{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
table.mt th{text-align:left;color:var(--muted);font-size:11px;font-weight:700;padding:6px 8px;border-bottom:1px solid var(--border);background:var(--soft)}
table.mt td{padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}
table.mt td.n,table.mt th.n{text-align:right;font-variant-numeric:tabular-nums}
.niche{background:var(--panel);border:1px solid var(--border);border-left:4px solid var(--red);border-radius:10px;padding:12px 16px;margin:10px 0}
.niche h3{margin:0;font-size:15px} .niche .why{font-size:13px;margin:5px 0;line-height:1.5}
.niche .ev{font-size:12px;color:var(--muted)} .niche ul{margin:6px 0 0;padding-left:18px;font-size:12.5px}
.niche .tag{display:inline-block;font-size:10.5px;font-weight:700;color:var(--red);text-transform:uppercase;letter-spacing:.4px}
.plan{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:8px 24px 18px;line-height:1.6;font-size:14px}
.plan h3{color:var(--navy);font-size:16px;margin:20px 0 4px;border-bottom:1px solid var(--border);padding-bottom:4px}
.plan .fill{background:#FFF4D6;border-radius:4px;padding:0 4px;color:#7A5A00}
.model{display:grid;grid-template-columns:minmax(300px,380px) 1fr;gap:16px;align-items:start}
.model .inputs{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:10px 14px;font-size:12.5px}
.model .inputs h4{margin:12px 0 4px;font-size:12px;color:var(--navy);text-transform:uppercase;letter-spacing:.4px}
.model .inputs label{display:grid;grid-template-columns:1fr 92px;gap:8px;align-items:center;margin:3px 0}
.model .inputs input{border:1px solid var(--border);border-radius:5px;padding:3px 6px;font-size:12.5px;text-align:right}
.model .out{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:10px 14px}
.model tr.sub td{font-weight:700;border-top:2px solid var(--border)} .model tr.neg td.n{color:#B42318}
@media (max-width:900px){.model{grid-template-columns:1fr} .mk .two{grid-template-columns:1fr}}
"""


def _money(v, short=True) -> str:
    v = float(v or 0)
    if short and abs(v) >= 1e6:
        return f"${v / 1e6:.1f}M"
    if short and abs(v) >= 1e4:
        return f"${v / 1e3:.0f}K"
    return f"${v:,.0f}"


def _pct(v, digits=0) -> str:
    return f"{(v or 0) * 100:.{digits}f}%"


def _bars(rows, value_key, label_fn, fmt, title_fn, top=10, other_label="All others") -> str:
    """Horizontal single-hue bars (magnitude), direct value labels, hover title."""
    if not rows:
        return '<div class="note">No data.</div>'
    shown, rest = rows[:top], rows[top:]
    items = [(label_fn(r), r[value_key], title_fn(r), False) for r in shown]
    if rest:
        rv = sum(r[value_key] for r in rest)
        items.append((f"{other_label} ({len(rest)})", rv, f"{len(rest)} more, combined", True))
    mx = max(v for _, v, _, _ in items) or 1
    return '<div class="bars">' + "".join(
        f'<div class="bar-row{" other" if other else ""}" title="{_esc(t)}"><div class="lbl">{lbl}</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{max(0.5, v / mx * 100):.1f}%"></div></div>'
        f'<div class="val">{fmt(v)}</div></div>' for lbl, v, t, other in items) + "</div>"


# ------------------------------------------------------------------ model
def plan_model(a: dict) -> dict:
    """Three-year projection from the assumptions (mirrors MODEL_JS)."""
    years = []
    for y in (1, 2, 3):
        placements = a[f"placements_y{y}"] * (1 - a["falloff_pct"] / 100)
        rev_place = placements * a["avg_salary"] * a["placement_fee_pct"] / 100
        rev_cred = a[f"cred_new_y{y}"] * a["cred_fee"] + a[f"cred_maint_y{y}"] * a["cred_maint_monthly"] * 12
        rev_consult = a[f"consult_y{y}"] * a["consult_avg"]
        cogs = rev_consult * a["consult_payout_pct"] / 100
        grow = (1 + a["growth_costs_pct"] / 100) ** (y - 1)
        opex = sum(a[k] for k in ("cost_recruiting", "cost_software", "cost_insurance", "cost_hlsa_sponsorship",
                                  "cost_marketing", "cost_admin", "cost_staff")) * grow
        revenue = rev_place + rev_cred + rev_consult
        years.append({"rev_place": rev_place, "rev_cred": rev_cred, "rev_consult": rev_consult, "revenue": revenue,
                      "cogs": cogs, "gross": revenue - cogs, "opex": opex, "net": revenue - cogs - opex})
    return {"years": years}


MODEL_ROWS = [("rev_place", "Placement fees (net of fall-offs)"), ("rev_cred", "Credentialing & enrollment"),
              ("rev_consult", "HLSA Consulting Collective projects"), ("revenue", "Total revenue"),
              ("cogs", "Consultant team payouts"), ("gross", "Gross margin"), ("opex", "Operating costs"),
              ("net", "Net before owners' compensation")]

MODEL_INPUTS = [
    ("Placements (boutique, mostly home health)", [
        ("placements_y1", "Placements - year 1", 1), ("placements_y2", "Placements - year 2", 1),
        ("placements_y3", "Placements - year 3", 1), ("avg_salary", "Avg first-year salary placed ($)", 1000),
        ("placement_fee_pct", "Placement fee (% of salary)", 1), ("falloff_pct", "Fall-offs / refunds (%)", 1)]),
    ("Credentialing & payer enrollment", [
        ("cred_new_y1", "Providers credentialed - year 1", 1), ("cred_new_y2", "Providers credentialed - year 2", 1),
        ("cred_new_y3", "Providers credentialed - year 3", 1), ("cred_fee", "Fee per provider ($)", 50),
        ("cred_maint_y1", "Providers on maintenance - year 1", 1), ("cred_maint_y2", "Providers on maintenance - year 2", 1),
        ("cred_maint_y3", "Providers on maintenance - year 3", 1), ("cred_maint_monthly", "Maintenance per provider / month ($)", 5)]),
    ("HLSA Consulting Collective", [
        ("consult_y1", "Projects - year 1", 1), ("consult_y2", "Projects - year 2", 1), ("consult_y3", "Projects - year 3", 1),
        ("consult_avg", "Average project fee ($)", 500), ("consult_payout_pct", "Paid to consultant team (%)", 1)]),
    ("Operating costs (year 1)", [
        ("cost_recruiting", "Job boards & recruiting tools ($)", 500), ("cost_software", "Credentialing software ($)", 500),
        ("cost_insurance", "Professional & cyber insurance ($)", 500),
        ("cost_hlsa_sponsorship", "HLSA sponsorship / program support - flat ($)", 500),
        ("cost_marketing", "Marketing ($)", 500), ("cost_admin", "Admin, accounting, legal ($)", 500),
        ("cost_staff", "Hired staff - salaries + taxes ($)", 1000),
        ("growth_costs_pct", "Cost growth per year (%)", 1)]),
]

MODEL_JS = r"""
const MODEL_ROWS=%s;
function mval(k){const e=document.querySelector('.inputs input[data-k="'+k+'"]');return e?parseFloat(e.value)||0:0;}
function money(v){return (v<0?'-':'')+'$'+Math.abs(Math.round(v)).toLocaleString();}
function computeModel(){
  const a={}; document.querySelectorAll('.inputs input[data-k]').forEach(e=>a[e.dataset.k]=parseFloat(e.value)||0);
  const ys=[1,2,3].map(y=>{const pl=a['placements_y'+y]*(1-a.falloff_pct/100), rp=pl*a.avg_salary*a.placement_fee_pct/100,
    rc=a['cred_new_y'+y]*a.cred_fee+a['cred_maint_y'+y]*a.cred_maint_monthly*12, rk=a['consult_y'+y]*a.consult_avg,
    cogs=rk*a.consult_payout_pct/100, grow=Math.pow(1+a.growth_costs_pct/100,y-1),
    opex=(a.cost_recruiting+a.cost_software+a.cost_insurance+a.cost_hlsa_sponsorship+a.cost_marketing+a.cost_admin+a.cost_staff)*grow,
    rev=rp+rc+rk; return {rev_place:rp,rev_cred:rc,rev_consult:rk,revenue:rev,cogs:cogs,gross:rev-cogs,opex:opex,net:rev-cogs-opex};});
  document.getElementById('model-body').innerHTML=MODEL_ROWS.map(([k,l])=>'<tr class="'+(['revenue','gross','net'].includes(k)?'sub':'')+
    (ys.some(y=>y[k]<0)?' neg':'')+'"><td>'+l+'</td>'+ys.map(y=>'<td class="n">'+money(y[k])+'</td>').join('')+'</tr>').join('');
  return a;
}
let _mt; function modelChanged(){const a=computeModel(); clearTimeout(_mt); _mt=setTimeout(()=>{
  fetch('/api/market/assumptions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(a)})
   .then(r=>{const s=document.getElementById('model-saved'); s.textContent=r.ok?'Saved':'Could not save'; setTimeout(()=>s.textContent='',1500)});},500);}
function resetModel(){fetch('/api/market/assumptions',{method:'DELETE'}).then(()=>location.reload());}
function refreshMarket(btn){btn.disabled=true;btn.textContent='Refreshing market data (about a minute)...';
  fetch('/api/market/refresh',{method:'POST'}).then(r=>r.json()).then(d=>{if(d.ok)location.reload();else{btn.disabled=false;btn.textContent='Refresh failed - try again';alert(d.error||'Refresh failed');}})
  .catch(()=>{btn.disabled=false;btn.textContent='Refresh failed - try again'});}
document.addEventListener('DOMContentLoaded',computeModel);
""" % json.dumps(MODEL_ROWS)


def _model_html(a: dict) -> str:
    groups = "".join(
        f"<h4>{_esc(title)}</h4>" + "".join(
            f'<label>{_esc(lbl)}<input type="number" step="{step}" data-k="{k}" value="{a[k]:g}" oninput="modelChanged()"></label>'
            for k, lbl, step in fields) for title, fields in MODEL_INPUTS)
    m = plan_model(a)
    rows = "".join(
        f'<tr class="{"sub" if k in ("revenue", "gross", "net") else ""}"><td>{_esc(lbl)}</td>'
        + "".join(f'<td class="n">{_money(y[k], short=False)}</td>' for y in m["years"]) + "</tr>"
        for k, lbl in MODEL_ROWS)
    return f"""<div class="model"><div class="inputs">{groups}
        <p style="margin-top:12px"><button class="btn" type="button" onclick="resetModel()">Reset to starting assumptions</button>
        <span id="model-saved" class="meta"></span></p></div>
      <div class="out"><table class="mt"><thead><tr><th></th><th class="n">Year 1</th><th class="n">Year 2</th><th class="n">Year 3</th></tr></thead>
        <tbody id="model-body">{rows}</tbody></table>
        <p class="note">Change any number on the left - the projection updates instantly and is saved on this computer.
        These are planning assumptions, not forecasts: replace them with NT Partnership's real pricing, capacity and costs.
        Owners' pay is excluded so the bottom line shows what the business can fund.</p></div></div>"""


# ------------------------------------------------------------------ niches
def _niches(m: dict, scan: dict | None) -> list:
    """Ranked niche opportunities, each with the evidence behind it and named targets."""
    out = []
    hh, ho, cl, cn, wf = (m.get(k) or {} for k in ("home_health", "hospice", "contract_labor", "clinicians", "workforce"))
    orgs = (scan or {}).get("orgs") or []
    stories = (scan or {}).get("stories") or []

    indep = [a for a in hh.get("agencies", []) if a["group_type"].startswith("Independent") and a["benes"]]
    if indep:
        share = sum(a["benes"] for a in indep) / (hh.get("total_benes") or 1)
        out.append({
            "tag": "Staffing + credentialing", "title": "Owner-operated home health agencies",
            "why": "Independents can't match the chains' recruiting departments, yet carry the same CMS staffing and "
                   "documentation burden. A boutique, relationship-based placement partner is exactly what they lack - "
                   "and the owner is the decision-maker you meet at an HLSA mixer.",
            "ev": f"{len([a for a in hh['agencies'] if a['group_type'].startswith('Independent')])} of {len(hh['agencies'])} "
                  f"Medicare home health agencies in the territory are owner-operated; together they served "
                  f"{_pct(share)} of the area's Medicare home health patients in 2024.",
            "targets": [f"{a['name']} ({a['city']}) - {a['benes']:,.0f} Medicare patients" for a in indep[:8]]})

    if cl.get("facilities"):
        reliant = sorted((f for f in cl["facilities"] if f["contract_share"] >= 0.08), key=lambda f: -f["contract_share"])
        rural = [f for f in reliant if f["region"] in ("rural", "ring")]
        out.append({
            "tag": "Staffing", "title": "Nursing homes already paying for contract nurses - especially in the rural ring",
            "why": "These facilities are already buying agency labor every day; converting some of those hours into "
                   "permanent placements saves them money and is a straightforward pitch. Rural facilities have the "
                   "thinnest local labor pools.",
            "ev": f"{len(reliant)} facilities used contract staff for 8%+ of nursing hours in {cl['quarter']} "
                  f"({len(rural)} of them outside Bexar/Travis cores). Contract hours across the territory: "
                  f"{cl['contract_hours']:,} that quarter (Payroll-Based Journal).",
            "targets": [f"{f['name']} ({f['city']}) - {_pct(f['contract_share'])} contract, {f['contract_hours']:,} hrs/qtr"
                        for f in reliant[:8]]})

    new_by_group = {}
    for o in orgs:
        new_by_group.setdefault(o["group"], []).append(o)
    startup = [o for g in ("Home health & home care", "Hospice", "Primary care & clinics", "Physician groups",
                           "Behavioral health", "Therapy & rehab") for o in new_by_group.get(g, []) if not o.get("big_system")]
    if startup:
        out.append({
            "tag": "Start-up package", "title": "Brand-new practices and agencies (the start-up package)",
            "why": "A new organization needs credentialing, payer enrollment, its first hires, billing and marketing all "
                   "at once - the ideal moment for one bundled NT + HLSA-partner offer instead of five vendors.",
            "ev": f"{len(startup)} new practices/agencies registered NPIs in the territory in the last 90 days "
                  f"(about {len(startup) / 3:.0f} a month) - see the New Organizations tab.",
            "targets": [f"{o['name']} ({o['city']}) - {o['taxonomy'] or o['group']}, NPI {o['enumerated']}" for o in startup[:8]]})

    beh = new_by_group.get("Behavioral health", [])
    np_count = dict(cn.get("by_specialty", [])).get("Nurse Practitioner", 0)
    if beh or np_count:
        out.append({
            "tag": "Credentialing", "title": "Behavioral health and nurse-practitioner practices",
            "why": "Small counseling, psychiatry and NP-led practices multiply fast, enroll with many payers (including "
                   "Medicaid managed care) and rarely have credentialing staff - a recurring-revenue niche for "
                   "credentialing plus maintenance.",
            "ev": f"{len(beh)} new behavioral-health organizations in 90 days; nurse practitioners are the largest group of "
                  f"Medicare-billing clinicians in the territory ({np_count:,}).",
            "targets": [f"{o['name']} ({o['city']}) - {o['taxonomy']}" for o in beh[:6]]})

    if ho.get("agencies"):
        out.append({
            "tag": "Staffing + consulting", "title": "A crowded, fragmented hospice market",
            "why": "Many small hospices competing on quality and compliance need hospice-experienced RNs and aides, "
                   "compliance help and, increasingly, buyers or exit plans - staffing for NT, transitions and finance "
                   "work for the HLSA Consulting Collective.",
            "ev": f"{len(ho['agencies'])} Medicare hospices have offices in the territory; concentration index (HHI) "
                  f"{ho['hhi']:,} - well under 1,500, i.e. unconcentrated.",
            "targets": [f"{a['name']} ({a['city']}) - {a['benes']:,.0f} patients" for a in ho["agencies"][:6]]})

    deals = [s for s in stories if "deals" in (s.get("categories") or [])]
    builds = [s for s in stories if "facilities" in (s.get("categories") or [])]
    if deals or builds:
        out.append({
            "tag": "HLSA Consulting Collective", "title": "Transitions and new facilities: ad hoc consulting teams",
            "why": "Ownership changes, expansions and new facilities need strategy, financial analysis, billing and "
                   "leadership help for a few months - exactly what an ad hoc team of HLSA members and partners can deliver, "
                   "with NT Partnership as the contracting firm.",
            "ev": f"This scan: {len(deals)} ownership-change/closure stories and {len(builds)} facility projects in the territory.",
            "targets": [f"{s['title']} ({s.get('place') or s['source']})" for s in (deals + builds)[:8]]})
    return out


# ------------------------------------------------------------------ page
def _agency_panel(title: str, d: dict, noun: str, plural: str, service: str) -> str:
    if not d or not d.get("groups"):
        return f'<div class="panel"><h3>{_esc(title)}</h3><div class="note">Not available.</div></div>'
    bars = _bars(d["groups"], "share",
                 lambda g: f'{_esc(g["group"])} <small>· {g["agencies"]} {plural if g["agencies"] > 1 else noun}</small>',
                 lambda v: _pct(v, 1),
                 lambda g: f'{g["group"]}: {g["benes"]:,.0f} Medicare patients, {_money(g["payments"])} Medicare payments, '
                           f'{g["agencies"]} {plural} - {g["type"]}', top=10)
    types = "".join(f'<tr><td>{_esc(t)}</td><td class="n">{v["agencies"]}</td><td class="n">{_pct(v["benes"] / (d["total_benes"] or 1))}</td></tr>'
                    for t, v in sorted(d["by_type"].items(), key=lambda kv: -kv[1]["benes"]))
    hhi_word = "unconcentrated" if d["hhi"] < 1500 else ("moderately concentrated" if d["hhi"] < 2500 else "highly concentrated")
    return f"""<div class="panel"><h3>{_esc(title)}</h3>
      <div class="note">Share of the territory's 2024 Medicare {service} patients ({d['total_benes']:,.0f}) by parent owner.
        Top 5 hold {_pct(d['top5_share'])}; concentration index (HHI) {d['hhi']:,} = {hhi_word}.</div>
      {bars}
      <table class="mt"><thead><tr><th>Ownership type</th><th class="n">{plural.title()}</th><th class="n">Patient share</th></tr></thead><tbody>{types}</tbody></table>
      <div class="note">{d['no_volume']} {plural} had no 2024 Medicare volume (new, very small, or Medicaid/private-pay only).
        Location = the {noun}'s office; most serve several counties.</div></div>"""


def market_page(m: dict | None, scan: dict | None, assumptions: dict, refreshing: bool = False) -> str:
    head = f"""<style>{MARKET_CSS}</style><div class="mk">
      <div class="disclaimer">Market research and business plan for <b>NT Partnership</b>, built from free public data (CMS, BLS) and
      HLSA Scout's own scan. Laptop only - this tab is never published to the public phone edition. Figures are for planning;
      verify before quoting them externally.</div>"""
    if not m:
        return render._shell("market", head + f"""<div class="empty">Market data hasn't been loaded on this computer yet.<br><br>
          <button class="btn red" onclick="refreshMarket(this)">Load market data now (about a minute)</button></div></div>
          <script>{MODEL_JS}</script>""", "Market & Plan")

    hh, ho, cl, cn, wf = (m.get(k) or {} for k in ("home_health", "hospice", "contract_labor", "clinicians", "workforce"))
    orgs = (scan or {}).get("orgs") or []
    stories = (scan or {}).get("stories") or []
    fetched = (m.get("fetched_at") or "")[:16].replace("T", " ")
    errs = m.get("errors") or {}
    rn_sa = next((r for r in wf.get("rows", []) if r["occ"] == "291141" and "San Antonio" in r["area"]), {})
    aides = sum(r.get("employment", 0) for r in wf.get("rows", []) if r["occ"] in ("311120", "311131"))
    est_contract_spend = cl.get("contract_hours", 0) * 4 * 65   # hours/qtr x 4 x ~$65/hr blended bill rate

    body = [head, f"""<div class="page-actions">
        <button class="btn" onclick="refreshMarket(this)">⟳ Refresh market data</button>
        <a class="btn red" href="/export/business_plan">⬇ Download business plan (opens in Word)</a></div>
      <p class="meta">Market data loaded {fetched}{' · some sources failed: ' + _esc(', '.join(errs)) if errs else ''}
        {'' if scan else ' · Run a scan to add the new organizations and regional stories to this analysis.'}</p>
      <h2 class="section">\U0001F4C8 Market at a glance</h2>
      <div class="tiles">
        <div class="tile"><b>{len(hh.get('agencies', []))}</b><span>Medicare home health agencies with offices in the territory</span></div>
        <div class="tile"><b>{hh.get('total_benes', 0):,.0f}</b><span>Medicare home health patients they served (2024)</span></div>
        <div class="tile"><b>{len(ho.get('agencies', []))}</b><span>Medicare hospices in the territory</span></div>
        <div class="tile"><b>{len(cl.get('facilities', []))}</b><span>nursing homes reporting staffing ({_esc(cl.get('quarter', ''))})</span></div>
        <div class="tile"><b>{cl.get('contract_hours', 0):,}</b><span>contract nursing hours that quarter (≈{_money(est_contract_spend)}/yr at ~$65/hr)</span></div>
        <div class="tile"><b>{cn.get('total', 0):,}</b><span>clinicians billing Medicare in the territory (credentialing base)</span></div>
        <div class="tile"><b>{len(orgs) or '–'}</b><span>new healthcare organizations, last 90 days (NPI Registry)</span></div>
        <div class="tile"><b>{rn_sa.get('employment', 0):,.0f}</b><span>RNs in the San Antonio metro, avg {_money(rn_sa.get('annual_wage', 0), False)}/yr (BLS {wf.get('year', '')})</span></div>
        <div class="tile"><b>{aides:,.0f}</b><span>home health, personal care &amp; nursing aides (SA + Austin metros)</span></div>
      </div>"""]

    body.append(f"""<h2 class="section">\U0001F967 Market share distribution</h2>
      <p class="lede">Who holds the market NT Partnership sells into. Staffing and credentialing firms don't publish revenue, so share is
      measured on the <b>customer side</b>: which owners hold the Medicare home health and hospice volume, who buys contract labor,
      and where the clinicians are. A fragmented market with many owner-operated agencies favors a relationship-driven boutique.</p>
      <div class="two">{_agency_panel('Home health agencies', hh, 'agency', 'agencies', 'home health')}{_agency_panel('Hospices', ho, 'hospice', 'hospices', 'hospice')}</div>""")

    if cl.get("facilities"):
        county_rows = sorted(cl["by_county"].items(), key=lambda kv: -kv[1]["contract_hours"])
        cbars = _bars([{"county": k, **v} for k, v in county_rows], "contract_hours",
                      lambda r: f'{_esc(r["county"])} County <small>· {r["facilities"]} facilities</small>',
                      lambda v: f"{v:,.0f}", lambda r: f'{r["county"]}: {r["contract_hours"]:,} contract of {r["total_hours"]:,} total nursing hours '
                                                      f'({_pct(r["contract_hours"] / (r["total_hours"] or 1), 1)})', top=10)
        top_f = "".join(f'<tr><td>{_esc(f["name"])}<div class="meta">{_esc(f["city"])}</div></td><td class="n">{_pct(f["contract_share"])}</td>'
                        f'<td class="n">{f["contract_hours"]:,}</td><td class="n">{f["avg_census"]}</td></tr>'
                        for f in sorted(cl["facilities"], key=lambda f: -f["contract_share"])[:12])
        body.append(f"""<div class="two" style="margin-top:16px">
          <div class="panel"><h3>Contract (agency) nursing hours by county - {_esc(cl['quarter'])}</h3>
            <div class="note">Nursing homes report every staff hour to CMS, split into employees and contract staff.
            Territory-wide, contract staff worked {_pct(cl['contract_hours'] / (cl['total_hours'] or 1), 1)} of nursing hours.</div>{cbars}</div>
          <div class="panel"><h3>Most contract-reliant facilities</h3>
            <table class="mt"><thead><tr><th>Facility</th><th class="n">Contract share</th><th class="n">Contract hrs/qtr</th><th class="n">Avg residents</th></tr></thead>
            <tbody>{top_f}</tbody></table></div></div>""")

    if cn.get("total"):
        spec_rows = [{"s": s, "n": n} for s, n in cn["by_specialty"]]
        sbars = _bars(spec_rows, "n", lambda r: _esc(r["s"]), lambda v: f"{v:,.0f}", lambda r: f'{r["s"]}: {r["n"]:,} clinicians', top=12)
        reg = "".join(f'<tr><td>{_esc(REG_LABEL.get(k, k))}</td><td class="n">{v:,}</td><td class="n">{sum(1 for o in orgs if o["region"] == k)}</td></tr>'
                      for k, v in sorted(cn["by_region"].items(), key=lambda kv: -kv[1]))
        groups = {}
        for o in orgs:
            groups[o["group"]] = groups.get(o["group"], 0) + 1
        gbars = _bars([{"g": g, "n": n} for g, n in sorted(groups.items(), key=lambda kv: -kv[1])], "n",
                      lambda r: _esc(r["g"]), lambda v: f"{v:,}", lambda r: f'{r["g"]}: {r["n"]} new organizations in 90 days', top=8) if orgs else \
            '<div class="note">Run a scan to include new organizations.</div>'
        body.append(f"""<div class="two" style="margin-top:16px">
          <div class="panel"><h3>Credentialing market: clinicians billing Medicare, by specialty</h3>
            <div class="note">{cn['total']:,} individual clinicians with a practice address in the territory (CMS 2024). Each one
            must be credentialed with every payer and re-credentialed about every three years.</div>{sbars}</div>
          <div class="panel"><h3>New-practice formation (last 90 days)</h3>
            <div class="note">New organizational NPIs by type - the flow of brand-new customers needing credentialing,
            enrollment and first hires.</div>{gbars}
            <table class="mt"><thead><tr><th>Area</th><th class="n">Medicare clinicians</th><th class="n">New orgs (90 days)</th></tr></thead><tbody>{reg}</tbody></table></div></div>""")

    if wf.get("rows"):
        wrows = "".join(f'<tr><td>{_esc(r["occupation"])}</td><td>{_esc(r["area"].replace(" metro", ""))}</td>'
                        f'<td class="n">{r.get("employment", 0):,.0f}</td><td class="n">{_money(r.get("annual_wage", 0), False)}</td>'
                        f'<td class="n">{_money(r.get("annual_wage", 0) * 0.20, False)}</td></tr>'
                        for r in sorted(wf["rows"], key=lambda r: (r["occupation"], r["area"])))
        body.append(f"""<div class="panel" style="margin-top:16px"><h3>Workforce &amp; pay benchmarks (BLS {wf['year']})</h3>
          <div class="note">The candidate pool and the basis for placement fees. A 20% direct-hire fee is shown for reference.</div>
          <table class="mt"><thead><tr><th>Occupation</th><th>Metro</th><th class="n">Employed</th><th class="n">Avg annual pay</th><th class="n">20% fee</th></tr></thead>
          <tbody>{wrows}</tbody></table></div>""")

    niches = _niches(m, scan)
    body.append('<h2 class="section">\U0001F3AF Niche opportunities</h2><p class="lede">Where NT Partnership and the HLSA network can win, '
                'ranked by fit - each with the evidence and named starting targets (save them to the Watchlist from the other tabs).</p>')
    for n in niches:
        targets = "".join(f"<li>{_esc(t)}</li>" for t in n["targets"])
        body.append(f"""<div class="niche"><span class="tag">{_esc(n['tag'])}</span><h3>{_esc(n['title'])}</h3>
          <div class="why">{_esc(n['why'])}</div><div class="ev">Evidence: {_esc(n['ev'])}</div>
          {'<ul>' + targets + '</ul>' if targets else ''}</div>""")

    comp = "".join(f'<tr><td><b>{_esc(c[0])}</b>{" <a href=" + chr(34) + _esc(c[4]) + chr(34) + " target=_blank rel=noopener>↗</a>" if c[4] else ""}</td>'
                   f'<td>{_esc(c[1])}</td><td>{_esc(c[2])}</td><td>{_esc(c[3])}</td></tr>' for c in config.COMPETITORS)
    body.append(f"""<h2 class="section">⚔️ Competitive landscape</h2>
      <p class="lede">No public source reports staffing or credentialing firms' local market shares, so this is a researched list
      (October 2026, from firms' own sites and job postings). NT Partnership's edge is what national and remote competitors can't
      copy: local relationships through HLSA, a boutique home health focus, and the ability to bundle credentialing, staffing,
      billing and consulting from trusted partners.</p>
      <div class="panel"><table class="mt"><thead><tr><th>Firm</th><th>Type</th><th>Model</th><th>Notes / positioning</th></tr></thead>
      <tbody>{comp}</tbody></table></div>""")

    body.append(f'<h2 class="section">\U0001F4D8 Business plan</h2>{plan_html(m, scan, assumptions, niches)}')
    body.append(f'<h2 class="section">\U0001F4B5 Financial model</h2>{_model_html(assumptions)}')
    body.append(f"</div><script>{MODEL_JS}</script>")
    return render._shell("market", "".join(body), "Market & Plan")


def plan_html(m: dict, scan: dict | None, a: dict, niches: list | None = None) -> str:
    """The narrative business plan with live numbers. [Highlighted] items are for NT Partnership to supply."""
    hh, ho, cl, cn, wf = (m.get(k) or {} for k in ("home_health", "hospice", "contract_labor", "clinicians", "workforce"))
    orgs = (scan or {}).get("orgs") or []
    niches = niches if niches is not None else _niches(m, scan)
    model = plan_model(a)
    y1, y3 = model["years"][0], model["years"][2]
    indep_n = len([x for x in hh.get("agencies", []) if x["group_type"].startswith("Independent")])
    fill = lambda t: f'<span class="fill">[{_esc(t)}]</span>'
    principals = "".join(f"<p><b>{_esc(name)}</b> - <i>{_esc(role)}</i><br>{_esc(bio)}</p>" for name, role, bio in config.PRINCIPALS)
    lines = "".join(f"<li><b>{_esc(n)}</b> - {_esc(d)}" + (f" <i>(partners: {_esc(', '.join(config.PARTNERS[p][0] for p in ps))})</i>" if ps else "") + "</li>"
                    for n, d, ps in config.CONSULTING_LINES)
    niche_list = "".join(f"<li><b>{_esc(n['title'])}</b> - {_esc(n['ev'])}</li>" for n in niches)
    return f"""<div class="plan">
<h3>1. Executive summary</h3>
<p>NT Partnership is a San Antonio boutique healthcare services firm offering <b>direct-hire placements</b> (primarily home
health), <b>physician and provider credentialing / payer enrollment</b>, and - through its relationship with Healthcare Leaders of
San Antonio (HLSA) - <b>ad hoc consulting teams</b> drawn from HLSA's membership and Trusted Referral Partners. It serves
independent practices, home health and hospice agencies, nursing facilities and new healthcare organizations across Bexar County,
the surrounding counties, the I-35 Corridor to Austin and the rural Hill Country. Its principals are
{' and '.join(_esc(p[0]) for p in config.PRINCIPALS)}; the business is in the planning stage, ahead of forming a Texas LLC.</p>
<p>The market is large and fragmented: {len(hh.get('agencies', []))} Medicare home health agencies ({indep_n} owner-operated),
{len(ho.get('agencies', []))} hospices, {len(cl.get('facilities', []))} nursing homes buying {cl.get('contract_hours', 0):,} contract
nursing hours a quarter, {cn.get('total', 0):,} Medicare-billing clinicians, and {len(orgs) or 'dozens of'} new healthcare
organizations registering every 90 days. On the starting assumptions, NT Partnership reaches {_money(y1['revenue'], False)} revenue in
year 1 and {_money(y3['revenue'], False)} in year 3, with {_money(y3['net'], False)} before owners' compensation in year 3.</p>

<h3>2. The company, its principals and the HLSA relationship</h3>
<p><b>Status.</b> NT Partnership is in the planning stage: the principals are organizing the business and intend to form a Texas limited
liability company (not yet filed). Ownership split: {fill('percentages')}. Formation steps are in the 12-month roadmap below.</p>
<p><b>Principals.</b> The two principals bring complementary strengths - health administration, strategy and nursing-workforce
experience on one side; physician relationships, sales, capital and deal structuring on the other - and both already sell into the same
San Antonio healthcare community through HLSA and Wave Online.</p>
{principals}
<p><b>HLSA.</b> Healthcare Leaders of San Antonio was founded and is led by {config.PRINCIPALS[0][0]} as president, who sets its strategic
direction with the help of an informal advisory board. HLSA is not yet incorporated; the intent is to organize it as an LLC and/or a tax-exempt
organization. It is a volunteer professional network of healthcare decision-makers (monthly mixers, newsletter, webinars, sponsorships;
an organization-reported 3,000+ invitees) and a talent pool of experienced executives, clinicians and specialists. NT Partnership is the
contracting and coordinating firm; the relationship gives it three things competitors lack: <b>warm access</b> to owners and administrators,
<b>credibility by association</b> with a trusted network, and <b>bench strength</b> to staff consulting teams without carrying salaries.</p>
<p><b>How the relationship is structured (recommended).</b> NT Partnership contracts with clients and engages HLSA members and partners as
independent subcontractors for consulting work at agreed rates; NT supports HLSA through a <b>flat, fair-market-value sponsorship</b> rather
than per-referral payments. Two things to settle with counsel and a CPA before launch:</p>
<ul><li><b>Referral compensation.</b> In healthcare, paying for referrals of patients or Medicare/Medicaid business can raise Anti-Kickback
and Texas patronage issues - keep payments flat and documented, never tied to referrals or patient volume.</li>
<li><b>Related parties.</b> Because HLSA's president is also an NT Partnership principal, the NT-HLSA arrangement is a related-party
transaction. Put it in writing, disclose it to HLSA's advisory board, and price it at fair market value now - it becomes a formal requirement
if HLSA becomes tax-exempt (private-benefit and conflict-of-interest rules). Also worth asking: professional and business networking
associations usually qualify as <b>501(c)(6)</b> business leagues rather than 501(c)(3) charities, which affects what HLSA can do and how
sponsorships are treated.</li></ul>

<h3>3. Services</h3>
<ul><li><b>Boutique placements</b> - direct-hire RNs, LVNs, home health aides, therapists, coordinators and administrators for home health,
hospice, nursing facilities and practices; fee {a['placement_fee_pct']:g}% of first-year salary with a replacement guarantee.</li>
<li><b>Credentialing &amp; payer enrollment</b> - CAQH, Medicare/Medicaid and commercial enrollment, hospital privileges, recredentialing
calendars and roster maintenance; {_money(a['cred_fee'], False)} per provider plus {_money(a['cred_maint_monthly'], False)}/provider/month maintenance.</li>
<li><b>HLSA Consulting Collective</b> - ad hoc teams assembled per engagement:<ul>{lines}</ul></li></ul>

<h3>4. Market analysis</h3>
<p>Home health: the top five owners hold {_pct(hh.get('top5_share', 0))} of the territory's Medicare home health patients (HHI
{hh.get('hhi', 0):,}); the rest is spread across many single-site and owner-operated agencies - the boutique's natural customers.
Hospice is even more fragmented (HHI {ho.get('hhi', 0):,}). Nursing homes reported {cl.get('contract_hours', 0):,} contract nursing hours in
{_esc(cl.get('quarter', ''))}, concentrated in rural-ring facilities. {cn.get('total', 0):,} clinicians bill Medicare from territory addresses,
nurse practitioners being the largest group. Workforce: see the BLS benchmarks above - the RN pool in the San Antonio metro alone is
about {next((r.get('employment', 0) for r in wf.get('rows', []) if r['occ'] == '291141' and 'San Antonio' in r['area']), 0):,.0f}.</p>

<h3>5. Target segments and niche opportunities</h3><ol>{niche_list}</ol>

<h3>6. Competition and positioning</h3>
<p>National travel firms and app marketplaces compete on volume and price; remote credentialing outsourcers compete on cost. NT
Partnership competes on <b>local relationships, speed and fit</b>: candidates vetted by people who know the agencies, credentialing that
includes local hospital-privileging know-how, and one-call bundles with HLSA partners (billing with Wave Online, staffing overflow with
Nurses Etc, marketing with Macro, finance with Ascent). See the competitive landscape above.</p>

<h3>7. Marketing and sales</h3>
<ul><li>HLSA channels: mixer presence, newsletter features, a quarterly webinar (e.g. "Credentialing a new practice in 90 days"),
event sponsorship.</li>
<li>HLSA Scout as the lead engine: new NPI registrations, opening/expansion stories and contract-reliant facilities feed a weekly call
list; track leads in the Watchlist and HLSA Pipeline.</li>
<li>Partner referrals both ways with the Trusted Referral Partners, coordinated through HLSA so prospects meet one network.</li>
<li>Owner-to-owner selling: the start-up package for new practices; conversion offers for facilities heavy on contract labor.</li></ul>

<h3>8. Operations and team</h3>
<p>Core team: the two principals at launch ({fill('who leads placements vs. credentialing vs. consulting')}); a contract recruiter
and credentialing specialist added as volume grows (see "Hired staff" in the financial model). Tools: an applicant tracking system, a credentialing
tracker, HIPAA-appropriate document handling (BAAs where PHI is touched). Consulting engagements: NT scopes and contracts the work,
assembles a team from HLSA members/partners, sets fixed-fee milestones and quality-reviews deliverables.</p>

<h3>9. Financial plan</h3>
<p>See the financial model below (assumptions are editable and saved). Year 1 revenue {_money(y1['revenue'], False)}
(placements {_money(y1['rev_place'], False)}, credentialing {_money(y1['rev_cred'], False)}, consulting {_money(y1['rev_consult'], False)});
year 3 revenue {_money(y3['revenue'], False)}. Start-up needs are modest - mainly insurance, software and working capital for the
weeks between placement and fee collection. {fill('capital available, owner draws, pricing confirmed')}</p>

<h3>10. 12-month roadmap</h3>
<ul><li>Months 1-2: form the Texas LLC (certificate of formation with the Secretary of State, operating agreement with the ownership split,
EIN, business bank account); agreements (HLSA sponsorship, subcontractors, client templates, BAAs); insurance; tools; pick two niches to
lead with.</li>
<li>Months 2-4: first credentialing clients from new-NPI outreach; first placements with owner-operated home health agencies.</li>
<li>Months 4-6: first HLSA Consulting Collective engagement; HLSA webinar; partner bundle offers.</li>
<li>Months 6-12: rural-ring facility program; maintenance-retainer base; review pricing and the model against actuals.</li></ul>

<h3>11. Risks and how they're handled</h3>
<ul><li>Referral-compensation compliance - flat FMV sponsorship, counsel review, written agreements.</li>
<li>Related-party perception (HLSA's president is an NT principal) - written agreement, advisory-board disclosure, open opportunities for
other HLSA members and partners.</li>
<li>Uneven placement cash flow - credentialing maintenance retainers as the steady base.</li>
<li>Candidate scarcity - HLSA referrals, rural relocation incentives, partnership with Nurses Etc on overflow.</li>
<li>Consultant quality and availability - vetted HLSA roster, scoped fixed-fee work, NT quality review.</li>
<li>Reimbursement changes (home health/hospice rules) - watched through HLSA Scout's news feed.</li></ul>

<h3>12. Key measures</h3>
<p>Placements per month and fill time; guarantee fall-offs; providers credentialed and days-to-enrollment; maintenance providers under
management; consulting projects and margin; HLSA-sourced share of new business.</p>
<p class="meta">Sources: CMS data catalog (home health and hospice enrollments, owners and 2024 Medicare utilization; Payroll-Based Journal;
Medicare Physician &amp; Other Practitioners 2024), BLS Occupational Employment &amp; Wage Statistics, CMS NPI Registry, regional news via
HLSA Scout. <span class="fill">[Highlighted]</span> items are for NT Partnership to fill in.</p>
</div>"""


def business_plan_export(m: dict, scan: dict | None, a: dict) -> str:
    """A standalone document of the plan + model (Word opens .html files directly)."""
    model = plan_model(a)
    rows = "".join(f"<tr><td>{_esc(l)}</td>" + "".join(f'<td style="text-align:right">{_money(y[k], False)}</td>' for y in model["years"]) + "</tr>"
                   for k, l in MODEL_ROWS)
    now = dt.date.today().strftime("%B %d, %Y").replace(" 0", " ")
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>NT Partnership - Market Analysis &amp; Business Plan</title>
<style>body{{font-family:Calibri,Segoe UI,Arial,sans-serif;max-width:860px;margin:30px auto;color:#1C2230;line-height:1.5}}
h1{{color:{config.NAVY}}} h3{{color:{config.NAVY};border-bottom:1px solid #ddd}} .fill{{background:#FFF4D6}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #ccc;padding:5px 8px;font-size:13px}} .meta{{color:#5F6878;font-size:12px}}</style></head>
<body><h1>NT Partnership - Market Analysis &amp; Business Plan</h1><p class="meta">Prepared with HLSA Scout · {now} · Confidential</p>
{plan_html(m, scan, a).replace('<div class="plan">', '<div>')}
<h3>Financial projection</h3><table><tr><th></th><th>Year 1</th><th>Year 2</th><th>Year 3</th></tr>{rows}</table>
<p class="meta">Assumptions: {_esc(', '.join(f'{k}={v:g}' for k, v in a.items()))}</p></body></html>"""
