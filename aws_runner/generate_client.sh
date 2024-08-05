#!/bin/sh

# manually update openapi_client/near-openapi.json
# it can be fetched from the locally running hub at http://localhost:9000/openapi.json

openapi-generator generate -i openapi_client/near-openapi.json -g python -o /tmp/nearai_api_client/
cp -r /tmp/nearai_api_client/openapi_client/* openapi_client/