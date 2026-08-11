from app.models.cube import Cube
from app.models.cube_instance import CubeInstance
from app.models.mtgo_account import MtgoAccount
from app.services.mtgo.mtgo_account_resolver import resolve_mtgo_account


def test_resolve_returns_account_id_and_username(db_session):
    account = MtgoAccount(name="TheLegionCube", mtgo_username="TheLegionCube")
    cube = Cube(name="Vintage Cube", cubecobra_url="https://cubecobra.com/cube/overview/vintage")
    db_session.add_all([account, cube])
    db_session.commit()

    instance = CubeInstance(cube_id=cube.id, mtgo_account_id=account.id, label="Main")
    db_session.add(instance)
    db_session.commit()

    account_id, username = resolve_mtgo_account(db_session, instance.id)

    assert account_id == account.id
    assert username == "TheLegionCube"


def test_resolve_returns_none_none_for_none_instance(db_session):
    assert resolve_mtgo_account(db_session, None) == (None, None)


def test_resolve_returns_none_none_for_missing_instance(db_session):
    assert resolve_mtgo_account(db_session, 999) == (None, None)
