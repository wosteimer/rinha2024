from collections.abc import Sequence
from typing import Protocol

from returns import Result

from ..core.entities.client import Client
from .errors import ClientAlreadyExists, ClientDoesNotExistError


class ClientRepository(Protocol):
    async def create(
        self, id: int, limit: int
    ) -> Result[None, ClientAlreadyExists]: ...
    async def get(self, id: int) -> Result[Client, ClientDoesNotExistError]: ...
    async def get_all(self) -> Sequence[Client]: ...
    async def exists(self, id: int) -> bool: ...
