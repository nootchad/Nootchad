
# 🏗️ Estructura del Servidor Discord - RbxServers

## 📋 Información General
Este documento detalla la estructura completa recomendada para el servidor de Discord de **RbxServers**, incluyendo canales, roles, permisos y configuraciones especiales.

---

## 🎭 **ROLES DEL SERVIDOR**

### 👑 **Roles de Administración**
- `👑｜Owner` - Color: #FF0000 (Rojo)
- `⚡｜Co-Owner` - Color: #FF4500 (Naranja Rojo)
- `🛡️｜Admin` - Color: #FF8C00 (Naranja Oscuro)
- `🔨｜Moderador` - Color: #FFD700 (Dorado)
- `🤖｜Bot-Manager` - Color: #00BFFF (Azul Cielo)

### ⭐ **Roles VIP y Premium**
- `💎｜VIP Diamond` - Color: #B9F2FF (Azul Diamante)
- `🥇｜VIP Gold` - Color: #FFD700 (Dorado)
- `🥈｜VIP Silver` - Color: #C0C0C0 (Plateado)
- `🥉｜VIP Bronze` - Color: #CD7F32 (Bronce)
- `⭐｜Premium User` - Color: #9932CC (Púrpura)
- `💰｜Donador` - Color: #32CD32 (Verde Lima)

### 🎮 **Roles de Usuario**
- `✅｜Verificado` - Color: #00FF00 (Verde)
- `🆕｜Nuevo Usuario` - Color: #87CEEB (Azul Cielo Claro)
- `🏆｜Usuario Activo` - Color: #FF69B4 (Rosa Fuerte)
- `📈｜Top Contributor` - Color: #8A2BE2 (Azul Violeta)

### 🚫 **Roles de Restricción**
- `⚠️｜Advertencia` - Color: #FFFF00 (Amarillo)
- `🔇｜Silenciado` - Color: #808080 (Gris)
- `🚫｜Baneado-Temp` - Color: #DC143C (Rojo Carmesí)

### 🎯 **Roles Especiales de Bot**
- `🤖｜Bot-Tester` - Color: #00CED1 (Turquesa Oscuro)
- `🧪｜Beta-Tester` - Color: #DA70D6 (Orquídea)
- `📊｜Stats-Access` - Color: #4169E1 (Azul Real)
- `🔧｜Developer` - Color: #228B22 (Verde Bosque)

---

## 📂 **ESTRUCTURA DE CANALES**

### 📢 **CATEGORÍA: INFORMACIÓN**
```
📢┃información
├── 📋┃reglas
├── 📝┃anuncios
├── 🎉┃eventos
├── 🔄┃actualizaciones
├── ❓┃faq
└── 🔗┃enlaces-útiles
```

### 🤖 **CATEGORÍA: BOT RBXSERVERS**
```
🤖┃rbxservers-bot
├── 🎮┃comandos-bot
├── 🔍┃verificación
├── 🎯┃servidores-vip
├── 📊┃estadísticas
├── 🛠️┃bugs-reportes
├── 💡┃sugerencias
└── 🎪┃testing-bot
```

### 💬 **CATEGORÍA: CHAT GENERAL**
```
💬┃chat-general
├── 🌍┃general
├── 🎮┃roblox-chat
├── 🔥┃memes
├── 🎨┃media
├── 🤝┃presentaciones
├── 💭┃off-topic
└── 🎵┃música
```

### 🎮 **CATEGORÍA: ROBLOX**
```
🎮┃roblox
├── 🏆┃logros
├── 🎯┃buscar-juegos
├── 👥┃buscar-amigos
├── 🔄┃intercambios
├── 💰┃trading
├── 🎪┃eventos-roblox
└── 📸┃screenshots
```

### ⭐ **CATEGORÍA: VIP ZONE**
```
⭐┃vip-zone
├── 💎┃vip-chat
├── 🎁┃vip-beneficios
├── 🏆┃vip-exclusivo
├── 🎯┃vip-servidores
└── 💰┃vip-rewards
```

