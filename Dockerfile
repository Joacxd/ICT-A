FROM python:3.11.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PORT=8000

CMD sh -c "python scripts/init_db.py && gunicorn api.app:app --bind 0.0.0.0:8000 --workers 2"