from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from starlette.applications import Starlette
from starlette.config import Config
from starlette.routing import Route

from .adapters.postgres_client_repository import PostgresClientRepository
from .adapters.postgres_transaction_repository import PostgresTransactionRepository
from .controllers.get_bank_statement_controller import get_bank_statement_controller
from .controllers.make_transaction_controller import make_transaction_controller

ENV_PATH = Path(".env")
config = Config(ENV_PATH if ENV_PATH.exists() else None)

DEBUG = config("DEBUG", cast=bool, default=False)
POSTGRES_HOST = config("POSTGRES_HOST")
POSTGRES_PORT = config("POSTGRES_PORT", cast=int)
POSTGRES_DB = config("POSTGRES_DB")
POSTGRES_USER = config("POSTGRES_USER")
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD")


@asynccontextmanager
async def lifespan(_: Starlette):
    async with asyncpg.create_pool(
        max_size=25,
        max_inactive_connection_lifetime=0,
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


app = Starlette(
    debug=DEBUG,
    routes=[
        Route(
            "/clientes/{id:int}/transacoes",
            make_transaction_controller,
            methods=["POST"],
        ),
        Route(
            "/clientes/{id:int}/extrato",
            get_bank_statement_controller,
            methods=["GET"],
        ),
    ],
    lifespan=lifespan,
)
