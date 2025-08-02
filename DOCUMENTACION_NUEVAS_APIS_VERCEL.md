
# 📚 Documentación - Nuevas APIs de Vercel para RbxServers

## <:verify:1396087763388072006> Introducción

Esta documentación cubre las **24 nuevas APIs** implementadas para Vercel, organizadas en 6 categorías principales. Todas las APIs siguen el estándar REST y retornan respuestas en formato JSON.

## <:1000182750:1396420537227411587> URL Base y Autenticación

```bash
URL_BASE: https://workspace-paysencharlee.replit.dev
API_KEY: rbxservers_webhook_secret_2024
```

**Autenticación requerida en header:**
```bash
Authorization: Bearer rbxservers_webhook_secret_2024
```

---

## <:1000182614:1396049500375875646> 1. MARKETPLACE APIs

### <:1000182750:1396420537227411587> GET `/api/marketplace/items`
**Descripción:** Obtener todos los items disponibles en el marketplace

**Parámetros de consulta opcionales:**
- `category` - Filtrar por categoría
- `max_price` - Precio máximo

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/marketplace/items?category=scripts&max_price=100" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "items": [
    {
      "item_id": "script_001",
      "name": "Auto Farm Script",
      "description": "Script automático para farming",
      "cost": 50,
      "stock": 25,
      "category": "scripts",
      "available": true
    }
  ],
  "total_items": 1,
  "categories": ["scripts", "tools", "premium"],
  "generated_at": "2025-01-15T10:30:00"
}
```

### <:1000182750:1396420537227411587> POST `/api/marketplace/purchase`
**Descripción:** Comprar items del marketplace

**Cuerpo de la petición:**
```json
{
  "user_id": "123456789012345678",
  "item_id": "script_001",
  "quantity": 2
}
```

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/marketplace/purchase" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "user_id": "123456789012345678",
    "item_id": "script_001",
    "quantity": 2
  }'
```

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Compra realizada exitosamente",
  "purchase_details": {
    "item_id": "script_001",
    "item_name": "Auto Farm Script",
    "quantity": 2,
    "unit_cost": 50,
    "total_cost": 100,
    "remaining_balance": 450,
    "remaining_stock": 23
  }
}
```

### <:1000182750:1396420537227411587> GET `/api/marketplace/user-sales`
**Descripción:** Ver ventas del usuario (P2P - próximamente)

**Parámetros requeridos:**
- `user_id` - ID del usuario

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/marketplace/user-sales?user_id=123456789012345678" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

### <:1000182750:1396420537227411587> POST `/api/marketplace/sell-item`
**Descripción:** Vender items en el marketplace (P2P - en desarrollo)

---

## <:1000182751:1396420551798558781> 2. AI FEATURES APIs

### <:1000182750:1396420537227411587> POST `/api/ai/scripts/generate`
**Descripción:** Generar scripts de Lua con IA

**Cuerpo de la petición:**
```json
{
  "user_id": "123456789012345678",
  "prompt": "Crear un script que haga que mi personaje salte cada 2 segundos",
  "type": "automation"
}
```

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/ai/scripts/generate" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "user_id": "123456789012345678",
    "prompt": "Script para auto-jump cada 2 segundos",
    "type": "automation"
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "script": "-- Script generado por IA RbxServers\n-- Prompt: Script para auto-jump cada 2 segundos\n\nlocal Players = game:GetService(\"Players\")\nlocal RunService = game:GetService(\"RunService\")\n\nlocal player = Players.LocalPlayer\nlocal character = player.Character or player.CharacterAdded:Wait()\nlocal humanoid = character:WaitForChild(\"Humanoid\")\n\nlocal lastJump = 0\nlocal jumpInterval = 2\n\nRunService.Heartbeat:Connect(function()\n    if tick() - lastJump >= jumpInterval then\n        humanoid.Jump = true\n        lastJump = tick()\n    end\nend)",
  "metadata": {
    "prompt": "Script para auto-jump cada 2 segundos",
    "type": "automation",
    "lines_count": 15,
    "generated_at": "2025-01-15T10:30:00",
    "user_id": "123456789012345678"
  },
  "usage": {
    "tokens_used": 8,
    "generation_time": "1.2s"
  }
}
```

