from collections.abc import Sequence
from copy import copy
from datetime import datetime, timezone
from operator import add, sub
from typing import Unpack

from returns import Err, Ok
from returns.result import Result

from ...adapters.errors import ClientDoesNotExistError, NoLimitError
from ...adapters.transaction_repository import GetByClientIdProps, TransactionRepository
from ...core.entities.client import Client
from ...core.entities.entity import Entity
from ...core.entities.transaction import Transaction, TransactionKind

OPERATION_MAP = {TransactionKind.CREDIT: add, TransactionKind.DEBIT: sub}


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(
        self, clients: dict[int, int], transactions: list[Transaction]
    ) -> None:
        self.__clients = clients
        self.__transactions = transactions

    async def create(
        self, transaction: Transaction
    ) -> Result[Entity[Client], ClientDoesNotExistError | NoLimitError]:
        if transaction.client_id not in self.__clients:
            return Err(ClientDoesNotExistError())

        operation = OPERATION_MAP[transaction.kind]
        balance = operation(
            self.__get_balance(transaction.client_id), transaction.value
        )

        if balance < self.__clients[transaction.client_id] * -1:
            return Err(NoLimitError())

        self.__transactions.append(copy(transaction))
        return Ok(
            Entity(
                Client(self.__clients[transaction.client_id], balance),
                transaction.client_id,
            )
        )

    def __get_balance(self, id: int) -> int:
        return sum(
            map(
                lambda transaction: (
                    transaction.value
                    if transaction.kind == TransactionKind.CREDIT
                    else transaction.value * -1
                ),
                filter(
                    lambda transaction: transaction.client_id == id, self.__transactions
                ),
            )
        )

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
