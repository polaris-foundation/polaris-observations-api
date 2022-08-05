import itertools
import uuid
from datetime import datetime, timedelta, timezone
from random import randint
from typing import Any, Callable, Dict, List

import pytest
from flask import jsonify
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import UnprocessibleEntityException
from flask_batteries_included.sqldb import db

from dhos_observations_api.blueprint_api.controller import (
    get_latest_observation_set_for_encounters,
    get_latest_observation_sets_by_encounter_ids,
    get_observation_sets,
    get_observation_sets_by_locations_and_date_range,
    get_observation_sets_for_patient,
    update_mins_late_for_encounter,
)
from dhos_observations_api.models.api_spec import (
    ObservationRequest,
    ObservationSetResponse,
)
from dhos_observations_api.models.sql.observation_set import ObservationSet


@pytest.mark.usefixtures("app", "jwt_send_clinician_uuid", "uses_sql_database")
class TestObservationSet:
    def test_new_method(self, encounter_uuid: str, location_uuid: str) -> None:
        record_time = datetime(2019, 1, 1, 11, 59, 50, tzinfo=timezone.utc)
        measured_time = datetime(2019, 1, 1, 11, 59, 0, tzinfo=timezone.utc)
        return_value = ObservationSet.new(
            observations=[
                {
                    "observation_type": "spo2",
                    "measured_time": measured_time,
                    "observation_value": 1,
                }
            ],
            record_time=record_time,
            score_system="news2",
            spo2_scale=1,
            encounter_id=encounter_uuid,
            location=location_uuid,
        )
        db.session.commit()
        assert return_value["encounter_id"] == encounter_uuid
        assert return_value["location"] == location_uuid

        # Tests use sqlite which strips timezone.
        assert return_value["record_time"].replace(tzinfo=timezone.utc) == record_time
        assert (
            return_value["observations"][0]["measured_time"].replace(
                tzinfo=timezone.utc
            )
            == measured_time
        )

    def test_new_method_spo2_default(
        self, encounter_uuid: str, location_uuid: str
    ) -> None:
        record_time = datetime(2019, 1, 1, 11, 59, 50, tzinfo=timezone.utc)
        measured_time = datetime(2019, 1, 1, 11, 59, 0, tzinfo=timezone.utc)
        return_value = ObservationSet.new(
            observations=[
                {
                    "observation_type": "spo2",
                    "measured_time": measured_time,
                    "observation_value": 1,
                }
            ],
            record_time=record_time,
            score_system="news2",
            encounter_id=encounter_uuid,
            location=location_uuid,
        )
        db.session.commit()
        assert return_value["spo2_scale"] == 1

    def test_returns_latest_observation_set(self, encounter_uuid: str) -> None:
        for i in range(10):
            record_time = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)

            ObservationSet.new(
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                encounter_id=encounter_uuid,
            )

        record_time = datetime(2020, 1, 1, 11, 59, 20, tzinfo=timezone.utc)

        ObservationSet.new(
            observations=[],
            record_time=record_time,
            score_system="news2",
            spo2_scale=1,
            encounter_id="different_encounter",
        )
        db.session.commit()

        obs_set = get_latest_observation_set_for_encounters([encounter_uuid])
        assert isinstance(obs_set, dict)
        assert obs_set["record_time"] == datetime(
            2019, 1, 1, 11, 59, 29, tzinfo=timezone.utc
        )
        assert obs_set["encounter_id"] == encounter_uuid

    @pytest.fixture
    def bulk_obs_times(self) -> List[datetime]:
        OBS_PER_ENCOUNTER = 4
        base_record_time = datetime(2019, 1, 1, 11, 59, 20, tzinfo=timezone.utc)
        obs_record_times = [
            base_record_time + timedelta(seconds=i) for i in range(OBS_PER_ENCOUNTER)
        ]
        return obs_record_times

    @pytest.fixture
    def bulk_encounter_data(self, bulk_obs_times: List[datetime]) -> List[str]:
        NUM_ENCOUNTERS = 5

        encounter_uuids = []
        with db.session.begin(subtransactions=True):
            for e in range(NUM_ENCOUNTERS):
                encounter_uuid = generate_uuid()
                for record_time in bulk_obs_times:
                    ObservationSet.new(
                        observations=[
                            {
                                "observation_type": "o2_therapy_status",
                                "patient_refused": False,
                                "observation_unit": "",
                                "measured_time": record_time,
                                "observation_value": 0,
                                "observation_metadata": {
                                    "mask": "Room Air",
                                    "mask_percent": None,
                                },
                                "score_value": 0,
                            },
                            {
                                "observation_type": "respiratory_rate",
                                "patient_refused": False,
                                "observation_unit": "/min",
                                "measured_time": record_time,
                                "observation_value": 35,
                                "score_value": 3,
                            },
                        ],
                        record_time=record_time,
                        score_system="news2",
                        spo2_scale=1,
                        encounter_id=encounter_uuid,
                    )

                encounter_uuids.append(encounter_uuid)

        return encounter_uuids

    def test_returns_latest_observation_sets(
        self, bulk_encounter_data: List[str], bulk_obs_times: List[datetime]
    ) -> None:
        obs_sets = get_latest_observation_sets_by_encounter_ids(bulk_encounter_data)

        assert len(obs_sets) == len(bulk_encounter_data)

        for key in obs_sets:
            obs_set = obs_sets[key]
            assert isinstance(obs_set, dict)
            assert obs_set["record_time"] == bulk_obs_times[-1]

    @pytest.mark.parametrize(
        "start_date,end_date",
        [
            ("2019-01-03T12:00:01.000Z", "2019-01-04T12:00:01.000Z"),
            ("2019-01-03T12:00:01.000", "2019-01-04T12:00:01.000Z"),
            ("2019-01-03T12:00:01.000Z", "2019-01-04T12:00"),
            ("2019-01-03T12:00:01.000Z", "2019-01-04"),
        ],
    )
    def test_returns_observation_sets_at_a_location(
        self, start_date: str, end_date: str, statement_counter: Callable
    ) -> None:
        location_uuid: str = generate_uuid()
        encounter_uuid: str = generate_uuid()
        for i in range(5):
            record_time = datetime(2019, 1, i + 1, 11, 59, 20 + i, tzinfo=timezone.utc)
            ObservationSet.new(
                observations=[
                    {
                        "observation_type": "o2_therapy_status",
                        "patient_refused": False,
                        "observation_unit": "L/min",
                        "measured_time": record_time,
                        "observation_value": 22,
                        "observation_metadata": {
                            "mask": "High Flow",
                            "mask_percent": 35,
                        },
                    },
                ],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                encounter_id=encounter_uuid,
                location=location_uuid,
            )

        with statement_counter(limit=1):
            response = get_observation_sets_by_locations_and_date_range(
                location_uuids=[location_uuid],
                start_date_str=start_date,
                end_date_str=end_date,
            )
        obs = jsonify(response).json
        assert obs
        obs_sets: List[Dict[str, Any]] = ObservationSetResponse().load(obs, many=True)

        assert len(obs_sets) == 1
        assert obs_sets[0]["record_time"] == datetime(
            2019, 1, 4, 11, 59, 23, tzinfo=timezone.utc
        )
        assert obs_sets[0]["mins_late"] is None

    def test_returns_observation_sets_at_a_parent_location(
        self,
    ) -> None:
        location_uuid_1: str = generate_uuid()
        location_uuid_2: str = generate_uuid()
        encounter_uuid: str = generate_uuid()

        for i in range(5):
            record_time = datetime(1970, 1, i + 1, 0, 0, 1, tzinfo=timezone.utc)
            ObservationSet.new(
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                encounter_id=encounter_uuid,
                location=location_uuid_2,
            )

        response = get_observation_sets_by_locations_and_date_range(
            location_uuids=[location_uuid_1, location_uuid_2],
            start_date_str="1970-01-03T12:00:01.000Z",
            end_date_str="1970-01-04T12:00:01.000Z",
        )
        obs = jsonify(response).json
        assert obs
        obs_sets: List[Dict[str, Any]] = ObservationSetResponse().load(obs, many=True)
        assert len(obs_sets) == 1
        assert obs_sets[0]["record_time"] == datetime(
            1970, 1, 4, 0, 0, 1, tzinfo=timezone.utc
        )

    def test_returns_observation_sets_at_parent_and_child_locations(
        self,
    ) -> None:
        location_uuid_1: str = generate_uuid()
        location_uuid_2: str = generate_uuid()
        encounter_uuid_1: str = generate_uuid()
        encounter_uuid_2: str = generate_uuid()

        for i in range(5):
            record_time = datetime(1970, 1, i + 1, 0, 0, 1, tzinfo=timezone.utc)
            ObservationSet.new(
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                encounter_id=encounter_uuid_1,
                location=location_uuid_1,
            )

        for i in range(5):
            ObservationSet.new(
                observations=[],
                record_time=datetime(1970, 1, i + 1, 0, 0, 1, tzinfo=timezone.utc),
                score_system="news2",
                spo2_scale=1,
                encounter_id=encounter_uuid_2,
                location=location_uuid_2,
            )

        response = get_observation_sets_by_locations_and_date_range(
            location_uuids=[location_uuid_1, location_uuid_2],
            start_date_str="1970-01-03T12:00:01.000Z",
            end_date_str="1970-01-04T12:00:01.000Z",
        )
        obs = jsonify(response).json
        assert obs
        obs_sets: List[Dict[str, Any]] = ObservationSetResponse().load(obs, many=True)

        assert len(obs_sets) == 2
        assert obs_sets[0]["record_time"] == datetime(
            1970, 1, 4, 0, 0, 1, tzinfo=timezone.utc
        )
        assert obs_sets[1]["record_time"] == datetime(
            1970, 1, 4, 0, 0, 1, tzinfo=timezone.utc
        )

    def test_returns_observation_sets_at_a_parent_location_compact_dict(
        self,
    ) -> None:
        location_uuid: str = generate_uuid()
        encounter_uuid: str = generate_uuid()

        for i in range(5):
            record_time = datetime(1970, 1, i + 1, 0, 0, 1, tzinfo=timezone.utc)
            ObservationSet.new(
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                encounter_id=encounter_uuid,
                location=location_uuid,
            )

        obs_sets = get_observation_sets_by_locations_and_date_range(
            location_uuids=[location_uuid],
            start_date_str="1970-01-03T12:00:01.000Z",
            end_date_str="1970-01-04T12:00:01.000Z",
            compact=True,
        )
        assert len(obs_sets) == 1
        assert type(obs_sets[0]["uuid"]) is str

    def test_returns_observation_sets_at_a_parent_location_throws_an_error_for_bad_dates(
        self,
    ) -> None:
        with pytest.raises(UnprocessibleEntityException):
            get_observation_sets_by_locations_and_date_range(
                location_uuids=["location_uuid"],
                start_date_str="1970-01-03T12:00:01.000Z",
                end_date_str="1970-01-02T12:00:01.000Z",
            )

    def test_returns_observation_sets_at_empty_location(self) -> None:
        location_uuid_1: str = generate_uuid()
        obs_sets = get_observation_sets_by_locations_and_date_range(
            location_uuids=[location_uuid_1],
            start_date_str="1970-01-03T12:00:01.000Z",
            end_date_str="1970-01-04T12:00:01.000Z",
        )
        assert len(obs_sets) == 0
        assert obs_sets == []

    def test_returns_observation_set_by_patient_id(
        self, patient_uuid: str, clinician: str
    ) -> None:
        for i in range(5):
            record_time = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)
            created = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)
            modified = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)

            ObservationSet.new(
                observations=[],
                record_time=record_time,
                patient_id=patient_uuid,
                created=created,
                modified=modified,
            )

        for i in range(5):
            different_patient_id = generate_uuid()
            record_time = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)
            created = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)
            modified = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)
            ObservationSet.new(
                observations=[],
                record_time=record_time,
                patient_id=different_patient_id,
                created=created,
                modified=modified,
            )

        db.session.commit()

        obs_sets = get_observation_sets_for_patient(patient_id=patient_uuid)

        response = jsonify(obs_sets[0])
        assert response.json
        parsed: Dict[str, Any] = ObservationSetResponse().load(response.json)

        assert isinstance(obs_sets, list)
        assert len(obs_sets) == 5
        assert parsed["patient_id"] == patient_uuid


