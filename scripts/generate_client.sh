#!/bin/sh
set -e

# manually update near-openapi.json
# it can be fetched from the locally running hub at http://localhost:9000/openapi.json
# curl http://localhost:9000/openapi.json | jq  > near-openapi.json

# https://openapi-generator.tech/docs/generators/python

#determine whether the command is installed as openapi-generator-cli or openapi-generator
if command -v openapi-generator-cli 2>&1 /dev/null
then
  OPENAPI_GENERATOR="openapi-generator-cli"
elif command -v openapi-generator 2>&1 /dev/null
then
  OPENAPI_GENERATOR="openapi-generator"
else
  echo "openapi-generator-cli or openapi-generator not found"
  echo "Install it from https://openapi-generator.tech/docs/installation"
  exit 1
fi

$OPENAPI_GENERATOR generate -i near-openapi.json -g python -o /tmp/nearai_api_client/ --package-name nearai.openapi_client

rm -rf ../nearai/openapi_client/
cp -r /tmp/nearai_api_client/nearai/openapi_client/ ../nearai/openapi_client/
