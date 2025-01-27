import logging

import requests
from nearai.shared.auth_data import AuthData
from runners.nearai_cvm.app.main import AssignRequest, RunRequest

logger = logging.getLogger(__name__)


class CvmClient:
    def __init__(self, url: str, auth: AuthData):
        """Initializes the NearAITeeClient.

        Args:
            url: The base URL for the CVM service
            auth: Optional Bearer token for authorization

        """
        self.url = url
        self.headers = {"Authorization": f"Bearer {auth.model_dump_json()}"}

    def assign(self, request: AssignRequest):
        """Assigns an agent to a CVM."""
        logger.info(f"Assigning agent {request.agent_id} to CVM")
        response = requests.post(f"{self.url}/assign", json=request.model_dump(), headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")
        return response.json()

    def run(self, request: RunRequest):
        """Runs an agent on a CVM."""
        logger.info(f"Running agent on on CVM, run_id: {request.run_id}")
        response = requests.post(f"{self.url}/run", json=request.model_dump(), headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")
        return response.json()
