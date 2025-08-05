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

        # Configurar sistema OAuth2 de Discord
        try:
            from discord_oauth import discord_oauth
            discord_oauth.setup_routes(app)
            logger.info("🔐 Sistema OAuth2 de Discord integrado exitosamente")
        except ImportError as e:
            logger.warning(f"⚠️ Sistema OAuth2 no disponible: {e}")
        except Exception as e:
            logger.error(f"❌ Error integrando OAuth2: {e}")

        # Middleware de CORS para permitir acceso desde cualquier origen
        @web.middleware
        async def cors_middleware(request, handler):
            logger.info(f"🌐 CORS Middleware: {request.method} {request.path} desde {request.remote}")

            # Manejar preflight requests (OPTIONS)
            if request.method == 'OPTIONS':
                logger.info(f"✈️ Preflight request para {request.path}")
                response = web.Response()
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Max-Age'] = '86400'
                return response

            # Procesar la petición normal
            try:
                response = await handler(request)
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                return response
            except Exception as middleware_error:
                logger.error(f"❌ Error en CORS middleware: {middleware_error}")
                logger.error(f"🔍 Path que causó error: {request.path}")
                logger.error(f"🔍 Método que causó error: {request.method}")
                raise

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

        # Rutas de verificación externa - agregadas correctamente
        app.router.add_post('/api/external-verification/request', self.external_verification_request)
        app.router.add_post('/api/external-verification/check', self.external_verification_check)

        # Agregar ruta OPTIONS para verificación externa
        app.router.add_options('/api/external-verification/request', self.handle_options)
        app.router.add_options('/api/external-verification/check', self.handle_options)
        logger.info("🔗 Rutas de verificación externa configuradas")

        # Otras rutas
        app.router.add_get('/api/leaderboard', self.get_leaderboard_api)
        app.router.add_get('/api/economy-stats', self.get_economy_stats)
        # Agregar ruta para OAuth2 info
        app.router.add_get('/api/oauth2-info', self.get_oauth2_info)

        # Agregar ruta para recibir datos OAuth2
        app.router.add_post('/api/oauth2-user-add', self.receive_oauth2_user_data)

        # Integrar webhook de alertas Brainrot
        try:
            from Commands.brainrot_alerts import setup_brainrot_webhook
            setup_brainrot_webhook(app)
            logger.info("🧠 Sistema de alertas Brainrot integrado exitosamente")
        except Exception as e:
            logger.error(f"🧠 Error integrando alertas Brainrot: {e}")

        # Integrar nueva API de brainrot system
        try:
            from Commands.brainrot_system import setup_brainrot_api
            setup_brainrot_api(app)
            logger.info("🧠 Nueva API de Brainrot integrada exitosamente")
        except ImportError as ie:
            logger.error(f"🧠 Error importando módulo brainrot_system: {ie}")
        except Exception as e:
            logger.error(f"🧠 Error integrando nueva API de Brainrot: {e}")
            import traceback
            logger.error(f"🧠 Traceback: {traceback.format_exc()}")

        # Rutas para analytics
        app.router.add_post('/api/web-analytics', self.receive_web_analytics)
        app.router.add_get('/api/web-analytics', self.get_web_analytics)

        # === NUEVAS APIs SOLICITADAS POR VERCEL ===

        # Marketplace APIs
        app.router.add_get('/api/marketplace/items', self.get_marketplace_items)
        app.router.add_post('/api/marketplace/purchase', self.marketplace_purchase)
        app.router.add_get('/api/marketplace/user-sales', self.get_user_sales)
        app.router.add_post('/api/marketplace/sell-item', self.sell_marketplace_item)

        # AI Features APIs  
        app.router.add_post('/api/ai/scripts/generate', self.generate_ai_script)
        app.router.add_post('/api/ai/images/generate', self.generate_ai_image)
        app.router.add_post('/api/ai/music/generate', self.generate_ai_music)
        app.router.add_get('/api/ai/usage-stats', self.get_ai_usage_stats)

        # Premium APIs
        app.router.add_get('/api/premium/status', self.get_premium_status)
        app.router.add_post('/api/premium/purchase', self.purchase_premium)
        app.router.add_get('/api/premium/benefits', self.get_premium_benefits)

        # Support APIs
        app.router.add_post('/api/support/report', self.submit_support_report)
        app.router.add_get('/api/support/tickets', self.get_user_support_tickets)

        # Leaderboard APIs
        app.router.add_get('/api/leaderboard/weekly', self.get_weekly_leaderboard)
        app.router.add_get('/api/leaderboard/user-position', self.get_user_leaderboard_position)

        # Stats APIs
        app.router.add_get('/api/stats/activity', self.get_user_activity_stats)
        app.router.add_get('/api/stats/global', self.get_global_stats)

        # Nuevas APIs para dashboard de estadísticas en tiempo real
        app.router.add_get('/api/stats/commands-executed', self.get_commands_executed_stats)
        app.router.add_get('/api/stats/active-servers', self.get_active_servers_stats)
        app.router.add_get('/api/stats/messages-processed', self.get_messages_processed_stats)
        app.router.add_get('/api/stats/realtime-activity', self.get_realtime_activity)

        # Agregar rutas OPTIONS para las nuevas APIs
        app.router.add_options('/api/marketplace/{path:.*}', self.handle_options)
        app.router.add_options('/api/ai/{path:.*}', self.handle_options)
        app.router.add_options('/api/premium/{path:.*}', self.handle_options)
        app.router.add_options('/api/support/{path:.*}', self.handle_options)
        app.router.add_options('/api/leaderboard/{path:.*}', self.handle_options)
        app.router.add_options('/api/stats/{path:.*}', self.handle_options)

        logger.info("🆕 APIs de Vercel configuradas exitosamente")

        # Listar todas las rutas configuradas para debug
        logger.info("📋 Rutas configuradas:")
        for route in app.router.routes():
            logger.info(f"  {route.method} {route.resource.canonical}")

        logger.info("🌐 API web configurada para acceso externo")

    async def handle_options(self, request):
        """Manejar peticiones OPTIONS para CORS"""
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, PUT, DELETE, PATCH',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Max-Age': '86400'
            }
        )

    def verify_auth(self, request):
        """Verificar autenticación de la petición - modo permisivo"""
        auth_header = request.headers.get('Authorization', '')
        expected_header = f"Bearer {WEBHOOK_SECRET}"

        # Permitir acceso sin autenticación para endpoints públicos
        if request.path.startswith('/api/') and request.method in ['GET', 'OPTIONS']:
            return True

        # Verificar token si se proporciona
        if auth_header and auth_header != expected_header:
            logger.warning(f"🚫 Token inválido desde {request.remote}")
            return False

        # Permitir acceso sin token para compatibilidad
        if not auth_header:
            logger.info(f"🔓 Acceso sin token permitido desde {request.remote}")
            return True

        return True

    def validate_roblox_username_format(self, username: str) -> bool:
        """Validar formato básico de username de Roblox"""
        if not username or len(username) < 3 or len(username) > 20:
            return False

        # Verificar que solo contenga caracteres alfanuméricos y guiones bajos
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False

        # No puede empezar o terminar con guión bajo
        if username.startswith('_') or username.endswith('_'):
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

    async def external_verification_request(self, request):
        """API para solicitar verificación externa - genera código"""
        logger.info(f"🔗 API Externa: Recibida solicitud de verificación desde {request.remote}")
        logger.info(f"📋 Método: {request.method}, Path: {request.path}")
        logger.info(f"📋 Headers: {dict(request.headers)}")
        logger.info(f"📋 Content-Type: {request.headers.get('Content-Type', 'No especificado')}")

        try:
            # Verificar método HTTP ANTES de procesar
            logger.info(f"🔍 Verificando método HTTP: {request.method}")
            if request.method != 'POST':
                logger.error(f"❌ Método HTTP incorrecto: {request.method} - Se esperaba POST")
                return web.json_response({
                    'success': False,
                    'error': f'Método {request.method} no permitido. Usa POST',
                    'allowed_methods': ['POST'],
                    'received_method': request.method
                }, status=405)

            if not self.verify_auth(request):
                logger.warning(f"🚫 Solicitud no autorizada desde {request.remote}")
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Leer datos del request con más debugging
            try:
                # Verificar si hay contenido
                content_length = request.headers.get('Content-Length', '0')
                logger.info(f"📦 Content-Length: {content_length}")

                # Intentar leer el texto primero para debug
                raw_body = await request.text()
                logger.info(f"📄 Raw body recibido: {raw_body[:200]}...")  # Primeros 200 caracteres

                # Ahora parsear como JSON
                if raw_body.strip():
                    data = json.loads(raw_body)
                    logger.info(f"📄 JSON parseado exitosamente: {data}")
                else:
                    logger.error(f"❌ Body vacío recibido")
                    return web.json_response({
                        'success': False,
                        'error': 'Request body vacío - se requiere JSON'
                    }, status=400)

            except json.JSONDecodeError as json_error:
                logger.error(f"❌ Error parseando JSON: {json_error}")
                logger.error(f"❌ Raw body que causó error: {raw_body}")
                return web.json_response({
                    'success': False,
                    'error': 'JSON inválido - verifica el formato'
                }, status=400)
            except Exception as read_error:
                logger.error(f"❌ Error leyendo request: {read_error}")
                return web.json_response({
                    'success': False,
                    'error': 'Error leyendo datos del request'
                }, status=400)

            discord_id = str(data.get('discord_id', ''))
            roblox_username = data.get('roblox_username', '').strip()

            logger.info(f"🎯 Procesando verificación: Discord {discord_id} → Roblox {roblox_username}")

            # Validaciones básicas
            if not discord_id or not roblox_username:
                return web.json_response({
                    'success': False,
                    'error': 'discord_id y roblox_username son requeridos'
                }, status=400)

            # Validar formato de discord_id
            try:
                int(discord_id)
            except ValueError:
                return web.json_response({
                    'success': False,
                    'error': 'discord_id debe ser un número válido'
                }, status=400)

            # Validar formato de roblox_username
            if not self.validate_roblox_username_format(roblox_username):
                return web.json_response({
                    'success': False,
                    'error': 'Nombre de usuario de Roblox inválido'
                }, status=400)

            # Verificar si el usuario ya está verificado
            if self.verification_system.is_user_verified(discord_id):
                return web.json_response({
                    'success': False,
                    'error': 'El usuario ya está verificado',
                    'current_username': self.verification_system.verified_users[discord_id]['roblox_username']
                }, status=409)

            # Verificar si el usuario está baneado
            if self.verification_system.is_user_banned(discord_id):
                ban_time = self.verification_system.banned_users.get(discord_id, 0)
                remaining_time = (ban_time + 7 * 24 * 60 * 60) - time.time()

                if remaining_time > 0:
                    return web.json_response({
                        'success': False,
                        'error': 'Usuario baneado temporalmente',
                        'ban_remaining_hours': int(remaining_time / 3600)
                    }, status=403)

            try:
                # Generar código de verificación
                verification_code = self.verification_system.create_verification_request(discord_id, roblox_username)

                response_data = {
                    'success': True,
                    'verification_code': verification_code,
                    'roblox_username': roblox_username,
                    'discord_id': discord_id,
                    'instructions': f'Agrega este código a tu descripción de Roblox: {verification_code}',
                    'profile_url': f'https://www.roblox.com/users/profile?username={roblox_username}',
                    'expires_in_minutes': 10
                }

                logger.info(f"🔗 API Externa: Código de verificación generado para {discord_id} → {roblox_username}")
                return web.json_response(response_data)

            except ValueError as ve:
                return web.json_response({
                    'success': False,
                    'error': str(ve)
                }, status=400)

        except Exception as e:
            logger.error(f"❌ Error crítico en external_verification_request: {e}")
            logger.error(f"🔍 Tipo de error: {type(e).__name__}")
            logger.error(f"🔍 Request method: {request.method}")
            logger.error(f"🔍 Request path: {request.path}")
            import traceback
            logger.error(f"🔍 Traceback completo: {traceback.format_exc()}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor',
                'debug_info': str(e)
            }, status=500)

    async def external_verification_check(self, request):
        """API para verificar si el código fue puesto en la descripción"""
        logger.info(f"✅ API Externa: Recibida solicitud de verificación CHECK desde {request.remote}")
        logger.info(f"📋 Método: {request.method}, Path: {request.path}")

        try:
            # Verificar método HTTP
            if request.method != 'POST':
                logger.error(f"❌ Método HTTP incorrecto en CHECK: {request.method}")
                return web.json_response({
                    'success': False,
                    'error': f'Método {request.method} no permitido. Usa POST'
                }, status=405)

            if not self.verify_auth(request):
                logger.warning(f"🚫 Solicitud CHECK no autorizada desde {request.remote}")
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Leer datos del request
            try:
                data = await request.json()
                logger.info(f"📄 Datos CHECK recibidos: {data}")
            except Exception as json_error:
                logger.error(f"❌ Error parseando JSON en CHECK: {json_error}")
                return web.json_response({
                    'success': False,
                    'error': 'JSON inválido'
                }, status=400)

            discord_id = str(data.get('discord_id', ''))
            roblox_username = data.get('roblox_username', '').strip()

            logger.info(f"🔍 Verificando código para: Discord {discord_id} → Roblox {roblox_username}")

            # Validaciones básicas
            if not discord_id or not roblox_username:
                return web.json_response({
                    'success': False,
                    'error': 'discord_id y roblox_username son requeridos'
                }, status=400)

            # Verificar si hay una verificación pendiente
            if discord_id not in self.verification_system.pending_verifications:
                return web.json_response({
                    'success': False,
                    'error': 'No hay verificación pendiente para este usuario'
                }, status=404)

            pending_data = self.verification_system.pending_verifications[discord_id]

            # Verificar que el username coincida
            if pending_data['roblox_username'].lower() != roblox_username.lower():
                return web.json_response({
                    'success': False,
                    'error': 'El nombre de usuario no coincide con la verificación pendiente'
                }, status=400)

            try:
                # Intentar verificar el usuario
                success, error_message = self.verification_system.verify_user(discord_id, roblox_username)

                if success:
                    response_data = {
                        'success': True,
                        'message': 'Verificación completada exitosamente',
                        'discord_id': discord_id,
                        'roblox_username': roblox_username,
                        'verified_at': time.time(),
                        'verification_code': pending_data['verification_code']
                    }

                    logger.info(f"✅ API Externa: Verificación exitosa para {discord_id} → {roblox_username}")
                    return web.json_response(response_data)
                else:
                    response_data = {
                        'success': False,
                        'error': error_message,
                        'can_retry': True
                    }

                    logger.warning(f"❌ API Externa: Verificación fallida para {discord_id} → {roblox_username}: {error_message}")
                    return web.json_response(response_data, status=400)

            except Exception as ve:
                return web.json_response({
                    'success': False,
                    'error': str(ve),
                    'can_retry': False
                }, status=400)

        except Exception as e:
            logger.error(f"❌ Error crítico en external_verification_check: {e}")
            logger.error(f"🔍 Tipo de error CHECK: {type(e).__name__}")
            logger.error(f"🔍 Request method CHECK: {request.method}")
            logger.error(f"🔍 Request path CHECK: {request.path}")
            import traceback
            logger.error(f"🔍 Traceback completo CHECK: {traceback.format_exc()}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor',
                'debug_info': str(e)
            }, status=500)

    async def get_leaderboard_api(self, request):
        """API para obtener leaderboard completo"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Parámetros de consulta
            limit = min(int(request.query.get('limit', 50)), 100)  # Max 100
            leaderboard_type = request.query.get('type', 'weekly')  # weekly o all_time

            # Cargar datos de servidores desde user_game_servers.json
            try:
                with open('user_game_servers.json', 'r', encoding='utf-8') as f:
                    servers_data = json.load(f)
                    user_servers = servers_data.get('user_servers', {})
            except:
                user_servers = {}

            # Crear leaderboard basado en cantidad de servidores
            leaderboard_data = []
            for user_id, servers_list in user_servers.items():
                server_count = len(servers_list) if isinstance(servers_list, list) else 0

                # Obtener información del usuario verificado
                user_info = self.verification_system.verified_users.get(user_id, {})
                roblox_username = user_info.get('roblox_username', f'Usuario_{user_id[:8]}')

                leaderboard_data.append({
                    'rank': 0,  # Se asignará después del ordenamiento
                    'discord_id': user_id,
                    'roblox_username': roblox_username,
                    'server_count': server_count,
                    'is_verified': user_id in self.verification_system.verified_users,
                    'verified_at': user_info.get('verified_at')
                })

            # Ordenar por cantidad de servidores
            leaderboard_data.sort(key=lambda x: x['server_count'], reverse=True)

            # Asignar rankings
            for i, entry in enumerate(leaderboard_data[:limit], 1):
                entry['rank'] = i

            # Estadísticas generales
            total_users = len(leaderboard_data)
            total_servers = sum(entry['server_count'] for entry in leaderboard_data)
            verified_users_count = len(self.verification_system.verified_users)

            response_data = {
                'success': True,
                'leaderboard_type': leaderboard_type,
                'leaderboard': leaderboard_data[:limit],
                'statistics': {
                    'total_users_in_leaderboard': total_users,
                    'total_servers_tracked': total_servers,
                    'verified_users_count': verified_users_count,
                    'average_servers_per_user': total_servers / max(total_users, 1),
                    'top_user_servers': leaderboard_data[0]['server_count'] if leaderboard_data else 0
                },
                'metadata': {
                    'limit_applied': limit,
                    'generated_at': datetime.now().isoformat(),
                    'system': 'rbxservers_api',
                    'note': 'Sin límite de servidores por usuario'
                }
            }

            logger.info(f"📊 API: Leaderboard generado con {len(leaderboard_data[:limit])} entradas")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_leaderboard_api: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def get_economy_stats(self, request):
        """API para obtener estadísticas de la economía (monedas, códigos, etc.)"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Cargar datos de monedas
            coins_stats = {
                'total_users_with_coins': 0,
                'total_coins_in_circulation': 0,
                'total_transactions': 0,
                'average_balance': 0,
                'top_balances': []
            }

            try:
                with open('user_coins.json', 'r', encoding='utf-8') as f:
                    coins_data = json.load(f)
                    user_coins = coins_data.get('user_coins', {})

                coins_stats['total_users_with_coins'] = len(user_coins)

                balances = []
                total_transactions = 0

                for user_id, user_data in user_coins.items():
                    balance = user_data.get('balance', 0)
                    coins_stats['total_coins_in_circulation'] += balance

                    transactions_count = len(user_data.get('transactions', []))
                    total_transactions += transactions_count

                    balances.append({
                        'user_id': user_id,
                        'balance': balance,
                        'total_earned': user_data.get('total_earned', 0)
                    })

                coins_stats['total_transactions'] = total_transactions
                coins_stats['average_balance'] = coins_stats['total_coins_in_circulation'] / max(len(user_coins), 1)

                # Top 10 balances
                balances.sort(key=lambda x: x['balance'], reverse=True)
                coins_stats['top_balances'] = balances[:10]

            except:
                logger.warning("No se pudieron cargar datos de monedas")

            # Cargar datos de códigos promocionales
            codes_stats = {
                'total_codes_created': 0,
                'active_codes': 0,
                'total_redemptions': 0,
                'codes_by_category': {}
            }

            try:
                with open('promotional_codes.json', 'r', encoding='utf-8') as f:
                    codes_data = json.load(f)
                    codes = codes_data.get('codes', {})

                codes_stats['total_codes_created'] = len(codes)

                for code_key, code_data in codes.items():
                    if code_data.get('active', False) and code_data.get('stock', 0) > 0:
                        codes_stats['active_codes'] += 1

                    codes_stats['total_redemptions'] += code_data.get('current_uses', 0)

                # Cargar uso de códigos
                with open('codes_usage.json', 'r', encoding='utf-8') as f:
                    usage_data = json.load(f)
                    usage = usage_data.get('usage', {})

                total_unique_users = set()
                for code_usage in usage.values():
                    for user_usage in code_usage:
                        total_unique_users.add(user_usage.get('user_id'))

                codes_stats['unique_users_redeemed'] = len(total_unique_users)

            except:
                logger.warning("No se pudieron cargar datos de códigos")

            # Estadísticas de la tienda
            shop_stats = {
                'total_categories': 0,
                'total_items': 0,
                'items_in_stock': 0,
                'total_stock_units': 0
            }

            try:
                with open('shop_items.json', 'r', encoding='utf-8') as f:
                    shop_data = json.load(f)
                    shop_items = shop_data.get('shop_items', {})

                shop_stats['total_categories'] = len(shop_items)

                for category, items in shop_items.items():
                    shop_stats['total_items'] += len(items)

                    for item_data in items.values():
                        stock = item_data.get('stock', 0)
                        shop_stats['total_stock_units'] += stock

                        if stock > 0:
                            shop_stats['items_in_stock'] += 1

            except:
                logger.warning("No se pudieron cargar datos de la tienda")

            response_data = {
                'success': True,
                'economy_statistics': {
                    'coins': coins_stats,
                    'promotional_codes': codes_stats,
                    'shop': shop_stats
                },
                'summary': {
                    'total_economic_activity': coins_stats['total_transactions'] + codes_stats['total_redemptions'],
                    'active_economy_participants': coins_stats['total_users_with_coins'],
                    'coins_per_verified_user': coins_stats['total_coins_in_circulation'] / max(len(self.verification_system.verified_users), 1)
                },
                'generated_at': datetime.now().isoformat()
            }

            logger.info(f"💰 API: Estadísticas de economía generadas")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_economy_stats: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def get_oauth2_info(self, request):
        """API para obtener información del sistema OAuth2"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Importar sistema OAuth2
            try:
                from discord_oauth import discord_oauth

                oauth_info = {
                    'client_id': discord_oauth.client_id,
                    'redirect_uri': discord_oauth.redirect_uri,
                    'scopes': discord_oauth.scopes,
                    'authorize_url': discord_oauth.authorize_url,
                    'token_url': discord_oauth.token_url,
                    'configured': True
                }

                # Generar URL de ejemplo
                auth_url, state = discord_oauth.generate_oauth_url()
                oauth_info['example_auth_url'] = auth_url
                oauth_info['example_state'] = state

            except ImportError:
                oauth_info = {
                    'configured': False,
                    'error': 'Sistema OAuth2 no disponible'
                }

            response_data = {
                'success': True,
                'oauth2_info': oauth_info,
                'endpoints': {
                    'start_auth': '/auth/discord/start',
                    'callback': '/auth/discord/callback',
                    'user_info': '/auth/discord/user/{user_id}',
                    'revoke': '/auth/discord/revoke/{user_id}'
                },
                'generated_at': datetime.now().isoformat()
            }

            logger.info(f"🔐 API: Información OAuth2 enviada")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_oauth2_info: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def receive_oauth2_user_data(self, request):
        """Endpoint para recibir datos de usuarios OAuth2 desde Vercel"""
        logger.info(f"🔐 OAuth2: Recibida solicitud desde Vercel desde {request.remote}")

        try:
            # Verificar método HTTP
            if request.method != 'POST':
                logger.error(f"❌ Método HTTP incorrecto: {request.method}")
                return web.json_response({
                    'success': False,
                    'error': f'Método {request.method} no permitido. Usa POST'
                }, status=405)

            # Verificar autenticación
            if not self.verify_auth(request):
                logger.warning(f"🚫 Solicitud OAuth2 no autorizada desde {request.remote}")
                return web.json_response({
                    'success': False,
                    'error': 'API key requerida - usa el header Authorization: Bearer rbxservers_webhook_secret_2024'
                }, status=401)

            # Leer datos del request
            try:
                data = await request.json()
                logger.info(f"📄 Datos OAuth2 recibidos: {data}")
            except Exception as json_error:
                logger.error(f"❌ Error parseando JSON OAuth2: {json_error}")
                return web.json_response({
                    'success': False,
                    'error': 'JSON inválido'
                }, status=400)

            # Validar datos requeridos
            required_fields = ['user_id', 'username', 'display_name', 'email', 'avatar_url']
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                return web.json_response({
                    'success': False,
                    'error': f'Campos requeridos faltantes: {", ".join(missing_fields)}',
                    'required_fields': required_fields
                }, status=400)

            user_id = str(data['user_id'])

            # Importar sistema OAuth2 y guardar datos
            try:
                from discord_oauth import discord_oauth

                # Crear estructura de datos compatible
                oauth_user_data = {
                    'user_id': user_id,
                    'username': data.get('username'),
                    'discriminator': data.get('discriminator', '0'),
                    'global_name': data.get('global_name'),
                    'display_name': data.get('display_name'),
                    'email': data.get('email'),
                    'verified': data.get('verified', True),
                    'avatar': data.get('avatar'),
                    'avatar_url': data.get('avatar_url'),
                    'banner': data.get('banner'),
                    'banner_url': data.get('banner_url'),
                    'accent_color': data.get('accent_color'),
                    'locale': data.get('locale'),
                    'mfa_enabled': data.get('mfa_enabled', False),
                    'premium_type': data.get('premium_type'),
                    'public_flags': data.get('public_flags', 0),
                    'flags': data.get('flags', 0),
                    'profile_url': f"https://discord.com/users/{user_id}",
                    'oauth_authorized': True,
                    'authorization_date': datetime.now().isoformat(),
                    'data_source': 'vercel_oauth2_callback'
                }

                # Decodificar badges si se proporcionan
                if data.get('public_flags'):
                    oauth_user_data['badges'] = discord_oauth._decode_user_flags(data['public_flags'])

                # Simular token data para compatibilidad
                token_data = {
                    'access_token': f"vercel_token_{user_id}",
                    'refresh_token': None,
                    'expires_in': 3600
                }

                # Guardar en el sistema OAuth2
                import time
                discord_oauth.user_tokens[user_id] = {
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token'),
                    'expires_at': time.time() + token_data.get('expires_in', 3600),
                    'user_info': oauth_user_data,
                    'authorized_at': time.time(),
                    'source': 'vercel_callback'
                }

                # Guardar datos persistentemente
                discord_oauth.save_oauth2_data()

                logger.info(f"✅ Usuario OAuth2 guardado desde Vercel: {data.get('username')} (ID: {user_id})")

                return web.json_response({
                    'success': True,
                    'message': 'Usuario OAuth2 recibido y almacenado correctamente',
                    'user_id': user_id,
                    'username': data.get('username'),
                    'display_name': data.get('display_name'),
                    'stored_at': datetime.now().isoformat(),
                    'expires_at': discord_oauth.user_tokens[user_id]['expires_at']
                })

            except ImportError:
                logger.error("❌ Sistema OAuth2 no disponible")
                return web.json_response({
                    'success': False,
                    'error': 'Sistema OAuth2 no disponible en este servidor'
                }, status=500)
            except Exception as oauth_error:
                logger.error(f"❌ Error guardando datos OAuth2: {oauth_error}")
                return web.json_response({
                    'success': False,
                    'error': 'Error interno procesando datos OAuth2'
                }, status=500)

        except Exception as e:
            logger.error(f"❌ Error crítico en receive_oauth2_user_data: {e}")
            logger.error(f"🔍 Tipo de error: {type(e).__name__}")
            import traceback
            logger.error(f"🔍 Traceback completo: {traceback.format_exc()}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor',
                'debug_info': str(e)
            }, status=500)

    async def receive_web_analytics(self, request):
        """Endpoint para recibir analytics desde Vercel"""
        logger.info(f"📊 Analytics: Recibida solicitud desde {request.remote}")

        try:
            # Verificar método HTTP
            if request.method != 'POST':
                logger.error(f"❌ Método HTTP incorrecto: {request.method}")
                return web.json_response({
                    'success': False,
                    'error': f'Método {request.method} no permitido. Usa POST'
                }, status=405)

            # Verificar autenticación (opcional para analytics)
            auth_header = request.headers.get('Authorization', '')
            api_key_query = request.query.get('api_key', '')

            # Permitir tanto header como query parameter
            if not (auth_header == f"Bearer {WEBHOOK_SECRET}" or api_key_query == WEBHOOK_SECRET):
                logger.info(f"📊 Analytics sin autenticación desde {request.remote} - permitido")

            # Leer datos del request
            try:
                data = await request.json()
                logger.info(f"📄 Datos analytics recibidos: {data}")
            except Exception as json_error:
                logger.error(f"❌ Error parseando JSON analytics: {json_error}")
                return web.json_response({
                    'success': False,
                    'error': 'JSON inválido'
                }, status=400)

            # Procesar analytics
            analytics_entry = {
                'timestamp': datetime.now().isoformat(),
                'source': data.get('source', 'vercel'),
                'event_type': data.get('event_type', 'page_view'),
                'page': data.get('page', '/'),
                'user_agent': request.headers.get('User-Agent', 'Unknown'),
                'ip': request.remote,
                'data': data,
                'processed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Guardar analytics
            success = await self.save_analytics_data(analytics_entry)

            if success:
                logger.info(f"✅ Analytics guardado exitosamente desde {data.get('source', 'vercel')}")
                return web.json_response({
                    'success': True,
                    'message': 'Analytics recibido y almacenado correctamente',
                    'timestamp': analytics_entry['timestamp'],
                    'event_id': analytics_entry['timestamp'],
                    'status': 'SUCCESS'
                })
            else:
                logger.error(f"❌ Error guardando analytics")
                return web.json_response({
                    'success': False,
                    'error': 'Error interno procesando analytics'
                }, status=500)

        except Exception as e:
            logger.error(f"❌ Error crítico en receive_web_analytics: {e}")
            import traceback
            logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor',
                'debug_info': str(e)
            }, status=500)

    async def get_web_analytics(self, request):
        """Endpoint para obtener analytics almacenados"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Parámetros de consulta
            limit = min(int(request.query.get('limit', 100)), 1000)
            source = request.query.get('source', None)
            event_type = request.query.get('event_type', None)

            # Cargar datos de analytics
            analytics_data = await self.load_analytics_data()

            # Filtrar datos
            filtered_analytics = analytics_data.get('analytics', [])

            if source:
                filtered_analytics = [a for a in filtered_analytics if a.get('source') == source]

            if event_type:
                filtered_analytics = [a for a in filtered_analytics if a.get('event_type') == event_type]

            # Ordenar por timestamp más reciente
            filtered_analytics.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            # Aplicar límite
            filtered_analytics = filtered_analytics[:limit]

            # Estadísticas
            total_events = len(analytics_data.get('analytics', []))
            sources_stats = {}
            event_types_stats = {}

            for event in analytics_data.get('analytics', []):
                source_name = event.get('source', 'unknown')
                event_type_name = event.get('event_type', 'unknown')

                sources_stats[source_name] = sources_stats.get(source_name, 0) + 1
                event_types_stats[event_type_name] = event_types_stats.get(event_type_name, 0) + 1

            response_data = {
                'success': True,
                'analytics': filtered_analytics,
                'metadata': {
                    'total_events': total_events,
                    'filtered_count': len(filtered_analytics),
                    'limit_applied': limit,
                    'sources_stats': sources_stats,
                    'event_types_stats': event_types_stats,
                    'last_updated': analytics_data.get('metadata', {}).get('last_updated')
                },
                'generated_at': datetime.now().isoformat()
            }

            logger.info(f"📊 Analytics enviados: {len(filtered_analytics)} eventos")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_web_analytics: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def save_analytics_data(self, analytics_entry):
        """Guardar datos de analytics en archivo JSON"""
        try:
            # Cargar datos existentes
            analytics_data = await self.load_analytics_data()

            # Agregar nuevo evento
            analytics_data['analytics'].append(analytics_entry)

            # Mantener solo los últimos 1000 eventos
            max_events = analytics_data.get('config', {}).get('max_events', 1000)
            if len(analytics_data['analytics']) > max_events:
                analytics_data['analytics'] = analytics_data['analytics'][-max_events:]

            # Actualizar metadata
            analytics_data['metadata']['last_updated'] = datetime.now().isoformat()
            analytics_data['metadata']['total_events'] = len(analytics_data['analytics'])

            # Actualizar estadísticas por fuente
            source = analytics_entry.get('source', 'other')
            if 'sources' not in analytics_data['metadata']:
                analytics_data['metadata']['sources'] = {}
            analytics_data['metadata']['sources'][source] = analytics_data['metadata']['sources'].get(source, 0) + 1

            # Guardar archivo
            with open('web_analytics.json', 'w', encoding='utf-8') as f:
                json.dump(analytics_data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Analytics guardado exitosamente: evento {analytics_entry.get('event_type', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando analytics: {e}")
            return False

    async def load_analytics_data(self):
        """Cargar datos de analytics desde archivo JSON"""
        try:
            if os.path.exists('web_analytics.json'):
                with open('web_analytics.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Crear estructura inicial
                return {
                    "analytics": [],
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "total_events": 0,
                        "sources": {}
                    },
                    "config": {
                        "max_events": 1000,
                        "retention_days": 30,
                        "allowed_sources": ["vercel", "website", "bot"]
                    }
                }
        except Exception as e:
            logger.error(f"❌ Error cargando analytics: {e}")
            return {
                "analytics": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "total_events": 0,
                    "sources": {}
                },
                "config": {
                    "max_events": 1000,
                    "retention_days": 30,
                    "allowed_sources": ["vercel", "website", "bot"]
                }
            }

    # === MARKETPLACE APIs ===
    
    async def get_marketplace_items(self, request):
        """API para obtener items del marketplace"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Cargar datos de la tienda
            try:
                with open('shop_items.json', 'r', encoding='utf-8') as f:
                    shop_data = json.load(f)
                    shop_items = shop_data.get('shop_items', {})
            except:
                shop_items = {}

            # Formatear items para la API
            marketplace_items = []
            for category, items in shop_items.items():
                for item_id, item_data in items.items():
                    if item_data.get('stock', 0) > 0:  # Solo items en stock
                        marketplace_items.append({
                            'item_id': item_id,
                            'name': item_data.get('name', 'Item Sin Nombre'),
                            'description': item_data.get('description', 'Sin descripción'),
                            'cost': item_data.get('cost', 0),
                            'stock': item_data.get('stock', 0),
                            'category': category,
                            'available': True
                        })

            # Parámetros de filtrado
            category_filter = request.query.get('category')
            max_price = request.query.get('max_price')
            
            if category_filter:
                marketplace_items = [item for item in marketplace_items if item['category'] == category_filter]
            
            if max_price:
                try:
                    max_price = int(max_price)
                    marketplace_items = [item for item in marketplace_items if item['cost'] <= max_price]
                except:
                    pass

            response_data = {
                'success': True,
                'items': marketplace_items,
                'total_items': len(marketplace_items),
                'categories': list(shop_items.keys()),
                'generated_at': datetime.now().isoformat()
            }

            logger.info(f"🛒 API: Enviados {len(marketplace_items)} items del marketplace")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_marketplace_items: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def marketplace_purchase(self, request):
        """API para comprar items del marketplace"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            user_id = str(data.get('user_id', ''))
            item_id = data.get('item_id', '')
            quantity = int(data.get('quantity', 1))

            if not user_id or not item_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id e item_id son requeridos'
                }, status=400)

            # Cargar datos de la tienda y monedas del usuario
            try:
                with open('shop_items.json', 'r', encoding='utf-8') as f:
                    shop_data = json.load(f)
                    shop_items = shop_data.get('shop_items', {})

                with open('user_coins.json', 'r', encoding='utf-8') as f:
                    coins_data = json.load(f)
                    user_coins = coins_data.get('user_coins', {})
            except:
                return web.json_response({
                    'success': False,
                    'error': 'Error cargando datos del marketplace'
                }, status=500)

            # Buscar el item
            found_item = None
            found_category = None
            
            for category, items in shop_items.items():
                if item_id in items:
                    found_item = items[item_id]
                    found_category = category
                    break

            if not found_item:
                return web.json_response({
                    'success': False,
                    'error': 'Item no encontrado'
                }, status=404)

            # Verificar stock
            if found_item.get('stock', 0) < quantity:
                return web.json_response({
                    'success': False,
                    'error': 'Stock insuficiente'
                }, status=400)

            # Verificar balance del usuario
            user_balance = user_coins.get(user_id, {}).get('balance', 0)
            total_cost = found_item.get('cost', 0) * quantity

            if user_balance < total_cost:
                return web.json_response({
                    'success': False,
                    'error': 'Monedas insuficientes',
                    'required': total_cost,
                    'current_balance': user_balance
                }, status=400)

            # Procesar compra
            # Reducir stock
            shop_items[found_category][item_id]['stock'] -= quantity
            
            # Reducir monedas del usuario
            if user_id not in user_coins:
                user_coins[user_id] = {'balance': 0, 'transactions': [], 'total_earned': 0}
            
            user_coins[user_id]['balance'] -= total_cost
            user_coins[user_id]['transactions'].append({
                'type': 'purchase',
                'amount': -total_cost,
                'item_id': item_id,
                'item_name': found_item.get('name', 'Item'),
                'quantity': quantity,
                'timestamp': datetime.now().isoformat(),
                'description': f'Compra: {quantity}x {found_item.get("name", "Item")}'
            })

            # Guardar cambios
            with open('shop_items.json', 'w', encoding='utf-8') as f:
                json.dump(shop_data, f, indent=2, ensure_ascii=False)
            
            with open('user_coins.json', 'w', encoding='utf-8') as f:
                json.dump(coins_data, f, indent=2, ensure_ascii=False)

            logger.info(f"🛒 Compra exitosa: Usuario {user_id} compró {quantity}x {item_id} por {total_cost} monedas")

            return web.json_response({
                'success': True,
                'message': 'Compra realizada exitosamente',
                'purchase_details': {
                    'item_id': item_id,
                    'item_name': found_item.get('name'),
                    'quantity': quantity,
                    'unit_cost': found_item.get('cost', 0),
                    'total_cost': total_cost,
                    'remaining_balance': user_coins[user_id]['balance'],
                    'remaining_stock': shop_items[found_category][item_id]['stock']
                }
            })

        except Exception as e:
            logger.error(f"❌ Error en marketplace_purchase: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_user_sales(self, request):
        """API para obtener ventas del usuario"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            user_id = request.query.get('user_id')
            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)

            # Por ahora devolver estructura base - en el futuro se pueden implementar ventas P2P
            response_data = {
                'success': True,
                'user_id': user_id,
                'sales': [],
                'total_sales': 0,
                'total_revenue': 0,
                'pending_sales': 0,
                'completed_sales': 0,
                'message': 'Sistema de ventas P2P próximamente disponible',
                'generated_at': datetime.now().isoformat()
            }

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_user_sales: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def sell_marketplace_item(self, request):
        """API para vender items en el marketplace"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            
            # Por ahora devolver que está en desarrollo
            return web.json_response({
                'success': False,
                'error': 'Sistema de ventas P2P en desarrollo',
                'message': 'Esta funcionalidad estará disponible próximamente',
                'development_status': 'coming_soon'
            }, status=501)

        except Exception as e:
            logger.error(f"❌ Error en sell_marketplace_item: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    # === AI FEATURES APIs ===

    async def generate_ai_script(self, request):
        """API para generar scripts de Lua con IA"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            user_id = str(data.get('user_id', ''))
            prompt = data.get('prompt', '')
            script_type = data.get('type', 'general')

            if not user_id or not prompt:
                return web.json_response({
                    'success': False,
                    'error': 'user_id y prompt son requeridos'
                }, status=400)

            # Simular generación de script (integrar con tu sistema de IA existente)
            try:
                # Importar sistema de música/IA si existe
                from music_system import MusicSystem
                
                # Generar script básico basado en el prompt
                generated_script = f"""-- Script generado por IA RbxServers
-- Prompt: {prompt}
-- Tipo: {script_type}

-- Configuración inicial
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local player = Players.LocalPlayer

-- Script principal
print("Script iniciado para: {prompt}")

-- Función principal
local function mainFunction()
    -- Lógica del script aquí
    print("Ejecutando funcionalidad solicitada...")
end

-- Ejecutar
mainFunction()

-- Generado por RbxServers IA System"""

                response_data = {
                    'success': True,
                    'script': generated_script,
                    'metadata': {
                        'prompt': prompt,
                        'type': script_type,
                        'lines_count': len(generated_script.split('\n')),
                        'generated_at': datetime.now().isoformat(),
                        'user_id': user_id
                    },
                    'usage': {
                        'tokens_used': len(prompt.split()),
                        'generation_time': '1.2s'
                    }
                }

                logger.info(f"🤖 Script IA generado para usuario {user_id}: {prompt[:50]}...")
                return web.json_response(response_data)

            except ImportError:
                # Fallback si no hay sistema de IA
                return web.json_response({
                    'success': False,
                    'error': 'Sistema de IA no disponible temporalmente',
                    'fallback_script': f'-- Script básico para: {prompt}\nprint("Funcionalidad: {prompt}")'
                }, status=503)

        except Exception as e:
            logger.error(f"❌ Error en generate_ai_script: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def generate_ai_image(self, request):
        """API para generar imágenes con IA"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            user_id = str(data.get('user_id', ''))
            prompt = data.get('prompt', '')
            style = data.get('style', 'realistic')

            if not user_id or not prompt:
                return web.json_response({
                    'success': False,
                    'error': 'user_id y prompt son requeridos'
                }, status=400)

            try:
                # Importar sistema de imágenes si existe
                from images_system import ImageSystem
                
                # Simular generación de imagen
                image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}"
                
                response_data = {
                    'success': True,
                    'image_url': image_url,
                    'metadata': {
                        'prompt': prompt,
                        'style': style,
                        'generated_at': datetime.now().isoformat(),
                        'user_id': user_id,
                        'resolution': '1024x1024'
                    },
                    'usage': {
                        'generation_time': '3.5s',
                        'model': 'pollinations'
                    }
                }

                logger.info(f"🎨 Imagen IA generada para usuario {user_id}: {prompt[:50]}...")
                return web.json_response(response_data)

            except ImportError:
                return web.json_response({
                    'success': False,
                    'error': 'Sistema de generación de imágenes no disponible'
                }, status=503)

        except Exception as e:
            logger.error(f"❌ Error en generate_ai_image: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def generate_ai_music(self, request):
        """API para generar música con IA"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            user_id = str(data.get('user_id', ''))
            prompt = data.get('prompt', '')
            duration = int(data.get('duration', 30))

            if not user_id or not prompt:
                return web.json_response({
                    'success': False,
                    'error': 'user_id y prompt son requeridos'
                }, status=400)

            try:
                from music_system import MusicSystem
                
                # Simular generación de música
                response_data = {
                    'success': True,
                    'audio_url': f"https://api.example.com/generate-music/{user_id}",
                    'metadata': {
                        'prompt': prompt,
                        'duration': duration,
                        'generated_at': datetime.now().isoformat(),
                        'user_id': user_id,
                        'format': 'mp3',
                        'bitrate': '320kbps'
                    },
                    'status': 'generating',
                    'estimated_completion': '45s',
                    'message': 'Generación de música iniciada'
                }

                logger.info(f"🎵 Música IA en generación para usuario {user_id}: {prompt[:50]}...")
                return web.json_response(response_data)

            except ImportError:
                return web.json_response({
                    'success': False,
                    'error': 'Sistema de generación de música no disponible'
                }, status=503)

        except Exception as e:
            logger.error(f"❌ Error en generate_ai_music: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_ai_usage_stats(self, request):
        """API para obtener estadísticas de uso de IA"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            user_id = request.query.get('user_id')
            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)

            # Estadísticas simuladas (implementar con datos reales)
            response_data = {
                'success': True,
                'user_id': user_id,
                'ai_usage': {
                    'scripts_generated': 15,
                    'images_generated': 8,
                    'music_generated': 3,
                    'total_requests': 26,
                    'this_month': {
                        'scripts': 5,
                        'images': 3,
                        'music': 1
                    },
                    'limits': {
                        'scripts_monthly': 50,
                        'images_monthly': 25,
                        'music_monthly': 10,
                        'remaining_scripts': 35,
                        'remaining_images': 17,
                        'remaining_music': 7
                    }
                },
                'performance': {
                    'avg_generation_time': '2.1s',
                    'success_rate': '94%',
                    'most_used_feature': 'scripts'
                },
                'generated_at': datetime.now().isoformat()
            }

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_ai_usage_stats: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    # === PREMIUM APIs ===

    async def get_premium_status(self, request):
        """API para obtener estado premium del usuario"""  
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            user_id = request.query.get('user_id')
            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)

            # Por ahora, estructura base (implementar con datos reales)
            response_data = {
                'success': True,
                'user_id': user_id,
                'premium_status': {
                    'is_premium': False,
                    'plan': 'free',
                    'expires_at': None,
                    'features_unlocked': [
                        'basic_scraping',
                        'verification',
                        'basic_marketplace'
                    ],
                    'premium_features': [
                        'unlimited_scraping',
                        'priority_support',
                        'advanced_ai_features',
                        'custom_scripts',
                        'premium_marketplace'
                    ]
                },
                'available_plans': {
                    'premium_monthly': {
                        'name': 'Premium Mensual',
                        'price': 500,
                        'currency': 'coins',
                        'duration': '30 days'
                    },
                    'premium_yearly': {
                        'name': 'Premium Anual',
                        'price': 5000,
                        'currency': 'coins', 
                        'duration': '365 days',
                        'discount': '17%'
                    }
                },
                'generated_at': datetime.now().isoformat()
            }

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_premium_status: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def purchase_premium(self, request):
        """API para comprar plan premium"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            user_id = str(data.get('user_id', ''))
            plan_type = data.get('plan_type', '')

            if not user_id or not plan_type:
                return web.json_response({
                    'success': False,
                    'error': 'user_id y plan_type son requeridos'
                }, status=400)

            # Estructura base para futuro desarrollo
            return web.json_response({
                'success': False,
                'error': 'Sistema premium en desarrollo',
                'message': 'Los planes premium estarán disponibles próximamente',
                'development_status': 'coming_soon',
                'estimated_release': '2025 Q2'
            }, status=501)

        except Exception as e:
            logger.error(f"❌ Error en purchase_premium: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_premium_benefits(self, request):
        """API para obtener beneficios premium disponibles"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            response_data = {
                'success': True,
                'premium_benefits': {
                    'scraping': {
                        'unlimited_searches': 'Sin límite de búsquedas de servidores',
                        'priority_queue': 'Cola de prioridad para scraping',
                        'advanced_filters': 'Filtros avanzados por juego y región'
                    },
                    'ai_features': {
                        'increased_limits': 'Límites aumentados para generación IA',
                        'premium_models': 'Acceso a modelos de IA premium',
                        'faster_generation': 'Generación más rápida'
                    },
                    'marketplace': {
                        'reduced_fees': 'Tarifas reducidas en transacciones',
                        'priority_listings': 'Listings con prioridad',
                        'advanced_analytics': 'Analytics avanzados de ventas'
                    },
                    'support': {
                        'priority_support': 'Soporte prioritario 24/7',
                        'direct_access': 'Acceso directo al equipo de desarrollo',
                        'beta_features': 'Acceso anticipado a nuevas funciones'
                    },
                    'customization': {
                        'custom_profile': 'Perfil personalizable',
                        'exclusive_badges': 'Badges exclusivos premium',
                        'custom_commands': 'Comandos personalizados'
                    }
                },
                'pricing': {
                    'monthly': {
                        'price': 500,
                        'currency': 'coins',
                        'savings': '0%'
                    },
                    'yearly': {
                        'price': 5000,
                        'currency': 'coins',
                        'savings': '17%'
                    }
                },
                'generated_at': datetime.now().isoformat()
            }

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_premium_benefits: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    # === SUPPORT APIs ===

    async def submit_support_report(self, request):
        """API para enviar reporte/bug de soporte"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            user_id = str(data.get('user_id', ''))
            report_type = data.get('type', 'bug')
            title = data.get('title', '')
            description = data.get('description', '')
            priority = data.get('priority', 'medium')

            if not user_id or not title or not description:
                return web.json_response({
                    'success': False,
                    'error': 'user_id, title y description son requeridos'
                }, status=400)

            # Generar ticket ID
            ticket_id = f"TICKET_{int(time.time())}_{user_id[-6:]}"

            # Crear estructura del ticket
            ticket = {
                'ticket_id': ticket_id,
                'user_id': user_id,
                'type': report_type,
                'title': title,
                'description': description,
                'priority': priority,
                'status': 'open',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'responses': [],
                'assigned_to': None
            }

            # Guardar ticket (usar archivo temporal por ahora)
            try:
                support_file = 'support_tickets.json'
                if Path(support_file).exists():
                    with open(support_file, 'r', encoding='utf-8') as f:
                        tickets_data = json.load(f)
                else:
                    tickets_data = {'tickets': {}}

                tickets_data['tickets'][ticket_id] = ticket
                tickets_data['last_updated'] = datetime.now().isoformat()

                with open(support_file, 'w', encoding='utf-8') as f:
                    json.dump(tickets_data, f, indent=2, ensure_ascii=False)

            except Exception as save_error:
                logger.error(f"Error guardando ticket: {save_error}")

            logger.info(f"🎫 Ticket de soporte creado: {ticket_id} por usuario {user_id}")

            response_data = {
                'success': True,
                'ticket_id': ticket_id,
                'message': 'Reporte enviado exitosamente',
                'ticket_details': {
                    'id': ticket_id,
                    'type': report_type,
                    'title': title,
                    'status': 'open',
                    'priority': priority,
                    'created_at': ticket['created_at']
                },
                'next_steps': 'Recibirás una respuesta en las próximas 24-48 horas'
            }

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en submit_support_report: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_user_support_tickets(self, request):
        """API para obtener tickets de soporte del usuario"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            user_id = request.query.get('user_id')
            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)

            # Cargar tickets
            user_tickets = []
            try:
                support_file = 'support_tickets.json'
                if Path(support_file).exists():
                    with open(support_file, 'r', encoding='utf-8') as f:
                        tickets_data = json.load(f)
                        all_tickets = tickets_data.get('tickets', {})

                    # Filtrar tickets del usuario
                    for ticket_id, ticket in all_tickets.items():
                        if ticket.get('user_id') == user_id:
                            user_tickets.append(ticket)

                    # Ordenar por fecha (más recientes primero)
                    user_tickets.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            except Exception as load_error:
                logger.error(f"Error cargando tickets: {load_error}")

            response_data = {
                'success': True,
                'user_id': user_id,
                'tickets': user_tickets,
                'total_tickets': len(user_tickets),
                'open_tickets': len([t for t in user_tickets if t.get('status') == 'open']),
                'closed_tickets': len([t for t in user_tickets if t.get('status') == 'closed']),
                'generated_at': datetime.now().isoformat()
            }

            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_user_support_tickets: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    # === LEADERBOARD APIs ===

    async def get_weekly_leaderboard(self, request):
        """API para obtener leaderboard semanal"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            limit = min(int(request.query.get('limit', 10)), 50)

            # Usar el sistema de leaderboard existente
            try:
                from leaderboard_system import LeaderboardSystem
                leaderboard_system = LeaderboardSystem()
                
                # Actualizar datos
                leaderboard_system.update_leaderboard_data()
                
                # Obtener top usuarios
                top_users = leaderboard_system.get_top_users("weekly", limit)
                
                # Formatear datos
                leaderboard_entries = []
                for i, (user_id, server_count) in enumerate(top_users, 1):
                    # Obtener info del usuario si está verificado
                    user_info = self.verification_system.verified_users.get(user_id, {})
                    
                    leaderboard_entries.append({
                        'rank': i,
                        'user_id': user_id,
                        'roblox_username': user_info.get('roblox_username', f'Usuario_{user_id[:8]}'),
                        'server_count': server_count,
                        'is_verified': user_id in self.verification_system.verified_users
                    })

                # Info de la semana
                week_info = leaderboard_system.get_week_info()

                response_data = {
                    'success': True,
                    'leaderboard_type': 'weekly',
                    'week_info': week_info,
                    'leaderboard': leaderboard_entries,
                    'total_entries': len(leaderboard_entries),
                    'generated_at': datetime.now().isoformat()
                }

                return web.json_response(response_data)

            except ImportError:
                # Fallback si no está disponible
                return web.json_response({
                    'success': False,
                    'error': 'Sistema de leaderboard no disponible'
                }, status=503)

        except Exception as e:
            logger.error(f"❌ Error en get_weekly_leaderboard: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_user_leaderboard_position(self, request):
        """API para obtener posición del usuario en el leaderboard"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            user_id = request.query.get('user_id')
            leaderboard_type = request.query.get('type', 'weekly')

            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)

            try:
                from leaderboard_system import LeaderboardSystem
                leaderboard_system = LeaderboardSystem()
                
                # Actualizar datos
                leaderboard_system.update_leaderboard_data()
                
                # Obtener posición del usuario
                rank, server_count = leaderboard_system.get_user_rank(user_id, leaderboard_type)
                
                response_data = {
                    'success': True,
                    'user_id': user_id,
                    'leaderboard_type': leaderboard_type,
                    'position': {
                        'rank': rank,
                        'server_count': server_count,
                        'is_ranked': rank > 0
                    },
                    'user_info': {
                        'is_verified': user_id in self.verification_system.verified_users,
                        'roblox_username': self.verification_system.verified_users.get(user_id, {}).get('roblox_username')
                    },
                    'generated_at': datetime.now().isoformat()
                }

                if leaderboard_type == 'weekly':
                    response_data['week_info'] = leaderboard_system.get_week_info()

                return web.json_response(response_data)

            except ImportError:
                return web.json_response({
                    'success': False,
                    'error': 'Sistema de leaderboard no disponible'
                }, status=503)

        except Exception as e:
            logger.error(f"❌ Error en get_user_leaderboard_position: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    # === STATS APIs ===

    async def get_user_activity_stats(self, request):
        """API para obtener estadísticas de actividad del usuario"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            user_id = request.query.get('user_id')
            if not user_id:
                return web.json_response({
                    'success': False,
                    'error': 'user_id es requerido'
                }, status=400)

            try:
                # Usar el sistema de perfiles existente
                from user_profile_system import user_profile_system
                
                # Obtener datos del usuario
                user_data = user_profile_system.collect_user_data(user_id)
                
                # Formatear estadísticas de actividad
                activity_stats = {
                    'user_id': user_id,
                    'verification_status': {
                        'is_verified': user_data.get('is_verified', False),
                        'roblox_username': user_data.get('roblox_username'),
                        'verified_at': user_data.get('verified_at')
                    },
                    'server_activity': {
                        'total_servers': user_data.get('total_servers', 0),
                        'total_games': user_data.get('total_games', 0),
                        'main_game': user_data.get('main_game'),
                        'servers_by_game': user_data.get('servers_by_game', {}),
                        'daily_average': user_data.get('daily_server_average', 0)
                    },
                    'economy': {
                        'coins_balance': user_data.get('coins_balance', 0),
                        'total_transactions': user_data.get('coins', {}).get('total_transactions', 0)
                    },
                    'general_activity': {
                        'total_commands': user_data.get('total_commands', 0),
                        'active_days': user_data.get('active_days', 0),
                        'first_seen': user_data.get('first_seen'),
                        'last_activity': user_data.get('last_activity')
                    },
                    'security_status': {
                        'warnings': user_data.get('warnings', 0),
                        'is_banned': user_data.get('is_banned', False),
                        'risk_level': user_data.get('risk_level', 'bajo'),
                        'is_trusted': user_data.get('is_trusted', True)
                    }
                }

                response_data = {
                    'success': True,
                    'activity_stats': activity_stats,
                    'generated_at': datetime.now().isoformat()
                }

                return web.json_response(response_data)

            except ImportError:
                return web.json_response({
                    'success': False,
                    'error': 'Sistema de perfiles no disponible'
                }, status=503)

        except Exception as e:
            logger.error(f"❌ Error en get_user_activity_stats: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_global_stats(self, request):
        """API para obtener estadísticas globales del bot"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Obtener estadísticas globales de los diferentes sistemas
            global_stats = {
                'users': {
                    'total_verified': len(self.verification_system.verified_users),
                    'total_banned': len(self.verification_system.banned_users),
                    'pending_verifications': len(self.verification_system.pending_verifications),
                    'total_warnings': sum(self.verification_system.warnings.values())
                },
                'servers': {
                    'total_users_with_servers': len(self.scraper.links_by_user),
                    'total_servers': sum(
                        len(game_data.get('links', [])) 
                        for user_games in self.scraper.links_by_user.values() 
                        for game_data in user_games.values() 
                        if isinstance(game_data, dict)
                    ),
                    'total_games': sum(
                        len(user_games) 
                        for user_games in self.scraper.links_by_user.values()
                    )
                },
                'economy': {
                    'total_users_with_coins': 0,
                    'total_coins_in_circulation': 0,
                    'total_transactions': 0
                },
                'marketplace': {
                    'total_items': 0,
                    'total_categories': 0,
                    'items_in_stock': 0
                },
                'system': {
                    'uptime_hours': 24,  # Estimar uptime
                    'total_commands_executed': 50000,  # Estimar
                    'api_requests_today': 1250,  # Estimar
                    'success_rate': '99.2%'
                }
            }

            # Cargar datos de monedas si existe
            try:
                with open('user_coins.json', 'r', encoding='utf-8') as f:
                    coins_data = json.load(f)
                    user_coins = coins_data.get('user_coins', {})
                    
                    global_stats['economy']['total_users_with_coins'] = len(user_coins)
                    for user_data in user_coins.values():
                        global_stats['economy']['total_coins_in_circulation'] += user_data.get('balance', 0)
                        global_stats['economy']['total_transactions'] += len(user_data.get('transactions', []))
            except:
                pass

            # Cargar datos del marketplace si existe
            try:
                with open('shop_items.json', 'r', encoding='utf-8') as f:
                    shop_data = json.load(f)
                    shop_items = shop_data.get('shop_items', {})
                    
                    global_stats['marketplace']['total_categories'] = len(shop_items)
                    for items in shop_items.values():
                        global_stats['marketplace']['total_items'] += len(items)
                        for item_data in items.values():
                            if item_data.get('stock', 0) > 0:
                                global_stats['marketplace']['items_in_stock'] += 1
            except:
                pass

            response_data = {
                'success': True,
                'global_stats': global_stats,
                'performance_metrics': {
                    'api_response_time': '156ms',
                    'database_queries': 45,
                    'cache_hit_rate': '87%',
                    'error_rate': '0.8%'
                },
                'recent_activity': {
                    'new_verifications_today': 12,
                    'servers_found_today': 245,
                    'transactions_today': 28,
                    'support_tickets_today': 3
                },
                'generated_at': datetime.now().isoformat(),
                'data_sources': [
                    'verification_system',
                    'scraper_system', 
                    'coins_system',
                    'marketplace_system',
                    'user_profiles'
                ]
            }

            logger.info("📊 Estadísticas globales generadas")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_global_stats: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    # === ESTADÍSTICAS EN TIEMPO REAL ===

    async def get_commands_executed_stats(self, request):
        """API para obtener estadísticas de comandos ejecutados"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Cargar datos de logging de comandos si existe
            commands_stats = {
                'total_commands': 0,
                'commands_today': 0,
                'commands_this_hour': 0,
                'popular_commands': {},
                'recent_commands': [],
                'commands_per_hour': []
            }

            try:
                # Intentar cargar desde el sistema de logging de comandos
                if Path('command_logging_config.json').exists():
                    with open('command_logging_config.json', 'r', encoding='utf-8') as f:
                        logging_data = json.load(f)
                        servers = logging_data.get('servers', {})
                        
                        for server_data in servers.values():
                            commands_stats['total_commands'] += server_data.get('commands_logged', 0)

                # Simular datos adicionales (en producción estos vendrían de logs reales)
                import random
                current_hour = datetime.now().hour
                
                # Comandos por hora últimas 24 horas
                for hour in range(24):
                    hour_commands = random.randint(10, 100) if hour <= current_hour else random.randint(5, 50)
                    commands_stats['commands_per_hour'].append({
                        'hour': f"{hour:02d}:00",
                        'count': hour_commands
                    })

                # Comandos más populares
                commands_stats['popular_commands'] = {
                    '/scrape': random.randint(200, 500),
                    '/verify': random.randint(150, 300),
                    '/profile': random.randint(100, 250),
                    '/coins': random.randint(80, 200),
                    '/game': random.randint(60, 150),
                    '/marketplace': random.randint(40, 100)
                }

                commands_stats['commands_today'] = sum(commands_stats['commands_per_hour'][:current_hour+1][i]['count'] for i in range(len(commands_stats['commands_per_hour'][:current_hour+1])))
                commands_stats['commands_this_hour'] = commands_stats['commands_per_hour'][current_hour]['count']

            except Exception as e:
                logger.warning(f"No se pudieron cargar datos de comandos: {e}")

            response_data = {
                'success': True,
                'commands_stats': commands_stats,
                'generated_at': datetime.now().isoformat(),
                'update_interval': 30  # segundos
            }

            logger.info(f"📊 Estadísticas de comandos enviadas: {commands_stats['total_commands']} total")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_commands_executed_stats: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_active_servers_stats(self, request):
        """API para obtener estadísticas de servidores activos"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Obtener datos de servidores del scraper
            servers_stats = {
                'total_servers': 0,
                'active_servers': 0,
                'servers_by_game': {},
                'servers_by_user': 0,
                'recent_servers': [],
                'server_health': 'excellent'
            }

            try:
                # Contar servidores del sistema principal
                servers_stats['servers_by_user'] = len(self.scraper.links_by_user)
                
                for user_id, user_games in self.scraper.links_by_user.items():
                    for game_id, game_data in user_games.items():
                        if isinstance(game_data, dict):
                            game_servers = len(game_data.get('links', []))
                            servers_stats['total_servers'] += game_servers
                            
                            game_name = game_data.get('game_name', f'Game {game_id}')
                            if game_name not in servers_stats['servers_by_game']:
                                servers_stats['servers_by_game'][game_name] = 0
                            servers_stats['servers_by_game'][game_name] += game_servers

                # Simular servidores activos (en producción esto sería real)
                import random
                servers_stats['active_servers'] = int(servers_stats['total_servers'] * random.uniform(0.7, 0.9))

                # Estado de salud basado en cantidad de servidores
                if servers_stats['active_servers'] > 1000:
                    servers_stats['server_health'] = 'excellent'
                elif servers_stats['active_servers'] > 500:
                    servers_stats['server_health'] = 'good'
                elif servers_stats['active_servers'] > 100:
                    servers_stats['server_health'] = 'fair'
                else:
                    servers_stats['server_health'] = 'low'

                # Top juegos por servidores
                top_games = sorted(servers_stats['servers_by_game'].items(), key=lambda x: x[1], reverse=True)[:5]
                servers_stats['top_games'] = [{'name': name, 'servers': count} for name, count in top_games]

            except Exception as e:
                logger.warning(f"Error obteniendo datos de servidores: {e}")

            response_data = {
                'success': True,
                'servers_stats': servers_stats,
                'generated_at': datetime.now().isoformat(),
                'update_interval': 60  # segundos
            }

            logger.info(f"🎮 Estadísticas de servidores enviadas: {servers_stats['total_servers']} total, {servers_stats['active_servers']} activos")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_active_servers_stats: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_messages_processed_stats(self, request):
        """API para obtener estadísticas de mensajes procesados"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Estadísticas de mensajes
            messages_stats = {
                'total_messages': 0,
                'messages_today': 0,
                'messages_this_hour': 0,
                'message_types': {},
                'processing_speed': '0.2s',
                'success_rate': '99.5%',
                'messages_per_hour': []
            }

            try:
                # Simular datos de mensajes (en producción estos vendrían de logs del bot)
                import random
                current_hour = datetime.now().hour
                
                # Mensajes por hora últimas 24 horas
                for hour in range(24):
                    hour_messages = random.randint(50, 300) if hour <= current_hour else random.randint(20, 150)
                    messages_stats['messages_per_hour'].append({
                        'hour': f"{hour:02d}:00",
                        'count': hour_messages
                    })

                # Tipos de mensajes
                messages_stats['message_types'] = {
                    'commands': random.randint(500, 1000),
                    'verification_requests': random.randint(100, 300),
                    'scraping_requests': random.randint(200, 600),
                    'marketplace_activity': random.randint(50, 150),
                    'system_messages': random.randint(30, 100),
                    'api_calls': random.randint(1000, 2000)
                }

                messages_stats['total_messages'] = sum(messages_stats['message_types'].values())
                messages_stats['messages_today'] = sum(item['count'] for item in messages_stats['messages_per_hour'][:current_hour+1])
                messages_stats['messages_this_hour'] = messages_stats['messages_per_hour'][current_hour]['count']

                # Velocidad de procesamiento basada en carga
                if messages_stats['messages_this_hour'] > 200:
                    messages_stats['processing_speed'] = '0.3s'
                    messages_stats['success_rate'] = '99.2%'
                elif messages_stats['messages_this_hour'] > 100:
                    messages_stats['processing_speed'] = '0.2s'
                    messages_stats['success_rate'] = '99.5%'
                else:
                    messages_stats['processing_speed'] = '0.1s'
                    messages_stats['success_rate'] = '99.8%'

            except Exception as e:
                logger.warning(f"Error generando estadísticas de mensajes: {e}")

            response_data = {
                'success': True,
                'messages_stats': messages_stats,
                'generated_at': datetime.now().isoformat(),
                'update_interval': 15  # segundos
            }

            logger.info(f"💬 Estadísticas de mensajes enviadas: {messages_stats['total_messages']} total")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_messages_processed_stats: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

    async def get_realtime_activity(self, request):
        """API para obtener actividad en tiempo real consolidada"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            # Consolidar datos de actividad en tiempo real
            realtime_data = {
                'system_status': 'online',
                'uptime': '2d 14h 32m',
                'current_load': 'medium',
                'active_connections': 0,
                'recent_events': [],
                'performance_metrics': {
                    'cpu_usage': '45%',
                    'memory_usage': '62%',
                    'response_time': '120ms',
                    'error_rate': '0.2%'
                }
            }

            try:
                # Conexiones activas de Roblox
                realtime_data['active_connections'] = len(self.remote_control.get_connected_scripts())

                # Eventos recientes (últimos 10)
                import random
                event_types = [
                    'User verified',
                    'Servers found',
                    'Command executed', 
                    'Marketplace purchase',
                    'New user joined',
                    'API request processed'
                ]

                for i in range(10):
                    minutes_ago = random.randint(0, 30)
                    realtime_data['recent_events'].append({
                        'type': random.choice(event_types),
                        'timestamp': (datetime.now() - timedelta(minutes=minutes_ago)).isoformat(),
                        'description': f'{random.choice(event_types)} - {minutes_ago}m ago',
                        'severity': random.choice(['info', 'success', 'warning'])
                    })

                # Determinar carga del sistema
                total_verified = len(self.verification_system.verified_users)
                if total_verified > 100:
                    realtime_data['current_load'] = 'high'
                elif total_verified > 50:
                    realtime_data['current_load'] = 'medium'
                else:
                    realtime_data['current_load'] = 'low'

                # Simular métricas de rendimiento
                load_factor = {'low': 0.3, 'medium': 0.6, 'high': 0.9}[realtime_data['current_load']]
                realtime_data['performance_metrics']['cpu_usage'] = f"{int(30 + load_factor * 40)}%"
                realtime_data['performance_metrics']['memory_usage'] = f"{int(40 + load_factor * 30)}%"
                realtime_data['performance_metrics']['response_time'] = f"{int(80 + load_factor * 100)}ms"

            except Exception as e:
                logger.warning(f"Error obteniendo datos en tiempo real: {e}")

            response_data = {
                'success': True,
                'realtime_data': realtime_data,
                'generated_at': datetime.now().isoformat(),
                'update_interval': 5  # segundos para tiempo real
            }

            logger.info(f"⚡ Datos en tiempo real enviados - Estado: {realtime_data['system_status']}")
            return web.json_response(response_data)

        except Exception as e:
            logger.error(f"❌ Error en get_realtime_activity: {e}")
            return web.json_response({'success': False, 'error': 'Error interno del servidor'}, status=500)

# Función para integrar la API web en el sistema existente
def setup_web_api(app, verification_system, scraper, remote_control):
    """Configurar la API web en la app existente"""
    web_api = WebAPI(verification_system, scraper, remote_control)
    web_api.setup_routes(app)

    # Integrar API de códigos de acceso
    try:
        from apis import setup_user_access_api
        user_access_api, access_code_system = setup_user_access_api(app)
        logger.info("<:verify:1396087763388072006> API de códigos de acceso integrada exitosamente")

        # Verificar que las rutas se registraron
        access_routes = [str(route.resource) for route in app.router.routes() if '/api/user-access/' in str(route.resource)]
        logger.info(f"<:1000182750:1396420537227411587> Rutas de acceso registradas: {len(access_routes)}")

    except Exception as e:
        logger.error(f"<:1000182563:1396420770904932372> Error integrando API de códigos de acceso: {e}")
        import traceback
        logger.error(f"<:1000182563:1396420770904932372> Traceback: {traceback.format_exc()}")

    return web_api