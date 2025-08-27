# Verification

[NEAR AI Cloud](https://cloud.near.ai) operates in Trusted Execution Enviornments (TEEs) that uses cryptographic proof to verify that your private AI conversations actually happened in secure, isolated environments - not on compromised systems or with unauthorized access.

This section will show you step-by-step processes for checking these proofs, validating digital signatures, and confirm your AI interactions haven't been tampered with.

---

## Overview

1. **Key Generation:** When the service initializes, it generates a cryptographic signing key pair within the Trusted Execution Environment (TEE).
2. **Attestation Retrieval:** You can obtain CPU and GPU attestation reports that cryptographically verify the service is running on genuine NVIDIA H100/H200/B100 hardware in TEE mode within a Confidential VM.
3. **Key Binding Attestation Reports:** The attestation reports include the public key corresponding to the TEE-generated signing key, establishing a cryptographic link between the hardware environment and the signing capability.
4. **Response Signing:** All AI inference responses are digitally signed using the private key that was generated and remains secured within the TEE.
5. **Verification Process:** You can use the attested public key to verify that all inference results were genuinely generated within the verified TEE environment and haven't been tampered with.

---

## Model Verification

To verify a NEAR AI model is operating in a secure trusted environment, there are two main steps:

- [Request Model Attestation](#request-model-attestation) report from NEAR AI Cloud
- [Verify Model Attestation](#verify-model-attestation) report using NVIDIA & Intel attestation authenticators

---

### Request Model Attestation

To request a model attestation from NEAR AI cloud, use the following `GET` API endpoint:

```bash
https://cloud-api.near.ai/v1/attestation/report?model={model_name}
```

***Example Requests:***

=== "curl"

    ```bash
    curl https://cloud-api.near.ai/v1/attestatuib/report?model=deepseek-chat-v3-0324 \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -H 'Authorization: Bearer <YOUR_NEAR_AI_CLOUD_API_KEY>'

    ```

=== "JavaScript"

    ```js
      const MODEL_NAME = 'deepseek-chat-v3-0324'
      const response = await fetch(
        `https://cloud-api.near.ai/v1/attestation/report?model=${MODEL_NAME}`,
        {
          headers: {
            Authorization: `Bearer ${YOUR_NEARAI_CLOUD_API_KEY}`,
            'Content-Type': 'application/json',
            },
        }
      );
    ```

!!! note
    This endpoint requires [NEAR AI Cloud Account & API Key](./get-started.md#quick-setup)
    
    **Implementation**: This endpoint is defined in the [NEAR AI Private ML SDK](https://github.com/nearai/private-ml-sdk/blob/a23fa797dfd7e676fba08cba68471b51ac9a13d9/vllm-proxy/src/app/api/v1/openai.py#L170).


>

***Example Model Attestation Response:***

```json
{
"signing_address": "...",     \\ TEE Public Key
"nvidia_payload": "...",      \\ Attestation report used to verify w/ NVIDIA
"intel_quote": "...",         \\ Attestation report use to verify w/ Intel
"all_attestations": [         \\ List of all GPU nodes in the network
  {
    "signing_address": "...",
    "nvidia_payload": "...",
    "intel_quote": "..."
  }
]
}
```

- `signing_address`: Account address generated inside TEE that will be used to sign the chat response.

- `nvidia_payload` and `intel_quote`: Attestation report formatted for NVIDIA TEE and Intel TEE respectively. You can use them to verify the integrity of the TEE. See [Verify the Attestation](#verify-the-attestation) for more details.

- `all_attestations`: List attestations from all GPU nodes as multiple TEE nodes may be used to serve inference requests. You can utilize the `signing_address` from `all_attestations` to select the appropriate TEE node for verifying its integrity.

---

### Verify Model Attestation

Once you have [requested a model attestation](#request-model-attestation) from NEAR AI Cloud, you can use the returned payload to verify its authenticity for both GPU & CPU chips. (TEE runs )

#### Verify GPU Attestation

NVIDIA offers a [Remote Attestation Service](https:// docs.nvidia.com/attestation/technical-docs-nras/latest/nras_introduction.html) that allows you to verify that you are using a trusted environment with one of their GPUs. To verify this they require:

- `nonce` - A randomly generated 64 character hexadecimal string
- `arch` - Architecture of the GPU _(HOPPER or BLACKWELL)_
- `evidence_list` - A list of GPU evidence items, each containing an evidence and a corresponding certificate

The `evidence_list` contains Base64 encoded data that lists the GPU's:

- Hardware Identity
- Firmware & Software measurements
- Security confiuguration state
- Endorsement certificates (Signed measurements from the GPU's unique key)

The private key of this GPU is how we can securely verify the authenticity. NVIDIA burns the key in the GPU during manufacturing process and only retains the public key which is used to verify the signature of attestations provided to them.

All of this data is provided to you from the [Model Attestation response](#response) as `nvidia_payload`.

Simply use this JSON Object with your API call:

```bash
curl -X POST https://nras.attestation.nvidia.com/v3/attest/gpu \
 -H "accept: application/json" \
 -H "content-type: application/json" \
 -d "<NVIDIA_PAYLOAD_FROM_NEARAI_MODEL_ATTESATION>"
```

See official documentation: https://docs.api.nvidia.com/attestation/reference/attestmultigpu_1

#### GPU Attestation Response

```bash

[
  [
    "JWT",
    "eyJraWQiOiJudi1lYXQta2lkLXByb2QtMjAyNTA4MjQxNzI2MzczMzEtMGM4YzM2MzQtY2ZkMC00YmViLWFmNWYtMTE2MzliOWUxOTIyIiwiYWxnIjoiRVMzODQifQ.eyJzdWIiOiJOVklESUEtUExBVEZPUk0tQVRURVNUQVRJT04iLCJ4LW52aWRpYS12ZXIiOiIyLjAiLCJuYmYiOjE3NTYxNjg5MjYsImlzcyI6Imh0dHBzOi8vbnJhcy5hdHRlc3RhdGlvbi5udmlkaWEuY29tIiwieC1udmlkaWEtb3ZlcmFsbC1hdHQtcmVzdWx0Ijp0cnVlLCJzdWJtb2RzIjp7IkdQVS0wIjpbIkRJR0VTVCIsWyJTSEEtMjU2IiwiMDJmYzJmMTg3M2JkZjg5Y2VlNGYzZTQzYzU3ZTE3YzI0ODUxODcwMmQ4ZGZjMzcwNmE3YjdmZTgwMzZlOTNkMCJdXX0sImVhdF9ub25jZSI6IjRkNmUwYzQ5MzIxZDIyZGFhOWJkN2ZjMjIwNWUzODFmOTUwNmMyMGU3N2RkNTA4MmVjZjVlMTI0ZWMwZjQ2MTgiLCJleHAiOjE3NTYxNzI1MjYsImlhdCI6MTc1NjE2ODkyNiwianRpIjoiYzFhM2NkYzktZWUyMi00MmFkLTljZDEtNDRhMTE5OWYyZGVlIn0.199S4bah6SVZpy4lpBvRBc975tmf25gkf_mLDwR9-fwrc_kWYePNxGygTRQUzGbRdbrZOQHXWP0eALUPkJvmwGIV_MVfHRIKaBIRdr1e2_7jEP1-mqkbCmbefimiZN8t"
  ],
  {
    "GPU-0": "eyJraWQiOiJudi1lYXQta2lkLXByb2QtMjAyNTA4MjQxNzI2MzczMzEtMGM4YzM2MzQtY2ZkMC00YmViLWFmNWYtMTE2MzliOWUxOTIyIiwiYWxnIjoiRVMzODQifQ.eyJ4LW52aWRpYS1ncHUtZHJpdmVyLXJpbS1zY2hlbWEtdmFsaWRhdGVkIjp0cnVlLCJpc3MiOiJodHRwczovL25yYXMuYXR0ZXN0YXRpb24ubnZpZGlhLmNvbSIsIngtbnZpZGlhLWdwdS1hdHRlc3RhdGlvbi1yZXBvcnQtY2VydC1jaGFpbi12YWxpZGF0ZWQiOnRydWUsImVhdF9ub25jZSI6IjRkNmUwYzQ5MzIxZDIyZGFhOWJkN2ZjMjIwNWUzODFmOTUwNmMyMGU3N2RkNTA4MmVjZjVlMTI0ZWMwZjQ2MTgiLCJ4LW52aWRpYS1ncHUtdmJpb3MtcmltLXNpZ25hdHVyZS12ZXJpZmllZCI6dHJ1ZSwieC1udmlkaWEtZ3B1LXZiaW9zLXJpbS1mZXRjaGVkIjp0cnVlLCJleHAiOjE3NTYxNzI1MjYsImlhdCI6MTc1NjE2ODkyNiwidWVpZCI6IjY0Mjk2MDE4OTI5ODAwNzUxMTI1MDk1ODAzMDUwMDc0OTE1MjczMDIyMTE0MjQ2OCIsImp0aSI6IjFhMzhjMTAzLWMyODAtNDQyMi1hZDc1LTRkMTA3OTkyMGI2MyIsIngtbnZpZGlhLWdwdS1hdHRlc3RhdGlvbi1yZXBvcnQtbm9uY2UtbWF0Y2giOnRydWUsIngtbnZpZGlhLWdwdS12Ymlvcy1pbmRleC1uby1jb25mbGljdCI6dHJ1ZSwieC1udmlkaWEtZ3B1LXZiaW9zLXJpbS1jZXJ0LXZhbGlkYXRlZCI6dHJ1ZSwic2VjYm9vdCI6dHJ1ZSwieC1udmlkaWEtZ3B1LWF0dGVzdGF0aW9uLXJlcG9ydC1wYXJzZWQiOnRydWUsIngtbnZpZGlhLWdwdS1kcml2ZXItcmltLXNpZ25hdHVyZS12ZXJpZmllZCI6dHJ1ZSwieC1udmlkaWEtZ3B1LWFyY2gtY2hlY2siOnRydWUsIngtbnZpZGlhLWF0dGVzdGF0aW9uLXdhcm5pbmciOm51bGwsIm5iZiI6MTc1NjE2ODkyNiwieC1udmlkaWEtZ3B1LWRyaXZlci12ZXJzaW9uIjoiNTcwLjEzMy4yMCIsIngtbnZpZGlhLWdwdS1kcml2ZXItcmltLW1lYXN1cmVtZW50cy1hdmFpbGFibGUiOnRydWUsIngtbnZpZGlhLWdwdS1hdHRlc3RhdGlvbi1yZXBvcnQtc2lnbmF0dXJlLXZlcmlmaWVkIjp0cnVlLCJod21vZGVsIjoiR0gxMDAgQTAxIEdTUCBCUk9NIiwiZGJnc3RhdCI6ImRpc2FibGVkIiwieC1udmlkaWEtZ3B1LWRyaXZlci1yaW0tZmV0Y2hlZCI6dHJ1ZSwib2VtaWQiOiI1NzAzIiwieC1udmlkaWEtZ3B1LXZiaW9zLXJpbS1zY2hlbWEtdmFsaWRhdGVkIjp0cnVlLCJtZWFzcmVzIjoic3VjY2VzcyIsIngtbnZpZGlhLWdwdS1kcml2ZXItcmltLWNlcnQtdmFsaWRhdGVkIjp0cnVlLCJ4LW52aWRpYS1ncHUtdmJpb3MtdmVyc2lvbiI6Ijk2LjAwLkNGLjAwLjAyIiwieC1udmlkaWEtZ3B1LXZiaW9zLXJpbS1tZWFzdXJlbWVudHMtYXZhaWxhYmxlIjp0cnVlfQ.Zjac1Al0OsYbrXu7lOKDAH7lLNnRU_G2R1UJBnUpvZKL1EE8mjPyy-4sqRvE_d8uZJ4GuhXoy_EonyuUIXESd3sxjY0Eohe9Rtlzatj14iLOdcVrF_eOq12ZHNIYs4Go"
  }
]
```

The example response is encoded in

#### Verify TDX Quote

You can verify the Intel TDX quote with the value of `intel_quote` at [TEE Attestation Explorer](https://proof.t16z.com/).

---

## Chat Message Verification

### Chat Message

#### Request

```bash
curl -X POST 'https://cloud-api.near.ai/v1/chat/completions' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-api-key' \
  -d '{
  "messages": [
    {
      "content": "What is your name? Please answer in less than 2 words",
      "role": "user"
    }
  ],
  "stream": true,
  "model": "phala/llama-3.3-70b-instruct"
}'
```

That sha256 hash of the request body is `0353202f04c8a24a484c8e4b7ea0b186ea510e2ae0f1808875fd8a96a8059e39`

(note: in this example, there is no new line at the end of request)

#### Response

```
data: {"id":"chatcmpl-717412b4a37f4e739146fdafdb682b68","created":1755541518,"model":"phala/llama-3.3-70b-instruct","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Assistant","role":"assistant"}}]}

