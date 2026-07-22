#!/usr/bin/env bash
# Boots JupyterHub and the publishing service locally, then runs
# `demo.py` to walk through alice creating a share that bob can read.
#
# Requires `jupyter-publishing` (this repo, installed with
# `pip install -e ".[jupyterhub]"` — the extra pulls in JupyterHub),
# `configurable-http-proxy` (a Node.js package
# JupyterHub needs to route requests; install with
# `npm install -g configurable-http-proxy`), and `openssl` on PATH.
# Logs go to /tmp/.
#
# Press Ctrl-C while the demo is running to tear everything down; the
# trap will stop both background services.
set -euo pipefail

cd "$(dirname "$0")"

# Preflight: configurable-http-proxy is JupyterHub's default proxy.
# Without it the Hub aborts during startup with a cryptic error in the
# log; surface it here instead.
if ! command -v configurable-http-proxy >/dev/null; then
    cat >&2 <<'MSG'
ERROR: `configurable-http-proxy` not found on PATH.

JupyterHub requires it as its default proxy. Install with:
    npm install -g configurable-http-proxy

(install Node.js first if `npm` is not available)
MSG
    exit 1
fi

HUB_PORT="${HUB_PORT:-8000}"
PUBLISH_PORT="${PUBLISH_PORT:-9000}"

# Fresh secrets every run.
export PUBLISH_SERVICE_API_TOKEN="${PUBLISH_SERVICE_API_TOKEN:-$(openssl rand -hex 32)}"
export ALICE_TOKEN="${ALICE_TOKEN:-$(openssl rand -hex 32)}"
export BOB_TOKEN="${BOB_TOKEN:-$(openssl rand -hex 32)}"

# What the publishing service sees as its Hub.
export JUPYTER_HUB_API_URL="${JUPYTER_HUB_API_URL:-http://127.0.0.1:${HUB_PORT}/hub/api}"
# Used by HubAuthenticator + HubUserStore as the service-owned token.
export JUPYTERHUB_API_TOKEN="$PUBLISH_SERVICE_API_TOKEN"
# The lab-local authority in publishing_config.py needs SOME JWKS URL
# at construction; the demo never exercises it, so a placeholder is OK.
export LAB_JWKS_URL="${LAB_JWKS_URL:-https://idp.example.com/.well-known/jwks.json}"

# Where the demo Python script reaches the publishing service.
export PUBLISH_URL="${PUBLISH_URL:-http://127.0.0.1:${PUBLISH_PORT}}"
export DEMO_AUTHORITY="${DEMO_AUTHORITY:-hub-local}"

# Clean state so each run is reproducible.
rm -f database.db jupyterhub.sqlite jupyterhub_cookie_secret jupyterhub-proxy.pid

HUB_PID=""
PUB_PID=""

cleanup() {
    set +e
    echo
    echo "stopping services..."
    [[ -n "$HUB_PID" ]] && kill -TERM "$HUB_PID" 2>/dev/null
    [[ -n "$PUB_PID" ]] && kill -TERM "$PUB_PID" 2>/dev/null
    wait 2>/dev/null
}
trap cleanup EXIT INT TERM

echo "starting JupyterHub on :${HUB_PORT} (logs: /tmp/jpsvc-hub.log)"
jupyterhub --config hub_config.py --port "$HUB_PORT" \
    >/tmp/jpsvc-hub.log 2>&1 &
HUB_PID=$!

echo "starting publishing service on :${PUBLISH_PORT} (logs: /tmp/jpsvc-publish.log)"
jupyter publishing --config publishing_config.py \
    --JupyterPublishingService.port="$PUBLISH_PORT" \
    >/tmp/jpsvc-publish.log 2>&1 &
PUB_PID=$!

echo "waiting for services to come up..."
for i in $(seq 1 30); do
    hub_ok=$(curl -sf -o /dev/null -w "%{http_code}" "http://127.0.0.1:${HUB_PORT}/hub/api" 2>/dev/null || true)
    pub_ok=$(curl -sf -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PUBLISH_PORT}/" 2>/dev/null || true)
    if [[ "$hub_ok" == "200" && "$pub_ok" == "200" ]]; then
        echo "ready (hub=${hub_ok}, publish=${pub_ok})"
        break
    fi
    if ! kill -0 "$HUB_PID" 2>/dev/null; then
        echo "JupyterHub exited early; check /tmp/jpsvc-hub.log" >&2
        exit 1
    fi
    if ! kill -0 "$PUB_PID" 2>/dev/null; then
        echo "Publishing service exited early; check /tmp/jpsvc-publish.log" >&2
        exit 1
    fi
    sleep 1
done

echo "diagnostic: GET /hub/api/user with alice's token"
curl -sS -o /tmp/jpsvc-alice-user.json -w "  status=%{http_code}\n" \
    -H "Authorization: token $ALICE_TOKEN" \
    "http://127.0.0.1:${HUB_PORT}/hub/api/user" || true
if [[ -s /tmp/jpsvc-alice-user.json ]]; then
    cat /tmp/jpsvc-alice-user.json
    echo
fi

python demo.py "$@"
demo_status=$?

if [[ "$demo_status" -ne 0 ]]; then
    echo "demo failed (exit $demo_status). hub log: /tmp/jpsvc-hub.log  publish log: /tmp/jpsvc-publish.log" >&2
fi

exit "$demo_status"
