"""
Interfaz Streamlit del agente conversacional.

Este módulo define una interfaz web simple para interactuar con el agente de
retail electrónico. La aplicación mantiene una sesión conversacional en
`st.session_state`, envía los mensajes del usuario a la API FastAPI y muestra
las respuestas generadas por el asistente.
"""

import logging
import os
from uuid import uuid4

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = 60

WELCOME_MESSAGE = (
    "¡Hola! Soy tu asistente de la tienda. Puedo ayudarte a buscar productos, "
    "consultar el estado de tus pedidos y gestionar garantías. ¿En qué te ayudo?"
)


# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Asistente Retail",
    page_icon="🛍️",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Estado de la sesión
# ---------------------------------------------------------------------------


def reset_conversation() -> None:
    """Reinicia la conversación con un nuevo identificador de sesión."""
    st.session_state.session_id = str(uuid4())
    st.session_state.messages = []


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def send_message(prompt: str) -> str:
    """Envía el mensaje del usuario a la API y devuelve la respuesta del asistente."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": prompt,
                "session_id": st.session_state.session_id,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        # Mantener el session_id que devuelve el backend, si existe.
        st.session_state.session_id = payload.get("session_id", st.session_state.session_id)
        return payload.get("reply", "El asistente no devolvió una respuesta.")

    except httpx.HTTPStatusError as exc:
        logger.error("La API devolvió status=%s", exc.response.status_code)
        try:
            return exc.response.json()["detail"]
        except (ValueError, KeyError):
            return "El asistente no pudo procesar la solicitud."

    except httpx.RequestError:
        logger.exception("No se pudo conectar con la API url=%s", API_BASE_URL)
        return "No fue posible conectarse con la API. Inténtalo de nuevo en un momento."


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("Asistente Retail")
    st.caption("Tienda de electrónica · soporte y compras")
    st.divider()

    if st.button("Nueva conversación", use_container_width=True):
        reset_conversation()
        st.rerun()

    st.caption(f"Sesión actual: `{st.session_state.session_id[:8]}`")


# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------

st.title("🛍️ Asistente de la tienda")
st.caption("Pregúntame por productos, pedidos o garantías.")


# ---------------------------------------------------------------------------
# Historial de mensajes
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown(WELCOME_MESSAGE)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------------------------------------------------------------------
# Entrada del usuario
# ---------------------------------------------------------------------------

prompt = st.chat_input("Escribe tu mensaje")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando…"):
            reply = send_message(prompt)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
