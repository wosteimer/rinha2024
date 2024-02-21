from collections.abc import Sequence
from copy import copy
from datetime import datetime, timezone
from typing import Unpack

from returns import Err, Ok
from returns.result import Result

from ...adapters.errors import ClientDoesNotExistError
from ...adapters.transaction_repository import GetByClientIdProps, TransactionRepository
from ...core.entities.entity import Entity
from ...core.entities.transaction import Transaction


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(
        self, clients: dict[int, int], transactions: list[Transaction]
    ) -> None:
        self.__clients = clients
        self.__transactions = transactions

    async def create(
        self, transaction: Transaction
    ) -> Result[Entity[Transaction], ClientDoesNotExistError]:
        if transaction.client_id not in self.__clients:
            return Err(ClientDoesNotExistError())
        entity = Entity(copy(transaction), len(self.__transactions))
        self.__transactions.append(copy(transaction))
        return Ok(entity)

    async def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> Result[Sequence[Entity[Transaction]], ClientDoesNotExistError]:
        if props["id"] not in self.__clients:
            return Err(ClientDoesNotExistError())
        if "starting_from" not in props:
            props["starting_from"] = datetime.now(timezone.utc)
        if "amount" not in props:
            props["amount"] = len(self.__transactions)
        return Ok(
            tuple(
                map(
                    lambda transaction: Entity(
                        transaction, self.__transactions.index(transaction)
                    ),
                    sorted(
                        filter(
                            lambda transaction: transaction.client_id == props["id"]
                            and transaction.created_at <= props["starting_from"],
                            self.__transactions,
                        ),
                        key=lambda transaction: transaction.created_at,
                        reverse=True,
                    )[0 : props["amount"]],
                )
            )
        )
