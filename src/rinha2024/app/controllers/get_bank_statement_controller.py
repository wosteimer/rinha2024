import asyncio
from datetime import datetime, timezone

from returns import Ok
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...adapters.client_repository import ClientRepository
from ...adapters.transaction_repository import TransactionRepository


class GetBankStatementController:
    async def handle(self, request: Request):
        id: int = request.path_params["id"]
        transaction_repository: TransactionRepository = (
            request.state.transaction_repository
        )
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
