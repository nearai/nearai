# Integrating NEAR AI Agents

Easily integrate your Agent or [any NEAR AI Agent](https://app.near.ai/agents) into an existing application. There are two main pathways to accomplish this:

- [iFrame Agent Embedding](#iframe-agent-embedding) - Simple high-level integration with just a few lines of code
- [Agent API](#api-agent-integration) - Lower-level integration for use when orchestrating multiple agents

---

## iFrame Agent Embedding

The quickest way to integrate a NEAR AI Agent into any existing website is with an iFrame. This allows users to interact with your agent without leaving your site.

### Basic Embedding

To embed an agent, use the following iframe code replacing the `src` with the agent you want to embed.

`Example`:

```html
<iframe 
  src="https://app.near.ai/embed/<your-account.near>/<your-agent-name>/latest" 
  sandbox="allow-scripts allow-popups allow-same-origin allow-forms"
  style="border: none; height: 100svh;">
</iframe>
```

!!! info
    - Note that the difference with this `src` path compared to a regular link to your agent is that it is using the `embed` endpoint.

    - Also note that you can replace the `latest` with a specific agent version number.

!!! tip
    You can also copy/paste the snippet from the [NEAR AI Dev Platform](https://app.near.ai/agents).
    
    - Clicking the `share` icon from your agent page and select `<embed>`

    ![agent embed snippet](../assets/agents/agent-embed.png)

### Customizing the Embed

There are three ways to customize the appearance and behavior of your embedded agent:

1. Basic `<iframe>` attributes
2. URL parameters
3. `metadata.json` file

!!! info
    The embedded agent will inherit the styling of the NEAR AI platform while maintaining a consistent look and feel with your website.

#### Light or Dark Theme

For light or dark themes, add a `theme` parameter to the embed src URL:

`src="https://app.near.ai/embed/<your-account.near>/<your-agent-name>/latest?theme=dark"`

#### Custom Logo

You can also add a custom logo to replace the default agent name in the upper left hand corner of your agent.

In your `metadata.json` file add an `embed` section under the agent details:

```json
{
  "details": {
    "agent": {
      "embed": {
        "logo": "https://near.ai/logo-white.svg"
      }
    }
  }
}
```

---

## Agent API Integration

NEAR AI Agents are compatible with the [OpenAI Assistants API](https://platform.openai.com/docs/assistants/overview), making it easy to integrate powerful AI capabilities into your applications. The API enables NEAR AI agents to:

1. Call various models with specific instructions to customize personality and capabilities
2. Access multiple tools for enhanced functionality
3. Maintain persistent conversation Threads
4. Process files in several formats (as inputs or outputs)

See [the complete NEAR AI OpenAPI specification](https://docs.near.ai/api/).

!!! info
    While you can orchestrate multiple agents, in many cases you can consolidate multiple roles into a single agent. For best practices, see ["Orchestrating Agents"](https://docs.near.ai/agents/patterns/orchestration/).

### Key Concepts

| Concept       | Description                                                                                                                                                                                                           |
|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Thread        | A conversation session between an Assistant and a user. Threads store Messages and automatically handle truncation to fit content into a model's context. You create a Thread once and simply append Messages as users reply.                                                                   |
| Message       | Content created by an Assistant or user. Messages can include text, images, and other files, and are stored as a list within a Thread.                                                                                    |
| Run           | An invocation of an Assistant on a Thread. The Assistant processes the Thread's Messages using its configuration to perform tasks by calling models and tools.      |
| Run Step      | Detailed record of actions the Assistant took during a Run. Examining Run Steps allows you to see how the Assistant reaches its conclusions. |
| Service Agent | A specialized Agent called by the Assistant to accomplish specific tasks (e.g., purchasing, swaps, smart contract generation).                                                                                     |

### Implementation Guide

NEAR AI provides a powerful Assistant API that you can integrate into your applications by following these steps:

1. [Authentication: Login to NEAR Account](#1-authentication-login-to-near-account)
2. [Create a Thread](#2-create-a-thread)
3. [Add Messages to the Thread](#3-add-messages-to-the-thread)
4. [Run the Assistant on the Thread](#4-run-the-assistant-on-the-thread)
5. [Process Assistant Responses](#5-process-assistant-responses)

#### 1. Authentication: Login to NEAR Account

=== "JavaScript"

    From client side, you can use the following [NEAR Wallet Selector](https://github.com/near/wallet-selector) function to sign the message and get the required NEAR AI authorization token.

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

    // Generate nonce based on current time in milliseconds and
    // pad it with zeros to ensure its exactly 32 bytes in length
    const nonce = Buffer.from(Date.now().toString().padStart(32, '0'));
    const recipient = YOUR_RECIPIENT_ADDRESS;
    const callbackUrl = YOUR_CALLBACK_URL;

    // Example usage of login function
    const auth = await login(wallet, "Login to NEAR AI", nonce, recipient, callbackUrl);
    ```

=== "Python"

    In Python, we recommend using the `nearai` CLI to login into your NEAR account. More details [here](../agents/quickstart.md#login-to-near-ai).

    ```python
    nearai login
    ```

#### 2. Create a Thread

A Thread represents a conversation between a user and one or many Assistants. You can create a Thread when a user (or your AI application) starts a conversation with your Assistant. For more information see [Threads](./threads.md).

=== "JavaScript"

    ```javascript
    import OpenAI from "openai";
    const openai = new OpenAI({
        baseURL: "https://api.near.ai/v1",
        apiKey: `Bearer ${JSON.stringify(auth)}`,
    });

    const thread = await openai.beta.threads.create();
    ```

=== "Python"

    ```python
    import openai

    client = openai.OpenAI(
        api_key="YOUR_NEARAI_SIGNATURE",
        base_url="https://api.near.ai/v1",
    )

    thread = client.beta.threads.create()
    ```

#### 3. Add Messages to the Thread

The contents of the messages your users or applications create are added as Message objects to the Thread. Messages can contain both text and files. There is a limit of 100,000 Messages per Thread and we smartly truncate any context that does not fit into the model's context window.

=== "JavaScript"

    ```javascript
    const message = await openai.beta.threads.messages.create(
      thread.id,
      {
        role: "user",
        content: "Help me plan my trip to Tokyo"
      }
    );
    ```

=== "Python"

    ```python
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Help me plan my trip to Tokyo"
    )
    ```

#### 4. Run the Assistant on the Thread

Once all the user Messages have been added to the Thread, you can Run the Thread with any Assistant. Creating a Run uses the model and tools associated with the Assistant to generate a response. These responses are added to the Thread as assistant Messages.

Runs are asynchronous, which means you'll want to monitor their status by polling the Run object until a terminal status is reached. For convenience, the 'create and poll' SDK helpers assist both in creating the run and then polling for its completion.

=== "JavaScript"

    ```javascript
    const assistant_id = "near-ai-agents.near/assistant/latest"
    let run = await openai.beta.threads.runs.createAndPoll(
      thread.id,
      { 
        assistant_id: assistant_id,
      }
    );
    ```

=== "Python"

    ```python
    assistant_id = "near-ai-agents.near/assistant/latest"
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )
    ```

#### 5. Process Assistant Responses

Once the Run completes, you can list the Messages added to the Thread by the Assistant.

=== "JavaScript"

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

=== "Python"

    ```python
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(run.thread_id)
        for message in messages:
            print(f"{message.role} > {message.content[0].text.value}")
    else:
        print(run.status)
    ```

You may also want to list the Run Steps of this Run if you'd like to look at any tool calls made during this Run.