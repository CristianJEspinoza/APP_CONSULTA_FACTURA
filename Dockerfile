# Usa una imagen oficial ligera de Python 3.11 (recomendado para evitar problemas con pydantic-core)
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Establece variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instala las dependencias del sistema necesarias
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia primero requirements.txt para aprovechar el caché de capas de Docker
COPY requirements.txt /app/

# Instala las dependencias de Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia todo el código fuente del proyecto al directorio de trabajo
COPY . /app/

# Expone el puerto 8000 para acceder a la API
EXPOSE 8000

# Comando para ejecutar la aplicación con Uvicorn en modo producción
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
