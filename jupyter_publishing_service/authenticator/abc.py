from abc import ABCMeta, abstractmethod
from typing import Optional

from jupyter_publishing_service.models.sql import User


class AuthenticatorABC(metaclass=ABCMeta):
    """Validate a bearer token and return the user it identifies.

    Implementations are bound to a single `authority` (set by the service
    at construction time) and must stamp it onto every User they return,
    so that downstream code can distinguish users with the same `username`
    coming from different Jupyter deployments.
    """

    @abstractmethod
    async def authenticate(self, token: str) -> Optional[User]:
        """
        Validate the bearer token and return the authenticated user.

        Must return a `User` with `authority` and `username` populated on
        success, or `None` on failure (callers translate `None` into 401).
        Implementations should raise `fastapi.HTTPException` for definitive
        rejections (e.g. token valid but missing required scope → 403).
        """
        raise NotImplementedError
