FROM python:3.13-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --extra prod

COPY app ./app

ENV PATH=/app/.venv/bin:$PATH

CMD [ "fastapi", "run" ]