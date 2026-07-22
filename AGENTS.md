# AGENTS.md

## Repository overview

This is a monorepo with three independently managed applications:

- `apps/web`: Vue 3, TypeScript, Vite, pnpm.
- `services/annotation`: Python 3.12 FastAPI annotation/training service, uv.
- `services/recognition`: Python 3.12 FastAPI/Celery recognition service, uv.
- `infra/local`: development-only PostgreSQL, RabbitMQ, Redis, and MinIO.

Read and follow the nearest nested `AGENTS.md` before changing a subproject. Nested instructions own code style and project-specific commands.

## Monorepo rules

- Keep the three dependency graphs independent. Do not move Python dependencies to a root project or move the frontend lockfile to the root.
- Never commit `.env`, `.local`, model caches, logs, virtual environments, or generated data.
- Business applications run natively for development. Do not add application containers to `infra/local/compose.yml`.
- Local infrastructure uses two PostgreSQL databases because the Python services have independent Alembic histories.
- Preserve the public ports: web 5173, annotation 8811, recognition 7987.
- Production images are built only from tracked files. Runtime model files must be mounted or downloaded explicitly.
- CI image changes must preserve immutable commit-SHA tags and the deploy-tag promotion guard.

## Root commands

```powershell
.\scripts\dev.ps1 -Profile full -Infra auto
.\scripts\infra.ps1 -Action status
.\scripts\check.ps1
```

## Pre-commit

Run `scripts/check.ps1` when changes cross project boundaries. For a single project, also follow the project-local checklist in its `AGENTS.md`.
