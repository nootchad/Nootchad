
# Usar Python 3.11 como base con imagen multi-arquitectura
FROM python:3.11-slim

# Establecer variables de entorno para evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar dependencias básicas del sistema
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    build-essential \
    dos2unix \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Establecer directorio de trabajo
WORKDIR /app

# Crear usuario no-root para mayor seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Copiar requirements.txt primero para aprovechar el cache de Docker
COPY --chown=app:app requirements.txt .

# Actualizar pip e instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY --chown=app:app . .

# Crear directorios necesarios con permisos correctos
RUN mkdir -p Commands RbxBotLogic Serversdb attached_assets \
    && chown -R app:app /app \
    && chmod -R 755 /app

# Cambiar al usuario no-root
USER app

# Configurar variables de entorno adicionales
ENV PATH="/home/app/.local/bin:${PATH}"
ENV HOME="/home/app"

# Exponer el puerto para el servidor web interno
EXPOSE 8080

# Healthcheck para verificar que la aplicación esté funcionando
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Copiar y configurar script de entrada
COPY --chown=app:app docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh \
    && dos2unix /app/docker-entrypoint.sh || true

# Comando para ejecutar la aplicación
ENTRYPOINT ["/app/docker-entrypoint.sh"]
