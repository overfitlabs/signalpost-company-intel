from __future__ import annotations

import base64
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from typing import Any

from bs4 import BeautifulSoup
from .website import normalize_homepage, USER_AGENT


BLOCKED_DISCOVERY_HOSTS = {
    "proff.no", "purehelp.no", "1881.no", "gulesider.no", "firmalisten.no", "companywall.no",
    "firmadatabasen.no", "sokfirma.no", "yra.no", "northdata.com", "nor47business.com",
    "linkedin.com", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com",
    "wikipedia.org", "opencorporates.com", "opencorpdata.com", "eintaxid.com", "b2bhint.com", "brreg.no",
    "dnb.com", "21st.ai", "infobelpro.com", "biztrac.no", "allabolag.se", "eiendomspriser.no",
    "regnskapstall.no", "blomster.no", "api1881.no", "fonecta1881group.no", "hjemmesidehuset.no",
}
GENERIC_NAME_TOKENS = {"as", "asa", "ans", "da", "enk", "sa", "nuf", "company", "norge", "norway", "gruppen", "group"}


def build_company_search_query(profile: dict[str, Any]) -> str:
    name = " ".join(str(profile.get("name") or "").split())
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    municipality = " ".join(str(profile.get("municipality") or "").split())
    if not name or not org:
        raise ValueError("Company discovery requires a legal name and organisation number")
    location = f" {municipality}" if municipality else ""
    return f'"{name}" {org}{location}'


def parse_brave_web_results(payload: dict[str, Any], *, query: str) -> list[dict[str, Any]]:
    results = (payload.get("web") or {}).get("results") or []
    parsed = []
    for rank, result in enumerate(results, start=1):
        if not isinstance(result, dict) or not result.get("url"):
            continue
        parsed.append({
            "url": result.get("url"),
            "title": result.get("title") or "",
            "snippet": result.get("description") or "",
            "rank": rank,
            "provider": "brave_search_api",
            "query": query,
        })
    return parsed


