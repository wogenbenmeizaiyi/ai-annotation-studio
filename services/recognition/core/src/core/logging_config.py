import logging
import sys


def setup_logging() -> None:
    """配置应用日志，默认输出到 stdout，避免普通 INFO 进入 err 日志。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("app").setLevel(logging.INFO)
