import os
import signal
import socket
import sys
import time
from typing import Any, Dict, Generator, NoReturn, Tuple
from unittest.mock import Mock
from urllib.parse import urlparse

import kombu_batteries_included
import pytest
from flask import Flask, g
from flask_batteries_included.config import RealSqlDbConfig
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import db
from pytest_mock import MockFixture

from dhos_observations_api.models.sql.agg_observation_sets import AggObservationSets


#####################################################
# Configuration to use postgres started by tox-docker
#####################################################
def pytest_configure(config: Any) -> None:
    for env_var, tox_var in [
        ("DATABASE_HOST", "POSTGRES_HOST"),
        ("DATABASE_PORT", "POSTGRES_5432_TCP_PORT"),
    ]:
        if tox_var in os.environ:
            os.environ[env_var] = os.environ[tox_var]

    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if os.environ.get("SQLALCHEMY_ECHO") else logging.WARNING
    )


def pytest_report_header(config: Any) -> str:
    db_config = (
        f"{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}"
        if os.environ.get("DATABASE_PORT")
        else "Sqlite"
    )
    return f"SQL database: {db_config}"


def _wait_for_it(service: str, timeout: int = 30) -> None:
    url = urlparse(service, scheme="http")

    host = url.hostname
    port = url.port or (443 if url.scheme == "https" else 80)

    friendly_name = f"{host}:{port}"

    def _handle_timeout(signum: Any, frame: Any) -> NoReturn:
        print(f"timeout occurred after waiting {timeout} seconds for {friendly_name}")
        sys.exit(1)

    if timeout > 0:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(timeout)
        print(f"waiting {timeout} seconds for {friendly_name}")
    else:
        print(f"waiting for {friendly_name} without a timeout")

    t1 = time.time()

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s = sock.connect_ex((host, port))
            if s == 0:
                seconds = round(time.time() - t1)
                print(f"{friendly_name} is available after {seconds} seconds")
                break
        except socket.gaierror:
            pass
        finally:
            time.sleep(1)

    signal.alarm(0)


#####################################################
# End Configuration to use neo4j started by tox-docker
#####################################################


@pytest.fixture(scope="session")
def session_app() -> Flask:
    import dhos_observations_api.app

    app = dhos_observations_api.app.create_app(testing=True)
    if os.environ.get("DATABASE_PORT"):
        # Override fbi use of sqlite to run tests with Postgres
        app.config.from_object(RealSqlDbConfig())
    return app


@pytest.fixture
def app(mocker: MockFixture, session_app: Flask) -> Flask:
    from flask_batteries_included.helpers.security import _ProtectedRoute

    def mock_claims(self: Any, verify: bool = True) -> Tuple:
        return g.jwt_claims, g.jwt_scopes

    mocker.patch.object(_ProtectedRoute, "_retrieve_jwt_claims", mock_claims)
    session_app.config["IGNORE_JWT_VALIDATION"] = False
    session_app.config["UNITTESTING"] = True
    session_app.config["ENVIRONMENT"] = "DEVELOPMENT"
    return session_app


@pytest.fixture
def app_context(app: Flask) -> Generator[None, None, None]:
    with app.app_context():
        yield


@pytest.fixture
def mock_publish(mocker: MockFixture) -> Mock:
    return mocker.patch.object(kombu_batteries_included, "publish_message")


@pytest.fixture(autouse=True)
def uses_sql_database() -> None:
    from flask_batteries_included.sqldb import db

    db.drop_all()
    db.create_all()


@pytest.fixture
def clinician() -> str:
    """Override clinician fixture in pytest-dhos so that jwt_send_clinician_uuid doesn't hit neo4j"""
    return generate_uuid()


@pytest.fixture
def location_uuid() -> str:
    return generate_uuid()


@pytest.fixture
def encounter_uuid() -> str:
    return generate_uuid()


@pytest.fixture
def patient_uuid() -> str:
    return generate_uuid()


@pytest.fixture
def jwt_contains_referring_device_id() -> str:
    from flask import g

    device_uuid = generate_uuid()
    g.jwt_claims["referring_device_id"] = device_uuid

    return device_uuid


