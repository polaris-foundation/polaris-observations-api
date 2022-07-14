from uuid import uuid4

from behave import given, step
from behave.runner import Context
from helpers.jwt import get_system_token
from messaging_steps import assert_message_published
from request_steps import create_observation_set


@given("a valid JWT")
def get_system_jwt(context: Context) -> None:
    if not hasattr(context, "system_jwt"):
        context.system_jwt = get_system_token()


@given("a patient is admitted to a ward")
def create_patient_and_location(context: Context) -> None:
    context.location_uuid = str(uuid4())
    context.patient_uuid = str(uuid4())
    context.patient_record_uuid = str(uuid4())
    context.product_uuid = str(uuid4())
    context.encounter_uuid = str(uuid4())


@step("an(?:other)? observation set is created for (?:a|the) patient")
def create_obs_set(context: Context) -> None:
    create_observation_set(context)
    assert_message_published(context, "OBSERVATION_SET_UPDATED")
    assert_message_published(context, "ENCOUNTER_UPDATED")