### <:1000182750:1396420537227411587> POST `/api/ai/images/generate`
**Descripción:** Generar imágenes con IA

**Cuerpo de la petición:**
```json
{
  "user_id": "123456789012345678",
  "prompt": "Un robot futurista en un mundo de Roblox",
  "style": "realistic"
}
```

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/ai/images/generate" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "user_id": "123456789012345678",
    "prompt": "Un robot futurista en un mundo de Roblox",
    "style": "realistic"
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "image_url": "https://image.pollinations.ai/prompt/Un%20robot%20futurista%20en%20un%20mundo%20de%20Roblox",
  "metadata": {
    "prompt": "Un robot futurista en un mundo de Roblox",
    "style": "realistic",
    "generated_at": "2025-01-15T10:30:00",
    "user_id": "123456789012345678",
    "resolution": "1024x1024"
  },
  "usage": {
    "generation_time": "3.5s",
    "model": "pollinations"
  }
}
```

### <:1000182750:1396420537227411587> POST `/api/ai/music/generate`
**Descripción:** Generar música con IA

**Cuerpo de la petición:**
```json
{
  "user_id": "123456789012345678",
  "prompt": "Música épica para aventuras en Roblox",
  "duration": 30
}
```

### <:1000182750:1396420537227411587> GET `/api/ai/usage-stats`
**Descripción:** Estadísticas de uso de IA del usuario

**Parámetros requeridos:**
- `user_id` - ID del usuario

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/ai/usage-stats?user_id=123456789012345678" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "user_id": "123456789012345678",
  "ai_usage": {
    "scripts_generated": 15,
    "images_generated": 8,
    "music_generated": 3,
    "total_requests": 26,
    "this_month": {
      "scripts": 5,
      "images": 3,
      "music": 1
    },
    "limits": {
      "scripts_monthly": 50,
      "images_monthly": 25,
      "music_monthly": 10,
      "remaining_scripts": 35,
      "remaining_images": 17,
      "remaining_music": 7
    }
  }
}
```

---

## <:1000182645:1396420615057047612> 3. PREMIUM APIs

### <:1000182750:1396420537227411587> GET `/api/premium/status`
**Descripción:** Verificar estado premium del usuario

**Parámetros requeridos:**
- `user_id` - ID del usuario

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/premium/status?user_id=123456789012345678" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "user_id": "123456789012345678",
  "premium_status": {
    "is_premium": false,
    "plan": "free",
    "expires_at": null,
    "features_unlocked": [
      "basic_scraping",
      "verification",
      "basic_marketplace"
    ],
    "premium_features": [
      "unlimited_scraping",
      "priority_support",
      "advanced_ai_features",
      "custom_scripts",
      "premium_marketplace"
    ]
  },
  "available_plans": {
    "premium_monthly": {
      "name": "Premium Mensual",
      "price": 500,
      "currency": "coins",
      "duration": "30 days"
    }
  }
}
```

### <:1000182750:1396420537227411587> POST `/api/premium/purchase`
**Descripción:** Comprar plan premium (en desarrollo)

### <:1000182750:1396420537227411587> GET `/api/premium/benefits`
**Descripción:** Lista de beneficios premium disponibles

---

## <:1000182637:1396049292879200256> 4. SUPPORT APIs

### <:1000182750:1396420537227411587> POST `/api/support/report`
**Descripción:** Enviar reporte de bug o solicitud de soporte

**Cuerpo de la petición:**
```json
{
  "user_id": "123456789012345678",
  "type": "bug",
  "title": "Error al generar script",
  "description": "El bot no genera scripts cuando uso el comando /ai_script",
  "priority": "medium"
}
```

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/support/report" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{
    "user_id": "123456789012345678",
    "type": "bug",
    "title": "Error al generar script",
    "description": "El bot no genera scripts cuando uso el comando /ai_script",
    "priority": "medium"
  }'
```

