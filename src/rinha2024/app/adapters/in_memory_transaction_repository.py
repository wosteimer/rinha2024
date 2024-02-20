from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Unpack

from returns import Err, Ok
from returns.result import Result

from ...adapters.errors import ClientDoesNotExistError
from ...adapters.transaction_repository import (
    CreateProps,
    GetByClientIdProps,
    TransactionRepository,
)
from ...core.entities.transaction import Transaction


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(
        self, clients: dict[int, int], transactions: list[Transaction]
    ) -> None:
        self.__clients = clients
        self.__transactions = transactions

    async def create(
        self, **props: Unpack[CreateProps]
    ) -> Result[None, ClientDoesNotExistError]:
        if props["client_id"] not in self.__clients:
            return Err(ClientDoesNotExistError())

        self.__transactions.append(
            Transaction(
                id=len(self.__transactions),
                created_at=datetime.now(timezone.utc),
                **props
            )
        )
        return Ok(None)

    async def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> Result[Sequence[Transaction], ClientDoesNotExistError]:
        if props["id"] not in self.__clients:
            return Err(ClientDoesNotExistError())
        if "starting_from" not in props:
            props["starting_from"] = datetime.now(timezone.utc)
        if "amount" not in props:
            props["amount"] = len(self.__transactions)
        return Ok(
            sorted(
                filter(
                    lambda transaction: transaction.client_id == props["id"]
                    and transaction.created_at <= props["starting_from"],
                    self.__transactions,
                ),
                key=lambda transaction: transaction.created_at,
                reverse=True,
            )[0 : props["amount"]]
        )
