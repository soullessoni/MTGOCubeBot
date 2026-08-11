import pytest
from sqlalchemy.exc import IntegrityError

from app.models.cube import Cube
from app.models.mtgo_account import MtgoAccount
from app.services.cube.cube_instance_service import CubeInstanceService


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
    account = MtgoAccount(
        name=name,
        mtgo_username=name,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_create_instance(db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    service = CubeInstanceService(db_session)

    instance = service.create(cube.id, account.id, label="Instance A")

    assert instance.id is not None
    assert instance.cube_id == cube.id
    assert instance.mtgo_account_id == account.id
    assert instance.label == "Instance A"
    assert instance.active is True


def test_different_accounts_can_each_host_a_different_cube(db_session):
    cube_a = _make_cube(db_session, "Vintage Cube")
    cube_b = _make_cube(db_session, "Legacy Cube")
    account_a = _make_account(db_session, "TheLegionCube")
    account_b = _make_account(db_session, "FruitDuChene")
    service = CubeInstanceService(db_session)

    service.create(cube_a.id, account_a.id, label="Main")
    service.create(cube_b.id, account_b.id, label="Main")

    assert {i.cube_id for i in service.list_for_account(account_a.id)} == {cube_a.id}
    assert {i.cube_id for i in service.list_for_account(account_b.id)} == {cube_b.id}


def test_one_account_can_host_several_different_cubes(db_session):
    cube_a = _make_cube(db_session, "Vintage Cube")
    cube_b = _make_cube(db_session, "Legacy Cube")
    account = _make_account(db_session)
    service = CubeInstanceService(db_session)

    service.create(cube_a.id, account.id, label="Vintage")
    service.create(cube_b.id, account.id, label="Legacy")

    result = service.list_for_account(account.id)

    assert {i.cube_id for i in result} == {cube_a.id, cube_b.id}


def test_one_account_can_host_several_instances_of_the_same_cube(db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    service = CubeInstanceService(db_session)

    first = service.create(cube.id, account.id, label="Instance A")
    second = service.create(cube.id, account.id, label="Instance B")

    result = service.list_for_account(account.id)

    assert {i.id for i in result} == {first.id, second.id}
    assert all(i.cube_id == cube.id for i in result)


def test_duplicate_label_on_same_account_is_rejected(db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    service = CubeInstanceService(db_session)

    service.create(cube.id, account.id, label="Instance A")

    with pytest.raises(IntegrityError):
        service.create(cube.id, account.id, label="Instance A")


def test_same_label_allowed_on_different_accounts(db_session):
    cube = _make_cube(db_session)
    account_a = _make_account(db_session, "TheLegionCube")
    account_b = _make_account(db_session, "FruitDuChene")
    service = CubeInstanceService(db_session)

    service.create(cube.id, account_a.id, label="Instance A")
    service.create(cube.id, account_b.id, label="Instance A")

    assert len(service.list_for_account(account_a.id)) == 1
    assert len(service.list_for_account(account_b.id)) == 1


def test_list_for_cube_returns_instances_across_accounts(db_session):
    cube = _make_cube(db_session)
    account_a = _make_account(db_session, "TheLegionCube")
    account_b = _make_account(db_session, "FruitDuChene")
    service = CubeInstanceService(db_session)

    service.create(cube.id, account_a.id, label="Main")
    service.create(cube.id, account_b.id, label="Main")

    result = service.list_for_cube(cube.id)

    assert {i.mtgo_account_id for i in result} == {account_a.id, account_b.id}


def test_get_returns_none_for_missing_instance(db_session):
    service = CubeInstanceService(db_session)

    assert service.get(999) is None


def test_set_active_toggles_flag(db_session):
    cube = _make_cube(db_session)
    account = _make_account(db_session)
    service = CubeInstanceService(db_session)
    instance = service.create(cube.id, account.id, label="Instance A")

    service.set_active(instance, False)
    assert instance.active is False

    service.set_active(instance, True)
    assert instance.active is True
