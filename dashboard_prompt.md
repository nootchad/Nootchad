
# 🎮 Prompt para Dashboard Animado de RbxServers

## 📋 Descripción del Proyecto

Necesito que desarrolles un **dashboard web moderno y animado** para el bot de Discord "RbxServers" que gestiona servidores VIP de Roblox. El dashboard debe mostrar estadísticas en tiempo real, actividad de usuarios, y ser completamente responsivo con animaciones suaves.

## 🎯 Funcionalidades Requeridas

### 1. **Dashboard Principal con Estadísticas**
- **Cards animadas** que muestren:
  - 👥 Total de usuarios verificados
  - 🎮 Juegos únicos disponibles  
  - 🔗 Enlaces VIP totales
  - 🚫 Usuarios baneados
  - 💰 Monedas en circulación
  - 📊 Actividad diaria/semanal

- **Gráficos interactivos** usando Chart.js o D3.js:
  - Crecimiento de usuarios por día/semana
  - Juegos más populares (gráfico de barras)
  - Actividad por horas del día (gráfico de líneas)
  - Distribución de usuarios por países (gráfico de dona)

### 2. **Feed de Actividad en Tiempo Real**
- **Lista en vivo** de usuarios usando el bot
- **Animaciones fluidas** cuando aparecen nuevos eventos
- **Información mostrada por evento**:
  - Nombre de Discord del usuario
  - Username de Roblox
  - Acción realizada (scrape, obtener servidor, etc.)
  - Juego en el que se realizó la acción
  - Timestamp exacto
  - País/ubicación del usuario

### 3. **Mapa Mundial Interactivo**
- **Mapa animado** mostrando usuarios activos por país
- **Puntos pulsantes** en países con actividad reciente
- **Tooltips informativos** al hacer hover
- **Colores dinámicos** basados en la cantidad de usuarios

### 4. **Panel de Usuarios Verificados**
- **Tabla filtrable y ordenable** de usuarios
- **Cards individuales** con información detallada:
  - Avatar de Discord
  - Username de Roblox  
  - Fecha de verificación
  - Juegos favoritos
  - Servidores obtenidos
  - Balance de monedas
- **Búsqueda en tiempo real**

### 5. **Sistema de Notificaciones**
- **Toast notifications** para eventos importantes:
  - Nuevas verificaciones
  - Usuarios baneados
  - Récords de actividad
  - Errores del sistema

## 🎨 Diseño y Estilo

