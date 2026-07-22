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

- `jupyter-publish-service` installed with the JupyterHub extra
  (`pip install -e ".[jupyterhub]"` from the repo root) — the extra pulls
  in JupyterHub, which the `HubAuthenticator` needs; the base install
  brings `aiosqlite`/`greenlet`/etc.
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

## Kubernetes with kind

Two ways to run this on a local [kind](https://kind.sigs.k8s.io/) cluster.
Both deploy the publishing service as a **separate Deployment**
(`kind/publishing-service.yaml`) that talks to the Hub at
`http://hub:8081/hub/api`; they differ only in how the Hub itself runs:

- **Single-pod Hub** (`kind/hub-deployment.yaml`) — one stock
  `jupyterhub/jupyterhub` pod with the proxy running in-process. Recommended
  for kind; this is the path validated end-to-end.
- **z2jh Helm chart** (`kind/z2jh-values.yaml`) — the production-shaped
  Zero-to-JupyterHub deployment (Hub, proxy, and pre-puller as separate pods).

Prerequisites: `kind`, `kubectl`, `helm` (for the z2jh path), Docker, `openssl`.

### Common setup (both paths)

```
# 1. Cluster.
kind create cluster --name jpsvc

# 2. Build the publishing-service image and load it into the cluster.
#    (Build context is the repo root.)
docker build -f examples/jupyterhub/Dockerfile -t jupyter-publishing:demo ../..
kind load docker-image jupyter-publishing:demo --name jpsvc

# 3. Namespace + the shared secret referenced by both the Hub and the service.
#    Three keys: the service-owned token plus a pre-minted token per demo user.
kubectl create namespace jhub
kubectl create secret generic publishing-shared-token -n jhub \
    --from-literal=service-token="$(openssl rand -hex 32)" \
    --from-literal=alice-token="$(openssl rand -hex 32)" \
    --from-literal=bob-token="$(openssl rand -hex 32)"
```

### Path A: single-pod Hub (recommended)

```
# Load the stock Hub image (bundles configurable-http-proxy).
docker pull jupyterhub/jupyterhub:5
kind load docker-image jupyterhub/jupyterhub:5 --name jpsvc

kubectl apply -n jhub -f kind/hub-deployment.yaml
kubectl apply -n jhub -f kind/publishing-service.yaml
kubectl rollout status -n jhub deploy/hub deploy/publish
```

The Hub pod holds its state in the pod (ephemeral): a restart re-mints the
demo tokens from the Secret, so nothing breaks. Add a PVC if you want it to
survive restarts.

### Path B: z2jh Helm chart

```
helm repo add jupyterhub https://hub.jupyter.org/helm-chart/
helm repo update
helm upgrade --install hub jupyterhub/jupyterhub \
    --namespace jhub --values kind/z2jh-values.yaml --timeout 10m
kubectl apply -n jhub -f kind/publishing-service.yaml
kubectl rollout status -n jhub deploy/hub deploy/publish
```

Caveats (why Path A is recommended for kind):

- z2jh runs the Hub, proxy, and image pre-puller as separate pods. On a
  small kind node the Hub's event loop can starve, showing up as
  `api_request to the proxy failed ... status code 599` and
  `Event loop was unresponsive`. Give each node **≥3 CPU**.
- The chart pulls `k8s-hub`/`configurable-http-proxy` from `quay.io`. If
  kind can't reach it (`ErrImagePull`), `docker pull` the exact images and
  tags the chart wants, `kind load` them, and point `hub.image`/`proxy.chp.image`
  at those names.
- This path was **not** validated end-to-end here; the values file is
  correct but the multi-pod runtime is what makes it finicky on kind.

If you previously ran Path B and are switching to Path A, run
`helm uninstall hub -n jhub` first so its `hub` Service does not collide with
the single-pod one.

### Verify (both paths)

```
# Optional: health check via port-forward.
kubectl port-forward -n jhub svc/publish 9000:9000 &
curl -s localhost:9000/ ; echo

# Run the two-user demo from inside the publish pod (env is already wired).
kubectl exec -n jhub deploy/publish -- python3 /src/examples/jupyterhub/demo.py
```

Success = the demo prints steps 1–4 and ends with `--- done ---`.

Tear down with `kind delete cluster --name jpsvc`.

**Scope gotcha:** the demo users receive `custom:publishing` via a dedicated
`publishing-user` role assigned to alice/bob. Do **not** instead grant it by
overriding the default `user` role — that drops the built-in user scopes, so
`/hub/api/user` returns empty scopes and the publishing service rejects the
caller with `403 Caller missing required scope(s): ['custom:publishing']`.

## Limitation: per-authority user search

In this version the user-search autocomplete returns users only from
the _caller's_ authority. To add a collaborator from a different
registered authority (e.g. alice@hub-local sharing with carol@lab-local),
the sharer must type the qualified `username@authority` directly.
Federated search across all registered authorities is planned as a
follow-up.
