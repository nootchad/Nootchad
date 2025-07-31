
import discord
from discord.ext import commands
import aiohttp
import json
import time
import secrets
import logging
from datetime import datetime, timedelta
from aiohttp import web
import asyncio

logger = logging.getLogger(__name__)

class DiscordOAuth2System:
    def __init__(self):
        # Configuración OAuth2 de Discord
        self.client_id = "1388660674573631549"  # Obtener de Discord Developer Portal
        self.client_secret = "XUppnOJNCNZSVouqe6KU5FH7qkpqyXtn"  # Obtener de Discord Developer Portal
        self.redirect_uri = "https://tu-repl-url.replit.dev/auth/discord/callback"
        
        # Scopes que necesitamos
        self.scopes = ["identify", "email"]  # identify para info básica, email para email
        
        # Almacenamiento temporal de tokens
        self.user_tokens = {}
        
        # URLs de Discord
        self.discord_api_base = "https://discord.com/api/v10"
        self.authorize_url = "https://discord.com/api/oauth2/authorize"
        self.token_url = "https://discord.com/api/oauth2/token"
        
    def generate_oauth_url(self, state=None):
        """Generar URL de autorización OAuth2"""
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'state': state
        }
        
        param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{self.authorize_url}?{param_string}", state
    
    async def exchange_code_for_token(self, code):
        """Intercambiar código de autorización por token de acceso"""
        try:
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=data, headers=headers) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        return token_data
                    else:
                        logger.error(f"Error obteniendo token: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error en intercambio de código: {e}")
            return None
    
    async def get_user_info_from_discord(self, access_token):
        """Obtener información completa del usuario desde Discord API"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Obtener información básica
                async with session.get(f"{self.discord_api_base}/users/@me", headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        
                        # Procesar información completa
                        discord_info = {
                            'user_id': user_data['id'],
                            'username': user_data['username'],
                            'discriminator': user_data.get('discriminator', '0'),
                            'global_name': user_data.get('global_name'),
                            'display_name': user_data.get('global_name') or user_data['username'],
                            'email': user_data.get('email'),
                            'verified': user_data.get('verified', False),
                            'avatar': user_data.get('avatar'),
                            'avatar_url': self._get_avatar_url(user_data['id'], user_data.get('avatar')),
                            'banner': user_data.get('banner'),
                            'banner_url': self._get_banner_url(user_data['id'], user_data.get('banner')),
                            'accent_color': user_data.get('accent_color'),
                            'locale': user_data.get('locale'),
                            'mfa_enabled': user_data.get('mfa_enabled', False),
                            'premium_type': user_data.get('premium_type'),
                            'public_flags': user_data.get('public_flags', 0),
                            'flags': user_data.get('flags', 0),
                            'profile_url': f"https://discord.com/users/{user_data['id']}",
                            'oauth_authorized': True,
                            'authorization_date': datetime.now().isoformat(),
                            'data_source': 'discord_oauth2'
                        }
                        
                        # Decodificar badges de public_flags
                        discord_info['badges'] = self._decode_user_flags(user_data.get('public_flags', 0))
                        
                        return discord_info
                    else:
                        logger.error(f"Error obteniendo info de usuario: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error obteniendo información de Discord: {e}")
            return None
    
    def _get_avatar_url(self, user_id, avatar_hash):
        """Generar URL del avatar"""
        if avatar_hash:
            extension = "gif" if avatar_hash.startswith("a_") else "png"
            return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{extension}?size=512"
        else:
            # Avatar por defecto
            default_avatar = int(user_id) % 5
            return f"https://cdn.discordapp.com/embed/avatars/{default_avatar}.png"
    
    def _get_banner_url(self, user_id, banner_hash):
        """Generar URL del banner"""
        if banner_hash:
            extension = "gif" if banner_hash.startswith("a_") else "png"
            return f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{extension}?size=1024"
        return None
    
    def _decode_user_flags(self, flags):
        """Decodificar flags de usuario en badges legibles"""
        badges = {}
        flag_meanings = {
            1 << 0: 'discord_employee',
            1 << 1: 'partnered_server_owner', 
            1 << 2: 'hypesquad_events',
            1 << 3: 'bug_hunter_level_1',
            1 << 6: 'hypesquad_bravery',
            1 << 7: 'hypesquad_brilliance',
            1 << 8: 'hypesquad_balance',
            1 << 9: 'early_supporter',
            1 << 10: 'team_user',
            1 << 14: 'bug_hunter_level_2',
            1 << 16: 'verified_bot',
            1 << 17: 'early_verified_bot_developer',
            1 << 18: 'discord_certified_moderator',
            1 << 19: 'bot_http_interactions',
            1 << 22: 'active_developer'
        }
        
        for flag_value, badge_name in flag_meanings.items():
            badges[badge_name] = bool(flags & flag_value)
        
        return badges
    
    def setup_routes(self, app):
        """Configurar rutas OAuth2 en la aplicación web"""
        
        # Ruta para iniciar autorización
        app.router.add_get('/auth/discord/start', self.start_oauth)
        
        # Ruta de callback de Discord
        app.router.add_get('/auth/discord/callback', self.oauth_callback)
        
        # Ruta para obtener información del usuario autorizado
        app.router.add_get('/auth/discord/user/{user_id}', self.get_authorized_user_info)
        
        # Ruta para revocar autorización
        app.router.add_post('/auth/discord/revoke/{user_id}', self.revoke_authorization)
        
        logger.info("🔐 Rutas OAuth2 de Discord configuradas")
    
    async def start_oauth(self, request):
        """Iniciar proceso de autorización OAuth2"""
        try:
            # Generar estado para seguridad
            oauth_url, state = self.generate_oauth_url()
            
            # Opcional: guardar el estado para validar después
            # En producción, deberías usar una base de datos o Redis
            
            # Responder con URL de autorización
            return web.json_response({
                'success': True,
                'authorization_url': oauth_url,
                'state': state,
                'instructions': 'Redirige al usuario a authorization_url para autorizar la aplicación'
            })
            
        except Exception as e:
            logger.error(f"Error iniciando OAuth: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)
    
    async def oauth_callback(self, request):
        """Manejar callback de autorización de Discord"""
        try:
            # Obtener parámetros del callback
            code = request.query.get('code')
            state = request.query.get('state')
            error = request.query.get('error')
            
            if error:
                logger.warning(f"Error de autorización Discord: {error}")
                return web.Response(
                    text=f"<h1>Error de Autorización</h1><p>Error: {error}</p>",
                    content_type='text/html',
                    status=400
                )
            
            if not code:
                return web.Response(
                    text="<h1>Error</h1><p>Código de autorización faltante</p>",
                    content_type='text/html',
                    status=400
                )
            
            # Intercambiar código por token
            token_data = await self.exchange_code_for_token(code)
            
            if not token_data:
                return web.Response(
                    text="<h1>Error</h1><p>No se pudo obtener token de acceso</p>",
                    content_type='text/html',
                    status=500
                )
            
            # Obtener información del usuario
            access_token = token_data['access_token']
            user_info = await self.get_user_info_from_discord(access_token)
            
            if not user_info:
                return web.Response(
                    text="<h1>Error</h1><p>No se pudo obtener información del usuario</p>",
                    content_type='text/html',
                    status=500
                )
            
            # Guardar token para uso futuro
            user_id = user_info['user_id']
            self.user_tokens[user_id] = {
                'access_token': access_token,
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': time.time() + token_data.get('expires_in', 3600),
                'user_info': user_info,
                'authorized_at': time.time()
            }
            
            logger.info(f"✅ Usuario autorizado correctamente: {user_info['username']} (ID: {user_id})")
            
            # Respuesta exitosa
            success_html = f"""
            <html>
            <head>
                <title>¡Autorización Exitosa!</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; margin: 50px; }}
                    .success {{ color: #43b581; }}
                    .info {{ background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ ¡Autorización Exitosa!</h1>
                <div class="info">
                    <h3>Información Obtenida:</h3>
                    <p><strong>Usuario:</strong> {user_info['display_name']} (@{user_info['username']})</p>
                    <p><strong>ID:</strong> {user_id}</p>
                    <p><strong>Email:</strong> {user_info.get('email', 'No proporcionado')}</p>
                    <p><strong>Verificado:</strong> {'Sí' if user_info.get('verified') else 'No'}</p>
                </div>
                <p>Tu información está ahora disponible a través de la API.</p>
                <p><small>Puedes cerrar esta ventana.</small></p>
            </body>
            </html>
            """
            
            return web.Response(text=success_html, content_type='text/html')
            
        except Exception as e:
            logger.error(f"Error en callback OAuth: {e}")
            return web.Response(
                text=f"<h1>Error Interno</h1><p>Error: {str(e)}</p>",
                content_type='text/html',
                status=500
            )
    
    async def get_authorized_user_info(self, request):
        """Obtener información de usuario autorizado"""
        try:
            user_id = request.match_info['user_id']
            
            if user_id not in self.user_tokens:
                return web.json_response({
                    'success': False,
                    'error': 'Usuario no autorizado o token expirado'
                }, status=404)
            
            token_info = self.user_tokens[user_id]
            
            # Verificar si el token ha expirado
            if time.time() > token_info['expires_at']:
                del self.user_tokens[user_id]
                return web.json_response({
                    'success': False,
                    'error': 'Token expirado, se requiere nueva autorización'
                }, status=401)
            
            # Devolver información del usuario
            return web.json_response({
                'success': True,
                'user_info': token_info['user_info'],
                'authorized_at': token_info['authorized_at'],
                'expires_at': token_info['expires_at']
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo info de usuario autorizado: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)
    
    async def revoke_authorization(self, request):
        """Revocar autorización de usuario"""
        try:
            user_id = request.match_info['user_id']
            
            if user_id in self.user_tokens:
                # Opcional: revocar token en Discord API
                # await self._revoke_token_on_discord(self.user_tokens[user_id]['access_token'])
                
                del self.user_tokens[user_id]
                logger.info(f"🚫 Autorización revocada para usuario {user_id}")
                
                return web.json_response({
                    'success': True,
                    'message': 'Autorización revocada exitosamente'
                })
            else:
                return web.json_response({
                    'success': False,
                    'error': 'Usuario no encontrado'
                }, status=404)
                
        except Exception as e:
            logger.error(f"Error revocando autorización: {e}")
            return web.json_response({
                'success': False,
                'error': 'Error interno del servidor'
            }, status=500)

# Instancia global
discord_oauth = DiscordOAuth2System()
