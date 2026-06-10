"""
Puertos de repositorios del dominio.

Este módulo define contratos de acceso a datos mediante `Protocol`.
Las implementaciones concretas pueden consultar una base de datos,
servicios externos o datos simulados, sin acoplar la capa de dominio
a una tecnología específica.
"""

from decimal import Decimal
from typing import Protocol

from app.domain.entities import Product


class CatalogRepository(Protocol):
    """
    Contrato para consultar productos del catálogo.

    Define las operaciones necesarias para buscar productos disponibles
    según texto libre, categoría, presupuesto y disponibilidad de inventario.
    """

    async def search(
        self,
        query: str,
        category: str | None = None,
        max_price: Decimal | None = None,
        in_stock_only: bool = True,
        limit: int = 10,
    ) -> list[Product]:
        """
        Busca productos en el catálogo.

        Args:
            query: Texto de búsqueda ingresado por el cliente.
            category: Categoría opcional para filtrar los productos.
            max_price: Precio máximo permitido para los resultados.
            in_stock_only: Indica si solo deben retornarse productos con stock.
            limit: Cantidad máxima de productos a retornar.

        Returns:
            list[Product]: Lista de productos que cumplen los criterios de búsqueda.
        """
        ...
