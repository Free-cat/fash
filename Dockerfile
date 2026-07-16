FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/data/storage

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY bot/ bot/
COPY assets/ assets/

EXPOSE 8080

CMD ["python", "-m", "bot.main"]
