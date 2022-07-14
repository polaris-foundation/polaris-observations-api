import logging
from typing import Dict, Generator

from behave import fixture
from behave.runner import Context
from environs import Env
from kombu import Connection, Exchange, Message, Queue
from kombu.simple import SimpleQueue
from kombu.utils import json

logger = logging.getLogger("Tests")


@fixture
def create_messaging_connection(context: Context) -> Generator[Connection, None, None]:
    env = Env()
    host: str = env.str("RABBITMQ_HOST")
    port: int = env.int("RABBITMQ_PORT", 5672)
    username: str = env.str("RABBITMQ_USERNAME")
    password: str = env.str("RABBITMQ_PASSWORD")
    conn_string: str = f"amqp://{username}:{password}@{host}:{port}//"
    context.messaging_connection = Connection(conn_string)
    context.messaging_exchange = Exchange(
        "dhos", "topic", channel=context.messaging_connection
    )
    yield context.messaging_connection
    context.messaging_connection.release()
    del context.messaging_exchange
    del context.messaging_connection


@fixture
def create_messaging_queues(
    context: Context, routing_keys: Dict[str, str]
) -> Generator[Dict[str, SimpleQueue], None, None]:
    connection = context.messaging_connection
    exchange = context.messaging_exchange
    context.messaging_queues = {}
    for name, routing_key in routing_keys.items():
        queue = Queue(
            routing_key, exchange=exchange, routing_key=routing_key, channel=connection
        )
        queue.declare()
        context.messaging_queues[routing_key] = SimpleQueue(connection, queue)

    yield context.messaging_queues

    messages = []
    for routing_key, queue in context.messaging_queues.items():
        if len(queue) != 0:
            messages.append(routing_key)
            logger.warning(f"Queue not empty {routing_key} length {len(queue)}")
        queue.clear()
        queue.close()
    del context.messaging_queues

    assert not messages, "Unexpected rabbit messages: " + ", ".join(
        k for k in routing_keys if routing_keys[k] in messages
    )


def get_message(context: Context, routing_key: str, timeout: int = 20) -> Dict:
    queue: SimpleQueue = context.messaging_queues[routing_key]
    message: Message = queue.get(block=True, timeout=timeout)
    message.ack()
    return json.loads(message.body)


def assert_message_queues_are_empty(context: Context) -> None:
    for routing_key, queue in context.messaging_queues.items():
        assert len(queue) == 0, f"Queue not empty {routing_key} length {len(queue)}"
