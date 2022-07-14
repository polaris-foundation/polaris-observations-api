import pytest

from dhos_observations_api.models.sql.observation import Observation


@pytest.mark.usefixtures("app", "uses_sql_database")
class TestObservation:
    def test_new_method(self) -> None:
        obs = Observation.new(
            observation_value=1,
            observation_type="temperature",
            measured_time="1970-01-01T00:00:00.000Z",
        )
        assert isinstance(obs, Observation)

    def test_raises_error_when_missing_either_value_or_string(self) -> None:
        with pytest.raises(KeyError):
            Observation.new(
                patient_refused=False,
                observation_type="temperature",
                measured_time="1970-01-01T00:00:00.000Z",
            )

    def test_raises_error_when_has_both_value_and_string(self) -> None:
        with pytest.raises(KeyError):
            Observation.new(
                observation_value=1,
                observation_string="1",
                observation_type="temperature",
                measured_time="1970-01-01T00:00:00.000Z",
            )

    def test_success_with_type(self) -> None:
        obs = Observation.new(
            observation_value=1,
            observation_type="temperature",
            measured_time="1970-01-01T00:00:00.000Z",
        )
        assert isinstance(obs, Observation)

    def test_success_with_string(self) -> None:
        obs = Observation.new(
            observation_string="1",
            observation_type="temperature",
            measured_time="1970-01-01T00:00:00.000Z",
        )
        assert isinstance(obs, Observation)

    def test_success_with_patient_refused(self) -> None:
        obs = Observation.new(
            patient_refused=True,
            observation_type="temperature",
            measured_time="1970-01-01T00:00:00.000Z",
        )
        assert isinstance(obs, Observation)
