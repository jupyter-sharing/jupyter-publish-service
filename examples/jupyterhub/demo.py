"""Two-user sharing demo against the publishing service.

Walks through the canonical flow:

  1. alice creates a notebook share with bob as a collaborator.
  2. bob lists his shares and sees the notebook.
  3. bob fetches the notebook contents and the collaborator list.
  4. alice searches for users; HubUserStore returns the hub's user list.

Assumes JupyterHub and the publishing service are already running, and
that pre-minted hub API tokens for alice and bob are exported via
`ALICE_TOKEN` and `BOB_TOKEN`. See `run_demo.sh`.
"""
import asyncio
import os
import sys
import uuid

from jupyter_publishing_service.client.simple import AsyncPublishingClient
from jupyter_publishing_service.models.rest import SharedFileRequestModel
from jupyter_publishing_service.models.sql import (
    JupyterContentsModel,
    Role,
    SharedFileMetadata,
    User,
)


PUBLISH_URL = os.environ.get("PUBLISH_URL", "http://localhost:9000")
AUTHORITY = os.environ.get("DEMO_AUTHORITY", "hub-local")  # matches publishing_config.py


def _client(token: str) -> AsyncPublishingClient:
    return AsyncPublishingClient(
        service_url=PUBLISH_URL,
        api_token=token,
        extra_headers={"X-Jupyter-Authority": AUTHORITY},
    )


def _hr(label: str) -> None:
    print(f"\n--- {label} " + "-" * max(0, 60 - len(label)))


async def main() -> int:
    try:
        alice_token = os.environ["ALICE_TOKEN"]
        bob_token = os.environ["BOB_TOKEN"]
    except KeyError as e:
        print(f"missing env var: {e}", file=sys.stderr)
        return 2

    alice = _client(alice_token)
    bob = _client(bob_token)

    file_id = uuid.uuid4().hex
    metadata = SharedFileMetadata(
        id=file_id,
        author="alice",
        name="hello.ipynb",
        title="Hello demo",
        version=1,
    )
    contents = JupyterContentsModel(
        id=file_id,
        name="hello.ipynb",
        path="hello.ipynb",
        type="notebook",
        writable=True,
        mimetype="application/x-ipynb+json",
        format="json",
        content={
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": "# Hello from alice\n\nShared via jupyter-publish-service.",
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": "print('hi bob')",
                },
            ],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5,
        },
    )
    request = SharedFileRequestModel(
        metadata=metadata,
        users=[
            User(authority=AUTHORITY, username="alice"),
            User(authority=AUTHORITY, username="bob"),
        ],
        roles=[Role(name="WRITER")],
        contents=contents,
    )

    _hr("step 1: alice creates a share with bob as a collaborator")
    print(f"file_id = {file_id}")
    response = await alice.add_file(request)
    print(f"created: name={response.metadata.name!r} author={response.metadata.author!r}")

    _hr("step 2: bob lists his shares")
    shares = await bob.list_files()
    print(f"bob sees {len(shares)} share(s):")
    for s in shares:
        print(f"  - {s.metadata.id}  name={s.metadata.name!r}  author={s.metadata.author!r}")
    if not any(s.metadata.id == file_id for s in shares):
        print("ERROR: bob does not see alice's share", file=sys.stderr)
        return 1

    _hr("step 3: bob fetches the notebook with collaborators")
    full = await bob.get_file(file_id, contents=True, collaborators=True)
    if full.contents:
        cells = full.contents.content.get("cells", []) if full.contents.content else []
        print(f"contents: name={full.contents.name!r} type={full.contents.type!r} cells={len(cells)}")
    else:
        print("ERROR: bob got no contents in the response", file=sys.stderr)
        return 1
    if full.collaborator:
        print(f"collaborators: {[u.username for u in full.collaborator]}")

    _hr("step 4: alice searches for users (HubUserStore)")
    users = await alice.search_users(substring="b")
    print(f"users matching 'b': {[u.username for u in users]}")

    _hr("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
