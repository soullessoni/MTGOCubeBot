import json

from app.services.mtgo.mtgo_job_runner_service import parse_job_output


def test_clean_success_parses_trailing_json():
    stdout = (
        "Retrieving 3 card(s) from 'FruitDuChene'\n"
        "Bot confirmed.\n"
        + json.dumps({"ok": True, "returned_count": 3})
    )

    status, result, error_message = parse_job_output(0, stdout)

    assert status == "SUCCEEDED"
    assert result == {"ok": True, "returned_count": 3}
    assert error_message is None


def test_success_with_reported_discrepancy_is_still_succeeded():
    result_payload = {
        "ok": False,
        "reconciliation": {"still_owed": {"Mulldrifter": 1}, "to_give_back": {}},
    }
    stdout = "some log line\n" + json.dumps(result_payload)

    status, result, error_message = parse_job_output(0, stdout)

    assert status == "SUCCEEDED"
    assert result == result_payload
    assert error_message is None


def test_nonzero_exit_with_error_json_is_failed():
    stdout = "MTGO window not found.\n" + json.dumps({"ok": False, "error": "MTGO window not found."})

    status, result, error_message = parse_job_output(1, stdout)

    assert status == "FAILED"
    assert result == {"ok": False, "error": "MTGO window not found."}
    assert error_message == "MTGO window not found."


def test_nonzero_exit_with_no_parseable_json_falls_back_to_log_tail():
    stdout = "Traceback (most recent call last):\nsome real crash\n"

    status, result, error_message = parse_job_output(1, stdout)

    assert status == "FAILED"
    assert result is None
    assert "some real crash" in error_message


def test_zero_exit_but_no_json_at_all_is_failed():
    stdout = "did something but forgot to print a summary\n"

    status, result, error_message = parse_job_output(0, stdout)

    assert status == "FAILED"
    assert result is None
    assert error_message is not None


def test_empty_stdout_with_nonzero_exit_reports_exit_code():
    status, result, error_message = parse_job_output(1, "")

    assert status == "FAILED"
    assert result is None
    assert "1" in error_message


def test_ignores_non_json_lines_and_finds_json_further_up_if_trailing_line_is_blank():
    stdout = json.dumps({"ok": True, "value": 42}) + "\n\n"

    status, result, error_message = parse_job_output(0, stdout)

    assert status == "SUCCEEDED"
    assert result == {"ok": True, "value": 42}


def test_nonzero_exit_with_per_player_failed_dict_keeps_structured_result():
    # prepare_session_binders.py's shape: no top-level "error" string,
    # just a per-player "failed" dict — this must not be discarded in
    # favor of a raw log tail, or a Discord-bot-side consumer has no
    # way to know which player's give failed.
    result_payload = {
        "ok": False,
        "given": {},
        "not_taken": {},
        "deposits_collected": {},
        "failed": {"FruitDuChene": "Could only pull 2/5 deposit ticket(s)"},
        "skipped_no_username": [],
    }
    stdout = "some log line\n" + json.dumps(result_payload)

    status, result, error_message = parse_job_output(1, stdout)

    assert status == "FAILED"
    assert result == result_payload
    assert "FruitDuChene" in error_message
    assert "Could only pull 2/5 deposit ticket(s)" in error_message


def test_nonzero_exit_with_ok_false_and_no_failed_dict_still_keeps_result():
    result_payload = {"ok": False}
    stdout = json.dumps(result_payload)

    status, result, error_message = parse_job_output(1, stdout)

    assert status == "FAILED"
    assert result == result_payload
    assert error_message is not None