@pytest.fixture()
def mocked_get_patient_observations(mocker: MockFixture) -> Mock:
    """Fixture to mock dhos_adapter.publish"""

    my_data = [
        {
            "patient_id": "1",
            "record_time": "1970-01-03T00:00:12.000Z",
            "observations": [
                {
                    "observation_type": "temp",
                    "observation_value": 37.5,
                    "measured_time": "1970-01-01T00:00:00.000Z",
                }
            ],
        },
        {
            "patient_id": "1",
            "record_time": "1970-01-03T00:00:10.000Z",
            "observations": [
                {
                    "observation_type": "temp",
                    "observation_value": 37.5,
                    "measured_time": "1970-01-01T00:00:01.000Z",
                }
            ],
        },
        {
            "patient_id": "1",
            "record_time": "1970-01-03T00:00:20.000Z",
            "observations": [
                {
                    "observation_type": "temp",
                    "observation_value": 37.5,
                    "measured_time": "1970-01-01T00:00:02.000Z",
                }
            ],
        },
    ]
    return mocker.patch(
        "dhos_observations_api.blueprint_api.controller.get_observation_sets_for_patient",
        return_value=my_data,
    )


@pytest.fixture()
def mocked_get_observations(mocker: MockFixture) -> Mock:
    """Fixture to mock dhos_adapter.publish"""

    my_data = [
        {
            "location": "location_uuid",
            "encounter_id": "1",
            "record_time": "1970-01-03T00:00:12.000Z",
            "score_system": "news2",
            "spo2_scale": 1,
            "observations": [
                {
                    "observation_type": "spo2",
                    "measured_time": "1970-01-01T00:00:00.000Z",
                }
            ],
        },
        {
            "location": "location_uuid",
            "encounter_id": "2",
            "record_time": "1970-01-03T00:00:10.000Z",
            "score_system": "news2",
            "spo2_scale": 1,
            "observations": [
                {
                    "observation_type": "spo2",
                    "measured_time": "1970-01-01T00:00:01.000Z",
                }
            ],
        },
        {
            "location": "location_uuid",
            "encounter_id": "3",
            "record_time": "1970-01-03T00:00:20.000Z",
            "score_system": "news2",
            "spo2_scale": 1,
            "observations": [
                {
                    "observation_type": "spo2",
                    "measured_time": "1970-01-01T00:00:02.000Z",
                }
            ],
        },
    ]
    return mocker.patch(
        "dhos_observations_api.blueprint_api.controller.get_observation_sets_by_locations_and_date_range",
        return_value=my_data,
    )


@pytest.fixture
def aggregate_observation_sets() -> Dict:
    return {
        "late": 8,
        "on_time": 22,
        "risk": {
            "low": {"on_time": 9, "late": 1},
            "medium": {"on_time": 8, "late": 2},
            "high": {"on_time": 5, "late": 5},
        },
        "location_uuid_1": {
            "on_time": 22,
            "late": 8,
            "date": {
                "2021-01-01": {
                    "on_time": 22,
                    "late": 8,
                    "risk": {
                        "low": {"on_time": 9, "late": 1},
                        "medium": {"on_time": 8, "late": 2},
                        "high": {"on_time": 5, "late": 5},
                    },
                }
            },
            "risk": {
                "low": {"on_time": 9, "late": 1},
                "medium": {"on_time": 8, "late": 2},
                "high": {"on_time": 5, "late": 5},
            },
        },
    }


@pytest.fixture
def aggregate_missing_observation_sets() -> Dict:
    return {
        "total_obs_sets": 30,
        "num_obs_missing": 5,
        "o2_therapy_status_missing": 3,
        "heart_rate_missing": 3,
        "spo2_missing": 1,
        "temperature_missing": 5,
        "diastolic_blood_pressure_missing": 0,
        "respiratory_rate_missing": 1,
        "consciousness_acvpu_missing": 4,
        "systolic_blood_pressure_missing": 0,
        "location_uuid_1": {
            "total_obs_sets": 30,
            "num_obs_missing": 5,
            "o2_therapy_status_missing": 3,
            "heart_rate_missing": 3,
            "spo2_missing": 1,
            "temperature_missing": 5,
            "diastolic_blood_pressure_missing": 0,
            "respiratory_rate_missing": 1,
            "consciousness_acvpu_missing": 4,
            "systolic_blood_pressure_missing": 0,
        },
    }


@pytest.fixture
def aggregate_observation_intervals() -> Dict:
    risk: Dict = {
        "low": {
            "minus60": 121,
            "minus45_59": 91,
            "minus30_44": 81,
            "minus15_29": 71,
            "minus0_14": 81,
            "plus1_15": 91,
            "plus16_30": 101,
            "plus31_45": 111,
            "plus46_60": 101,
            "plus61_75": 91,
            "plus76_90": 71,
            "plus91_105": 61,
            "plus106_120": 51,
            "plus121_135": 41,
            "plus136_150": 31,
            "plus151_165": 21,
            "plus166_180": 11,
            "plus180": 51,
        }
    }
    return {"risk": {**risk}, "location_uuid_1": {"risk": {**risk}}}


