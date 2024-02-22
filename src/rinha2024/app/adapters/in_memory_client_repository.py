from collections.abc import Sequence
from itertools import count

from returns import Err, Ok, Result

from ...adapters.client_repository import ClientRepository
from ...adapters.errors import ClientDoesNotExistError
from ...core.entities.client import Client
from ...core.entities.entity import Entity
from ...core.entities.transaction import Transaction, TransactionKind


class InMemoryClientRepository(ClientRepository):
    def __init__(
        self, clients: dict[int, int], transactions: list[Transaction]
    ) -> None:
        self.__next_id = count()
        next(self.__next_id)
        self.__clients = clients
        self.__transactions = transactions

    async def create(self, client: Client) -> Entity[Client]:
        id = next(self.__next_id)

        self.__clients[id] = client.limit
        return Entity(Client(client.limit, self.__get_balance(id)), id)

    async def get(self, id: int) -> Result[Entity[Client], ClientDoesNotExistError]:
        if not await self.exists(id):
            return Err(ClientDoesNotExistError())
        return Ok(Entity(Client(self.__clients[id], self.__get_balance(id)), id))

    async def get_all(self) -> Sequence[Entity[Client]]:
        result = list[Entity[Client]]()
        for id, limit in self.__clients.items():
            result.append(Entity(Client(limit, self.__get_balance(id)), id))
        return tuple(result)

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

    async def exists(self, id: int) -> bool:
        return id in self.__clients
