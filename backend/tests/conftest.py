import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.cube import Cube
from app.models.cube_instance import CubeInstance
from app.models.mtgo_account import MtgoAccount


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine
    )

    SessionLocal = sessionmaker(
        bind=engine
    )

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cube_instance_id(db_session) -> int:
    """A ready-to-use CubeInstance id — every LoanSession/InventoryItem
    now requires one, and most tests don't care which, just that it
    exists. Tests that DO care (multi-instance scenarios) build their
    own via CubeInstanceService instead of this fixture."""
    account = MtgoAccount(name="TestAccount", mtgo_username="TestAccount")
    cube = Cube(name="Test Cube", cubecobra_url="https://cubecobra.com/cube/overview/test")
    db_session.add_all([account, cube])
    db_session.commit()

    instance = CubeInstance(cube_id=cube.id, mtgo_account_id=account.id, label="Default")
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)

    return instance.id


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
