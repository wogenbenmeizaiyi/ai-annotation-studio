ARG BASE_IMAGE=image_detection_service_deps:latest
FROM ${BASE_IMAGE} AS runtime

WORKDIR /app

ENV PYTHONPATH=/app/api/src:/app/worker/src:/app/consumer/src:/app/core/src:/app/engine/src

COPY api ./api
COPY worker ./worker
COPY consumer ./consumer
COPY core ./core
COPY engine ./engine
RUN mkdir -p logs models

EXPOSE 7987

CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "7987"]
