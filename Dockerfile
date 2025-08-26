# Dockerfile para APIs Python con FastAPI

# Usar imagen base oficial de Python
FROM python:3.9-slim

# Establecer variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root por seguridad
RUN useradd --create-home --shell /bin/bash app

# Copiar archivo de requerimientos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar el código de la aplicación
COPY . .


# Cambiar permisos y usuario
RUN chown -R app:app /app
USER app

# Exponer el puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://0.0.0.0:8000/kms/objects || exit 1

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]