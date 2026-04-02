# syntax=docker/dockerfile:1

FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends binutils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml entry_point.py ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e .

COPY build_executable.sh ./
RUN chmod +x build_executable.sh && ./build_executable.sh

FROM debian:bookworm-slim AS runtime

COPY --from=builder /app/dist/starrocks-br /usr/local/bin/starrocks-br

ENTRYPOINT ["/usr/local/bin/starrocks-br"]
CMD ["--help"]
