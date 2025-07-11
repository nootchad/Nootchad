# API del Bot RbxServers

## 🔐 Autenticación

La API utiliza autenticación mediante Bearer tokens. Para acceder a los endpoints, debes incluir tu API key en el header `Authorization`.

### API Keys Disponibles:
- **Usuario**: `rbxservers_user` - Acceso a endpoints básicos de lectura y funcionalidades del bot
- **Admin**: `rbxservers_admin` - Acceso completo incluyendo administración de usuarios y configuración

### Headers Requeridos:
```
Authorization: Bearer rbxservers_user
Content-Type: application/json
Accept: application/json
```

### Ejemplo de Request:
```bash
curl -H "Authorization: Bearer rbxservers_user" \
     -H "Content-Type: application/json" \
     https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000/stats
```

### Niveles de Acceso:
- **Usuario** (`rbxservers_user`): Acceso a endpoints básicos de lectura y funcionalidades del bot
- **Admin** (`rbxservers_admin`): Acceso completo incluyendo administración de usuarios y configuración

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

## Dashboard con Animaciones en Tiempo Real

### Propuesta de Dashboard Interactivo

Queremos crear un dashboard web moderno con animaciones en tiempo real que muestre:

- **Últimos usuarios que han usado el bot** (en tiempo real)
- **Información detallada de cada usuario** (nombre, ID, Roblox username)
- **Servidores donde usaron el bot** (juegos, enlaces VIP)
- **Estadísticas en vivo** con gráficos animados
- **Mapa de actividad global** de usuarios
- **Timeline de eventos recientes**

### API Endpoints para Dashboard

#### `GET /dashboard/recent-activity`
Obtener actividad reciente de usuarios (últimos 50 eventos).

**URL Base:** `https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev`

**Ejemplo de respuesta:**
```json
{
  "recent_activity": [
    {
      "user_id": "123456789",
      "discord_name": "usuario#1234",
      "roblox_username": "RobloxUser123",
      "action": "scrape_servers",
      "game_id": "2753915549",
      "game_name": "Blox Fruits",
      "timestamp": "2025-01-11T01:30:45.123Z",
      "server_link": "https://www.roblox.com/games/...",
      "location": "España"
    }
  ],
  "total_events": 147,
  "live_users": 12
}
```

#### `GET /dashboard/live-stats`
Estadísticas en tiempo real para animaciones.

**Respuesta:**
```json
{
  "stats": {
    "users_online": 23,
    "active_scrapers": 5,
    "servers_found_today": 1250,
    "total_verified_users": 41,
    "popular_games": [
      {
        "game_id": "2753915549",
        "name": "Blox Fruits",
        "usage_count": 89,
        "trend": "up"
      }
    ]
  },
  "charts_data": {
    "hourly_usage": [12, 18, 25, 31, 28, 45, 52],
    "user_growth": [100, 120, 150, 180, 210, 250, 280],
    "server_discoveries": [50, 75, 120, 95, 140, 180, 200]
  }
}
```

#### `GET /dashboard/user-map`
Datos para mapa mundial de usuarios activos.

**Respuesta:**
```json
{
  "user_locations": [
    {
      "country": "España",
      "users_count": 8,
      "coordinates": [40.4168, -3.7038],
      "recent_activity": 15
    },
    {
      "country": "México",
      "users_count": 12,
      "coordinates": [19.4326, -99.1332],
      "recent_activity": 23
    }
  ],
  "total_countries": 25,
  "most_active_country": "México"
}
```

#### `WebSocket /dashboard/live-feed`
Conexión WebSocket para actualizaciones en tiempo real.

**Eventos que recibirás:**
```javascript
// Nuevo usuario usando el bot
{
  "type": "user_activity",
  "data": {
    "user_id": "123456789",
    "action": "scrape_servers",
    "timestamp": "2025-01-11T01:30:45.123Z",
    "game_name": "Blox Fruits"
  }
}

// Estadísticas actualizadas
{
  "type": "stats_update",
  "data": {
    "users_online": 24,
    "servers_found_today": 1251
  }
}

// Nueva verificación de usuario
{
  "type": "new_verification",
  "data": {
    "discord_name": "newuser#5678",
    "roblox_username": "NewRobloxUser",
    "timestamp": "2025-01-11T01:31:00.000Z"
  }
}
```

### Implementación Frontend Sugerida

#### HTML Dashboard Básico
```html
<!DOCTYPE html>
<html>
<head>
    <title>RbxServers Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
</head>
<body>
    <div id="dashboard">
        <div class="stats-grid">
            <div class="stat-card" id="users-online">
                <h3>Usuarios Online</h3>
                <span class="number">0</span>
            </div>
            <div class="stat-card" id="servers-found">
                <h3>Servidores Encontrados</h3>
                <span class="number">0</span>
            </div>
        </div>

        <div class="activity-feed" id="recent-activity">
            <!-- Actividad reciente aquí -->
        </div>

        <canvas id="usage-chart"></canvas>
        <div id="world-map"></div>
    </div>
</body>
</html>
```

