from dataclasses import dataclass


@dataclass(slots=True)
class Customer:
    identification: str
    full_name: str
    phone: str
    email: str
    kind: str = "NEW"
