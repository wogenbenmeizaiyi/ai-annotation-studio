import logging

from core.db import SessionLocal
from core.logging_config import setup_logging
from core.mq import subscribe_raw_results
from recognition_result_handler import (
    handle_recognition_result_message,
)

logger = logging.getLogger(__name__)


def handle_message(body: bytes) -> None:
    db = SessionLocal()
    try:
        handle_recognition_result_message(body, db)
    finally:
        db.close()


def main() -> None:
    setup_logging()
    logger.info("recognition consumer starting")
    subscribe_raw_results(handle_message)


if __name__ == "__main__":
    main()
