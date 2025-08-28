import pytest

def test_broker_kpis(client, base_url, auth_headers):
    r = client.get(f"{base_url}/analytics/broker-kpis", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    for k in ["followUpAtrasado","leadsEmTratativa","leadsPrimeiroAtendimento","totalLeads"]:
        assert k in body

def test_productivity(client, base_url, auth_headers):
    r = client.get(f"{base_url}/analytics/productivity?startDate=2025-01-01&endDate=2025-12-31", headers=auth_headers)
    assert r.status_code == 200
    assert "series" in r.json()

def test_funnel(client, base_url, auth_headers):
    r = client.get(f"{base_url}/analytics/funnel?startDate=2025-01-01&endDate=2025-12-31", headers=auth_headers)
    assert r.status_code == 200
    assert "stages" in r.json()
