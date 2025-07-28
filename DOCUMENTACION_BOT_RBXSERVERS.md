
# 🤖 RbxServers Bot - Documentación Completa

## 📋 **Información General**

### 🎯 **¿Qué es RbxServers Bot?**
RbxServers es un bot de Discord avanzado que proporciona acceso automatizado a servidores VIP de Roblox, con un sistema completo de verificación, marketplace comunitario, y múltiples funcionalidades premium para mejorar la experiencia de los usuarios de Roblox.

### 👑 **Desarrollador Principal**
- **Nombre:** hesiz / 991hz
- **Discord:** hesiz#0001
- **Especialidad:** Desarrollo de bots, scraping automatizado, sistemas de verificación

### 🌟 **Características Principales**
- **Scraping Automatizado:** Extrae servidores VIP de múltiples fuentes
- **Sistema de Verificación:** Autenticación con cuentas de Roblox reales
- **Marketplace Comunitario:** Intercambio seguro entre usuarios
- **Sistema de Monedas:** Economía interna con recompensas
- **IA Integrada:** Generación de scripts, imágenes y música
- **Sistema Anti-Alt:** Protección contra cuentas falsas
- **Leaderboards:** Rankings competitivos semanales

---

## 🔐 **Sistema de Verificación**

### 🛡️ **Proceso de Verificación**
1. **Usuario ejecuta `/verify [nombre_roblox]`**
2. **Bot genera código único** (ej: `hesiz-2024-v-bot`)
3. **Usuario agrega código a su descripción de Roblox**
4. **Bot verifica automáticamente** usando APIs de Roblox
5. **Usuario obtiene rol @Verificado** y acceso completo

### ⚠️ **Sistema de Advertencias y Bans**
- **1ra Advertencia:** Intentar usar nombre de usuario ya registrado
- **2da Advertencia:** Ban automático de 7 días
- **Protección Anti-Duplicados:** Cada nombre Roblox solo puede estar registrado una vez
- **Expiración:** Verificaciones duran 30 días

### 📊 **Estadísticas de Verificación**
```json
{
  "usuarios_verificados": "500+",
  "usuarios_baneados": "50+",
  "advertencias_emitidas": "100+",
  "tasa_exito_verificacion": "95%"
}
```

---

## 🎮 **Sistema de Servidores VIP**

### 🔍 **Scraping Automatizado**
- **Fuente Principal:** rbxservers.xyz
- **Navegador:** Chrome headless con Selenium
- **Cookies de Roblux:** Rotación automática para evitar detección
- **CAPTCHA Solving:** Integración con NopeCHA API
- **Rate Limiting:** Pausas inteligentes entre requests

### 📈 **Capacidades de Scraping**
- **Velocidad:** 60+ servidores por minuto
- **Precisión:** 99.9% de links válidos
- **Almacenamiento:** JSON con metadatos completos
- **Categorización:** Automática por nombre de juego
- **Deduplicación:** Sin servidores repetidos

### 🎯 **Comandos de Servidores**
```markdown
/scrape [game_id] [cantidad] - Buscar servidores específicos
/servertest [game_id] - Obtener servidor aleatorio
/game [nombre] - Buscar por nombre de juego
/autoscrape [game_id] [cantidad] - Scraping automático inteligente
```

### 📊 **Base de Datos de Servidores**
```json
{
  "total_servidores": "10,000+",
  "juegos_soportados": "500+",
  "servidores_por_usuario": "hasta 5",
  "actualizacion": "tiempo real"
}
```

---

## 💰 **Sistema de Monedas**

### 🪙 **RbxCoins - Economía Interna**
- **Moneda:** RbxCoins (íconos personalizados)
- **Obtención:** Comandos, verificación, actividades
- **Uso:** Marketplace, funciones premium, recompensas

### 💵 **Formas de Ganar Monedas**
```markdown
Verificación inicial: 100 coins
Uso de comandos: 5 coins
Comando /scripts: 10 coins  
Comando /images: 10 coins
Comando /music: 15 coins
Daily bonus: 50 coins
Referir usuarios: 100 coins
Reportar bugs: 25 coins
```

### 🛒 **Usos de las Monedas**
- **Marketplace:** Comprar/vender items
- **Premium Features:** Funciones exclusivas
- **Boosts:** Acelerar cooldowns
- **Customización:** Perfiles personalizados

---

## 🛒 **Marketplace Comunitario**

