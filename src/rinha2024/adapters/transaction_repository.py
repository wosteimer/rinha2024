from datetime import datetime
from typing import NotRequired, Protocol, Sequence, TypedDict, Unpack

from returns.result import Result

from ..adapters.errors import ClientDoesNotExistError, NoLimitError
from ..core.entities.client import Client
from ..core.entities.entity import Entity
from ..core.entities.transaction import Transaction


class GetByClientIdProps(TypedDict):
    id: int
    starting_from: NotRequired[datetime]
    amount: NotRequired[int]


class TransactionRepository(Protocol):
    async def create(
        self, transaction: Transaction
    ) -> Result[Entity[Client], ClientDoesNotExistError | NoLimitError]: ...
    async def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> Result[Sequence[Entity[Transaction]], ClientDoesNotExistError]: ...
