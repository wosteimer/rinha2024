from collections.abc import AsyncIterable
from datetime import datetime
from typing import AsyncContextManager, NotRequired, Protocol, TypedDict, Unpack

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
    def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> AsyncContextManager[
        Result[AsyncIterable[Entity[Transaction]], ClientDoesNotExistError]
    ]: ...
