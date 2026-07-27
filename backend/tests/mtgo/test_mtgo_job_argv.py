import json

import pytest

from app.services.mtgo.mtgo_job_argv import build_job_argv


def test_give_argv_targets_prepare_session_binders():
    argv = build_job_argv("GIVE", session_id=7)

    assert argv == ["-m", "mtgo.prepare_session_binders", "7"]


def test_return_argv_targets_process_session_returns():
    argv = build_job_argv("RETURN", session_id=7, mtgo_username="FruitDuChene")

    assert argv == ["-m", "mtgo.process_session_returns", "7", "FruitDuChene"]


def test_integrity_check_argv_takes_no_extra_args():
    argv = build_job_argv("INTEGRITY_CHECK")

    assert argv == ["-m", "mtgo.cube_integrity_check"]


def test_give_back_argv_encodes_cards_as_json_and_includes_job_id():
    argv = build_job_argv(
        "GIVE_BACK",
        mtgo_username="FruitDuChene",
        params={"cards": {"Mulldrifter": 2}},
        job_id=42,
    )

    assert argv[:2] == ["-m", "mtgo.give_back_excess_cards"]
    assert argv[2] == "FruitDuChene"
    assert json.loads(argv[3]) == {"Mulldrifter": 2}
    assert argv[4] == "42"


def test_give_requires_session_id():
    with pytest.raises(ValueError):
        build_job_argv("GIVE")


def test_return_requires_mtgo_username():
    with pytest.raises(ValueError):
        build_job_argv("RETURN", session_id=7)


def test_give_back_requires_job_id():
    with pytest.raises(ValueError):
        build_job_argv("GIVE_BACK", mtgo_username="FruitDuChene", params={"cards": {"A": 1}})


def test_unknown_job_type_raises():
    with pytest.raises(ValueError):
        build_job_argv("SOMETHING_ELSE")
