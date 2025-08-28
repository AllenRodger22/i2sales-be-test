import pytest

@pytest.mark.smoke
def test_health(client, base_url):
    r = client.get(f"{base_url}/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"

@pytest.mark.smoke
def test_me(client, base_url, auth_headers):
    r = client.get(f"{base_url}/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert "id" in r.json()
    assert "role" in r.json()
