"""Chainlit entrypoint for serving the Smart Financial Assistant chat UI."""

from __future__ import annotations

import asyncio
from typing import Optional

import chainlit as cl
from dotenv import load_dotenv

from smart_financial_assistant import SmartFinancialAssistant

load_dotenv()

_assistant_lock = asyncio.Lock()
_assistant_singleton: Optional[SmartFinancialAssistant] = None
_ingest_lock = asyncio.Lock()
_knowledge_index_ready = False


async def _get_or_create_assistant() -> SmartFinancialAssistant:
    """Return a singleton assistant instance, creating it lazily in a thread."""
    global _assistant_singleton
    if _assistant_singleton is not None:
        return _assistant_singleton

    async with _assistant_lock:
        if _assistant_singleton is None:
            _assistant_singleton = await asyncio.to_thread(SmartFinancialAssistant)
    return _assistant_singleton


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize assistant resources and send a startup status message to the user."""
    global _knowledge_index_ready
    try:
        assistant = await _get_or_create_assistant()
        ingested = 0

        # Avoid duplicate inserts when multiple chats start at nearly the same time.
        if not _knowledge_index_ready:
            async with _ingest_lock:
                if not _knowledge_index_ready:
                    ingested = await asyncio.to_thread(assistant.ingest_knowledge, force=False)
                    _knowledge_index_ready = True

        indexed_count = await asyncio.to_thread(assistant.indexed_fragments_count)

        welcome = (
            "Asistente financiero listo. "
            "Puedo consultar SIIGO (datos reales) y combinarlo con conocimiento RAG para interpretar resultados."
        )
        if ingested:
            welcome += f"\n\nBase de conocimiento indexada: {ingested} fragmentos."
        welcome += f"\n\nFragmentos actualmente en indice: {indexed_count}."

        await cl.Message(content=welcome).send()
    except Exception as exc:
        await cl.Message(
            content=(
                "No fue posible iniciar el asistente. "
                "Verifica variables de entorno y conectividad. "
                f"Detalle: {exc}"
            )
        ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle an incoming chat message and stream the assistant response."""
    thinking = cl.Message(content="Analizando tu solicitud...")
    await thinking.send()

    try:
        assistant = await _get_or_create_assistant()
        answer = await asyncio.to_thread(assistant.ask, message.content)
        thinking.content = answer
        await thinking.update()
    except Exception as exc:
        thinking.content = (
            "Ocurrio un error al procesar tu consulta. "
            "Revisa credenciales SIIGO, claves del LLM y acceso de red. "
            f"Detalle: {exc}"
        )
        await thinking.update()
