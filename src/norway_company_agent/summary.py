"""Grounded executive summary synthesis per company."""
from __future__ import annotations

from typing import Any
from .official import financial_sort_key


def generate_company_summary(profile: dict[str, Any]) -> str:
    """Generate a concise, factual executive summary strictly grounded in gathered evidence."""
    name = (profile.get("name") or "The company").strip()
    org = profile.get("organisation_number") or ""
    form = (profile.get("legal_form") or "entity").strip()
    muni = (profile.get("municipality") or "").strip()
    ind = (profile.get("industry_label") or "").strip()
    emp = profile.get("employees")

    sentences: list[str] = []

    # 1. Identity & Location
    id_core = f"{name} ({org})" if org else name
    if form and form.upper() != "ENTITY":
        desc = f"{id_core} is a Norwegian {form}"
    else:
        desc = f"{id_core} is a registered Norwegian enterprise"
    if muni:
        muni_name = muni.title() if muni.isupper() else muni
        desc += f" based in {muni_name}"
    if ind:
        desc += f", operating within {ind.lower()}"
    desc += "."
    sentences.append(desc)

    # 2. Leadership & Employment
    roles_ev = profile.get("evidence", {}).get("roles", {})
    roles_val = (roles_ev.get("value") or {}).get("roles", []) if isinstance(roles_ev, dict) else []
    active_roles = [r for r in roles_val if isinstance(r, dict) and not r.get("inactive")]

    ceo = next((r.get("name") for r in active_roles if r.get("role_code") == "DAGL" or "daglig leder" in (r.get("role") or "").lower()), None)
    chair = next((r.get("name") for r in active_roles if r.get("role_code") == "LEDE" or "styrets leder" in (r.get("role") or "").lower() or (r.get("role") or "").lower() == "leder"), None)

    leaders = []
    if ceo:
        leaders.append(f"Managing Director {ceo}")
    if chair and chair != ceo:
        leaders.append(f"Board Chair {chair}")

    leadership_text = ""
    if leaders:
        leadership_text = f"Led by {' and '.join(leaders)}"

    if emp is not None and emp > 0:
        emp_text = f"{emp} registered employee{'s' if emp != 1 else ''}"
        if leadership_text:
            sentences.append(f"{leadership_text}, the company reports {emp_text}.")
        else:
            sentences.append(f"The company reports {emp_text}.")
    elif emp == 0:
        if leadership_text:
            sentences.append(f"{leadership_text}, with 0 registered employees.")
        else:
            sentences.append("The company has 0 registered employees.")
    elif leadership_text:
        sentences.append(f"{leadership_text}.")

    # 3. Financial Performance
    fin_ev = profile.get("evidence", {}).get("financials", {})
    fin_val = fin_ev.get("value") or {} if isinstance(fin_ev, dict) else {}
    records = fin_val.get("records") or []
    if records:
        latest = max(records, key=financial_sort_key)
        period = latest.get("period") or {}
        year = period.get("tilDato", "")[:4]
        rev = latest.get("revenue")
        profit = latest.get("annual_result")
        op = latest.get("operating_result")
        curr = latest.get("currency") or "NOK"

        fin_parts = []
        if rev is not None:
            fin_parts.append(f"revenue of {rev:,.0f} {curr}".replace(",", " "))
        if op is not None:
            fin_parts.append(f"operating result of {op:,.0f} {curr}".replace(",", " "))
        if profit is not None:
            kind = "net profit" if profit >= 0 else "net loss"
            fin_parts.append(f"{kind} of {abs(profit):,.0f} {curr}".replace(",", " "))

        if fin_parts:
            prefix = f"In {year}, the company recorded " if year else "Latest accounts report "
            sentences.append(prefix + ", ".join(fin_parts) + ".")

    # 4. Digital & Web Footprint
    web_ev = profile.get("evidence", {}).get("website", {})
    web_val = web_ev.get("value") or {} if isinstance(web_ev, dict) else {}
    is_pub = bool((web_val.get("identity_assessment") or {}).get("publishable"))

    if is_pub and web_val.get("final_url"):
        web_parts = [f"Official website: {web_val['final_url']}."]
        desc = web_val.get("description")
        if desc:
            clean_desc = " ".join(desc.split())
            if len(clean_desc) > 140:
                clean_desc = clean_desc[:137] + "..."
            web_parts.append(f"Site description: \"{clean_desc}\".")
        if web_val.get("careers_page"):
            c_url = web_val["careers_page"].get("url")
            web_parts.append(f"Active careers/job section found at {c_url}.")
        if web_val.get("news_page"):
            n_url = web_val["news_page"].get("url")
            web_parts.append(f"News and updates published at {n_url}.")
        socials = web_val.get("social_links") or []
        if socials:
            platforms = ", ".join(sorted(set(s.get("platform", "").capitalize() for s in socials if s.get("platform"))))
            if platforms:
                web_parts.append(f"Verified social profiles on {platforms}.")
        sentences.append(" ".join(web_parts))
    else:
        sentences.append("No verified official website established.")

    return " ".join(sentences)

