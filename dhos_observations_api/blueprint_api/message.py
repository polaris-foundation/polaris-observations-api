from typing import Dict, Optional

import kombu_batteries_included
from she_logging import logger

from dhos_observations_api.models.api_spec import ObservationSetResponse


# SCTID: DM000004 observation_set_notification
# Updated observations need to be processed to trigger generation of ORU message
def publish_scored_obs_message(obs_set: ObservationSetResponse.Meta.Dict) -> None:
    obs_update_msg = {
        "actions": [
            {"name": "process_observation_set", "data": {"observation_set": obs_set}}
        ]
    }
    logger.debug("Publishing scored obs message", extra={"msg_data": obs_update_msg})
    kombu_batteries_included.publish_message(
        routing_key="dhos.DM000004", body=obs_update_msg
    )


# SCTID: DM000007 encounter_update
def publish_encounter_update_message(obs_set: ObservationSetResponse.Meta.Dict) -> None:
    encounter_id: Optional[str] = obs_set.get("encounter_id")

    if not encounter_id:
        logger.debug("Observation set has no encounter id: skipping update message")
        return

    encounter_update_message = {"encounter_id": encounter_id}
    logger.debug(
        "Publishing encounter message",
        extra={"encounter_data": encounter_update_message},
    )
    kombu_batteries_included.publish_message(
        routing_key="dhos.DM000007", body=encounter_update_message
    )


def publish_audit_message(audit_message: Dict) -> None:
    kombu_batteries_included.publish_message(
        routing_key="dhos.34837004", body=audit_message
    )
