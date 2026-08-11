from app.models.cube import Cube
from app.models.mtgo_account import MtgoAccount


def _make_cube(db_session, name="Vintage Cube") -> Cube:
    cube = Cube(
        name=name,
        cubecobra_url=f"https://cubecobra.com/cube/overview/{name.lower().replace(' ', '-')}",
    )
    db_session.add(cube)
    db_session.commit()
    db_session.refresh(cube)
    return cube


def _make_account(db_session, name="TheLegionCube") -> MtgoAccount:
    account = MtgoAccount(name=name, mtgo_username=name)
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_create_cube_instance(client, db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)

    response = client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account.id, "label": "Main"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cube_id"] == cube.id
    assert data["mtgo_account_id"] == account.id
    assert data["label"] == "Main"
    assert data["active"] is True


def test_create_cube_instance_rejects_duplicate_label_on_same_account(client, db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account.id, "label": "Main"},
    )

    response = client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account.id, "label": "Main"},
    )

    assert response.status_code == 409


def test_list_cube_instances_filtered_by_account(client, db_session):
    cube = _make_cube(db_session)
    account_a = _make_account(db_session, "TheLegionCube")
    account_b = _make_account(db_session, "FruitDuChene")
    client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account_a.id, "label": "Main"},
    )
    client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account_b.id, "label": "Main"},
    )

    response = client.get(f"/mtgo/cube-instances/?mtgo_account_id={account_a.id}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["mtgo_account_id"] == account_a.id


def test_list_cube_instances_returns_all_without_filter(client, db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account.id, "label": "A"},
    )
    client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account.id, "label": "B"},
    )

    response = client.get("/mtgo/cube-instances/")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_cube_instance_404s_for_missing(client):
    response = client.get("/mtgo/cube-instances/999")

    assert response.status_code == 404


def test_set_cube_instance_active(client, db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    created = client.post(
        "/mtgo/cube-instances/",
        json={"cube_id": cube.id, "mtgo_account_id": account.id, "label": "Main"},
    ).json()

    response = client.patch(
        f"/mtgo/cube-instances/{created['id']}/active",
        json={"active": False},
    )

    assert response.status_code == 200
    assert response.json()["active"] is False
