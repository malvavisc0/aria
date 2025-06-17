FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip uv

COPY pyproject.toml ./
COPY aria ./aria

RUN uv pip install . --system

RUN mkdir -p /app/aria/uploads

EXPOSE 8000

CMD ["/usr/bin/bash", "-c", "aria", "run"]
