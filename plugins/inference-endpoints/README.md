# Inference Endpoints Plugin

Lets administrators add and remove any number of OpenAI-compatible inference endpoints, such as [Ollama](https://ollama.com), vLLM, LM Studio, the llama.cpp server, LiteLLM or OpenRouter. Each endpoint is registered as a provider in the core LLM provider registry (`fastapi_app/lib/llm/`), so its models can be selected wherever the registry is used (for example Tools > Default Model, the [Annotation Review](../annotation-review/README.md) plugin and the [LLamore extractor](../llamore-extractor/README.md)).

## Usage

Administrators open the management page from the plugin menu (Inference > Inference endpoints). For each endpoint they enter:

| Field | Meaning |
| --- | --- |
| Name | Label of the provider in the model picker; models appear as `<Name>/<model id>` |
| Base URL | The URL that `/chat/completions` and `/models` are appended to, e.g. `http://localhost:11434/v1` for Ollama |
| API key | No key; a shared key used for all users; or per-user keys, which each user enters under user menu > API Keys |
| Models | Comma-separated model ids to offer; empty offers every model the endpoint lists at `GET /models` |
| Vision | The models accept images (sent as `image_url` content parts with base64 data URLs) |
| Free | Non-admin users may use the models. Otherwise only administrators can, unless a model is the default model (see the editor's model access rules) |
| Timeout | Seconds to wait for a completion (default 600, since local models can be slow) |

"Test connection" lists the models of the endpoint before or after saving it. An endpoint cannot be edited; delete it and add it again.

## Models on your own computer (Ollama)

The server sends the requests to the endpoint, not the browser. Two things follow:

- **CORS does not apply.** Browser CORS settings such as `OLLAMA_ORIGINS` are not needed.
- **The endpoint must be reachable from the server.** `localhost` in the base URL is the machine or container the editor runs on.

Depending on where the editor runs:

| Editor runs | Base URL |
| --- | --- |
| On your computer (`npm run start:dev`, `uv run ...`) | `http://localhost:11434/v1` |
| On your computer, in Docker | `http://host.docker.internal:11434/v1`. On Linux, start the container with `--add-host=host.docker.internal:host-gateway` and make Ollama listen on all interfaces (`OLLAMA_HOST=0.0.0.0`) |
| On a remote server | The server cannot reach your computer's `localhost`. Connect the two through a VPN such as Tailscale (`http://<machine>.<tailnet>.ts.net:11434/v1`, with `OLLAMA_HOST=0.0.0.0`), or an SSH reverse tunnel from your computer (`ssh -N -R 11434:localhost:11434 user@server`, then `http://localhost:11434/v1`; in Docker the tunnel has to end where the container can reach it). Tunnel services such as ngrok or Cloudflare Tunnel work too, but make Ollama, which has no authentication, publicly reachable: put an authenticating proxy in front of it and enter its key here |

Calling the model directly from the browser, which would need `OLLAMA_ORIGINS`, is not supported: all LLM features of the editor (extraction, review, metadata) run on the server.

## Security

Endpoint URLs make the server send requests, so the management page and its API are restricted to administrators. URLs must be `http` or `https` without credentials, query or fragment. Local and private addresses are allowed (that is what Ollama on `localhost` or in a VPN needs), but link-local addresses (`169.254.0.0/16`, `fe80::/10`, including cloud metadata services), multicast and unspecified addresses are always rejected. The URL is checked when an endpoint is saved and before each request, and redirects are not followed.

API keys are stored encrypted in the editor's secret store (the shared key under a reserved pseudo user, per-user keys under each user) and are never returned by the API.

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `INFERENCE_ENDPOINTS_ALLOWED_HOSTS` | none (all hosts allowed, except the addresses above) | Comma-separated host names (`ollama.example.org`, `*.ts.net`) and networks in CIDR notation (`10.0.0.0/8`, `127.0.0.1/32`). If set, endpoint URLs must match one of them; a host name matches by name, an IP network matches if all addresses of the host are in it. Read from the environment only, so that administrators cannot widen it in the application's configuration |

The endpoints are stored in `data/db/inference-endpoints.json`. Every server worker watches this file and updates its providers within a few seconds of a change.

## Provider

- Provider ID: `endpoint-<id>`, where `<id>` is derived from the name
- Requests: `POST {base_url}/chat/completions` (non-streaming), `GET {base_url}/models`, with `Authorization: Bearer <key>` if there is a key
- Image input if "Vision" is set; PDF input is not supported (consumers send the PDF's text layer instead)

## Implementation

- **Plugin file**: [plugin.py](src/pte_plugin_inference_endpoints/plugin.py) (provider registration, file watcher)
- **Provider**: [llm_provider.py](src/pte_plugin_inference_endpoints/llm_provider.py)
- **Storage**: [store.py](src/pte_plugin_inference_endpoints/store.py), [keys.py](src/pte_plugin_inference_endpoints/keys.py)
- **URL checks**: [url_policy.py](src/pte_plugin_inference_endpoints/url_policy.py)
- **Routes and page**: [routes.py](src/pte_plugin_inference_endpoints/routes.py), [static/manage.html](src/pte_plugin_inference_endpoints/static/manage.html)
- **Tests**: [tests/](src/pte_plugin_inference_endpoints/tests/)

## Technical Details

- Category: `inference`
- Menu entry and API: admin role. The registered models follow the editor's model access rules
