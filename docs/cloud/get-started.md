# Get Started with NEAR AI Cloud

[NEAR AI Cloud](https://cloud.near.ai) offers developers access to private, verifiable AI models through a unified API. This guide will walk you through setting up your account, creating API keys, and making your first requests.

---

## Overview

NEAR AI Cloud provides:

- **Unified API for AI Models**: Access leading AI models like DeepSeek, Llama, OpenAI, Qwen and more through a single API
- **Private Inference**: All AI computations run in Trusted Execution Environments (TEEs) ensuring complete privacy and verifiability
- **Flexible Payments**: Top up or pay as you go using fiat

---

## Quick Setup

### 1. Create Your Account

1. Visit [NEAR AI Cloud](https://cloud.near.ai/) and click "Sign In"
2. Connect your GitHub or Google account

### 2. Get Credits

1. Navigate to the **Credits** section in your dashboard
2. Select the amount of credits you want to purchase
3. Complete the transaction

### 3. Create Your First API Key

1. Go to the **API Keys** section in your dashboard
2. Click **"Create New API Key"**
3. Set usage limits (optional)
4. Click **"Create"** to generate your API key

!!! note "API Key Security"
    Keep your API key secure and never share it publicly. You can regenerate keys at any time from your dashboard.

---

## Making Your First Request

### Basic Chat Completion

Here's a simple example using Python:

```python
import openai

# Initialize the client
client = openai.OpenAI(
    base_url="https://cloud-api.near.ai/v1",
    api_key="your-api-key-here"
)

# Create a chat completion
response = client.chat.completions.create(
    model="deepseek-chat-v3-0324",
    messages=[
        {"role": "system", "content": "You are a helpful coding assistant."},
        {"role": "user", "content": "Write a Python function to calculate fibonacci numbers."}
    ],
    temperature=0.7,
    max_tokens=500
)

print(response.choices[0].message.content)
```

### Using cURL

```bash
curl https://cloud-api.near.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key-here" \
  -d '{
    "model": "deepseek-chat-v3-0324",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ],
    "temperature": 0.7
  }'
```

### Using JavaScript/Node.js

```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  baseURL: 'https://cloud-api.near.ai/v1',
  apiKey: 'your-api-key-here',
});

const completion = await openai.chat.completions.create({
  model: 'deepseek-chat-v3-0324',
  messages: [
    { role: 'user', content: 'Hello, how are you?' }
  ],
  temperature: 0.7,
});

console.log(completion.choices[0].message.content);
```

---

## Available Models

NEAR AI Cloud supports a wide range of open source verifiable models.

You can find the model list from [https://cloud.near.ai/models](https://cloud.near.ai/models)

---

## Next Steps

Now that you're set up with NEAR AI Cloud, explore these resources:

- [:material-cog: Private Inference Deep Dive](./private-inference.md) - Learn about TEE technology and privacy features
- [:material-check-decagram: Verification Guide](./verification.md) - Understand how to verify AI responses
