"""
DTOs utilizados por las herramientas de gestión de garantías.

Este módulo define los modelos de entrada y salida usados por las herramientas
relacionadas con garantías, reclamos técnicos y escalamiento a atención humana.

La identificación del cliente nunca se recibe desde el modelo de lenguaje.
Debe obtenerse exclusivamente desde `ConversationContext` después de verificar
al cliente. Esto evita que el modelo consulte o registre garantías para un
cliente distinto al validado en la sesión.

Responsabilidades principales:

- Validar entradas para consultar garantías por pedido y producto.
- Exponer resúmenes seguros de garantías al agente.
- Registrar reclamos de garantía con descripciones normalizadas.
- Retornar tickets técnicos creados o reclamos existentes.
- Validar entradas para escalar reclamos a un asesor humano.
- Garantizar consistencia entre banderas como `success`, `found`, `covered`,
  `created` y `escalated`.
"""

from datetime import date, datetime
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.entities import WarrantyClaimStatus


class WarrantyLookupInputDTO(BaseModel):
    """
    Entrada para consultar la garantía de un producto comprado.

    Este DTO se usa cuando el usuario quiere saber si un producto incluido en un
    pedido tiene garantía vigente.

    El SKU es opcional porque un pedido puede contener un único producto. Si el
    pedido contiene varias garantías y no se proporciona SKU, la herramienta
    debe retornar las opciones disponibles para que el usuario seleccione el
    producto correcto.

    Attributes:
        order_number: Número del pedido asociado a la compra.
        product_sku: SKU del producto cuando el pedido contiene varios
            productos o cuando el usuario ya lo proporcionó.
    """

    model_config = ConfigDict(extra="forbid")

    order_number: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[A-Z0-9-]+$",
        description="Número del pedido. Ejemplo: ORD-1002.",
    )

    product_sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        pattern=r"^[A-Z0-9-]+$",
        description=(
            "SKU del producto cuando el pedido contiene varios productos. No inventes este valor."
        ),
    )

    @field_validator("order_number", mode="before")
    @classmethod
    def normalize_order_number(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza el número del pedido.

        Elimina espacios externos y convierte el valor a mayúsculas para evitar
        diferencias de formato entre lo escrito por el usuario y lo almacenado.

        Args:
            value: Número de pedido recibido.

        Returns:
            Número de pedido normalizado.
        """

        return value.strip().upper()

    @field_validator("product_sku", mode="before")
    @classmethod
    def normalize_product_sku(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normaliza el SKU cuando fue proporcionado.

        Si el SKU no fue enviado, se conserva como `None` para permitir que la
        herramienta decida si debe consultar una única garantía o pedir selección
        de producto.

        Args:
            value: SKU recibido o `None`.

        Returns:
            SKU normalizado en mayúsculas, o `None` si no fue proporcionado.
        """

        if value is None:
            return None

        return value.strip().upper()


class WarrantySummaryDTO(BaseModel):
    """
    Resumen seguro de una garantía perteneciente al cliente verificado.

    Este DTO expone únicamente los datos necesarios para que el agente pueda
    informar si una garantía existe, está activa y cubre la fecha actual.

    Attributes:
        id: Identificador único de la garantía.
        product_sku: SKU del producto cubierto.
        order_id: Número del pedido asociado a la garantía.
        active: Indica si la garantía está habilitada administrativamente.
        starts_on: Fecha de inicio de cobertura.
        expires_on: Fecha de vencimiento de cobertura.
        covered: Indica si la garantía cubre actualmente el producto.
    """

    id: str = Field(
        min_length=1,
        max_length=30,
    )

    product_sku: str = Field(
        min_length=1,
        max_length=30,
    )

    order_id: str = Field(
        min_length=1,
        max_length=30,
    )

    active: bool

    starts_on: date

    expires_on: date

    covered: bool

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        """
        Valida la consistencia del periodo de garantía.

        Reglas de consistencia:

        - La fecha de vencimiento no puede ser anterior a la fecha de inicio.
        - Una garantía inactiva no puede aparecer como cubierta.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si las fechas o el estado de cobertura son
                inconsistentes.
        """

        if self.expires_on < self.starts_on:
            raise ValueError("La fecha de vencimiento no puede ser anterior al inicio")

        if self.covered and not self.active:
            raise ValueError("Una garantía inactiva no puede aparecer como cubierta")

        return self


WarrantyLookupReason = Literal[
    "CUSTOMER_NOT_VERIFIED",
    "ORDER_OR_WARRANTY_NOT_FOUND",
    "PRODUCT_SELECTION_REQUIRED",
    "WARRANTY_NOT_ACTIVE",
    "WARRANTY_NOT_STARTED",
    "WARRANTY_EXPIRED",
]
"""
Motivos controlados por los que una consulta de garantía no produce cobertura.

Valores permitidos:
    CUSTOMER_NOT_VERIFIED: No hay cliente validado en la conversación.
    ORDER_OR_WARRANTY_NOT_FOUND: El pedido o la garantía no existen, o no
        pertenecen al cliente validado.
    PRODUCT_SELECTION_REQUIRED: El pedido tiene varias garantías y se requiere
        seleccionar un producto.
    WARRANTY_NOT_ACTIVE: La garantía existe, pero no está activa.
    WARRANTY_NOT_STARTED: La garantía existe, pero su cobertura aún no inicia.
    WARRANTY_EXPIRED: La garantía existe, pero ya venció.
"""


class WarrantyLookupResultDTO(BaseModel):
    """
    Resultado de consultar la cobertura de garantía.

    Este DTO representa una consulta de garantía exitosa, una garantía no
    cubierta, una falta de verificación del cliente o una selección pendiente de
    producto.

    Cuando existen varias garantías y no se indicó el SKU, `warranties` contiene
    las opciones disponibles y `requires_product_selection` debe ser `True`.

    Attributes:
        success: Indica si la consulta se ejecutó correctamente.
        found: Indica si se encontró una garantía asociada.
        covered: Indica si la garantía cubre actualmente el producto.
        requires_customer_verification: Indica si primero debe validarse el
            cliente.
        requires_product_selection: Indica si el usuario debe seleccionar un
            producto.
        reason: Motivo controlado cuando no hay cobertura o falta información.
        warranty: Garantía individual consultada.
        warranties: Lista de garantías disponibles cuando se requiere selección.
    """

    success: bool

    found: bool

    covered: bool

    requires_customer_verification: bool = False

    requires_product_selection: bool = False

    reason: WarrantyLookupReason | None = None

    warranty: WarrantySummaryDTO | None = None

    warranties: list[WarrantySummaryDTO] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Comprueba que las banderas y los datos sean consistentes.

        Reglas principales:

        - Una consulta sin cliente verificado no puede ser exitosa.
        - Una selección de producto requiere una consulta exitosa y al menos dos
          garantías disponibles.
        - Una garantía cubierta debe incluir una garantía individual.
        - No se debe retornar una garantía individual y una lista de garantías al
          mismo tiempo.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.requires_customer_verification:
            if self.success or self.found or self.covered:
                raise ValueError("Una consulta sin cliente verificado no puede ser exitosa")

            if self.reason != "CUSTOMER_NOT_VERIFIED":
                raise ValueError("La consulta debe indicar que falta verificar al cliente")

            if self.warranty is not None or self.warranties:
                raise ValueError("No pueden retornarse garantías sin verificar al cliente")

        if self.requires_product_selection:
            if not self.success or not self.found:
                raise ValueError("La selección de producto requiere una consulta exitosa")

            if self.covered or self.warranty is not None:
                raise ValueError("No puede existir una garantía seleccionada todavía")

            if len(self.warranties) < 2:
                raise ValueError("La selección requiere al menos dos garantías disponibles")

            if self.reason != "PRODUCT_SELECTION_REQUIRED":
                raise ValueError("Debe indicarse que hace falta seleccionar el producto")

        if self.covered:
            if not self.success or not self.found:
                raise ValueError("Una garantía cubierta debe haber sido encontrada")

            if self.warranty is None:
                raise ValueError("Una garantía cubierta debe incluir información")

            if not self.warranty.covered:
                raise ValueError("La garantía retornada debe aparecer como cubierta")

            if self.reason is not None:
                raise ValueError("Una garantía cubierta no debe tener motivo de fallo")

        if self.warranty is not None and self.warranties:
            raise ValueError(
                "No se debe retornar una garantía individual y una lista simultáneamente"
            )

        return self


class WarrantyClaimCreateInputDTO(BaseModel):
    """
    Entrada para registrar un reclamo de garantía.

    Este DTO se usa cuando el usuario reporta un problema sobre un producto
    comprado y cubierto por garantía.

    La herramienta debe volver a comprobar cobertura y propiedad antes de crear
    el reclamo. No debe confiar únicamente en una consulta anterior realizada
    por el agente.

    Attributes:
        order_number: Número del pedido asociado al producto.
        product_sku: SKU del producto afectado.
        issue_description: Descripción concreta del problema reportado por el
            cliente.
    """

    model_config = ConfigDict(extra="forbid")

    order_number: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[A-Z0-9-]+$",
        description="Número del pedido asociado al producto.",
    )

    product_sku: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[A-Z0-9-]+$",
        description="SKU del producto afectado, obtenido previamente.",
    )

    issue_description: str = Field(
        min_length=10,
        max_length=2_000,
        description=(
            "Descripción concreta del problema reportado por el cliente. "
            "No agregues síntomas que el cliente no haya mencionado."
        ),
    )

    @field_validator("order_number", "product_sku", mode="before")
    @classmethod
    def normalize_identifiers(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza identificadores de pedido y producto.

        Args:
            value: Número de pedido o SKU recibido.

        Returns:
            Identificador normalizado en mayúsculas.
        """

        return value.strip().upper()

    @field_validator("issue_description")
    @classmethod
    def normalize_description(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza la descripción del problema.

        Elimina espacios repetidos para almacenar una descripción más limpia,
        sin modificar el contenido semántico reportado por el cliente.

        Args:
            value: Descripción del problema.

        Returns:
            Descripción normalizada.
        """

        return " ".join(value.split())


class WarrantyClaimDTO(BaseModel):
    """
    Reclamo de garantía expuesto de forma segura al agente.

    Este DTO representa un reclamo o ticket técnico sin exponer información
    innecesaria del cliente.

    Attributes:
        id: Identificador del reclamo. También funciona como número de ticket.
        warranty_id: Garantía asociada al reclamo.
        description: Descripción normalizada del problema.
        status: Estado actual del reclamo.
        requires_human: Indica si el caso requiere atención humana.
        created_at: Fecha y hora de creación del reclamo.
        updated_at: Fecha y hora de última actualización.
    """

    id: str = Field(
        min_length=1,
        max_length=40,
    )

    warranty_id: str = Field(
        min_length=1,
        max_length=30,
    )

    description: str = Field(
        min_length=1,
        max_length=2_000,
    )

    status: WarrantyClaimStatus

    requires_human: bool

    created_at: datetime

    updated_at: datetime


WarrantyClaimCreateReason = Literal[
    "CUSTOMER_NOT_VERIFIED",
    "ORDER_OR_WARRANTY_NOT_FOUND",
    "WARRANTY_NOT_COVERED",
    "CLAIM_ALREADY_EXISTS",
]
"""
Motivos controlados por los que no se pudo crear un reclamo de garantía.

Valores permitidos:
    CUSTOMER_NOT_VERIFIED: No hay cliente validado en la conversación.
    ORDER_OR_WARRANTY_NOT_FOUND: El pedido o la garantía no existen, o no
        pertenecen al cliente validado.
    WARRANTY_NOT_COVERED: La garantía existe, pero no cubre actualmente el
        producto.
    CLAIM_ALREADY_EXISTS: Ya existe un reclamo abierto o registrado para esa
        garantía.
"""


class WarrantyClaimCreateResultDTO(BaseModel):
    """
    Resultado del registro de un reclamo y ticket técnico.

    Cuando el reclamo se crea correctamente, `ticket_number` contiene el mismo
    valor que el ID del reclamo.

    Si el reclamo no se crea, el resultado incluye un motivo controlado. En caso
    de duplicidad, también puede incluir el reclamo existente.

    Attributes:
        success: Indica si la operación terminó exitosamente.
        created: Indica si se creó un nuevo reclamo.
        reason: Motivo controlado cuando no se pudo crear el reclamo.
        ticket_number: Número de ticket generado. Coincide con el ID del
            reclamo.
        claim: Reclamo creado cuando la operación es exitosa.
        existing_claim: Reclamo existente cuando ya había un caso registrado.
    """

    success: bool

    created: bool

    reason: WarrantyClaimCreateReason | None = None

    ticket_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=40,
    )

    claim: WarrantyClaimDTO | None = None

    existing_claim: WarrantyClaimDTO | None = None

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Valida consistencia entre creación, ticket y reclamo.

        Reglas de consistencia:

        - Un reclamo creado debe ser exitoso.
        - Un reclamo creado debe incluir caso y número de ticket.
        - El número de ticket debe coincidir con el ID del reclamo.
        - Un reclamo creado no debe contener información de fallo.
        - Un reclamo no creado debe incluir motivo.
        - Solo un reclamo duplicado puede incluir `existing_claim`.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.created:
            if not self.success:
                raise ValueError("Un reclamo creado debe ser exitoso")

            if self.claim is None or self.ticket_number is None:
                raise ValueError("Un reclamo creado debe incluir caso y número de ticket")

            if self.ticket_number != self.claim.id:
                raise ValueError("El número de ticket debe coincidir con el ID del reclamo")

            if self.reason is not None or self.existing_claim is not None:
                raise ValueError("Un reclamo creado no debe contener información de fallo")

        if not self.created:
            if self.success:
                raise ValueError("Un reclamo no creado no puede marcarse como exitoso")

            if self.reason is None:
                raise ValueError("Un reclamo no creado debe incluir el motivo")

            if self.claim is not None or self.ticket_number is not None:
                raise ValueError("Un reclamo no creado no debe generar un ticket nuevo")

        if self.reason == "CLAIM_ALREADY_EXISTS" and self.existing_claim is None:
            raise ValueError("Un reclamo duplicado debe incluir el reclamo existente")

        if self.reason != "CLAIM_ALREADY_EXISTS" and self.existing_claim is not None:
            raise ValueError("Solo un reclamo duplicado puede incluir un caso existente")

        return self


