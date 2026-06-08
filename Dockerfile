FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["python scripts/init_db.py && exec gunicorn api.app:app --bind 0.0.0.0:${PORT:-8000}"]