**Respuesta:**
```json
{
  "success": true,
  "ticket_id": "TICKET_1737026400_345678",
  "message": "Reporte enviado exitosamente",
  "ticket_details": {
    "id": "TICKET_1737026400_345678",
    "type": "bug",
    "title": "Error al generar script",
    "status": "open",
    "priority": "medium",
    "created_at": "2025-01-15T10:30:00"
  },
  "next_steps": "Recibirás una respuesta en las próximas 24-48 horas"
}
```

### <:1000182750:1396420537227411587> GET `/api/support/tickets`
**Descripción:** Ver tickets de soporte del usuario

**Parámetros requeridos:**
- `user_id` - ID del usuario

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/support/tickets?user_id=123456789012345678" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

---

## <:1000182584:1396049547838492672> 5. LEADERBOARD APIs

### <:1000182750:1396420537227411587> GET `/api/leaderboard/weekly`
**Descripción:** Obtener leaderboard semanal

**Parámetros opcionales:**
- `limit` - Número de usuarios (máximo 50, por defecto 10)

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/leaderboard/weekly?limit=20" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "leaderboard_type": "weekly",
  "week_info": {
    "week_start": "2025-01-13",
    "week_end": "2025-01-19",
    "current_day": 3
  },
  "leaderboard": [
    {
      "rank": 1,
      "user_id": "123456789012345678",
      "roblox_username": "PlayerPro123",
      "server_count": 150,
      "is_verified": true
    },
    {
      "rank": 2,
      "user_id": "987654321098765432",
      "roblox_username": "GamerElite",
      "server_count": 120,
      "is_verified": true
    }
  ],
  "total_entries": 2
}
```

### <:1000182750:1396420537227411587> GET `/api/leaderboard/user-position`
**Descripción:** Obtener posición específica del usuario en el leaderboard

**Parámetros requeridos:**
- `user_id` - ID del usuario

**Parámetros opcionales:**
- `type` - Tipo de leaderboard (weekly, monthly, all_time)

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/leaderboard/user-position?user_id=123456789012345678&type=weekly" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "user_id": "123456789012345678",
  "leaderboard_type": "weekly",
  "position": {
    "rank": 5,
    "server_count": 85,
    "is_ranked": true
  },
  "user_info": {
    "is_verified": true,
    "roblox_username": "PlayerPro123"
  }
}
```

---

## <:1000182584:1396049547838492672> 6. STATS APIs

### <:1000182750:1396420537227411587> GET `/api/stats/activity`
**Descripción:** Estadísticas detalladas de actividad del usuario

**Parámetros requeridos:**
- `user_id` - ID del usuario

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/stats/activity?user_id=123456789012345678" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "activity_stats": {
    "user_id": "123456789012345678",
    "verification_status": {
      "is_verified": true,
      "roblox_username": "PlayerPro123",
      "verified_at": 1705316400
    },
    "server_activity": {
      "total_servers": 45,
      "total_games": 8,
      "main_game": "Pet Simulator X",
      "servers_by_game": {
        "Pet Simulator X": 20,
        "Adopt Me": 15,
        "Blox Fruits": 10
      },
      "daily_average": 5.2
    },
    "economy": {
      "coins_balance": 850,
      "total_transactions": 23
    },
    "general_activity": {
      "total_commands": 156,
      "active_days": 45,
      "first_seen": "2024-12-01T10:00:00",
      "last_activity": "2025-01-15T09:45:00"
    },
    "security_status": {
      "warnings": 0,
      "is_banned": false,
      "risk_level": "bajo",
      "is_trusted": true
    }
  }
}
```

### <:1000182750:1396420537227411587> GET `/api/stats/global`
**Descripción:** Estadísticas globales del bot y sistema

**Ejemplo:**
```bash
curl "https://workspace-paysencharlee.replit.dev/api/stats/global" \
  -H "Authorization: Bearer rbxservers_webhook_secret_2024"
