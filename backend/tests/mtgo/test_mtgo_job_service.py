from app.services.mtgo.mtgo_job_service import MtgoJobService


def test_create_sets_pending_status_and_defaults(db_session):
    service = MtgoJobService(db_session)

    job = service.create(
        job_type="RETURN",
        session_id=7,
        mtgo_username="FruitDuChene",
    )

    assert job.id is not None
    assert job.job_type == "RETURN"
    assert job.status == "PENDING"
    assert job.session_id == 7
    assert job.mtgo_username == "FruitDuChene"
    assert job.params is None
    assert job.result is None
    assert job.log_output == ""


def test_create_stores_params_requested_by_and_retry_of(db_session):
    service = MtgoJobService(db_session)

    original = service.create(job_type="RETURN", session_id=7, mtgo_username="FruitDuChene")
    retry = service.create(
        job_type="RETURN",
        session_id=7,
        mtgo_username="FruitDuChene",
        params={"cards": {"Mulldrifter": 1}},
        requested_by="discord:123",
        retry_of_job_id=original.id,
    )

    assert retry.params == {"cards": {"Mulldrifter": 1}}
    assert retry.requested_by == "discord:123"
    assert retry.retry_of_job_id == original.id


def test_get_returns_none_for_missing_job(db_session):
    service = MtgoJobService(db_session)

    assert service.get(999) is None


def test_get_returns_the_matching_job(db_session):
    service = MtgoJobService(db_session)
    job = service.create(job_type="GIVE", session_id=3)

    fetched = service.get(job.id)

    assert fetched is not None
    assert fetched.id == job.id


def test_list_recent_orders_newest_first_and_respects_limit(db_session):
    service = MtgoJobService(db_session)
    jobs = [service.create(job_type="GIVE", session_id=i) for i in range(5)]

    recent = service.list_recent(limit=3)

    assert [j.id for j in recent] == [jobs[4].id, jobs[3].id, jobs[2].id]


def test_list_recent_filters_by_session_id(db_session):
    service = MtgoJobService(db_session)
    service.create(job_type="GIVE", session_id=1)
    match = service.create(job_type="RETURN", session_id=2)
    service.create(job_type="GIVE", session_id=1)

    recent = service.list_recent(session_id=2)

    assert [j.id for j in recent] == [match.id]
