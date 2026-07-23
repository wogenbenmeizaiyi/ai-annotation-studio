ARG BASE_IMAGE=ai_annotation_studio_auth_deps:latest
FROM ${BASE_IMAGE} AS runtime

WORKDIR /app
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
RUN mkdir -p /app/.local/keys

EXPOSE 8787
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
