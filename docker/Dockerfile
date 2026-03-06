FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY openmemo/ openmemo/

RUN pip install --no-cache-dir ".[server]"

EXPOSE 8080

CMD ["python", "-m", "openmemo.api.rest_server"]
