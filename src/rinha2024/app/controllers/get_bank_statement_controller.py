from datetime import datetime, timezone

from returns import Err, Ok
from starlette.requests import Request
from starlette.responses import Response

from ...adapters.client_repository import ClientRepository
from ...adapters.transaction_repository import TransactionRepository
from .orjson_response import OrjsonResponse


async def get_bank_statement_controller(request: Request):
    id: int = request.path_params["id"]
    transaction_repository: TransactionRepository = request.state.transaction_repository
    client_repository: ClientRepository = request.state.client_repository
    async with transaction_repository.get_by_client_id(
        id=id, amount=10
    ) as transaction_result:
        match transaction_result:
            case Ok(transactions):
                client = (await client_repository.get(id)).unwrap()
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
                        async for transaction in transactions
                    ],
                }
                return OrjsonResponse(json_response)
            case Err():
                return Response(status_code=404)
