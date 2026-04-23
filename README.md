# Asistente Financiero Inteligente

Asistente financiero inteligente que combina:

- Tools de SIIGO para datos reales (cuentas por pagar, balance de prueba).
- Descarga y parseo de reportes `.xlsx` devueltos por SIIGO.
- RAG sobre base de conocimiento financiera/contable.
- Agent de LangChain para decidir automaticamente que fuente usar.

## Arquitectura

Usuario -> Agent (LangChain) -> Tools SIIGO y/o RAG -> Respuesta final

Separacion de capas:

- `Tools`: solo datos reales desde SIIGO.
- `RAG`: solo conocimiento externo (NIIF, impuestos, interpretacion).
- `Agent`: decide y combina.

## Estructura del proyecto

- `chainlit_app.py`: interfaz web conversacional con Chainlit.
- `main.py`: entrada CLI (opcional para pruebas locales).
- `smart_financial_assistant/config.py`: configuracion segura por variables de entorno.
- `smart_financial_assistant/siigo_client.py`: cliente HTTP con retry, timeout y auth token cacheado.
- `smart_financial_assistant/tools.py`: tools de LangChain para SIIGO.
- `smart_financial_assistant/rag.py`: ingesta y recuperacion con Qdrant.
- `smart_financial_assistant/agent.py`: prompt y orquestacion del agente.
- `smart_financial_assistant/assistant.py`: integracion completa.
- `knowledge_base/`: documentos de conocimiento para RAG.

## Requisitos

- Python 3.13+
- Credenciales SIIGO
- API key para LLM (OpenRouter)

## Configuracion

1. Crear entorno virtual e instalar dependencias con uv:

```bash
uv venv
source .venv/bin/activate
uv sync
```

2. Configurar variables:

```bash
cp .env.example .env
```

Completa `.env` con tus credenciales reales.

## Uso

Iniciar interfaz web (recomendado):

```bash
uv run chainlit run chainlit_app.py
```

Luego abre el navegador en la URL local mostrada por Chainlit.

CLI alternativa (opcional):

```bash
uv run main.py"
```

Reindexar la base RAG (opcional):

```bash
uv run main.py --reindex
```

## Buenas practicas implementadas

- No se guardan secretos en codigo.
- Validacion tipada de payloads para endpoints SIIGO.
- Timeouts + retries en llamadas HTTP.
- Separacion estricta entre datos operativos (SIIGO) y conocimiento (RAG).
- Prompt del agente con reglas anti-alucinacion para datos numericos.

## Endpoints SIIGO cubiertos

- `POST /auth`
- `GET /v1/accounts-payable`
- `POST /v1/test-balance-report`
- `POST /v1/test-balance-report-by-thirdparty`

## Prompts de prueba

- Muéstrame mis cuentas por pagar.
- Muéstrame el balance de prueba 2026 de la cuenta 13 a la 14 (meses 1 a 12).
- Muéstrame el balance de prueba por tercero de 11050501 a 53053502 para 2026 (meses 1 a 12).
- Mis cuentas por pagar subieron este mes, es preocupante? Analiza con datos reales y dame interpretacion financiera.
- Con base en mis cuentas por pagar actuales, que acciones recomiendas para mejorar flujo de caja?
- Que es el IVA?
- Que significa la cuenta 2408?
- Segun buenas practicas, cuando un aumento en cuentas por pagar es normal?
