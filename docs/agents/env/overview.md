# The Environment Object

Each time an agents executes it receives an environment, which gives it access to features such as:

* Retrieve messages in the conversation, both from the user and the agent
* Request input from the user
* Read and write files on the agent's storage
* Call other agents

## Available variables
 * [`signer_account_id`](../../api.md#nearai.agents.environment.Environment.signer_account_id): get the NEAR Account ID of the signer 

<!-- 

### Signed messages
NEAR AI authentication is through a Signed Message: a payload signed by a Near Account private key. (How to [Login with NEAR](login.md))

If you need one for manual testing, you can `nearai login` then copy the auth section from your `~/.nearai/config.json`.

To add signed message login to an application, see the code in hub demo [near.tsx](https://github.com/nearai/nearai/blob/main/hub/demo/src/app/_components/near.tsx). 

-->