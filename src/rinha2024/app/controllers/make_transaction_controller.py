from datetime import datetime, timezone
from json import JSONDecodeError
from typing import TypedDict

import jsonschema
from jsonschema import ValidationError
from returns import Err, Ok
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ...adapters.errors import ClientDoesNotExistError, NoLimitError
from ...adapters.transaction_repository import TransactionRepository
from ...core.entities.transaction import Transaction, TransactionKind


class Payload(TypedDict):
    valor: int
    tipo: TransactionKind
    descricao: str


class MakeTransactionController:
    async def handle(self, request: Request) -> Response:
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
            payload: Payload = await request.json()
            jsonschema.validate(payload, schema)
        except (JSONDecodeError, ValidationError):
            return JSONResponse({"error": "bad request"}, status_code=422)

        transaction_repository: TransactionRepository = (
            request.state.transaction_repository
        )

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
                        return JSONResponse(
                            {"error": "client not found"}, status_code=404
                        )
                    case NoLimitError():
                        return JSONResponse({"error": "no limit"}, status_code=422)
