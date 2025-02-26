# NEAR AI Typescript SDK - Getting Started

## Prerequisites

Before creating a NEAR AI Typescript Agent, please make sure you have the [NEAR AI CLI](https://docs.near.ai/cli/) installed and have logged in with your Near wallet.

- [ ] You have `Python 3.11.xx` in your machine. (**IMPORTANT** `Python 3.12+` currently not supported!)
- [ ] Installing NEAR AI CLI `python3 -m pip install nearai`
- [ ] Login to NEAR AI `nearai login`

> You'll be provided with a URL to login with your NEAR account.
>
> Example:

```shell
$> nearai login

Please visit the following URL to complete the login process: https://auth.near.ai?message=Welcome+to+NEAR+AI&nonce=<xyzxyzxyzxyzx>&recipient=ai.near&callbackUrl=http%3A%2F%2Flocalhost%3A63130%2Fcapture
```

- [ ] Login with NEAR by connecting with your wallet. After successfully logging in, you will see a confirmation screen. Close it and return to your terminal.

## Local Development

Clone the NEAR AI Github Repository

```shell
git clone https://github.com/nearai/nearai.git
```

Change your directory to `ts_runner/ts_agent` and Install `Node.js` dependencies by running the command below

```shell
cd ts_runner/ts_agent && npm install
```

Change the directory to `ts_runner/ts_agent/agents` and add your agent related code in `agent.ts` file

```typescript
import { env } from "ts-agent-runner";

(async () => {
  try {
    const userMessage = "Tell me an AI joke";

    console.log("User input:", userMessage);

    const messages: any = [
      {
        role: "system",
        content: "You are a smart assistant.",
      },
      {
        role: "user",
        content: userMessage,
      },
    ];

    // inference
    const reply = await env.completion(
      messages,
      "llama-v3p1-70b-instruct",
      4000,
      0.5
    );

    if (env.get_thread_id() !== "thread_local") {
      await env.add_reply(reply);
    }

    console.log("Agent output:", reply);
  } catch (error) {
    console.error("Agent error:", error);
  }
})();
```

Run the agent

```shell
npm run build && npm run start agents/agent.ts
```

## Deployment

> This process will be simplified in the future. For now, you can follow these steps to deploy your TypeScript agent.

Create an Agent

```shell
nearai agent create
```

> For more detail follow the link: [NEAR AI Quickstart - NEAR AI](https://docs.near.ai/agents/quickstart/)
> Name can’t contain space. Example: Agent name have to be AgentName and can’t be “Agent Name”

During the agent creation process, `nearai` builds your agent in your local AI registry located at:

`/home_directory/.nearai/registry/<your-account.near>/<agent-name>/0.0.1`

This folder contains two files that define your agent:

1. `metadata.json`: Contains information / configuration about your agent.
2. `agent.py`: Python code that executes each time your agent receives a prompt.

Update your Agent

- Rename the [`agent.py`](http://agent.py) to `agent.ts` and copy-paste your agent code
- Update the `metadata.json` file and include `"framework": "ts",` line

```json
{
  "category": "agent",
  ...
  "details": {
    "agent": {
      "framework": "ts",
      ...
    }
  },
  ...
}
```

Interacting with your Agent locally

```shell
# Run agent locally
nearai agent interactive <path-to-agent> --local
```

Deploy your Agent

```shell
# Upload agent to NEAR AI's public registry
nearai registry upload <path-to-agent>
```

> You have to update the version number of your Agent in the metadata.json file every time you deploy your agent.

**Success!** You now have a new Typescript Agent ready to use!
