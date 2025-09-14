"""
Cliente centralizado de Supabase para el bot RbxServers
Migración de sistemas JSON a Supabase PostgreSQL
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
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
        
    async def initialize(self):
        """Inicializar conexiones a Supabase"""
        try:
            if not self.url or not self.key:
                logger.error("❌ Variables SUPABASE_URL o SUPABASE_API_KEY no encontradas")
                return False
                
            # Cliente de Supabase para API REST
            self.client = create_client(self.url, self.key)
            
            # Pool de conexiones para PostgreSQL directo
            if self.database_url:
                self.db_pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                
            self.connected = True
            logger.info("✅ Conexión a Supabase establecida exitosamente")
            return True
            
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
        """Insertar o actualizar usuario"""
        try:
            if not self.connected:
                await self.initialize()
                
            if not self.db_pool:
                logger.error("❌ Pool de conexiones no disponible")
                return False
                
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
                user_data['user_id'], 
                user_data.get('username', 'Usuario Desconocido'),
                user_data.get('discriminator', '0000'),
                user_data.get('avatar_url'),
                user_data.get('created_at'),
                user_data.get('joined_at'),
                datetime.now(timezone.utc)
                )
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando usuario: {e}")
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
                
            logger.info("✅ Migración completada exitosamente:")
            logger.info(f"   👥 Usuarios: {results['users_migrated']}")
            logger.info(f"   ✅ Verificaciones: {results['verifications_migrated']}")
            logger.info(f"   💰 Monedas: {results['coins_migrated']}")
            logger.info(f"   📊 Transacciones: {results['transactions_migrated']}")
            logger.info(f"   🔒 Fingerprints: {results['fingerprints_migrated']}")
            
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