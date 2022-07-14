#!/bin/bash

SERVER_PORT=${1-5000}
export SERVER_PORT=${SERVER_PORT}
export DATABASE_HOST=localhost
export DATABASE_PORT=15432
export AUTH0_DOMAIN=https://login-sandbox.sensynehealth.com/
export AUTH0_AUDIENCE=https://dev.sensynehealth.com/
export AUTH0_METADATA=https://gdm.sensynehealth.com/metadata
export AUTH0_JWKS_URL=https://login-sandbox.sensynehealth.com/.well-known/jwks.json
export RABBITMQ_DISABLED=true
export ENVIRONMENT=DEVELOPMENT
export ALLOW_DROP_DATA=true
export PROXY_URL=http://localhost
export HS_KEY=secret
export FLASK_APP=dhos_observations_api/autoapp.py
export IGNORE_JWT_VALIDATION=true
export REDIS_INSTALLED=False
export LOG_FORMAT=colour
export DATABASE_USER=dhos-observations
export DATABASE_PASSWORD=dhos-observations
export DATABASE_NAME=dhos-observations-db

scripts/setup_local.sh

if [ -z "$*" ]
then
   python -m dhos_observations_api
else
  flask "$@"
fi
