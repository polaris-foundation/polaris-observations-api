#!/usr/bin/env bash
set -e

if [ ${CIRCLECI} ]; then
    echo "running on circle ci";
else
    echo "running locally";

    cd "$( dirname "$0" )"
    docker-compose up -d && docker wait dhos-observations-dependencies

    printf "\rStarted!\n"
fi
