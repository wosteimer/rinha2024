from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Client:
    limit: int
    balance: int
