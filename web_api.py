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

        # Middleware de CORS para permitir acceso desde cualquier origen
        @web.middleware
        async def cors_middleware(request, handler):
            # Manejar preflight requests (OPTIONS)
            if request.method == 'OPTIONS':
                response = web.Response()
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
                response.headers['Access-Control-Max-Age'] = '86400'
                return response
            
            # Procesar la petición normal
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
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
        
        # Rutas de verificación externa - agregadas correctamente
        app.router.add_post('/api/external-verification/request', self.external_verification_request)
        app.router.add_post('/api/external-verification/check', self.external_verification_check)
        
        # Otras rutas
        app.router.add_get('/api/leaderboard', self.get_leaderboard_api)
        app.router.add_get('/api/economy-stats', self.get_economy_stats)


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
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            discord_id = str(data.get('discord_id', ''))
            roblox_username = data.get('roblox_username', '').strip()

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
            logger.error(f"❌ Error en external_verification_request: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

    async def external_verification_check(self, request):
        """API para verificar si el código fue puesto en la descripción"""
        try:
            if not self.verify_auth(request):
                return web.json_response({'error': 'Unauthorized'}, status=401)

            data = await request.json()
            discord_id = str(data.get('discord_id', ''))
            roblox_username = data.get('roblox_username', '').strip()

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
            logger.error(f"❌ Error en external_verification_check: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
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


# Función para integrar la API web en el sistema existente
def setup_web_api(app, verification_system, scraper, remote_control):
    """Configurar la API web en la app existente"""
    web_api = WebAPI(verification_system, scraper, remote_control)
    web_api.setup_routes(app)
    return web_api