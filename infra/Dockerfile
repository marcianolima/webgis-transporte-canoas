FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home transporte
COPY pipeline /app/pipeline
COPY backend /app/backend
COPY public/data/stop-inventory.json /app/public/data/stop-inventory.json
COPY public/data/route-shapes.geojson /app/public/data/route-shapes.geojson
COPY public/data/stops.geojson /app/public/data/stops.geojson
COPY public/data/bairros-oficiais.geojson /app/public/data/bairros-oficiais.geojson
COPY infra/sql /app/infra/sql
RUN mkdir -p /app/var/gobus && chown -R transporte:transporte /app/var
ENV PYTHONPATH=/app/pipeline:/app PYTHONUNBUFFERED=1
USER transporte
CMD ["uvicorn","backend.app:create_app","--factory","--host","0.0.0.0","--port","8000"]
