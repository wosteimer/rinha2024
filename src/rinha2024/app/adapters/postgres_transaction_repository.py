from __future__ import annotations

from collections.abc import Sequence
from dataclasses import astuple
from datetime import datetime, timezone
from typing import Unpack, cast

from asyncpg import Pool, PostgresError, Record
from returns import Err, Ok, Result

from ...adapters.errors import ClientDoesNotExistError, NoLimitError
from ...adapters.transaction_repository import GetByClientIdProps, TransactionRepository
from ...core.entities.client import Client
from ...core.entities.entity import Entity
from ...core.entities.transaction import Transaction


class PostgresTransactionRepository(TransactionRepository):
    def __init__(self, pool: Pool[Record]):
        self.__pool = pool

    async def create(
        self, transaction: Transaction
    ) -> Result[Entity[Client], ClientDoesNotExistError | NoLimitError]:
        async with self.__pool.acquire() as connection:
            exists: bool = await connection.fetchval(
                """SELECT EXISTS(SELECT 1 FROM Client WHERE id = $1)""",
                transaction.client_id,
            )
            if not exists:
                return Err(ClientDoesNotExistError())
            try:
                await connection.execute(
                    """INSERT INTO Transaction (client_id, value, kind, description,  created_at)\n"""
                    """VALUES ($1, $2, $3, $4, $5)""",
                    *astuple(transaction),
                )
                result = await connection.fetchrow(
                    "SELECT id, limit_value AS limit, balance FROM Client WHERE id = $1;\n",
                    transaction.client_id,
                )
                result = cast(Record, result)
                return Ok(
                    Entity(Client(result["limit"], result["balance"]), result["id"])
                )
            except PostgresError as error:
                if "No limit" in str(error):
                    return Err(NoLimitError())

                raise error

    async def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> Result[Sequence[Entity[Transaction]], ClientDoesNotExistError]:
        if "starting_from" not in props:
            props["starting_from"] = datetime.now(timezone.utc)
        if "amount" not in props:
            props["amount"] = 10
        async with self.__pool.acquire() as connection:

            exists: bool = await connection.fetchval(
                """SELECT EXISTS(SELECT 1 FROM Client WHERE id = $1)""", props["id"]
            )
            if not exists:
                return Err(ClientDoesNotExistError())
            result = await connection.fetch(
                """SELECT id, client_id, kind, description, value, created_at\n"""
                """FROM Transaction\n"""
                """WHERE client_id = $1 AND created_at <= $2\n"""
                """ORDER BY created_at DESC\n"""
                """LIMIT $3\n""",
                props["id"],
                props["starting_from"],
                props["amount"],
            )

            return Ok(
                tuple(
                    map(
                        lambda row: PostgresTransactionRepository.__to_entity(row),
                        result,
                    )
                )
            )

    @staticmethod
    def __to_entity(row: Record) -> Entity[Transaction]:
        row_to_dict = dict(row)
        id = row_to_dict.pop("id")
        return Entity(Transaction(**row_to_dict), id=id)
