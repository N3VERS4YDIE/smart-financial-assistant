"""CLI entrypoint for local execution of the Smart Financial Assistant."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from smart_financial_assistant import SmartFinancialAssistant


def main() -> None:
    """Run the assistant in single-question or interactive CLI mode."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Asistente Financiero Inteligente (SIIGO + RAG + Agent)")
    parser.add_argument("question", nargs="?", help="Pregunta para el asistente")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Reconstruye el indice RAG desde knowledge_base",
    )
    args = parser.parse_args()

    assistant = SmartFinancialAssistant()
    try:
        ingested = assistant.ingest_knowledge(force=args.reindex)
        if ingested:
            print(f"RAG listo: {ingested} fragmentos procesados.")

        if args.reindex and not args.question:
            return

        if args.question:
            print(assistant.ask(args.question))
            return

        print("Asistente listo. Escribe tu pregunta (o 'salir').")
        while True:
            question = input("\n> ").strip()
            if question.lower() in {"salir", "exit", "quit"}:
                break
            if not question:
                continue
            print(assistant.ask(question))
    finally:
        assistant.close()


if __name__ == "__main__":
    main()
