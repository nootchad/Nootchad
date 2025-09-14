
#!/bin/bash
set -e

# Función para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Iniciando RbxServers Discord Bot..."

# Verificar variables de entorno críticas
if [ -z "$BOT_TOKEN" ]; then
    log "ERROR: BOT_TOKEN no está configurado"
    exit 1
fi

log "Variables de entorno verificadas"

# Crear directorios necesarios si no existen
mkdir -p /app/Serversdb
mkdir -p /app/RbxBotLogic
mkdir -p /app/attached_assets
mkdir -p /app/Commands

log "Directorios verificados"

# Verificar que Chrome y ChromeDriver estén instalados
if ! command -v google-chrome &> /dev/null; then
    log "ERROR: Google Chrome no está instalado"
    exit 1
fi

if ! command -v chromedriver &> /dev/null; then
    log "ERROR: ChromeDriver no está instalado"
    exit 1
fi

log "Chrome y ChromeDriver verificados"

# Verificar conectividad con Discord
log "Verificando conectividad..."
if ! curl -s --connect-timeout 10 https://discord.com > /dev/null; then
    log "WARNING: No se puede conectar a Discord, pero continuando..."
fi

# Esperar a que Xvfb esté listo si está siendo usado
if [ "$DISPLAY" = ":99" ]; then
    log "Esperando a que Xvfb esté listo..."
    sleep 5
fi

log "Iniciando aplicación Python..."

# Ejecutar la aplicación
exec python main.py
