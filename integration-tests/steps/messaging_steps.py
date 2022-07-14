from behave import given, then, use_fixture
from behave.runner import Context
from clients.messaging_client import (
    create_messaging_connection,
    create_messaging_queues,
    get_message,
)

MESSAGES = {
    "ENCOUNTER_UPDATED": "dhos.DM000007",
    "OBSERVATION_SET_UPDATED": "dhos.DM000004",
}


@given("the messaging broker is running")
def create_messaging_broker_queues(context: Context) -> None:
    if not hasattr(context, "messaging_connection"):
        use_fixture(create_messaging_connection, context=context)
        use_fixture(create_messaging_queues, context=context, routing_keys=MESSAGES)


@then("a(?:n?) (?P<message_name>\w+) message is published")
def assert_message_published(context: Context, message_name: str) -> None:
    for i in range(3):
        message = get_message(context, MESSAGES[message_name])
        if message_name == "ENCOUNTER_UPDATED":
            expected = {"encounter_id": context.encounter_uuid}
        elif message_name == "OBSERVATION_SET_UPDATED":
            actual_observation_set = message["actions"][0]["data"].pop(
                "observation_set"
            )
            expected = {"actions": [{"name": "process_observation_set", "data": {}}]}
            assert message == expected, f"expected={expected}, got message={message}"
        else:
            assert False, f"Unexpected message_name={message_name} message={message}"

        if message != expected:
            # We can see messages from earlier tests, so ignore any extras
            print(f"Extra message discarded {message}")
            continue

        assert message == expected, f"expected={expected}, got {message}"
        return

    assert False, f"Expected {message_name} not received"
