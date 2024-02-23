from __future__ import annotations

from collections.abc import Sequence

from asyncpg import Pool, Record
from returns import Err, Ok, Result

from ...adapters.client_repository import ClientRepository
from ...adapters.errors import ClientDoesNotExistError
from ...core.entities.client import Client
from ...core.entities.entity import Entity


class PostgresClientRepository(ClientRepository):
    def __init__(self, pool: Pool[Record]) -> None:
        self.__pool = pool

    async def create(self, client: Client) -> Entity[Client]:
        async with self.__pool.acquire() as connection:
            id: int = await connection.fetchval(
                """INSERT INTO Client(limit_value, balance)\n"""
                """VALUES($1, 0);\n"""
                """RETURNING id""",
                client.limit,
            )
        return Entity(Client(client.limit, 0), id)

    async def get(self, id: int) -> Result[Entity[Client], ClientDoesNotExistError]:
        async with self.__pool.acquire() as connection:
            result = await connection.fetchrow(
                "SELECT id, limit_value AS limit, balance FROM Client WHERE id = $1;\n",
                id,
            )

            if not result:
                return Err(ClientDoesNotExistError())
            result_to_dict = dict(result)
            client_id = result_to_dict.pop("id")
            return Ok(Entity(Client(**result_to_dict), client_id))

    async def get_all(self) -> Sequence[Entity[Client]]:
        async with self.__pool.acquire() as connection:
            result = await connection.fetch(
                "SELECT id, limit_value AS limit, balance FROM Client;\n",
            )

            return tuple(
                map(
                    lambda row: Entity(Client(row["limit"], row["balance"]), row["id"]),
                    result,
                )
            )

    async def exists(self, id: int) -> bool:
        async with self.__pool.acquire() as connection:
            exists: bool = await connection.fetchval(
                """SELECT EXISTS(SELECT 1 FROM Client WHERE id = $1)""", id
            )

        return exists
