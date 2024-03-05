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
            create_client_prepare = await connection.prepare(
                """INSERT INTO Client(limit_value, balance)\n"""
                """VALUES($1, 0);\n"""
                """RETURNING id""",
            )
            id: int = await create_client_prepare.fetchval(client.limit)
        return Entity(Client(client.limit, 0), id)

    async def get(self, id: int) -> Result[Entity[Client], ClientDoesNotExistError]:
        async with self.__pool.acquire() as connection:
            get_client_prepare = await connection.prepare(
                "SELECT id, limit_value AS limit, balance FROM Client WHERE id = $1;\n",
            )
            record = await get_client_prepare.fetchrow(id)

            if not record:
                return Err(ClientDoesNotExistError())
            return Ok(Entity(Client(record["limit"], record["balance"]), record["id"]))

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
