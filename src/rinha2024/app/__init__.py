from __future__ import annotations

from contextlib import asynccontextmanager

import asyncpg
from starlette.applications import Starlette
from starlette.config import Config
from starlette.routing import Route

from .adapters.postgres_client_repository import PostgresClientRepository
from .adapters.postgres_transaction_repository import PostgresTransactionRepository
from .controllers.get_bank_statement_controller import GetBankStatementController
from .controllers.make_transaction_controller import MakeTransactionController

config = Config(".env")
DEBUG = config("DEBUG", cast=bool, default=False)
POSTGRES_HOST = config("POSTGRES_HOST")
POSTGRES_PORT = config("POSTGRES_PORT", cast=int)
POSTGRES_DB = config("POSTGRES_DB")
POSTGRES_USER = config("POSTGRES_USER")
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD")


@asynccontextmanager
async def lifespan(_: Starlette):
    async with asyncpg.create_pool(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    ) as pool:
        client_repository = PostgresClientRepository(pool)
        transaction_repository = PostgresTransactionRepository(pool)
        yield {
            "client_repository": client_repository,
            "transaction_repository": transaction_repository,
        }


make_transaction_controller = MakeTransactionController()
get_bank_statement_controller = GetBankStatementController()

app = Starlette(
    debug=DEBUG,
    routes=[
        Route(
            "/clientes/{id:int}/transacoes",
            make_transaction_controller.handle,
            methods=["POST"],
        ),
        Route(
            "/clientes/{id:int}/extrato",
            get_bank_statement_controller.handle,
            methods=["GET"],
        ),
    ],
    lifespan=lifespan,
)
