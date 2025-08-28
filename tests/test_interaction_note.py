import pytest
from conftest import rand_phone, rand_name

@pytest.mark.destructive
def test_interaction_note_has_no_side_effects(client, base_url, auth_headers):
    # 1) cria um cliente
    payload = {
        "name": rand_name("NOTE"),
        "phone": rand_phone(),
        "source": "pytest",
        "status": "Primeiro Atendimento",
        "followUpState": "Sem Follow Up"
    }
    r = client.post(f"{base_url}/clients", headers=auth_headers, json=payload)
    assert r.status_code == 201, r.text
    created = r.json()
    cid = created["id"]

    # Estado inicial do cliente
    initial_status = created["status"]
    initial_fu = created["followUpState"]

    # 2) cria uma interação só de observação (NOTE)
    inter = {
        "clientId": cid,
        "type": "NOTE",
        "observation": "Apenas uma anotação para histórico."
    }
    r = client.post(f"{base_url}/interactions", headers=auth_headers, json=inter)
    assert r.status_code == 201, r.text

    # 3) busca o cliente e verifica que nada mudou em status/followUpState
    r = client.get(f"{base_url}/clients/{cid}", headers=auth_headers)
    assert r.status_code == 200
    detail = r.json()
    assert detail["status"] == initial_status
    assert detail["followUpState"] == initial_fu

    # 4) interactions devem vir ordenadas DESC (a NOTE deve estar no topo agora)
    assert len(detail.get("interactions", [])) >= 2  # CLIENT_CREATED + NOTE
    assert detail["interactions"][0]["type"] in ("NOTE", "OBSERVATION")
    assert detail["interactions"][1]["type"] == "CLIENT_CREATED"

    # cleanup
    client.delete(f"{base_url}/clients/{cid}", headers=auth_headers)
