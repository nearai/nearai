# Verification

NEAR AI Cloud provides cryptographic verification for all private inference results, ensuring you can trust that AI responses were generated in secure, isolated environments. This guide explains how to verify attestations, validate signatures, and ensure the integrity of your AI interactions.

---

## Overview

1. When the service starts, it generates a signing key in TEE.
2. You can get the CPU and GPU attestation to verify the service is running in Confidential VM with NVIDIA H100/H200/B100 in TEE mode.
3. The attestation includes the public key of the signing key to prove the key is generated in TEE.
4. All the inference results contain signature with the signing key.
5. You can use the public key to verify all the inference results is generated in TEE.

---

## Preparation

First, you'll need a NEAR AI Cloud API key to use the Confidential AI service. Check out [Get Started](./get-started.md) to learn how to:

* Create your API key in minutes
* Make your first API request

---

## Model Attestation

### Request

`GET https://cloud-api.near.ai/v1/attestation/report?model={model_name}`

> **Implementation**: This endpoint is defined in the [NEAR AI Private ML SDK](https://github.com/nearai/private-ml-sdk/blob/a23fa797dfd7e676fba08cba68471b51ac9a13d9/vllm-proxy/src/app/api/v1/openai.py#L170).

### Response

```json
{
  "signing_address": "...",
  "nvidia_payload": "...",
  "intel_quote": "...",
  "all_attestations": [
    {
      "signing_address": "...",
      "nvidia_payload": "...",
      "intel_quote": "..."
    }
  ]
}
```

`signing_address` is the account address generated inside TEE that will be used to sign the chat response.

`nvidia_payload` and `intel_quote` are the attestation report from NVIDIA TEE and Intel TEE respectively. You can use them to verify the integrity of the TEE. See [Verify the Attestation](#verify-the-attestation) for more details.

The `all_attestations` is the list of all the attestations of all GPU nodes as we may add multiple TEE nodes to serve the inference requests. You can utilize the `signing_address` from the `all_attestations` to select the appropriate TEE node for verifying its integrity.

### Verify the Attestation

#### Verify GPU Attestation

You can copy the value of `nvidia_payload` as the whole payload as followed to verify:

```bash
curl -X POST https://nras.attestation.nvidia.com/v3/attest/gpu \
 -H "accept: application/json" \
 -H "content-type: application/json" \
 -d "<NVIDIA_PAYLOAD_FROM_ABOVE>"
```

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

* Text: the message you may want to verify. It is joined by the sha256 of the HTTP request body, and of the HTTP response body, separated by a colon `:`
* Signature: the signature of the text signed by the signing key generated inside TEE

```json
{
    "text":"0353202f04c8a24a484c8e4b7ea0b186ea510e2ae0f1808875fd8a96a8059e39:479be7c96bb9b21ca927fe23f2f092abe2eb2fff7e3ad368ea96505e04673cdc",
    "signature":"0x5ed3ac0642bceb8cdd5b222cd2db36b92af2a4d427f11cd1bec0e5b732b94628015f32f2cec91865148bf9d6f56ab673645f6bc500421cd28ff120339ea7e1a01b",
    "signing_address":"0x1d58EE32e9eB327c074294A2b8320C47E33b9316",
    "signing_algo":"ecdsa"
}
```

We can see that the `text` is `0353202f04c8a24a484c8e4b7ea0b186ea510e2ae0f1808875fd8a96a8059e39:479be7c96bb9b21ca927fe23f2f092abe2eb2fff7e3ad368ea96505e04673cdc`

Exactly match the value we calculated in the sample in previous section.

#### Limitation

Since the resource limitation, the signature will be kept in the memory for **5 minutes** since the response is generated. But the signature will be kept persistent in LLM gateway once it's queried within 5 minutes.

---

### Verify Signature

Verify ECDSA signature in the response is signed by the signing address. This can be verified with any ECDSA verification tool.

* Address: You can get the address from the attestation API. The address should be same if the service did not restarted.
* Message: The sha256 hash of the request and response. You can also calculate the sha256 by yourselves.
* Signature Hash: The signature you have got in "Get Signature" section.
