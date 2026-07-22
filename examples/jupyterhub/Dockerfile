# Image for the PUBLISHING SERVICE only.
#
# This is deliberately NOT a JupyterHub image. The publishing service is a
# separate app that fronts one or more Jupyter deployments; it does not run,
# spawn, or proxy a Hub. The Hub in docker-compose.yml uses the stock
# `jupyterhub/jupyterhub` image, unmodified.
#
# `[jupyterhub]` extra is installed because publishing_config.py configures a
# HubAuthenticator authority, whose lazy import needs `check_scopes` from the
# jupyterhub package. A JWT-only deployment could drop the extra and this
# image would shrink accordingly.
#
# Build context is the REPOSITORY ROOT (docker-compose.yml sets context: ../..):
#     docker build -f examples/jupyterhub/Dockerfile -t jupyter-publishing:demo .
FROM python:3.11-slim

COPY . /src
RUN python3 -m pip install --no-cache-dir "/src[jupyterhub]"

# publishing_config.py and demo.py are referenced by absolute path.
WORKDIR /src/examples/jupyterhub
EXPOSE 9000

# Bind to 0.0.0.0 (the service defaults to localhost, unreachable across a
# container boundary). Overridable on the command line in docker-compose.yml.
CMD ["jupyter-publishing", \
     "--config=/src/examples/jupyterhub/publishing_config.py", \
     "--JupyterPublishingService.ip=0.0.0.0", \
     "--JupyterPublishingService.port=9000"]