@pytest.mark.usefixtures("app", "jwt_send_clinician_uuid", "uses_sql_database")
class TestBulkObservations:
    def _random_obs(
        self, observation_type: str, measured_time: datetime
    ) -> ObservationRequest.Meta.Dict:
        return {
            "observation_metadata": {"patient_position": "upright"},
            "observation_value": randint(0, 99),
            "observation_type": observation_type,
            "measured_time": measured_time,
        }

    def _random_obs_set(
        self, record_time: datetime, patient_uuid: str, obs_count: int
    ) -> None:
        observation_type: itertools.cycle[str] = itertools.cycle(
            [
                "temperature",
                "subjective_fever",
                "continuous_cough",
                "illness",
                "something_else",
            ]
        )
        ObservationSet.new(
            record_time=record_time,
            observations=[
                self._random_obs(next(observation_type), measured_time=record_time)
                for d in range(obs_count)
            ],
            patient_id=patient_uuid,
        )

    def _random_patient(self, obs_set_count: int, obs_per_set: int) -> str:
        today = datetime.utcnow().replace(tzinfo=timezone.utc)
        patient_uuid = generate_uuid()
        for i in range(obs_set_count):
            obs_time = today - timedelta(days=obs_set_count - i)
            self._random_obs_set(
                record_time=obs_time, patient_uuid=patient_uuid, obs_count=obs_per_set
            )

        return patient_uuid

    @pytest.fixture
    def bulk_patient_uuids(
        self, bulk_patients: int, sets_per_patient: int, obs_per_set: int
    ) -> List[str]:
        patients = [
            self._random_patient(
                obs_set_count=sets_per_patient, obs_per_set=obs_per_set
            )
            for i in range(bulk_patients)
        ]
        db.session.commit()
        return patients

    @pytest.mark.parametrize("bulk_patients,sets_per_patient,obs_per_set", [(3, 20, 5)])
    def test_get_observation_sets_for_patient(
        self, bulk_patient_uuids: List[str], sets_per_patient: int
    ) -> None:
        obs_sets = get_observation_sets_for_patient(patient_id=bulk_patient_uuids[1])
        assert len(obs_sets) == sets_per_patient

    def test_get_observation_sets(self) -> None:
        for i in range(10):
            record_time = datetime(2019, 1, 1, 11, 59, 20 + i, tzinfo=timezone.utc)

            ObservationSet.new(
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                encounter_id=str(uuid.uuid4()),
            )
        db.session.commit()

        obs_sets = get_observation_sets(modified_since="1970-01-01", compact=False)
        assert len(obs_sets) == 10

        now = datetime.now()
        obs_sets = get_observation_sets(modified_since=now.isoformat(), compact=False)
        assert len(obs_sets) == 0

    def test_mins_late(self) -> None:
        uuids_1: List = []
        uuids_2: List = []
        encounter_id_1: str = str(uuid.uuid4())
        encounter_id_2: str = str(uuid.uuid4())
        mins_late: List = [0, -60, -60, -60, -60, -60, -60, -60, -60, -60]
        for i in range(10):
            record_time = datetime(2019, 1, 1, 11 + i, 0, 0, tzinfo=timezone.utc)
            time_next_obs_set_due = datetime(
                2019, 1, 1, 13 + i, 0, 0, tzinfo=timezone.utc
            )
            id_1: str = str(uuid.uuid4())
            uuids_1.append(id_1)
            id_2: str = str(uuid.uuid4())
            uuids_2.append(id_2)
            ObservationSet.new(
                uuid=id_1,
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                time_next_obs_set_due=time_next_obs_set_due,
                encounter_id=encounter_id_1,
            )
            ObservationSet.new(
                uuid=id_2,
                observations=[],
                record_time=record_time,
                score_system="news2",
                spo2_scale=1,
                time_next_obs_set_due=time_next_obs_set_due,
                encounter_id=encounter_id_2,
            )

        db.session.commit()
        update_mins_late_for_encounter(encounter_id=encounter_id_1)
        update_mins_late_for_encounter(encounter_id=encounter_id_2)
        for i, id in enumerate(uuids_1):
            os = ObservationSet.query.filter(ObservationSet.uuid == id).first()
            assert os.mins_late == mins_late[i]
        for i, id in enumerate(uuids_2):
            os = ObservationSet.query.filter(ObservationSet.uuid == id).first()
            assert os.mins_late == mins_late[i]
