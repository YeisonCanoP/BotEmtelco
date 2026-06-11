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

    Todas las operaciones trabajan con la identificación del cliente validado.
    El repositorio nunca debe retornar un pedido individual sin comprobar
    simultáneamente que pertenece a ese cliente.
    """

    async def list_by_customer(
        self,
        customer_identification: str,
    ) -> list[Order]:
        """
        Lista los pedidos pertenecientes al cliente.

        Args:
            customer_identification: Identificación obtenida desde
                `ConversationContext`, nunca desde argumentos del LLM.

        Returns:
            Pedidos del cliente, ordenados del más reciente al más antiguo.
        """
        ...

    async def get_by_number_and_customer(
        self,
        order_number: str,
        customer_identification: str,
    ) -> Order | None:
        """
        Consulta un pedido comprobando su propietario.

        Args:
            order_number: Número normalizado del pedido.
            customer_identification: Cliente validado en la sesión.

        Returns:
            Pedido encontrado o `None` cuando no existe o no pertenece al
            cliente indicado.
        """
        ...

    async def update_delivery_address(
        self,
        order_number: str,
        customer_identification: str,
        new_address: str,
    ) -> Order | None:
        """
        Actualiza la dirección de un pedido modificable.

        La implementación debe comprobar en una misma operación:

        - Que el pedido existe.
        - Que pertenece al cliente.
        - Que está en estado `CONFIRMED` o `PREPARING`.

        Args:
            order_number: Número normalizado del pedido.
            customer_identification: Cliente validado en la sesión.
            new_address: Nueva dirección normalizada.

        Returns:
            Pedido actualizado o `None` si no existe, no pertenece al cliente
            o su estado no permite cambios.
        """
        ...
