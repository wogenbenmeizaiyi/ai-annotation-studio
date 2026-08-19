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
- Production deployment has **no container registry**: images are built on the target server from source. Do not reintroduce registry build/push jobs.

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

## PR & commit conventions

- Branch from `main`; never push to it directly
- Commit messages follow Conventional Commits (`feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`)
- Open MRs via the GitLab web UI once the pipeline is green (see "Production deployment" below for what triggers a deploy)

## Production deployment (GitLab CI, no registry)

Triggered by pushing to **`main`** on the internal GitLab (`origin`, `http://172.16.0.110:802`). The pipeline has a single `deploy:server` job running `scripts/deploy-remote.sh`; it SSHes to the production server and builds/runs everything **on the server**. There is no registry, no pushed images.

Flow (`deploy-remote.sh`):
1. Collects business connection vars (list in `VAR_DEFS`), base64-encodes each value, sends them over SSH as one blob.
2. On the server: decodes the blob, `export`s each var, `git pull`s `main`, builds the 6 business images locally, then `docker compose -f infra/server/compose.yml up -d`.
3. `infra/server/compose.yml` connects to **external** PostgreSQL/Redis/RabbitMQ/S3 (no bundled infra services) and injects env via `${VAR}` interpolation. `auth-keygen` generates JWT keys into a volume; `*-migrate` run Alembic against the external DBs.

Key facts an agent must not get wrong:
- **CI only triggers if `changes.paths` matches** (`.gitlab-ci.yml`). Added `infra/**` and `scripts/deploy-remote.sh` — anything else touched (e.g. README) will NOT redeploy.
- Vars come from GitLab project variables by **bare name** (root `.env` is the source of truth for names; shared keys like `POSTGRES_USER` have no prefix, only per-service DB names get `AUTH_`/`ANNOTATION_`/`RECOGNITION_` prefixes). `deploy-remote.sh` falls back to code defaults when a var is missing or arrives as literal `$NAME`.
- Values are base64-per-line and decoded on the server — do not `eval` the raw blob.
- `infra/server/nginx.conf` proxies `/api/*` to compose service names (`auth`, `annotation-api`, `recognition-api`). It must NOT reference removed services (e.g. `minio`) or nginx dies with `host not found in upstream` and the web container crash-loops → blank white page.
- The web container serves on `:7280`; the standalone old frontend container (`ai-annotation-studio-web-web-1`, project `ai-annotation-studio-web`) also used `:7280` and must be stopped first.
- `S3_PUBLIC_ENDPOINT` must be browser-reachable (external S3/object storage); image display depends on it.
- After deployment, create the super admin manually: `cd $DEPLOY_PATH && bash scripts/server-local.sh create-admin` (use ASCII-only username; Chinese input over SSH fails with `UnicodeEncodeError`).
