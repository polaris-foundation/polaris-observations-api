from typing import List, Optional

from flask import Blueprint, Response, g, jsonify, request
from flask_batteries_included.config import is_production_environment
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import (
    and_,
    key_contains_value,
    or_,
    scopes_present,
)
from marshmallow import ValidationError
from she_logging import logger

from dhos_observations_api.blueprint_api import controller
from dhos_observations_api.models.api_spec import (
    ObservationSetRequest,
    ObservationSetUpdate,
)

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/dhos/v2/observation_set", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["write:send_observation"]),
        scopes_present(required_scopes=["write:observation"]),
    )
)
def create_observation_set(
    observation_set: ObservationSetRequest.Meta.Dict, suppress_obs_publish: bool = False
) -> Response:
    """---
    post:
      summary: Create a new observation set
      description: >-
          Create a new observation set, which has been scored. This endpoint may
          trigger the generation of an ORU HL7 message and a BCP PDF for SEND.
      tags: [observation]
      parameters:
        - name: suppress_obs_publish
          in: query
          required: false
          description: >-
              Set true to suppress PDF and ORU message generation
              (ignored in production environments)
          schema:
            type: boolean
            example: false
      requestBody:
        description: JSON body containing the observation set
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ObservationSetRequest'
              x-body-name: observation_set
      responses:
        '200':
          description: 'New observation set'
          content:
            application/json:
              schema: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if suppress_obs_publish and is_production_environment():
        suppress_obs_publish = False
    try:
        observation_set_processed: ObservationSetRequest.Meta.Dict = (
            ObservationSetRequest().load(observation_set)
        )
    except ValidationError as err:
        logger.error("Error parsing observation set: %s", err.messages)
        raise ValueError("Error validating request body")
    return jsonify(
        controller.create_observation_set(
            obs_set=observation_set_processed,
            suppress_obs_publish=suppress_obs_publish,
            referring_device_id=g.jwt_claims.get("referring_device_id"),
        )
    )


@api_blueprint.route("/dhos/v2/observation_set/<observation_set_id>", methods=["PATCH"])
@protected_route(
    and_(
        or_(
            scopes_present(required_scopes=["write:send_observation"]),
            scopes_present(required_scopes=["write:observation"]),
        ),
        key_contains_value("system_id", "dhos-observations-adapter-worker"),
    )
)
def update_observation_set(
    observation_set_id: str, observation_set_details: dict
) -> Response:
    """---
    patch:
      summary: Update an observation set
      description: Update an existing observation set with new or changed details.
      tags: [observation]
      parameters:
        - name: observation_set_id
          in: path
          required: true
          description: UUID of the observation set to update
          schema:
            type: string
            example: 'dfc94d4a-43c5-4595-9606-bf921d3f1964'
      requestBody:
        description: Details of the observation set to update
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ObservationSetUpdate'
              x-body-name: observation_set_details
      responses:
        '200':
          description: 'Updated observation set'
          content:
            application/json:
              schema: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    try:
        observation_set_details_processed = ObservationSetUpdate().load(
            observation_set_details
        )
    except ValidationError as err:
        logger.error("Error parsing observation set details: %s", err.messages)
        raise ValueError("Error validating request body")

    return jsonify(
        controller.update_observation_set(
            observation_set_uuid=observation_set_id,
            updated_obs_set=observation_set_details_processed,
        )
    )


