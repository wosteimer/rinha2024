from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class TransactionKind(StrEnum):
    CREDIT = "c"
    DEBIT = "d"


@dataclass(slots=True, frozen=True)
class Transaction:
    client_id: int
    value: int
    kind: TransactionKind
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
