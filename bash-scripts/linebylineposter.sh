#!/bin/bash
input="$1"
okapi_url_and_path="$2"
tenant_id="$3"
okapi_token="$4"
while IFS= read -r line
do
curl -POST $okapi_url_and_path  -d "${line}" -H "x-okapi-tenant: $tenant_id" -H "x-okapi-token: $okapi_token" -H "Content-Type: application/json" -s -S
done < "$input"