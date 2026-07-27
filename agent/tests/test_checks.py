from types import SimpleNamespace

from bot.checks import user_is_admin


def make_role(name):
    return SimpleNamespace(name=name)


def make_member(is_administrator=False, role_names=()):
    return SimpleNamespace(
        guild_permissions=SimpleNamespace(administrator=is_administrator),
        roles=[make_role(name) for name in role_names],
    )


def test_administrator_permission_is_admin():
    member = make_member(is_administrator=True)

    assert user_is_admin(member) is True


def test_admin_role_is_admin():
    member = make_member(is_administrator=False, role_names=["Member", "Admin"])

    assert user_is_admin(member) is True


def test_plain_member_is_not_admin():
    member = make_member(is_administrator=False, role_names=["Member"])

    assert user_is_admin(member) is False


def test_dm_user_without_guild_context_is_not_admin():
    dm_user = SimpleNamespace()

    assert user_is_admin(dm_user) is False


def test_role_name_is_case_sensitive_match_only():
    member = make_member(is_administrator=False, role_names=["admin"])

    assert user_is_admin(member) is False
