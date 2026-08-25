FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=intersoft.settings

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc default-libmysqlclient-dev pkg-config && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

RUN mkdir -p logs staticfiles media

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
