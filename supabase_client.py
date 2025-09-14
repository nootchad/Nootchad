"""
Cliente centralizado de Supabase para el bot RbxServers
Migración de sistemas JSON a Supabase PostgreSQL
"""

import os
import json
import asyncio
import logging
import ssl
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
import asyncpg
from supabase import create_client, Client

# Configurar logging
logger = logging.getLogger(__name__)

class SupabaseManager:
    """Gestor centralizado de Supabase para el bot"""
    
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_API_KEY')
        self.database_url = os.getenv('DATABASE_URL')
        self.client: Optional[Client] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.connected = False
        
        # Configuración de robustez
        self.max_retries = 3
        self.retry_delay = 1.0
        self.connection_timeout = 10.0
        self.command_timeout = 30.0
        self.pool_max_inactive_connection_lifetime = 300.0  # 5 minutos
    
    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Crear contexto SSL seguro para conexiones"""
        try:
            # Usar configuración SSL segura por defecto
            context = ssl.create_default_context()
            # MANTENER verificación de certificados habilitada para seguridad
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            return context
        except Exception as e:
            logger.warning(f"⚠️ Error creando contexto SSL: {e}")
            # Fallar de manera segura - mejor sin SSL que con SSL inseguro
            return None
    
    def parse_datetime_robust(self, datetime_str: str) -> Optional[datetime]:
        """Parsing robusto de fechas con múltiples formatos"""
        if not datetime_str or not isinstance(datetime_str, str):
            return None
        
        # Limpiar la cadena
        datetime_str = datetime_str.strip()
        if not datetime_str:
            return None
        
        # Lista de formatos de fecha compatibles
        formats = [
            "%Y-%m-%dT%H:%M:%S.%f%z",      # ISO 8601 con microsegundos y timezone
            "%Y-%m-%dT%H:%M:%S%z",         # ISO 8601 con timezone
            "%Y-%m-%dT%H:%M:%S.%fZ",       # ISO 8601 con Z
            "%Y-%m-%dT%H:%M:%SZ",          # ISO 8601 con Z sin microsegundos
            "%Y-%m-%dT%H:%M:%S.%f",        # ISO 8601 sin timezone
            "%Y-%m-%dT%H:%M:%S",           # ISO 8601 básico
            "%Y-%m-%d %H:%M:%S.%f",        # Formato SQL con microsegundos
            "%Y-%m-%d %H:%M:%S",           # Formato SQL básico
            "%Y-%m-%d",                    # Solo fecha
        ]
        
        # Reemplazar Z por +00:00 para compatibilidad
        datetime_str = datetime_str.replace('Z', '+00:00')
        
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                # Si no tiene timezone, asumir UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        
        # Intentar con datetime.fromisoformat como último recurso
        try:
            return datetime.fromisoformat(datetime_str)
        except ValueError:
            pass
        
        logger.warning(f"⚠️ No se pudo parsear fecha: {datetime_str}")
        return None
    
    def validate_user_id(self, user_id: Any) -> Optional[int]:
        """Validar y convertir user_id a entero"""
        try:
            if user_id is None:
                return None
            
            # Si ya es entero
            if isinstance(user_id, int):
                return user_id if user_id > 0 else None
            
            # Si es string, intentar convertir
            if isinstance(user_id, str):
                user_id = user_id.strip()
                if user_id.isdigit():
                    return int(user_id)
                # Remover caracteres no numéricos comunes
                user_id_clean = re.sub(r'[^\d]', '', user_id)
                if user_id_clean.isdigit():
                    return int(user_id_clean)
            
            return None
        except (ValueError, TypeError):
            return None
    
    async def retry_operation(self, operation, *args, **kwargs):
        """Ejecutar operación con reintentos automáticos"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # No reintentar ciertos errores
                if "authentication" in str(e).lower() or "permission" in str(e).lower():
                    break
                
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Backoff exponencial
                    logger.warning(f"⚠️ Intento {attempt + 1}/{self.max_retries} falló: {e}. Reintentando en {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Operación falló después de {self.max_retries} intentos")
        
        raise last_exception
    
    async def health_check(self) -> bool:
        """Verificar salud de las conexiones"""
        try:
            if not self.connected or not self.db_pool:
                return False
            
            # Prueba básica de conexión
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
                
        except Exception as e:
            logger.warning(f"⚠️ Health check falló: {e}")
            return False
    
    async def ensure_connected(self) -> bool:
        """Asegurar que hay conexión activa, reconectar si es necesario"""
        if not self.connected or not await self.health_check():
            logger.info("🔄 Reconectando a Supabase...")
            return await self.initialize()
        return True
    
    async def _execute_robust(self, operation_name: str, operation, *args, **kwargs):
        """Helper unificado para operaciones robustas con reconexión y reintentos"""
        # Asegurar conexión activa
        if not await self.ensure_connected():
            raise Exception(f"No se puede establecer conexión para {operation_name}")
        
        # Ejecutar operación con reintentos
        try:
            return await self.retry_operation(operation, *args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error en {operation_name}: {e}")
            raise
        
    async def initialize(self):
        """Inicializar conexiones a Supabase con configuración robusta"""
        try:
            if not self.url or not self.key:
                logger.error("❌ Variables SUPABASE_URL o SUPABASE_API_KEY no encontradas")
                return False
                
            # Verificar DATABASE_URL para operaciones críticas
            if not self.database_url:
                logger.error("❌ Variable DATABASE_URL no encontrada - requerida para migración de datos")
                return False
                
            # Cliente de Supabase para API REST
            self.client = create_client(self.url, self.key)
            
            # Configuración SSL robusta
            ssl_context = self._create_ssl_context()
            
            # Pool de conexiones para PostgreSQL directo con configuración robusta
            pool_kwargs = {
                'min_size': 2,
                'max_size': 10,
                'command_timeout': self.command_timeout,
                'server_settings': {
                    'application_name': 'RbxServers_Discord_Bot',
                    'timezone': 'UTC'
                },
                'max_inactive_connection_lifetime': self.pool_max_inactive_connection_lifetime,
            }
            
            # Configurar SSL seguro - usar URL con sslmode si no hay contexto
            if ssl_context:
                pool_kwargs['ssl'] = ssl_context
            elif 'sslmode' not in self.database_url:
                # Forzar SSL si no está explícitamente configurado
                if '?' in self.database_url:
                    self.database_url += '&sslmode=require'
                else:
                    self.database_url += '?sslmode=require'
            
            # Crear pool con timeout
            self.db_pool = await asyncio.wait_for(
                asyncpg.create_pool(self.database_url, **pool_kwargs),
                timeout=self.connection_timeout
            )
            
            # Verificar que la conexión funciona
            if not await self.health_check():
                logger.error("❌ Health check inicial falló")
                return False
                
            self.connected = True
            logger.info("✅ Conexión a Supabase establecida exitosamente con configuración robusta")
            return True
            
        except asyncio.TimeoutError:
            logger.error("❌ Timeout conectando a Supabase")
            return False
        except Exception as e:
            logger.error(f"❌ Error conectando a Supabase: {e}")
            return False
    
    async def close(self):
        """Cerrar conexiones"""
        if self.db_pool:
            await self.db_pool.close()
        self.connected = False
        logger.info("🔌 Conexiones a Supabase cerradas")
    
    # ====================================
    # GESTIÓN DE USUARIOS
    # ====================================
    
    async def upsert_user(self, user_data: Dict) -> bool:
        """Insertar o actualizar usuario con validación robusta"""
        try:
            # Asegurar conexión activa con reconexión automática
            if not await self.ensure_connected():
                return False
            
            # Validar datos de entrada
            user_id = self.validate_user_id(user_data.get('user_id'))
            if not user_id:
                logger.error("❌ user_id inválido")
                return False
            
            # Parsear fechas de forma robusta
            created_at = self.parse_datetime_robust(user_data.get('created_at'))
            joined_at = self.parse_datetime_robust(user_data.get('joined_at'))
            now = datetime.now(timezone.utc)
            
            # Ejecutar con reintentos automáticos
            async def _upsert_operation():
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO users (id, username, discriminator, avatar_url, created_at, joined_at, last_activity)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (id) DO UPDATE SET
                            username = EXCLUDED.username,
                            discriminator = EXCLUDED.discriminator,
                            avatar_url = EXCLUDED.avatar_url,
                            last_activity = EXCLUDED.last_activity,
                            updated_at = NOW()
                    """, 
                    user_id,
                    user_data.get('username', 'Usuario Desconocido'),
                    user_data.get('discriminator', '0000'),
                    user_data.get('avatar_url'),
                    created_at,
                    joined_at,
                    now
                    )
            
            await self.retry_operation(_upsert_operation)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error guardando usuario {user_data.get('user_id')}: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Obtener datos completos de usuario"""
        try:
            if not self.connected:
                await self.initialize()
                
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return None
                
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow("""
                    SELECT * FROM user_complete_profile WHERE id = $1
                """, user_id)
                
                if result:
                    return dict(result)
                return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuario {user_id}: {e}")
            return None
    
    # ====================================
    # SISTEMA DE VERIFICACIÓN
    # ====================================
    
    async def upsert_verification(self, user_id: int, verification_data: Dict) -> bool:
        """Insertar o actualizar verificación de usuario"""
        try:
            if not self.connected:
                await self.initialize()
                
            # Primero asegurar que el usuario existe
            await self.upsert_user({'user_id': user_id})
            
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_verification (user_id, is_verified, roblox_username, roblox_id, verification_code, verification_date, verified_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (user_id) DO UPDATE SET
                        is_verified = EXCLUDED.is_verified,
                        roblox_username = EXCLUDED.roblox_username,
                        roblox_id = EXCLUDED.roblox_id,
                        verification_code = EXCLUDED.verification_code,
                        verification_date = EXCLUDED.verification_date,
                        verified_at = EXCLUDED.verified_at,
                        updated_at = NOW()
                """,
                user_id,
                verification_data.get('is_verified', False),
                verification_data.get('roblox_username'),
                verification_data.get('roblox_id'),
                verification_data.get('verification_code'),
                verification_data.get('verification_date'),
                verification_data.get('verified_at')
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando verificación: {e}")
            return False
    
    async def get_verified_users(self) -> Dict:
        """Obtener todos los usuarios verificados"""
        try:
            if not self.connected:
                await self.initialize()
                
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return {'verified_users': {}}
                
            async with self.db_pool.acquire() as conn:
                results = await conn.fetch("""
                    SELECT user_id, roblox_username, verification_code, verified_at
                    FROM user_verification 
                    WHERE is_verified = true
                """)
                
                verified_users = {}
                for row in results:
                    verified_users[str(row['user_id'])] = {
                        'roblox_username': row['roblox_username'],
                        'verification_code': row['verification_code'],
                        'verified_at': row['verified_at'].timestamp() if row['verified_at'] else None
                    }
                
                return {'verified_users': verified_users}
        except Exception as e:
            logger.error(f"❌ Error obteniendo usuarios verificados: {e}")
            return {'verified_users': {}}
    
    # ====================================
    # SISTEMA DE MONEDAS
    # ====================================
    
    async def upsert_user_coins(self, user_id: int, coin_data: Dict) -> bool:
        """Insertar o actualizar monedas de usuario"""
        try:
            if not self.connected:
                await self.initialize()
                
            # Asegurar que el usuario existe
            await self.upsert_user({'user_id': user_id})
            
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_coins (user_id, balance, total_earned, total_transactions, last_activity)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id) DO UPDATE SET
                        balance = EXCLUDED.balance,
                        total_earned = EXCLUDED.total_earned,
                        total_transactions = EXCLUDED.total_transactions,
                        last_activity = EXCLUDED.last_activity,
                        updated_at = NOW()
                """,
                user_id,
                coin_data.get('balance', 0),
                coin_data.get('total_earned', 0),
                coin_data.get('total_transactions', 0),
                coin_data.get('last_activity')
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando monedas: {e}")
            return False
    
    async def add_coin_transaction(self, user_id: int, transaction: Dict) -> bool:
        """Agregar transacción de monedas"""
        try:
            if not self.connected:
                await self.initialize()
                
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO coin_transactions (user_id, type, amount, reason, item_id, item_name, quantity, description, balance_after, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                user_id,
                transaction.get('type'),
                transaction.get('amount'),
                transaction.get('reason'),
                transaction.get('item_id'),
                transaction.get('item_name'),
                transaction.get('quantity', 1),
                transaction.get('description'),
                transaction.get('balance_after'),
                transaction.get('timestamp', datetime.now(timezone.utc))
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando transacción: {e}")
            return False
    
    # ====================================
    # SISTEMA ANTI-ALT
    # ====================================
    
    async def upsert_user_fingerprint(self, user_id: int, fingerprint_data: Dict) -> bool:
        """Insertar o actualizar fingerprint de usuario"""
        try:
            if not self.connected:
                await self.initialize()
                
            await self.upsert_user({'user_id': user_id})
            
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_fingerprints (
                        user_id, discord_username, roblox_username, account_creation_date,
                        first_seen, last_activity, total_code_redemptions, failed_attempts,
                        trust_score, risk_level, flags, redeemed_codes, account_age_hours, account_age_days
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (user_id) DO UPDATE SET
                        discord_username = EXCLUDED.discord_username,
                        roblox_username = EXCLUDED.roblox_username,
                        account_creation_date = EXCLUDED.account_creation_date,
                        last_activity = EXCLUDED.last_activity,
                        total_code_redemptions = EXCLUDED.total_code_redemptions,
                        failed_attempts = EXCLUDED.failed_attempts,
                        trust_score = EXCLUDED.trust_score,
                        risk_level = EXCLUDED.risk_level,
                        flags = EXCLUDED.flags,
                        redeemed_codes = EXCLUDED.redeemed_codes,
                        account_age_hours = EXCLUDED.account_age_hours,
                        account_age_days = EXCLUDED.account_age_days,
                        updated_at = NOW()
                """,
                user_id,
                fingerprint_data.get('discord_username'),
                fingerprint_data.get('roblox_username'),
                fingerprint_data.get('account_creation_date'),
                fingerprint_data.get('first_seen'),
                fingerprint_data.get('last_activity', datetime.now(timezone.utc)),
                fingerprint_data.get('total_code_redemptions', 0),
                fingerprint_data.get('failed_attempts', 0),
                fingerprint_data.get('trust_score', 100),
                fingerprint_data.get('risk_level', 'low'),
                json.dumps(fingerprint_data.get('flags', [])),
                json.dumps(fingerprint_data.get('redeemed_codes', [])),
                fingerprint_data.get('account_age_hours'),
                fingerprint_data.get('account_age_days')
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando fingerprint: {e}")
            return False
    
    async def add_suspicious_activity(self, user_id: int, activity: Dict) -> bool:
        """Agregar actividad sospechosa"""
        try:
            if not self.connected:
                await self.initialize()
                
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO suspicious_activities (user_id, activity_type, details, severity, timestamp)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                activity.get('type'),
                activity.get('details'),
                activity.get('severity', 'low'),
                activity.get('timestamp', datetime.now(timezone.utc))
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando actividad sospechosa: {e}")
            return False
    
    # ====================================
    # LISTAS NEGRAS/BLANCAS
    # ====================================
    
    async def add_to_blacklist(self, user_id: int, reason: str, added_by: Optional[int] = None) -> bool:
        """Agregar usuario a lista negra"""
        try:
            if not self.connected:
                await self.initialize()
                
            await self.upsert_user({'user_id': user_id})
            
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_blacklist (user_id, reason, added_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        added_by = EXCLUDED.added_by,
                        added_at = NOW()
                """, user_id, reason, added_by)
            return True
        except Exception as e:
            logger.error(f"❌ Error agregando a blacklist: {e}")
            return False
    
    async def add_to_whitelist(self, user_id: int, reason: str, added_by: Optional[int] = None) -> bool:
        """Agregar usuario a lista blanca"""
        try:
            if not self.connected:
                await self.initialize()
                
            await self.upsert_user({'user_id': user_id})
            
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO user_whitelist (user_id, reason, added_by)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) DO UPDATE SET
                        reason = EXCLUDED.reason,
                        added_by = EXCLUDED.added_by,
                        added_at = NOW()
                """, user_id, reason, added_by)
            return True
        except Exception as e:
            logger.error(f"❌ Error agregando a whitelist: {e}")
            return False
    
    # ====================================
    # REPORTES DE SCAM
    # ====================================
    
    async def create_scam_report(self, report_data: Dict) -> bool:
        """Crear reporte de scam"""
        try:
            if not self.connected:
                await self.initialize()
                
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO scam_reports (
                        reported_user_id, reporter_user_id, report_type, description,
                        evidence_urls, status, severity
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                report_data.get('reported_user_id'),
                report_data.get('reporter_user_id'),
                report_data.get('report_type', 'scam'),
                report_data.get('description'),
                json.dumps(report_data.get('evidence_urls', [])),
                report_data.get('status', 'pending'),
                report_data.get('severity', 'medium')
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error creando reporte: {e}")
            return False
    
    # ====================================
    # MIGRACIÓN DE DATOS JSON
    # ====================================
    
    async def migrate_json_to_supabase(self) -> Dict:
        """Migrar todos los datos JSON existentes a Supabase"""
        results = {
            'users_migrated': 0,
            'verifications_migrated': 0,
            'coins_migrated': 0,
            'transactions_migrated': 0,
            'fingerprints_migrated': 0,
            'blacklist_migrated': 0,
            'whitelist_migrated': 0,
            'warnings_migrated': 0,
            'bans_migrated': 0,
            'cooldowns_migrated': 0,
            'errors': []
        }
        
        try:
            # Migrar perfiles de usuario
            try:
                with open('user_profiles.json', 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    
                for user_id, profile in profiles_data.get('user_profiles', {}).items():
                    if user_id == 'global':  # Saltar el perfil global
                        continue
                        
                    success = await self.upsert_user({
                        'user_id': int(user_id),
                        'username': profile.get('username'),
                        'discriminator': profile.get('discriminator'),
                        'avatar_url': profile.get('avatar_url'),
                        'created_at': profile.get('created_at'),
                        'joined_at': profile.get('joined_at')
                    })
                    
                    if success:
                        results['users_migrated'] += 1
                        
            except FileNotFoundError:
                logger.warning("⚠️ Archivo user_profiles.json no encontrado")
                
            # Migrar verificaciones
            try:
                with open('followers.json', 'r', encoding='utf-8') as f:
                    verification_data = json.load(f)
                    
                for user_id, verif in verification_data.get('verified_users', {}).items():
                    success = await self.upsert_verification(int(user_id), {
                        'is_verified': True,
                        'roblox_username': verif.get('roblox_username'),
                        'verification_code': verif.get('verification_code'),
                        'verified_at': datetime.fromtimestamp(verif.get('verified_at', 0), tz=timezone.utc) if verif.get('verified_at') else None
                    })
                    
                    if success:
                        results['verifications_migrated'] += 1
                        
            except FileNotFoundError:
                logger.warning("⚠️ Archivo followers.json no encontrado")
                
            # Migrar monedas y transacciones
            try:
                with open('user_coins.json', 'r', encoding='utf-8') as f:
                    coins_data = json.load(f)
                    
                for user_id, coin_info in coins_data.get('user_coins', {}).items():
                    # Migrar datos de monedas
                    success = await self.upsert_user_coins(int(user_id), coin_info)
                    if success:
                        results['coins_migrated'] += 1
                        
                    # Migrar transacciones
                    for transaction in coin_info.get('transactions', []):
                        success = await self.add_coin_transaction(int(user_id), transaction)
                        if success:
                            results['transactions_migrated'] += 1
                            
            except FileNotFoundError:
                logger.warning("⚠️ Archivo user_coins.json no encontrado")
                
            # Migrar fingerprints anti-alt
            try:
                with open('anti_alt_data.json', 'r', encoding='utf-8') as f:
                    anti_alt_data = json.load(f)
                    
                for user_id, fingerprint in anti_alt_data.get('user_fingerprints', {}).items():
                    success = await self.upsert_user_fingerprint(int(user_id), fingerprint)
                    if success:
                        results['fingerprints_migrated'] += 1
                        
            except FileNotFoundError:
                logger.warning("⚠️ Archivo anti_alt_data.json no encontrado")
                
            # Migrar cooldowns desde anti_alt_data.json
            try:
                with open('anti_alt_data.json', 'r', encoding='utf-8') as f:
                    anti_alt_data = json.load(f)
                    
                for user_id, user_cooldowns in anti_alt_data.get('cooldowns', {}).items():
                    for cooldown_type, cooldown_info in user_cooldowns.items():
                        try:
                            if not self.db_pool:
                                continue
                            async with self.db_pool.acquire() as conn:
                                await conn.execute("""
                                    INSERT INTO user_cooldowns (user_id, cooldown_type, expires_at, duration_minutes, set_at)
                                    VALUES ($1, $2, $3, $4, $5)
                                    ON CONFLICT (user_id, cooldown_type) DO UPDATE SET
                                        expires_at = EXCLUDED.expires_at,
                                        duration_minutes = EXCLUDED.duration_minutes,
                                        set_at = EXCLUDED.set_at
                                """,
                                int(user_id),
                                cooldown_type,
                                datetime.fromisoformat(cooldown_info.get('expires_at', '').replace('Z', '+00:00')) if cooldown_info.get('expires_at') else None,
                                cooldown_info.get('duration_minutes', 0),
                                datetime.fromisoformat(cooldown_info.get('set_at', '').replace('Z', '+00:00')) if cooldown_info.get('set_at') else None
                                )
                                results['cooldowns_migrated'] += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Error migrando cooldown {cooldown_type} para usuario {user_id}: {e}")
                            
            except FileNotFoundError:
                logger.warning("⚠️ Archivo anti_alt_data.json no encontrado para cooldowns")
                
            # Migrar blacklist
            try:
                with open('user_blacklist.json', 'r', encoding='utf-8') as f:
                    blacklist_data = json.load(f)
                    
                for user_entry in blacklist_data.get('blacklisted_users', []):
                    try:
                        if isinstance(user_entry, dict):
                            user_id = user_entry.get('user_id')
                            reason = user_entry.get('reason', 'Migrado desde JSON')
                        else:
                            user_id = user_entry
                            reason = 'Migrado desde JSON'
                            
                        success = await self.add_to_blacklist(int(user_id), reason)
                        if success:
                            results['blacklist_migrated'] += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Error migrando usuario a blacklist: {e}")
                        
            except FileNotFoundError:
                logger.warning("⚠️ Archivo user_blacklist.json no encontrado")
                
            # Migrar whitelist
            try:
                with open('user_whitelist.json', 'r', encoding='utf-8') as f:
                    whitelist_data = json.load(f)
                    
                for user_entry in whitelist_data.get('whitelisted_users', []):
                    try:
                        if isinstance(user_entry, dict):
                            user_id = user_entry.get('user_id')
                            reason = user_entry.get('reason', 'Migrado desde JSON')
                        else:
                            user_id = user_entry
                            reason = 'Migrado desde JSON'
                            
                        success = await self.add_to_whitelist(int(user_id), reason)
                        if success:
                            results['whitelist_migrated'] += 1
                    except Exception as e:
                        logger.warning(f"⚠️ Error migrando usuario a whitelist: {e}")
                        
            except FileNotFoundError:
                logger.warning("⚠️ Archivo user_whitelist.json no encontrado")
                
            # Migrar warnings
            try:
                with open('warnings.json', 'r', encoding='utf-8') as f:
                    warnings_data = json.load(f)
                    
                for user_id, warning_info in warnings_data.items():
                    if user_id.isdigit():
                        try:
                            if not self.db_pool:
                                continue
                            async with self.db_pool.acquire() as conn:
                                await conn.execute("""
                                    INSERT INTO user_warnings (user_id, warning_count, reason, issued_at)
                                    VALUES ($1, $2, $3, $4)
                                """,
                                int(user_id),
                                warning_info.get('count', 0) if isinstance(warning_info, dict) else 1,
                                warning_info.get('reason', 'Migrado desde JSON') if isinstance(warning_info, dict) else 'Migrado desde JSON',
                                datetime.now(timezone.utc)
                                )
                                results['warnings_migrated'] += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Error migrando warning para usuario {user_id}: {e}")
                            
            except FileNotFoundError:
                logger.warning("⚠️ Archivo warnings.json no encontrado")
                
            # Migrar bans
            try:
                with open('bans.json', 'r', encoding='utf-8') as f:
                    bans_data = json.load(f)
                    
                for user_id, ban_info in bans_data.items():
                    if user_id.isdigit():
                        try:
                            if not self.db_pool:
                                continue
                            async with self.db_pool.acquire() as conn:
                                await conn.execute("""
                                    INSERT INTO user_bans (user_id, is_banned, ban_reason, ban_time, ban_duration_days)
                                    VALUES ($1, $2, $3, $4, $5)
                                    ON CONFLICT (user_id) DO UPDATE SET
                                        is_banned = EXCLUDED.is_banned,
                                        ban_reason = EXCLUDED.ban_reason,
                                        ban_time = EXCLUDED.ban_time,
                                        ban_duration_days = EXCLUDED.ban_duration_days,
                                        updated_at = NOW()
                                """,
                                int(user_id),
                                ban_info.get('is_banned', True) if isinstance(ban_info, dict) else True,
                                ban_info.get('reason', 'Migrado desde JSON') if isinstance(ban_info, dict) else 'Migrado desde JSON',
                                datetime.fromisoformat(ban_info.get('ban_time', '').replace('Z', '+00:00')) if isinstance(ban_info, dict) and ban_info.get('ban_time') else datetime.now(timezone.utc),
                                ban_info.get('duration_days', 7) if isinstance(ban_info, dict) else 7
                                )
                                results['bans_migrated'] += 1
                        except Exception as e:
                            logger.warning(f"⚠️ Error migrando ban para usuario {user_id}: {e}")
                            
            except FileNotFoundError:
                logger.warning("⚠️ Archivo bans.json no encontrado")
                
            logger.info("✅ Migración completada exitosamente:")
            logger.info(f"   👥 Usuarios: {results['users_migrated']}")
            logger.info(f"   ✅ Verificaciones: {results['verifications_migrated']}")
            logger.info(f"   💰 Monedas: {results['coins_migrated']}")
            logger.info(f"   📊 Transacciones: {results['transactions_migrated']}")
            logger.info(f"   🔒 Fingerprints: {results['fingerprints_migrated']}")
            logger.info(f"   ⏱️ Cooldowns: {results['cooldowns_migrated']}")
            logger.info(f"   🚫 Blacklist: {results['blacklist_migrated']}")
            logger.info(f"   ✅ Whitelist: {results['whitelist_migrated']}")
            logger.info(f"   ⚠️ Warnings: {results['warnings_migrated']}")
            logger.info(f"   🔨 Bans: {results['bans_migrated']}")
            
        except Exception as e:
            error_msg = f"Error durante migración: {e}"
            results['errors'].append(error_msg)
            logger.error(f"❌ {error_msg}")
            
        return results

# Instancia global del gestor
supabase_manager = SupabaseManager()

# Funciones de compatibilidad para mantener la API existente
async def init_supabase():
    """Inicializar conexión a Supabase"""
    return await supabase_manager.initialize()

async def get_user_data(user_id: int):
    """Obtener datos de usuario - compatible con API existente"""
    return await supabase_manager.get_user(user_id)

async def save_user_data(user_id: int, data: Dict):
    """Guardar datos de usuario - compatible con API existente"""
    return await supabase_manager.upsert_user({**data, 'user_id': user_id})

async def migrate_all_data():
    """Migrar todos los datos JSON a Supabase"""
    return await supabase_manager.migrate_json_to_supabase()

# Verificar si tenemos las variables de entorno configuradas
def check_supabase_config():
    """Verificar configuración de Supabase"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_API_KEY')
    db_url = os.getenv('DATABASE_URL')
    
    if not url or not key:
        logger.error("❌ Variables SUPABASE_URL o SUPABASE_API_KEY no configuradas")
        return False
        
    if not db_url:
        logger.warning("⚠️ Variable DATABASE_URL no encontrada")
        
    logger.info("✅ Configuración de Supabase verificada")
    return True

if __name__ == "__main__":
    # Test básico de conexión
    import asyncio
    
    async def test_connection():
        if check_supabase_config():
            success = await init_supabase()
            if success:
                print("✅ Conexión a Supabase exitosa!")
                # Ejecutar migración si es necesario
                # results = await migrate_all_data()
                # print(f"📊 Resultados de migración: {results}")
            else:
                print("❌ Error conectando a Supabase")
        else:
            print("❌ Configuración de Supabase incompleta")
    
    asyncio.run(test_connection())