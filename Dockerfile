
# Usar Python 3.11 como base con imagen multi-arquitectura
FROM python:3.11-slim

# Establecer variables de entorno para evitar prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Instalar dependencias del sistema con manejo robusto de errores
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    unzip \
    curl \
    xvfb \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libnss3 \
    libgtk-3-0 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Instalar Google Chrome de forma más robusta
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Instalar ChromeDriver con detección automática de versión
RUN CHROME_VERSION=$(google-chrome --version | cut -d " " -f3 | cut -d "." -f1) \
    && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}") \
    && wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

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
RUN chmod +x /app/docker-entrypoint.sh

# Comando para ejecutar la aplicación
ENTRYPOINT ["/app/docker-entrypoint.sh"]
