from datetime import datetime, timezone
from typing import Any

import orjson
from orjson import JSONDecodeError
from returns import Err, Ok
from starlette.requests import Request
from starlette.responses import Response

from ...adapters.errors import ClientDoesNotExistError, NoLimitError
from ...adapters.transaction_repository import TransactionRepository
from ...core.entities.transaction import Transaction
from .orjson_response import OrjsonResponse


async def make_transaction_controller(request: Request) -> Response:
    id: int = request.path_params["id"]
    try:
        payload = orjson.loads(await request.body())
        if not __validate_payload(payload):
            return Response(status_code=422)
    except JSONDecodeError:
        return Response(status_code=422)

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
            return OrjsonResponse(
                {"limite": client.props.limit, "saldo": client.props.balance}
            )
        case Err(error):
            match error:
                case ClientDoesNotExistError():
                    return Response(status_code=404)
                case NoLimitError():
                    return Response(status_code=422)


def __validate_payload(payload: dict[str, Any]) -> bool:
    valor = payload.get("valor")
    tipo = payload.get("tipo")
    descricao = payload.get("descricao")

    return (
        (isinstance(valor, int) and valor > 0)
        and (isinstance(tipo, str) and (tipo == "c" or tipo == "d"))
        and (isinstance(descricao, str) and (1 <= len(descricao) <= 10))
    )
