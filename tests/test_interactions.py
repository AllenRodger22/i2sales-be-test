import pytest
from conftest import rand_phone, rand_name

@pytest.mark.destructive
def test_interaction_status_change_updates_client(client, base_url, auth_headers):
    # create a client first
    payload = {
        "name": rand_name("INT"),
        "phone": rand_phone(),
        "source": "pytest",
        "status": "Primeiro Atendimento",
        "followUpState": "Sem Follow Up"
    }
    r = client.post(f"{base_url}/clients", headers=auth_headers, json=payload)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]

    # create a STATUS_CHANGE interaction
    inter = {
        "clientId": cid,
        "type": "STATUS_CHANGE",
        "observation": "indo para Em Tratativa",
        "explicitNext": "Em Tratativa"
    }
    r = client.post(f"{base_url}/interactions", headers=auth_headers, json=inter)
    assert r.status_code == 201, r.text

    # fetch client and verify status changed
    r = client.get(f"{base_url}/clients/{cid}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "Em Tratativa"

    # cleanup
    client.delete(f"{base_url}/clients/{cid}", headers=auth_headers)
