
import discord
from discord.ext import commands
import json
import time
import secrets
import string
import hashlib
import logging
from datetime import datetime
from aiohttp import web
import asyncio

logger = logging.getLogger(__name__)

class UserAccessCodeSystem:
    def __init__(self):
        self.access_codes_file = "user_access_codes.json"
        self.access_codes = {}
        self.load_access_codes()

    def load_access_codes(self):
        """Cargar códigos de acceso desde archivo"""
        try:
            with open(self.access_codes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.access_codes = data.get('codes', {})
                # Limpiar códigos expirados al cargar
                self.cleanup_expired_codes()
                logger.info(f"<:1000182750:1396420537227411587> Códigos de acceso cargados: {len(self.access_codes)}")
        except FileNotFoundError:
            self.access_codes = {}
            logger.info("<:1000182750:1396420537227411587> Archivo de códigos no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error cargando códigos: {e}")
            self.access_codes = {}

    def save_access_codes(self):
        """Guardar códigos de acceso a archivo"""
        try:
            data = {
                'codes': self.access_codes,
                'last_updated': datetime.now().isoformat(),
                'total_codes': len(self.access_codes)
            }
            with open(self.access_codes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"<:1000182750:1396420537227411587> Códigos guardados: {len(self.access_codes)}")
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error guardando códigos: {e}")

    def generate_user_code(self, user_id: str) -> str:
        """Generar un nuevo código de acceso para un usuario"""
        # Invalidar código anterior si existe
        self.invalidate_user_code(user_id)
        
        # Generar nuevo código único
        code = self.generate_unique_code()
        
        # Guardar código con información del usuario
        self.access_codes[code] = {
            'user_id': user_id,
            'created_at': time.time(),
            'expires_at': time.time() + (24 * 60 * 60),  # 24 horas
            'uses': 0,
            'max_uses': 50,  # Límite de usos
            'active': True
        }
        
        self.save_access_codes()
        logger.info(f"<:verify:1396087763388072006> Código generado para usuario {user_id}: {code}")
        return code

    def generate_unique_code(self) -> str:
        """Generar un código único de 12 caracteres"""
        while True:
            # Generar código de 12 caracteres alfanuméricos
            code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            
            # Verificar que no exista ya
            if code not in self.access_codes:
                return code

    def invalidate_user_code(self, user_id: str):
        """Invalidar código anterior del usuario"""
        codes_to_remove = []
        for code, data in self.access_codes.items():
            if data.get('user_id') == user_id:
                codes_to_remove.append(code)
        
        for code in codes_to_remove:
            del self.access_codes[code]
            logger.info(f"<:1000182563:1396420770904932372> Código anterior invalidado: {code}")

    def cleanup_expired_codes(self):
        """Limpiar códigos expirados"""
        current_time = time.time()
        expired_codes = []
        
        for code, data in self.access_codes.items():
            if current_time > data.get('expires_at', 0):
                expired_codes.append(code)
        
        for code in expired_codes:
            del self.access_codes[code]
        
        if expired_codes:
            logger.info(f"<:1000182750:1396420537227411587> Códigos expirados limpiados: {len(expired_codes)}")
            self.save_access_codes()

    def validate_code(self, code: str) -> dict:
        """Validar un código y devolver información"""
        # Limpiar códigos expirados primero
        self.cleanup_expired_codes()
        
        # Log para debug
        logger.info(f"<:1000182657:1396060091366637669> Validando código: '{code}' (longitud: {len(code)})")
        logger.info(f"<:1000182750:1396420537227411587> Códigos disponibles: {list(self.access_codes.keys())}")
        
        # Verificar formato del código
        if not code or len(code) != 12:
            logger.warning(f"<:1000182563:1396420770904932372> Código con formato inválido: '{code}' (longitud: {len(code)})")
            return {
                'valid': False,
                'error': 'Formato de código inválido (debe tener 12 caracteres)',
                'debug_info': f'Código recibido: "{code}" (longitud: {len(code)})'
            }
        
        # Verificar si el código existe
        if code not in self.access_codes:
            logger.warning(f"<:1000182563:1396420770904932372> Código no encontrado: {code}")
            available_codes = list(self.access_codes.keys())
            return {
                'valid': False,
                'error': 'Código no encontrado o inválido',
                'debug_info': f'Códigos disponibles: {len(available_codes)} códigos activos'
            }
        
        code_data = self.access_codes[code]
        current_time = time.time()
        
        # Verificar si está activo
        if not code_data.get('active', True):
            logger.warning(f"<:1000182563:1396420770904932372> Código desactivado: {code}")
            return {
                'valid': False,
                'error': 'Código desactivado',
                'debug_info': 'El código fue desactivado manualmente'
            }
        
        # Verificar expiración
        expires_at = code_data.get('expires_at', 0)
        if current_time > expires_at:
            hours_expired = int((current_time - expires_at) / 3600)
            logger.warning(f"<:1000182563:1396420770904932372> Código expirado: {code} (expiró hace {hours_expired} horas)")
            return {
                'valid': False,
                'error': 'Código expirado',
                'debug_info': f'Expiró hace {hours_expired} horas'
            }
        
        # Verificar límite de usos
        uses = code_data.get('uses', 0)
        max_uses = code_data.get('max_uses', 50)
        if uses >= max_uses:
            logger.warning(f"<:1000182563:1396420770904932372> Código sin usos restantes: {code} ({uses}/{max_uses})")
            return {
                'valid': False,
                'error': 'Código ha alcanzado el límite de usos',
                'debug_info': f'Usos agotados: {uses}/{max_uses}'
            }
        
        # Incrementar contador de usos
        self.access_codes[code]['uses'] += 1
        self.access_codes[code]['last_used'] = current_time
        self.save_access_codes()
        
        logger.info(f"<:verify:1396087763388072006> Código validado exitosamente: {code} (usos: {self.access_codes[code]['uses']}/50)")
        
        return {
            'valid': True,
            'user_id': code_data['user_id'],
            'created_at': code_data['created_at'],
            'expires_at': code_data['expires_at'],
            'uses': self.access_codes[code]['uses'],
            'max_uses': code_data['max_uses']
        }

    def get_user_info(self, user_id: str) -> dict:
        """Obtener información completa del usuario desde diferentes sistemas"""
        try:
            # Importar aquí para evitar import circular
            from main import roblox_verification, bot
            from user_profile_system import user_profile_system
            
            # Obtener datos de verificación
            is_verified = roblox_verification.is_user_verified(user_id)
            verification_info = roblox_verification.verified_users.get(user_id, {})
            
            # Obtener datos del perfil completo
            profile_data = user_profile_system.collect_user_data(user_id)
            
            # Cargar datos de monedas
            coins_data = self.load_user_coins(user_id)
            
            # Obtener información de Discord del usuario
            discord_user_info = self.get_discord_user_info(user_id, bot)
            
            user_info = {
                'user_id': user_id,
                'discord_info': discord_user_info,
                'verification': {
                    'is_verified': is_verified,
                    'roblox_username': verification_info.get('roblox_username'),
                    'verified_at': verification_info.get('verified_at'),
                    'verification_code': verification_info.get('verification_code')
                },
                'servers': {
                    'total_servers': profile_data.get('total_servers', 0),
                    'total_games': profile_data.get('total_games', 0),
                    'servers_by_game': profile_data.get('servers_data', {}).get('servers_by_game', {}),
                    'main_game': profile_data.get('servers_data', {}).get('main_game')
                },
                'economy': {
                    'coins_balance': coins_data.get('balance', 0),
                    'total_earned': coins_data.get('total_earned', 0),
                    'total_transactions': coins_data.get('total_transactions', 0)
                },
                'activity': {
                    'total_commands': profile_data.get('total_commands', 0),
                    'active_days': profile_data.get('active_days', 0),
                    'first_seen': profile_data.get('first_seen'),
                    'last_activity': profile_data.get('last_activity')
                },
                'security': {
                    'warnings': roblox_verification.get_user_warnings(user_id),
                    'is_banned': roblox_verification.is_user_banned(user_id),
                    'risk_level': profile_data.get('risk_level', 'bajo'),
                    'is_trusted': profile_data.get('is_trusted', True)
                },
                'retrieved_at': time.time()
            }
            
            return user_info
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error obteniendo info del usuario {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': 'Error interno obteniendo información del usuario',
                'retrieved_at': time.time()
            }

    def load_user_coins(self, user_id: str) -> dict:
        """Cargar datos de monedas del usuario"""
        try:
            with open('user_coins.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_coins = data.get('user_coins', {}).get(user_id, {})
                
                transactions = user_coins.get('transactions', [])
                return {
                    'balance': user_coins.get('balance', 0),
                    'total_earned': user_coins.get('total_earned', 0),
                    'total_transactions': len(transactions),
                    'last_activity': transactions[-1]['timestamp'] if transactions else None
                }
        except:
            return {
                'balance': 0,
                'total_earned': 0,
                'total_transactions': 0,
                'last_activity': None
            }

    def get_discord_user_info(self, user_id: str, bot) -> dict:
        """Obtener información completa de Discord del usuario"""
        try:
            # Intentar obtener el usuario desde el cache del bot
            user = bot.get_user(int(user_id))
            
            if user:
                # Usuario encontrado en cache
                discord_info = {
                    'user_id': user_id,
                    'username': user.name,
                    'display_name': user.display_name,
                    'discriminator': user.discriminator,
                    'global_name': getattr(user, 'global_name', None),
                    'avatar_url': str(user.display_avatar.url) if user.display_avatar else None,
                    'avatar_hash': user.avatar.key if user.avatar else None,
                    'default_avatar_url': str(user.default_avatar.url),
                    'profile_url': f"https://discord.com/users/{user_id}",
                    'created_at': user.created_at.isoformat(),
                    'is_bot': user.bot,
                    'is_system': getattr(user, 'system', False),
                    'public_flags': user.public_flags.value if hasattr(user, 'public_flags') else 0,
                    'cached': True
                }
                
                # Información adicional de badges/flags
                if hasattr(user, 'public_flags'):
                    flags = user.public_flags
                    discord_info['badges'] = {
                        'staff': flags.staff,
                        'partner': flags.partner,
                        'hypesquad': flags.hypesquad,
                        'bug_hunter': flags.bug_hunter,
                        'hypesquad_bravery': flags.hypesquad_bravery,
                        'hypesquad_brilliance': flags.hypesquad_brilliance,
                        'hypesquad_balance': flags.hypesquad_balance,
                        'early_supporter': flags.early_supporter,
                        'verified_bot_developer': flags.verified_bot_developer,
                        'discord_certified_moderator': flags.discord_certified_moderator,
                        'active_developer': getattr(flags, 'active_developer', False)
                    }
                
                logger.info(f"<:verify:1396087763388072006> Info de Discord obtenida desde cache para {user_id}: {user.name}")
                return discord_info
            
            else:
                # Usuario no en cache, intentar fetch
                import asyncio
                try:
                    # Crear una nueva tarea asyncio para fetch
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Si ya hay un loop corriendo, crear una tarea
                        task = asyncio.create_task(bot.fetch_user(int(user_id)))
                        # No podemos await aquí, así que devolvemos info básica
                        pass
                    else:
                        # Si no hay loop, crear uno nuevo
                        user = loop.run_until_complete(bot.fetch_user(int(user_id)))
                        if user:
                            return self.get_discord_user_info(user_id, bot)
                except Exception as fetch_error:
                    logger.warning(f"<:1000182563:1396420770904932372> No se pudo hacer fetch del usuario {user_id}: {fetch_error}")
                
                # Fallback: información básica
                discord_info = {
                    'user_id': user_id,
                    'username': f'Usuario#{user_id[-4:]}',
                    'display_name': f'Usuario Desconocido',
                    'discriminator': '0000',
                    'global_name': None,
                    'avatar_url': f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png",
                    'avatar_hash': None,
                    'default_avatar_url': f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png",
                    'profile_url': f"https://discord.com/users/{user_id}",
                    'created_at': None,
                    'is_bot': False,
                    'is_system': False,
                    'public_flags': 0,
                    'cached': False,
                    'badges': {},
                    'note': 'Usuario no encontrado en cache del bot'
                }
                
                logger.warning(f"<:1000182563:1396420770904932372> Usuario {user_id} no encontrado, usando info por defecto")
                return discord_info
                
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error obteniendo info de Discord para {user_id}: {e}")
            
            # Fallback completo
            return {
                'user_id': user_id,
                'username': f'Error#{user_id[-4:]}',
                'display_name': 'Error al cargar',
                'discriminator': '0000',
                'global_name': None,
                'avatar_url': f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png",
                'avatar_hash': None,
                'default_avatar_url': f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png",
                'profile_url': f"https://discord.com/users/{user_id}",
                'created_at': None,
                'is_bot': False,
                'is_system': False,
                'public_flags': 0,
                'cached': False,
                'badges': {},
                'error': str(e)
            }

class UserAccessAPI:
    def __init__(self, access_code_system):
        self.access_code_system = access_code_system

    def setup_routes(self, app):
        """Configurar rutas de la API de acceso de usuarios"""
        
        try:
            # Registrar rutas directamente en el router
            app.router.add_post('/api/user-access/generate', self.generate_access_code)
            app.router.add_post('/api/user-access/verify', self.verify_access_code)
            app.router.add_get('/api/user-access/info/{code}', self.get_user_info_by_code)
            
            # Rutas OPTIONS para CORS
            app.router.add_options('/api/user-access/generate', self.handle_options)
            app.router.add_options('/api/user-access/verify', self.handle_options)
            app.router.add_options('/api/user-access/info/{code}', self.handle_options)
            
            logger.info("<:1000182750:1396420537227411587> Rutas de API de acceso de usuarios registradas exitosamente")
            
            # Verificar rutas registradas
            registered_routes = []
            for route in app.router.routes():
                route_info = str(route.resource)
                if '/api/user-access/' in route_info:
                    registered_routes.append(f"{route.method} {route_info}")
                    
            logger.info(f"<:verify:1396087763388072006> {len(registered_routes)} rutas de acceso registradas:")
            for route_info in registered_routes:
                logger.info(f"  ✅ {route_info}")
                
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error configurando rutas: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

    async def handle_options(self, request):
        """Manejar peticiones OPTIONS para CORS"""
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Access-Control-Max-Age': '86400'
            }
        )

    async def generate_access_code(self, request):
        """Generar un nuevo código de acceso para un usuario"""
        try:
            data = await request.json()
            user_id = str(data.get('user_id', ''))
            
            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)
            
            # Validar que el user_id sea un número válido
            try:
                int(user_id)
            except ValueError:
                return web.json_response({
                    'success': False,
                    'error': 'user_id debe ser un número válido'
                }, status=400)
            
            # Generar código
            code = self.access_code_system.generate_user_code(user_id)
            
            response_data = {
                'success': True,
                'access_code': code,
                'user_id': user_id,
                'expires_in_hours': 24,
                'max_uses': 50,
                'instructions': f'Usa este código para acceder a tu información: {code}',
                'api_endpoints': {
                    'verify': '/api/user-access/verify',
                    'get_info': f'/api/user-access/info/{code}'
                },
                'generated_at': time.time()
            }
            
            logger.info(f"<:verify:1396087763388072006> Código de acceso generado para usuario {user_id}")
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error generando código: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def verify_access_code(self, request):
        """Verificar si un código de acceso es válido"""
        try:
            data = await request.json()
            code = data.get('access_code', '').strip()
            
            logger.info(f"<:1000182657:1396060091366637669> Verificando código: {code}")
            
            if not code:
                return web.json_response({
                    'success': False,
                    'error': 'access_code es requerido'
                }, status=400)
            
            # Validar código usando el sistema simplificado
            validation_result = self.access_code_system.validate_code(code)
            
            if not validation_result['valid']:
                logger.warning(f"<:1000182563:1396420770904932372> Código inválido: {code} - {validation_result['error']}")
                return web.json_response({
                    'success': False,
                    'error': validation_result['error'],
                    'code_status': 'invalid',
                    'debug_info': validation_result.get('debug_info', 'Sin información adicional'),
                    'provided_code': code,
                    'code_length': len(code),
                    'timestamp': datetime.now().isoformat()
                }, status=400)
            
            response_data = {
                'success': True,
                'code_status': 'valid',
                'user_id': validation_result['user_id'],
                'uses_remaining': validation_result['max_uses'] - validation_result['uses'],
                'expires_at': validation_result['expires_at'],
                'verified_at': time.time()
            }
            
            logger.info(f"<:verify:1396087763388072006> Código verificado exitosamente: {code} para usuario {validation_result['user_id']}")
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error verificando código: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def get_user_info_by_code(self, request):
        """Obtener información del usuario usando un código de acceso"""
        try:
            code = request.match_info['code'].strip()
            
            logger.info(f"<:1000182584:1396049547838492672> Obteniendo info con código: {code}")
            
            if not code:
                return web.json_response({
                    'success': False,
                    'error': 'Código de acceso requerido'
                }, status=400)
            
            # Validar código
            validation_result = self.access_code_system.validate_code(code)
            
            if not validation_result['valid']:
                logger.warning(f"<:1000182563:1396420770904932372> Código inválido para info: {code}")
                return web.json_response({
                    'success': False,
                    'error': validation_result['error'],
                    'code_status': 'invalid'
                }, status=400)
            
            # Obtener información del usuario
            user_info = self.access_code_system.get_user_info(validation_result['user_id'])
            
            response_data = {
                'success': True,
                'code_info': {
                    'uses_remaining': validation_result['max_uses'] - validation_result['uses'],
                    'expires_at': validation_result['expires_at']
                },
                'user_info': user_info
            }
            
            logger.info(f"<:1000182584:1396049547838492672> Información de usuario entregada para código: {code}")
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error obteniendo info de usuario: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

# Instancia global del sistema
access_code_system = UserAccessCodeSystem()
user_access_api = UserAccessAPI(access_code_system)

def setup_user_access_api(app):
    """Configurar la API de acceso de usuarios en la app existente"""
    user_access_api.setup_routes(app)
    return user_access_api, access_code_system

# Sistema de auto-carga
def initialize_access_code_system():
    """Inicializar sistema de códigos de acceso automáticamente"""
    try:
        from auto_apis_loader import get_auto_loader
        loader = get_auto_loader()
        loader.force_load()
        logger.info("<:1000182751:1396420551798558781> Sistema de códigos inicializado automáticamente")
    except Exception as e:
        logger.warning(f"<:1000182563:1396420770904932372> Error en inicialización automática: {e}")

# Inicializar cuando se carga el módulo
initialize_access_code_system()
