from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import TypedDict

import asyncpg
import jsonschema
from jsonschema.exceptions import ValidationError
from returns import Err, Ok
from starlette.applications import Starlette
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..adapters.client_repository import ClientRepository
from ..adapters.errors import ClientDoesNotExistError, NoLimitError
from ..adapters.transaction_repository import TransactionRepository
from ..app.adapters.postgres_client_repository import PostgresClientRepository
from ..app.adapters.postgres_transaction_repository import PostgresTransactionRepository
from ..core.entities.transaction import Transaction, TransactionKind

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


class TransactionsPayload(TypedDict):
    valor: int
    tipo: TransactionKind
    descricao: str


class TransactionsResponse(TypedDict):
    limite: int
    saldo: int


async def transactions_handler(request: Request):
    id: int = request.path_params["id"]
    try:
        schema = {
            "type": "object",
            "properties": {
                "valor": {"type": "integer", "minimum": 0},
                "tipo": {"type": "string", "enum": ["c", "d"]},
                "descricao": {"type": "string", "minLength": 1, "maxLength": 10},
            },
            "required": ["valor", "tipo", "descricao"],
        }
        payload: TransactionsPayload = await request.json()
        jsonschema.validate(payload, schema)
    except (JSONDecodeError, ValidationError):
        return JSONResponse({"error": "bad request"}, status_code=400)

    transaction_repository: TransactionRepository = request.state.transaction_repository

    result = await transaction_repository.create(
        Transaction(
            id,
            payload["valor"],
            payload["tipo"],
            payload["descricao"],
            datetime.now(timezone.utc),
        )
    )
    match result:
        case Ok(client):
            return JSONResponse(
                {"limite": client.props.limit, "saldo": client.props.balance}
            )
        case Err(error):
            match error:
                case ClientDoesNotExistError():
                    return JSONResponse({"error": "client not found"}, status_code=404)
                case NoLimitError():
                    return JSONResponse({"error": "no limit"}, status_code=422)


async def bank_statement_handler(request: Request):
    id: int = request.path_params["id"]
    transaction_repository: TransactionRepository = request.state.transaction_repository
    client_repository: ClientRepository = request.state.client_repository
    result = await asyncio.gather(
        client_repository.get(id),
        transaction_repository.get_by_client_id(id=id, amount=10),
    )
    match result:
        case Ok(client), Ok(transactions):
            json_response = {
                "saldo": {
                    "total": client.props.balance,
                    "data_extrato": str(datetime.now(timezone.utc)),
                    "limite": client.props.limit,
                },
                "ultimas_transacoes": [
                    {
                        "valor": transaction.props.value,
                        "tipo": transaction.props.kind,
                        "descricao": transaction.props.description,
                        "realizada_em": str(transaction.props.created_at),
                    }
                    for transaction in transactions
                ],
            }
            return JSONResponse(json_response)
        case _:
            return JSONResponse({"error": "client not found"}, status_code=404)


app = Starlette(
    debug=DEBUG,
    routes=[
        Route("/clientes/{id:int}/transacoes", transactions_handler, methods=["POST"]),
        Route("/clientes/{id:int}/extrato", bank_statement_handler, methods=["GET"]),
    ],
    lifespan=lifespan,
)
