from datetime import datetime
from typing import NotRequired, Protocol, Sequence, TypedDict, Unpack

from returns.result import Result

from ..adapters.errors import ClientDoesNotExistError
from ..core.entities.transaction import Transaction, TransactionKind


class CreateProps(TypedDict):
    client_id: int
    value: int
    kind: TransactionKind
    description: str


class GetByClientIdProps(TypedDict):
    id: int
    starting_from: NotRequired[datetime]
    amount: NotRequired[int]


class TransactionRepository(Protocol):
    async def create(
        self, **props: Unpack[CreateProps]
    ) -> Result[None, ClientDoesNotExistError]: ...
    async def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> Result[Sequence[Transaction], ClientDoesNotExistError]: ...
