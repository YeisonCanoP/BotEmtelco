"""
Herramientas para consultar y comparar productos del catálogo.

Este módulo contiene las herramientas que el agente puede invocar para obtener
información actualizada del catálogo, incluyendo productos, precios,
disponibilidad y especificaciones técnicas.

Las herramientas de este módulo evitan que el agente invente datos comerciales,
ya que toda recomendación o comparación debe basarse en información consultada
desde el repositorio de catálogo.
"""

from app.application.dtos import (
    CatalogSearchInputDTO,
    CatalogSearchResultDTO,
    CompareProductsInputDTO,
    ProductComparisonResultDTO,
    ProductResultDTO,
)
from app.application.ports.repositories import CatalogRepository
from app.application.tools.base import Tool
from app.domain.entities import Product


def product_to_result_dto(
    product: Product,
) -> ProductResultDTO:
    """
    Convierte una entidad de dominio `Product` en un DTO serializable.

    Esta función adapta el producto obtenido desde el repositorio al formato
    usado por las herramientas del agente.

    Args:
        product: Producto de dominio obtenido desde el catálogo.

    Returns:
        ProductResultDTO: Producto serializable con información comercial,
        disponibilidad y especificaciones técnicas.
    """
    return ProductResultDTO(
        sku=product.sku,
        name=product.name,
        category=product.category,
        description=product.description,
        price=product.price,
        stock=product.stock,
        available=product.is_available,
        specs=dict(product.specs),
    )


class SearchCatalogTool(Tool[CatalogSearchInputDTO, CatalogSearchResultDTO]):
    """
    Herramienta para buscar productos en el catálogo.

    Permite consultar productos usando una necesidad del cliente, una categoría,
    un presupuesto máximo y un filtro de disponibilidad. Debe usarse antes de
    responder con precios, stock, características técnicas o recomendaciones.
    """

    name = "search_catalog"

    description = (
        "Busca productos reales en el catálogo de la tienda. "
        "Usa esta herramienta obligatoriamente antes de mencionar precios, "
        "disponibilidad, características técnicas o recomendaciones de compra. "
        "Permite buscar por necesidad del cliente, categoría, presupuesto máximo "
        "y disponibilidad en inventario."
    )

    def __init__(
        self,
        repository: CatalogRepository,
    ) -> None:
        """
        Inicializa la herramienta de búsqueda de catálogo.

        Args:
            repository: Repositorio usado para consultar productos disponibles.
        """
        self._repository = repository

    @property
    def input_model(self) -> type[CatalogSearchInputDTO]:
        """
        Retorna el modelo de entrada de la herramienta.

        Returns:
            type[CatalogSearchInputDTO]: DTO usado para validar los criterios
            de búsqueda del catálogo.
        """
        return CatalogSearchInputDTO

    async def execute(
        self,
        arguments: CatalogSearchInputDTO,
    ) -> CatalogSearchResultDTO:
        """
        Ejecuta la búsqueda de productos en el catálogo.

        Args:
            arguments: Criterios validados de búsqueda, como necesidad,
                categoría, presupuesto máximo, disponibilidad y límite.

        Returns:
            CatalogSearchResultDTO: Resultado normalizado con los productos
            encontrados y la cantidad total retornada.
        """
        products = await self._repository.search(
            query=arguments.query,
            category=arguments.category,
            max_price=arguments.max_price,
            in_stock_only=arguments.in_stock_only,
            limit=arguments.limit,
        )

        product_results = [product_to_result_dto(product) for product in products]

        return CatalogSearchResultDTO(
            found=bool(product_results),
            count=len(product_results),
            products=product_results,
        )


class CompareProductsTool(
    Tool[
        CompareProductsInputDTO,
        ProductComparisonResultDTO,
    ]
):
    """
    Herramienta para consultar productos que serán comparados.

    Recibe entre dos y cuatro SKU previamente obtenidos desde el catálogo y
    consulta nuevamente su información para asegurar que precio, inventario y
    especificaciones estén actualizados.
    """

    name = "compare_products"

    description = (
        "Consulta información actualizada de entre dos y cuatro productos "
        "para compararlos. Usa esta herramienta después de buscar productos "
        "cuando necesites contrastar precio, disponibilidad, procesador, RAM, "
        "almacenamiento, GPU, pantalla u otras especificaciones. "
        "Solo debes enviar códigos SKU obtenidos previamente del catálogo."
    )

    def __init__(
        self,
        repository: CatalogRepository,
    ) -> None:
        """
        Inicializa la herramienta de comparación de productos.

        Args:
            repository: Repositorio usado para consultar productos por SKU.
        """
        self._repository = repository

    @property
    def input_model(self) -> type[CompareProductsInputDTO]:
        """
        Retorna el modelo de entrada de la herramienta.

        Returns:
            type[CompareProductsInputDTO]: DTO usado para validar los SKU que
            serán comparados.
        """
        return CompareProductsInputDTO

    async def execute(
        self,
        arguments: CompareProductsInputDTO,
    ) -> ProductComparisonResultDTO:
        """
        Consulta productos específicos para comparación.

        Los productos encontrados se retornan con información actualizada. Los
        SKU que no existan en el catálogo se reportan en `missing_skus`.

        Args:
            arguments: Lista validada de SKU que se desean comparar.

        Returns:
            ProductComparisonResultDTO: Resultado con productos encontrados,
            SKU solicitados y SKU ausentes.
        """
        products = await self._repository.get_by_skus(arguments.skus)

        found_skus = {product.sku for product in products}
        missing_skus = [sku for sku in arguments.skus if sku not in found_skus]
        product_results = [product_to_result_dto(product) for product in products]

        return ProductComparisonResultDTO(
            found=bool(product_results),
            requested_skus=arguments.skus,
            missing_skus=missing_skus,
            products=product_results,
        )
