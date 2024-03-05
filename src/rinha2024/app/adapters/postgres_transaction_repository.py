from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from datetime import datetime, timezone
from types import TracebackType
from typing import AsyncContextManager, Optional, Unpack

from asyncpg import Pool, Record
from asyncpg.cursor import CursorFactory
from asyncpg.pool import PoolConnectionProxy
from asyncpg.transaction import Transaction as AsyncpgTransaction
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
            async with connection.transaction():
                client_prepare = await connection.prepare(
                    """SELECT id, limit_value AS limit, balance FROM Client WHERE id = $1\n"""
                    """FOR UPDATE\n""",
                )
                client_result = await client_prepare.fetchrow(transaction.client_id)
                if not client_result:
                    return Err(ClientDoesNotExistError())

                client_id = client_result["id"]
                limit = client_result["limit"]
                balance = client_result["balance"]
                if transaction.kind == "c":
                    new_balance = balance + transaction.value
                else:
                    new_balance = balance - transaction.value
                    if new_balance < limit * -1:
                        return Err(NoLimitError())
                await connection.execute(
                    """INSERT INTO Transaction (client_id, value, kind, description, created_at)\n"""
                    """VALUES ($1, $2, $3, $4, $5)\n""",
                    transaction.client_id,
                    transaction.value,
                    transaction.kind,
                    transaction.description,
                    transaction.created_at,
                )
                await connection.execute(
                    """UPDATE Client\n"""
                    """SET balance = $2\n"""
                    """WHERE id = $1\n""",
                    transaction.client_id,
                    new_balance,
                )
            return Ok(Entity(Client(limit=limit, balance=new_balance), client_id))

    def get_by_client_id(
        self, **props: Unpack[GetByClientIdProps]
    ) -> AsyncContextManager[
        Result[AsyncIterable[Entity[Transaction]], ClientDoesNotExistError]
    ]:
        if "starting_from" not in props:
            props["starting_from"] = datetime.now(timezone.utc)
        if "amount" not in props:
            props["amount"] = 10
        return GetTransactionsContextManager(self.__pool, **props)


class GetTransactionsContextManager:
    __transaction: AsyncpgTransaction
    __connection: PoolConnectionProxy[Record]

    def __init__(
        self, pool: Pool[Record], id: int, starting_from: datetime, amount: int
    ):
        self.__pool = pool
        self.__id = id
        self.__starting_from = starting_from
        self.__amount = amount

    async def __aenter__(
        self,
    ) -> Result[AsyncIterable[Entity[Transaction]], ClientDoesNotExistError]:
        self.__connection = await self.__pool.acquire()
        self.__transaction = self.__connection.transaction()
        await self.__transaction.start()
        exists_prepare = await self.__connection.prepare(
            """SELECT EXISTS(SELECT 1 FROM Client WHERE id = $1)\n"""
        )
        cursor_prepare = await self.__connection.prepare(
            """SELECT id, client_id, kind, description, value, created_at\n"""
            """FROM Transaction\n"""
            """WHERE client_id = $1 AND created_at <= $2\n"""
            """ORDER BY created_at DESC\n"""
            """LIMIT $3\n""",
        )
        exists: bool = await exists_prepare.fetchval(self.__id)
        if not exists:
            return Err(ClientDoesNotExistError())

        cursor = cursor_prepare.cursor(
            self.__id,
            self.__starting_from,
            self.__amount,
        )
        return Ok(GetTransactions(cursor))

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        if exc_type and exc_value and traceback:
            await self.__transaction.rollback()
            exc_value.__traceback__ = traceback
            raise exc_value
        else:
            await self.__transaction.commit()

        await self.__pool.release(self.__connection)


class GetTransactions:
    def __init__(self, cursor: CursorFactory[Record]):
        self.__cursor = aiter(cursor)

    def __aiter__(self):
        return self

    async def __anext__(self):
        record = await anext(self.__cursor)
        return Entity(
            Transaction(
                client_id=record["client_id"],
                kind=record["kind"],
                description=record["description"],
                value=record["value"],
                created_at=record["created_at"],
            ),
            id=record["id"],
        )
