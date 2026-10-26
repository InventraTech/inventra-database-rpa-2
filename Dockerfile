FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

RUN useradd --create-home rpa
USER rpa

# As credenciais entram por variáveis de ambiente (--env-file .env), nunca na imagem.
ENTRYPOINT ["rpa-pre-lista"]
