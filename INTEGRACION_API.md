
# 🌐 Integración de API de RbxServers

## 📍 URL Actual del Bot

**URL Base:** `https://workspace-paysencharlee.replit.dev`

## 🔑 Configuración de API Key

Para acceder a la API necesitas usar la siguiente API key:
```
rbxservers_webhook_secret_2024
```

## 📊 Endpoints Disponibles

### 1. **Autenticación**
```http
POST /api/authenticate
Content-Type: application/json

{
  "secret": "rbxservers_webhook_secret_2024"
}
```

### 2. **Usuarios Verificados**
```http
GET /api/verified-users
Authorization: Bearer rbxservers_webhook_secret_2024
```

**Respuesta:**
```json
{
  "status": "success",
  "total_verified": 40,
  "users": [
    {
      "discord_id": "123456789",
      "roblox_username": "ejemplo",
      "verified_at": 1736575641,
      "expires_in_hours": 720
    }
  ]
}
```

### 3. **Estadísticas de Usuarios**
```http
GET /api/user-stats
Authorization: Bearer rbxservers_webhook_secret_2024
```

### 4. **Estadísticas de Servidores**
```http
GET /api/server-stats
Authorization: Bearer rbxservers_webhook_secret_2024
```

### 5. **Estado del Bot**
```http
GET /api/bot-status
Authorization: Bearer rbxservers_webhook_secret_2024
```

### 6. **Detalles de Usuario Específico**
```http
GET /api/user-details/{user_id}
Authorization: Bearer rbxservers_webhook_secret_2024
```

### 7. **Actividad Reciente**
```http
GET /api/recent-activity
Authorization: Bearer rbxservers_webhook_secret_2024
```

## 💻 Ejemplos de Integración

### JavaScript (Frontend)
```javascript
const API_BASE_URL = 'https://workspace-paysencharlee.replit.dev';
const API_KEY = 'rbxservers_webhook_secret_2024';

// Obtener usuarios verificados
async function getVerifiedUsers() {
    const response = await fetch(`${API_BASE_URL}/api/verified-users`, {
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        }
    });
    
    const data = await response.json();
    return data;
}

// Autenticar
async function authenticate() {
    const response = await fetch(`${API_BASE_URL}/api/authenticate`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            secret: API_KEY
        })
    });
    
    return response.json();
}
```

### Python (Backend)
```python
import requests

API_BASE_URL = "https://workspace-paysencharlee.replit.dev"
API_KEY = "rbxservers_webhook_secret_2024"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Obtener usuarios verificados
def get_verified_users():
    response = requests.get(f"{API_BASE_URL}/api/verified-users", headers=headers)
    return response.json()

# Obtener estadísticas
def get_user_stats():
    response = requests.get(f"{API_BASE_URL}/api/user-stats", headers=headers)
    return response.json()

# Obtener estado del bot
def get_bot_status():
    response = requests.get(f"{API_BASE_URL}/api/bot-status", headers=headers)
    return response.json()
```

### PHP
```php
<?php
$api_base_url = "https://workspace-paysencharlee.replit.dev";
$api_key = "rbxservers_webhook_secret_2024";

$headers = [
    "Authorization: Bearer " . $api_key,
    "Content-Type: application/json"
];

function getVerifiedUsers() {
    global $api_base_url, $headers;
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $api_base_url . "/api/verified-users");
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    
    $response = curl_exec($ch);
    curl_close($ch);
    
    return json_decode($response, true);
}
?>
```

## 🛡️ Seguridad

- **API Key:** Mantén la API key segura y no la expongas en el frontend
- **HTTPS:** Todas las peticiones deben usar HTTPS
- **Rate Limiting:** Respeta los límites de peticiones para evitar bloqueos
- **CORS:** La API permite peticiones desde cualquier origen

## 📱 Página Web de Ejemplo

Ya tienes disponible una página web de ejemplo en:
- Archivo: `ejemplo_uso_api.html`
- Solo necesitas cambiar la URL en la línea 140:

```javascript
const API_BASE_URL = 'https://workspace-paysencharlee.replit.dev';
```

## 🔧 Configuración Rápida

1. **Descarga** el archivo `ejemplo_uso_api.html`
2. **Cambia** la URL por la actual: `https://workspace-paysencharlee.replit.dev`
3. **Abre** el archivo en tu navegador
4. **Ingresa** la API key: `rbxservers_webhook_secret_2024`
5. **¡Ya puedes acceder** a todos los datos del bot!

## 🌟 Funcionalidades Disponibles

- ✅ **Usuarios verificados** con detalles completos
- 📊 **Estadísticas en tiempo real** del bot
- 🎮 **Estado de servidores VIP** y juegos
- 🔍 **Búsqueda de usuarios** específicos
- 📈 **Actividad reciente** del sistema
- 🤖 **Estado de conexión** del bot

## 📞 Soporte

Si necesitas ayuda con la integración:
- Revisa los logs del bot en Replit
- Verifica que la URL sea correcta
- Asegúrate de usar la API key correcta
- Contacta al desarrollador: hesiz

## 🔄 Actualizaciones

La URL puede cambiar si se reinicia el proyecto de Replit. Siempre verifica en los logs la URL actual:
```
🔗 Server accessible at: https://workspace-paysencharlee.replit.dev
```

---

**Desarrollado con ❤️ por hesiz para la comunidad de RbxServers**
