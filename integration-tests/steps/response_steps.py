from datetime import datetime
from typing import Dict, List

from behave import step, then
from behave.runner import Context
from helpers.observations_helper import assert_observations_set_body


@then("the observation set response is correct")
def assert_observation_set_response(context: Context) -> None:
    assert context.observation_set_response.status_code == 200
    returned: Dict = context.observation_set_response.json()
    assert returned

    # last obs set
    expected_obs_set: Dict = context.observation_set_data[-1]

    if context.encounter_uuid in returned:
        # search returned a dict
        assert returned[context.encounter_uuid]["mins_late"] is not None
        assert_observations_set_body(
            actual_observation_set=returned[context.encounter_uuid],
            expected_observation_set=expected_obs_set,
        )
    else:
        # encounter by uuid
        assert returned["mins_late"] is not None
        assert_observations_set_body(
            actual_observation_set=returned,
            expected_observation_set=expected_obs_set,
        )


@step("the patch response is correct")
def assert_patch_response(context: Context) -> None:
    assert context.observation_set_patch_response.status_code == 200
    expected = context.observation_set_response.json()  # unpatched obs set
    for patch in context.observation_set_patch_request["observations"]:
        # add the bits from patch request
        expected["observations"] = list(
            map(
                lambda obs: {**obs, **patch}
                if patch["observation_type"] == obs["observation_type"]
                else obs,
                expected["observations"],
            )
        )

    assert_observations_set_body(
        actual_observation_set=context.observation_set_patch_response.json(),
        expected_observation_set=expected,
    )


@step("the observation set exists in the search result")
def assert_obs_set_in_search_list(context: Context) -> None:
    assert context.observation_set_response.status_code == 200
    returned: List = context.observation_set_response.json()

    obs_set_data: List[Dict] = [
        o for o in returned if o["encounter_id"] == context.encounter_uuid
    ]
    assert obs_set_data
    assert_observations_set_body(
        actual_observation_set=obs_set_data[0],
        expected_observation_set=context.observation_set_data[-1],
    )


@step("the encounter has (?P<count>\w+) observation set(?:s?)")
def assert_obs_set_count(context: Context, count: str) -> None:
    obs_sets: dict = context.observation_set_count_response.json()
    assert context.encounter_uuid in obs_sets
    assert obs_sets[context.encounter_uuid] == int(count)


@step("observation set (?P<number>\w+) is returned")
def assert_specific_obs_set_returned(context: Context, number: str) -> None:
    assert context.observation_set_response.status_code == 200
    returned: Dict = context.observation_set_response.json()
    assert returned
    assert context.created_observation_sets[int(number) - 1].json().get(
        "uuid"
    ) == returned.get("uuid")


@step("aggregate observation sets are returned")
def assert_aggregate_obs_set_returned(context: Context) -> None:
    assert context.agg_observation_sets_by_month_response.status_code == 200
    returned: Dict = context.agg_observation_sets_by_month_response.json()
    assert returned
    yyyymm = str(datetime.now())[:7]
    assert 2 == returned[yyyymm]["all_obs_sets"]


@step("aggregate location based observation sets are returned")
def assert_aggregate_location_based_obs_set_returned(context: Context) -> None:
    assert context.agg_observation_sets_by_location_by_month_response.status_code == 200
    returned: Dict = context.agg_observation_sets_by_location_by_month_response.json()
    assert returned
    yyyymm = str(datetime.now())[:7]
    assert 2 == returned[context.location_uuid][yyyymm]["all_obs_sets"]
