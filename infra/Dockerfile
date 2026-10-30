FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home transporte
COPY pipeline /app/pipeline
COPY backend /app/backend
COPY infra/sql /app/infra/sql
RUN mkdir -p /app/var && chown -R transporte:transporte /app/var
ENV PYTHONPATH=/app/pipeline:/app PYTHONUNBUFFERED=1
USER transporte
CMD ["uvicorn","backend.app:create_app","--factory","--host","0.0.0.0","--port","8000"]
