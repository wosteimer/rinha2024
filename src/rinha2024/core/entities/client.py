from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Client:
    id: int
    limit: int
    balance: int
