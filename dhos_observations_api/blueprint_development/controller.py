# -*- coding: utf-8 -*-
from flask_batteries_included.sqldb import db
from she_logging import logger

from dhos_observations_api.models.sql.observation import Observation
from dhos_observations_api.models.sql.observation_metadata import ObservationMetaData
from dhos_observations_api.models.sql.observation_set import ObservationSet


def reset_database() -> None:
    """Drops SQL data only, Neo4j data is dropped from dhos-services-api"""
    try:
        for model in (ObservationMetaData, Observation, ObservationSet):
            db.session.query(model).delete()
        db.session.commit()
    except Exception:
        logger.exception("Drop SQL data failed")
        db.session.rollback()
