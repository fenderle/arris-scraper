# syntax=docker/dockerfile:1

# 1) Base image
FROM python:3.13-slim

# 2) Install system deps needed by Poetry & any build requirements
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      build-essential \
 && rm -rf /var/lib/apt/lists/*

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