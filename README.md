# Suppport Assistant

AI customer-support API. Authenticated users chat with a RAG-powered support
assistant that answers from a knowledge base, and manage support tickets.
Transactional email is sent via Resend.

## Features

- **Auth** — register/login/logout, JWT access + refresh tokens, email
  verification, password reset, per-endpoint rate limiting, `create-admin` CLI.
- **Users** — profile read/update and password change.
- **Tickets** — create, list (paginated), update status/priority/assignee, delete,
  with ownership/assignee/admin visibility rules.
- **Conversations** — chat threads and messages; posting a message runs the agent.
- **Knowledge base (RAG)** — ingest text or PDF, chunk + embed with OpenAI, store
  vectors in **pgvector** (same Postgres — no separate vector DB), cosine search.
- **Agent** — LangChain v1 `create_agent` with a knowledge-base retrieval tool and a
  create-ticket tool; replies persist their cited sources.
- **Notifications** — Resend emails (welcome, verification, password reset,
  ticket created, ticket status changed); dry-run mode when no API key is set.

## Tech stack

FastAPI · SQLModel (async) · PostgreSQL 18 + pgvector · Alembic · asyncpg ·
LangChain v1 · OpenAI · Resend · pydantic-settings · slowapi · uv

## Project layout

```
src/suppport_assistant/
  core/           config, errors, security, logging, middleware, pagination, ratelimit
  db/             async engine/session
  modules/
    auth/ users/ tickets/ conversations/ knowledge_base/ agents/ notifications/
alembic/          migrations (async env)
```

Each feature is a self-contained module with `models.py`, `schemas.py`, `service.py`,
and `router.py`.

## Setup

```bash
uv sync                              # install dependencies
cp .env.example .env                 # then fill in real values
alembic upgrade head                 # apply database migrations
uv run suppport-assistant            # start the API (http://localhost:8000/docs)
```

Create an admin user (needed for knowledge-base ingestion):

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=secret123 uv run suppport-assistant create-admin
```

## Docker

```bash
docker compose up --build            # Postgres (pgvector/pgvector:pg18) + API
```

The app container runs `alembic upgrade head` before starting.

## Database

PostgreSQL 18 with the `pgvector` extension (vectors live in the same database).
Schema is managed with Alembic; the `vector` extension is enabled by the initial
migration.

```bash
alembic upgrade head                            # apply migrations
alembic revision --autogenerate -m "message"    # create a migration
alembic check                                   # verify models and DB are in sync
```

## API

All routes are prefixed with `/api/v1` (except the probes). Authenticate via
`/api/v1/auth/login` and send `Authorization: Bearer <access_token>`.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | Create an account (emails a verification token) |
| POST | `/auth/login` | Issue access + refresh tokens |
| POST | `/auth/refresh` | Exchange a refresh token |
| POST | `/auth/verify-email` | Verify an email with a token |
| POST | `/auth/forgot-password` | Email a reset token (always 202) |
| POST | `/auth/reset-password` | Reset a password with a token |
| POST | `/auth/logout` | Invalidate the current session |
| GET/PATCH | `/users/me` | Read / update the current profile |
| POST | `/users/me/change-password` | Change the password |
| GET/POST | `/tickets` | List (paginated) / create tickets |
| GET/PATCH/DELETE | `/tickets/{id}` | Read / update / delete a ticket |
| GET/POST | `/conversations` | List / create chat threads |
| GET/DELETE | `/conversations/{id}` | Read (with messages) / delete a thread |
| POST | `/conversations/{id}/messages` | Send a message; returns the agent reply |
| GET/POST | `/knowledge/documents` | List / ingest documents (admin) |
| POST | `/knowledge/documents/upload` | Ingest a PDF (admin) |
| DELETE | `/knowledge/documents/{id}` | Delete a document (admin) |
| POST | `/knowledge/search` | Vector search preview |
| GET | `/health`, `/ready` | Liveness / readiness probes |

## Evaluation (accuracy & hallucination)

The assistant was assessed on **40 mixed questions** against the two sample policy PDFs
(`docs/`), spanning three buckets: **correct** (answerable from the documents),
**partial** (only partly covered), and **irrelevant** (not in the documents). Answers were
produced by the agent and verified **by hand** against the corpus (no LLM judge).

| bucket | n | accurate | grounded (no hallucination) |
| --- | --- | --- | --- |
| correct | 15 | 15/15 | 15/15 |
| partial | 12 | 12/12 | 11/12 |
| irrelevant | 13 | 13/13 | 13/13 |
| **total** | **40** | **40/40 (100%)** | **39/40 (97.5%)** |

- Answerable questions match the PDFs exactly (14-day return window, 5% student discount,
  up to 25% combined discount, 5–10 business-day refunds, etc.).
- Questions not covered by the documents are correctly declined — *"I could not find that
  information in the documents."* — rather than inventing a policy, phone number, CEO,
  shipping region, payment method, or store location.
- One partial answer (manufacturer's warranty-claim process) added a minor procedural step
  inferred from the return flow; that is the only non-verbatim detail and it is not a
  fabricated policy fact.

Guardrails behind this: the agent answers **only** from retrieved passages, never states
what the policy *does not* allow, cites the source chunk inline (`source: chunk N`), and
`sources` also lists the chunk references. A `RAG_MAX_DISTANCE` cutoff (default `0.85`)
drops clearly-unrelated passages.

## Development

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy src              # type check
```

## Environment

See `.env.example` for the full list. Key variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://…` (Postgres + pgvector) |
| `SECRET_KEY` | JWT signing + action-token salt |
| `OPENAI_API_KEY` | Chat + embeddings |
| `RESEND_API_KEY`, `EMAIL_FROM` | Transactional email (dry-run if unset) |
| `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `RAG_TOP_K` | RAG tuning |
