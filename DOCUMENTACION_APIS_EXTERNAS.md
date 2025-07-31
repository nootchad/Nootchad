
# 🔗 APIs Externas - RbxServers Bot

Esta documentación describe las nuevas APIs diseñadas para integración externa con sitios web y aplicaciones.

## 🔐 Autenticación

Todas las APIs requieren autenticación usando el header `Authorization`:

```
Authorization: Bearer rbxservers_webhook_secret_2024
```

## 📡 Endpoints Disponibles

### 1. Solicitar Verificación Externa

**Endpoint:** `POST /api/external-verification/request`

**Descripción:** Genera un código de verificación para un usuario.

**Request Body:**
```json
{
    "discord_id": "916070251895091241",
    "roblox_username": "hesiz"
}
```

**Response Success (200):**
```json
{
    "success": true,
    "verification_code": "hesiz_2025xvip",
    "roblox_username": "hesiz",
    "discord_id": "916070251895091241",
    "instructions": "Agrega este código a tu descripción de Roblox: hesiz_2025xvip",
    "profile_url": "https://www.roblox.com/users/profile?username=hesiz",
    "expires_in_minutes": 10
}
```

**Response Error (400/403/409):**
```json
{
    "success": false,
    "error": "Usuario ya está verificado",
    "current_username": "hesiz"
}
```

### 2. Verificar Código

**Endpoint:** `POST /api/external-verification/check`

**Descripción:** Verifica si el código fue agregado a la descripción del usuario.

**Request Body:**
```json
{
    "discord_id": "916070251895091241",
    "roblox_username": "hesiz"
}
```

**Response Success (200):**
```json
{
    "success": true,
    "message": "Verificación completada exitosamente",
    "discord_id": "916070251895091241",
    "roblox_username": "hesiz",
    "verified_at": 1753918796.2251582,
    "verification_code": "hesiz_2025xvip"
}
```

**Response Error (400/404):**
```json
{
    "success": false,
    "error": "Código no encontrado en la descripción",
    "can_retry": true
}
```

### 3. Obtener Leaderboard

**Endpoint:** `GET /api/leaderboard`

**Parámetros de Query:**
- `limit` (opcional): Número máximo de usuarios (default: 50, max: 100)
- `type` (opcional): Tipo de leaderboard - "weekly" o "all_time" (default: "weekly")

**Response Success (200):**
```json
{
    "success": true,
    "leaderboard_type": "weekly",
    "leaderboard": [
        {
            "rank": 1,
            "discord_id": "916070251895091241",
            "roblox_username": "hesiz",
            "server_count": 45,
            "is_verified": true,
            "verified_at": 1753918796.2251582
        }
    ],
    "statistics": {
        "total_users_in_leaderboard": 150,
        "total_servers_tracked": 2847,
        "verified_users_count": 89,
        "average_servers_per_user": 18.98,
        "top_user_servers": 45
    },
    "metadata": {
        "limit_applied": 50,
        "generated_at": "2025-01-27T12:34:56.789123",
        "system": "rbxservers_api",
        "note": "Sin límite de servidores por usuario"
    }
}
```

### 4. Estadísticas de Economía

**Endpoint:** `GET /api/economy-stats`

**Response Success (200):**
```json
{
    "success": true,
    "economy_statistics": {
        "coins": {
            "total_users_with_coins": 89,
            "total_coins_in_circulation": 125750,
            "total_transactions": 543,
            "average_balance": 1413.48,
            "top_balances": [
                {
                    "user_id": "916070251895091241",
                    "balance": 5000,
                    "total_earned": 7500
                }
            ]
        },
        "promotional_codes": {
            "total_codes_created": 25,
            "active_codes": 12,
            "total_redemptions": 234,
            "unique_users_redeemed": 78
        },
        "shop": {
            "total_categories": 4,
            "total_items": 18,
            "items_in_stock": 15,
            "total_stock_units": 156
        }
    },
    "summary": {
        "total_economic_activity": 777,
        "active_economy_participants": 89,
        "coins_per_verified_user": 1413.48
    },
    "generated_at": "2025-01-27T12:34:56.789123"
}
```

