import json
import pytest
from bs4 import BeautifulSoup
from norway_company_agent.summary import generate_company_summary
from norway_company_agent.discovery import search_company_website_candidates
from norway_company_agent.viewer import generate_simple_page
from norway_company_agent.batch import terminal_envelope


def test_generate_company_summary_grounded():
    profile = {
        "name": "TEST NORGE AS",
        "organisation_number": "912345678",
        "legal_form": "AS",
        "municipality": "OSLO",
        "industry_label": "Programvareutvikling",
        "employees": 12,
        "evidence": {
            "roles": {
                "value": {
                    "roles": [
                        {"name": "Kari Nordmann", "role_code": "DAGL", "role": "Daglig leder", "inactive": False},
                        {"name": "Ola Nordmann", "role_code": "LEDE", "role": "Styrets leder", "inactive": False},
                    ]
                }
            },
            "financials": {
                "value": {
                    "records": [
                        {
                            "period": {"fraDato": "2024-01-01", "tilDato": "2024-12-31"},
                            "revenue": 15000000.0,
                            "operating_result": 2500000.0,
                            "annual_result": 1950000.0,
                            "currency": "NOK",
                        }
                    ]
                }
            },
            "website": {
                "status": "available",
                "value": {
                    "final_url": "https://testnorge.no/",
                    "description": "Ledende leverandor av programvare",
                    "careers_page": {"url": "https://testnorge.no/karriere", "title": "Bli med pa laget"},
                    "news_page": {"url": "https://testnorge.no/nyheter", "title": "Siste nytt"},
                    "social_links": [{"platform": "linkedin", "url": "https://linkedin.com/company/testnorge"}],
                    "identity_assessment": {"publishable": True},
                },
            },
        },
    }
    summary = generate_company_summary(profile)
    assert "TEST NORGE AS (912345678)" in summary
    assert "Norwegian AS" in summary
    assert "Oslo" in summary
    assert "Managing Director Kari Nordmann" in summary
    assert "Board Chair Ola Nordmann" in summary
    assert "12 registered employees" in summary
    assert "15 000 000 NOK" in summary
    assert "net profit of 1 950 000 NOK" in summary
    assert "https://testnorge.no/" in summary
    assert "https://testnorge.no/karriere" in summary
    assert "https://testnorge.no/nyheter" in summary


def test_generate_simple_page_creates_self_contained_html(tmp_path):
    profile = {
        "name": "EQUINOR ASA",
        "organisation_number": "923609016",
        "legal_form": "ASA",
        "municipality": "STAVANGER",
        "summary": "Equinor ASA is an international energy company.",
        "evidence": {
            "registry": {
                "field": "registry",
                "status": "available",
                "source_url": "https://data.brreg.no",
                "retrieved_at": "2026-01-01T00:00:00Z",
                "content_sha256": "a" * 64,
            }
        },
    }
    envelope = terminal_envelope(
        profile,
        run_id="test-run",
        modules=["registry"],
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:00:05Z",
    )
    assert envelope["summary"] == "Equinor ASA is an international energy company."

    out_file = tmp_path / "index.html"
    res = generate_simple_page([envelope], out_file, run_id="test-run")
    assert res.exists()
    html_text = res.read_text(encoding="utf-8")
    assert "Signalpost" in html_text
    assert "EQUINOR ASA" in html_text
    assert "923609016" in html_text
    assert "Equinor ASA is an international energy company." in html_text


def test_careers_and_news_page_detection_in_website_parsing():
    from norway_company_agent.website import _priority_links
    html = '''
    <html>
      <head><title>Test Company</title></head>
      <body>
        <a href="/om-oss">Om oss</a>
        <a href="/karriere">Ledige stillinger</a>
        <a href="/nyheter/lansering">Siste nyheter</a>
      </body>
    </html>
    '''
    soup = BeautifulSoup(html, "html.parser")
    links = _priority_links("https://example.no/", soup)
    assert any("karriere" in link for link in links)
    assert any("nyheter" in link for link in links)