### 🛒 **CATEGORÍA: MARKETPLACE**
```
🛒┃marketplace
├── 💰┃compra-venta
├── 🎁┃códigos
├── 💎┃premium-items
├── 🔄┃intercambios-seguras
└── 📋┃reglas-trading
```

### 🔧 **CATEGORÍA: SOPORTE**
```
🔧┃soporte
├── 🎫┃tickets
├── 💬┃soporte-general
├── 🚨┃reportes
├── 📞┃contacto-staff
└── 🔄┃resoluciones
```

### 👑 **CATEGORÍA: STAFF ONLY**
```
👑┃staff-only
├── 🛡️┃staff-chat
├── 📊┃staff-reports
├── 🔨┃moderación
├── 📋┃logs-sistema
├── 🤖┃bot-commands
└── 📈┃analytics
```

### 🔊 **CATEGORÍA: CANALES DE VOZ**
```
🔊┃canales-de-voz
├── 🎮┃Roblox Gaming
├── 💬┃Chat General
├── 🎵┃Música
├── 🎯┃VIP Lounge
├── 🛠️┃Soporte de Voz
├── 🎪┃Eventos
└── 🔒┃Staff Meeting
```

---

## ⚙️ **CONFIGURACIONES ESPECIALES**

### 🤖 **Configuración de Bots**
- **RbxServers Bot**: Acceso completo a canales de bot
- **MEE6**: Moderación automática y sistema de niveles
- **Carl-bot**: Automod y tickets
- **Dyno**: Logs y música

### 🔒 **Permisos por Categorías**

#### 📢 **Información** - Solo lectura para usuarios
- **@everyone**: Ver canal, leer historial
- **Staff**: Enviar mensajes, gestionar mensajes

#### 🤖 **RbxServers Bot** - Interacción con bot
- **@Verificado**: Usar comandos slash, enviar mensajes
- **@VIP**: Permisos adicionales de comandos premium
- **@Bot-Manager**: Gestión completa del bot

#### ⭐ **VIP Zone** - Solo usuarios VIP
- **@VIP Diamond/Gold/Silver/Bronze**: Acceso completo
- **@Premium User**: Acceso limitado
- **Staff**: Supervisión

### 📋 **Sistema de Verificación**
1. **Canal #verificación**: Comando `/verify [username]`
2. **Verificación por descripción de Roblox**
3. **Rol automático @Verificado** tras completar
4. **Acceso a comandos del bot**

### 🎯 **Canales con Funciones Especiales**

#### 🎮 **#comandos-bot**
- Uso exclusivo de comandos del bot
- Cooldown de 5 segundos entre comandos
- Solo usuarios verificados

#### 🔍 **#verificación**
- Canal exclusivo para verificación
- Auto-delete de mensajes después de 10 minutos
- Bot responde con embeds privados

#### 📊 **#estadísticas**
- Estadísticas automáticas del bot cada hora
- Información de servidores VIP encontrados
- Usuarios activos y verificados

#### 🎫 **#tickets**
- Sistema de tickets para soporte
- Categoría privada creada automáticamente
- Solo staff puede ver y responder

---

## 🎨 **PERSONALIZACIÓN VISUAL**

### 🌈 **Esquema de Colores**
- **Primario**: #7289DA (Azul Discord)
- **Secundario**: #99AAB5 (Gris Claro)
- **Éxito**: #43B581 (Verde)
- **Advertencia**: #FAA61A (Naranja)
- **Error**: #F04747 (Rojo)
- **VIP**: #9932CC (Púrpura)

### 🎭 **Emojis Personalizados Recomendados**
- `:rbxservers:` - Logo del bot
- `:roblox_verified:` - Verificación de Roblox
- `:vip_star:` - Estrella VIP
- `:server_link:` - Enlace de servidor
- `:coin_gold:` - Moneda del sistema
- `:diamond_tier:` - Tier diamante
- `:warning_bot:` - Advertencia del bot

