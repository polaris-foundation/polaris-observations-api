#!/usr/bin/env bash

set -eux

# The Dockerfiles require these
for SERVICE_FOLDER in ${SERVICE_FOLDERS}; do
    touch ${SERVICE_FOLDER}/build-circleci.txt
    touch ${SERVICE_FOLDER}/build-githash.txt
done

TEST_CONTAINER_NAME=$(git remote -v | head -1 | cut -d/ -f2 | sed 's/-api.*/-integration-tests/')

cd integration-tests

# Start the containers, backgrounded so we can do docker wait
# Pre pulling the postgres image so wait-for-it doesn't time out
docker-compose rm -f
docker-compose pull
docker-compose up --build --force-recreate -d

# Wait for the integration-tests container to finish, and assign to RESULT
RESULT=$(docker wait ${TEST_CONTAINER_NAME})

# Print logs based on the test results
if [ "$RESULT" -ne 0 ];
then
  docker-compose logs
else
  docker-compose logs ${TEST_CONTAINER_NAME}
fi

# Stop the containers
docker-compose down

# Exit based on the test results
if [ "$RESULT" -ne 0 ]; then
  echo "Tests failed :-("
  exit 1
fi

echo "Tests passed! :-)"
