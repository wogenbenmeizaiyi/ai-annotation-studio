from collections import Counter

from core.mq import task_infra
from core.mq.task_routing import TASK_QUEUE_SPECS


class RecordingChannel:
    def __init__(self) -> None:
        self.exchange_declarations: list[dict] = []
        self.queue_declarations: list[dict] = []
        self.bindings: list[dict] = []

    def exchange_declare(self, **kwargs) -> None:
        self.exchange_declarations.append(kwargs)

    def queue_declare(self, **kwargs) -> None:
        self.queue_declarations.append(kwargs)

    def queue_bind(self, **kwargs) -> None:
        self.bindings.append(kwargs)


def test_ensure_task_infra_declares_three_isolated_durable_queues(
    monkeypatch,
) -> None:
    channel = RecordingChannel()
    monkeypatch.setattr(task_infra, "_task_infra_declared", False)

    task_infra.ensure_task_infra(channel)

    expected_exchanges = {
        spec.exchange_name for spec in TASK_QUEUE_SPECS.values()
    } | {spec.dead_letter_exchange for spec in TASK_QUEUE_SPECS.values()}
    assert {item["exchange"] for item in channel.exchange_declarations} == (
        expected_exchanges
    )
    assert all(
        item["exchange_type"] == "direct" and item["durable"] is True
        for item in channel.exchange_declarations
    )

    expected_queues = {
        spec.queue_name for spec in TASK_QUEUE_SPECS.values()
    } | {spec.dead_letter_queue for spec in TASK_QUEUE_SPECS.values()}
    assert {item["queue"] for item in channel.queue_declarations} == expected_queues
    assert all(item["durable"] is True for item in channel.queue_declarations)

    declarations_by_name = {
        item["queue"]: item for item in channel.queue_declarations
    }
    for spec in TASK_QUEUE_SPECS.values():
        assert declarations_by_name[spec.queue_name]["arguments"] == {
            "x-dead-letter-exchange": spec.dead_letter_exchange,
            "x-dead-letter-routing-key": spec.dead_letter_routing_key,
        }
        assert "arguments" not in declarations_by_name[spec.dead_letter_queue]

        assert {
            "queue": spec.queue_name,
            "exchange": spec.exchange_name,
            "routing_key": spec.routing_key,
        } in channel.bindings
        assert {
            "queue": spec.dead_letter_queue,
            "exchange": spec.dead_letter_exchange,
            "routing_key": spec.dead_letter_routing_key,
        } in channel.bindings

    assert Counter(item["queue"] for item in channel.bindings) == Counter(
        {queue_name: 1 for queue_name in expected_queues}
    )


def test_ensure_task_infra_is_idempotent(monkeypatch) -> None:
    channel = RecordingChannel()
    monkeypatch.setattr(task_infra, "_task_infra_declared", False)

    task_infra.ensure_task_infra(channel)
    first_call_counts = (
        len(channel.exchange_declarations),
        len(channel.queue_declarations),
        len(channel.bindings),
    )
    task_infra.ensure_task_infra(channel)

    assert (
        len(channel.exchange_declarations),
        len(channel.queue_declarations),
        len(channel.bindings),
    ) == first_call_counts
