
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
                self.access_codes = data.get('access_codes', {})
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
                'access_codes': self.access_codes,
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
        """Validar un código y obtener información del usuario"""
        self.cleanup_expired_codes()
        
        if code not in self.access_codes:
            return {
                'valid': False,
                'error': 'Código no encontrado o inválido'
            }
        
        code_data = self.access_codes[code]
        current_time = time.time()
        
        # Verificar si está activo
        if not code_data.get('active', True):
            return {
                'valid': False,
                'error': 'Código desactivado'
            }
        
        # Verificar expiración
        if current_time > code_data.get('expires_at', 0):
            return {
                'valid': False,
                'error': 'Código expirado'
            }
        
        # Verificar límite de usos
        if code_data.get('uses', 0) >= code_data.get('max_uses', 50):
            return {
                'valid': False,
                'error': 'Código ha alcanzado el límite de usos'
            }
        
        # Incrementar contador de usos
        self.access_codes[code]['uses'] += 1
        self.access_codes[code]['last_used'] = current_time
        self.save_access_codes()
        
        return {
            'valid': True,
            'user_id': code_data['user_id'],
            'created_at': code_data['created_at'],
            'expires_at': code_data['expires_at'],
            'uses': code_data['uses'],
            'max_uses': code_data['max_uses']
        }

    def get_user_info(self, user_id: str) -> dict:
        """Obtener información completa del usuario desde diferentes sistemas"""
        try:
            # Importar aquí para evitar import circular
            from main import roblox_verification
            from user_profile_system import user_profile_system
            
            # Obtener datos de verificación
            is_verified = roblox_verification.is_user_verified(user_id)
            verification_info = roblox_verification.verified_users.get(user_id, {})
            
            # Obtener datos del perfil completo
            profile_data = user_profile_system.collect_user_data(user_id)
            
            # Cargar datos de monedas
            coins_data = self.load_user_coins(user_id)
            
            user_info = {
                'user_id': user_id,
                'discord_info': {
                    'user_id': user_id,
                    'username': profile_data.get('username', 'Usuario Desconocido')
                },
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

class UserAccessAPI:
    def __init__(self, access_code_system):
        self.access_code_system = access_code_system

    def setup_routes(self, app):
        """Configurar rutas de la API de acceso de usuarios"""
        
        # Middleware de CORS específico para estas rutas
        @web.middleware
        async def cors_middleware(request, handler):
            if request.method == 'OPTIONS':
                response = web.Response()
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                return response
            
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response

        # Solo agregar middleware si no existe
        if cors_middleware not in app.middlewares:
            app.middlewares.append(cors_middleware)

        # Rutas de la API de códigos de acceso
        app.router.add_post('/api/user-access/generate', self.generate_access_code)
        app.router.add_post('/api/user-access/verify', self.verify_access_code)
        app.router.add_get('/api/user-access/info/{code}', self.get_user_info_by_code)
        app.router.add_options('/api/user-access/{path:.*}', self.handle_options)
        
        logger.info("<:1000182750:1396420537227411587> Rutas de API de acceso de usuarios configuradas")

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
            
            if not code:
                return web.json_response({
                    'success': False,
                    'error': 'access_code es requerido'
                }, status=400)
            
            # Validar código
            validation_result = self.access_code_system.validate_code(code)
            
            if not validation_result['valid']:
                return web.json_response({
                    'success': False,
                    'error': validation_result['error'],
                    'code_status': 'invalid'
                }, status=400)
            
            response_data = {
                'success': True,
                'code_status': 'valid',
                'user_id': validation_result['user_id'],
                'uses_remaining': validation_result['max_uses'] - validation_result['uses'],
                'expires_at': validation_result['expires_at'],
                'verified_at': time.time()
            }
            
            logger.info(f"<:verify:1396087763388072006> Código verificado exitosamente: {code}")
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
            
            if not code:
                return web.json_response({
                    'success': False,
                    'error': 'Código de acceso requerido'
                }, status=400)
            
            # Validar código
            validation_result = self.access_code_system.validate_code(code)
            
            if not validation_result['valid']:
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
