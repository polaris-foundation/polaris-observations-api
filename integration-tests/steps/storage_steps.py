from behave import then
from behave.runner import Context
from clients.observations_api_client import get_latest_observation_set
from helpers.observations_helper import assert_observations_set_body


@then("the observation set is stored")
def assert_last_obs_set_is_returned(context: Context) -> None:
    response = get_latest_observation_set(
        encounter_uuid=context.encounter_uuid, jwt=context.system_jwt
    )
    assert_observations_set_body(
        actual_observation_set=response.json(),
        expected_observation_set=context.observation_set_data[-1],
    )
