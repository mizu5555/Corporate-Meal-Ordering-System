from dataclasses import dataclass


@dataclass(frozen=True)
class Vendor:
    id: int
    name: str
    status: str
