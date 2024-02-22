from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import TypedDict

import jsonschema
from jsonschema.exceptions import ValidationError
from returns import Err, Ok
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..adapters.errors import ClientDoesNotExistError, NoLimitError
from ..core.entities.client import Client
from ..core.entities.transaction import Transaction, TransactionKind
from .adapters.in_memory_client_repository import InMemoryClientRepository
from .adapters.in_memory_transaction_repository import InMemoryTransactionRepository

clients = dict[int, int]()
transactions = list[Transaction]()
client_repository = InMemoryClientRepository(clients, transactions)
transactions_repository = InMemoryTransactionRepository(clients, transactions)


@asynccontextmanager
async def lifespan(_: Starlette):
    await client_repository.create(Client(100_000, 0))
    await client_repository.create(Client(80_000, 0))
    await client_repository.create(Client(100_000_000, 0))
    await client_repository.create(Client(10_000_000, 0))
    await client_repository.create(Client(500_000, 0))
    yield


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

    result = await transactions_repository.create(
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
    result = await asyncio.gather(
        client_repository.get(id),
        transactions_repository.get_by_client_id(id=id, amount=10),
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
    debug=True,
    routes=[
        Route("/clientes/{id:int}/transacoes", transactions_handler, methods=["POST"]),
        Route("/clientes/{id:int}/extrato", bank_statement_handler, methods=["GET"]),
    ],
    lifespan=lifespan,
)
