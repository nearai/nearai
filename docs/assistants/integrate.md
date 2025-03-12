# Integrate NEAR AI assistant

NEAR AI offers a powerful Assistant that answers questions, queries other agents, and more. You can integrate the Assistant into your own applications by using the Assistant API.

NEAR AI Assistants API is compatible with OpenAI Assistants API.

## Step 0: Login into NEAR account

### JavaScript, client side. Useful for wallets.

From client side, you can use the following function to sign the message and get the required NEAR AI authorization token.

```javascript
async function login(wallet, message, nonce, recipient, callbackUrl) {
    const signedMessage = await wallet.signMessage({
        message,
        nonce,
        recipient,
        callbackUrl
    });
    return {
        signature: signedMessage.signature,
        accountId: signedMessage.accountId,
        publicKey: signedMessage.publicKey,
        message,
        nonce,
        recipient,
        callbackUrl
    };
}

// Generate nonce based on current time in milliseconds
const nonce = String(Date.now());
const recipient = YOUR_RECIPIENT_ADDRESS;
const callbackUrl = YOUR_CALLBACK_URL;

// Example usage of login function
const auth = await login(wallet, "Login to NEAR AI", nonce, recipient, callbackUrl);
```

### Python

In Python, we recommend using the `nearai` CLI to login into your NEAR account. More details [here](../agents/quickstart.md#login-to-near-ai).

```python
nearai login
```

## Step 1: Create a Thread

A Thread represents a conversation between a user and one or many Assistants. You can create a Thread when a user (or your AI application) starts a conversation with your Assistant.

### Create a Thread

In JavaScript:

```javascript
import OpenAI from "openai";
const openai = new OpenAI({
    baseURL: "https://api.near.ai/v1",
    apiKey: `Bearer ${JSON.stringify(auth)}`,
});

const thread = await openai.beta.threads.create();
```

In Python:

```python
import openai

client = openai.OpenAI(
    api_key="YOUR_NEARAI_SIGNATURE",
    base_url="https://api.near.ai/v1",
)

thread = client.beta.threads.create()
```

## Step 2: Add a Message to the Thread
The contents of the messages your users or applications create are added as Message objects to the Thread. Messages can contain both text and files. There is a limit of 100,000 Messages per Thread and we smartly truncate any context that does not fit into the model's context window.

### Add a Message to the Thread

In JavaScript:

```javascript
const message = await openai.beta.threads.messages.create(
  thread.id,
  {
    role: "user",
    content: "Help me plan my trip to Tokyo"
  }
);
```

In Python:

```python
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Help me plan my trip to Tokyo"
)
```

## Step 3: Create a Run
Once all the user Messages have been added to the Thread, you can Run the Thread with any Assistant. Creating a Run uses the model and tools associated with the Assistant to generate a response. These responses are added to the Thread as assistant Messages.

Runs are asynchronous, which means you'll want to monitor their status by polling the Run object until a terminal status is reached. For convenience, the 'create and poll' SDK helpers assist both in creating the run and then polling for its completion.

### Create a Run

In JavaScript:

```javascript
const assistant_id = "near-ai-agents.near/assistant/latest"
let run = await openai.beta.threads.runs.createAndPoll(
  thread.id,
  { 
    assistant_id: assistant_id,
  }
);
```

In Python:

```python
assistant_id = "near-ai-agents.near/assistant/latest"
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant_id,
)
```

Once the Run completes, you can list the Messages added to the Thread by the Assistant.

```javascript
if (run.status === 'completed') {
  const messages = await openai.beta.threads.messages.list(
    run.thread_id
  );
  for (const message of messages.data.reverse()) {
    console.log(`${message.role} > ${message.content[0].text.value}`);
  }
} else {
  console.log(run.status);
}
```

```python
if run.status == 'completed':
    messages = client.beta.threads.messages.list(run.thread_id)
    for message in messages:
        print(f"{message.role} > {message.content[0].text.value}")
else:
    print(run.status)
```

You may also want to list the Run Steps of this Run if you'd like to look at any tool calls made during this Run.