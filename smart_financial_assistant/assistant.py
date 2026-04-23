"""High-level assistant orchestration combining SIIGO tools, RAG, and agent runtime."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools.retriever import create_retriever_tool

from .agent import build_agent
from .config import load_settings
from .rag import RAGService
from .siigo_client import SiigoClient
from .tools import build_siigo_tools


class SmartFinancialAssistant:
    """Facade that exposes ingestion, querying, and lifecycle management methods."""

    def __init__(self) -> None:
        """Initialize settings, external services, tools, and the LLM agent."""
        self._settings = load_settings()
        self._siigo = SiigoClient(self._settings)
        self._rag = RAGService(self._settings)

        siigo_tools = build_siigo_tools(self._siigo, self._settings)
        rag_tool = create_retriever_tool(
            self._rag.as_retriever(k=4),
            name="financial_knowledge_base",
            description=(
                "Usa esta herramienta para conceptos financieros, NIIF, impuestos, "
                "contexto contable e interpretaciones de resultados."
            ),
        )

        self._agent = build_agent(self._settings, [*siigo_tools, rag_tool])

    def ingest_knowledge(self, *, force: bool = False) -> int:
        """Ingest local knowledge documents into the vector index."""
        return self._rag.ingest(force=force)

    def indexed_fragments_count(self) -> int:
        """Return how many document fragments are currently indexed in RAG storage."""
        return self._rag.count_indexed_fragments()

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Normalize different message content formats into plain text."""
        if content is None:
            return ""
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    if item.strip():
                        parts.append(item.strip())
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip()
        return str(content).strip()

    @staticmethod
    def _fallback_from_tool_messages(messages: list[Any]) -> str:
        """Build a readable fallback response from tool outputs when AI text is unavailable."""
        for msg in reversed(messages):
            name = getattr(msg, "name", None)
            content = getattr(msg, "content", None)
            if not isinstance(msg, dict) and name != "download_and_parse_xlsx_report":
                continue

            if isinstance(msg, dict) and msg.get("name") != "download_and_parse_xlsx_report":
                continue
            if isinstance(msg, dict):
                content = msg.get("content")

            text = SmartFinancialAssistant._extract_text(content)
            if not text:
                continue

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return text

            sheets = data.get("sheets") or []
            sheet_count = data.get("sheet_count", len(sheets))
            lines = [
                "Se descargó y leyó correctamente el reporte Excel.",
                f"Hojas detectadas: {sheet_count}.",
            ]

            for sheet in sheets[:2]:
                sheet_name = sheet.get("sheet", "(sin nombre)")
                rows = sheet.get("preview_rows") or []
                lines.append(f"- Hoja {sheet_name}: {len(rows)} filas de vista previa.")
                if rows:
                    header = rows[0]
                    lines.append(f"  Encabezado inicial: {header}")

            lines.append(
                "Puedo darte un resumen financiero más puntual si me indicas qué columnas quieres priorizar "
                "(saldo, débito, crédito, tercero, etc.)."
            )
            return "\n".join(lines)

        return ""

    def ask(self, question: str) -> str:
        """Invoke the agent with a user question and return the best available response text."""
        result = self._agent.invoke({"messages": [{"role": "user", "content": question}]})
        messages = result.get("messages", [])
        for msg in reversed(messages):
            content = getattr(msg, "content", None)
            msg_type = getattr(msg, "type", None)
            if msg_type == "ai":
                text = self._extract_text(content)
                if text:
                    return text
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                text = self._extract_text(msg.get("content"))
                if text:
                    return text

        tool_fallback = self._fallback_from_tool_messages(messages)
        if tool_fallback:
            return tool_fallback

        return "No fue posible generar una respuesta."

    def close(self) -> None:
        """Release external resources held by SIIGO and RAG clients."""
        self._siigo.close()
        self._rag.close()
