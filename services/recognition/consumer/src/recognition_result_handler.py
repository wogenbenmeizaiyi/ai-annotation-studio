import json
import logging

from sqlalchemy.orm import Session

from core.storage.recognition_result_storage import (
    get_recognition_task_record,
    load_recognition_result_payload,
    save_recognition_result,
)
from callback_delivery import deliver_recognition_callback

logger = logging.getLogger(__name__)


def handle_recognition_result_message(body: bytes, db: Session) -> None:
    """处理一条识别结果消息：先落库，再按任务记录发起回调。"""
    try:
        body_text = body.decode("utf-8")
        payload = json.loads(body_text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.exception("invalid recognition result message")
        raise ValueError("invalid recognition result message") from exc

    if not isinstance(payload, dict):
        logger.error("invalid recognition result message type")
        raise TypeError("recognition result message body must be a JSON object")

    if payload.get("event_type") == "task_completed":
        task_id = payload.get("task_id")
        if not task_id:
            raise ValueError("task_completed event missing task_id")

        record = get_recognition_task_record(task_id, db)
        callback_payload = load_recognition_result_payload(task_id, db)
        if record is None or callback_payload is None:
            return
        body_text = json.dumps(callback_payload, ensure_ascii=False)
    else:
        record = save_recognition_result(payload, db)
        if record is None:
            return

    deliver_recognition_callback(record, body_text, db)
