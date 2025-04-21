import hashlib
import json
import logging
import subprocess
import tempfile
from typing import Optional
from urllib.parse import urlparse

import requests
from dcap_qvl import verify_quote  # type: ignore
from dstack_sdk import TdxQuoteResponse  # type: ignore
from nearai.shared.auth_data import AuthData
from runners.nearai_cvm.app.main import AssignRequest, IsAssignedResp, QuoteResponse, RunRequest, Worker

logger = logging.getLogger(__name__)


class CvmClient:
    def __init__(self, url: str, auth: Optional[AuthData] = None):
        """Initializes the NearAITeeClient.

        Args:
            url: The base URL for the CVM service
            auth: Optional Bearer token for authorization

        """
        self.url = url
        self.headers = {"Authorization": f"Bearer {auth.model_dump_json()}"} if auth else {}
        self.is_attested = False

        # Get and store server's certificate
        parsed = urlparse(url)
        self.hostname = parsed.hostname or "localhost"
        self.port = str(parsed.port or (443 if parsed.scheme == "https" else 80))

        cert_file = tempfile.NamedTemporaryFile(delete=True, suffix=".pem")
        self.cert_path = cert_file.name
        cert_file.close()

        # Fetch server certificate
        cmd = f"""echo | openssl s_client -connect {self.hostname}:{self.port} -servername {self.hostname} \
            -showcerts 2>/dev/null </dev/null | openssl x509 -outform PEM > {self.cert_path}"""
        subprocess.run(cmd, shell=True, check=True)
        logger.info(f"Certificate saved to {self.cert_path}")

    def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make an HTTP request with proper certificate verification."""
        if not self.is_attested and path != "quote":
            logger.info("Server not attested yet, performing attestation...")
            self._attest()
        logger.info(f"Headers: {self.headers}")

        url = f"{self.url}/{path.lstrip('/')}"
        response = requests.request(method, url, headers=self.headers, verify=False, **kwargs)
        response.raise_for_status()
        return response

    def _attest(self):
        """Internal method to perform attestation."""
        if self.is_attested:
            return

        # Get quote from server, no auth!
        response = requests.get(f"{self.url}/quote", verify=False)
        print(response.text)
        response.raise_for_status()
        quote = TdxQuoteResponse(**response.json())
        print(quote)

        # Get certificate's public key hash
        cmd = f"""openssl x509 -in {self.cert_path} -pubkey -noout -outform DER | openssl dgst -sha256"""
        ssl_pub_key = subprocess.check_output(cmd, shell=True).decode("utf-8").split("= ")[1].strip()
        report_data = generate_sha512_hash(ssl_pub_key)

        # Verify quote and certificate
        try:
            verified = verify_quote(quote.quote.encode("utf-8"))
            if not verified:
                raise Exception("Quote verification failed")

            print("Verification result\n", verified)

            verified = json.loads(verified)
            if verified["report"]["TD10"]["report_data"] != report_data:
                raise Exception("Report data mismatch")

            self.is_attested = True
            logger.info("Attestation successful - certificate is now trusted")
        except Exception as e:
            logger.error(f"Quote verification failed: {e}")
            raise e

    def assign(self, request: AssignRequest) -> Worker:
        """Assigns an agent to a CVM."""
        logger.info(f"Assigning agent {request.agent_id} to CVM")
        response = self._make_request("POST", "assign_cvm", json=request.model_dump())
        return Worker(**response.json())

    def run(self, request: RunRequest):
        """Runs an agent on a CVM."""
        logger.info(f"Running agent on CVM, run_id: {request.run_id}")
        response = self._make_request("POST", "run", json=request.model_dump())
        return response.json()

    def is_assigned(self) -> IsAssignedResp:
        """Checks the health of the CVM."""
        response = self._make_request("GET", "is_assigned")
        logger.info(f"Health response: {response.json()}")
        return IsAssignedResp(**response.json())

    def attest(self):
        """Public method to manually trigger attestation."""
        self._attest()
        return QuoteResponse(quote=self._make_request("GET", "quote").json()["quote"])


def generate_sha512_hash(report_data: str, prefix: str = "app-data"):
    """Generate SHA-512 hash of the report data with prefix."""
    report_data_bytes = report_data.encode("utf8")
    sha512_hash = hashlib.sha512(f"{prefix}:".encode() + report_data_bytes).hexdigest()
    return sha512_hash