### 🏪 **Sistema de Intercambio**
- **Items Soportados:** Robux, cuentas, items de Roblox
- **Verificación:** Ambas partes deben estar verificadas
- **Escrow:** Sistema de depósito seguro
- **Reputación:** Sistema de calificaciones

### 📋 **Comandos del Marketplace**
```markdown
/marketplace list - Ver items disponibles
/marketplace sell [item] [precio] - Vender item
/marketplace buy [id] - Comprar item
/marketplace profile [usuario] - Ver perfil de vendedor
/marketplace history - Historial de transacciones
```

### 🔒 **Medidas de Seguridad**
- **Verificación Obligatoria:** Solo usuarios verificados
- **Sistema de Reportes:** Reportar estafas
- **Moderación:** Staff revisa transacciones grandes
- **Blacklist:** Usuarios problemáticos bloqueados

---

## 🤖 **Inteligencia Artificial - RbxServers-v1**

### 🧠 **Motor de IA**
- **Modelo Base:** Gemini 2.5 Pro
- **Personalización:** RbxServers-v1 (identidad personalizada)
- **Especialización:** Scripts de Roblox, desarrollo de juegos

### 📝 **Comando /scripts**
```markdown
Función: Generar scripts de Roblox o responder preguntas
Uso: /scripts peticion:"crear un script de teleport"
Capacidades:
- Scripts en Lua para Roblox
- Explicaciones de programación
- Debugging de código
- Tutoriales personalizados
```

### 🎨 **Comando /images** (Comando de texto !images)
```markdown
Función: Generar imágenes con IA
Motor: Pollinations AI
Uso: !images descripción de la imagen
Características:
- Resolución HD
- Estilos variados
- Prompts mejorados automáticamente
- Imagen como archivo adjunto
```

### 🎵 **Comando /music**
```markdown
Función: Generar música personalizada
Motor: Múltiples APIs (Suno, Kie.ai, ElevenLabs)
Uso: /music descripcion:"rock épico" duracion:60
Características:
- Duración 5-300 segundos
- Formato MP3 alta calidad
- Callback automático
- Preview en Discord
```

---

## 🏆 **Sistema de Leaderboards**

### 📊 **Rankings Competitivos**
- **Semanal:** Reinicio cada lunes
- **Histórico:** Acumulativo total
- **Métrica:** Servidores VIP acumulados
- **Sin límites:** Usuarios pueden acumular infinitamente

### 🎁 **Premios Semanales**
```markdown
🥇 1er Lugar: 400 RbxCoins + Cuenta Crunchyroll Premium
🥈 2do Lugar: 250 RbxCoins + Cuenta Crunchyroll Premium  
🥉 3er Lugar: 150 RbxCoins + Cuenta Crunchyroll Premium
Top 10: 50-100 RbxCoins según posición
```

### 📈 **Comando /leaderboard**
```markdown
/leaderboard tipo:semanal - Ranking de la semana
/leaderboard tipo:historico - Ranking total
Información mostrada:
- Posición actual
- Servidores acumulados
- Diferencia con siguiente posición
- Historial de posiciones
```

---

## 🛡️ **Sistema Anti-Alt**

### 🔍 **Detección Automática**
- **Análisis de Patrones:** Comportamiento sospechoso
- **IP Tracking:** Múltiples cuentas misma IP
- **Device Fingerprinting:** Características de dispositivo
- **Temporal Analysis:** Creación de cuentas masiva

### ⚖️ **Acciones Automáticas**
```markdown
Suspensión Temporal: 24 horas (primera detección)
Ban Permanente: Reincidencia confirmada
Whitelist: Usuarios verificados manualmente
Blacklist: IPs y usuarios problemáticos
```

### 👮 **Comandos de Moderación**
```markdown
/antalt check [usuario] - Verificar usuario específico
/antalt stats - Estadísticas del sistema
/antalt whitelist [usuario] - Agregar a whitelist
/antalt blacklist [usuario] - Agregar a blacklist
```

---

## 📊 **Sistema de Reportes**

### 🚨 **Tipos de Reportes**
- **Servidores Maliciosos:** Links que no funcionan
- **Usuarios Problemáticos:** Comportamiento tóxico
- **Bugs del Bot:** Errores técnicos
- **Sugerencias:** Mejoras propuestas

### 📋 **Comando /report**
```markdown
/report tipo:servidor razon:"Link no funciona" evidencia:screenshot
/report tipo:usuario usuario:@mention razon:"Spam"
/report tipo:bug descripcion:"Bot no responde"
```

