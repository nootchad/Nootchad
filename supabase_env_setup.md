# Configuración de Variables de Entorno para Supabase

## Variables Requeridas

Para que el sistema funcione completamente con Supabase, necesitas configurar las siguientes variables de entorno:

### 1. DATABASE_URL (Ya configurada ✅)
- **Descripción**: URL de conexión a la base de datos PostgreSQL de Supabase
- **Formato**: `postgresql://[usuario]:[contraseña]@[host]:[puerto]/[base_de_datos]`
- **Estado**: ✅ Ya configurada

### 2. SUPABASE_URL (Pendiente ⏳)
- **Descripción**: URL pública de tu proyecto de Supabase
- **Formato**: `https://[project-id].supabase.co`
- **Dónde encontrarla**: 
  1. Ve a tu proyecto en [Supabase Dashboard](https://supabase.com/dashboard)
  2. En la sección "Settings" → "API"
  3. Copia el valor de "Project URL"

### 3. SUPABASE_API_KEY (Pendiente ⏳)
- **Descripción**: Clave API anónima de Supabase para autenticación
- **Formato**: `eyJ...` (un JWT largo)
- **Dónde encontrarla**:
  1. Ve a tu proyecto en [Supabase Dashboard](https://supabase.com/dashboard)
  2. En la sección "Settings" → "API"
  3. Copia el valor de "anon/public" key (NO la service_role key)

## Cómo obtener las variables:

### Paso 1: Accede a tu proyecto Supabase
1. Ve a [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Selecciona tu proyecto
3. Ve a "Settings" (⚙️) en el menú lateral izquierdo
4. Haz clic en "API"

### Paso 2: Copia las variables
```
Project URL (SUPABASE_URL):
https://xxxxxxxxxxxxx.supabase.co

anon/public key (SUPABASE_API_KEY):
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSI...
```

### Paso 3: Configura las variables en Replit
1. Ve a la pestaña "Secrets" (🔒) en Replit
2. Agrega estas dos nuevas variables:
   - `SUPABASE_URL`: Tu Project URL
   - `SUPABASE_API_KEY`: Tu anon/public key

## Script SQL para Ejecutar

Después de configurar las variables, ejecuta el archivo `supabase_tables.sql` en el SQL Editor de Supabase:

1. Ve a tu proyecto Supabase
2. Abre "SQL Editor" desde el menú lateral
3. Crea una nueva query
4. Copia y pega todo el contenido de `supabase_tables.sql`
5. Ejecuta el script haciendo clic en "Run"

Esto creará todas las tablas necesarias para almacenar:
- ✅ Perfiles de usuarios
- ✅ Sistema de verificación de Roblox
- ✅ Sistema de monedas y transacciones
- ✅ Sistema anti-scam y anti-alt
- ✅ Reportes de scammers
- ✅ Listas negras y blancas
- ✅ Servidores de juegos
- ✅ Todas las demás funcionalidades

## Beneficios de usar Supabase:

1. **Escalabilidad**: PostgreSQL puede manejar millones de registros
2. **Rendimiento**: Índices optimizados para consultas rápidas
3. **Seguridad**: Autenticación y autorización integradas
4. **Backups**: Respaldos automáticos
5. **API REST**: Acceso automático via API REST
6. **Tiempo real**: Subscripciones en tiempo real a cambios en datos
7. **Dashboard**: Interfaz visual para ver y editar datos

## Siguiente paso:

Después de configurar las variables, el sistema migrará automáticamente todos los datos JSON existentes a Supabase.