"""
DTOs utilizados por las operaciones del catálogo.

Este módulo define los modelos de entrada y salida para buscar y comparar
productos. Los DTOs permiten validar los datos intercambiados entre el agente,
las herramientas de aplicación y los adaptadores de infraestructura.
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CatalogSearchInputDTO(BaseModel):
    """
    Criterios usados para buscar productos en el catálogo.

    Attributes:
        query: Necesidad, uso o característica solicitada por el cliente.
        category: Categoría opcional usada para filtrar productos.
        max_price: Presupuesto máximo en pesos colombianos.
        in_stock_only: Indica si deben excluirse productos sin inventario.
        limit: Cantidad máxima de resultados a retornar.
    """

    query: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "Necesidad principal del cliente, por ejemplo: "
            "'diseño gráfico', 'edición de video' o 'gaming'."
        ),
    )
    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
        description=(
            "Categoría opcional del producto en singular y mayúsculas. "
            "Ejemplos: LAPTOP, CELULAR, TELEVISION o ACCESSORY."
        ),
    )
    max_price: Decimal | None = Field(
        default=None,
        gt=Decimal("0"),
        description="Presupuesto máximo del cliente en pesos colombianos.",
    )
    in_stock_only: bool = Field(
        default=True,
        description="Indica si solamente deben buscarse productos disponibles.",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Cantidad máxima de productos que se deben retornar.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        """
        Normaliza el texto de búsqueda.

        Args:
            value: Texto original enviado para buscar productos.

        Returns:
            str: Texto de búsqueda sin espacios al inicio ni al final.
        """
        return value.strip()

    @field_validator("category")
    @classmethod
    def normalize_category(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normaliza la categoría del producto.

        Args:
            value: Categoría recibida en la solicitud.

        Returns:
            str | None: Categoría en mayúsculas, o `None` si no fue informada.
        """
        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value.upper()


class ProductResultDTO(BaseModel):
    """
    Producto retornado por una operación de catálogo.

    Representa una versión serializable del producto para que pueda ser usada
    por herramientas, servicios de aplicación o respuestas del agente.

    Attributes:
        sku: Código único del producto.
        name: Nombre comercial del producto.
        category: Categoría a la que pertenece el producto.
        description: Descripción comercial del producto.
        price: Precio actual en pesos colombianos.
        stock: Cantidad disponible en inventario.
        available: Indica si el producto tiene inventario disponible.
        specs: Especificaciones técnicas del producto.
    """

    sku: str = Field(description="Código único del producto.")
    name: str = Field(description="Nombre comercial del producto.")
    category: str = Field(description="Categoría a la que pertenece el producto.")
    description: str = Field(description="Descripción comercial del producto.")
    price: Decimal = Field(description="Precio actual en pesos colombianos.")
    stock: int = Field(description="Cantidad disponible en inventario.")
    available: bool = Field(description="Indica si el producto tiene inventario disponible.")
    specs: dict[str, Any] = Field(
        default_factory=dict,
        description="Especificaciones técnicas del producto.",
    )


class CatalogSearchResultDTO(BaseModel):
    """
    Resultado normalizado de una búsqueda en el catálogo.

    Attributes:
        found: Indica si se encontraron productos.
        count: Cantidad de productos encontrados.
        products: Lista de productos que cumplen los criterios de búsqueda.
    """

    found: bool = Field(description="Indica si se encontraron productos.")
    count: int = Field(
        ge=0,
        description="Cantidad de productos encontrados.",
    )
    products: list[ProductResultDTO] = Field(
        default_factory=list,
        description="Lista de productos que cumplen los criterios de búsqueda.",
    )


class CompareProductsInputDTO(BaseModel):
    """
    Entrada requerida para comparar productos específicos.

    Attributes:
        skus: Lista de códigos SKU que se desean comparar.
    """

    skus: list[str] = Field(
        min_length=2,
        max_length=4,
        description=(
            "Lista de códigos SKU de los productos que se desean comparar. "
            "Debe contener entre dos y cuatro códigos diferentes."
        ),
    )

    @field_validator("skus")
    @classmethod
    def normalize_skus(
        cls,
        values: list[str],
    ) -> list[str]:
        """
        Normaliza y valida los códigos SKU recibidos.

        Args:
            values: Lista original de códigos SKU.

        Returns:
            list[str]: Lista de SKU normalizados en mayúsculas.

        Raises:
            ValueError: Si algún SKU está vacío o si existen códigos repetidos.
        """
        normalized_skus = [value.strip().upper() for value in values]

        if any(not sku for sku in normalized_skus):
            raise ValueError("Los códigos SKU no pueden estar vacíos")

        if len(set(normalized_skus)) != len(normalized_skus):
            raise ValueError("Los códigos SKU no pueden estar repetidos")

        return normalized_skus


class ProductComparisonResultDTO(BaseModel):
    """
    Resultado normalizado de una comparación de productos.

    Attributes:
        found: Indica si fue posible encontrar al menos un producto.
        requested_skus: SKU solicitados originalmente.
        missing_skus: SKU solicitados que no existen en el catálogo.
        products: Productos encontrados con información actualizada.
    """

    found: bool = Field(description="Indica si fue posible encontrar al menos un producto.")
    requested_skus: list[str] = Field(description="SKU solicitados originalmente.")
    missing_skus: list[str] = Field(
        default_factory=list,
        description="SKU solicitados que no existen en el catálogo.",
    )
    products: list[ProductResultDTO] = Field(
        default_factory=list,
        description="Productos encontrados con información actualizada.",
    )
