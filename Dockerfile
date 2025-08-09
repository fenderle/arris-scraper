# syntax=docker/dockerfile:1

# 1) Base image
FROM python:3.13-slim

# 2) Install system deps needed by Poetry & any build requirements
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      build-essential \
 && rm -rf /var/lib/apt/lists/*

# Add Ookla Speedtest CLI (no repo; download tarball)
ARG OOKLA_VERSION=1.2.0
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) OOKLA_ARCH="x86_64" ;; \
      arm64) OOKLA_ARCH="aarch64" ;; \
      i386)  OOKLA_ARCH="i386" ;; \
      armhf) OOKLA_ARCH="armhf" ;; \
      *) echo "unsupported arch: $arch" && exit 1 ;; \
    esac; \
    url="https://install.speedtest.net/app/cli/ookla-speedtest-${OOKLA_VERSION}-linux-${OOKLA_ARCH}.tgz"; \
    echo "Fetching $url"; \
    curl -fsSL "$url" -o /tmp/speedtest.tgz; \
    tar -xzf /tmp/speedtest.tgz -C /usr/local/bin speedtest; \
    rm -f /tmp/speedtest.tgz; \
    /usr/local/bin/speedtest --version

    # 3) Install Poetry
ENV POETRY_VERSION=2.1.3 \
    POETRY_HOME=/opt/poetry \
    PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 - \
 && /opt/poetry/bin/poetry --version

 # 2) Now export it for later layers
ENV POETRY_HOME=/opt/poetry \
    PATH="$POETRY_HOME/bin:$PATH"

# 4) Copy only lockfiles & install dependencies (no dev)
WORKDIR /app
COPY arris_scraper /app/arris_scraper
COPY pyproject.toml poetry.lock* entrypoint.sh /app/
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi

# 5) Copy the rest of your code
COPY . /app

# 6) Make sure entrypoint.sh is executable
RUN chmod +x /app/entrypoint.sh

# 7) Default DELAY (seconds), can be overridden at runtime:
ENV DELAY=300

# 8) Run your scraper loop
ENTRYPOINT ["./entrypoint.sh"]