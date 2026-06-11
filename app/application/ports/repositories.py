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

from app.domain.entities import (
    Customer,
    Order,
    Product,
    Warranty,
    WarrantyClaim,
)


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

    Esto evita que el modelo de lenguaje pueda consultar pedidos de otro cliente
    enviando una identificación arbitraria.
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

        La implementación debe buscar el pedido por número y cliente en una
        misma operación. Si el pedido no existe o pertenece a otro cliente, debe
        retornar `None`.

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
            Pedido actualizado o `None` si no existe, no pertenece al cliente o
            su estado no permite cambios.
        """

        ...


class WarrantyRepository(Protocol):
    """
    Contrato para consultar garantías y administrar reclamos técnicos.

    Todas las operaciones reciben la identificación del cliente validado desde
    `ConversationContext`. La implementación nunca debe confiar en una
    identificación proporcionada directamente por el modelo de lenguaje.

    La implementación concreta debe comprobar la propiedad mediante la relación:

    `customer -> order -> order_items -> warranty`

    Esto evita consultar, registrar o escalar garantías pertenecientes a otro
    cliente.

    Este contrato cubre tres flujos principales:

    - Consultar cobertura de garantía.
    - Crear reclamos o tickets técnicos.
    - Escalar reclamos a atención humana.
    """

    async def list_by_order_and_customer(
        self,
        order_number: str,
        customer_identification: str,
    ) -> list[Warranty]:
        """
        Lista las garantías de los productos incluidos en un pedido.

        La consulta debe comprobar que el pedido pertenece al cliente indicado.
        Si el pedido no existe, pertenece a otro cliente o no tiene garantías,
        debe retornar una lista vacía.

        Esta operación permite detectar pedidos con varios productos y pedir al
        usuario que seleccione el SKU correcto antes de consultar cobertura o
        registrar un reclamo.

        Args:
            order_number: Número normalizado del pedido.
            customer_identification: Identificación del cliente verificado en
                la sesión.

        Returns:
            Garantías asociadas al pedido y al cliente.
        """

        ...

    async def get_by_order_product_and_customer(
        self,
        order_number: str,
        product_sku: str,
        customer_identification: str,
    ) -> Warranty | None:
        """
        Consulta una garantía validando pedido, producto y propietario.

        La consulta debe comprobar simultáneamente:

        - Que el pedido existe.
        - Que pertenece al cliente verificado.
        - Que el producto está incluido en el pedido.
        - Que existe una garantía para ese producto y pedido.

        Retornar `None` tanto para recursos inexistentes como ajenos evita
        revelar información de otros clientes.

        Args:
            order_number: Número normalizado del pedido.
            product_sku: SKU normalizado del producto.
            customer_identification: Cliente verificado en la sesión.

        Returns:
            Garantía encontrada, o `None` si no existe o no pertenece al cliente.
        """

        ...

    async def get_open_claim_by_warranty_and_customer(
        self,
        warranty_id: str,
        customer_identification: str,
    ) -> WarrantyClaim | None:
        """
        Consulta un reclamo activo para evitar tickets duplicados.

        Se consideran activos los reclamos en estado:

        - `OPEN`
        - `IN_REVIEW`
        - `ESCALATED`

        Los reclamos `RESOLVED` o `REJECTED` no bloquean necesariamente la
        creación de un caso nuevo, porque el cliente podría reportar una falla
        diferente sobre el mismo producto.

        Args:
            warranty_id: Identificador de la garantía.
            customer_identification: Cliente verificado en la sesión.

        Returns:
            Reclamo activo encontrado, o `None` si no existe.
        """

        ...

    async def create_claim(
        self,
        claim_id: str,
        warranty_id: str,
        customer_identification: str,
        description: str,
    ) -> WarrantyClaim | None:
        """
        Registra un reclamo y genera el ticket técnico.

        La implementación debe validar nuevamente que la garantía pertenece al
        cliente. No debe confiar únicamente en una consulta anterior, porque el
        estado de los datos pudo cambiar entre la consulta de cobertura y la
        creación del reclamo.

        `claim_id` también funciona como número de ticket.

        Args:
            claim_id: Identificador único del reclamo, por ejemplo `CLM-1001`.
            warranty_id: Garantía sobre la cual se registra el caso.
            customer_identification: Cliente verificado en la sesión.
            description: Problema reportado por el cliente.

        Returns:
            Reclamo creado, o `None` si la garantía no existe o no pertenece al
            cliente.
        """

        ...

    async def get_claim_by_number_and_customer(
        self,
        ticket_number: str,
        customer_identification: str,
    ) -> WarrantyClaim | None:
        """
        Consulta un ticket validando su propietario.

        La implementación debe comprobar que el ticket exista y pertenezca al
        cliente verificado. Si no existe o pertenece a otro cliente, debe
        retornar `None`.

        Args:
            ticket_number: ID del reclamo y número de ticket.
            customer_identification: Cliente verificado en la sesión.

        Returns:
            Reclamo encontrado, o `None` si no existe o pertenece a otro cliente.
        """

        ...

    async def escalate_claim(
        self,
        ticket_number: str,
        customer_identification: str,
        escalation_reason: str,
    ) -> WarrantyClaim | None:
        """
        Escala un reclamo a atención humana.

        La implementación debe ejecutar una actualización condicionada que
        compruebe simultáneamente:

        - Que el ticket existe.
        - Que pertenece al cliente verificado.
        - Que está en estado `OPEN` o `IN_REVIEW`.

        La actualización debe establecer:

        - `status = ESCALATED`
        - `requires_human = True`
        - `escalation_reason` con el motivo validado por la aplicación

        Args:
            ticket_number: Número del ticket que será escalado.
            customer_identification: Cliente verificado en la sesión.
            escalation_reason: Motivo concreto del escalamiento.

        Returns:
            Reclamo actualizado, o `None` si no existe, no pertenece al cliente
            o no admite escalamiento.
        """

        ...
