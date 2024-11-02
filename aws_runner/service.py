# -*- coding: utf-8 -*-
import time
from subprocess import call

from shared.agents.agent_runner import run_with_environment, write_metric
from shared.auth_data import AuthData
from shared.near.sign import SignatureVerificationResult, verify_signed_message


def handler(event, context):
    start_time = time.perf_counter()
    required_params = ["agents", "auth"]
    agents = event.get("agents")
    auth = event.get("auth")
    if not agents or not auth:
        missing = list(filter(lambda x: event.get(x) is (None or ""), required_params))
        return f"Missing required parameters: {missing}"

    auth_object = auth if isinstance(auth, AuthData) else AuthData(**auth)
    start_time_val = time.perf_counter()
    verification_result = verify_signed_message(
        auth_object.account_id,
        auth_object.public_key,
        auth_object.signature,
        auth_object.message,
        auth_object.nonce,
        auth_object.recipient,
        auth_object.callback_url,
    )

    if verification_result == SignatureVerificationResult.VERIFY_ACCESS_KEY_OWNER_SERVICE_NOT_AVAILABLE:
        write_metric("AdminNotifications", "SignatureAccessKeyVerificationServiceFailed", "Count")
    elif not verification_result:
        return "Unauthorized: Invalid signature"
    else:
        # signature is valid
        stop_time_val = time.perf_counter()
        write_metric("VerifySignatureDuration", stop_time_val - start_time_val)

    environment_id = event.get("environment_id")
    new_message = event.get("new_message")
    thread_id = event.get("thread_id")
    run_id = event.get("run_id")

    params = event.get("params", {})

    new_environment_registry_id = run_with_environment(
        agents,
        auth_object,
        thread_id,
        run_id,
        new_message=new_message,
        params=params,
    )
    if not new_environment_registry_id:
        return f"Run not recorded. Ran {agents} agent(s) with generated near client and environment {environment_id}"

    call("rm -rf /tmp/..?* /tmp/.[!.]* /tmp/*", shell=True)
    stop_time = time.perf_counter()
    write_metric("TotalRunnerDuration", stop_time - start_time)
    return new_environment_registry_id
