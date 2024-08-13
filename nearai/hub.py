import json

import requests

from nearai.config import load_config_file

config = load_config_file()


def hub(query, endpoint, model, provider, info):
    try:
        auth = config["auth"]
        bearer_data = {
            "account_id": auth["account_id"],
            "public_key": auth["public_key"],
            "signature": auth["signature"],
            "callback_url": auth["callback_url"],
            "message": auth["message"],
            "nonce": auth["nonce"],
            "recipient": auth["recipient"],
        }

        bearer_token = json.dumps(bearer_data)

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {bearer_token}"}

        data = {
            "max_tokens": 256,
            "temperature": 1,
            "frequency_penalty": 0,
            "n": 1,
            "messages": [{"role": "user", "content": query}],
            "model": model,
            "provider": provider,
        }

        if info:
            print(f'Requesting hub using NEAR Account {auth["account_id"]}')

        response = requests.post(endpoint, headers=headers, data=json.dumps(data))

        completion = response.json()

        print(completion["choices"][0]["message"]["content"])

    except Exception as e:
        print(f"Request failed: {e}")
