from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from core.schemas.task import RecognitionSubmitRequest, TypedRecognitionSubmitRequest
from recognition_submission import RecognitionTaskPublishError
from routes import recognition
from routes.project import project


def _post_endpoint(router, path: str):
    return next(
        route.endpoint
        for route in router.routes
        if route.path == path and "POST" in route.methods
    )


@pytest.mark.asyncio
async def test_generic_recognize_maps_invalid_detection_type_to_400(
    monkeypatch,
) -> None:
    monkeypatch.setattr(recognition, "validate_public_images", Mock())
    endpoint = _post_endpoint(recognition.router, "/recognize")

    with pytest.raises(HTTPException) as error:
        await endpoint(
            RecognitionSubmitRequest(
                detection_type=99,
                images=["https://images.example.test/example.jpg"],
            ),
            Mock(),
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expected_detection_type"),
    [
        ("/recognize/yolo-detection", 1),
        ("/recognize/yolo-segmentation", 2),
        ("/recognize/sam-segmentation", 3),
        ("/recognize/multimodal", 4),
    ],
)
async def test_fixed_recognition_endpoint_submits_its_detection_type(
    monkeypatch,
    path: str,
    expected_detection_type: int,
) -> None:
    submit = Mock(return_value={"status": "pending"})
    monkeypatch.setattr(recognition, "_submit_recorded_request", submit)
    endpoint = _post_endpoint(recognition.router, path)
    db = Mock()

    response = await endpoint(
        TypedRecognitionSubmitRequest(
            text="model-or-prompt",
            images=["https://images.example.test/example.jpg"],
            project_name="route-test",
        ),
        db,
    )

    recorded_request, submitted_db = submit.call_args.args
    assert recorded_request.detection_type == expected_detection_type
    assert recorded_request.text == "model-or-prompt"
    assert recorded_request.project_name == "route-test"
    assert submitted_db is db
    assert response == {"status": "pending"}


@pytest.mark.asyncio
async def test_recognition_publish_error_maps_to_503(monkeypatch) -> None:
    monkeypatch.setattr(recognition, "validate_public_images", Mock())
    monkeypatch.setattr(
        recognition,
        "submit_recorded_recognition",
        Mock(side_effect=RecognitionTaskPublishError("broker unavailable")),
    )
    endpoint = _post_endpoint(recognition.router, "/recognize")

    with pytest.raises(HTTPException) as error:
        await endpoint(
            RecognitionSubmitRequest(
                detection_type=1,
                images=["https://images.example.test/example.jpg"],
            ),
            Mock(),
        )

    assert error.value.status_code == 503
    assert error.value.detail == "recognition task broker unavailable"


def _model(detection_type: int):
    return SimpleNamespace(
        uuid=f"model-{detection_type}",
        name=f"model name {detection_type}",
        detection_type=detection_type,
        model_file=(
            f"/models/model-{detection_type}.pt" if detection_type <= 3 else ""
        ),
        prompt=f"prompt-{detection_type}" if detection_type >= 3 else "",
    )


@pytest.mark.asyncio
async def test_project_recognition_submits_each_model_detection_type(
    monkeypatch,
) -> None:
    models = [_model(detection_type) for detection_type in (1, 2, 3, 4)]
    submit = Mock(side_effect=[f"task-{index}" for index in range(1, 5)])
    ensure_available = Mock()
    monkeypatch.setattr(project, "validate_public_images", Mock())
    monkeypatch.setattr(project, "_get_models", Mock(return_value=models))
    monkeypatch.setattr(project, "ensure_model_available", ensure_available)
    monkeypatch.setattr(project, "submit_recorded_recognition", submit)
    db = Mock()

    response = await project.submit_project_recognition(
        project.ProjectRecognitionRequest(
            model_ids=[model.uuid for model in models],
            images=["https://images.example.test/example.jpg"],
            project_name="project-route-test",
        ),
        db,
    )

    submitted_requests = [call.args[0] for call in submit.call_args_list]
    assert [request.detection_type for request in submitted_requests] == [1, 2, 3, 4]
    assert [request.text for request in submitted_requests] == [
        "model-1",
        "model-2",
        "model-3|prompt-3",
        "prompt-4",
    ]
    assert all(call.args[1] is db for call in submit.call_args_list)
    assert ensure_available.call_count == 4
    assert [item["sub_task_id"] for item in response["data"]["items"]] == [
        "task-1",
        "task-2",
        "task-3",
        "task-4",
    ]


@pytest.mark.asyncio
async def test_project_publish_error_keeps_already_submitted_tasks(
    monkeypatch,
) -> None:
    models = [_model(1), _model(4)]
    submit = Mock(
        side_effect=[
            "already-submitted-task",
            RecognitionTaskPublishError("broker unavailable"),
        ]
    )
    monkeypatch.setattr(project, "validate_public_images", Mock())
    monkeypatch.setattr(project, "_get_models", Mock(return_value=models))
    monkeypatch.setattr(project, "ensure_model_available", Mock())
    monkeypatch.setattr(project, "submit_recorded_recognition", submit)
    db = Mock()

    with pytest.raises(HTTPException) as error:
        await project.submit_project_recognition(
            project.ProjectRecognitionRequest(
                model_ids=[model.uuid for model in models],
                images=["https://images.example.test/example.jpg"],
            ),
            db,
        )

    assert error.value.status_code == 503
    assert submit.call_count == 2
    assert submit.call_args_list[0].args[0].detection_type == 1
    assert submit.call_args_list[1].args[0].detection_type == 4
    db.rollback.assert_not_called()
