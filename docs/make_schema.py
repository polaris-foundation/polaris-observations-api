import codecs
import subprocess

import sadisplay

from dhos_observations_api.models.sql import (
    observation,
    observation_metadata,
    observation_set,
)

desc = sadisplay.describe(
    [
        observation.Observation,
        observation_set.ObservationSet,
        observation_metadata.ObservationMetaData,
    ]
)
with codecs.open("docs/schema.plantuml", "w", encoding="utf-8") as f:
    f.write(sadisplay.plantuml(desc).rstrip() + "\n")

with codecs.open("docs/schema.dot", "w", encoding="utf-8") as f:
    f.write(sadisplay.dot(desc).rstrip() + "\n")

my_cmd = ["dot", "-Tpng", "docs/schema.dot"]
with open("docs/schema.png", "w") as outfile:
    subprocess.run(my_cmd, stdout=outfile)
