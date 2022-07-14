from datetime import datetime, timezone
from typing import Dict

from behave import step, when
from behave.runner import Context
from clients.observations_api_client import (
    get_agg_observation_sets_by_location_by_month,
    get_latest_observation_set,
    get_observation_sets_by_location,
    patch_observation_set,
    post_agg_observation_sets_by_month,
    post_latest_observations_by_encounter_list,
    post_observation_set,
    post_observation_set_count,
    post_observation_sets_by_location_list,
    post_refresh_agg_observation_sets,
)
from helpers.jwt import get_system_token
from helpers.observations_helper import (
    generate_observation_set_request,
    generate_update_observation_set_request,
)
from requests import Response


@when("a new observation set is submitted")
def create_observation_set(context: Context) -> None:
    obs_set_request: Dict = generate_observation_set_request(
        encounter_uuid=context.encounter_uuid, location_uuid=context.location_uuid
    )
    context.observation_set_data.append(obs_set_request)
    context.observation_set_response = post_observation_set(
        observation_set_data=obs_set_request, jwt=context.system_jwt
    )
    context.created_observation_sets.append(context.observation_set_response)
    context.observation_set_uuid = context.observation_set_response.json()["uuid"]


@when("the observation set is updated")
def update_current_observation_set(context: Context) -> None:
    obs_set: Response = context.created_observation_sets[-1]
    _do_update_observation_set(context=context, obs_set_uuid=obs_set.json().get("uuid"))


@step("observation set (?P<number>\w+) is updated")
def update_nth_observation_set(context: Context, number: str) -> None:
    obs_set: Response = context.created_observation_sets[int(number) - 1]
    _do_update_observation_set(context=context, obs_set_uuid=obs_set.json().get("uuid"))


@step("observation count is requested for the encounter")
def request_observation_set_count(context: Context) -> None:
    context.observation_set_count_response = post_observation_set_count(
        encounter_uuids=[context.encounter_uuid], jwt=context.system_jwt
    )


@step("a latest observation set is retrieved for the encounter")
def get_latest_observation_set_by_encounter_uuid(context: Context) -> None:
    context.observation_set_response = get_latest_observation_set(
        encounter_uuid=context.encounter_uuid, jwt=context.system_jwt
    )


@step("latest observation sets are retrieved for a list of encounters")
def retrieve_last_observation_sets_by_encounter_list(context: Context) -> None:
    context.observation_set_response = post_latest_observations_by_encounter_list(
        encounter_uuids=[context.encounter_uuid], jwt=context.system_jwt
    )


@step("observation sets are searched for by a location")
def retrieve_observation_sets_by_location(context: Context) -> None:
    context.observation_set_response = get_observation_sets_by_location(
        location_uuid=context.location_uuid,
        start_date="2011-11-04T00:00:00.000Z",
        end_date=datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
        jwt=context.system_jwt,
    )


@step("observation sets are searched for by a list of locations")
def retrieve_observation_sets_by_location_list(context: Context) -> None:
    context.observation_set_response = post_observation_sets_by_location_list(
        location_uuids=[context.location_uuid],
        start_date="2011-11-04T00:00:00.000Z",
        end_date=datetime.now(tz=timezone.utc).isoformat(timespec="milliseconds"),
        jwt=context.system_jwt,
    )


def _do_update_observation_set(context: Context, obs_set_uuid: str) -> None:
    context.observation_set_patch_request = generate_update_observation_set_request()
    adapter_worker_jwt: str = get_system_token("dhos-observations-adapter-worker")
    context.observation_set_patch_response = patch_observation_set(
        observation_set_uuid=obs_set_uuid,
        observation_set_data=context.observation_set_patch_request,
        jwt=adapter_worker_jwt,
    )


@step("aggregate observation sets by month report requested")
def agg_observation_sets_by_month(context: Context) -> None:
    context.agg_observation_sets_by_month_response = post_agg_observation_sets_by_month(
        location_uuids=[context.location_uuid],
        start_date="2011-11-04",
        end_date="9999-12-31",
        jwt=context.system_jwt,
    )


@step("observation set aggregation has processed")
def aggregation_has_processed(context: Context) -> None:
    context.refresh_agg_observation_sets = post_refresh_agg_observation_sets(
        jwt=context.system_jwt
    )


@step("aggregate observation sets by location by month report requested")
def agg_observation_sets_by_location_by_month(context: Context) -> None:
    context.agg_observation_sets_by_location_by_month_response = (
        get_agg_observation_sets_by_location_by_month(
            start_date="2011-11-04",
            end_date="9999-12-31",
            jwt=context.system_jwt,
        )
    )