@api_blueprint.route("/dhos/v2/observation_set", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_observation_sets_by_encounter_id(
    encounter_id: List[str], compact: bool = True, limit: Optional[int] = None
) -> Response:
    """---
    get:
      summary: Get observation sets by encounter
      description: >-
          Get a list of observations sets associated with one or more encounters (specified by UUID).
          An invalid encounter uuid will return an empty list.
      tags: [observation]
      parameters:
        - name: encounter_id
          in: query
          required: true
          description: UUIDs of the encounters (comma-separated or use the parameter multiple times)
          schema:
            type: array
            items:
                type: string
                example: 'e22f5175-6283-408d-9ba4-ea3b3a5354b8'
        - name: limit
          in: query
          required: false
          description: The maximum number of observation sets to return
          schema:
            type: integer
            example: 20
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form
          schema:
            type: boolean
            default: true
      responses:
        '200':
          description: A list of observation sets
          content:
            application/json:
              schema:
                type: array
                items: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")

    return jsonify(
        controller.get_observation_sets_for_encounters(
            encounter_ids=encounter_id, limit=limit, compact=compact
        )
    )


@api_blueprint.route("/dhos/v2/observation_set/latest", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_latest_observation_set_by_encounter_id(
    encounter_id: List[str], compact: bool = True
) -> Response:
    """---
    get:
      summary: Get latest observation set for an encounter
      description: >-
          Get the most recently recorded observations set associated with
          a given encounter (specified by UUID). Multiple encounters may be given
          but only a single observation set is returned.
      tags: [observation]
      parameters:
        - name: encounter_id
          in: query
          required: true
          description: UUIDs of the encounters (comma-separated or use the parameter multiple times)
          schema:
            type: array
            items:
                type: string
                example: 'e22f5175-6283-408d-9ba4-ea3b3a5354b8'
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form
          schema:
            type: boolean
            default: true
      responses:
        '200':
          description: An observation set
          content:
            application/json:
              schema: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")

    return jsonify(
        controller.get_latest_observation_set_for_encounters(
            encounter_ids=encounter_id, compact=compact
        )
    )


@api_blueprint.route("/dhos/v2/observation_set/latest", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_latest_observation_sets_by_encounter_ids(
    encounter_ids: List[str], compact: bool = True
) -> Response:
    """---
    post:
      summary: Retrieve latest observation sets for a list of encounters
      description: >-
          Get the most recently recorded observations set associated with
          each encounter. UUIDs are passed in the request body.
      tags: [observation]
      parameters:
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form
          schema:
            type: boolean
            default: false
      requestBody:
          description: List of encounter UUIDs
          required: true
          content:
            application/json:
              schema:
                x-body-name: encounter_ids
                type: array
                items:
                  type: string
                  example: '2c4f1d24-2952-4d4e-b1d1-3637e33cc161'
      responses:
        '200':
          description: Encounter UUIDs and their latest observation sets
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/ObservationSetResponse'
        default:
          description: >-
              Error, e.g. 400 Bad Request, 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.get_latest_observation_sets_by_encounter_ids(
            encounter_ids=encounter_ids, compact=compact
        )
    )


@api_blueprint.route("/dhos/v2/observation_set/<observation_set_id>", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_observation_set_by_id(
    observation_set_id: str, compact: bool = True
) -> Response:
    """---
    get:
      summary: Get observation set
      description: Get an observation set by UUID
      tags: [observation]
      parameters:
        - name: observation_set_id
          in: path
          required: true
          description: The observation set UUID
          schema:
            type: string
            example: 'f8254bdb-5ba1-4bdf-8834-4ad4dbf9c193'
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: An observation set
          content:
            application/json:
              schema: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    return jsonify(controller.get_observation_set_by_id(observation_set_id, compact))


@api_blueprint.route("/dhos/v2/observation_set_search", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_observation_sets_by_locations_and_date_range(
    location: List[str],
    start_date: str,
    end_date: str,
    limit: int = None,
    compact: bool = False,
) -> Response:
    """---
    get:
      summary: Search observation sets by location and date
      description: >-
          Get a list of observation sets observation set, filtered by location
          UUIDs and by date range. Only observation sets recorded against the
          provided location, and during the provided date range, will be returned.
      tags: [observation]
      parameters:
        - name: location
          in: query
          required: true
          description: The UUID of the location to filter by
          schema:
            type: array
            items:
              type: string
              example: 'e22f5175-6283-408d-9ba4-ea3b3a5354b8'
        - name: start_date
          in: query
          required: true
          description: The ISO8601-formatted start date of the search
          schema:
            type: string
            format: date-time
            example: '1996-12-06T00:00:01.000Z'
        - name: end_date
          in: query
          required: true
          description: The ISO8601-formatted end date of the search
          schema:
            type: string
            format: date-time
            example: '2019-08-22T00:00:01.000Z'
        - name: limit
          in: query
          required: false
          description: The maximum number of observation sets to return
          schema:
            type: integer
            example: 20
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: A list of observation sets
          content:
            application/json:
              schema:
                type: array
                items: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a json body")

    location_uuids = location

    return jsonify(
        controller.get_observation_sets_by_locations_and_date_range(
            location_uuids, start_date, end_date, limit, compact
        )
    )


@api_blueprint.route("/dhos/v2/observation_set_search", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def search_observation_sets_by_locations_and_date_range(
    locations: List[str],
    start_date: str,
    end_date: str,
    limit: int = None,
    compact: bool = False,
) -> Response:
    """---
    post:
      summary: Search observation sets by locations and date
      description: >-
          Get a list of observation sets observation set, filtered by location
          UUIDs and by date range. Only observation sets recorded against the
          provided location, and during the provided date range, will be returned.
      tags: [observation]
      parameters:
        - name: start_date
          in: query
          required: true
          description: The ISO8601-formatted start date of the search
          schema:
            type: string
            format: date-time
            example: '1996-12-06T00:00:01.000Z'
        - name: end_date
          in: query
          required: true
          description: The ISO8601-formatted end date of the search
          schema:
            type: string
            format: date-time
            example: '2019-08-22T00:00:01.000Z'
        - name: limit
          in: query
          required: false
          description: The maximum number of observation sets to return
          schema:
            type: integer
            example: 20
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form (uuid only)
          schema:
            type: boolean
            default: false
      requestBody:
          description: List of location UUIDs
          required: true
          content:
            application/json:
              schema:
                x-body-name: locations
                type: array
                items:
                  type: string
                  example: '2c4f1d24-2952-4d4e-b1d1-3637e33cc161'
      responses:
        '200':
          description: A list of observation sets
          content:
            application/json:
              schema:
                type: array
                items: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 404 Not Found, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.get_observation_sets_by_locations_and_date_range(
            locations, start_date, end_date, limit, compact
        )
    )


@api_blueprint.route("/dhos/v2/patient/<patient_id>/observation_set", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_observation_sets_by_patient_id(patient_id: str, limit: int = None) -> Response:
    """---
    get:
      summary: Get observation sets by patient
      description: >-
          Get a list of observations sets associated with a given patient (specified by UUID).
          Note: this will only work for obs sets created with a patient UUID, which doesn't happen for SEND.
      tags: [observation]
      parameters:
        - name: patient_id
          in: path
          required: true
          description: UUID of the patient
          schema:
            type: string
            example: 'e22f5175-6283-408d-9ba4-ea3b3a5354b8'
        - name: limit
          in: query
          required: false
          description: The maximum number of observation sets to return
          schema:
            type: integer
            example: 20
      responses:
        '200':
          description: A list of observation sets
          content:
            application/json:
              schema:
                type: array
                items: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 404 Not Found, 503 Service Unavailable
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")

    return jsonify(
        controller.get_observation_sets_for_patient(patient_id=patient_id, limit=limit)
    )


@api_blueprint.route("/dhos/v2/observation_set/count", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def retrieve_observation_set_count(encounters: List[str]) -> Response:
    """---
    post:
      summary: Retrieve count of observation sets
      description: >-
          Return the number of observation sets associated with each of a list of encounter UUIDS.
      tags: [observation]
      requestBody:
        description: List of encounter UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: encounters
              type: array
              items:
                type: string
                example: 8788b763-6437-4f61-ae1e-f1289ef9f5db
      responses:
        '200':
          description: Observation set count
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  type: integer
                  example: 5
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.retrieve_observation_count_for_encounter_ids(
            encounter_uuids=encounters
        )
    )


@api_blueprint.route("/dhos/v2/observation_sets", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def get_observation_sets(modified_since: str, compact: bool = False) -> Response:
    """---
    get:
      summary: Get observation sets modified after
      description: >-
          Get a list of observations sets which have been modified after the specified date and time
          i.e modified_since=2020-12-30 will include an observation from 2020-12-30 00:00:00.000001
      tags: [observation]
      parameters:
        - name: modified_since
          in: query
          required: true
          description: Earliest modified by date for observation sets to be returned
          schema:
            type: string
            example: '2020-12-30'
        - name: compact
          in: query
          required: false
          description: Whether to return the observation sets in compact form
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: A list of observation sets
          content:
            application/json:
              schema:
                type: array
                items: ObservationSetResponse
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if request.is_json:
        raise ValueError("Request should not contain a JSON body")

    return jsonify(
        controller.get_observation_sets(modified_since=modified_since, compact=compact)
    )


@api_blueprint.route("/dhos/v2/aggregate_obs", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["write:send_observation"]),
        scopes_present(required_scopes=["write:observation"]),
    )
)
def refresh_agg_observation_sets() -> Response:
    """---
    post:
      summary: Refresh agg_observation_sets MATERIALIZED VIEW
      description: >-
          Refresh the data in the Aggregate observations set view
      tags: [observation]
      responses:
        '200':
          description: 'Data refresh time taken'

          content:
            application/json:
              schema: AggregateUpdateResponse
        default:
          description: >-
              Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """

    return jsonify(controller.refresh_agg_observation_sets())


@api_blueprint.route("/dhos/v2/on_time_obs_stats", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def on_time_observation_sets(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Response:
    """---
    post:
      summary: Return observation sets on time statistics
      description: >-
          Get aggregate data for the number and % of observation sets recorded on time
          by location by risk
      tags: [observation]
      parameters:
        - name: start_date
          in: query
          required: true
          description: Earliest record time date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-12-01'
        - name: end_date
          in: query
          required: true
          description: Latest record time date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
      requestBody:
        description: List of location UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: location_uuids
              type: array
              items:
                type: string
                example: 8788b763-6437-4f61-ae1e-f1289ef9f5db
      responses:
        '200':
          description: Aggregate observation on time statistics
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/AggregateOnTimeObservationSets'
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.on_time_observation_sets(
            start_date=start_date, end_date=end_date, location_uuids=location_uuids
        )
    )


@api_blueprint.route("/dhos/v2/missing_obs_stats", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def missing_observation_sets(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Response:
    """---
    post:
      summary: Return observation sets missing statistics
      description: >-
          Get aggregate data for the number and % of observation sets which have missing
          observations from observation sets by location
      tags: [observation]
      parameters:
        - name: start_date
          in: query
          required: true
          description: Earliest record time date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-12-01'
        - name: end_date
          in: query
          required: true
          description: Latest record time date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
      requestBody:
        description: List of location UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: location_uuids
              type: array
              items:
                type: string
                example: 8788b763-6437-4f61-ae1e-f1289ef9f5db
      responses:
        '200':
          description: Aggregate observation missing statistics
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/AggregateMissingObservationSets'
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.missing_observation_sets(
            start_date=start_date, end_date=end_date, location_uuids=location_uuids
        )
    )


@api_blueprint.route("/dhos/v2/on_time_intervals", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def observation_sets_time_intervals(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Response:
    """---
    post:
      summary: Return observation sets within late / early intervals
      description: >-
          Get aggregate data for the number of observation sets grouped by interval of
          time taken relative to the expected time taken by risk category
      tags: [observation]
      parameters:
        - name: start_date
          in: query
          required: true
          description: Earliest record time date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-12-01'
        - name: end_date
          in: query
          required: true
          description: Latest record time date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
      requestBody:
        description: List of location UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: location_uuids
              type: array
              items:
                type: string
                example: 8788b763-6437-4f61-ae1e-f1289ef9f5db
      responses:
        '200':
          description: Aggregate observation by interval and risk
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/AggregateObservationsByInterval'
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.observation_sets_time_intervals(
            start_date=start_date, end_date=end_date, location_uuids=location_uuids
        )
    )


@api_blueprint.route("/dhos/v2/observation_sets_by_month", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def agg_observation_sets_by_month(
    start_date: str, end_date: str, location_uuids: List[str]
) -> Response:
    """---
    post:
      summary: Return observation set aggregate data by month
      description: >-
          Get aggregate data for the number of observation sets grouped by month
      tags: [observation]
      parameters:
        - name: start_date
          in: query
          required: true
          description: Earliest record_day date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
        - name: end_date
          in: query
          required: true
          description: Latest record_day date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-07-01'
      requestBody:
        description: List of location UUIDs
        required: true
        content:
          application/json:
            schema:
              x-body-name: location_uuids
              type: array
              items:
                type: string
                example: 8788b763-6437-4f61-ae1e-f1289ef9f5db
      responses:
        '200':
          description: Aggregate observation by month
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/AggregateObservationSetsByMonth'
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.agg_observation_sets_by_month(
            start_date=start_date, end_date=end_date, location_uuids=location_uuids
        )
    )


@api_blueprint.route("/dhos/v2/observation_sets_by_month", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes=["read:send_observation"]),
        scopes_present(required_scopes=["read:observation"]),
    )
)
def all_agg_obs_by_location_by_month(start_date: str, end_date: str) -> Response:
    """---
    get:
      summary: Return observation set aggregate data by location and month
      description: >-
          Get aggregate data for the number of observation sets grouped by location and month
      tags: [observation]
      parameters:
        - name: start_date
          in: query
          required: true
          description: Earliest record_day date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-01-01'
        - name: end_date
          in: query
          required: true
          description: Latest record_day date for observation sets to be returned
          schema:
            type: string
            format: date
            example: '2020-07-01'
      responses:
        '200':
          description: Aggregate observation by location and month
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/AggregateObservationSetsByLocationMonth'
        default:
          description: >-
              Error, e.g. 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    return jsonify(
        controller.all_agg_obs_by_location_by_month(
            start_date=start_date, end_date=end_date
        )
    )
