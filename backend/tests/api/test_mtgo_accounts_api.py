def test_create_account(client):
    response = client.post(
        "/mtgo/accounts/",
        json={"name": "TheLegionCube", "mtgo_username": "TheLegionCube"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TheLegionCube"
    assert data["mtgo_username"] == "TheLegionCube"
    assert data["active"] is True


def test_create_account_rejects_duplicate_username(client):
    client.post(
        "/mtgo/accounts/",
        json={"name": "TheLegionCube", "mtgo_username": "TheLegionCube"},
    )

    response = client.post(
        "/mtgo/accounts/",
        json={"name": "Duplicate", "mtgo_username": "TheLegionCube"},
    )

    assert response.status_code == 409


def test_list_accounts(client):
    client.post("/mtgo/accounts/", json={"name": "A", "mtgo_username": "A"})
    client.post("/mtgo/accounts/", json={"name": "B", "mtgo_username": "B"})

    response = client.get("/mtgo/accounts/")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_accounts_active_only(client):
    created = client.post("/mtgo/accounts/", json={"name": "A", "mtgo_username": "A"}).json()
    client.post("/mtgo/accounts/", json={"name": "B", "mtgo_username": "B"})
    client.patch(f"/mtgo/accounts/{created['id']}/active", json={"active": False})

    response = client.get("/mtgo/accounts/?active_only=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["mtgo_username"] == "B"


def test_get_account(client):
    created = client.post("/mtgo/accounts/", json={"name": "A", "mtgo_username": "A"}).json()

    response = client.get(f"/mtgo/accounts/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_account_404s_for_missing(client):
    response = client.get("/mtgo/accounts/999")

    assert response.status_code == 404


def test_set_account_active(client):
    created = client.post("/mtgo/accounts/", json={"name": "A", "mtgo_username": "A"}).json()

    response = client.patch(f"/mtgo/accounts/{created['id']}/active", json={"active": False})

    assert response.status_code == 200
    assert response.json()["active"] is False


def test_set_account_active_404s_for_missing(client):
    response = client.patch("/mtgo/accounts/999/active", json={"active": False})

    assert response.status_code == 404
