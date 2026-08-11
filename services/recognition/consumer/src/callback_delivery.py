import logging
import time
from datetime import UTC, datetime, timedelta

import requests
from sqlalchemy.orm import Session

from core.config import config
from core.schemas.recognition.task_record import RecognitionTaskRecord

logger = logging.getLogger(__name__)


class CallbackDeliveryAbandoned(Exception):
    """回调投递已达到放弃条件。"""


def deliver_recognition_callback(
    record: RecognitionTaskRecord,
    body_text: str,
    db: Session,
) -> None:
    """按任务记录里的回调地址投递识别结果，失败按配置重试。"""
    logger.info(
        "recognition callback started task_id=%s callback_url=%s",
        record.task_id,
        record.callback_url,
    )
    _retry_callback_until_done(record, body_text, db)


def _retry_callback_until_done(
    record: RecognitionTaskRecord,
    body_text: str,
    db: Session,
) -> None:
    """循环执行回调投递，直到成功或超过最大重试时间。"""
    started_at = _to_aware_datetime(record.callback_started_at)
    deadline = started_at + timedelta(seconds=config.CALLBACK_RETRY_TIMEOUT_SECONDS)
    interval_seconds = config.CALLBACK_RETRY_INTERVAL_SECONDS

    while True:
        if _send_callback_once(record, body_text, db):
            return

        now = datetime.now(UTC)
        if record.callback_attempts >= config.CALLBACK_MAX_ATTEMPTS or now >= deadline:
            record.last_callback_error = (
                "callback max attempts reached"
                if record.callback_attempts >= config.CALLBACK_MAX_ATTEMPTS
                else "callback retry timeout"
            )
            logger.info(
                "db commit callback abandoned started task_id=%s attempts=%s",
                record.task_id,
                record.callback_attempts,
            )
            db.commit()
            logger.info(
                "db commit callback abandoned succeeded task_id=%s attempts=%s",
                record.task_id,
                record.callback_attempts,
            )
            logger.error(
                "recognition callback abandoned task_id=%s attempts=%s task_status=%s",
                record.task_id,
                record.callback_attempts,
                record.status,
            )
            raise CallbackDeliveryAbandoned(record.last_callback_error)

        retry_at = min(
            now + timedelta(seconds=interval_seconds),
            deadline,
        )

        sleep_seconds = max((retry_at - now).total_seconds(), 0)
        logger.info(
            "recognition callback will retry task_id=%s attempts=%s retry_at=%s task_status=%s",
            record.task_id,
            record.callback_attempts,
            retry_at.isoformat(),
            record.status,
        )
        time.sleep(sleep_seconds)


def _send_callback_once(
    record: RecognitionTaskRecord,
    body_text: str,
    db: Session,
) -> bool:
    """执行一次 HTTP 回调请求，并记录本次投递结果。"""
    record.callback_attempts += 1
    record.last_callback_error = None
    record.last_callback_status_code = None
    logger.info(
        "db commit callback attempt started task_id=%s attempts=%s",
        record.task_id,
        record.callback_attempts,
    )
    db.commit()
    logger.info(
        "db commit callback attempt succeeded task_id=%s attempts=%s",
        record.task_id,
        record.callback_attempts,
    )

    try:
        response = requests.post(
            record.callback_url,
            data=body_text.encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=config.CALLBACK_REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        record.last_callback_error = str(exc)
        logger.info(
            "db commit callback exception started task_id=%s attempts=%s",
            record.task_id,
            record.callback_attempts,
        )
        db.commit()
        logger.info(
            "db commit callback exception succeeded task_id=%s attempts=%s",
            record.task_id,
            record.callback_attempts,
        )
        logger.warning(
            "recognition callback request failed task_id=%s attempts=%s error=%s",
            record.task_id,
            record.callback_attempts,
            exc,
        )
        return False

    record.last_callback_status_code = response.status_code
    if response.status_code == 200:
        logger.info(
            "db commit callback success started task_id=%s attempts=%s status_code=%s",
            record.task_id,
            record.callback_attempts,
            response.status_code,
        )
        db.commit()
        logger.info(
            "db commit callback success succeeded task_id=%s attempts=%s",
            record.task_id,
            record.callback_attempts,
        )
        logger.info(
            "recognition callback succeeded task_id=%s attempts=%s",
            record.task_id,
            record.callback_attempts,
        )
        return True

    record.last_callback_error = response.text[:2000]
    logger.info(
        "db commit callback non_200 started task_id=%s attempts=%s status_code=%s",
        record.task_id,
        record.callback_attempts,
        response.status_code,
    )
    db.commit()
    logger.info(
        "db commit callback non_200 succeeded task_id=%s attempts=%s status_code=%s",
        record.task_id,
        record.callback_attempts,
        response.status_code,
    )
    logger.warning(
        "recognition callback returned non-200 task_id=%s attempts=%s status_code=%s",
        record.task_id,
        record.callback_attempts,
        response.status_code,
    )
    return False


def _to_aware_datetime(value: datetime | None) -> datetime:
    """把数据库时间统一转换成带 UTC 时区的时间。"""
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