## 🛠️ Ejemplos de Uso

### JavaScript (Navegador)

```javascript
const API_BASE_URL = 'https://workspace-paysencharlee.replit.dev';
const API_KEY = 'rbxservers_webhook_secret_2024';

// Solicitar verificación
async function requestVerification(discordId, robloxUsername) {
    const response = await fetch(`${API_BASE_URL}/api/external-verification/request`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            discord_id: discordId,
            roblox_username: robloxUsername
        })
    });
    
    return await response.json();
}

// Verificar código
async function checkVerification(discordId, robloxUsername) {
    const response = await fetch(`${API_BASE_URL}/api/external-verification/check`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            discord_id: discordId,
            roblox_username: robloxUsername
        })
    });
    
    return await response.json();
}

// Obtener leaderboard
async function getLeaderboard(limit = 10) {
    const response = await fetch(`${API_BASE_URL}/api/leaderboard?limit=${limit}`, {
        headers: {
            'Authorization': `Bearer ${API_KEY}`
        }
    });
    
    return await response.json();
}

// Obtener estadísticas de economía
async function getEconomyStats() {
    const response = await fetch(`${API_BASE_URL}/api/economy-stats`, {
        headers: {
            'Authorization': `Bearer ${API_KEY}`
        }
    });
    
    return await response.json();
}
```

### Python

```python
import requests

API_BASE_URL = "https://workspace-paysencharlee.replit.dev"
API_KEY = "rbxservers_webhook_secret_2024"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def request_verification(discord_id: str, roblox_username: str):
    response = requests.post(
        f"{API_BASE_URL}/api/external-verification/request",
        headers=headers,
        json={
            "discord_id": discord_id,
            "roblox_username": roblox_username
        }
    )
    return response.json()

def check_verification(discord_id: str, roblox_username: str):
    response = requests.post(
        f"{API_BASE_URL}/api/external-verification/check",
        headers=headers,
        json={
            "discord_id": discord_id,
            "roblox_username": roblox_username
        }
    )
    return response.json()

def get_leaderboard(limit: int = 10):
    response = requests.get(
        f"{API_BASE_URL}/api/leaderboard?limit={limit}",
        headers=headers
    )
    return response.json()

def get_economy_stats():
    response = requests.get(
        f"{API_BASE_URL}/api/economy-stats",
        headers=headers
    )
    return response.json()
```

## 🔍 Códigos de Error

| Código | Descripción |
|--------|-------------|
| 400 | Datos inválidos o faltantes |
| 401 | No autorizado (API key inválida) |
| 403 | Usuario baneado |
| 404 | Recurso no encontrado |
| 409 | Usuario ya verificado |
| 500 | Error interno del servidor |

## 🚀 Flujo de Verificación

1. **Tu web llama a** `/api/external-verification/request` con Discord ID y Roblox username
2. **El bot genera y devuelve** un código de verificación único
3. **Tu web muestra el código** y las instrucciones al usuario
4. **El usuario agrega el código** a su descripción de Roblox
5. **Tu web llama a** `/api/external-verification/check` para verificar
6. **El bot comprueba la descripción** y confirma la verificación

## 📊 Límites y Consideraciones

- **Rate Limiting:** 60 peticiones por minuto por IP
- **Timeout de verificación:** 10 minutos
- **Cache:** Las estadísticas se actualizan cada 5 minutos
- **Leaderboard:** Máximo 100 usuarios por petición
- **Sistema sin límite:** No hay límite en la cantidad de servidores por usuario

## 🔐 Seguridad

- Todas las APIs requieren autenticación con API key
- Los códigos de verificación expiran en 10 minutos
- Se registran todos los intentos de acceso
- Sistema anti-alt integrado para prevenir abusos

## 📞 Soporte

Para soporte técnico o dudas sobre la integración, contacta al equipo de desarrollo.
