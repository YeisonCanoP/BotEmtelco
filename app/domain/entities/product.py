"""
Entidad de dominio que representa un producto del catálogo.

Este módulo no depende de SQLAlchemy, FastAPI ni OpenAI. Su responsabilidad
es representar un producto dentro de la lógica de negocio.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class Product:
    """
    Producto disponible en el catálogo de la tienda.

    Attributes:
        sku: Identificador único del producto.
        name: Nombre comercial.
        category: Categoría normalizada, por ejemplo LAPTOP.
        description: Descripción comercial del producto.
        price: Precio actual en pesos colombianos.
        stock: Cantidad disponible.
        specs: Especificaciones técnicas variables según la categoría.
    """

    sku: str
    name: str
    category: str
    description: str
    price: Decimal
    stock: int
    specs: dict[str, Any] = field(default_factory=dict)

    @property
    def is_available(self) -> bool:
        """Indica si el producto tiene unidades disponibles."""
        return self.stock > 0