#### JavaScript para Animaciones
```javascript
// Conectar a la API
const API_BASE = 'https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev';
const headers = {
    'Authorization': 'Bearer rbxservers_user'
};

// Conectar WebSocket para tiempo real
const ws = new WebSocket('wss://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev/dashboard/live-feed');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);

    if (data.type === 'user_activity') {
        addActivityToFeed(data.data);
        animateStatsUpdate();
    }
};

// Animar números con GSAP
function animateNumber(element, newValue) {
    gsap.to(element, {
        textContent: newValue,
        duration: 1,
        ease: "power2.out",
        snap: { textContent: 1 }
    });
}

// Agregar actividad reciente con animación
function addActivityToFeed(activity) {
    const feed = document.getElementById('recent-activity');
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <div class="user-info">
            <strong>${activity.discord_name}</strong>
            <span class="roblox-user">${activity.roblox_username}</span>
        </div>
        <div class="action">${activity.action} en ${activity.game_name}</div>
        <div class="timestamp">${new Date(activity.timestamp).toLocaleTimeString()}</div>
    `;

    // Animar entrada
    gsap.fromTo(item, 
        { opacity: 0, x: -50 },
        { opacity: 1, x: 0, duration: 0.5 }
    );

    feed.prepend(item);

    // Limitar a 10 items
    if (feed.children.length > 10) {
        gsap.to(feed.lastChild, {
            opacity: 0,
            x: 50,
            duration: 0.3,
            onComplete: () => feed.removeChild(feed.lastChild)
        });
    }
}

// Cargar datos iniciales
async function loadDashboard() {
    try {
        // Cargar actividad reciente
        const activityResponse = await fetch(`${API_BASE}/dashboard/recent-activity`, { headers });
        const activityData = await activityResponse.json();

        // Cargar estadísticas
        const statsResponse = await fetch(`${API_BASE}/dashboard/live-stats`, { headers });
        const statsData = await statsResponse.json();

        // Actualizar UI con animaciones
        animateNumber(document.querySelector('#users-online .number'), statsData.stats.users_online);
        animateNumber(document.querySelector('#servers-found .number'), statsData.stats.servers_found_today);

        // Mostrar actividad reciente
        activityData.recent_activity.forEach(activity => {
            addActivityToFeed(activity);
        });

    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Actualizar cada 30 segundos
setInterval(loadDashboard, 30000);
loadDashboard();
```

### CSS para Animaciones
```css
.dashboard {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.stat-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    padding: 30px;
    text-align: center;
    transition: transform 0.3s ease;
}

.stat-card:hover {
    transform: translateY(-10px);
}

.stat-card .number {
    font-size: 3em;
    font-weight: bold;
    color: #fff;
    display: block;
}

.activity-feed {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 20px;
    max-height: 400px;
    overflow-y: auto;
}

.activity-item {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 10px;
    border-left: 4px solid #00ff88;
    transition: all 0.3s ease;
}

.activity-item:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: scale(1.02);
}

@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(0, 255, 136, 0); }
    100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0); }
}

.stat-card.pulse {
    animation: pulse 2s infinite;
}
```

## 🌐 URLs de Acceso

- **Control Remoto (Web)**: https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:8080/
- **API REST**: https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000/

> **Nota**: Es importante usar el puerto correcto:
> - Puerto **8080** para el control remoto web
> - Puerto **5000** para la API REST

## 🔧 Configuración para el Dashboard

Para conectar tu dashboard web con la API del bot, usa esta configuración:

```javascript
const API_BASE_URL = 'https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000';
const API_KEY = 'rbxservers_user'; // Para usuarios normales, 'rbxservers_admin' para admin

// Configuración de headers para todas las requests
const apiHeaders = {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
};

// Función para hacer requests a la API
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const config = {
        headers: apiHeaders,
        ...options
    };

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
```

## ⚠️ Solución de Problemas Comunes

### 1. Error CORS
Si recibes errores de CORS, asegúrate de que tu dominio esté en la lista de orígenes permitidos.

### 2. Error 404 en OPTIONS
Si ves errores 404 en requests OPTIONS, verifica que estés usando el puerto correcto (5000) para la API REST.

### 3. URL Incorrecta
- ✅ **Correcto**: `https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000/stats`
- ❌ **Incorrecto**: `https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev/stats`

### 4. Testing de la API
Puedes probar la API directamente:

```bash
# Verificar que la API esté funcionando
curl https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000/

# Obtener estadísticas (requiere API key)
curl -H "Authorization: Bearer rbxservers_user" \
     https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000/stats
```

## URL de la API

La API está disponible en:
`https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev`

El puerto 5000 se mapea automáticamente a los puertos 80/443 en Replit.