data: {"id":"chatcmpl-717412b4a37f4e739146fdafdb682b68","created":1755541518,"model":"phala/llama-3.3-70b-instruct","object":"chat.completion.chunk","choices":[{"finish_reason":"stop","index":0,"delta":{}}]}

data: [DONE]


```

The sha256 hash of the response body is `479be7c96bb9b21ca927fe23f2f092abe2eb2fff7e3ad368ea96505e04673cdc`

(note: in this example, there are two new line at the end of response)

---

### Get Signature

By default, you can query another API with the value of `id` in the response in 5 minutes after chat completion. The signature will be persistent in the LLM gateway once it's queried.

#### Request

`GET https://cloud-api.near.ai/v1/signature/{chat_id}?model={model_id}&signing_algo=ecdsa`

> **Implementation**: This endpoint is defined in the [NEAR AI Private ML SDK](https://github.com/nearai/private-ml-sdk/blob/a23fa797dfd7e676fba08cba68471b51ac9a13d9/vllm-proxy/src/app/api/v1/openai.py#L257).

For example, the response in the previous section, the `id` is `chatcmpl-717412b4a37f4e739146fdafdb682b68`:

```bash
curl -X GET 'https://cloud-api.near.ai/signature/chatcmpl-717412b4a37f4e739146fdafdb682b68?model=phala/llama-3.3-70b-instruct&signing_algo=ecdsa' \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-api-key"
```

#### Response

- Text: the message you may want to verify. It is joined by the sha256 of the HTTP request body, and of the HTTP response body, separated by a colon `:`
- Signature: the signature of the text signed by the signing key generated inside TEE

```json
{
  "text": "0353202f04c8a24a484c8e4b7ea0b186ea510e2ae0f1808875fd8a96a8059e39:479be7c96bb9b21ca927fe23f2f092abe2eb2fff7e3ad368ea96505e04673cdc",
  "signature": "0x5ed3ac0642bceb8cdd5b222cd2db36b92af2a4d427f11cd1bec0e5b732b94628015f32f2cec91865148bf9d6f56ab673645f6bc500421cd28ff120339ea7e1a01b",
  "signing_address": "0x1d58EE32e9eB327c074294A2b8320C47E33b9316",
  "signing_algo": "ecdsa"
}
```

We can see that the `text` is `0353202f04c8a24a484c8e4b7ea0b186ea510e2ae0f1808875fd8a96a8059e39:479be7c96bb9b21ca927fe23f2f092abe2eb2fff7e3ad368ea96505e04673cdc`

Exactly match the value we calculated in the sample in previous section.

#### Limitation

Since the resource limitation, the signature will be kept in the memory for **5 minutes** since the response is generated. But the signature will be kept persistent in LLM gateway once it's queried within 5 minutes.

---

### Verify Signature

Verify ECDSA signature in the response is signed by the signing address. This can be verified with any ECDSA verification tool.

- Address: You can get the address from the attestation API. The address should be same if the service did not restarted.
- Message: The sha256 hash of the request and response. You can also calculate the sha256 by yourselves.
- Signature Hash: The signature you have got in "Get Signature" section.
