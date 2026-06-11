"""
Puertos de repositorios utilizados por la capa de aplicación.

Este módulo define contratos de acceso a datos mediante `Protocol`.
Los contratos describen las operaciones que los casos de uso, servicios del
agente y herramientas conversacionales necesitan para consultar información del
negocio sin depender de una tecnología concreta.

Las implementaciones pueden usar distintas fuentes de datos, por ejemplo:

- PostgreSQL o cualquier base de datos relacional.
- Datos simulados en memoria.
- Servicios externos.
- Archivos locales.
- APIs internas.
"""

from decimal import Decimal
from typing import Protocol

from app.domain.entities import Customer, Order, Product


class CatalogRepository(Protocol):
    """
    Contrato para consultar productos del catálogo.

    Este repositorio expone las operaciones necesarias para que el agente pueda
    resolver solicitudes de venta consultiva, búsqueda de productos, comparación
    de alternativas y recomendaciones según la necesidad del cliente.

    La implementación concreta es responsable de consultar la fuente de datos
    correspondiente y aplicar filtros como categoría, precio máximo,
    disponibilidad de inventario y límite de resultados.
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
        Busca productos en el catálogo según criterios conversacionales.

        Este métod se utiliza cuando el usuario solicita productos por nombre,
        categoría, necesidad, presupuesto o características esperadas. También
        permite que el agente consulte datos reales antes de recomendar, para
        evitar inventar precios, disponibilidad o referencias.

        Args:
            query: Texto de búsqueda ingresado por el usuario o construido por
                el agente a partir de la intención detectada.
            category: Categoría opcional para restringir los resultados.
            max_price: Precio máximo permitido. Si es `None`, no se aplica
                filtro por presupuesto.
            in_stock_only: Indica si solo deben retornarse productos con
                inventario disponible.
            limit: Cantidad máxima de productos a retornar.

        Returns:
            Lista de productos que cumplen los criterios de búsqueda.
        """

        ...

    async def get_by_skus(
        self,
        skus: list[str],
    ) -> list[Product]:
        """
        Consulta productos específicos por sus códigos SKU.

        Este métod se utiliza cuando el agente ya conoce los identificadores de
        los productos que debe recuperar, por ejemplo para comparar alternativas
        o ampliar información sobre productos previamente mencionados.

        La implementación debe ignorar SKU vacíos, duplicados o inexistentes.
        Cuando sea posible, los productos encontrados deben conservar el orden
        de los SKU solicitados.

        Args:
            skus: Códigos SKU de los productos que se desean consultar.

        Returns:
            Lista de productos encontrados en el orden solicitado.
        """

        ...


class CustomerRepository(Protocol):
    """
    Contrato para consultar y registrar clientes.

    Este repositorio permite validar clientes frecuentes y registrar clientes
    nuevos dentro del flujo conversacional.

    El agente lo utiliza antes de ejecutar operaciones asociadas a información
    sensible del cliente, como consultar pedidos, modificar direcciones de
    entrega o gestionar garantías.
    """

    async def get_by_identification(
        self,
        identification: str,
    ) -> Customer | None:
        """
        Consulta un cliente por su número de identificación.

        Este métod permite determinar si el usuario ya existe como cliente
        registrado en el sistema.

        Args:
            identification: Número de identificación del cliente.

        Returns:
            Cliente encontrado, o `None` si no existe un registro asociado.
        """

        ...

    async def get_by_email(
        self,
        email: str,
    ) -> Customer | None:
        """
        Consulta un cliente por su correo electrónico.

        Este métod puede usarse para validar duplicados durante el registro de
        clientes nuevos o para recuperar un cliente cuando el correo es el dato
        disponible en la conversación.

        Args:
            email: Correo electrónico del cliente.

        Returns:
            Cliente encontrado, o `None` si no existe un registro asociado.
        """

        ...

    async def create(
        self,
        customer: Customer,
    ) -> Customer | None:
        """
        Registra un cliente nuevo.

        La entidad recibida debe llegar validada y normalizada desde la capa de
        aplicación o desde una herramienta del agente. La implementación debe
        evitar duplicados por identificación o correo.

        Args:
            customer: Entidad de dominio con los datos del cliente a registrar.

        Returns:
            Cliente persistido, o `None` si no fue posible crearlo por una regla
            controlada de negocio.
        """

        ...


class OrderRepository(Protocol):
    """
    Contrato para consultar y actualizar pedidos.

    Este repositorio agrupa las operaciones necesarias para los flujos de
    postventa relacionados con seguimiento de pedidos, fecha estimada de entrega
    y actualización de dirección.

    El agente debe usar este contrato después de contar con la información
    mínima requerida, como identificación del cliente o número de pedido.
    """

    async def list_by_customer(
        self,
        customer_identification: str,
    ) -> list[Order]:
        """
        Lista los pedidos asociados a un cliente.

        Este métod se utiliza cuando el usuario quiere consultar sus compras,
        pero todavía no entregó un número de pedido específico.

        Args:
            customer_identification: Identificación del cliente validado.

        Returns:
            Lista de pedidos asociados al cliente.
        """

        ...

    async def get_by_number(
        self,
        order_number: str,
    ) -> Order | None:
        """
        Consulta un pedido por su número único.

        Este métod se usa cuando el usuario entrega directamente el número de
        pedido o cuando el agente necesita recuperar el detalle de un pedido
        previamente identificado.

        Args:
            order_number: Número único del pedido.

        Returns:
            Pedido encontrado, o `None` si no existe.
        """

        ...

    async def get_by_number_and_customer(
        self,
        order_number: str,
        customer_identification: str,
    ) -> Order | None:
        """
        Consulta un pedido validando que pertenezca al cliente indicado.

        Este métod evita exponer información de pedidos a usuarios que no
        corresponden al titular de la compra.

        Args:
            order_number: Número único del pedido.
            customer_identification: Identificación del cliente validado.

        Returns:
            Pedido encontrado para ese cliente, o `None` si no existe o no le
            pertenece.
        """

        ...

    async def update_delivery_address(
        self,
        order_number: str,
        customer_identification: str,
        new_address: str,
    ) -> Order | None:
        """
        Actualiza la dirección de entrega de un pedido.

        Este métod se utiliza cuando el cliente solicita modificar la dirección
        asociada a un pedido activo. La implementación debe validar si el pedido
        todavía permite cambios antes de aplicar la actualización.

        Args:
            order_number: Número único del pedido.
            customer_identification: Identificación del cliente validado.
            new_address: Nueva dirección de entrega.

        Returns:
            Pedido actualizado, o `None` si el pedido no existe, no pertenece al
            cliente o ya no permite cambios.
        """

        ...
