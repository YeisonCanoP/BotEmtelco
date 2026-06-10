"""Excepciones controladas de la capa de aplicación."""


class ApplicationError(Exception):
    """Excepción base de la capa de aplicación."""


class LLMServiceError(ApplicationError):
    """Error al comunicarse con el modelo de lenguaje."""


class SessionStoreError(ApplicationError):
    """Error al consultar o guardar una conversación."""
