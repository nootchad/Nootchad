
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
        """Obtener información completa de Discord del usuario con manejo robusto de errores"""
        try:
            # Método 1: Verificar si el usuario tiene autorización OAuth2
            try:
                from discord_oauth import discord_oauth
                if user_id in discord_oauth.user_tokens:
                    token_info = discord_oauth.user_tokens[user_id]
                    # Verificar si el token no ha expirado
                    if time.time() < token_info['expires_at']:
                        oauth_info = token_info['user_info'].copy()
                        oauth_info['data_source'] = 'oauth2_authorized'
                        oauth_info['authorization_status'] = 'active'
                        logger.info(f"<a:verify2:1418486831993061497> Usuario {user_id} obtenido via OAuth2: {oauth_info.get('username', 'N/A')}")
                        return oauth_info
                    else:
                        # Token expirado, limpiar
                        del discord_oauth.user_tokens[user_id]
                        logger.info(f"⏰ Token OAuth2 expirado para {user_id}, usando método tradicional")
            except ImportError:
                logger.debug("Sistema OAuth2 no disponible, usando método tradicional")
            except Exception as oauth_error:
                logger.debug(f"Error verificando OAuth2 para {user_id}: {oauth_error}")
            
            # Método 2: Validar que user_id sea válido
            try:
                user_id_int = int(user_id)
                if user_id_int <= 0:
                    raise ValueError("ID de usuario inválido")
            except (ValueError, TypeError) as e:
                logger.error(f"<:1000182563:1396420770904932372> ID de usuario inválido {user_id}: {e}")
                return self._generate_fallback_user_info(user_id, "ID de usuario inválido")
            
            user = None
            
            # Método 3: Intentar obtener desde caché del bot
            try:
                if hasattr(bot, 'get_user') and bot.get_user:
                    user = bot.get_user(user_id_int)
                    if user:
                        logger.info(f"<a:verify2:1418486831993061497> Usuario {user_id} encontrado en caché del bot: {user.name}")
                    else:
                        logger.debug(f"Usuario {user_id} no encontrado en caché del bot")
            except Exception as e:
                logger.debug(f"Error en caché del bot para {user_id}: {e}")
            
            # Método 4: Buscar en servidores del bot si no se encontró en caché
            if not user and hasattr(bot, 'guilds') and bot.guilds:
                try:
                    for guild in bot.guilds:
                        try:
                            member = guild.get_member(user_id_int)
                            if member:
                                user = member
                                logger.info(f"<a:verify2:1418486831993061497> Usuario {user_id} encontrado en servidor {guild.name}: {member.name}")
                                break
                        except Exception as guild_error:
                            logger.debug(f"Error buscando en guild {guild.id}: {guild_error}")
                            continue
                except Exception as e:
                    logger.debug(f"Error buscando en servidores para {user_id}: {e}")
            
            if user:
                # Usuario encontrado - obtener información completa
                try:
                    discord_info = self._extract_user_info_safely(user, user_id)
                    discord_info['oauth_available'] = True  # Indica que OAuth2 está disponible
                    discord_info['data_source'] = 'bot_cache_or_guild'
                    logger.info(f"<:verify:1396087763388072006> Info de Discord obtenida exitosamente para {user_id}: {discord_info.get('username', 'N/A')}")
                    return discord_info
                except Exception as extract_error:
                    logger.error(f"<:1000182563:1396420770904932372> Error extrayendo info del usuario {user_id}: {extract_error}")
                    return self._generate_fallback_user_info(user_id, f"Error extrayendo información: {extract_error}")
            
            else:
                # Usuario no encontrado - generar fallback con sugerencia de OAuth2
                fallback_info = self._generate_enhanced_fallback_user_info(user_id)
                fallback_info['oauth_available'] = True
                fallback_info['oauth_suggestion'] = f"Para obtener información completa, el usuario puede autorizar la aplicación en: /auth/discord/start"
                logger.warning(f"<:1000182563:1396420770904932372> Usuario {user_id} no encontrado, OAuth2 disponible para mejor información")
                return fallback_info
                
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error crítico obteniendo info de Discord para {user_id}: {e}")
            return self._generate_fallback_user_info(user_id, f"Error crítico: {str(e)}")
    
    def _extract_user_info_safely(self, user, user_id: str) -> dict:
        """Extraer información del usuario de forma segura"""
        try:
            # Obtener nombres de forma segura
            username = getattr(user, 'name', f'Usuario#{user_id[-4:]}')
            display_name = getattr(user, 'display_name', username)
            global_name = getattr(user, 'global_name', None)
            
            # Determinar el nombre a mostrar
            if global_name:
                shown_name = global_name
            elif display_name and display_name != username:
                shown_name = display_name
            else:
                shown_name = username
            
            # Obtener URLs de avatar de forma segura
            try:
                avatar_url = str(user.display_avatar.url) if hasattr(user, 'display_avatar') and user.display_avatar else None
                default_avatar_url = str(user.default_avatar.url) if hasattr(user, 'default_avatar') and user.default_avatar else f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png"
                
                if not avatar_url:
                    avatar_url = default_avatar_url
            except Exception as avatar_error:
                logger.debug(f"Error obteniendo avatar para {user_id}: {avatar_error}")
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png"
                default_avatar_url = avatar_url
            
            # Información básica del usuario
            discord_info = {
                'user_id': user_id,
                'username': username,
                'display_name': shown_name,
                'discriminator': getattr(user, 'discriminator', '0'),
                'global_name': global_name,
                'avatar_url': avatar_url,
                'avatar_hash': user.avatar.key if hasattr(user, 'avatar') and user.avatar else None,
                'default_avatar_url': default_avatar_url,
                'profile_url': f"https://discord.com/users/{user_id}",
                'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
                'is_bot': getattr(user, 'bot', False),
                'is_system': getattr(user, 'system', False),
                'public_flags': user.public_flags.value if hasattr(user, 'public_flags') and user.public_flags else 0,
                'cached': hasattr(user, 'joined_at'),
                'found_via_fetch': True
            }
            
            # Badges de forma segura
            try:
                if hasattr(user, 'public_flags') and user.public_flags:
                    flags = user.public_flags
                    discord_info['badges'] = {
                        'staff': getattr(flags, 'staff', False),
                        'partner': getattr(flags, 'partner', False),
                        'hypesquad': getattr(flags, 'hypesquad', False),
                        'bug_hunter': getattr(flags, 'bug_hunter', False),
                        'hypesquad_bravery': getattr(flags, 'hypesquad_bravery', False),
                        'hypesquad_brilliance': getattr(flags, 'hypesquad_brilliance', False),
                        'hypesquad_balance': getattr(flags, 'hypesquad_balance', False),
                        'early_supporter': getattr(flags, 'early_supporter', False),
                        'verified_bot_developer': getattr(flags, 'verified_bot_developer', False),
                        'discord_certified_moderator': getattr(flags, 'discord_certified_moderator', False),
                        'active_developer': getattr(flags, 'active_developer', False)
                    }
                else:
                    discord_info['badges'] = {}
            except Exception as badges_error:
                logger.debug(f"Error obteniendo badges para {user_id}: {badges_error}")
                discord_info['badges'] = {}
            
            # Información de servidor si es miembro
            try:
                if hasattr(user, 'joined_at') and user.joined_at:
                    discord_info['joined_at'] = user.joined_at.isoformat()
            except Exception as joined_error:
                logger.debug(f"Error obteniendo fecha de unión para {user_id}: {joined_error}")
            
            logger.info(f"<:verify:1396087763388072006> Info de Discord extraída exitosamente para {user_id}: {shown_name}")
            return discord_info
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en _extract_user_info_safely para {user_id}: {e}")
            raise
    
    def _generate_enhanced_fallback_user_info(self, user_id: str) -> dict:
        """Generar información mejorada de fallback usando datos existentes del sistema"""
        try:
            # Intentar obtener datos desde user_profiles.json
            existing_data = self._load_existing_profile_data(user_id)
            
            # Calcular fecha de creación desde el ID de Discord
            try:
                discord_epoch = 1420070400000  # 1 de enero 2015
                timestamp = ((int(user_id) >> 22) + discord_epoch) / 1000
                created_at = datetime.fromtimestamp(timestamp).isoformat()
            except Exception as date_error:
                logger.debug(f"Error calculando fecha de creación para {user_id}: {date_error}")
                created_at = None
            
            # Generar avatar por defecto
            try:
                avatar_index = int(user_id) % 5
                default_avatar = f"https://cdn.discordapp.com/embed/avatars/{avatar_index}.png"
            except Exception:
                default_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
            
            # Usar datos existentes si están disponibles
            username = existing_data.get('username', f'Usuario#{user_id[-4:]}')
            display_name = existing_data.get('display_name', username)
            
            enhanced_info = {
                'user_id': user_id,
                'username': username,
                'display_name': display_name,
                'discriminator': existing_data.get('discriminator', '0'),
                'global_name': existing_data.get('global_name'),
                'avatar_url': existing_data.get('avatar_url', default_avatar),
                'avatar_hash': existing_data.get('avatar_hash'),
                'default_avatar_url': default_avatar,
                'profile_url': f"https://discord.com/users/{user_id}",
                'created_at': created_at,
                'is_bot': existing_data.get('is_bot', False),
                'is_system': existing_data.get('is_system', False),
                'public_flags': existing_data.get('public_flags', 0),
                'cached': False,
                'found_via_fetch': False,
                'badges': existing_data.get('badges', {}),
                'fallback_reason': 'Usuario no encontrado en Discord, usando datos del sistema',
                'data_source': 'enhanced_fallback',
                'has_existing_data': bool(existing_data)
            }
            
            logger.info(f"<:1000182750:1396420537227411587> Usando fallback mejorado para {user_id}: {username} (datos existentes: {bool(existing_data)})")
            return enhanced_info
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en fallback mejorado para {user_id}: {e}")
            return self._generate_fallback_user_info(user_id, f"Error en fallback mejorado: {str(e)}")
    
    def _load_existing_profile_data(self, user_id: str) -> dict:
        """Cargar datos existentes del perfil de usuario"""
        try:
            import json
            
            # Intentar cargar desde user_profiles.json
            try:
                with open('user_profiles.json', 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    existing_profile = profiles_data.get('user_profiles', {}).get(user_id, {})
                    
                    if existing_profile:
                        return {
                            'username': existing_profile.get('username'),
                            'display_name': existing_profile.get('display_name'),
                            'discriminator': existing_profile.get('discriminator'),
                            'global_name': existing_profile.get('global_name'),
                            'avatar_url': existing_profile.get('avatar_url'),
                            'avatar_hash': existing_profile.get('avatar_hash'),
                            'is_bot': existing_profile.get('is_bot'),
                            'is_system': existing_profile.get('is_system'),
                            'public_flags': existing_profile.get('public_flags'),
                            'badges': existing_profile.get('badges')
                        }
            except Exception as profile_error:
                logger.debug(f"Error leyendo user_profiles.json para {user_id}: {profile_error}")
            
            return {}
            
        except Exception as e:
            logger.debug(f"Error cargando datos existentes para {user_id}: {e}")
            return {}

    def _generate_fallback_user_info(self, user_id: str, reason: str = "Usuario no encontrado") -> dict:
        """Generar información de fallback cuando no se puede obtener del usuario"""
        try:
            # Calcular fecha de creación desde el ID de Discord
            try:
                discord_epoch = 1420070400000  # 1 de enero 2015
                timestamp = ((int(user_id) >> 22) + discord_epoch) / 1000
                created_at = datetime.fromtimestamp(timestamp).isoformat()
            except Exception as date_error:
                logger.debug(f"Error calculando fecha de creación para {user_id}: {date_error}")
                created_at = None
            
            # Generar avatar por defecto
            try:
                avatar_index = int(user_id) % 5
                default_avatar = f"https://cdn.discordapp.com/embed/avatars/{avatar_index}.png"
            except Exception as avatar_error:
                logger.debug(f"Error generando avatar para {user_id}: {avatar_error}")
                default_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
            
            # Intentar obtener nombre desde perfiles existentes
            username = f'Usuario#{user_id[-4:]}'
            display_name = f'Usuario {user_id[-4:]}'
            
            try:
                import json
                with open('user_profiles.json', 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    existing_profile = profiles_data.get('user_profiles', {}).get(user_id, {})
                    if existing_profile.get('username') and not existing_profile['username'].startswith('Usuario#'):
                        username = existing_profile['username']
                        display_name = existing_profile.get('display_name', username)
            except Exception as profile_error:
                logger.debug(f"Error leyendo perfil existente para {user_id}: {profile_error}")
            
            fallback_info = {
                'user_id': user_id,
                'username': username,
                'display_name': display_name,
                'discriminator': '0',
                'global_name': None,
                'avatar_url': default_avatar,
                'avatar_hash': None,
                'default_avatar_url': default_avatar,
                'profile_url': f"https://discord.com/users/{user_id}",
                'created_at': created_at,
                'is_bot': False,
                'is_system': False,
                'public_flags': 0,
                'cached': False,
                'found_via_fetch': False,
                'badges': {},
                'fallback_reason': reason,
                'note': f'Información generada automáticamente - {reason}'
            }
            
            logger.warning(f"<:1000182563:1396420770904932372> Usando información de fallback para {user_id}: {reason}")
            return fallback_info
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error crítico en fallback para {user_id}: {e}")
            # Fallback del fallback
            return {
                'user_id': user_id,
                'username': 'Usuario Desconocido',
                'display_name': 'Usuario Desconocido',
                'discriminator': '0000',
                'global_name': None,
                'avatar_url': "https://cdn.discordapp.com/embed/avatars/0.png",
                'avatar_hash': None,
                'default_avatar_url': "https://cdn.discordapp.com/embed/avatars/0.png",
                'profile_url': f"https://discord.com/users/{user_id}",
                'created_at': None,
                'is_bot': False,
                'is_system': False,
                'public_flags': 0,
                'cached': False,
                'found_via_fetch': False,
                'badges': {},
                'error': f'Error crítico generando fallback: {str(e)}',
                'fallback_reason': f'Error crítico: {str(e)}'
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
                logger.info(f"  <a:verify2:1418486831993061497> {route_info}")
                
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
