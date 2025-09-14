
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

# Verificar conectividad (sin salir si falla)
log "Verificando conectividad..."
if ! curl -s --connect-timeout 10 https://discord.com > /dev/null; then
    log "WARNING: No se puede conectar a Discord, pero continuando..."
fi

# Configurar Railway específico
if [ ! -z "$RAILWAY_ENVIRONMENT" ]; then
    log "Detectado entorno Railway: $RAILWAY_ENVIRONMENT"
fi

log "Iniciando aplicación Python..."

# Ejecutar la aplicación
exec python main.py
