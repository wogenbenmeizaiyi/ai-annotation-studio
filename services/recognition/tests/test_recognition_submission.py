from unittest.mock import Mock

import pytest

import recognition_submission
from core.schemas.task import RecognitionRecordedSubmitRequest


def _request(detection_type: int = 1) -> RecognitionRecordedSubmitRequest:
    return RecognitionRecordedSubmitRequest(
        detection_type=detection_type,
        text="model-or-prompt",
        images=["https://images.example.test/example.jpg"],
    )


def test_invalid_type_is_rejected_before_record_is_added() -> None:
    db = Mock()

    with pytest.raises(ValueError):
        recognition_submission.submit_recorded_recognition(_request(99), db)

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_broker_failure_marks_saved_record_failed(monkeypatch) -> None:
    db = Mock()
    monkeypatch.setattr(
        recognition_submission,
        "submit_recognition_task",
        Mock(side_effect=ConnectionError("broker unavailable")),
    )

    with pytest.raises(recognition_submission.RecognitionTaskPublishError):
        recognition_submission.submit_recorded_recognition(_request(), db)

    record = db.add.call_args.args[0]
    assert record.status == "failed"
    assert "broker unavailable" in record.last_callback_error
    assert db.commit.call_count == 2


def test_successful_publish_keeps_record_pending(monkeypatch) -> None:
    db = Mock()
    submit = Mock()
    monkeypatch.setattr(recognition_submission, "submit_recognition_task", submit)

    task_id = recognition_submission.submit_recorded_recognition(_request(4), db)

    record = db.add.call_args.args[0]
    assert record.task_id == task_id
    assert record.status == "pending"
    submit.assert_called_once()
    assert submit.call_args.kwargs == {"task_id": task_id}


def test_broker_failure_retries_failed_state_with_independent_session(
    monkeypatch,
) -> None:
    db = Mock()
    db.commit.side_effect = [None, RuntimeError("connection lost")]
    retry_record = Mock()
    retry_db = Mock()
    retry_db.query.return_value.filter.return_value.one_or_none.return_value = retry_record
    monkeypatch.setattr(recognition_submission, "SessionLocal", Mock(return_value=retry_db))
    monkeypatch.setattr(
        recognition_submission,
        "submit_recognition_task",
        Mock(side_effect=ConnectionError("broker unavailable")),
    )

    with pytest.raises(recognition_submission.RecognitionTaskPublishError):
        recognition_submission.submit_recorded_recognition(_request(), db)

    assert retry_record.status == "failed"
    assert "broker unavailable" in retry_record.last_callback_error
    retry_db.commit.assert_called_once()
    retry_db.close.assert_called_once()


def test_broker_failure_still_raises_publish_error_when_db_fallback_is_down(
    monkeypatch,
) -> None:
    db = Mock()
    db.commit.side_effect = [None, RuntimeError("connection lost")]
    db.rollback.side_effect = RuntimeError("rollback unavailable")
    monkeypatch.setattr(
        recognition_submission,
        "SessionLocal",
        Mock(side_effect=RuntimeError("database unavailable")),
    )
    monkeypatch.setattr(
        recognition_submission,
        "submit_recognition_task",
        Mock(side_effect=ConnectionError("broker unavailable")),
    )

    with pytest.raises(recognition_submission.RecognitionTaskPublishError):
        recognition_submission.submit_recorded_recognition(_request(), db)
