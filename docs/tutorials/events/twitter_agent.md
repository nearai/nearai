# Twitter(X) Agent

NEAR AI allows anyone to easily create an agent that uses an [`X account`](https://x.com) (previously `Twitter`) and answers to mentions.

<!--- INSERT SCREENSHOT OF THE TWITTER AGENT INTERACTING WITH SOMEBODY HERE --->

In this tutorial we will learn how an [existing agent](#) works, and how you can change it to create your own X AI agent in less than five minute.

---

## The X Agent

Let's explore the code of the agent. The agent is a simple bot that replies to mentions with a random joke. The agent uses the `x` library to interact with the X API and the `jokeapi` library to get random jokes.

Try it out by tweeting a mention to the agent, and see how it replies with a random joke.

```
Hey @maguila_bot, tell me a joke!
```

### Invoking the Agent: Mentions

The agent works by listening to mentions of the account `@...` and replying to them. This is configured in the `metadata.json` file, specifically in the section <>.

```json title="metadata.json"


```

> info
> Notice that the agent is replying to an event, events are automatically handled by the NEAR AI platform, so you don't need to worry about them. You can see the list of supported events [here](#). 


### Processing the Tweet

The agent receives as an input the `tweet` object, which contains the following data:

- something
- something
- something
- something

Since the `tweet` object contains all the information needed, we can process it through a model in order to generate a response.

### Answering

Bla

----

## Modifying the Agent

If you want to create your own agent, you will need to start by forking [<maguila>](#), and setting up the right Twitter API keys, so the agent can control the account you want.

<details>

<summary>Getting the Twitter API Keys</summary>

here is very briefly how you get your API keys

</details>

### Setting up the Keys



### Modifying the Agent

Let's change the agent so people can ask it history related questions, and the agent uses the Llama 3 model to reply. 





Before creating a NEAR AI agent, please make sure you have the [NEAR AI CLI](../../cli.md) installed and have logged in with your Near wallet.


You will need to create a Twitter developer account and generate your API keys. Follow the instructions [here](https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api) to set up your Twitter developer account and obtain your API keys.

---
## Fork an Agent

To fork the Twitter agent, enter [https://app.near.ai/agents/maguila.near/jokester/latest/source](https://app.near.ai/agents/maguila.near/jokester/latest/source) in your browser and click on the "Fork" button. This will create a copy of the agent in your NEAR AI registry.

![start](./twitter/01-start.png)


You can see the next windows where you can change the name and version to create the agent.
![start](./twitter/02-fork-window.png)

## Develop and upload Agent
Once you have forked the agent, you can start developing it. You can clone the repository to your local machine using the NEAR AI CLI.
To clone the repository, run the following command in your terminal:

```bash
nearai registry download <your-account.near>/<agent-name>/<version>
```
eg:
```bash
nearai registry download maguila.near/clown/0.0.1
```

This will create a directory with the agent's code in your working directory.
You can now open the agent's code in your favorite code editor and start making changes.
```bash
cd ~/.nearai/registry/<your-account.near>/<agent-name>/<version>
```
eg:
```bash
cd ~/.nearai/registry/maguila.near/clown/0.0.1
```

You need modify the `metadata.json` file to add metions accounts. You can do this by adding the following lines to the `details` section of the `metadata.json` file:


```json
{
  "category": "agent",
  "description": "",
  "tags": [],
  "details": {
    "agent": {
      "welcome": {
        "description": "To use tweet a message and mention @maguila_bot.",
        "title": "No chat interface"
      },
      "framework": "standard"
    },
    "triggers": {
      "events" : {
        "x_mentions": ["@nearsecretagent"]
      }
    }
  },
  "show_entry": true,
  "name": "clown",
  "version": "0.0.1"
}
```

once saved, you must upload it to the NEAR AI. You can do this by running the following command in your terminal:
```bash
nearai registry upload .
```

## Generate keys
To allow your agent to post to X you will need your own developer api key. Free X developer accounts have low read limits but fairly high write limits.
To generate your API keys, follow these steps:  

1. Go to the [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard).

2. Click on the "Projects & Apps" tab.

3. Click on the "Create App" button.

4. Fill in the required fields, such as the app name and description.

5. Click on the "Create" button.

6. Once the app is created, go to the "Keys and tokens" tab.

7. You must create a API Key and Secret, and a Access Token and Secret.


!!! warning "Permissions"
    Remember to set the permissions for the Access Token and Secret to **"Read and Write"**.

    To change the permissions, go to the **Settings** tab, scroll down to the **User authentication settings** section, and select **"Read and Write"** under **App permissions**.

## Set your keys to environment variables
There are two ways to set your keys to environment variables. You can set them in web interface or in fe.

### Web interface

1. Go to the agent.
2. Click on the "Run" tab.
3. On the left side, click on the "Add" Button next to "Environment Variables".
4. Add the following variables:
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
   - `X_CONSUMER_KEY`
   - `X_CONSUMER_SECRET`

You must see the following screen:
![env](./twitter/env.png)

### CLI
You can set your keys to environment variables using the following command:
```bash 
curl -X POST "https://<api-url>/v1/create_hub_secret" \
  -H "Authorization: Bearer <YOUR-NEAR-AUTH-TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "example_agent",
    "name": "my_secret_name",
    "version": "0.0.1",
    "description": "GitHub token for my agent",
    "key": "GITHUB_API_TOKEN",
    "value": "ghp_abc123",
    "category": "agent"
  }'



curl -X GET "https://https://app.near.ai//v1/get_user_secrets?limit=10&offset=0" \
  -H "Authorization: Bearer {"auth":{"account_id":"maguila.near","public_key":"ed25519:5FQv7bXse932RvoZ1ZdLqGNUuTmtSLueTZavrH4DQ9u5","signature":"loP40E80I+gQgIDlEzjT5WpZKyNdD66S2uICWI0+ddMFAtgcjlfn1uv0TYws35G52uJcdK9fIyRsUNjebopOCg==","callback_url":"https://app.near.ai/sign-in/callback","message":"Welcome to NEAR AI Hub!","recipient":"ai.near","nonce":"00000000000000000001736863615398"},"currentNonce":"00000000000000000001736863615398","isAuthenticated":true}"
