
# 🚀 RbxServers Bot API - Documentación

## 📋 Información General

**Nombre:** RbxServers Bot API  
**Versión:** 1.0.0  
**Puerto:** 5000 (automáticamente mapeado a 80/443 en producción)  
**Creado por:** hesiz  
**URL Base:** `http://localhost:5000` (desarrollo) | `https://3c1525f4-678e-4a8f-a0f3-6fd818f430a8-00-2l9rwpvizcpst.janeway.replit.dev:5000` (producción)

## 🔗 Endpoints Disponibles

### 🏠 Información General
```
GET /
```
Retorna información general de la API y lista de todos los endpoints disponibles.

### 📊 Estadísticas Generales
```
GET /stats
```
Obtiene estadísticas completas del bot incluyendo usuarios, servidores, bans, etc.

**Respuesta ejemplo:**
```json
{
  "success": true,
  "data": {
    "users": {
      "total_verified": 40,
      "total_banned": 1,
      "total_with_warnings": 0,
      "total_delegated_owners": 0,
      "total_with_coins": 0
    },
    "servers": {
      "total_servers": 5,
      "total_games": 1
    },
    "last_updated": "2025-01-20T12:00:00.000Z"
  }
}
```

### 👥 Usuarios

#### Listar todos los usuarios
```
GET /users
```
Obtiene lista completa de usuarios verificados con información resumida.

#### Información específica de usuario
```
GET /users/:id
```
Obtiene información detallada de un usuario específico por Discord ID.

**Ejemplo:** `GET /users/826599725150371860`

#### Buscar por nombre de Roblox
```
GET /search/roblox/:username
```
Busca usuarios por nombre de usuario de Roblox (búsqueda parcial).

**Ejemplo:** `GET /search/roblox/hesiz`

### 💰 Sistema de Monedas

#### Información general de monedas
```
GET /coins
```
Estadísticas del sistema de monedas del bot.

#### Monedas de usuario específico
```
GET /coins/:userId
```
Información detallada de monedas de un usuario específico.

### 🖥️ Servidores VIP

#### Información general de servidores
```
GET /servers
```
Estadísticas y información de todos los servidores VIP.

#### Servidores de usuario específico
```
GET /servers/:userId
```
Servidores VIP específicos de un usuario.

### 🚫 Sistema de Moderación

#### Lista de usuarios baneados
```
GET /bans
```
Información completa de usuarios baneados, incluyendo bans activos y expirados.

### 🛒 Marketplace
```
GET /marketplace
```
Información del marketplace del bot incluyendo listados e intercambios.

### 🔔 Sistema de Alertas
```
GET /alerts
```
Información del sistema de alertas y usuarios monitoreados.

### 👑 Owners Delegados
```
GET /delegated
```
Lista de owners delegados del bot.

## 🎛️ Dashboard de Owner

### 📱 Diseño Propuesto

El dashboard será una interfaz web exclusiva para owners que incluirá:

#### 🏠 **Panel Principal**
- **Estadísticas en Tiempo Real:** Cards con números grandes mostrando usuarios totales, servidores activos, bans, etc.
- **Gráficos:** Líneas de tiempo de actividad, uso de comandos, registros diarios
- **Estado del Bot:** Indicador de salud, uptime, última actividad

#### 👥 **Gestión de Usuarios**
- **Tabla de Usuarios:** Lista paginada con filtros por verificación, bans, warnings
- **Acciones Rápidas:** Banear, des-banear, agregar warnings, verificar manualmente
- **Perfil Detallado:** Modal con toda la información de un usuario específico
- **Búsqueda Avanzada:** Por Discord ID, nombre de Roblox, estado, etc.

#### 🖥️ **Servidores VIP**
- **Mapa de Servidores:** Visualización por juegos y categorías
- **Gestión de Enlaces:** Agregar, eliminar, verificar estado de enlaces VIP
- **Uso por Usuario:** Quién está usando qué servidores
- **Categorías:** Organización por tipos de juegos

#### 💰 **Sistema Económico**
- **Balance Global:** Total de monedas en circulación
- **Transacciones:** Historial completo con filtros por usuario/fecha
- **Marketplace:** Gestión de listados e intercambios
- **Economía:** Estadísticas de ganancias, gastos, items más populares

#### 🚫 **Moderación**
- **Panel de Bans:** Lista de usuarios baneados con opciones de gestión
- **Sistema de Warnings:** Historial y gestión de advertencias
- **Reportes:** Sistema de reportes de usuarios (si existe)
- **Logs de Actividad:** Registro de acciones de moderación

