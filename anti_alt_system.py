import json
import time
import hashlib
import difflib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import logging
import re
import statistics

logger = logging.getLogger(__name__)

class AntiAltSystem:
    def __init__(self):
        self.data_file = "anti_alt_data.json"
        self.blacklist_file = "user_blacklist.json"
        self.whitelist_file = "user_whitelist.json"

        # Datos principales del sistema
        self.user_fingerprints: Dict[str, Dict] = {}  # discord_id -> fingerprint data
        self.suspicious_activities: Dict[str, List] = {}  # discord_id -> lista de actividades sospechosas
        self.username_history: Dict[str, List] = {}  # discord_id -> historial de usernames
        self.cooldowns: Dict[str, Dict] = {}  # discord_id -> cooldown data
        self.blacklist: Set[str] = set()  # discord_ids baneados permanentemente
        self.whitelist: Set[str] = set()  # discord_ids en lista blanca (confiables)

        # Configuración del sistema
        self.config = {
            'min_account_age_hours': 24,  # Mínimo 24 horas de antigüedad
            'username_similarity_threshold': 0.8,  # 80% de similitud para considerar sospechoso
            'max_codes_per_day': 3,  # Máximo códigos por día por usuario
            'cooldown_base_minutes': 15,  # Cooldown base de 15 minutos
            'cooldown_multiplier': 2,  # Multiplicador para cooldowns dinámicos
            'max_cooldown_hours': 24,  # Cooldown máximo de 24 horas
            'suspicious_threshold': 5,  # Número de actividades sospechosas para ban automático
            'similar_username_penalty_hours': 2,  # Penalty por nombres similares
        }

        self.load_data()

    def load_data(self):
        """Cargar todos los datos del sistema"""
        try:
            # Cargar datos principales
            if Path(self.data_file).exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_fingerprints = data.get('user_fingerprints', {})
                    self.suspicious_activities = data.get('suspicious_activities', {})
                    self.username_history = data.get('username_history', {})
                    self.cooldowns = data.get('cooldowns', {})
                    logger.info(f"✅ Datos anti-alt cargados: {len(self.user_fingerprints)} usuarios")

            # Cargar blacklist
            if Path(self.blacklist_file).exists():
                with open(self.blacklist_file, 'r', encoding='utf-8') as f:
                    blacklist_data = json.load(f)
                    self.blacklist = set(blacklist_data.get('blacklisted_users', []))
                    logger.info(f"✅ Blacklist cargada: {len(self.blacklist)} usuarios")

            # Cargar whitelist
            if Path(self.whitelist_file).exists():
                with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                    whitelist_data = json.load(f)
                    self.whitelist = set(whitelist_data.get('whitelisted_users', []))
                    logger.info(f"✅ Whitelist cargada: {len(self.whitelist)} usuarios")

        except Exception as e:
            logger.error(f"❌ Error cargando datos anti-alt: {e}")

    def save_data(self):
        """Guardar todos los datos del sistema"""
        try:
            # Guardar datos principales
            data = {
                'user_fingerprints': self.user_fingerprints,
                'suspicious_activities': self.suspicious_activities,
                'username_history': self.username_history,
                'cooldowns': self.cooldowns,
                'last_updated': datetime.now().isoformat(),
                'config': self.config
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Guardar blacklist
            blacklist_data = {
                'blacklisted_users': list(self.blacklist),
                'last_updated': datetime.now().isoformat(),
                'total_blacklisted': len(self.blacklist)
            }
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                json.dump(blacklist_data, f, indent=2)

            # Guardar whitelist
            whitelist_data = {
                'whitelisted_users': list(self.whitelist),
                'last_updated': datetime.now().isoformat(),
                'total_whitelisted': len(self.whitelist)
            }
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                json.dump(whitelist_data, f, indent=2)

            logger.info("💾 Datos anti-alt guardados exitosamente")

        except Exception as e:
            logger.error(f"❌ Error guardando datos anti-alt: {e}")

    def create_user_fingerprint(self, discord_id: str, discord_username: str, roblox_username: str, 
                               account_creation_date: Optional[datetime] = None) -> Dict:
        """Crear huella digital del usuario"""
        try:
            current_time = datetime.now()

            # Crear fingerprint básico
            fingerprint = {
                'discord_id': discord_id,
                'discord_username': discord_username,
                'roblox_username': roblox_username,
                'account_creation_date': account_creation_date.isoformat() if account_creation_date else None,
                'first_seen': current_time.isoformat(),
                'last_activity': current_time.isoformat(),
                'total_code_redemptions': 0,
                'failed_attempts': 0,
                'trust_score': 100,  # Puntuación de confianza inicial
                'risk_level': 'low',  # low, medium, high, banned
                'flags': []
            }

            # Verificar edad de cuenta
            if account_creation_date:
                account_age_hours = (current_time - account_creation_date).total_seconds() / 3600
                fingerprint['account_age_hours'] = account_age_hours

                if account_age_hours < self.config['min_account_age_hours']:
                    fingerprint['flags'].append('new_account')
                    fingerprint['trust_score'] -= 20
                    self.log_suspicious_activity(discord_id, 'new_account', 
                                               f"Cuenta muy nueva: {account_age_hours:.1f} horas")

            self.user_fingerprints[discord_id] = fingerprint
            return fingerprint

        except Exception as e:
            logger.error(f"❌ Error creando fingerprint para {discord_id}: {e}")
            return {}

    def check_username_similarity(self, discord_id: str, new_roblox_username: str) -> Tuple[bool, List[str]]:
        """Verificar similitud con nombres de usuario existentes"""
        try:
            new_username_clean = self.normalize_username(new_roblox_username)
            similar_users = []
            is_suspicious = False

            # Verificar contra todos los usuarios existentes
            for other_id, fingerprint in self.user_fingerprints.items():
                if other_id == discord_id:
                    continue

                other_username = fingerprint.get('roblox_username', '')
                other_username_clean = self.normalize_username(other_username)

                # Calcular similitud usando difflib
                similarity = difflib.SequenceMatcher(None, new_username_clean, other_username_clean).ratio()

                if similarity >= self.config['username_similarity_threshold']:
                    similar_users.append({
                        'discord_id': other_id,
                        'username': other_username,
                        'similarity': similarity
                    })
                    is_suspicious = True

                    logger.warning(f"⚠️ Usuario {discord_id} ({new_roblox_username}) similar a {other_id} ({other_username}): {similarity:.2%}")

            # Registrar actividad sospechosa si se encuentra similitud
            if is_suspicious:
                self.log_suspicious_activity(discord_id, 'similar_username', 
                                           f"Nombre similar a {len(similar_users)} usuario(s) existente(s)")

                # Reducir trust score
                if discord_id in self.user_fingerprints:
                    self.user_fingerprints[discord_id]['trust_score'] -= 30
                    self.user_fingerprints[discord_id]['flags'].append('similar_username')

            return is_suspicious, similar_users

        except Exception as e:
            logger.error(f"❌ Error verificando similitud de username: {e}")
            return False, []

    def normalize_username(self, username: str) -> str:
        """Normalizar username para comparación"""
        try:
            # Convertir a minúsculas
            normalized = username.lower()

            # Remover números comunes al final
            normalized = re.sub(r'\d+$', '', normalized)

            # Remover caracteres especiales comunes
            normalized = re.sub(r'[_\-\.]+', '', normalized)

            # Remover prefijos/sufijos comunes
            common_patterns = ['alt', 'alt2', 'new', 'backup', 'main', 'old']
            for pattern in common_patterns:
                normalized = normalized.replace(pattern, '')

            return normalized.strip()

        except Exception as e:
            logger.error(f"❌ Error normalizando username: {e}")
            return username.lower()

    def log_suspicious_activity(self, discord_id: str, activity_type: str, details: str):
        """Registrar actividad sospechosa"""
        try:
            if discord_id not in self.suspicious_activities:
                self.suspicious_activities[discord_id] = []

            activity = {
                'type': activity_type,
                'details': details,
                'timestamp': datetime.now().isoformat(),
                'severity': self.get_activity_severity(activity_type)
            }

            self.suspicious_activities[discord_id].append(activity)

            # Mantener solo los últimos 50 registros
            if len(self.suspicious_activities[discord_id]) > 50:
                self.suspicious_activities[discord_id] = self.suspicious_activities[discord_id][-50:]

            logger.warning(f"🚨 Actividad sospechosa registrada para {discord_id}: {activity_type} - {details}")

            # Verificar si debe ser baneado automáticamente
            self.check_auto_ban(discord_id)

        except Exception as e:
            logger.error(f"❌ Error registrando actividad sospechosa: {e}")

    def get_activity_severity(self, activity_type: str) -> int:
        """Obtener severidad de actividad (1-10)"""
        severity_map = {
            'new_account': 3,
            'similar_username': 5,
            'multiple_attempts': 4,
            'rapid_requests': 6,
            'blacklisted_pattern': 8,
            'verified_alt': 10,
            'suspicious_timing': 3,
            'duplicate_fingerprint': 7
        }
        return severity_map.get(activity_type, 5)

    def check_auto_ban(self, discord_id: str):
        """Verificar si el usuario debe ser baneado automáticamente"""
        try:
            if discord_id in self.whitelist:
                return False

            if discord_id not in self.suspicious_activities:
                return False

            # Calcular score total de actividades sospechosas recientes (últimas 24 horas)
            recent_cutoff = datetime.now() - timedelta(hours=24)
            recent_activities = []

            for activity in self.suspicious_activities[discord_id]:
                activity_time = datetime.fromisoformat(activity['timestamp'])
                if activity_time >= recent_cutoff:
                    recent_activities.append(activity)

            total_severity = sum(activity['severity'] for activity in recent_activities)

            # Ban automático si supera el threshold
            if total_severity >= self.config['suspicious_threshold'] * 5:  # 25 points
                self.add_to_blacklist(discord_id, f"Ban automático: {total_severity} puntos de actividad sospechosa")
                logger.error(f"🚫 Usuario {discord_id} baneado automáticamente por actividad sospechosa")
                return True

            # Actualizar trust score
            if discord_id in self.user_fingerprints:
                self.user_fingerprints[discord_id]['trust_score'] = max(0, 100 - (total_severity * 2))

                # Actualizar risk level
                if total_severity >= 20:
                    self.user_fingerprints[discord_id]['risk_level'] = 'high'
                elif total_severity >= 10:
                    self.user_fingerprints[discord_id]['risk_level'] = 'medium'
                else:
                    self.user_fingerprints[discord_id]['risk_level'] = 'low'

            return False

        except Exception as e:
            logger.error(f"❌ Error en verificación de auto-ban: {e}")
            return False

    def calculate_dynamic_cooldown(self, discord_id: str, base_action: str = 'code_redeem') -> int:
        """Calcular cooldown dinámico basado en comportamiento del usuario"""
        try:
            base_cooldown = self.config['cooldown_base_minutes']

            # Usuario en whitelist: cooldown reducido
            if discord_id in self.whitelist:
                return max(5, base_cooldown // 2)

            # Usuario baneado: cooldown máximo
            if discord_id in self.blacklist:
                return self.config['max_cooldown_hours'] * 60

            # Obtener datos del usuario
            fingerprint = self.user_fingerprints.get(discord_id, {})
            trust_score = fingerprint.get('trust_score', 100)
            risk_level = fingerprint.get('risk_level', 'low')
            failed_attempts = fingerprint.get('failed_attempts', 0)

            # Calcular multiplicador basado en confianza
            trust_multiplier = 1.0
            if trust_score >= 80:
                trust_multiplier = 0.8  # Reducir cooldown para usuarios confiables
            elif trust_score >= 60:
                trust_multiplier = 1.0  # Normal
            elif trust_score >= 40:
                trust_multiplier = 1.5  # Aumentar cooldown
            else:
                trust_multiplier = 2.0  # Doble cooldown para usuarios no confiables

            # Multiplicador por nivel de riesgo
            risk_multipliers = {
                'low': 1.0,
                'medium': 1.5,
                'high': 2.5,
                'banned': 10.0
            }
            risk_multiplier = risk_multipliers.get(risk_level, 1.0)

            # Multiplicador por intentos fallidos
            failure_multiplier = 1.0 + (failed_attempts * 0.2)

            # Verificar actividades sospechosas recientes
            recent_suspicious = self.get_recent_suspicious_count(discord_id, hours=1)
            suspicious_multiplier = 1.0 + (recent_suspicious * 0.3)

            # Calcular cooldown final
            final_cooldown = base_cooldown * trust_multiplier * risk_multiplier * failure_multiplier * suspicious_multiplier

            # Aplicar límites
            final_cooldown = max(5, min(final_cooldown, self.config['max_cooldown_hours'] * 60))

            logger.info(f"🕐 Cooldown calculado para {discord_id}: {int(final_cooldown)} minutos "
                       f"(trust: {trust_score}, risk: {risk_level}, failures: {failed_attempts})")

            return int(final_cooldown)

        except Exception as e:
            logger.error(f"❌ Error calculando cooldown dinámico: {e}")
            return self.config['cooldown_base_minutes']

    def get_recent_suspicious_count(self, discord_id: str, hours: int = 24) -> int:
        """Obtener cantidad de actividades sospechosas recientes"""
        try:
            if discord_id not in self.suspicious_activities:
                return 0

            cutoff_time = datetime.now() - timedelta(hours=hours)
            count = 0

            for activity in self.suspicious_activities[discord_id]:
                activity_time = datetime.fromisoformat(activity['timestamp'])
                if activity_time >= cutoff_time:
                    count += 1

            return count

        except Exception as e:
            logger.error(f"❌ Error obteniendo actividades sospechosas recientes: {e}")
            return 0

    def set_cooldown(self, discord_id: str, action: str, custom_minutes: Optional[int] = None):
        """Establecer cooldown para usuario"""
        try:
            cooldown_minutes = custom_minutes or self.calculate_dynamic_cooldown(discord_id, action)
            expires_at = datetime.now() + timedelta(minutes=cooldown_minutes)

            if discord_id not in self.cooldowns:
                self.cooldowns[discord_id] = {}

            self.cooldowns[discord_id][action] = {
                'expires_at': expires_at.isoformat(),
                'duration_minutes': cooldown_minutes,
                'set_at': datetime.now().isoformat()
            }

            logger.info(f"⏳ Cooldown establecido para {discord_id} ({action}): {cooldown_minutes} minutos")

        except Exception as e:
            logger.error(f"❌ Error estableciendo cooldown: {e}")

    def check_cooldown(self, discord_id: str, action: str) -> Tuple[bool, int]:
        """Verificar si el usuario está en cooldown"""
        try:
            # Usuarios en whitelist no tienen cooldown
            if discord_id in self.whitelist:
                return False, 0

            if discord_id not in self.cooldowns or action not in self.cooldowns[discord_id]:
                return False, 0

            cooldown_data = self.cooldowns[discord_id][action]
            expires_at = datetime.fromisoformat(cooldown_data['expires_at'])
            current_time = datetime.now()

            if current_time >= expires_at:
                # Cooldown expirado, remover
                del self.cooldowns[discord_id][action]
                if not self.cooldowns[discord_id]:
                    del self.cooldowns[discord_id]
                return False, 0

            remaining_seconds = int((expires_at - current_time).total_seconds())
            return True, remaining_seconds

        except Exception as e:
            logger.error(f"❌ Error verificando cooldown: {e}")
            return False, 0

    def add_to_blacklist(self, discord_id: str, reason: str):
        """Agregar usuario a blacklist"""
        try:
            self.blacklist.add(discord_id)

            # Actualizar fingerprint
            if discord_id in self.user_fingerprints:
                self.user_fingerprints[discord_id]['risk_level'] = 'banned'
                self.user_fingerprints[discord_id]['trust_score'] = 0
                self.user_fingerprints[discord_id]['flags'].append('blacklisted')

            # Registrar actividad
            self.log_suspicious_activity(discord_id, 'blacklisted', reason)

            self.save_data()
            logger.error(f"🚫 Usuario {discord_id} agregado a blacklist: {reason}")

        except Exception as e:
            logger.error(f"❌ Error agregando a blacklist: {e}")

    def create_ban_embed(self, reason: str, additional_info: str = None) -> tuple:
        """Crear embed de ban con imagen"""
        try:
            import discord
            
            embed = discord.Embed(
                title="🚫 Usuario Baneado",
                description=f"Has sido baneado del sistema.\n\n**Razón:** {reason}",
                color=0xff0000
            )
            
            if additional_info:
                embed.add_field(
                    name="💡 Información Adicional",
                    value=additional_info,
                    inline=False
                )
            
            # Intentar cargar imagen de ban
            try:
                banned_file = discord.File("./attached_assets/banned.png", filename="banned.png")
                embed.set_thumbnail(url="attachment://banned.png")
                return embed, banned_file
            except:
                # Fallback sin imagen
                return embed, None
                
        except Exception as e:
            logger.error(f"❌ Error creando embed de ban: {e}")
            return None, None

    def add_to_whitelist(self, discord_id: str, reason: str):
        """Agregar usuario a whitelist"""
        try:
            self.whitelist.add(discord_id)

            # Actualizar fingerprint
            if discord_id in self.user_fingerprints:
                self.user_fingerprints[discord_id]['risk_level'] = 'low'
                self.user_fingerprints[discord_id]['trust_score'] = 100
                self.user_fingerprints[discord_id]['flags'] = [flag for flag in 
                                                             self.user_fingerprints[discord_id].get('flags', []) 
                                                             if flag != 'blacklisted']

            self.save_data()
            logger.info(f"✅ Usuario {discord_id} agregado a whitelist: {reason}")

        except Exception as e:
            logger.error(f"❌ Error agregando a whitelist: {e}")

    def remove_from_blacklist(self, discord_id: str) -> bool:
        """Remover usuario de blacklist"""
        try:
            if discord_id in self.blacklist:
                self.blacklist.remove(discord_id)

                # Actualizar fingerprint
                if discord_id in self.user_fingerprints:
                    self.user_fingerprints[discord_id]['risk_level'] = 'medium'
                    self.user_fingerprints[discord_id]['trust_score'] = 50
                    flags = self.user_fingerprints[discord_id].get('flags', [])
                    self.user_fingerprints[discord_id]['flags'] = [f for f in flags if f != 'blacklisted']

                self.save_data()
                logger.info(f"✅ Usuario {discord_id} removido de blacklist")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Error removiendo de blacklist: {e}")
            return False

    def remove_from_whitelist(self, discord_id: str) -> bool:
        """Remover usuario de whitelist"""
        try:
            if discord_id in self.whitelist:
                self.whitelist.remove(discord_id)
                self.save_data()
                logger.info(f"✅ Usuario {discord_id} removido de whitelist")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Error removiendo de whitelist: {e}")
            return False

    def is_blacklisted(self, discord_id: str) -> bool:
        """Verificar si usuario está en blacklist"""
        return discord_id in self.blacklist

    def is_whitelisted(self, discord_id: str) -> bool:
        """Verificar si usuario está en whitelist"""
        return discord_id in self.whitelist

    def validate_code_redemption(self, discord_id: str, code: str) -> Tuple[bool, str]:
        """Validar si el usuario puede canjear un código"""
        try:
            # Verificar blacklist
            if self.is_blacklisted(discord_id):
                return False, "Usuario en lista negra - no puede canjear códigos"

            # Verificar cooldown
            on_cooldown, remaining_seconds = self.check_cooldown(discord_id, 'code_redeem')
            if on_cooldown:
                remaining_minutes = remaining_seconds // 60
                return False, f"Cooldown activo - espera {remaining_minutes} minutos"

            # Verificar límites diarios (excepto whitelist)
            if not self.is_whitelisted(discord_id):
                daily_redemptions = self.get_daily_redemption_count(discord_id)
                if daily_redemptions >= self.config['max_codes_per_day']:
                    return False, f"Límite diario alcanzado ({self.config['max_codes_per_day']} códigos por día)"

            # Verificar edad mínima de cuenta
            fingerprint = self.user_fingerprints.get(discord_id, {})
            account_age_hours = fingerprint.get('account_age_hours', 999)
            if account_age_hours < self.config['min_account_age_hours']:
                return False, f"Cuenta muy nueva - espera {self.config['min_account_age_hours'] - account_age_hours:.1f} horas"

            # Verificar trust score
            trust_score = fingerprint.get('trust_score', 100)
            if trust_score < 30:
                return False, "Cuenta con actividad sospechosa - no puede canjear códigos"

            return True, "Validación exitosa"

        except Exception as e:
            logger.error(f"❌ Error validando canje de código: {e}")
            return False, "Error interno del sistema"

    def get_daily_redemption_count(self, discord_id: str) -> int:
        """Obtener cantidad de canjes del día"""
        try:
            fingerprint = self.user_fingerprints.get(discord_id, {})
            redeemed_codes = fingerprint.get('redeemed_codes', [])

            # Contar canjes del día actual
            today = datetime.now().date()
            daily_count = 0

            for code_entry in redeemed_codes:
                if isinstance(code_entry, dict):
                    try:
                        code_timestamp = datetime.fromisoformat(code_entry['timestamp'])
                        if code_timestamp.date() == today:
                            daily_count += 1
                    except:
                        continue

            return daily_count

        except Exception as e:
            logger.error(f"❌ Error obteniendo canjes diarios: {e}")
            return 0

    def record_successful_redemption(self, discord_id: str, code: str):
        """Registrar canje exitoso"""
        try:
            if discord_id in self.user_fingerprints:
                self.user_fingerprints[discord_id]['total_code_redemptions'] += 1
                self.user_fingerprints[discord_id]['last_activity'] = datetime.now().isoformat()

                # Mejorar trust score ligeramente por actividad legítima
                current_trust = self.user_fingerprints[discord_id].get('trust_score', 100)
                self.user_fingerprints[discord_id]['trust_score'] = min(100, current_trust + 1)

                # Registrar el código específico canjeado
                if 'redeemed_codes' not in self.user_fingerprints[discord_id]:
                    self.user_fingerprints[discord_id]['redeemed_codes'] = []

                self.user_fingerprints[discord_id]['redeemed_codes'].append({
                    'code': code,
                    'timestamp': datetime.now().isoformat()
                })
            # Establecer cooldown dinámico
            self.set_cooldown(discord_id, 'code_redeem')

            self.save_data()
            logger.info(f"✅ Canje exitoso registrado para {discord_id}: {code}")

        except Exception as e:
            logger.error(f"❌ Error registrando canje exitoso: {e}")

    def record_failed_attempt(self, discord_id: str, reason: str):
        """Registrar intento fallido"""
        try:
            if discord_id in self.user_fingerprints:
                self.user_fingerprints[discord_id]['failed_attempts'] += 1
                self.user_fingerprints[discord_id]['last_activity'] = datetime.now().isoformat()

                # Reducir trust score
                current_trust = self.user_fingerprints[discord_id].get('trust_score', 100)
                self.user_fingerprints[discord_id]['trust_score'] = max(0, current_trust - 5)

            # Registrar como actividad sospechosa si hay muchos fallos
            failed_attempts = self.user_fingerprints[discord_id].get('failed_attempts', 0)
            if failed_attempts >= 3:
                self.log_suspicious_activity(discord_id, 'multiple_attempts', 
                                           f"Múltiples intentos fallidos: {failed_attempts}")

            self.save_data()
            logger.warning(f"⚠️ Intento fallido registrado para {discord_id}: {reason}")

        except Exception as e:
            logger.error(f"❌ Error registrando intento fallido: {e}")

    def get_user_stats(self, discord_id: str) -> dict:
        """Obtener estadísticas completas de un usuario"""
        if discord_id not in self.user_fingerprints:
            return None

        fingerprint = self.user_fingerprints[discord_id]

        # Verificar si está en cooldown
        on_cooldown = False
        cooldown_remaining = 0
        if discord_id in self.cooldowns:
            cooldown_data = self.cooldowns[discord_id].get('code_redeem')
            if cooldown_data:
                expires_at = datetime.fromisoformat(cooldown_data['expires_at'])
                if datetime.now() < expires_at:
                    on_cooldown = True
                    cooldown_remaining = int((expires_at - datetime.now()).total_seconds())

        # Contar actividades sospechosas
        suspicious_count = len(self.suspicious_activities.get(discord_id, []))

        # Procesar códigos canjeados con más detalle
        redeemed_codes = fingerprint.get('redeemed_codes', [])
        code_names = []
        if redeemed_codes:
            for code_entry in redeemed_codes:
                if isinstance(code_entry, dict):
                    code_names.append(code_entry.get('code', 'Unknown'))
                else:
                    code_names.append(str(code_entry))

        stats = {
            'discord_id': discord_id,
            'discord_username': fingerprint.get('discord_username', 'Unknown'),
            'trust_score': fingerprint.get('trust_score', 100),
            'risk_level': fingerprint.get('risk_level', 'low'),
            'total_redemptions': fingerprint.get('total_code_redemptions', 0),
            'failed_attempts': fingerprint.get('failed_attempts', 0),
            'suspicious_activities_count': suspicious_count,
            'is_blacklisted': self.is_blacklisted(discord_id),
            'is_whitelisted': self.is_whitelisted(discord_id),
            'on_cooldown': on_cooldown,
            'cooldown_remaining_seconds': cooldown_remaining,
            'account_age_hours': fingerprint.get('account_age_hours'),
            'account_age_days': fingerprint.get('account_age_days'),
            'account_created_at': fingerprint.get('account_creation_date'),
            'roblox_username': fingerprint.get('roblox_username'),
            'flags': fingerprint.get('flags', []),
            'first_seen': fingerprint.get('first_seen'),
            'last_activity': fingerprint.get('last_activity'),
            'redeemed_codes': code_names,
            'redeemed_codes_details': redeemed_codes,
            'suspicious_activities': self.suspicious_activities.get(discord_id, [])
        }

        return stats

    def get_system_stats(self) -> Dict:
        """Obtener estadísticas del sistema"""
        try:
            total_users = len(self.user_fingerprints)
            blacklisted_count = len(self.blacklist)
            whitelisted_count = len(self.whitelist)

            # Contar por nivel de riesgo
            risk_counts = {'low': 0, 'medium': 0, 'high': 0, 'banned': 0}
            trust_scores = []

            for fingerprint in self.user_fingerprints.values():
                risk_level = fingerprint.get('risk_level', 'low')
                risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
                trust_scores.append(fingerprint.get('trust_score', 100))

            # Calcular estadísticas de confianza
            avg_trust = statistics.mean(trust_scores) if trust_scores else 100
            median_trust = statistics.median(trust_scores) if trust_scores else 100

            # Contar actividades sospechosas recientes (últimas 24 horas)
            recent_suspicious = 0
            for activities in self.suspicious_activities.values():
                for activity in activities:
                    activity_time = datetime.fromisoformat(activity['timestamp'])
                    if datetime.now() - activity_time <= timedelta(hours=24):
                        recent_suspicious += 1

            stats = {
                'total_users': total_users,
                'blacklisted_users': blacklisted_count,
                'whitelisted_users': whitelisted_count,
                'risk_distribution': risk_counts,
                'average_trust_score': round(avg_trust, 2),
                'median_trust_score': round(median_trust, 2),
                'recent_suspicious_activities': recent_suspicious,
                'cooldowns_active': len(self.cooldowns),
                'system_config': self.config,
                'last_updated': datetime.now().isoformat()
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Error obteniendo estadísticas del sistema: {e}")
            return {}

    def cleanup_old_data(self, days: int = 30):
        """Limpiar datos antiguos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0

            # Limpiar datos sospechosas antiguas
            for discord_id in list(self.suspicious_activities.keys()):
                activities = self.suspicious_activities[discord_id]
                filtered_activities = []

                for activity in activities:
                    activity_time = datetime.fromisoformat(activity['timestamp'])
                    if activity_time >= cutoff_date:
                        filtered_activities.append(activity)
                    else:
                        cleaned_count += 1

                if filtered_activities:
                    self.suspicious_activities[discord_id] = filtered_activities
                else:
                    del self.suspicious_activities[discord_id]

            # Limpiar cooldowns expirados
            for discord_id in list(self.cooldowns.keys()):
                user_cooldowns = self.cooldowns[discord_id]
                active_cooldowns = {}

                for action, cooldown_data in user_cooldowns.items():
                    expires_at = datetime.fromisoformat(cooldown_data['expires_at'])
                    if expires_at > datetime.now():
                        active_cooldowns[action] = cooldown_data

                if active_cooldowns:
                    self.cooldowns[discord_id] = active_cooldowns
                else:
                    del self.cooldowns[discord_id]

            self.save_data()
            logger.info(f"🧹 Limpieza completada: {cleaned_count} registros antiguos eliminados")

        except Exception as e:
            logger.error(f"❌ Error en limpieza de datos: {e}")

    def update_account_info(self, discord_id: str, discord_user=None):
        """Actualizar información de la cuenta del usuario"""
        try:
            # Obtener username de Roblox desde el sistema de verificación
            roblox_username = None
            try:
                from main import roblox_verification
                if roblox_verification and roblox_verification.is_user_verified(discord_id):
                    verification_data = roblox_verification.verified_users.get(discord_id)
                    if verification_data:
                        roblox_username = verification_data.get('roblox_username', 'Unknown')
            except Exception as e:
                logger.warning(f"No se pudo obtener username de Roblox para {discord_id}: {e}")

            if discord_id not in self.user_fingerprints:
                # Crear fingerprint básico si no existe
                current_time = datetime.now()

                fingerprint = {
                    'discord_id': discord_id,
                    'discord_username': discord_user.name if discord_user else f"user_{discord_id}",
                    'roblox_username': roblox_username,
                    'account_creation_date': None,
                    'first_seen': current_time.isoformat(),
                    'last_activity': current_time.isoformat(),
                    'total_code_redemptions': 0,
                    'failed_attempts': 0,
                    'trust_score': 100,
                    'risk_level': 'low',
                    'flags': [],
                    'redeemed_codes': []
                }

                # Calcular edad de cuenta si tenemos la información
                if discord_user and discord_user.created_at:
                    # Convertir ambas fechas a UTC timezone-aware
                    current_time_utc = current_time.replace(tzinfo=discord_user.created_at.tzinfo)
                    account_age_seconds = (current_time_utc - discord_user.created_at).total_seconds()
                    account_age_hours = account_age_seconds / 3600
                    account_age_days = account_age_seconds / 86400

                    fingerprint['account_creation_date'] = discord_user.created_at.isoformat()
                    fingerprint['account_age_hours'] = account_age_hours
                    fingerprint['account_age_days'] = account_age_days

                    if account_age_hours < self.config['min_account_age_hours']:
                        fingerprint['flags'].append('new_account')
                        fingerprint['trust_score'] -= 20
                        self.log_suspicious_activity(discord_id, 'new_account', 
                                                   f"Cuenta muy nueva: {account_age_days:.1f} días")

                self.user_fingerprints[discord_id] = fingerprint
            else:
                # Actualizar información existente
                if discord_user:
                    self.user_fingerprints[discord_id]['discord_username'] = discord_user.name

                    # Actualizar username de Roblox si está disponible
                    if roblox_username:
                        self.user_fingerprints[discord_id]['roblox_username'] = roblox_username

                    # Actualizar fecha de creación si no existe
                    if not self.user_fingerprints[discord_id].get('account_creation_date') and discord_user.created_at:
                        current_time = datetime.now()
                        current_time_utc = current_time.replace(tzinfo=discord_user.created_at.tzinfo)
                        account_age_seconds = (current_time_utc - discord_user.created_at).total_seconds()
                        account_age_hours = account_age_seconds / 3600
                        account_age_days = account_age_seconds / 86400

                        self.user_fingerprints[discord_id]['account_creation_date'] = discord_user.created_at.isoformat()
                        self.user_fingerprints[discord_id]['account_age_hours'] = account_age_hours
                        self.user_fingerprints[discord_id]['account_age_days'] = account_age_days

            # Actualizar última actividad
            self.user_fingerprints[discord_id]['last_activity'] = datetime.now().isoformat()

            # Recalcular nivel de riesgo
            self.user_fingerprints[discord_id]['risk_level'] = self._calculate_risk_level(
                self.user_fingerprints[discord_id]
            )

            logger.info(f"✅ Información de cuenta actualizada para {discord_id} (Roblox: {roblox_username or 'No verificado'})")

        except Exception as e:
            logger.error(f"❌ Error actualizando información de cuenta: {e}")

    def _calculate_risk_level(self, fingerprint: Dict) -> str:
        """Calcular nivel de riesgo basado en el fingerprint"""
        try:
            trust_score = fingerprint.get('trust_score', 100)
            failed_attempts = fingerprint.get('failed_attempts', 0)
            flags = fingerprint.get('flags', [])

            if trust_score <= 20 or 'blacklisted' in flags:
                return 'banned'
            elif trust_score <= 40 or failed_attempts >= 5:
                return 'high'
            elif trust_score <= 70 or failed_attempts >= 2:
                return 'medium'
            else:
                return 'low'

        except Exception as e:
            logger.error(f"❌ Error calculando nivel de riesgo: {e}")
            return 'medium'

# Instancia global del sistema anti-alt
anti_alt_system = AntiAltSystem()