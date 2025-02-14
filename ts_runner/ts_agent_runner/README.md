Local Development
===

This process will be simplified in the future. For now, you can follow these steps to run your TypeScript agent locally.

1. Make sure you installed [NEAR AI CLI](https://docs.near.ai/agents/quickstart/#installing-near-ai-cli) and you have a named NEAR Account. You can create one with [Meteor Wallet](https://wallet.meteorwallet.app/). No funds are required.
2. Install the dependencies
    ```shell
    cd ts_runner/ts_agent && npm install
    ```
3. Perform `nearai login` to have a valid NEAR signature in `~/.nearai/config.json`.
4. Update the agent code at `/ts_runner/ts_agent/agents/agent.ts` as you need. Keep the first line as `import {env} from 'ts-agent-runner';` and use methods from the `env` object to use NEAR AI Agent Framework (completions, etc). More methods are coming in the nearest future.
5. Run the agent:
    ```shell
    npm run build &&  npm run start agents/agent.ts
    ```
6. If you want to provide ENV variables, you can provide them as arguments:
    ```shell
    npm run build && CDP_API_KEY_NAME=name CDP_API_KEY_PRIVATE_KEY="key" npm run start agents/agent.ts
    ```

This is valid only for local development. On NEAR AI Runner we have [NEAR AI HUB secrets](https://docs.near.ai/agents/secrets/) for this purpose.

How to deploy your TypeScript agent:
===
1. [Create a new agent](https://docs.near.ai/agents/quickstart/#creating-a-new-agent)
2. Copy the `agent.ts` you built to the agent folder
3. Make sure to set framework to `ts` in the metadata.json
4. Deploy the agent ([Doc above](https://docs.near.ai/agents/quickstart/#creating-a-new-agent)) has the details)

---
Example of the agent: [cdp-agent](https://app.near.ai/agents/zavodil.near/cdp-agent/latest/run)

Metadata example:
```shell
{
  "category": "agent",
  "name": "cdp-agent",
  "description": "Coinbase Agent",
  "tags": ["coinbase", "cdp"],
  "details": {
    "agent":{
      "framework": "ts"
    }
  },
  "show_entry": true,  
  "version": "0.01"
}
```