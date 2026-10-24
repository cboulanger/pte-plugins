"""
Which endpoint URLs the server may send requests to.

Endpoints are configured by administrators and called by the server, so a URL is a way
to make the server send requests into its own network (server-side request forgery).
Local and private addresses stay allowed, since a model on the same machine or in the
same network (Ollama on localhost, a GPU server, a Tailscale address) is the main use
of this plugin. Always rejected are link-local addresses (169.254.0.0/16 and fe80::/10,
which include the cloud metadata services), multicast and unspecified addresses.

Operators can restrict the endpoints further with the environment variable
``INFERENCE_ENDPOINTS_ALLOWED_HOSTS``: a comma-separated list of host names
(``*.example.org`` matches subdomains) and networks in CIDR notation
(``10.0.0.0/8``, ``127.0.0.1/32``). If it is set, a URL must match one of them. It is
read from the environment and not from the configuration, which administrators can
edit in the application.

The URL is checked when an endpoint is saved and before every request; requests do not
follow redirects.
"""

import ipaddress
import os
import socket
from urllib.parse import urlsplit

ALLOWED_HOSTS_ENV_VAR = "INFERENCE_ENDPOINTS_ALLOWED_HOSTS"

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class EndpointURLError(ValueError):
    """The URL may not be used as an endpoint; the message is user-presentable."""


def _allowed_hosts() -> tuple[list[str], list[IPNetwork]]:
    """The host name patterns and networks of the allowlist (both empty if it is not set)."""
    names: list[str] = []
    networks: list[IPNetwork] = []
    for entry in os.environ.get(ALLOWED_HOSTS_ENV_VAR, "").split(","):
        entry = entry.strip().lower()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            names.append(entry)
    return names, networks


def _name_matches(host: str, pattern: str) -> bool:
    if pattern.startswith("*."):
        return host.endswith(pattern[1:])
    return host == pattern


def _resolve(host: str, port: int) -> list[IPAddress]:
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise EndpointURLError(f"Cannot resolve host '{host}': {e.strerror}") from e
    return [ipaddress.ip_address(str(info[4][0]).split("%")[0]) for info in infos]


def _is_forbidden(address: IPAddress) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_link_local or address.is_multicast or address.is_unspecified


def normalize_base_url(url: str) -> str:
    """
    Check the syntax of a base URL and return it without trailing slash.

    Raises:
        EndpointURLError: If it is not an http(s) URL with a host, or contains credentials,
            a query or a fragment
    """
    url = (url or "").strip()
    try:
        parts = urlsplit(url)
        parts.port  # raises ValueError for an invalid port
    except ValueError as e:
        raise EndpointURLError(f"Invalid URL: {e}") from e
    if parts.scheme not in ("http", "https"):
        raise EndpointURLError("The URL must start with http:// or https://")
    if not parts.hostname:
        raise EndpointURLError("The URL has no host")
    if parts.username or parts.password:
        raise EndpointURLError("The URL must not contain credentials; use the API key instead")
    if parts.query or parts.fragment:
        raise EndpointURLError("The URL must not contain a query or fragment")
    return url.rstrip("/")


def check_url(url: str) -> None:
    """
    Raise EndpointURLError unless the server may send requests to `url`.

    Resolves the host name; an address that changes between this check and the request
    (DNS rebinding) is not detected.
    """
    normalize_base_url(url)
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    port = parts.port or (443 if parts.scheme == "https" else 80)
    addresses = _resolve(host, port)
    if not addresses:
        raise EndpointURLError(f"Cannot resolve host '{host}'")
    forbidden = [a for a in addresses if _is_forbidden(a)]
    if forbidden:
        raise EndpointURLError(f"Host '{host}' resolves to a link-local, multicast or unspecified address ({forbidden[0]})")
    names, networks = _allowed_hosts()
    if not names and not networks:
        return
    if any(_name_matches(host, pattern) for pattern in names):
        return
    if networks and all(any(a in network for network in networks) for a in addresses):
        return
    raise EndpointURLError(f"Host '{host}' is not in {ALLOWED_HOSTS_ENV_VAR}")
