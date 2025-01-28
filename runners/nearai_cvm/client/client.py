import logging
from typing import Optional

import requests
from nearai.shared.auth_data import AuthData
from runners.nearai_cvm.app.main import AssignRequest, IsAssignedResp, RunRequest

logger = logging.getLogger(__name__)


class CvmClient:
    def __init__(self, url: str, auth: Optional[AuthData] = None):
        """Initializes the NearAITeeClient.

        Args:
            url: The base URL for the CVM service
            auth: Optional Bearer token for authorization

        """
        self.url = url
        if auth is not None:
            self.headers = {"Authorization": f"Bearer {auth.model_dump_json()}"}
        else:
            self.headers = {}

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

    def is_assigned(self) -> IsAssignedResp:
        """Checks the health of the CVM."""
        response = requests.get(f"{self.url}/is_assigned", headers=self.headers)
        logger.info(f"Health response: {response.json()}")

        response.raise_for_status()
        return IsAssignedResp(**response.json())
