from datetime import datetime

from scripts.backup_db import backup_filename, select_backups_to_prune


def test_backup_filename_formats_timestamp():
    now = datetime(2026, 7, 28, 14, 30, 0)

    assert backup_filename(now) == "cubebot_20260728_143000.db"


def test_backup_filename_pads_single_digit_components():
    now = datetime(2026, 1, 2, 3, 4, 5)

    assert backup_filename(now) == "cubebot_20260102_030405.db"


def test_select_backups_to_prune_keeps_all_when_under_limit():
    filenames = [
        "cubebot_20260101_000000.db",
        "cubebot_20260102_000000.db",
    ]

    assert select_backups_to_prune(filenames, keep=30) == []


def test_select_backups_to_prune_keeps_exactly_the_limit():
    filenames = [
        "cubebot_20260101_000000.db",
        "cubebot_20260102_000000.db",
        "cubebot_20260103_000000.db",
    ]

    assert select_backups_to_prune(filenames, keep=3) == []


def test_select_backups_to_prune_removes_oldest_beyond_limit():
    filenames = [
        "cubebot_20260101_000000.db",
        "cubebot_20260102_000000.db",
        "cubebot_20260103_000000.db",
        "cubebot_20260104_000000.db",
    ]

    assert select_backups_to_prune(filenames, keep=2) == [
        "cubebot_20260101_000000.db",
        "cubebot_20260102_000000.db",
    ]


def test_select_backups_to_prune_ignores_input_order():
    filenames = [
        "cubebot_20260103_000000.db",
        "cubebot_20260101_000000.db",
        "cubebot_20260104_000000.db",
        "cubebot_20260102_000000.db",
    ]

    assert select_backups_to_prune(filenames, keep=1) == [
        "cubebot_20260101_000000.db",
        "cubebot_20260102_000000.db",
        "cubebot_20260103_000000.db",
    ]


def test_select_backups_to_prune_with_zero_keep_removes_all():
    filenames = [
        "cubebot_20260101_000000.db",
        "cubebot_20260102_000000.db",
    ]

    assert select_backups_to_prune(filenames, keep=0) == filenames


def test_select_backups_to_prune_empty_list_returns_empty():
    assert select_backups_to_prune([], keep=30) == []


def test_select_backups_to_prune_negative_keep_treated_as_zero():
    filenames = ["cubebot_20260101_000000.db"]

    assert select_backups_to_prune(filenames, keep=-5) == filenames
