import hashlib
import logging
import subprocess
from typing import Optional

import requests
from dcap_qvl import verify_quote  # type: ignore
from nearai.shared.auth_data import AuthData
from runners.nearai_cvm.app.main import AssignRequest, IsAssignedResp, QuoteResponse, RunRequest

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

    def attest(self):
        """Attests the CVM."""
        response = requests.get(f"{self.url}/quote", headers=self.headers)
        if response.status_code != 200:
            raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

        quote = QuoteResponse(**response.json())

        cmd = f"""echo | openssl s_client -connect {self.url} 2>/dev/null |\
             openssl x509 -pubkey -noout -outform DER | openssl dgst -sha256"""
        ssl_pub_key = subprocess.check_output(cmd, shell=True).decode("utf-8").split("= ")[1].strip()
        report_data = generate_sha512_hash(ssl_pub_key)

        try:
            verified = verify_quote(quote.quote.encode("utf-8"))
            if not verified:
                raise Exception("Quote verification failed")
            if verified["report"]["TD10"]["report_data"] != report_data:
                raise Exception("Report data mismatch")
        except Exception as e:
            logger.error(f"Quote verification failed: {e}")
            raise e

        return quote


def generate_sha512_hash(report_data: str, prefix: str = "app-data"):
    # Ensure report_data is properly encoded
    report_data_bytes = report_data.encode("utf8")

    # Compute SHA-512 hash
    sha512_hash = hashlib.sha512(f"{prefix}:".encode() + report_data_bytes).hexdigest()

    return sha512_hash
