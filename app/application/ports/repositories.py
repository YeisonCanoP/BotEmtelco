from typing import Protocol

from app.domain.entities import Customer, Order, Product, Warranty


class CatalogRepository(Protocol):
    async def search(self, query: str, limit: int = 10) -> list[Product]: ...


class OrderRepository(Protocol):
    async def get(self, order_id: str) -> Order | None: ...


class WarrantyRepository(Protocol):
    async def get_by_order(self, order_id: str) -> Warranty | None: ...


class CustomerRepository(Protocol):
    async def get(self, identification: str) -> Customer | None: ...

    async def add(self, customer: Customer) -> None: ...
