"""Self-contained interactive visual showcase for Signalpost batch runs."""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def generate_simple_page(envelopes: list[dict[str, Any]], output_path: str | Path, *, run_id: str = "run", report: dict[str, Any] | None = None) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Prepare lightweight payload for UI
    ui_records = []
    for env in envelopes:
        prof = env.get("profile") or {}
        claims = {c.get("field"): c.get("value") for c in env.get("claims") or []}
        ev = prof.get("evidence") or {}
        
        web_ev = ev.get("website") or {}
        web_val = web_ev.get("value") or {}
        web_publishable = bool((web_val.get("identity_assessment") or {}).get("publishable"))
        
        fin_val = (ev.get("financials") or {}).get("value") or {}
        records = fin_val.get("records") or []
        
        roles_val = (ev.get("roles") or {}).get("value") or {}
        roles = [r for r in roles_val.get("roles") or [] if not r.get("inactive")]
        
        loc_val = (ev.get("locations") or {}).get("value") or {}
        locations = loc_val.get("locations") or []

        ui_records.append({
            "org": env.get("organisation_number"),
            "name": env.get("legal_identity", {}).get("name") or prof.get("name") or "Unnamed",
            "form": env.get("legal_identity", {}).get("legal_form") or prof.get("legal_form") or "",
            "municipality": prof.get("municipality") or "",
            "industry": prof.get("industry_label") or "",
            "industry_code": prof.get("industry_code") or "",
            "employees": prof.get("employees"),
            "summary": env.get("summary") or prof.get("summary") or claims.get("company_summary") or "",
            "website": web_val.get("final_url") if web_publishable else None,
            "careers": web_val.get("careers_page") if web_publishable else None,
            "news": web_val.get("news_page") if web_publishable else None,
            "social": [s for s in web_val.get("social_links") or []] if web_publishable else [],
            "financials": records,
            "roles": roles[:10],
            "locations": locations[:8],
            "state": env.get("state"),
            "modules": env.get("modules") or {},
            "evidence": env.get("evidence") or [],
        })

    payload_json = json.dumps(ui_records, ensure_ascii=False).replace("</", "<\\/")
    report_json = json.dumps(report or {}, ensure_ascii=False).replace("</", "<\\/")

    html_content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Signalpost Intelligence — {html.escape(run_id)}</title>
<style>
:root {{
  --bg: #f8fafc;
  --surface: #ffffff;
  --panel: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --primary: #0284c7;
  --primary-hover: #0369a1;
  --success: #16a34a;
  --success-bg: #f0fdf4;
  --success-border: #bbf7d0;
  --warn: #d97706;
  --warn-bg: #fffbeb;
  --accent: #4f46e5;
  --tag: #f1f5f9;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  font-size: 14px;
}}
header {{
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 18px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 20;
}}
.logo {{ font-weight: 700; font-size: 18px; color: var(--text); display: flex; align-items: center; gap: 8px; }}
.logo-badge {{ background: var(--primary); color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
.run-meta {{ color: var(--muted); font-size: 13px; }}
.container {{
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px 32px;
}}
.stats-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}}
.stat-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}}
.stat-val {{ font-size: 26px; font-weight: 700; color: var(--text); }}
.stat-lbl {{ color: var(--muted); font-size: 12px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; margin-top: 2px; }}

