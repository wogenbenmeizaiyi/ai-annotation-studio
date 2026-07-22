ARG BASE_IMAGE=ai_annotation_studio_service_deps:latest
FROM ${BASE_IMAGE} AS runtime

ENV YOLO_CONFIG_DIR=/app/.config

WORKDIR /app

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
COPY yolo26n.pt ./yolo26n.pt

RUN mkdir -p logs models/yolo_models storage/train_data runs

EXPOSE 8811

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8811"]
