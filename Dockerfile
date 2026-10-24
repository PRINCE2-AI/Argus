# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

LABEL org.opencontainers.image.title="Argus" \
      org.opencontainers.image.description="A small, inspectable agent harness with explicit safety boundaries." \
      org.opencontainers.image.source="https://github.com/PRINCE2-AI/Argus" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /opt/argus
COPY pyproject.toml README.md LICENSE ./
COPY argus ./argus
RUN pip install . \
    && useradd --create-home --uid 10001 argus \
    && mkdir -p /workspace \
    && chown argus:argus /workspace

WORKDIR /workspace
USER argus

ENTRYPOINT ["argus"]
CMD ["--help"]
