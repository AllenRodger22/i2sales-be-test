import pytest
from conftest import rand_phone, rand_name

@pytest.mark.destructive
def test_clients_crud_flow(client, base_url, auth_headers):
    # Create
    payload = {
        "name": rand_name(),
        "phone": rand_phone(),
        "source": "pytest",
        "status": "Primeiro Atendimento",
        "followUpState": "Sem Follow Up",
        "product": "Apartamento",
        "propertyValue": 123456.78
    }
    r = client.post(f"{base_url}/clients", headers=auth_headers, json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    cid = created["id"]

    # List (search by q)
    r = client.get(f"{base_url}/clients?q=pytest", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # Get by ID (should include interactions, newest first)
    r = client.get(f"{base_url}/clients/{cid}", headers=auth_headers)
    assert r.status_code == 200
    detail = r.json()
    assert "interactions" in detail
    assert detail["interactions"][0]["type"] == "CLIENT_CREATED"

    # Update
    r = client.put(f"{base_url}/clients/{cid}", headers=auth_headers, json={"status": "Em Tratativa"})
    assert r.status_code == 200
    assert r.json()["status"] == "Em Tratativa"

    # Export CSV
    r = client.get(f"{base_url}/clients/export", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type","")

    # Delete (requires ADMIN)
    r = client.delete(f"{base_url}/clients/{cid}", headers=auth_headers)
    assert r.status_code in (204, 200)
