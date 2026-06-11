"""Interfaz Streamlit del agente."""

import logging
import os
from uuid import uuid4

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000",
).rstrip("/")

st.set_page_config(
    page_title="Asistente Retail",
    page_icon="AI",
)

st.title("Asistente de tienda electrónica")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.button("Nueva conversación"):
    st.session_state.session_id = str(uuid4())
    st.session_state.messages = []
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Escribe tu mensaje")

if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.spinner("Pensando..."):
            response = httpx.post(
                f"{API_BASE_URL}/chat",
                json={
                    "message": prompt,
                    "session_id": st.session_state.session_id,
                },
                timeout=60,
            )

            response.raise_for_status()
            payload = response.json()

            st.session_state.session_id = payload["session_id"]
            reply = payload["reply"]

    except httpx.HTTPStatusError as exc:
        logger.error(
            "API returned status=%s",
            exc.response.status_code,
        )

        try:
            reply = exc.response.json()["detail"]
        except (ValueError, KeyError):
            reply = "El asistente no pudo procesar la solicitud."

    except httpx.RequestError:
        logger.exception(
            "Could not connect to API url=%s",
            API_BASE_URL,
        )
        reply = "No fue posible conectarse con la API."

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": reply,
        }
    )

    with st.chat_message("assistant"):
        st.markdown(reply)
