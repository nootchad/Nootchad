
from aiohttp import web
import json
import logging
from datetime import datetime
import time
import os

logger = logging.getLogger(__name__)

# Configuración de seguridad
WEBHOOK_SECRET = "rbxservers_webhook_secret_2024"

class WebAPI:
    def __init__(self, verification_system, scraper, remote_control):
        self.verification_system = verification_system
        self.scraper = scraper
        self.remote_control = remote_control
        
    def setup_routes(self, app):
        """Configurar rutas de la API web"""
        
        # Middleware de CORS para permitir acceso desde tu página web
        @web.middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        # Solo agregar middleware si no existe
        if cors_middleware not in app.middlewares:
            app.middlewares.append(cors_middleware)
        
        # Rutas para tu página web
        app.router.add_get('/api/verified-users', self.get_verified_users)
        app.router.add_get('/api/user-stats', self.get_user_statistics)
        app.router.add_get('/api/server-stats', self.get_server_statistics)
        app.router.add_get('/api/user-details/{user_id}', self.get_user_details)
        app.router.add_get('/api/bot-status', self.get_bot_status)
        app.router.add_get('/api/recent-activity', self.get_recent_activity)
        app.router.add_post('/api/authenticate', self.authenticate_request)
        app.router.add_options('/{path:.*}', self.handle_options)
        
        logger.info("🌐 API web configurada para acceso externo")
    
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
    
    def verify_auth(self, request):
        """Verificar autenticación de la petición"""
        auth_header = request.headers.get('Authorization', '')
        expected_header = f"Bearer {WEBHOOK_SECRET}"
        
        if auth_header != expected_header:
            logger.warning(f"🚫 Intento de acceso no autorizado desde {request.remote}")
            return False
        return True
    
    async def get_verified_users(self, request):
        """Obtener lista de usuarios verificados"""
        try:
            if not self.verify_auth(request):
                return web.json_response({
                    'error': 'Unauthorized access',
                    'message': 'Invalid API key'
                }, status=401)
            
            # Limpiar datos expirados primero
            self.verification_system.cleanup_expired_data()
            
            verified_users = []
            for discord_id, user_data in self.verification_system.verified_users.items():
                user_info = {
                    'discord_id': discord_id,
                    'roblox_username': user_data['roblox_username'],
                    'verified_at': user_data['verified_at'],
                    'verification_code': user_data.get('verification_code', 'N/A'),
                    'days_since_verification': int((time.time() - user_data['verified_at']) / (24 * 60 * 60)),
                    'expires_in_hours': int((30 * 24 * 60 * 60 - (time.time() - user_data['verified_at'])) / 3600)
                }
                verified_users.append(user_info)
            
            # Ordenar por fecha de verificación (más recientes primero)
            verified_users.sort(key=lambda x: x['verified_at'], reverse=True)
            
            response_data = {
                'status': 'success',
                'total_verified': len(verified_users),
                'users': verified_users,
                'generated_at': datetime.now().isoformat(),
                'verification_duration_hours': 24 * 30  # 30 días
            }
            
            logger.info(f"✅ API: Enviados datos de {len(verified_users)} usuarios verificados")
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error en get_verified_users: {e}")
            return web.json_response({
                'error': 'Internal server error',
                'message': str(e)
            }, status=500)
    
    async def get_user_statistics(self, request):
        """Obtener estadísticas generales de usuarios"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            # Limpiar datos expirados
            self.verification_system.cleanup_expired_data()
            
            total_verified = len(self.verification_system.verified_users)
            total_banned = len(self.verification_system.banned_users)
            total_warnings = len(self.verification_system.warnings)
            pending_verifications = len(self.verification_system.pending_verifications)
            
            # Estadísticas por día (últimos 7 días)
            current_time = time.time()
            daily_stats = {}
            
            for i in range(7):
                day_start = current_time - (i * 24 * 60 * 60)
                day_end = day_start + (24 * 60 * 60)
                
                day_verifications = 0
                for user_data in self.verification_system.verified_users.values():
                    if day_start <= user_data['verified_at'] <= day_end:
                        day_verifications += 1
                
                date_key = datetime.fromtimestamp(day_start).strftime('%Y-%m-%d')
                daily_stats[date_key] = day_verifications
            
            response_data = {
                'status': 'success',
                'statistics': {
                    'total_verified': total_verified,
                    'total_banned': total_banned,
                    'total_warnings': total_warnings,
                    'pending_verifications': pending_verifications,
                    'daily_verifications': daily_stats,
                    'ban_duration_days': 7,
                    'verification_duration_days': 30
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error en get_user_statistics: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_server_statistics(self, request):
        """Obtener estadísticas de servidores VIP"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            total_users_with_servers = len(self.scraper.links_by_user)
            total_servers = 0
            total_games = 0
            servers_by_category = {}
            
            for user_id, user_games in self.scraper.links_by_user.items():
                for game_id, game_data in user_games.items():
                    if isinstance(game_data, dict):
                        game_servers = len(game_data.get('links', []))
                        total_servers += game_servers
                        total_games += 1
                        
                        category = game_data.get('category', 'other')
                        if category not in servers_by_category:
                            servers_by_category[category] = 0
                        servers_by_category[category] += game_servers
            
            response_data = {
                'status': 'success',
                'server_statistics': {
                    'total_users_with_servers': total_users_with_servers,
                    'total_servers': total_servers,
                    'total_games': total_games,
                    'servers_by_category': servers_by_category,
                    'scraping_stats': self.scraper.scraping_stats
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error en get_server_statistics: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_user_details(self, request):
        """Obtener detalles específicos de un usuario"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            user_id = request.match_info['user_id']
            
            # Información de verificación
            verification_info = None
            if user_id in self.verification_system.verified_users:
                user_data = self.verification_system.verified_users[user_id]
                verification_info = {
                    'is_verified': True,
                    'roblox_username': user_data['roblox_username'],
                    'verified_at': user_data['verified_at'],
                    'verification_code': user_data.get('verification_code', 'N/A'),
                    'expires_at': user_data['verified_at'] + (30 * 24 * 60 * 60)
                }
            else:
                verification_info = {'is_verified': False}
            
            # Información de bans/advertencias
            ban_info = {
                'is_banned': user_id in self.verification_system.banned_users,
                'ban_time': self.verification_system.banned_users.get(user_id),
                'warnings_count': self.verification_system.warnings.get(user_id, 0)
            }
            
            # Información de servidores
            server_info = {
                'has_servers': user_id in self.scraper.links_by_user,
                'total_games': 0,
                'total_servers': 0,
                'games': []
            }
            
            if user_id in self.scraper.links_by_user:
                user_games = self.scraper.links_by_user[user_id]
                server_info['total_games'] = len(user_games)
                
                for game_id, game_data in user_games.items():
                    if isinstance(game_data, dict):
                        game_servers = len(game_data.get('links', []))
                        server_info['total_servers'] += game_servers
                        
                        server_info['games'].append({
                            'game_id': game_id,
                            'game_name': game_data.get('game_name', f'Game {game_id}'),
                            'category': game_data.get('category', 'other'),
                            'server_count': game_servers,
                            'game_image_url': game_data.get('game_image_url')
                        })
            
            response_data = {
                'status': 'success',
                'user_id': user_id,
                'verification': verification_info,
                'moderation': ban_info,
                'servers': server_info,
                'generated_at': datetime.now().isoformat()
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error en get_user_details: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_bot_status(self, request):
        """Obtener estado general del bot"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            # Estado de scripts de Roblox conectados
            connected_scripts = self.remote_control.get_connected_scripts()
            active_commands = len([cmd for cmd in self.remote_control.active_commands.values() if cmd['status'] == 'pending'])
            
            response_data = {
                'status': 'success',
                'bot_status': {
                    'is_online': True,
                    'uptime_start': datetime.now().isoformat(),  # Aprox, podrías guardarlo al inicio
                    'discord_connected': True,
                    'roblox_scripts_connected': len(connected_scripts),
                    'active_commands': active_commands,
                    'remote_control_port': 8080
                },
                'system_stats': {
                    'verified_users': len(self.verification_system.verified_users),
                    'banned_users': len(self.verification_system.banned_users),
                    'total_servers': sum(
                        len(game_data.get('links', [])) 
                        for user_games in self.scraper.links_by_user.values() 
                        for game_data in user_games.values() 
                        if isinstance(game_data, dict)
                    ),
                    'users_with_servers': len(self.scraper.links_by_user)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error en get_bot_status: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_recent_activity(self, request):
        """Obtener actividad reciente del bot"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)
            
            current_time = time.time()
            recent_verifications = []
            recent_bans = []
            
            # Últimas verificaciones (24 horas)
            for discord_id, user_data in self.verification_system.verified_users.items():
                if current_time - user_data['verified_at'] <= 24 * 60 * 60:
                    recent_verifications.append({
                        'discord_id': discord_id,
                        'roblox_username': user_data['roblox_username'],
                        'verified_at': user_data['verified_at'],
                        'hours_ago': int((current_time - user_data['verified_at']) / 3600)
                    })
            
            # Últimos bans (7 días)
            for discord_id, ban_time in self.verification_system.banned_users.items():
                if current_time - ban_time <= 7 * 24 * 60 * 60:
                    recent_bans.append({
                        'discord_id': discord_id,
                        'banned_at': ban_time,
                        'days_ago': int((current_time - ban_time) / (24 * 60 * 60))
                    })
            
            # Ordenar por más recientes
            recent_verifications.sort(key=lambda x: x['verified_at'], reverse=True)
            recent_bans.sort(key=lambda x: x['banned_at'], reverse=True)
            
            response_data = {
                'status': 'success',
                'recent_activity': {
                    'recent_verifications': recent_verifications[:10],  # Últimas 10
                    'recent_bans': recent_bans[:5],  # Últimos 5
                    'connected_roblox_scripts': len(self.remote_control.get_connected_scripts()),
                    'pending_commands': len([cmd for cmd in self.remote_control.active_commands.values() if cmd['status'] == 'pending'])
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return web.json_response(response_data)
            
        except Exception as e:
            logger.error(f"❌ Error en get_recent_activity: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def authenticate_request(self, request):
        """Endpoint para autenticar una petición"""
        try:
            data = await request.json()
            provided_secret = data.get('secret', '')
            
            if provided_secret == WEBHOOK_SECRET:
                return web.json_response({
                    'status': 'success',
                    'message': 'Authentication successful',
                    'access_token': WEBHOOK_SECRET,  # En producción usarías JWT
                    'valid_until': int(time.time() + 3600)  # 1 hora
                })
            else:
                return web.json_response({
                    'status': 'error',
                    'message': 'Invalid secret'
                }, status=401)
                
        except Exception as e:
            logger.error(f"❌ Error en authenticate_request: {e}")
            return web.json_response({'error': str(e)}, status=500)


# Función para integrar la API web en el sistema existente
def setup_web_api(app, verification_system, scraper, remote_control):
    """Configurar la API web en la app existente"""
    web_api = WebAPI(verification_system, scraper, remote_control)
    web_api.setup_routes(app)
    return web_api
