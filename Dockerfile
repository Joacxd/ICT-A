FROM python:3.11.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "python scripts/init_db.py && python -m gunicorn api.app:app --bind 0.0.0.0:$(printenv PORT)"]