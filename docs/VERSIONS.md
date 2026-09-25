# Versions

Recorded for the Gemini-only model setup.

| Component | Version |
|---|---|
| Python | 3.12 |
| PydanticAI | 2.61.0 |
| FastAPI | 0.115+ (lockfile) |
| SQLAlchemy | 2.1.6 |
| Postgres image | pgvector/pgvector:pg16 |
| Node | 22 |
| LLM | Google Gemini via `google-gla:gemini-2.5-flash` |
| API key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |

Every agent model string defaults to `google-gla:gemini-2.5-flash`. No OpenAI or Anthropic model is configured. Embeddings default to a local 384-dimension hash embedder so tests stay offline. Set `EMBEDDER=gemini` to call Gemini's embedding API with the same key.