def _tokens(value: Any) -> list[str]:
    text = str(value or "").translate(str.maketrans({"ø": "o", "å": "a", "æ": "ae", "Ø": "O", "Å": "A", "Æ": "AE"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return [token for token in re.findall(r"[a-z0-9]+", text) if len(token) > 1]


def score_search_candidate(profile: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_homepage(result.get("url"))
    if not normalized:
        return {"status": "rejected", "score": 0.0, "publishable_candidate": False, "reasons": ["invalid HTTP(S) candidate URL"]}
    host = (urllib.parse.urlparse(normalized).hostname or "").casefold().removeprefix("www.")
    if any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_DISCOVERY_HOSTS):
        return {"status": "rejected", "score": 0.0, "publishable_candidate": False, "url": normalized, "host": host, "reasons": ["directory, aggregator, or social host is not a company website candidate"]}

    name_tokens = [token for token in _tokens(profile.get("name")) if token not in GENERIC_NAME_TOKENS]
    title_tokens = _tokens(result.get("title"))
    snippet_tokens = _tokens(result.get("snippet"))
    evidence_tokens = set(title_tokens + snippet_tokens + _tokens(host))
    host_compact = "".join(_tokens(host))
    name_compact = "".join(name_tokens)
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    evidence_digits = re.sub(r"\D", "", f"{result.get('title', '')} {result.get('snippet', '')}")
    municipality_tokens = set(_tokens(profile.get("municipality")))

    org_match = bool(org and org in evidence_digits)
    all_name_tokens = bool(name_tokens and set(name_tokens).issubset(evidence_tokens))
    all_name_tokens_in_title = bool(name_tokens and set(name_tokens).issubset(set(title_tokens)))
    name_in_host = bool(name_compact and name_compact in host_compact)
    any_token_in_host = bool(name_tokens and any(t in host_compact for t in name_tokens))
    municipality_match = bool(municipality_tokens and municipality_tokens <= set(snippet_tokens))
    score = 0.0
    reasons = []
    if org_match:
        score += 0.75
        reasons.append("exact organisation number appears in result evidence")
    if all_name_tokens_in_title:
        score += 0.45
        reasons.append("all distinctive legal-name tokens appear in the result title")
    elif all_name_tokens:
        score += 0.25
        reasons.append("all distinctive legal-name tokens appear across result evidence")
    if name_in_host:
        score += 0.3
        reasons.append("normalized legal name appears in candidate hostname")
    if municipality_match:
        score += 0.1
        reasons.append("registry municipality appears in result snippet")
    score = min(score, 1.0)
    publishable_candidate = score >= 0.75 and name_in_host and (org_match or all_name_tokens_in_title)
    return {
        "status": "accepted_for_crawl" if publishable_candidate else "review" if score >= 0.6 else "rejected",
        "score": score,
        "publishable_candidate": publishable_candidate,
        "url": normalized,
        "host": host,
        "rank": result.get("rank"),
        "provider": result.get("provider"),
        "query": result.get("query"),
        "reasons": reasons or ["insufficient exact-entity evidence"],
        "method": "deterministic_search_candidate_identity_v1",
    }


def choose_search_candidate(profile: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    assessed = [score_search_candidate(profile, result) for result in results]
    assessed.sort(key=lambda item: (-item.get("score", 0.0), item.get("rank") or 10_000, item.get("url") or ""))
    accepted = [item for item in assessed if item.get("publishable_candidate")]
    return {
        "selected": accepted[0] if accepted else None,
        "candidates": assessed,
        "abstained": not accepted,
        "policy": "A search result is only a crawl candidate. Publication still requires fetched-page exact-entity verification.",
    }


def _search_1881(query: str, *, timeout: float = 6.0) -> list[str]:
    url = f"https://www.1881.no/?query={urllib.parse.quote(query)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    candidates: list[str] = []
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            soup = BeautifulSoup(response.read(), "html.parser")
            for a in soup.select("a[href]"):
                href = str(a.get("href") or "").strip()
                text = a.get_text(strip=True)
                if not href.startswith("http"):
                    continue
                parsed = urllib.parse.urlparse(href)
                host = (parsed.hostname or "").lower().removeprefix("www.")
                if any(host == b or host.endswith("." + b) for b in BLOCKED_DISCOVERY_HOSTS):
                    continue
                if text.startswith("www.") or text.startswith("http") or "hjemmeside" in text.lower() or "nettside" in text.lower():
                    clean = f"{parsed.scheme}://{parsed.netloc}/"
                    if clean not in candidates:
                        candidates.append(clean)
    except Exception:
        pass
    return candidates


def _decode_bing_url(href: str) -> str | None:
    match = re.search(r"[?&]u=a1([A-Za-z0-9+/=_-]+)", href)
    if match:
        b64 = match.group(1).replace("-", "+").replace("_", "/")
        pad = "=" * (-len(b64) % 4)
        try:
            return base64.b64decode(b64 + pad).decode("utf-8", errors="ignore")
        except Exception:
            pass
    if href.startswith("http") and "bing.com" not in href:
        return href
    return None


def _search_bing(query: str, *, timeout: float = 6.0, limit: int = 4) -> list[dict[str, Any]]:
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    candidates: list[dict[str, Any]] = []
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            soup = BeautifulSoup(response.read(), "html.parser")
            for li in soup.select("li.b_algo"):
                a = li.select_one("h2 a")
                if not a:
                    continue
                actual_url = _decode_bing_url(str(a.get("href") or ""))
                if not actual_url:
                    continue
                parsed = urllib.parse.urlparse(actual_url)
                host = (parsed.hostname or "").lower().removeprefix("www.")
                if any(host == b or host.endswith("." + b) for b in BLOCKED_DISCOVERY_HOSTS):
                    continue
                title = a.get_text(" ", strip=True)
                snippet_el = li.select_one(".b_caption p, .b_snippet")
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
                clean = f"{parsed.scheme}://{parsed.netloc}/"
                if clean not in [c["url"] for c in candidates]:
                    candidates.append({"url": clean, "title": title, "snippet": snippet, "rank": len(candidates) + 1, "provider": "bing"})
                if len(candidates) >= limit:
                    break
    except Exception:
        pass
    return candidates


def search_company_website_candidates(profile: dict[str, Any], *, timeout: float = 8.0, limit: int = 4) -> list[str]:
    """Search for plausible company website homepage URLs without requiring a paid API key."""
    org = re.sub(r"\D", "", str(profile.get("organisation_number") or ""))
    name = " ".join(str(profile.get("name") or "").split())
    municipality = " ".join(str(profile.get("municipality") or "").split())

    candidates: list[str] = []

    # 1. Check authoritative Norwegian business index (1881.no) by organisation number
    if org:
        for url in _search_1881(org, timeout=timeout):
            if url not in candidates:
                candidates.append(url)
            if len(candidates) >= limit:
                return candidates

    # 2. Check 1881 by exact name if org lookup yielded no candidate
    if not candidates and name:
        for url in _search_1881(name, timeout=timeout):
            if url not in candidates:
                candidates.append(url)
            if len(candidates) >= limit:
                return candidates

    # 3. Optional Brave Search API if key provided in environment
    api_key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if api_key and not candidates:
        try:
            brave_url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(f'\"{name}\" {org}')}&count=5&country=no"
            req = urllib.request.Request(brave_url, headers={"Accept": "application/json", "X-Subscription-Token": api_key, "User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
                for item in parse_brave_web_results(data, query=name):
                    u = normalize_homepage(item.get("url"))
                    if u and u not in candidates:
                        parsed = urllib.parse.urlparse(u)
                        host = (parsed.hostname or "").lower().removeprefix("www.")
                        if not any(host == b or host.endswith("." + b) for b in BLOCKED_DISCOVERY_HOSTS):
                            candidates.append(u)
        except Exception:
            pass

    # 4. Search engine lookup fallback
    if not candidates and name:
        query = f'"{name}" {municipality}' if municipality else f'"{name}"'
        bing_results = _search_bing(query, timeout=timeout, limit=limit)
        for res in bing_results:
            u = res.get("url")
            if u and u not in candidates:
                candidates.append(u)

    return candidates[:limit]
