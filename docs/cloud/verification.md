# Verification

[NEAR AI Cloud](https://cloud.near.ai) operates in Trusted Execution Environments (TEEs) which use cryptographic proofs to verify that your private AI conversations actually happened in secure, isolated environments - not on compromised systems or with unauthorized access.

This section will show you step-by-step processes for checking these proofs, validating digital signatures, and confirming that your AI interactions haven't been tampered with.

---

## Overview

### How NEAR AI Cloud Verification Works:

1. **Secure Key Generation:** When NEAR AI Cloud initializes, it generates a unique cryptographic signing key pair inside the Trusted Execution Environment (TEE). The private key never leaves the secure hardware.

2. **Hardware Attestation:** The system generates attestation reports that cryptographically prove it's running on genuine NVIDIA H100/H200/B100 hardware in TEE mode within a Confidential VM.

3. **Key Binding:** These attestation reports include the public key from step 1, creating a verifiable link between the secure hardware and the signing capability.

4. **Message Signing:** Every AI inference request and response is digitally signed using the private key that remains secured within the TEE.

5. **End-to-End Verification:** You can verify that your AI interactions were genuinely processed in the secure environment by:
   
    - Checking the hardware attestation reports
    - Validating the digital signatures on your messages
    - Confirming the signing key matches the attested hardware

---

## Model Verification

To verify a NEAR AI model is operating in a secure trusted environment, there are two main steps:

- [Request Model Attestation](#request-model-attestation) report from NEAR AI Cloud
- [Verify Model Attestation](#verifying-model-attestation) report using NVIDIA & Intel attestation authenticators

---

### Request Model Attestation

To request a model attestation from NEAR AI cloud, use the following `GET` API endpoint:

```bash
https://cloud-api.near.ai/v1/attestation/report?model={model_name}
```

**_Example Requests:_**

=== "curl"

    ```bash
    curl https://cloud-api.near.ai/v1/attestation/report?model=deepseek-chat-v3-0324 \
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

=== "Python"

    ```py
    import requests

    MODEL_NAME = 'deepseek-chat-v3-0324'

    response = requests.get(
        f'https://cloud-api.near.ai/v1/attestation/report?model={MODEL_NAME}',
        headers={
            'Authorization': f'Bearer {YOUR_NEARAI_CLOUD_API_KEY}',
            'Content-Type': 'application/json',
        }
    )
    ```

!!! note
    This endpoint requires [NEAR AI Cloud Account & API Key](./get-started.md#quick-setup)

    **Implementation**: This endpoint is defined in the [NEAR AI Private ML SDK](https://github.com/nearai/private-ml-sdk/blob/a23fa797dfd7e676fba08cba68471b51ac9a13d9/vllm-proxy/src/app/api/v1/openai.py#L170).

**_Example Response:_**

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

### Verifying Model Attestation

Once you have [requested a model attestation](#request-model-attestation) from NEAR AI Cloud, you can use the returned payload to verify its authenticity for both GPU & CPU chips.

#### Verify GPU Attestation

NVIDIA offers a [Remote Attestation Service](https://docs.nvidia.com/attestation/technical-docs-nras/latest/nras_introduction.html) that allows you to verify that you are using a trusted environment with one of their GPUs. To verify this they require:

- `nonce` - A randomly generated 64 character hexadecimal string
- `arch` - Architecture of the GPU _(HOPPER or BLACKWELL)_
- `evidence_list` - A list of GPU evidence items, each containing an evidence and a corresponding certificate

The `evidence_list` contains Base64 encoded data that lists the GPU's:

- Hardware Identity
- Firmware & Software measurements
- Security configuration state
- Endorsement certificates (Signed measurements from the GPU's unique key)

The private key of this GPU is how we can securely verify the authenticity. NVIDIA burns this unique private key into each GPU during the manufacturing process and only retains the corresponding public key, which is used to verify the signature of attestations provided to them.

All of this data is provided to you from the [Model Attestation response](#request-model-attestation) as `nvidia_payload`.

Simply use this JSON Object with your API call:

```bash
curl -X POST https://nras.attestation.nvidia.com/v3/attest/gpu \
 -H "accept: application/json" \
 -H "content-type: application/json" \
 -d "<NVIDIA_PAYLOAD_FROM_NEARAI_MODEL_ATTESTATION>"
```

See official documentation: https://docs.api.nvidia.com/attestation/reference/attestmultigpu_1

**_Example GPU Attestation Response:_**

```json
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

!!! tip
    NVIDIA's attestation verification response returns a "Entity Attestation Token" (EAT) encoded as a JSON Web Token (JWT)

    To decode these values, you can use an online tool such as [jwt.io](https://www.jwt.io) or a library such as [Jose](https://www.npmjs.com/package/jose).

Example Formatted Result:

```json

"JWT":
{
  "sub": "NVIDIA-PLATFORM-ATTESTATION",
  "x-nvidia-ver": "2.0",
  "nbf": 1756168926,
  "iss": "https://nras.attestation.nvidia.com",
  "x-nvidia-overall-att-result": true,
  "submods": {
    "GPU-0": [
      "DIGEST",
      [
        "SHA-256",
        "02fc2f1873bdf89cee4f3e43c57e17c248518702d8dfc3706a7b7fe8036e93d0"
      ]
    ]
  },
  "eat_nonce": "4d6e0c49321d22daa9bd7fc2205e381f9506c20e77dd5082ecf5e124ec0f4618",
  "exp": 1756172526,
  "iat": 1756168926,
  "jti": "c1a3cdc9-ee22-42ad-9cd1-44a1199f2dee"
}

"GPU-0":
{
  "x-nvidia-gpu-driver-rim-schema-validated": true,
  "iss": "https://nras.attestation.nvidia.com",
  "x-nvidia-gpu-attestation-report-cert-chain-validated": true,
  "eat_nonce": "4d6e0c49321d22daa9bd7fc2205e381f9506c20e77dd5082ecf5e124ec0f4618",
  "x-nvidia-gpu-vbios-rim-signature-verified": true,
  "x-nvidia-gpu-vbios-rim-fetched": true,
  "exp": 1756172526,
  "iat": 1756168926,
  "ueid": "642960189298007511250958030500749152730221142468",
  "jti": "1a38c103-c280-4422-ad75-4d1079920b63",
  "x-nvidia-gpu-attestation-report-nonce-match": true,
  "x-nvidia-gpu-vbios-index-no-conflict": true,
  "x-nvidia-gpu-vbios-rim-cert-validated": true,
  "secboot": true,
  "x-nvidia-gpu-attestation-report-parsed": true,
  "x-nvidia-gpu-driver-rim-signature-verified": true,
  "x-nvidia-gpu-arch-check": true,
  "x-nvidia-attestation-warning": null,
  "nbf": 1756168926,
  "x-nvidia-gpu-driver-version": "570.133.20",
  "x-nvidia-gpu-driver-rim-measurements-available": true,
  "x-nvidia-gpu-attestation-report-signature-verified": true,
  "hwmodel": "GH100 A01 GSP BROM",
  "dbgstat": "disabled",
  "x-nvidia-gpu-driver-rim-fetched": true,
  "oemid": "5703",
  "x-nvidia-gpu-vbios-rim-schema-validated": true,
  "measres": "success",
  "x-nvidia-gpu-driver-rim-cert-validated": true,
  "x-nvidia-gpu-vbios-version": "96.00.CF.00.02",
  "x-nvidia-gpu-vbios-rim-measurements-available": true
}

```

#### Verify TDX Quote

You can verify the Intel TDX quote with the value of `intel_quote` at [TEE Attestation Explorer](https://proof.t16z.com/).

---

## Chat Message Verification

You can verify each chat message with NEAR AI Confidential Cloud. For this you will need:

1. [Chat Message **REQUEST** Hash](#chat-request-hash)
2. [Chat Message **RESPONSE** Hash](#chat-response-hash)
3. [Chat Message Signature](#chat-message-signature)

---

### Chat Message Request Hash

The value is calculated from the **exact JSON request body string**.

**_Example:_**

```json
{
  "messages": [
    {
      "content": "Respond with only two words.",
      "role": "user"
    }
  ],
  "stream": true,
  "model": "deepseek-v3.1"
}
```

Which hashes to:

```bash
2ec65b4a042f68d7d4520e21a7135505a5154d52aa87dbd19e9d08021ffe5c4d
```

Here is an example of how to get the sha256 hash of your message request body:

=== "JavaScript"

    ```js
    import crypto from 'crypto';

    const requestBody = JSON.stringify({
      "messages": [
        {
          "content": "Respond with only two words.",
          "role": "user"
        }
      ],
      "stream": true,
      "model": "deepseek-v3.1"
    });

    const hash = crypto.createHash('sha256').update(requestBody).digest('hex');
    console.log(hash); //2ec65b4a042f68d7d4520e21a7135505a5154d52aa87dbd19e9d08021ffe5c4d
    ```

---

### Chat Message Response Hash

This value is calculated from the **exact response body string**.

!!! info
    Please note the streaming response contains two new lines at the end and should not be omitted when copying response as the hash value will change.

**_Example Response Body:_**

```bash
data: {"id":"chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46","object":"chat.completion.chunk","created":1760031300,"model":"deepseek-ai/DeepSeek-V3.1","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}],"prompt_token_ids":null}

data: {"id":"chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46","object":"chat.completion.chunk","created":1760031300,"model":"deepseek-ai/DeepSeek-V3.1","choices":[{"index":0,"delta":{"content":"Okay"},"logprobs":null,"finish_reason":null,"token_ids":null}]}

data: {"id":"chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46","object":"chat.completion.chunk","created":1760031300,"model":"deepseek-ai/DeepSeek-V3.1","choices":[{"index":0,"delta":{"content":"."},"logprobs":null,"finish_reason":null,"token_ids":null}]}

data: {"id":"chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46","object":"chat.completion.chunk","created":1760031300,"model":"deepseek-ai/DeepSeek-V3.1","choices":[{"index":0,"delta":{"content":" Sure"},"logprobs":null,"finish_reason":null,"token_ids":null}]}

data: {"id":"chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46","object":"chat.completion.chunk","created":1760031300,"model":"deepseek-ai/DeepSeek-V3.1","choices":[{"index":0,"delta":{"content":"."},"logprobs":null,"finish_reason":null,"token_ids":null}]}

data: {"id":"chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46","object":"chat.completion.chunk","created":1760031300,"model":"deepseek-ai/DeepSeek-V3.1","choices":[{"index":0,"delta":{"content":""},"logprobs":null,"finish_reason":"stop","stop_reason":null,"token_ids":null}]}

data: [DONE]

```

Which hashes to:

```bash
bdcfaa70301ea760ad215a2de31e80b7a69ee920c02a4b97ae05d0798b75fe79
```

Here is an example of how to get the sha256 hash of your message response body:

=== "JavaScript"

    ```js
    const response = await fetch('https://cloud-api.near.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.NEARAI_CLOUD_API_KEY}`
      },
      body: requestBody
    });

    const responseBody = await response.text();
    const hash = crypto.createHash('sha256').update(responseBody).digest('hex');
    console.log(hash); // bdcfaa70301ea760ad215a2de31e80b7a69ee920c02a4b97ae05d0798b75fe79
    ```

---

### Chat Message Signature

From the Chat Message Response you will get a unique chat `id` that is used to fetch the Chat Message Signature from NEAR AI Confidential Cloud.

By default, you can query another API with the value of `id` in the response in 5 minutes after chat completion. The signature will be persistent in the LLM gateway once it's queried.

Use the following endpoint to get this signature:

```bash
GET https://cloud-api.near.ai/v1/signature/{chat_id}?model={model_id}&signing_algo=ecdsa
```

> **Implementation**: This endpoint is defined in the [NEAR AI Private ML SDK](https://github.com/nearai/private-ml-sdk/blob/a23fa797dfd7e676fba08cba68471b51ac9a13d9/vllm-proxy/src/app/api/v1/openai.py#L257).

For example, the response in the previous section, the `id` is:

 `chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46`

```bash
curl -X GET 'https://cloud-api.near.ai/signature/chatcmpl-f42e8ae7ddb346e1adfba47e3d710b46?model=deepseek-v3.1&signing_algo=ecdsa' \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <YOUR-NEARAI-CLOUD-API-KEY>"
```

***Example Response:***

```json
{
  "text":"2ec65b4a042f68d7d4520e21a7135505a5154d52aa87dbd19e9d08021ffe5c4d:bdcfaa70301ea760ad215a2de31e80b7a69ee920c02a4b97ae05d0798b75fe79",
  "signature":"0xb6bed282118266c5bc157bc7a88185dd017826da13c7aeb2aeebb9be88c7c7400047b88528d29f82792df1f2288a1b84e11ffddfe32517d46d5f7056e9082b941c",
  "signing_address":"0xCaAA4842758658A85785Ad15367a700C601ffEA5",
  "signing_algo":"ecdsa"
}
```

The above response gives us all of the crucial information we need to verify that the message was executed in our trusted environment:

- `text` - This is the [Chat Message REQUEST Hash](#chat-message-request-hash) & [Chat Message RESPONSE Hash](#chat-message-response-hash) concatenated with a `:` separator.
- `signature` - This is the cryptographic signature of the `text` field, generated using the TEE's private key 
- `signing_address` - Public key of the TEE unique to the model we used
- `signing_algo` - Cryptography curve used to sign

You can see that `text` is:

`2ec65b4a042f68d7d4520e21a7135505a5154d52aa87dbd19e9d08021ffe5c4d:bdcfaa70301ea760ad215a2de31e80b7a69ee920c02a4b97ae05d0798b75fe79`

This exactly matches the concatenated values we calculated in the previous sections:

- Request hash: `2ec65b4a042f68d7d4520e21a7135505a5154d52aa87dbd19e9d08021ffe5c4d`
- Response hash: `bdcfaa70301ea760ad215a2de31e80b7a69ee920c02a4b97ae05d0798b75fe79`

!!! Note
    Due to resource limitations, signatures are kept in memory for **5 minutes** after the response is generated. However, once queried within this 5-minute window, the signature becomes persistent in the LLM gateway for future verification.

---

#### Verify Signature

Signature verification can be easily done with any standard ECDSA verification library such as [ethers](https://www.npmjs.com/package/ethers) or even an online tool such as [etherscan's VerifySignatures](https://etherscan.io/verifiedSignatures).

These tools will require:

- `Address`: What the expected address is for the signature. In our case it will be the one retrieved from your [attestation API query](#request-model-attestation). 
- `Message`: The original message before signing. In our case it will be the sha256 hash of the request and response (`text` field from [Get Chat Message Signature](#chat-message-signature))
- `Signature`: The signed message from above

Here is an example of how to verify the Chat Message signature using `ethers`:

```js
  import { ethers } from 'ethers';

  const text = "65b0adb47d0450971803dfb18d0ce4af4a64d27420a43d5aad4066ebf10b81b5:e508d818744d175a62aae1a9fb3f373c075460cbe50bf962a88ac008c843dff1";
  const signature = "0xf28f537325c337fd96ae6e156783c904ca708dcd38fb8a476d1280dfc72dc88e4fcb5c3941bdd4f8fe5238a2253b975c6b02ea6a0a450b5b0f9296ab54cf24181b";
  const expectedAddress = "0xc51268C9b46140619CBC066A34441a6ca51F85f9";

  // Recover the address from the signature
  const recoveredAddress = ethers.verifyMessage(text, signature);
  
  // Compare with expected address (case-insensitive)
  const isValid = recoveredAddress.toLowerCase() === expectedAddress.toLowerCase();
  
  console.log("Text:", text);
  console.log("Expected address:", expectedAddress);
  console.log("Recovered address:", recoveredAddress);
  console.log("Signature valid:", isValid);
```
