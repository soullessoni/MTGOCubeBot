import json


def build_job_argv(
        job_type: str,
        session_id: int | None = None,
        mtgo_username: str | None = None,
        params: dict | None = None,
        job_id: int | None = None,
) -> list[str]:
    """Build the `python -m mtgo.<script> <args>` argv for a job type.
    Shared by the trigger use cases (building argv for a new job) and
    the retry use case (rebuilding the identical argv from a stored
    job's fields) so both stay in sync."""
    if job_type == "GIVE":
        if session_id is None:
            raise ValueError("GIVE jobs require session_id")

        return ["-m", "mtgo.prepare_session_binders", str(session_id)]

    if job_type == "RETURN":
        if session_id is None or not mtgo_username:
            raise ValueError("RETURN jobs require session_id and mtgo_username")

        return ["-m", "mtgo.process_session_returns", str(session_id), mtgo_username]

    if job_type == "INTEGRITY_CHECK":
        return ["-m", "mtgo.cube_integrity_check"]

    if job_type == "GIVE_BACK":
        if not mtgo_username or not params or not params.get("cards"):
            raise ValueError("GIVE_BACK jobs require mtgo_username and params.cards")

        if job_id is None:
            raise ValueError("GIVE_BACK jobs require job_id")

        return [
            "-m", "mtgo.give_back_excess_cards",
            mtgo_username,
            json.dumps(params["cards"]),
            str(job_id),
        ]

    raise ValueError(f"Unknown job_type: {job_type!r}")