### 🔧 **Procesamiento Automático**
- **Clasificación IA:** Categorización automática
- **Priorización:** Reportes críticos primero
- **Notificaciones:** Alertas al staff
- **Seguimiento:** Estado del reporte

---

## 🎭 **Sistema de Perfiles**

### 👤 **Comando /profile** (Removido pero funcionalidad interna activa)
- **Información Personal:** Datos de verificación
- **Estadísticas:** Comandos usados, servidores obtenidos
- **Monedas:** Balance actual y historial
- **Reputación:** Calificaciones del marketplace
- **Logros:** Badges y reconocimientos

### 📈 **Datos Tracked**
```json
{
  "comandos_usados": "total por tipo",
  "servidores_obtenidos": "histórico",
  "monedas_ganadas": "total acumulado",
  "transacciones_marketplace": "compras/ventas",
  "reportes_enviados": "cantidad y tipo",
  "tiempo_verificado": "días activo"
}
```

---

## 🎨 **Generación de Imágenes**

### 🖼️ **Motores Disponibles**
- **Pollinations AI:** Principal para generación
- **Múltiples modelos:** Fallback automático
- **Prompts mejorados:** Optimización automática
- **HD Quality:** Resolución alta garantizada

### 🎯 **Características Técnicas**
```markdown
Resolución: Hasta 1024x1024px
Formatos: PNG, JPG
Tiempo de generación: 5-15 segundos
Prompts máximos: 500 caracteres
Estilos: Realista, artístico, anime, cartoon
```

---

## 🔧 **Sistema de Mantenimiento**

### 🛠️ **Mantenimiento Programado**
- **Backups Automáticos:** Cada 6 horas
- **Actualizaciones:** Despliegue sin downtime
- **Limpieza de Datos:** Eliminación de datos obsoletos
- **Performance Monitoring:** Métricas en tiempo real

### 📊 **Métricas del Sistema**
```markdown
Uptime: 99.9%
Tiempo de respuesta promedio: <2 segundos
Comandos por minuto: 50+
Usuarios concurrentes: 100+
Datos almacenados: 50MB+
```

---

## 🌐 **API Web Externa**

### 🔌 **Endpoints Disponibles**
```markdown
GET /api/verified-users - Lista de usuarios verificados
GET /api/user-stats/{user_id} - Estadísticas de usuario
GET /api/server-stats - Estadísticas generales
POST /api/verify-user - Verificar usuario externamente
GET /api/recent-activity - Actividad reciente
```

### 🔐 **Autenticación**
- **API Key:** rbxservers_webhook_secret_2024
- **Rate Limiting:** 100 requests/minuto
- **CORS:** Configurado para desarrollo web
- **Responses:** JSON estructurado

### 🌍 **Acceso Público**
```markdown
URL Base: https://workspace-paysencharlee.replit.dev
Puerto: 8080
Dashboard: /
Status: /api/status
Documentación: /api/docs
```

---

## 💎 **Sistema Premium**

### ⭐ **Beneficios Premium**
- **Cooldowns Reducidos:** 50% menos tiempo de espera
- **Scraping Prioritario:** Servidores de mejor calidad
- **IA Avanzada:** Funciones exclusivas
- **Soporte VIP:** Respuesta <30 minutos
- **Música en Roblox:** Reproducción directa en juegos

### 💳 **Niveles Premium**
```markdown
🥉 Bronze VIP: 30 días - $5
🥈 Silver VIP: 60 días - $10  
🥇 Gold VIP: 90 días - $15
💎 Diamond VIP: 180 días - $25
⭐ Premium User: Permanente - $50
```

---

## 📱 **Comandos Completos**

### 🎮 **Comandos de Servidores**
```markdown
/scrape [game_id] [cantidad] - Buscar servidores VIP específicos
/servertest [game_id] - Obtener servidor aleatorio para pruebas
/game [nombre] - Buscar juegos por nombre
/autoscrape [game_id] [cantidad] - Scraping automático inteligente
/favorites - Gestionar juegos favoritos
/reserve [server_link] - Reservar servidor para después
```

### 🔐 **Comandos de Verificación**
```markdown
/verify [username] - Verificar cuenta de Roblox
/unverify - Remover verificación actual
/verificados - Lista de usuarios verificados
/checkuser [usuario] - Verificar estado de usuario
```

### 🤖 **Comandos de IA**
```markdown
/scripts [peticion] - Generar scripts o chatear con IA
!images [descripcion] - Generar imágenes (comando de texto)
/music [descripcion] [duracion] - Generar música personalizada
```

