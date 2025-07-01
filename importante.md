
# Documentación Técnica - VIP Server Scraper Bot

## Información General

Este bot de Discord está diseñado para extraer enlaces de servidores privados VIP de Roblox desde rbxservers.xyz y proporcionarlos a usuarios verificados a través de comandos slash.

## Limitaciones de Hosting

### Disponibilidad del Servicio

El bot funciona en una plataforma de desarrollo gratuita (Replit) que tiene las siguientes limitaciones:

- **No disponibilidad 24/7**: El bot no puede mantenerse ejecutándose continuamente debido a las restricciones de la plataforma gratuita
- **Activación manual requerida**: Debe ser activado manualmente cada cierto tiempo
- **Suspensión automática**: El servicio se suspende después de períodos de inactividad
- **Recursos limitados**: CPU y memoria restringidos que pueden afectar el rendimiento durante picos de uso

### Recomendaciones para Usuarios

- El bot puede no estar disponible en ciertos momentos
- Se recomienda exportar los enlaces importantes usando el comando `/export`
- Los datos se mantienen almacenados incluso cuando el bot está offline

## Sistema de Verificación

### Proceso de Verificación

El bot requiere verificación obligatoria antes del uso:

1. El usuario debe ejecutar `/verify [nombre_usuario_roblox]`
2. Se genera un código de verificación único
3. El usuario debe agregar este código a su descripción de Roblox
4. El sistema valida automáticamente la presencia del código
5. La verificación tiene duración de 24 horas

### Medidas Anti-Abuso

- **Sistema de advertencias**: Dos advertencias por usar nombres de usuario falsos
- **Baneos automáticos**: Ban de 7 días tras segunda advertencia
- **Prevención de duplicados**: No se permite el mismo nombre de usuario de Roblox para múltiples cuentas de Discord

## Sistema de Cooldowns

### Funcionamiento

- **Cooldown principal**: 5 minutos entre comandos de scraping
- **Cooldown de búsqueda**: 2 minutos para comandos de búsqueda
- **Limpieza automática**: Los cooldowns expirados se eliminan automáticamente cada 10 minutos

### Propósito

- Prevenir spam y sobrecarga del sistema
- Proteger la fuente de datos (rbxservers.xyz) de requests excesivos
- Mantener estabilidad del servicio para todos los usuarios

## Arquitectura de Datos

### Almacenamiento

- **Datos por usuario**: Cada usuario tiene su propia base de datos de enlaces
- **Categorización automática**: Los juegos se categorizan automáticamente
- **Persistencia**: Los datos se mantienen aunque el bot se reinicie

### Archivos de Sistema

- `followers.json`: Usuarios verificados y verificaciones pendientes
- `bans.json`: Usuarios baneados del sistema
- `warnings.json`: Registro de advertencias por usuario
- `vip_links.json`: Base de datos completa de enlaces VIP

## Limitaciones Técnicas

### Scraping

- **Límite por sesión**: Máximo 5 servidores procesados por ejecución
- **Dependencia externa**: Requiere acceso a rbxservers.xyz
- **Selenium WebDriver**: Necesita Chrome/Chromium instalado en el sistema
- **Tiempo de procesamiento**: 30-60 segundos promedio por sesión de scraping

### Capacidad

- **Usuarios concurrentes**: Limitado por recursos del hosting
- **Tamaño de base de datos**: Sin límite específico, pero afectado por almacenamiento disponible
- **Rate limiting**: Implementado para prevenir sobrecarga

## Comandos Principales

### Usuario Regular

- `/verify`: Verificación obligatoria
- `/scrape`: Extraer enlaces (acepta ID o nombre de juego)
- `/servertest`: Navegar por enlaces disponibles
- `/game`: Búsqueda automática por nombre
- `/export`: Exportar todos los enlaces a archivo de texto

### Administración

- `/admin`: Comandos de gestión (solo owner)
- `/debug`: Panel de administración avanzado (solo owner)

## Consideraciones de Seguridad

### Datos de Usuario

- No se almacenan contraseñas
- Solo se guarda el nombre de usuario de Roblox verificado
- Los enlaces son específicos por usuario

### Validación

- Verificación real contra la API de Roblox
- Prevención de bypass del sistema de verificación
- Logs completos de actividad para auditoría

## Recomendaciones de Uso

### Para Usuarios

1. Realizar verificación inmediatamente tras unirse
2. Usar `/export` regularmente para respaldar enlaces
3. Reportar problemas al administrador
4. Respetar los cooldowns del sistema

### Para Administradores

1. Monitorear logs regularmente
2. Realizar backups de datos importantes
3. Verificar estado del sistema periódicamente
4. Mantener el bot activo durante horas pico

## Mantenimiento

### Rutinas Recomendadas

- Limpieza de datos expirados semanal
- Backup de archivos críticos
- Monitoreo de tamaño de archivos de log
- Verificación de integridad de datos

### Solución de Problemas

- Restart del bot si hay problemas de conectividad
- Limpieza manual de cooldowns si es necesario
- Validación de integridad de datos tras interrupciones
- Verificación de estado de archivos del sistema

## Notas Importantes

- El bot NO está afiliado oficialmente con Roblox Corporation
- Los enlaces proporcionados provienen de fuentes públicas
- El uso está sujeto a los términos de servicio de Discord y Roblox
- La disponibilidad del servicio no está garantizada debido a las limitaciones de hosting
