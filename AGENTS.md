# AGENTS.md

## Repository overview

Monorepo with four independently managed applications plus local infrastructure:

- `apps/web`: Vue 3, TypeScript, Vite, pnpm.
- `services/auth`: Python 3.12 FastAPI login/session/user-approval service, uv. No nested `AGENTS.md` — see `services/auth/README.md`.
- `services/annotation`: Python 3.12 FastAPI annotation/training/SAM3 service, uv.
- `services/recognition`: Python 3.12 FastAPI/Celery recognition service, uv.
- `infra/local`: development-only PostgreSQL, RabbitMQ, Redis, and MinIO.

Read and follow the nearest nested `AGENTS.md` before changing a subproject (web, annotation, recognition). Nested instructions own code style and project-specific commands. `README.md` is the canonical setup and env-reference doc.

## Monorepo rules

- Keep the four dependency graphs independent. Do not move Python dependencies to a root project or move the frontend lockfile to the root.
- Never commit `.env`, `.local`, model caches, logs, virtual environments, or generated data.
- Business applications run natively for development. Do not add application containers to `infra/local/compose.yml`.
- Local infrastructure runs three PostgreSQL databases (`annotation_studio_local`, `recognition_service_local`, `auth_service_local`) because each Python service has an independent Alembic history.
- Preserve the public ports: web 5173, auth 8787, annotation 8811, recognition 7987.
- Production images are built only from tracked files. Runtime model files must be mounted or downloaded explicitly (models live in `services/{annotation,recognition}/models/`).
- CI image changes must preserve immutable commit-SHA tags and the deploy-tag promotion guard.

## Root commands

```powershell
.\scripts\dev.ps1 -Profile full -Infra auto   # Profile: web|api|full; Infra: auto|external|local
.\scripts\infra.ps1 -Action status            # Actions: up|down|status|reset
.\scripts\check.ps1
.\scripts\export-images.ps1 -ImageSet business -Tag offline -Build
```

`dev.ps1 -Infra local` auto-generates infra credentials into `.local/infra.env` and overwrites the per-service `.env` DB/broker/S3 values; business keys (`AGENT_API_KEY`, `QWEN_API_KEY`) still come from the per-service `.env`, which are read per service, never from the repo root. `check.ps1` runs web type-check; Python `compileall` + `alembic heads` for all three services; ruff + pytest for auth and recognition only; Compose validation; and a Git secrets scan.

## Operational gotchas

- The first super admin can only be created via CLI, not registration (registration creates pending users): in `services/auth`, `$env:APP_ENV_FILE` set, then `uv run python -m scripts.create_super_admin` (see `services/auth/README.md`).
- YOLO/SAM model files are never fetched from Git; place them in `services/annotation/models/` and `services/recognition/models/`.
- After editing any `.env`, fully stop and restart `dev.ps1` (Ctrl+C) — changes are not hot-reloaded.

## Pre-commit

Run `scripts/check.ps1` when changes cross project boundaries. For a single project, follow the project-local checklist in its `AGENTS.md`.
