from app.services.mtgo.mtgo_account_service import MtgoAccountService


def test_create_account(db_session):
    service = MtgoAccountService(db_session)

    account = service.create("TheLegionCube", "TheLegionCube")

    assert account.id is not None
    assert account.name == "TheLegionCube"
    assert account.mtgo_username == "TheLegionCube"
    assert account.active is True


def test_get_returns_none_for_missing_account(db_session):
    service = MtgoAccountService(db_session)

    assert service.get(999) is None


def test_get_by_username(db_session):
    service = MtgoAccountService(db_session)
    created = service.create("TheLegionCube", "TheLegionCube")

    found = service.get_by_username("TheLegionCube")

    assert found.id == created.id


def test_get_by_username_returns_none_when_not_found(db_session):
    service = MtgoAccountService(db_session)

    assert service.get_by_username("NoSuchAccount") is None


def test_list_all_includes_inactive_accounts(db_session):
    service = MtgoAccountService(db_session)
    active_account = service.create("TheLegionCube", "TheLegionCube")
    inactive_account = service.create("RetiredAccount", "RetiredAccount")
    service.set_active(inactive_account, False)

    result = service.list_all()

    assert [a.id for a in result] == [active_account.id, inactive_account.id]


def test_list_active_excludes_inactive_accounts(db_session):
    service = MtgoAccountService(db_session)
    active_account = service.create("TheLegionCube", "TheLegionCube")
    inactive_account = service.create("RetiredAccount", "RetiredAccount")
    service.set_active(inactive_account, False)

    result = service.list_active()

    assert [a.id for a in result] == [active_account.id]


def test_set_active_toggles_flag(db_session):
    service = MtgoAccountService(db_session)
    account = service.create("TheLegionCube", "TheLegionCube")

    service.set_active(account, False)
    assert account.active is False

    service.set_active(account, True)
    assert account.active is True
