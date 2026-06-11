"""
Entidades y reglas de dominio relacionadas con garantías.

Este módulo representa una garantía independientemente de PostgreSQL,
SQLAlchemy, FastAPI o el proveedor de inteligencia artificial.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Warranty:
    """
    Garantía asociada a un producto incluido en un pedido.

    Attributes:
        id: Identificador único de la garantía.
        product_sku: SKU del producto cubierto.
        order_id: Pedido mediante el cual fue comprado el producto.
        active: Indica si la garantía fue habilitada administrativamente.
        starts_on: Fecha desde la cual comienza la cobertura.
        expires_on: Último día de cobertura.
    """

    id: str
    product_sku: str
    order_id: str
    active: bool
    starts_on: date
    expires_on: date

    def is_valid_on(
        self,
        reference_date: date,
    ) -> bool:
        """
        Indica si la garantía está vigente en una fecha determinada.

        La garantía solo se considera vigente cuando está activa y la fecha
        consultada se encuentra dentro del periodo de cobertura, incluyendo
        las fechas de inicio y vencimiento.

        Args:
            reference_date: Fecha para la cual se valida la cobertura.

        Returns:
            True si la garantía está vigente; de lo contrario, False.
        """

        return self.active and self.starts_on <= reference_date <= self.expires_on
