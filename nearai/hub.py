import json

import requests

from nearai.config import Config, NearAiHubConfig


class Hub(object):
    def __init__(self, config: Config) -> None:
        """Initializes the Hub class with the given configuration."""
        self.info = None
        self.provider = None
        self.model = None
        self.endpoint = None
        self.query = None
        self._config = config

    def parse_hub_chat_params(self, kwargs):
        """Parses and sets instance attributes from the given keyword arguments, using default values if needed."""
        if self._config.nearai_hub is None:
            self._config.nearai_hub = NearAiHubConfig()

        self.query = kwargs.get("query")
        self.endpoint = kwargs.get("endpoint", f"{self._config.nearai_hub.base_url}/chat/completions")
        self.model = kwargs.get("model", self._config.nearai_hub.default_model)
        self.provider = kwargs.get("provider", self._config.nearai_hub.default_provider)
        self.info = kwargs.get("info", False)

    def chat(self, kwargs):
        """Processes a chat request by sending parameters to the NEAR AI Hub and printing the response."""
        try:
            self.parse_hub_chat_params(kwargs)

            if not self.query:
                return print("Error: 'query' is required for the `hub chat` command.")

            if self._config.nearai_hub is None:
                self._config.nearai_hub = NearAiHubConfig()

            data = {
                "max_tokens": 256,
                "temperature": 1,
                "frequency_penalty": 0,
                "n": 1,
                "messages": [{"role": "user", "content": str(self.query)}],
                "model": self.model,
            }

            auth = self._config.auth

            if self._config.nearai_hub.login_with_near:
                bearer_token = auth.generate_bearer_token()
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {bearer_token}"}

                data["provider"] = self.provider
            elif self._config.nearai_hub.api_key:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {}".format(self._config.nearai_hub.api_key),
                }
            else:
                return print("Illegal NEAR AI Hub Config")

            if self.info:
                print(f"Requesting hub using NEAR Account {auth.account_id}")

            response = requests.post(self.endpoint, headers=headers, data=json.dumps(data))

            completion = response.json()

            print(completion["choices"][0]["message"]["content"])

        except Exception as e:
            print(f"Request failed: {e}")
