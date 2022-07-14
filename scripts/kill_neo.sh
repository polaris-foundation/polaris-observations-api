#!/usr/bin/env bash
set -e

if [ -z ${CIRCLECI} ]; then
    cd "$( dirname "$0" )"
    docker-compose down
fi
