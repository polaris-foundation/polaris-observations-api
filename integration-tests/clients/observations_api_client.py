from typing import Dict, List

import requests
from environs import Env
from requests import Response


def _get_base_url() -> str:
    return Env().str("DHOS_OBSERVATIONS_BASE_URL", "http://dhos-observations-api:5000")


def post_observation_set(observation_set_data: Dict, jwt: str) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v2/observation_set",
        headers={"Authorization": f"Bearer {jwt}"},
        json=observation_set_data,
        timeout=15,
    )


def get_latest_observation_set(encounter_uuid: str, jwt: str) -> Response:
    return requests.get(
        f"{_get_base_url()}/dhos/v2/observation_set/latest",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
        params={"encounter_id": encounter_uuid},
    )


def patch_observation_set(
    observation_set_uuid: str, observation_set_data: Dict, jwt: str
) -> Response:
    return requests.patch(
        f"{_get_base_url()}/dhos/v2/observation_set/{observation_set_uuid}",
        headers={"Authorization": f"Bearer {jwt}"},
        json=observation_set_data,
        timeout=15,
    )


def post_observation_set_count(encounter_uuids: List, jwt: str) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v2/observation_set/count",
        headers={"Authorization": f"Bearer {jwt}"},
        json=encounter_uuids,
        timeout=15,
    )


def post_latest_observations_by_encounter_list(
    encounter_uuids: List, jwt: str
) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v2/observation_set/latest",
        headers={"Authorization": f"Bearer {jwt}"},
        json=encounter_uuids,
        timeout=15,
    )


def get_observation_sets_by_location(
    location_uuid: str, start_date: str, end_date: str, jwt: str
) -> Response:
    return requests.get(
        f"{_get_base_url()}/dhos/v2/observation_set_search",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
        params={
            "location": location_uuid,
            "start_date": start_date,
            "end_date": end_date,
        },
    )


def post_observation_sets_by_location_list(
    location_uuids: List, start_date: str, end_date: str, jwt: str
) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v2/observation_set_search",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
        params={"start_date": start_date, "end_date": end_date},
        json=location_uuids,
    )


def post_agg_observation_sets_by_month(
    location_uuids: List, start_date: str, end_date: str, jwt: str
) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v2/observation_sets_by_month",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
        params={"start_date": start_date, "end_date": end_date},
        json=location_uuids,
    )


def post_refresh_agg_observation_sets(jwt: str) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v2/aggregate_obs",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )


def get_agg_observation_sets_by_location_by_month(
    start_date: str, end_date: str, jwt: str
) -> Response:
    return requests.get(
        f"{_get_base_url()}/dhos/v2/observation_sets_by_month",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
        params={"start_date": start_date, "end_date": end_date},
    )
