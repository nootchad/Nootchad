
# API del Bot RbxServers

## Autenticación

Todas las solicitudes requieren un Bearer token en el header `Authorization`:

```
Authorization: Bearer rbxservers_admin
```

### API Keys disponibles:
- `rbxservers_admin`: Acceso completo (admin)
- `rbxservers_user`: Acceso básico (usuario)

## Endpoints

### Información General

#### `GET /`
Información básica de la API.

#### `GET /stats`
Estadísticas generales del bot.

**Respuesta:**
```json
{
  "usuarios": {
    "verificados": 41,
    "baneados": 0,
    "con_advertencias": 0
  },
  "servidores": {
    "total_enlaces": 1250,
    "total_juegos": 45
  },
  "bot_uptime": "2025-01-11T00:54:58.000Z"
}
```

### Verificación

#### `GET /verification/status/{discord_id}`
Obtener estado de verificación de un usuario.

#### `POST /verification/start`
Iniciar proceso de verificación.

**Body:**
```json
{
  "discord_id": "123456789",
  "roblox_username": "MiUsuario"
}
```

#### `POST /verification/confirm/{discord_id}`
Confirmar verificación automáticamente.

### Scraping

#### `POST /scraping/scrape`
Realizar scraping de servidores VIP.

**Body:**
```json
{
  "game_id": "2753915549",
  "user_id": "123456789"
}
```

#### `GET /scraping/search?query=blox+fruits`
Buscar juegos por nombre.

### Servidores

#### `GET /servers/user/{user_id}`
Obtener todos los servidores de un usuario.

#### `GET /servers/random/{user_id}/{game_id}`
Obtener servidor aleatorio para un juego.

### Usuarios

#### `GET /users/{user_id}/favorites`
Obtener juegos favoritos del usuario.

#### `POST /users/{user_id}/favorites/{game_id}`
Agregar/quitar juego de favoritos.

#### `GET /users/{user_id}/history`
Obtener historial de uso del usuario.

### Marketplace

#### `GET /marketplace/listings`
Obtener todas las listings del marketplace.

#### `POST /marketplace/listings`
Crear nueva listing.

**Body:**
```json
{
  "seller_id": "123456789",
  "title": "Servidor VIP Premium",
  "description": "Servidor con muchas ventajas",
  "price": 100,
  "item_type": "vip_server",
  "contact_info": "discord: usuario#1234"
}
```

### Monedas

#### `GET /coins/{user_id}/balance`
Obtener balance de monedas del usuario.

#### `POST /coins/transaction` (Solo Admin)
Crear transacción de monedas.

**Body:**
```json
{
  "user_id": "123456789",
  "amount": 50,
  "reason": "Premio por evento"
}
```

### Imágenes

#### `POST /images/generate`
Generar imagen usando IA.

**Body:**
```json
{
  "prompt": "Un robot futurista",
  "style": "realistic"
}
```

### Admin (Solo administradores)

#### `GET /admin/users`
Obtener información de todos los usuarios.

#### `POST /admin/user/{discord_id}/ban`
Banear usuario.

## Códigos de Error

- `400`: Bad Request - Datos inválidos
- `403`: Forbidden - Sin permisos o usuario baneado
- `404`: Not Found - Recurso no encontrado
- `429`: Too Many Requests - Cooldown activo
- `500`: Internal Server Error - Error del servidor
- `503`: Service Unavailable - Servicio no disponible

## Ejemplos de Uso

### JavaScript (Fetch)

```javascript
// Obtener estadísticas
const response = await fetch('https://tu-bot.replit.dev/stats', {
  headers: {
    'Authorization': 'Bearer rbxservers_user'
  }
});
const stats = await response.json();

// Scraping
const scrapeResponse = await fetch('https://tu-bot.replit.dev/scraping/scrape', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer rbxservers_user',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    game_id: '2753915549',
    user_id: '123456789'
  })
});
```

### Python (requests)

```python
import requests

headers = {'Authorization': 'Bearer rbxservers_user'}

# Obtener servidores de usuario
response = requests.get(
    'https://tu-bot.replit.dev/servers/user/123456789',
    headers=headers
)
servers = response.json()

# Obtener servidor aleatorio
response = requests.get(
    'https://tu-bot.replit.dev/servers/random/123456789/2753915549',
    headers=headers
)
random_server = response.json()
```

## URL de la API

Una vez desplegado en Replit, la API estará disponible en:
`https://[tu-repl-name].[tu-username].replit.dev`

El puerto 5000 se mapea automáticamente a los puertos 80/443 en Replit.
