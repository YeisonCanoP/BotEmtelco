"""
Interfaz Streamlit del agente conversacional.

Este módulo define una interfaz web simple para interactuar con el agente de
retail electrónico. La aplicación mantiene una sesión conversacional en
`st.session_state`, envía los mensajes del usuario a la API FastAPI y muestra
las respuestas generadas por el asistente.

El session_id se persiste en la URL (?session=...) para que no cambie al
recargar la página.
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
# Persistencia del session_id en la URL
# ---------------------------------------------------------------------------


def get_or_create_session_id() -> str:
    """
    Lee el session_id desde los query params de la URL.
    Si no existe, crea uno nuevo y lo escribe en la URL.
    Así persiste entre recargas sin depender de st.session_state.
    """
    params = st.query_params
    if "session" in params:
        return params["session"]
    new_id = str(uuid4())
    st.query_params["session"] = new_id
    return new_id


def set_session_id(session_id: str) -> None:
    """Actualiza el session_id en la URL y reinicia el historial."""
    st.query_params["session"] = session_id
    st.session_state.messages = []


def reset_session() -> None:
    """Genera un nuevo session_id aleatorio."""
    set_session_id(str(uuid4()))


# ---------------------------------------------------------------------------
# Estado de la sesión
# ---------------------------------------------------------------------------

current_session_id = get_or_create_session_id()

# Si el session_id de la URL cambió respecto al anterior, limpiar historial.
if st.session_state.get("last_session_id") != current_session_id:
    st.session_state.messages = []
    st.session_state.last_session_id = current_session_id

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def send_message(prompt: str, session_id: str) -> str:
    """Envía el mensaje del usuario a la API y devuelve la respuesta."""
    try:
        response = httpx.post(
            f"{API_BASE_URL}/chat",
            json={"message": prompt, "session_id": session_id},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("reply", "El asistente no devolvió una respuesta.")

    except httpx.HTTPStatusError as exc:
        logger.error("La API devolvió status=%s", exc.response.status_code)
        try:
            return exc.response.json()["detail"]
        except (ValueError, KeyError):
            return "El asistente no pudo procesar la solicitud."

    except httpx.RequestError:
        logger.exception("No se pudo conectar con la API url=%s", API_BASE_URL)
        return "No fue posible conectarse con la API. Inténtalo de nuevo."


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

with st.sidebar:
    st.subheader("🛍️ Asistente Retail")
    st.caption("Tienda de electrónica · soporte y compras")
    st.divider()

    # Sesión activa (solo lectura, para referencia)
    st.markdown("**Sesión activa**")
    st.code(current_session_id, language=None)

    # Ingresar sesión manualmente
    st.markdown("**Cambiar sesión**")
    manual_id = st.text_input(
        "Session ID",
        placeholder="Pega un ID existente o deja vacío",
        label_visibility="collapsed",
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Usar", use_container_width=True, disabled=not manual_id):
            set_session_id(manual_id.strip())
            st.rerun()
    with col2:
        if st.button("Nueva", use_container_width=True):
            reset_session()
            st.rerun()

    st.divider()
    st.caption(
        "El ID de sesión se guarda en la URL. Cópialo para retomar esta conversación más tarde."
    )

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
    session_id = st.query_params.get("session", current_session_id)

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando…"):
            reply = send_message(prompt, session_id)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
