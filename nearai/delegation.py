from datetime import datetime, timedelta
from typing import List, Union

from nearai.openapi_client.api.delegation_api import Delegation, DelegationApi
from nearai.openapi_client.api_client import ApiClient
from nearai.shared.auth_data import AuthData


class OnBehalfOf:
    """Create a context manager that allows you to delegate actions to another account.

    ```python
    with OnBehalfOf("scheduler.ai"):
        # Upload is done on behalf of scheduler.ai
        # If delegation permission is not granted, this will raise an exception
        registry.upload()
    ```
    """

    def __init__(self, on_behalf_of: str):
        """Context manager that creates a scope where all actions are done on behalf of another account."""
        self.target_on_behalf_of = on_behalf_of
        self.original_access_token = None

    def __enter__(self):
        """Set the default client to the account we are acting on behalf of."""
        default_client = ApiClient.get_default()
        self.original_access_token = default_client.configuration.access_token

        if not isinstance(self.original_access_token, str):
            return

        assert self.original_access_token.startswith("Bearer ")
        auth = self.original_access_token[len("Bearer ") :]
        auth_data = AuthData.model_validate_json(auth)
        auth_data.on_behalf_of = self.target_on_behalf_of
        new_access_token = f"Bearer {auth_data.generate_bearer_token()}"
        default_client.configuration.access_token = new_access_token

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset the default client to the original account."""
        default_client = ApiClient.get_default()
        default_client.configuration.access_token = self.original_access_token
        self.original_access_token = None


def check_on_behalf_of():
    """Check if the request is being made on behalf of another account."""
    api = DelegationApi()
    return api.api_client.configuration.access_token


def delegate(account_id: str, expires_at: Union[datetime, timedelta]):
    if isinstance(expires_at, timedelta):
        expires_at = datetime.now() + expires_at
    DelegationApi().delegate_v1_delegation_delegate_post(account_id, expires_at)


def list_delegations() -> List[Delegation]:
    return DelegationApi().list_delegation_v1_delegation_list_delegations_post()


def revoke_delegation(delegate_account_id: str):
    """Revoke delegation to a specific account."""
    DelegationApi().revoke_delegation_v1_delegation_revoke_delegation_post(delegate_account_id)