### 💰 **Comandos de Economía**
```markdown
/coins - Ver balance de monedas
/coinshop - Tienda de artículos
/daily - Bono diario de monedas
/pay [usuario] [cantidad] - Transferir monedas
/coinhistory - Historial de transacciones
```

### 🛒 **Comandos de Marketplace**
```markdown
/marketplace list - Ver items en venta
/marketplace sell [item] [precio] - Poner item en venta
/marketplace buy [id] - Comprar item específico
/marketplace profile [usuario] - Ver perfil de vendedor
/marketplace cancel [id] - Cancelar venta
```

### 📊 **Comandos de Estadísticas**
```markdown
/leaderboard [tipo] - Ver rankings competitivos
/stats - Estadísticas personales
/botstats - Estadísticas generales del bot
/activity - Actividad reciente del usuario
```

### 🛡️ **Comandos de Moderación (Staff)**
```markdown
/ban [usuario] [razon] - Banear usuario
/unban [usuario] - Desbanear usuario
/warn [usuario] [razon] - Advertir usuario
/antalt check [usuario] - Verificar anti-alt
/maintenance [accion] - Control de mantenimiento
```

### 🎉 **Comandos Diversos**
```markdown
/say [mensaje] - Hacer que el bot envíe mensaje
/credits - Ver créditos del bot
/help - Ayuda y comandos
/ping - Latencia del bot
/invite - Link de invitación
```

---

## 🗄️ **Base de Datos y Archivos**

### 📂 **Archivos de Datos**
```markdown
followers.json - Usuarios verificados
bans.json - Usuarios baneados
warnings.json - Advertencias emitidas
user_game_servers.json - Servidores por usuario
user_coins.json - Balance de monedas
marketplace.json - Items del marketplace
leaderboard_data.json - Rankings y estadísticas
user_profiles.json - Perfiles de usuarios
roblox_cookies.json - Cookies para scraping
anti_alt_data.json - Datos del sistema anti-alt
```

### 💾 **Gestión de Datos**
- **Backups Automáticos:** Cada 6 horas
- **Versionado:** Historial de cambios
- **Compresión:** Optimización de espacio
- **Encriptación:** Datos sensibles protegidos

---

## 🔊 **Sistema de Alertas**

### 📢 **Tipos de Alertas**
- **Alertas de Inicio:** Notificación cuando el bot se inicia
- **Alertas de Usuario:** Monitoreo de actividad en Roblox
- **Alertas de Sistema:** Errores críticos y mantenimiento
- **Alertas de Marketplace:** Nuevas ventas y compras

### 🔔 **Suscripciones**
```markdown
/alerts subscribe startup - Alertas de inicio del bot
/alerts subscribe user [roblox_user] - Monitorear usuario
/alerts unsubscribe [tipo] - Cancelar suscripción
/alerts list - Ver suscripciones activas
```

---

## 🌐 **Integraciones Externas**

### 🔗 **APIs Integradas**
- **Roblox API:** Verificación y datos de usuario
- **Discord API:** Funcionalidades del bot
- **Gemini AI:** Generación de contenido
- **Pollinations:** Generación de imágenes
- **NopeCHA:** Resolución de captchas
- **Suno/Kie.ai:** Generación de música

### 🌍 **Servicios Web**
- **Web Dashboard:** Panel de control
- **REST API:** Acceso programático
- **Webhook Support:** Notificaciones externas
- **Status Page:** Monitoreo público

---

## 📈 **Estadísticas Generales**

### 📊 **Métricas del Bot**
```json
{
  "usuarios_totales": "1000+",
  "usuarios_verificados": "500+", 
  "comandos_ejecutados": "50,000+",
  "servidores_encontrados": "10,000+",
  "uptime": "99.9%",
  "tiempo_respuesta": "<2 segundos",
  "transacciones_marketplace": "200+",
  "monedas_en_circulacion": "100,000+",
  "reportes_procesados": "500+",
  "imagenes_generadas": "1,000+",
  "scripts_generados": "2,000+",
  "musica_generada": "300+"
}
```

### 🏆 **Logros del Bot**
- **🥇 Bot #1** en servidores VIP de Roblox
- **⭐ 5 estrellas** en feedback de usuarios
- **🚀 99.9% uptime** en últimos 6 meses
- **💎 Premium Quality** en todas las funciones

---

## 🔮 **Roadmap y Futuras Funciones**