#### 🔔 **Alertas y Monitoreo**
- **Usuarios Monitoreados:** Lista de usuarios bajo vigilancia
- **Alertas de Sistema:** Notificaciones importantes del bot
- **Configuración:** Ajustes de alertas y notificaciones

#### ⚙️ **Configuración**
- **Settings del Bot:** Configuraciones generales
- **API Keys:** Gestión de claves (Gemini, etc.)
- **Owners Delegados:** Agregar/remover permisos
- **Mantenimiento:** Modo mantenimiento y actualizaciones

### 🎨 **Características del Dashboard**

#### **Seguridad**
- **Autenticación:** Solo owners pueden acceder
- **Tokens de Sesión:** Sistema de autenticación seguro
- **Logs de Acceso:** Registro de quién accede y cuándo

#### **Interfaz**
- **Responsive:** Compatible con móviles y tablets
- **Dark/Light Mode:** Tema oscuro y claro
- **Tiempo Real:** Actualizaciones automáticas cada 30 segundos
- **Notificaciones:** Alertas push para eventos importantes

#### **Funcionalidades Avanzadas**
- **Exportación:** Datos en CSV/JSON para análisis
- **Filtros Avanzados:** Múltiples criterios de búsqueda
- **Acciones en Masa:** Operaciones sobre múltiples usuarios
- **Historial:** Seguimiento de cambios y acciones realizadas

## 🛠️ Tecnologías Sugeridas para el Dashboard

### **Frontend**
- **Framework:** React.js o Vue.js
- **UI Library:** Material-UI, Ant Design o Bootstrap
- **Charts:** Chart.js o Recharts
- **Estado:** Redux o Vuex
- **Real-time:** Socket.io para actualizaciones en vivo

### **Backend Adicional** (si es necesario)
- **WebSockets:** Para actualizaciones en tiempo real
- **Autenticación:** JWT tokens
- **Middleware:** Validación de permisos de owner

## 🚀 Cómo Usar la API

### **1. Desarrollo Local**
```bash
node api_server.js
```
La API estará disponible en `http://localhost:5000`

### **2. Producción en Replit**
La API se ejecuta automáticamente y está disponible en tu URL de Replit.

### **3. Ejemplos de Uso**

#### JavaScript/Fetch
```javascript
// Obtener estadísticas
const stats = await fetch('/stats').then(r => r.json());

// Buscar usuario
const user = await fetch('/users/826599725150371860').then(r => r.json());

// Buscar por nombre de Roblox
const search = await fetch('/search/roblox/hesiz').then(r => r.json());
```

#### Python/Requests
```python
import requests

base_url = "https://3c1525f4-678e-4a8f-a0f3-6fd818f430a8-00-2l9rwpvizcpst.janeway.replit.dev:5000"

# Obtener estadísticas
stats = requests.get(f"{base_url}/stats").json()

# Información de usuario
user = requests.get(f"{base_url}/users/826599725150371860").json()
```

#### cURL
```bash
# Estadísticas generales
curl https://3c1525f4-678e-4a8f-a0f3-6fd818f430a8-00-2l9rwpvizcpst.janeway.replit.dev:5000/stats

# Usuario específico
curl https://3c1525f4-678e-4a8f-a0f3-6fd818f430a8-00-2l9rwpvizcpst.janeway.replit.dev:5000/users/826599725150371860

# Buscar por Roblox
curl https://3c1525f4-678e-4a8f-a0f3-6fd818f430a8-00-2l9rwpvizcpst.janeway.replit.dev:5000/search/roblox/hesiz
```

## 📝 Notas Importantes

- **Cors Habilitado:** La API acepta peticiones desde cualquier origen
- **Formato JSON:** Todas las respuestas están en formato JSON
- **Manejo de Errores:** Códigos HTTP estándar (404, 500, etc.)
- **Rate Limiting:** Considera implementar limitación de peticiones para producción
- **Logs:** Todos los accesos se registran en la consola del servidor

## 🔒 Próximos Pasos para el Dashboard

1. **Crear el frontend** del dashboard
2. **Implementar autenticación** de owners
3. **Añadir WebSockets** para actualizaciones en tiempo real
4. **Crear endpoints adicionales** para acciones de administración (banear, modificar monedas, etc.)
5. **Implementar sistema de logs** para auditoría
6. **Añadir configuraciones** del bot via web

---

**Dashboard exclusivo para owners - Nadie más tendrá acceso**
