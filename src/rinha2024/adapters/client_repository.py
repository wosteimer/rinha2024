from collections.abc import Sequence
from typing import Protocol

from returns import Result

from ..core.entities.client import Client
from ..core.entities.entity import Entity
from .errors import ClientAlreadyExists, ClientDoesNotExistError


class ClientRepository(Protocol):
    async def create(
        self, client: Client
    ) -> Result[Entity[Client], ClientAlreadyExists]: ...
    async def get(self, id: int) -> Result[Entity[Client], ClientDoesNotExistError]: ...
    async def get_all(self) -> Sequence[Entity[Client]]: ...
    async def exists(self, id: int) -> bool: ...
