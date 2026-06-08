FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["/bin/sh", "-c", "python scripts/init_db.py && gunicorn api.app:app --bind 0.0.0.0:$PORT"]