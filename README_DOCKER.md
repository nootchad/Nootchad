
# RbxServers Discord Bot - Docker Setup

## Requisitos Previos

- Docker Engine 20.10+
- Docker Compose 2.0+
- Al menos 2GB de RAM disponible
- Conexión a internet estable

## Configuración Inicial

1. **Clonar el repositorio:**
```bash
git clone <tu-repositorio>
cd rbxservers-bot
```

2. **Configurar variables de entorno:**
```bash
cp .env.template .env
# Editar .env con tus valores reales
```

3. **Variables requeridas en .env:**
- `BOT_TOKEN`: Token del bot de Discord
- `COOKIE`: Cookie de Roblox (.ROBLOSECURITY)
- `CAPTCHA2`: API key de NopeCHA (opcional)
- `GEMINI_API_KEY`: API key de Google Gemini (opcional)

## Uso

### Producción
```bash
# Construir e iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f rbxservers-bot

# Detener
docker-compose down
```

### Desarrollo
```bash
# Usar override para desarrollo
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# Rebuild después de cambios
docker-compose build rbxservers-bot
```

## Comandos Útiles

```bash
# Ver estado de contenedores
docker-compose ps

# Acceder al contenedor
docker-compose exec rbxservers-bot bash

# Ver logs en tiempo real
docker-compose logs -f

# Restart solo el bot
docker-compose restart rbxservers-bot

# Limpiar volúmenes
docker-compose down -v
```

## Troubleshooting

### El bot no se conecta
- Verificar `BOT_TOKEN` en `.env`
- Revisar logs: `docker-compose logs rbxservers-bot`

### Chrome no funciona
- Verificar que tienes suficiente RAM (mínimo 2GB)
- El contenedor usa modo headless por defecto

### Problemas de permisos
- Verificar que los archivos JSON tienen permisos de escritura
- El bot corre como usuario no-root por seguridad

### Monitoreo de recursos
```bash
# Ver uso de recursos
docker stats

# Ver espacio en disco
docker system df
```

## Arquitectura

- **rbxservers-bot**: Contenedor principal con el bot
- **xvfb**: Servidor X virtual para Chrome headless
- **Volúmenes**: Persistencia de datos JSON
- **Red**: Red interna para comunicación entre contenedores

## Puertos

- `8080`: API web del bot
- `5900`: VNC (solo en modo desarrollo)
- `9222`: Chrome debugging (solo en modo desarrollo)

## Actualizaciones

```bash
# Actualizar código
git pull
docker-compose build
docker-compose up -d
```