.main-layout {{
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 24px;
  align-items: start;
}}
.sidebar {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.sidebar-header {{
  padding: 16px;
  border-bottom: 1px solid var(--border);
  background: #fcfdfe;
}}
.search-input {{
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}}
.search-input:focus {{ border-color: var(--primary); }}
.filter-pills {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 12px;
}}
.pill {{
  background: var(--tag);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 11px;
  cursor: pointer;
  font-weight: 500;
}}
.pill.active {{
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}}
.company-list {{
  max-height: calc(100vh - 270px);
  overflow-y: auto;
}}
.company-item {{
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.1s;
}}
.company-item:hover {{ background: #f8fafc; }}
.company-item.active {{ background: #f0f9ff; border-left: 3px solid var(--primary); }}
.item-title {{ font-weight: 600; font-size: 14px; color: var(--text); }}
.item-sub {{ color: var(--muted); font-size: 12px; margin-top: 2px; }}
.item-badges {{ display: flex; gap: 4px; margin-top: 6px; }}
.badge {{
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}}
.badge-web {{ background: #e0f2fe; color: #0369a1; }}
.badge-fin {{ background: #dcfce7; color: #15803d; }}
.badge-careers {{ background: #fef3c7; color: #b45309; }}
.badge-news {{ background: #f3e8ff; color: #7e22ce; }}

.content-panel {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 28px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}}
.company-header {{
  border-bottom: 1px solid var(--border);
  padding-bottom: 20px;
  margin-bottom: 24px;
}}
.company-header h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 6px; }}
.company-meta {{ color: var(--muted); font-size: 14px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }}

.summary-card {{
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-left: 4px solid var(--primary);
  padding: 18px 22px;
  border-radius: 6px;
  margin-bottom: 24px;
}}
.summary-title {{
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
}}
.summary-text {{
  font-size: 15px;
  line-height: 1.6;
  color: #1e293b;
}}

.actions-bar {{
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}}
.action-btn {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--tag);
  border: 1px solid var(--border);
  padding: 8px 14px;
  border-radius: 6px;
  color: var(--text);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}}
.action-btn:hover {{
  background: var(--surface);
  border-color: var(--primary);
  color: var(--primary);
}}
.action-btn.primary {{
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}}
.action-btn.primary:hover {{ background: var(--primary-hover); }}

.section {{ margin-bottom: 28px; }}
.section-title {{
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.info-card {{
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px 18px;
  background: #fdfdfd;
}}
.info-label {{ font-size: 11px; text-transform: uppercase; color: var(--muted); font-weight: 600; margin-bottom: 4px; }}
.info-value {{ font-size: 14px; font-weight: 600; color: var(--text); }}

table.fin-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}}
table.fin-table th, table.fin-table td {{
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}}
table.fin-table th {{
  background: #f8fafc;
  color: var(--muted);
  font-weight: 600;
  font-size: 12px;
}}
table.fin-table tr:hover td {{ background: #fafafa; }}

details.evidence-box {{
  margin-top: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fafafa;
}}
details.evidence-box summary {{
  padding: 12px 16px;
  font-weight: 600;
  cursor: pointer;
  color: var(--muted);
}}
details.evidence-box .evidence-content {{
  padding: 16px;
  border-top: 1px solid var(--border);
  background: white;
  font-size: 12px;
}}
.evidence-row {{
  padding: 6px 0;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}}
.evidence-row code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 11px; }}
</style>
</head>
<body>

<header>
  <div class="logo">
    <span class="logo-badge">Signalpost</span>
    <span>Company Intelligence Dashboard</span>
  </div>
  <div class="run-meta">
    Run: <strong>{html.escape(run_id)}</strong> · Evaluated: <strong>{len(ui_records)} companies</strong>
  </div>
</header>

<div class="container">
  <div class="stats-grid" id="stats-grid"></div>

  <div class="main-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <input type="text" id="search-input" class="search-input" placeholder="Search company, org nr, city, industry..." />
        <div class="filter-pills" id="filter-pills">
          <button class="pill active" data-filter="all">All</button>
          <button class="pill" data-filter="has-web">Website Verified</button>
          <button class="pill" data-filter="has-careers">Careers Found</button>
          <button class="pill" data-filter="has-news">News Found</button>
          <button class="pill" data-filter="has-fin">Accounts Available</button>
        </div>
      </div>
      <div class="company-list" id="company-list"></div>
    </aside>

    <main class="content-panel" id="detail-panel">
      <p style="color:var(--muted); text-align:center; padding: 60px 0;">Select a company from the list to view its complete verified intelligence profile.</p>
    </main>
  </div>
</div>

<script>
const DATA = {payload_json};
const REPORT = {report_json};

let currentFilter = 'all';
let searchQuery = '';
let selectedOrg = DATA.length ? DATA[0].org : null;

function renderStats() {{
  const total = DATA.length;
  const webCount = DATA.filter(c => !!c.website).length;
  const finCount = DATA.filter(c => c.financials && c.financials.length > 0).length;
  const careersCount = DATA.filter(c => !!c.careers).length;
  const newsCount = DATA.filter(c => !!c.news).length;

  const grid = document.getElementById('stats-grid');
  grid.innerHTML = `
    <div class="stat-card">
      <div class="stat-val">${{total}}</div>
      <div class="stat-lbl">Evaluator Companies</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:var(--primary);">${{webCount}} <span style="font-size:14px;color:var(--muted);">(${{Math.round(webCount/total*100)}}%)</span></div>
      <div class="stat-lbl">Verified Websites</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:var(--success);">${{finCount}} <span style="font-size:14px;color:var(--muted);">(${{Math.round(finCount/total*100)}}%)</span></div>
      <div class="stat-lbl">Annual Accounts</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:#b45309;">${{careersCount}}</div>
      <div class="stat-lbl">Careers Discovered</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:#7e22ce;">${{newsCount}}</div>
      <div class="stat-lbl">News / Updates</div>
    </div>
  `;
}}

function getFilteredData() {{
  return DATA.filter(item => {{
    if (currentFilter === 'has-web' && !item.website) return false;
    if (currentFilter === 'has-careers' && !item.careers) return false;
    if (currentFilter === 'has-news' && !item.news) return false;
    if (currentFilter === 'has-fin' && (!item.financials || !item.financials.length)) return false;

    if (searchQuery) {{
      const q = searchQuery.toLowerCase();
      const match = (item.name || '').toLowerCase().includes(q)
        || (item.org || '').includes(q)
        || (item.municipality || '').toLowerCase().includes(q)
        || (item.industry || '').toLowerCase().includes(q)
        || (item.summary || '').toLowerCase().includes(q);
      if (!match) return false;
    }}
    return true;
  }});
}}

function renderList() {{
  const listEl = document.getElementById('company-list');
  const filtered = getFilteredData();
  
  if (!filtered.length) {{
    listEl.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--muted);">No matching companies found.</div>';
    return;
  }}

  listEl.innerHTML = filtered.map(item => `
    <div class="company-item ${{item.org === selectedOrg ? 'active' : ''}}" onclick="selectCompany('${{item.org}}')">
      <div class="item-title">${{escapeHtml(item.name)}}</div>
      <div class="item-sub">${{item.org}} · ${{escapeHtml(item.form)}} · ${{escapeHtml(item.municipality || 'Norway')}}</div>
      <div class="item-badges">
        ${{item.website ? '<span class="badge badge-web">Website</span>' : ''}}
        ${{item.financials && item.financials.length ? '<span class="badge badge-fin">Accounts</span>' : ''}}
        ${{item.careers ? '<span class="badge badge-careers">Careers</span>' : ''}}
        ${{item.news ? '<span class="badge badge-news">News</span>' : ''}}
      </div>
    </div>
  `).join('');
}}

function selectCompany(org) {{
  selectedOrg = org;
  renderList();
  renderDetail();
}}

function formatMoney(val, curr) {{
  if (val == null) return '—';
  return new Intl.NumberFormat('nb-NO').format(val) + ' ' + (curr || 'NOK');
}}

function escapeHtml(str) {{
  return String(str || '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}

function renderDetail() {{
  const panel = document.getElementById('detail-panel');
  const comp = DATA.find(c => c.org === selectedOrg);
  if (!comp) return;

  const ceo = (comp.roles || []).find(r => (r.role_code === 'DAGL' || (r.role || '').toLowerCase().includes('daglig leder')));
  const chair = (comp.roles || []).find(r => (r.role_code === 'LEDE' || (r.role || '').toLowerCase().includes('leder')));

  panel.innerHTML = `
    <div class="company-header">
      <h1>${{escapeHtml(comp.name)}}</h1>
      <div class="company-meta">
        <span>Org nr: <strong>${{comp.org}}</strong></span>
        <span>Legal form: <strong>${{escapeHtml(comp.form)}}</strong></span>
        <span>Municipality: <strong>${{escapeHtml(comp.municipality || 'Not specified')}}</strong></span>
        <span>Employees: <strong>${{comp.employees ?? 'Not reported'}}</strong></span>
      </div>
    </div>

    ${{comp.summary ? `
    <div class="summary-card">
      <div class="summary-title">Executive Brief & Synthesized Intelligence</div>
      <div class="summary-text">${{escapeHtml(comp.summary)}}</div>
    </div>
    ` : ''}}

    <div class="actions-bar">
      ${{comp.website ? `<a href="${{escapeHtml(comp.website)}}" target="_blank" rel="noreferrer" class="action-btn primary">🌐 Official Website ↗</a>` : '<span class="action-btn" style="color:var(--muted);opacity:0.7;">No Website Established</span>'}}
      ${{comp.careers ? `<a href="${{escapeHtml(comp.careers.url)}}" target="_blank" rel="noreferrer" class="action-btn">💼 Careers / Openings (${{escapeHtml(comp.careers.title)}}) ↗</a>` : ''}}
      ${{comp.news ? `<a href="${{escapeHtml(comp.news.url)}}" target="_blank" rel="noreferrer" class="action-btn">📰 News / Updates (${{escapeHtml(comp.news.title)}}) ↗</a>` : ''}}
      ${{(comp.social || []).map(s => `<a href="${{escapeHtml(s.url)}}" target="_blank" rel="noreferrer" class="action-btn">🔗 ${{escapeHtml(s.platform.toUpperCase())}} ↗</a>`).join('')}}
    </div>

    <div class="section">
      <div class="section-title">Registration & Leadership</div>
      <div class="grid-2">
        <div class="info-card">
          <div class="info-label">Industry Classification</div>
          <div class="info-value">${{comp.industry_code ? comp.industry_code + ' - ' : ''}}${{escapeHtml(comp.industry || 'Not reported')}}</div>
        </div>
        <div class="info-card">
          <div class="info-label">Registered Leadership</div>
          <div class="info-value">
            ${{ceo ? `<div>CEO: ${{escapeHtml(ceo.name || 'Unnamed')}}</div>` : ''}}
            ${{chair && chair !== ceo ? `<div>Chair: ${{escapeHtml(chair.name || 'Unnamed')}}</div>` : ''}}
            ${{!ceo && !chair ? '<div>No public role holder record</div>' : ''}}
          </div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Annual Accounts History</div>
      ${{comp.financials && comp.financials.length ? `
      <table class="fin-table">
        <thead>
          <tr>
            <th>Period</th>
            <th>Revenue</th>
            <th>Operating Result</th>
            <th>Annual Result</th>
            <th>Total Assets</th>
            <th>Debt</th>
            <th>Equity</th>
          </tr>
        </thead>
        <tbody>
          ${{comp.financials.map(f => `
            <tr>
              <td><strong>${{f.period?.fraDato || ''}} – ${{f.period?.tilDato || ''}}</strong></td>
              <td>${{formatMoney(f.revenue, f.currency)}}</td>
              <td>${{formatMoney(f.operating_result, f.currency)}}</td>
              <td style="font-weight:600;color:${{(f.annual_result || 0) >= 0 ? 'var(--success)' : '#dc2626'}};">${{formatMoney(f.annual_result, f.currency)}}</td>
              <td>${{formatMoney(f.assets, f.currency)}}</td>
              <td>${{formatMoney(f.debt, f.currency)}}</td>
              <td>${{formatMoney(f.equity, f.currency)}}</td>
            </tr>
          `).join('')}}
        </tbody>
      </table>
      ` : '<p style="color:var(--muted); font-style:italic;">No normalized multi-year financial statements returned for this entity.</p>'}}
    </div>

    <details class="evidence-box">
      <summary>Inspect Source Evidence & Cryptographic Hashes (${{(comp.evidence || []).length}} records)</summary>
      <div class="evidence-content">
        ${{(comp.evidence || []).map(e => `
          <div class="evidence-row">
            <div>
              <strong>${{escapeHtml(e.field || e.source_class || 'source')}}</strong>
              <div style="color:var(--muted);">${{escapeHtml(e.source_url || '')}} · Retrieved: ${{e.retrieved_at || '—'}}</div>
            </div>
            <div>
              <code>${{e.content_sha256 ? e.content_sha256.substring(0, 16) + '...' : 'none'}}</code>
            </div>
          </div>
        `).join('')}}
      </div>
    </details>
  `;
}}

document.getElementById('search-input').addEventListener('input', e => {{
  searchQuery = e.target.value.trim();
  renderList();
}});

document.querySelectorAll('#filter-pills .pill').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('#filter-pills .pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    renderList();
  }});
}});

renderStats();
renderList();
if (DATA.length) {{
  selectCompany(DATA[0].org);
}}
</script>
</body>
</html>
"""
    out.write_text(html_content, encoding="utf-8")
    return out

