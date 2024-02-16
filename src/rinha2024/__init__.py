from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from json import JSONDecodeError
from typing import TypedDict

import jsonschema
from jsonschema.exceptions import ValidationError
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


class TransactionKind(StrEnum):
    CREDIT = "c"
    DEBIT = "d"


@dataclass(slots=True, frozen=True)
class Transaction:
    value: int
    kind: TransactionKind
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True, frozen=True)
class Client:
    id: int
    limit: int
    transactions: tuple[Transaction] = field(default_factory=tuple)

    @property
    def balance(self) -> int:
        return sum(
            map(
                lambda transaction: (
                    transaction.value
                    if transaction.kind == TransactionKind.CREDIT
                    else transaction.value * -1
                ),
                self.transactions,
            )
        )

    def apply_transaction(self, transaction: Transaction) -> Client:
        return replace(self, transactions=(*self.transactions, transaction))


REPOSITORY = dict[int, Client]()
REPOSITORY[1] = Client(1, 100_000)
REPOSITORY[2] = Client(2, 80_000)
REPOSITORY[3] = Client(3, 100_000_000)
REPOSITORY[4] = Client(4, 10_000_000)
REPOSITORY[5] = Client(5, 500_000)


class TransactionsPayload(TypedDict):
    valor: int
    tipo: TransactionKind
    descricao: str


async def transactions(request: Request):
    id: int = request.path_params["id"]
    if id not in REPOSITORY:
        return JSONResponse({"error": "client not found"}, status_code=404)
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
    except JSONDecodeError:
        return JSONResponse({"error": "bad request"}, status_code=400)
    except ValidationError:
        return JSONResponse({"error": "bad request"}, status_code=400)

    client = REPOSITORY[id]
    if (
        payload["tipo"] == TransactionKind.DEBIT
        and client.balance - payload["valor"] < client.limit * -1
    ):
        return JSONResponse({"error": "no limit"}, status_code=422)

    new_client = client.apply_transaction(
        Transaction(payload["valor"], payload["tipo"], payload["descricao"])
    )
    REPOSITORY[id] = new_client
    return JSONResponse({"limite": new_client.limit, "saldo": new_client.balance})


async def bank_statement(request: Request):
    id: int = request.path_params["id"]
    if id not in REPOSITORY:
        return JSONResponse({"error": "client not found"}, status_code=404)
    client = REPOSITORY[id]
    result = {
        "saldo": {
            "total": client.balance,
            "data_extrato": str(datetime.now(timezone.utc)),
            "limite": client.limit,
        },
        "ultimas_transacoes": [
            {
                "valor": transaction.value,
                "tipo": transaction.kind,
                "descricao": transaction.description,
                "realizada_em": str(transaction.created_at),
            }
            for transaction in tuple(reversed(client.transactions))[0:10]
        ],
    }
    return JSONResponse(result)


app = Starlette(
    debug=True,
    routes=[
        Route("/clientes/{id:int}/transacoes", transactions, methods=["POST"]),
        Route("/clientes/{id:int}/extrato", bank_statement, methods=["GET"]),
    ],
)
