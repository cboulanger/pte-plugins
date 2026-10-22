"""
API keys of the endpoints, kept in the core's encrypted secret store.

A shared key (key mode "shared") is stored under the pseudo user ``SHARED_KEY_OWNER``
and the endpoint's secret service; per-user keys (key mode "user") are stored by each
user under the same service id through the API Keys dialog.
"""

from fastapi_app.lib.secrets import SecretServiceRegistry, get_secret_store, register_secret_service

from .store import Endpoint

# Not a valid login name in practice; the secrets API only ever acts on the requesting user's
# own name, so users cannot read or replace this entry
SHARED_KEY_OWNER = ":inference-endpoints"


def get_shared_key(endpoint: Endpoint) -> str | None:
    """The shared key of an endpoint, or None."""
    return get_secret_store().get(SHARED_KEY_OWNER, endpoint.secret_service)


def set_shared_key(endpoint: Endpoint, key: str) -> None:
    """Store the shared key of an endpoint."""
    get_secret_store().set(SHARED_KEY_OWNER, endpoint.secret_service, key)


def delete_shared_key(endpoint: Endpoint) -> None:
    """Remove the shared key of an endpoint, if there is one."""
    get_secret_store().delete(SHARED_KEY_OWNER, endpoint.secret_service)


def register_user_key_service(endpoint: Endpoint) -> None:
    """Make the endpoint appear in the users' API Keys dialog."""
    register_secret_service(
        endpoint.secret_service,
        endpoint.name,
        f"Used for the models of the inference endpoint {endpoint.base_url}.",
    )


def unregister_user_key_service(endpoint_id: str) -> None:
    """Remove a deleted endpoint from the users' API Keys dialog (needs a core with SecretServiceRegistry.unregister)."""
    unregister = getattr(SecretServiceRegistry, "unregister", None)
    if unregister is not None:
        unregister(f"inference-endpoint-{endpoint_id}")