class WarrantyClaimEscalateInputDTO(BaseModel):
    """
    Entrada para escalar un ticket a atención humana.

    Este DTO se usa cuando el caso requiere intervención de un asesor humano o
    equipo especializado.

    La herramienta debe comprobar que el ticket pertenezca al cliente verificado
    antes de escalarlo.

    Attributes:
        ticket_number: Número de ticket generado al registrar el reclamo.
        escalation_reason: Motivo concreto por el cual el caso requiere
            atención humana.
    """

    model_config = ConfigDict(extra="forbid")

    ticket_number: str = Field(
        min_length=1,
        max_length=40,
        pattern=r"^[A-Z0-9-]+$",
        description="Número de ticket generado al registrar el reclamo.",
    )

    escalation_reason: str = Field(
        min_length=10,
        max_length=1_000,
        description=("Motivo concreto por el cual el caso requiere atención humana."),
    )

    @field_validator("ticket_number", mode="before")
    @classmethod
    def normalize_ticket_number(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza el número de ticket.

        Args:
            value: Número de ticket recibido.

        Returns:
            Número de ticket normalizado en mayúsculas.
        """

        return value.strip().upper()

    @field_validator("escalation_reason")
    @classmethod
    def normalize_escalation_reason(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza el motivo del escalamiento.

        Args:
            value: Motivo del escalamiento recibido.

        Returns:
            Motivo normalizado sin espacios repetidos.
        """

        return " ".join(value.split())


WarrantyClaimEscalationReason = Literal[
    "CUSTOMER_NOT_VERIFIED",
    "CLAIM_NOT_FOUND_OR_NOT_OWNED",
    "CLAIM_ALREADY_ESCALATED",
    "CLAIM_NOT_ESCALATABLE",
]
"""
Motivos controlados por los que no se pudo escalar un reclamo.

Valores permitidos:
    CUSTOMER_NOT_VERIFIED: No hay cliente validado en la conversación.
    CLAIM_NOT_FOUND_OR_NOT_OWNED: El reclamo no existe o no pertenece al cliente.
    CLAIM_ALREADY_ESCALATED: El reclamo ya fue escalado previamente.
    CLAIM_NOT_ESCALATABLE: El estado actual del reclamo no permite escalarlo.
"""


class WarrantyClaimEscalationResultDTO(BaseModel):
    """
    Resultado de escalar un reclamo a un asesor humano.

    Este DTO representa tanto escalamiento exitoso como fallos controlados.

    Attributes:
        success: Indica si la operación terminó exitosamente.
        escalated: Indica si el reclamo fue escalado.
        reason: Motivo controlado cuando no se pudo escalar.
        claim: Reclamo actualizado cuando el escalamiento es exitoso.
    """

    success: bool

    escalated: bool

    reason: WarrantyClaimEscalationReason | None = None

    claim: WarrantyClaimDTO | None = None

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Valida consistencia del resultado de escalamiento.

        Reglas de consistencia:

        - Un escalamiento exitoso debe incluir el reclamo.
        - Un escalamiento exitoso no debe tener motivo de fallo.
        - El reclamo escalado debe tener estado `ESCALATED`.
        - El reclamo escalado debe requerir atención humana.
        - Un escalamiento fallido debe indicar el motivo.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.escalated:
            if not self.success or self.claim is None:
                raise ValueError("Un escalamiento exitoso debe incluir el reclamo")

            if self.reason is not None:
                raise ValueError("Un escalamiento exitoso no debe tener motivo de fallo")

            if self.claim.status is not WarrantyClaimStatus.ESCALATED:
                raise ValueError("El reclamo escalado debe tener estado ESCALATED")

            if not self.claim.requires_human:
                raise ValueError("El reclamo escalado debe requerir atención humana")

        if not self.escalated:
            if self.success:
                raise ValueError("Un reclamo no escalado no puede marcarse como exitoso")

            if self.reason is None:
                raise ValueError("Un escalamiento fallido debe indicar el motivo")

        return self