@pytest.fixture
def create_aggregate_observation_intervals() -> str:
    obj1 = AggObservationSets(
        record_day="2021-01-01",
        location_id="location_uuid_1",
        score_severity="low",
        all_obs_sets=1220,
        late_obs_sets=0,
        missing_obs=0,
        o2_therapy_status=0,
        heart_rate=0,
        spo2=0,
        temperature=0,
        diastolic_blood_pressure=0,
        respiratory_rate=0,
        consciousness_acvpu=0,
        systolic_blood_pressure=0,
        nurse_concern=0,
        minus60=120,
        minus45_59=90,
        minus30_44=80,
        minus15_29=70,
        minus0_14=80,
        plus1_15=90,
        plus16_30=100,
        plus31_45=110,
        plus46_60=100,
        plus61_75=90,
        plus76_90=70,
        plus91_105=60,
        plus106_120=50,
        plus121_135=40,
        plus136_150=30,
        plus151_165=20,
        plus166_180=10,
        plus180=50,
    )
    obj2 = AggObservationSets(
        record_day="2021-01-02",
        location_id="location_uuid_1",
        score_severity="low",
        all_obs_sets=1220,
        late_obs_sets=0,
        missing_obs=0,
        o2_therapy_status=0,
        heart_rate=0,
        spo2=0,
        temperature=0,
        diastolic_blood_pressure=0,
        respiratory_rate=0,
        consciousness_acvpu=0,
        systolic_blood_pressure=0,
        nurse_concern=0,
        minus60=1,
        minus45_59=1,
        minus30_44=1,
        minus15_29=1,
        minus0_14=1,
        plus1_15=1,
        plus16_30=1,
        plus31_45=1,
        plus46_60=1,
        plus61_75=1,
        plus76_90=1,
        plus91_105=1,
        plus106_120=1,
        plus121_135=1,
        plus136_150=1,
        plus151_165=1,
        plus166_180=1,
        plus180=1,
    )
    db.session.add(obj1)
    db.session.add(obj2)
    db.session.commit()
    return "created"


@pytest.fixture
def agg_observation_sets_by_month() -> dict:
    return {
        "2021-09": {
            "all_obs_sets": 100,
            "on_time": 20,
            "low": 25,
            "low_medium": 25,
            "medium": 25,
            "high": 25,
            "missing_obs": 40,
            "o2_therapy_status": 4,
            "heart_rate": 4,
            "spo2": 8,
            "temperature": 8,
            "diastolic_blood_pressure": 16,
            "respiratory_rate": 16,
            "consciousness_acvpu": 32,
            "systolic_blood_pressure": 32,
            "nurse_concern": 32,
        },
        "2021-08": {
            "all_obs_sets": 140,
            "on_time": 35,
            "low": 35,
            "low_medium": 35,
            "medium": 35,
            "high": 35,
            "missing_obs": 80,
            "o2_therapy_status": 8,
            "heart_rate": 8,
            "spo2": 16,
            "temperature": 16,
            "diastolic_blood_pressure": 32,
            "respiratory_rate": 32,
            "consciousness_acvpu": 64,
            "systolic_blood_pressure": 64,
            "nurse_concern": 64,
        },
    }


@pytest.fixture
def agg_observation_sets_by_location_month() -> dict:
    return {
        "location_uuid_1": {
            "2021-09": {
                "all_obs_sets": 100,
                "on_time": 20,
                "low": 25,
                "low_medium": 25,
                "medium": 25,
                "high": 25,
                "missing_obs": 40,
                "o2_therapy_status": 4,
                "heart_rate": 4,
                "spo2": 8,
                "temperature": 8,
                "diastolic_blood_pressure": 16,
                "respiratory_rate": 16,
                "consciousness_acvpu": 32,
                "systolic_blood_pressure": 32,
                "nurse_concern": 32,
            },
            "2021-08": {
                "all_obs_sets": 140,
                "on_time": 35,
                "low": 35,
                "low_medium": 35,
                "medium": 35,
                "high": 35,
                "missing_obs": 80,
                "o2_therapy_status": 8,
                "heart_rate": 8,
                "spo2": 16,
                "temperature": 16,
                "diastolic_blood_pressure": 32,
                "respiratory_rate": 32,
                "consciousness_acvpu": 64,
                "systolic_blood_pressure": 64,
                "nurse_concern": 64,
            },
        }
    }
