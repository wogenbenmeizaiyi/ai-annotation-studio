from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

import boto3
import pika
import psycopg2
import redis
from botocore.config import Config as BotoConfig
from dotenv import dotenv_values


def load_environment(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(f"environment file does not exist: {path}")
    return {
        key: str(value)
        for key, value in dotenv_values(path).items()
        if value is not None
    }


def required(env: dict[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ValueError(f"missing required variable {key}")
    return value


def sanitize(message: str, environments: list[dict[str, str]]) -> str:
    result = message
    secret_keys = {
        "POSTGRES_PASSWORD",
        "RABBITMQ_PASS",
        "REDIS_PASSWORD",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
    }
    for env in environments:
        for key in secret_keys:
            secret = env.get(key, "")
            if secret:
                result = result.replace(secret, "***")
    return result


def probe_postgres(env: dict[str, str]) -> None:
    connection = psycopg2.connect(
        host=required(env, "POSTGRES_HOST"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=required(env, "POSTGRES_USER"),
        password=required(env, "POSTGRES_PASSWORD"),
        dbname=required(env, "POSTGRES_DB"),
        connect_timeout=4,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    finally:
        connection.close()


def probe_s3(env: dict[str, str], bucket_key: str) -> None:
    client = boto3.client(
        "s3",
        endpoint_url=required(env, "S3_ENDPOINT"),
        aws_access_key_id=required(env, "S3_ACCESS_KEY"),
        aws_secret_access_key=required(env, "S3_SECRET_KEY"),
        region_name=env.get("S3_REGION", "us-east-1"),
        config=BotoConfig(
            signature_version=env.get("S3_SIGNATURE_VERSION", "s3v4"),
            connect_timeout=4,
            read_timeout=4,
            retries={"max_attempts": 1},
        ),
    )
    client.head_bucket(Bucket=env.get(bucket_key, "ai-cmm"))


def probe_rabbitmq(env: dict[str, str]) -> None:
    credentials = pika.PlainCredentials(
        required(env, "RABBITMQ_USER"),
        required(env, "RABBITMQ_PASS"),
    )
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=required(env, "RABBITMQ_HOST"),
            port=int(env.get("RABBITMQ_PORT", "5672")),
            virtual_host=env.get("RABBITMQ_VHOST", "/"),
            credentials=credentials,
            connection_attempts=1,
            socket_timeout=4,
            blocked_connection_timeout=4,
            heartbeat=0,
        )
    )
    connection.close()


def probe_redis(env: dict[str, str]) -> None:
    client = redis.Redis(
        host=required(env, "REDIS_HOST"),
        port=int(env.get("REDIS_PORT", "6379")),
        db=int(env.get("REDIS_DB", "0")),
        password=env.get("REDIS_PASSWORD") or None,
        socket_connect_timeout=4,
        socket_timeout=4,
    )
    if client.ping() is not True:
        raise RuntimeError("Redis PING did not return success")


def run_check(
    name: str,
    target: str,
    check: Callable[[], None],
    environments: list[dict[str, str]],
) -> dict[str, object]:
    try:
        check()
        return {"name": name, "target": target, "ok": True}
    except Exception as exc:
        return {
            "name": name,
            "target": target,
            "ok": False,
            "error": sanitize(str(exc), environments),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotation-env", type=Path, required=True)
    parser.add_argument("--recognition-env", type=Path, required=True)
    args = parser.parse_args()

    annotation = load_environment(args.annotation_env)
    recognition = load_environment(args.recognition_env)
    environments = [annotation, recognition]

    checks = [
        run_check(
            "annotation-postgres",
            f"{annotation.get('POSTGRES_HOST', '?')}:{annotation.get('POSTGRES_PORT', '5432')}/"
            f"{annotation.get('POSTGRES_DB', '?')}",
            lambda: probe_postgres(annotation),
            environments,
        ),
        run_check(
            "annotation-s3",
            annotation.get("S3_ENDPOINT", "?"),
            lambda: probe_s3(annotation, "S3_BUCKET_NAME"),
            environments,
        ),
        run_check(
            "recognition-postgres",
            f"{recognition.get('POSTGRES_HOST', '?')}:{recognition.get('POSTGRES_PORT', '5432')}/"
            f"{recognition.get('POSTGRES_DB', '?')}",
            lambda: probe_postgres(recognition),
            environments,
        ),
        run_check(
            "recognition-rabbitmq",
            f"{recognition.get('RABBITMQ_HOST', '?')}:"
            f"{recognition.get('RABBITMQ_PORT', '5672')}",
            lambda: probe_rabbitmq(recognition),
            environments,
        ),
        run_check(
            "recognition-redis",
            f"{recognition.get('REDIS_HOST', '?')}:{recognition.get('REDIS_PORT', '6379')}",
            lambda: probe_redis(recognition),
            environments,
        ),
        run_check(
            "recognition-s3",
            recognition.get("S3_ENDPOINT", "?"),
            lambda: probe_s3(recognition, "S3_BUCKET"),
            environments,
        ),
    ]
    result = {"ok": all(check["ok"] for check in checks), "checks": checks}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
