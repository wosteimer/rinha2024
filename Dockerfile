FROM python:3.12.2-bookworm as builder

ENV PATH="/root/.local/bin:$PATH" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache 

WORKDIR /usr/app

COPY pyproject.toml poetry.lock ./

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root


FROM python:3.12.2-slim-bookworm as runtime

ENV VIRTUAL_ENV=/usr/app/.venv \
    PATH="/usr/app/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY src/ .

EXPOSE 8000

ENTRYPOINT ["uvicorn", "rinha2024.app:app", "--http=httptools", "--loop=uvloop", "--no-access-log", "--host=0.0.0.0"]
