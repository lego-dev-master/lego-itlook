FROM python:3.11-slim

# Evita que Python escriba .pyc y fuerce logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema para compilar psycopg2 y Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependencias de Python primero (mejor cache de capas)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn==21.2.0

# Copia el resto del código
COPY . .

EXPOSE 5000

# En producción se sirve con Gunicorn (ver docker-compose.prod.yml)
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000", "--timeout", "120", "wsgi:app"]
