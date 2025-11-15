FROM python:3.13-slim

WORKDIR /app

COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt

COPY src/core ./src/core
COPY src/server ./src/server

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "src.server.main:app", "--host", "0.0.0.0", "--port", "8000"]

