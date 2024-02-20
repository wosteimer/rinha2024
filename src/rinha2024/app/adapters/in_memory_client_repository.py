from collections.abc import Sequence

from returns import Err, Ok, Result

from ...adapters.client_repository import ClientRepository
from ...adapters.errors import ClientAlreadyExists, ClientDoesNotExistError
from ...core.entities.client import Client
from ...core.entities.transaction import Transaction, TransactionKind


class InMemoryClientRepository(ClientRepository):
    def __init__(
        self, clients: dict[int, int], transactions: list[Transaction]
    ) -> None:
        self.__clients = clients
        self.__transactions = transactions

    async def create(self, id: int, limit: int) -> Result[None, ClientAlreadyExists]:
        if await self.exists(id):
            return Err(ClientAlreadyExists())

        self.__clients[id] = limit
        return Ok(None)

    async def get(self, id: int) -> Result[Client, ClientDoesNotExistError]:
        if not await self.exists(id):
            return Err(ClientDoesNotExistError())
        return Ok(Client(id, self.__clients[id], await self.__get_balance(id)))

    async def get_all(self) -> Sequence[Client]:
        result = list[Client]()
        for id, limit in self.__clients.items():
            result.append(Client(id, limit, await self.__get_balance(id)))
        return tuple(result)

    async def __get_balance(self, id: int) -> int:
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

    async def exists(self, id: int) -> bool:
        return id in self.__clients
