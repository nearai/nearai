# NearAI AWS Runner
A docker container that runs on AWS Lambda to run NearAI agents.
 * This is invoked by the NearAI Api server or NearAI cli.
 * The runner calls back to the NearAI Api server for inference, 
to fetch agent code, and to fetch and store environments (store not implemented yet).


## Local testing
`docker build --platform linux/amd64 -t nearai-runner:test .`

`docker run --platform linux/amd64 -p 9000:8080 nearai-runner:test`

This will start the server on port 9000. To call the server you will need a signedMessage for the auth param.
```
curl "http://localhost:9000/2015-03-31/functions/function/invocations" \
-d @- <<'EOF'
  {
    "agents": "xela-agent", 
    "environment_id":"environment_run_xela-tools-agent_541869e6753c41538c87cb6f681c6932", 
    "auth":"{\"account_id\":\"your_account.near\",
        \"public_key\":\"ed25519:F5DeKFoya9fl35hapvpXxwReoksgi9a677JkniDIFLAW\",
        \"signature\":\"SIGNATURE_FIELD_FROM_A_REAL_SIGNATURE\",
        \"callback_url\":\"https://demo.near.ai/auth/login\",\"plainMsg\":\"Welcome to NEAR Talkbot app\"}"}
EOF
```