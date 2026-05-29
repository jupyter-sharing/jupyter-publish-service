# An example with JupyterHub and standalone JupyterLab

This example wires a single publishing service to two authorities:
- A JupyterHub at `localhost:8000` (authority `hub-local`)
- A standalone JupyterLab (authority `lab-local`)

Either side can share notebooks with the other; user identities are
namespaced by authority so the same `username` from each side never
collides.

## Quick start: run the two-user demo

`run_demo.sh` boots both services locally, mints API tokens for two
hub users (alice and bob), and walks through alice creating a
notebook share that bob can read.

Prerequisites:
- `jupyter-publish-service` installed (`pip install -e .` from the
  repo root) — pulls in JupyterHub and `aiosqlite`/`greenlet`/etc.
- [`configurable-http-proxy`](https://github.com/jupyterhub/configurable-http-proxy):
  JupyterHub's default proxy, distributed as a Node.js package.
  Install with `npm install -g configurable-http-proxy` (install
  Node.js first if `npm` is not on your PATH).
- `openssl` for generating per-run secrets.

Then:

```
./run_demo.sh
```

The script prints each step. Logs go to `/tmp/jpsvc-hub.log` and
`/tmp/jpsvc-publish.log`. Press Ctrl-C while it's running and both
services are torn down by the trap.

What the demo exercises:

1. alice creates a share with bob as a collaborator.
2. bob lists his shares and sees the notebook alice just shared.
3. bob fetches the notebook contents and the collaborator list.
4. alice searches users via `HubUserStore` (the autocomplete used
   by JupyterLab's sharing dialog).

If you want to inspect the moving parts manually instead, read on.

## Manual setup

### 1. Pick a shared service API token

```
export PUBLISH_SERVICE_API_TOKEN=$(openssl rand -hex 32)
```

### 2. Start JupyterHub

```
jupyterhub --config hub_config.py
```

This declares the `custom:publishing` scope, registers `publish` as an
external service that shares `PUBLISH_SERVICE_API_TOKEN` with the
publishing service, grants `list:users`/`read:users` to the service
itself, and grants every user the `custom:publishing` scope.

### 3. Start the publishing service

```
export JUPYTER_HUB_API_URL=http://localhost:8000/hub/api
export JUPYTERHUB_API_TOKEN=$PUBLISH_SERVICE_API_TOKEN
export LAB_JWKS_URL=https://idp.example.com/.well-known/jwks.json
jupyter publishing --config publishing_config.py
```

`publishing_config.py` registers both authorities. To run only one,
drop the other entry from the `authorities` list.

### 4. How clients pick an authority

Clients should send the `X-Jupyter-Authority` header on every request,
matching one of the configured `name` values (`hub-local` or
`lab-local`). For Hub-spawned single-user servers, set this in
`c.Spawner.environment` and have the jupyter-server extension forward
it. The publishing service falls back to matching the `Host` header
against each authority's `hosts` list when the header is absent.

## Limitation: per-authority user search

In this version the user-search autocomplete returns users only from
the *caller's* authority. To add a collaborator from a different
registered authority (e.g. alice@hub-local sharing with carol@lab-local),
the sharer must type the qualified `username@authority` directly.
Federated search across all registered authorities is planned as a
follow-up.