### **Tema y Colores**
- **Tema oscuro** como principal (fondo #1a1a1a, cards #2d2d2d)
- **Tema claro** opcional 
- **Colores de acento**:
  - Azul: #3b82f6 (información)
  - Verde: #10b981 (éxito/verificados)
  - Rojo: #ef4444 (errores/baneados)
  - Amarillo: #f59e0b (advertencias)
  - Púrpura: #8b5cf6 (premium/especial)

### **Animaciones Requeridas**
- **Fade in/out** para elementos que aparecen/desaparecen
- **Slide up** para nuevos elementos en el feed
- **Pulse effect** para números que se actualizan
- **Smooth transitions** entre secciones
- **Loading skeletons** mientras cargan datos
- **Hover effects** en botones y cards
- **CountUp animations** para números grandes

### **Layout Responsivo**
- **Desktop**: Layout de 3 columnas
- **Tablet**: Layout de 2 columnas  
- **Mobile**: Layout de 1 columna con navegación inferior

## 🔌 Integración con API

### **URL Base de la API**
```
https://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000
```

### **Headers de Autenticación**
```javascript
headers: {
    'Authorization': 'Bearer rbxservers_user',
    'Content-Type': 'application/json'
}
```

### **Endpoints Principales a Consumir**

#### **Estadísticas Generales**
```
GET /stats
```
Respuesta incluye usuarios, servidores, scraper stats, monedas, etc.

#### **Actividad Reciente**  
```
GET /dashboard/recent-activity
```
Últimos 50 eventos de actividad de usuarios.

#### **Estadísticas en Tiempo Real**
```
GET /dashboard/live-stats  
```
Datos actualizados para gráficos y métricas.

#### **Mapa de Usuarios**
```
GET /dashboard/user-map
```
Ubicaciones y conteos por país.

#### **WebSocket para Tiempo Real**
```
wss://a07a462b-cf39-43eb-85d2-3f250e733fcb-00-3l0ph7x2hrb5s.kirk.replit.dev:5000/dashboard/live-feed
```

**Eventos WebSocket que recibirás:**
```javascript
// Nueva actividad de usuario
{
  "type": "user_activity", 
  "data": {
    "user_id": "123456789",
    "discord_name": "usuario#1234", 
    "roblox_username": "RobloxUser123",
    "action": "scrape_servers",
    "game_name": "Blox Fruits",
    "timestamp": "2025-01-11T01:30:45.123Z",
    "location": "España"
  }
}

// Actualización de estadísticas
{
  "type": "stats_update",
  "data": {
    "users_online": 24,
    "servers_found_today": 1251  
  }
}

// Nueva verificación
{
  "type": "new_verification",
  "data": {
    "discord_name": "newuser#5678",
    "roblox_username": "NewRobloxUser", 
    "timestamp": "2025-01-11T01:31:00.000Z"
  }
}
```

## 🛠️ Tecnologías Recomendadas

### **Frontend Framework**
- **React** con hooks (useState, useEffect, useContext)
- **Next.js** para SSR y routing (opcional)
- **Vanilla JavaScript** + **HTML5/CSS3** (alternativa simple)

### **Librerías de UI/Animaciones**
- **Tailwind CSS** para estilos responsivos
- **Framer Motion** para animaciones complejas
- **React Spring** (alternativa a Framer Motion)
- **AOS (Animate On Scroll)** para animaciones de scroll
- **GSAP** para animaciones avanzadas (opcional)

### **Gráficos y Visualización**
- **Chart.js** con **react-chartjs-2**
- **Recharts** (alternativa más React-friendly)
- **D3.js** para gráficos avanzados
- **Leaflet** o **Mapbox** para el mapa mundial

### **Tiempo Real**
- **Socket.io-client** o **WebSocket API nativo**
- **SWR** o **React Query** para cache y refetch automático

### **Notificaciones**
- **React Hot Toast** o **React Toastify**

## 📱 Componentes Específicos Necesarios

### 1. **StatsCard Component**
```jsx
<StatsCard 
  title="Usuarios Verificados"
  value={147}
  previousValue={132}
  icon="👥"
  color="green"
  trend="up"
  percentage={11.4}
/>
```

### 2. **ActivityFeed Component**  
```jsx
<ActivityFeed 
  events={recentActivity}
  maxItems={10}
  showAnimation={true}
  autoScroll={true}
/>
```

### 3. **UserMap Component**
```jsx
<UserMap 
  userData={userLocationData}
  interactive={true}
  showTooltips={true}
  theme="dark"
/>
```

### 4. **LiveChart Component**
```jsx
<LiveChart 
  type="line"
  data={hourlyUsage}
  updateInterval={30000}
  animated={true}
  responsive={true}
/>
```

### 5. **UserTable Component**
```jsx
<UserTable 
  users={verifiedUsers}
  sortable={true}
  filterable={true}
  pagination={true}
  itemsPerPage={20}
/>
```

## 🎛️ Funcionalidades Interactivas

### **Dashboard Controls**
- **Selector de rango de tiempo** (1h, 6h, 24h, 7d, 30d)
- **Toggle entre tema claro/oscuro**
- **Botón de actualización manual**
- **Filtros por país, juego, tipo de actividad**
- **Exportar datos** (CSV, JSON)

### **Real-time Features**
- **Indicador de conexión** WebSocket (verde/rojo)
- **Contador de usuarios online** en tiempo real
- **Última actualización** timestamp
- **Auto-refresh** cada 30 segundos para datos que no vienen por WS

### **Responsive Behavior**
- **Navigation drawer** en móvil
- **Collapse automático** de sidebars en tablets
- **Touch gestures** para navegación móvil
- **Optimización** para diferentes tamaños de pantalla

## 📊 Métricas y KPIs a Mostrar

### **Métricas Principales**
- Total usuarios verificados
- Usuarios activos (última hora/día)
- Servidores VIP totales disponibles
- Juegos únicos soportados
- Países representados
- Tiempo promedio de verificación
- Éxito rate del scraping
- Monedas en circulación
- Transacciones diarias

### **Trends y Analytics**
- Crecimiento de usuarios (diario/semanal)
- Picos de actividad por horas
- Juegos más populares por período
- Distribución geográfica de usuarios
- Ratio verificación/ban
- Performance del scraper (servidores/minuto)

## 🚀 Objetivos de Performance

- **Carga inicial** < 3 segundos
- **Actualización de datos** < 500ms
- **Animaciones** a 60 FPS
- **Tamaño del bundle** < 2MB
- **Mobile-friendly** al 100%
- **Accesibilidad** WCAG 2.1 AA

## 📋 Entregables Esperados

1. **Código fuente completo** con estructura modular
2. **README detallado** con instrucciones de instalación
3. **Componentes reutilizables** bien documentados  
4. **Responsive design** funcionando en todos los dispositivos
5. **Conexión WebSocket** funcional para tiempo real
6. **Manejo de errores** robusto
7. **Loading states** y **error boundaries**
8. **Configuración de despliegue** (Vercel, Netlify, etc.)

## 💡 Extras Opcionales (Bonus)

- **PWA support** (offline functionality)
- **Dark/light mode** automático según preferencias del sistema
- **Exportación de reportes** en PDF
- **Sistema de alertas** personalizables
- **Comparación histórica** de métricas
- **Panel de administración** para gestionar usuarios
- **API rate limiting** visualization
- **Health check** del sistema en tiempo real

---

**¡Crea un dashboard impresionante que muestre la potencia y actividad del bot RbxServers en tiempo real! 🚀✨**