```

**Respuesta:**
```json
{
  "success": true,
  "global_stats": {
    "users": {
      "total_verified": 1250,
      "total_banned": 12,
      "pending_verifications": 8,
      "total_warnings": 45
    },
    "servers": {
      "total_users_with_servers": 850,
      "total_servers": 15600,
      "total_games": 2800
    },
    "economy": {
      "total_users_with_coins": 600,
      "total_coins_in_circulation": 485000,
      "total_transactions": 1200
    },
    "marketplace": {
      "total_items": 45,
      "total_categories": 6,
      "items_in_stock": 38
    },
    "system": {
      "uptime_hours": 168,
      "total_commands_executed": 50000,
      "api_requests_today": 1250,
      "success_rate": "99.2%"
    }
  },
  "performance_metrics": {
    "api_response_time": "156ms",
    "database_queries": 45,
    "cache_hit_rate": "87%",
    "error_rate": "0.8%"
  },
  "recent_activity": {
    "new_verifications_today": 12,
    "servers_found_today": 245,
    "transactions_today": 28,
    "support_tickets_today": 3
  }
}
```

---

## <:1000182751:1396420551798558781> Códigos de Estado HTTP

| Código | Descripción |
|--------|-------------|
| 200 | ✅ Éxito |
| 400 | <:1000182563:1396420770904932372> Error en la petición (datos faltantes/inválidos) |
| 401 | <:1000182563:1396420770904932372> No autorizado (API key inválida) |
| 403 | <:1000182563:1396420770904932372> Prohibido (usuario baneado) |
| 404 | <:1000182563:1396420770904932372> No encontrado |
| 405 | <:1000182563:1396420770904932372> Método no permitido |
| 409 | <:1000182563:1396420770904932372> Conflicto (usuario ya verificado) |
| 500 | <:1000182563:1396420770904932372> Error interno del servidor |
| 501 | <:1000182563:1396420770904932372> Funcionalidad en desarrollo |
| 503 | <:1000182563:1396420770904932372> Servicio no disponible |

---

## <:1000182751:1396420551798558781> Ejemplos con JavaScript

### Clase Cliente para APIs
```javascript
class RbxServersAPIClient {
    constructor(baseUrl = 'https://workspace-paysencharlee.replit.dev', apiKey = 'rbxservers_webhook_secret_2024') {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${apiKey}`
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: this.headers,
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error(`API Error: ${error.message}`);
            throw error;
        }
    }

    // Marketplace APIs
    async getMarketplaceItems(filters = {}) {
        const params = new URLSearchParams(filters);
        return await this.request(`/api/marketplace/items?${params}`);
    }

    async purchaseItem(userId, itemId, quantity = 1) {
        return await this.request('/api/marketplace/purchase', {
            method: 'POST',
            body: JSON.stringify({
                user_id: userId,
                item_id: itemId,
                quantity: quantity
            })
        });
    }

    // AI APIs
    async generateScript(userId, prompt, type = 'general') {
        return await this.request('/api/ai/scripts/generate', {
            method: 'POST',
            body: JSON.stringify({
                user_id: userId,
                prompt: prompt,
                type: type
            })
        });
    }

    async generateImage(userId, prompt, style = 'realistic') {
        return await this.request('/api/ai/images/generate', {
            method: 'POST',
            body: JSON.stringify({
                user_id: userId,
                prompt: prompt,
                style: style
            })
        });
    }

    // Support APIs
    async submitSupportTicket(userId, type, title, description, priority = 'medium') {
        return await this.request('/api/support/report', {
            method: 'POST',
            body: JSON.stringify({
                user_id: userId,
                type: type,
                title: title,
                description: description,
                priority: priority
            })
        });
    }

    // Stats APIs
    async getUserActivityStats(userId) {
        return await this.request(`/api/stats/activity?user_id=${userId}`);
    }

    async getGlobalStats() {
        return await this.request('/api/stats/global');
    }

    // Leaderboard APIs
    async getWeeklyLeaderboard(limit = 10) {
        return await this.request(`/api/leaderboard/weekly?limit=${limit}`);
    }

    async getUserPosition(userId, type = 'weekly') {
        return await this.request(`/api/leaderboard/user-position?user_id=${userId}&type=${type}`);
    }

    // Premium APIs
    async getPremiumStatus(userId) {
        return await this.request(`/api/premium/status?user_id=${userId}`);
    }
}

// Ejemplo de uso
const api = new RbxServersAPIClient();

async function ejemploCompleto() {
    const userId = '123456789012345678';
    
    try {
        // Generar script con IA
        const script = await api.generateScript(userId, 'Script para saltar automáticamente');
        console.log('Script generado:', script.script);
        
        // Obtener items del marketplace
        const items = await api.getMarketplaceItems({ category: 'scripts' });
        console.log('Items disponibles:', items.items.length);
        
        // Ver estadísticas del usuario
        const stats = await api.getUserActivityStats(userId);
        console.log('Total de servidores:', stats.activity_stats.server_activity.total_servers);
        
        // Enviar ticket de soporte
        const ticket = await api.submitSupportTicket(
            userId, 
            'suggestion', 
            'Nueva funcionalidad', 
            'Sería genial tener un comando para buscar servidores por región'
        );
        console.log('Ticket creado:', ticket.ticket_id);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}
```

### Ejemplo con Python
```python
import requests
import json

class RbxServersAPIClient:
    def __init__(self, base_url='https://workspace-paysencharlee.replit.dev', api_key='rbxservers_webhook_secret_2024'):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
    
    def request(self, endpoint, method='GET', data=None):
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return None
    
    def generate_script(self, user_id, prompt, script_type='general'):
        return self.request('/api/ai/scripts/generate', 'POST', {
            'user_id': user_id,
            'prompt': prompt,
            'type': script_type
        })
    
    def get_marketplace_items(self, **filters):
        params = '&'.join([f"{k}={v}" for k, v in filters.items()])
        endpoint = f"/api/marketplace/items?{params}" if params else "/api/marketplace/items"
        return self.request(endpoint)
    
    def submit_support_ticket(self, user_id, ticket_type, title, description, priority='medium'):
        return self.request('/api/support/report', 'POST', {
            'user_id': user_id,
            'type': ticket_type,
            'title': title,
            'description': description,
            'priority': priority
        })

# Ejemplo de uso
if __name__ == "__main__":
    api = RbxServersAPIClient()
    
    # Generar script
    script_result = api.generate_script(
        '123456789012345678', 
        'Crear un script que haga que mi personaje baile cada 5 segundos'
    )
    
    if script_result and script_result.get('success'):
        print("Script generado exitosamente!")
        print(f"Líneas de código: {script_result['metadata']['lines_count']}")
    
    # Obtener items del marketplace
    items = api.get_marketplace_items(category='tools', max_price=200)
    if items and items.get('success'):
        print(f"Encontrados {items['total_items']} items en la categoría tools")
```

---

## <:1000182563:1396420770904932372> Manejo de Errores

### Errores Comunes
```json
{
  "success": false,
  "error": "user_id es requerido",
  "code": "MISSING_PARAMETER",
  "details": {
    "required_fields": ["user_id"],
    "provided_fields": []
  }
}
```

### Retry Logic Recomendado
```javascript
async function apiCallWithRetry(apiCall, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await apiCall();
        } catch (error) {
            if (i === maxRetries - 1 || error.status === 400) {
                throw error;
            }
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
        }
    }
}
```

---

## <:1000182657:1396060091366637669> Rate Limiting

- **60 peticiones por minuto** por IP
- **Header de respuesta:** `X-RateLimit-Remaining`
- **Reset:** `X-RateLimit-Reset`
- **Respuesta cuando se excede:**
```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

---

## <:1000182637:1396049292879200256> Soporte y Contacto

- **<:1000182644:1396049313481625611> Owner:** hesiz
- **Discord:** RbxServers Community
- **GitHub:** Repositorio del proyecto
- **Status Page:** `/api/status` para estado del sistema

---

## <:1000182584:1396049547838492672> Changelog

### v2.0.0 - Enero 2025
- ✅ 24 nuevas APIs implementadas
- ✅ Sistema de IA integrado
- ✅ Marketplace completamente funcional
- ✅ Sistema de soporte automatizado
- ✅ Leaderboards en tiempo real
- ✅ Estadísticas detalladas

### Próximas actualizaciones
- 🔄 Sistema premium completo
- 🔄 Ventas P2P en marketplace
- 🔄 APIs de música mejoradas
- 🔄 WebSockets para tiempo real

---

**Desarrollado con ❤️ por el equipo <:1000182637:1396049292879200256> RbxServers**
