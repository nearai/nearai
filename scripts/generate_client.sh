#!/bin/sh

# manually update near-openapi.json
# it can be fetched from the locally running hub at http://localhost:9000/openapi.json
# curl http://localhost:9000/openapi.json | jq  > near-openapi.json

# https://openapi-generator.tech/docs/generators/python
openapi-generator-cli generate -i near-openapi.json -g python -o /tmp/nearai_api_client/

rm -rf ../openapi_client/
cp -r /tmp/nearai_api_client/openapi_client/ ../openapi_client/
