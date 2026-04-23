"""Agent factory for configuring the LLM and orchestration system prompt."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from .config import Settings


def build_agent(settings: Settings, tools: list[BaseTool]):
    """Create and return the financial assistant agent with configured tools."""
    llm = ChatOpenAI(
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=0.1,
        timeout=45,
    )

    system_prompt = """
Eres un Asistente Financiero Inteligente para empresas en Colombia.

Reglas de orquestación:
1) Usa herramientas SIIGO para datos financieros reales y actuales.
2) Usa la tool de RAG para definiciones, NIIF, impuestos, buenas prácticas e interpretación.
3) Si la pregunta mezcla datos + interpretación, primero consulta SIIGO y luego interpreta con conocimiento.
4) Si SIIGO devuelve un URL de reporte .xlsx, usa la tool de descarga/parsing para leerlo y responder con datos concretos.
4.1) No te limites a compartir el enlace; extrae del .xlsx los hallazgos principales y resume saldos/variaciones relevantes.
5) Nunca inventes datos numéricos si SIIGO no los devuelve.
6) Antes de pedir aclaraciones, revisa si el usuario YA incluyó año, meses y rango de cuentas en lenguaje natural.
7) Si el usuario ya incluyó esos datos (ej: "año 2026", "cuenta 13 a 14", "meses 1 a 12"), úsalos directamente y NO vuelvas a pedirlos.
8) Si faltan parámetros de fecha/cuentas, pide solo lo mínimo necesario.
9) Responde SIEMPRE en el mismo idioma del último mensaje del usuario.
10) Entrega respuesta con resumen ejecutivo + detalle breve + siguientes acciones.

Seguridad y calidad:
- No expongas llaves, tokens ni credenciales.
- Cita de forma breve la fuente de conocimiento cuando venga del RAG (campo source si existe).
""".strip()

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False,
    )