---

## 🔧 **CONFIGURACIÓN DE AUTOMOD**

### 🚫 **Filtros Automáticos**
- Links externos (excepto Roblox y Discord)
- Spam de comandos
- Palabras prohibidas
- Contenido NSFW
- Invitaciones a otros servidores

### ⚡ **Acciones Automáticas**
- **1era infracción**: Advertencia automática
- **2da infracción**: Timeout de 10 minutos
- **3era infracción**: Timeout de 1 hora
- **4ta infracción**: Ban temporal de 24 horas

### 📋 **Logs Automáticos**
- Mensajes eliminados
- Usuarios baneados/desbaneados
- Cambios de roles
- Entradas/salidas del servidor
- Uso de comandos del bot

---

## 🎯 **CANALES ESPECIALES DEL BOT**

### 🤖 **Comandos Principales**
```
/verify - Verificación con Roblox
/scrape - Buscar servidores VIP
/game - Buscar juegos por nombre
/profile - Ver perfil de usuario
/coins - Sistema de monedas
/marketplace - Marketplace comunitario
/report - Reportar servidores
/stats - Estadísticas del usuario
```

### 🔄 **Canales de Actividad Automática**
- **#logs-bot**: Actividad del bot cada 5 minutos
- **#nuevos-servidores**: Notificación de servidores encontrados
- **#usuarios-verificados**: Anuncio de nuevas verificaciones
- **#marketplace-activity**: Actividad del marketplace

---

## 📈 **MÉTRICAS Y ANALYTICS**

### 📊 **Estadísticas Tracked**
- Usuarios activos diarios/semanales
- Comandos usados por hora
- Servidores VIP encontrados
- Verificaciones completadas
- Actividad del marketplace
- Errores y bugs reportados

### 🎯 **Objetivos del Servidor**
- **100+ usuarios verificados**
- **500+ servidores VIP en base de datos**
- **10+ transacciones marketplace diarias**
- **95%+ uptime del bot**
- **<5 segundos tiempo de respuesta promedio**

---

## 🔐 **SEGURIDAD Y MODERACIÓN**

### 🛡️ **Niveles de Seguridad**
- **Nivel 1**: Verificación por email
- **Anti-raid**: Detección de entrada masiva
- **Anti-spam**: Rate limiting automático
- **Filter explicit**: Contenido explícito bloqueado

### 👮 **Staff Guidelines**
1. **Respuesta dentro de 2 horas** a tickets de soporte
2. **Verificación manual** de reportes importantes
3. **Backup diario** de configuraciones
4. **Review semanal** de métricas y logs

---

## 🎉 **EVENTOS Y ACTIVIDADES**

### 🎪 **Eventos Programados**
- **Lunes**: Actualización de estadísticas semanales
- **Miércoles**: Review de nuevos servidores VIP
- **Viernes**: Eventos comunitarios y sorteos
- **Domingo**: Mantenimiento y actualizaciones del bot

### 🏆 **Sistema de Recompensas**
- **Daily Login**: 10 monedas por día activo
- **Weekly Activity**: Bono de 100 monedas
- **Referrals**: 50 monedas por usuario referido
- **Bug Reports**: 25 monedas por bug válido reportado

---

## 📞 **CONTACTO Y SOPORTE**

### 🎫 **Sistema de Tickets**
- Categorías: Soporte General, Bug Report, VIP Support, Trading Issues
- Tiempo de respuesta: <2 horas (normal), <30 min (VIP)
- Escalación automática después de 24 horas sin respuesta

### 📧 **Contacto Directo**
- **Owner**: hesiz#0001
- **Bot Support**: rbxservers@support.com
- **Emergency**: Canal #contacto-staff

---

*Última actualización: Enero 2025*
*Versión: 2.0*
*Creado para RbxServers Discord Bot*