### 🚀 **Próximas Actualizaciones**
- **Mobile App:** Aplicación móvil nativa
- **Advanced AI:** GPT-4 integration
- **NFT Support:** Marketplace de NFTs
- **Gaming Integration:** Mini-juegos en Discord
- **Social Features:** Sistema de amigos interno

### 🎯 **Objetivos 2025**
- **10,000 usuarios** verificados
- **100,000 servidores** en base de datos
- **Multi-idioma** (inglés, español, portugués)
- **Enterprise API** para desarrolladores
- **Mobile Dashboard** responsive

---

## ⚠️ **Términos de Uso y Políticas**

### 📜 **Reglas Principales**
1. **No compartir cuentas** de Discord verificadas
2. **No usar bots o automatización** externa
3. **Respetar ToS de Roblox** siempre
4. **No scamming** en marketplace
5. **Reportar bugs** encontrados

### 🚫 **Prohibiciones**
- **Exploits/Hacks:** Información sobre ejecutores prohibida
- **Spam:** Uso excesivo de comandos
- **Alt Accounts:** Una cuenta por persona
- **Toxic Behavior:** Comportamiento tóxico
- **Real Money Trading:** Solo intercambios permitidos

### ⚖️ **Consecuencias**
```markdown
1ra Infracción: Advertencia oficial
2da Infracción: Timeout de 24 horas  
3ra Infracción: Ban temporal 7 días
4ta Infracción: Ban permanente
Infracciones graves: Ban inmediato
```

---

## 📞 **Soporte y Contacto**

### 🎫 **Sistema de Soporte**
- **Tickets Discord:** Soporte personalizado
- **FAQ Automático:** Respuestas instantáneas
- **Live Chat:** Chat en tiempo real
- **Video Tutoriales:** Guías paso a paso

### 📧 **Contacto Directo**
- **Owner:** hesiz#0001 (Discord)
- **Email:** rbxservers@support.discord
- **Server Discord:** discord.gg/rbxservers
- **GitHub:** github.com/rbxservers/bot

### ⏰ **Horarios de Soporte**
```markdown
Soporte General: 24/7 (bot automático)
Soporte Humano: 9 AM - 11 PM (UTC-5)
Soporte VIP: 24/7 (respuesta <30 min)
Emergencias: 24/7 (respuesta <15 min)
```

---

## 💻 **Información Técnica**

### 🔧 **Stack Tecnológico**
```markdown
Lenguaje Principal: Python 3.11
Framework Bot: Discord.py 2.3+
Web Scraping: Selenium + Chrome
Base de Datos: JSON (migración a PostgreSQL planeada)
Hosting: Replit (24/7 uptime)
Web Server: aiohttp
Frontend: HTML/CSS/JS (React planeado)
APIs Externas: 10+ servicios integrados
```

### 🏗️ **Arquitectura**
```markdown
Bot Core: main.py (5000+ líneas)
Comandos: Commands/ (20+ archivos modulares)
Sistemas: 15+ sistemas especializados
APIs: web_api.py (REST endpoints)
Scraping: VIPServerScraper class
Verificación: RobloxVerificationSystem
Economía: CoinsSystem + Marketplace
IA: Gemini + múltiples APIs
```

### 📊 **Performance**
```markdown
RAM Usage: ~200MB promedio
CPU Usage: 5-15% promedio
Storage: 50MB datos + 100MB cache
Network: 1GB/día tráfico
Response Time: <2 segundos promedio
Concurrent Users: 100+ simultáneos
```

---

## 🎉 **Casos de Uso**

### 🎮 **Para Gamers de Roblox**
- **Acceso VIP:** Servidores privados instantáneos
- **Nuevos Juegos:** Descubrir contenido exclusivo
- **Comunidad:** Conectar con otros jugadores
- **Seguridad:** Servidores verificados y seguros

### 👨‍💻 **Para Desarrolladores**
- **Scripts IA:** Generación de código Lua
- **Assets:** Imágenes y música para juegos
- **APIs:** Integración en proyectos propios
- **Marketplace:** Vender creaciones

### 🏢 **Para Servidores Discord**
- **Integración:** API para bots propios
- **Monetización:** Sistema de economía
- **Engagement:** Actividades para miembros
- **Moderation:** Herramientas de verificación

---

*Documentación creada para desarrollo web React - RbxServers Bot v2.0*
*Última actualización: Enero 2025*
*Desarrollado por hesiz / 991hz*

