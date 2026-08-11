"""
简单测试消费者：监听并打印 result 队列中的消息。
运行方式: uv run python tests/consume_result_queue.py
"""

import os
import sys
import json

# 确保项目根目录在 sys.path 中，以便导入配置
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "core", "src"))

import pika  # noqa: E402
from core.config import config  # noqa: E402


def callback(ch, method, properties, body):
    """收到消息时的回调函数"""
    print("\n" + "=" * 50)
    print(f" [x] 收到消息 (Routing Key: {method.routing_key})")
    try:
        # 解析并打印完整 JSON 数据
        data = json.loads(body.decode())
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        # 如果不是 JSON，则打印原始字符串
        print(f" [x] 原始数据: {body.decode()}")
    print("=" * 50 + "\n")


def main():
    print(f"[*] 正在连接 RabbitMQ ({config.RABBITMQ_HOST})...")

    credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        virtual_host=config.RABBITMQ_VHOST,
        credentials=credentials,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    print(
        f"[*] 正在准备队列 '{config.RESULT_QUEUE}' (绑定到交换机 '{config.RESULT_EXCHANGE}')..."
    )

    # 确保基础设施存在 (声明是幂等的，重复执行无副作用)
    channel.exchange_declare(
        exchange=config.RESULT_EXCHANGE, exchange_type="fanout", durable=True
    )
    channel.queue_declare(queue=config.RESULT_QUEUE, durable=True)
    channel.queue_bind(queue=config.RESULT_QUEUE, exchange=config.RESULT_EXCHANGE)

    print("[*] 开始监听队列，等待结果消息... (按 Ctrl+C 退出)")

    channel.basic_consume(
        queue=config.RESULT_QUEUE, on_message_callback=callback, auto_ack=True
    )
    channel.start_consuming()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] 停止监听")
