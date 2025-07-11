import discord
from discord.ext import commands
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import random
import string

logger = logging.getLogger(__name__)

class CodesSystem:
    def __init__(self):
        self.codes_file = "promotional_codes.json"
        self.codes_usage_file = "codes_usage.json"
        self.codes = {}
        self.codes_usage = {}
        self.load_data()

    def load_data(self):
        """Cargar datos de códigos"""
        try:
            if Path(self.codes_file).exists():
                with open(self.codes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.codes = data.get('codes', {})
                    logger.info(f"✅ Cargados {len(self.codes)} códigos promocionales")
            else:
                self.codes = {}
                logger.info("⚠️ Archivo de códigos no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando códigos: {e}")
            self.codes = {}

        try:
            if Path(self.codes_usage_file).exists():
                with open(self.codes_usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.codes_usage = data.get('usage', {})
                    logger.info(f"✅ Cargados registros de uso de {len(self.codes_usage)} códigos")
            else:
                self.codes_usage = {}
                logger.info("⚠️ Archivo de uso de códigos no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando uso de códigos: {e}")
            self.codes_usage = {}

    def save_data(self):
        """Guardar datos de códigos"""
        try:
            codes_data = {
                'codes': self.codes,
                'total_codes': len(self.codes),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.codes_file, 'w', encoding='utf-8') as f:
                json.dump(codes_data, f, indent=2)
            logger.info(f"💾 Datos de códigos guardados ({len(self.codes)} códigos)")
        except Exception as e:
            logger.error(f"❌ Error guardando códigos: {e}")

        try:
            usage_data = {
                'usage': self.codes_usage,
                'total_usages': sum(len(users) for users in self.codes_usage.values()),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.codes_usage_file, 'w', encoding='utf-8') as f:
                json.dump(usage_data, f, indent=2)
            logger.info(f"💾 Datos de uso de códigos guardados")
        except Exception as e:
            logger.error(f"❌ Error guardando uso de códigos: {e}")

    def generate_random_code(self, length=8):
        """Generar código aleatorio"""
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=length))

    def create_code(self, creator_id: str, code: str = None, reward_type: str = "coins", 
                   reward_amount: int = 100, max_uses: int = 50, expires_hours: int = 168) -> str:
        """Crear un nuevo código promocional"""
        if not code:
            # Generar código único
            while True:
                code = self.generate_random_code()
                if code not in self.codes:
                    break

        # Verificar que el código no existe
        if code in self.codes:
            return None

        # Crear código
        code_data = {
            'code': code,
            'creator_id': creator_id,
            'reward_type': reward_type,
            'reward_amount': reward_amount,
            'max_uses': max_uses,
            'current_uses': 0,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=expires_hours)).isoformat(),
            'active': True
        }

        self.codes[code] = code_data
        self.codes_usage[code] = []
        self.save_data()

        logger.info(f"🎫 Código {code} creado por {creator_id} - {reward_amount} {reward_type}")
        return code

    def redeem_code(self, user_id: str, username: str, code: str) -> dict:
        """Canjear un código promocional con validación anti-alt"""
        code = code.upper().strip()

        # VALIDACIÓN ANTI-ALT PRIMERO
        try:
            from anti_alt_system import anti_alt_system
            
            # Validar con sistema anti-alt
            can_redeem, validation_message = anti_alt_system.validate_code_redemption(user_id, code)
            if not can_redeem:
                # Registrar intento fallido
                anti_alt_system.record_failed_attempt(user_id, validation_message)
                return {'success': False, 'message': f'🛡️ Anti-Alt: {validation_message}'}
        except Exception as e:
            logger.warning(f"Error en validación anti-alt: {e}")
            # Continuar sin validación anti-alt si hay error

        # Verificar que el código existe
        if code not in self.codes:
            try:
                from anti_alt_system import anti_alt_system
                anti_alt_system.record_failed_attempt(user_id, "Código inválido")
            except:
                pass
            return {'success': False, 'message': 'Código no válido o no existe'}

        code_data = self.codes[code]

        # Verificar que el código está activo
        if not code_data['active']:
            try:
                from anti_alt_system import anti_alt_system
                anti_alt_system.record_failed_attempt(user_id, "Código desactivado")
            except:
                pass
            return {'success': False, 'message': 'Este código ha sido desactivado'}

        # Verificar expiración
        expires_at = datetime.fromisoformat(code_data['expires_at'])
        if datetime.now() > expires_at:
            try:
                from anti_alt_system import anti_alt_system
                anti_alt_system.record_failed_attempt(user_id, "Código expirado")
            except:
                pass
            return {'success': False, 'message': 'Este código ha expirado'}

        # Verificar usos máximos
        if code_data['current_uses'] >= code_data['max_uses']:
            try:
                from anti_alt_system import anti_alt_system
                anti_alt_system.record_failed_attempt(user_id, "Código agotado")
            except:
                pass
            return {'success': False, 'message': 'Este código ha alcanzado el límite de usos'}

        # Verificar que el usuario no lo haya usado antes
        if any(usage['user_id'] == user_id for usage in self.codes_usage[code]):
            try:
                from anti_alt_system import anti_alt_system
                anti_alt_system.record_failed_attempt(user_id, "Código ya usado")
            except:
                pass
            return {'success': False, 'message': 'Ya has usado este código anteriormente'}

        # Registrar uso
        usage_record = {
            'user_id': user_id,
            'username': username,
            'redeemed_at': datetime.now().isoformat(),
            'reward_type': code_data['reward_type'],
            'reward_amount': code_data['reward_amount']
        }

        self.codes_usage[code].append(usage_record)
        self.codes[code]['current_uses'] += 1

        # Guardar cambios inmediatamente
        self.save_data()

        # REGISTRAR CANJE EXITOSO EN SISTEMA ANTI-ALT
        try:
            from anti_alt_system import anti_alt_system
            anti_alt_system.record_successful_redemption(user_id, code)
        except Exception as e:
            logger.warning(f"Error registrando canje exitoso en anti-alt: {e}")

        logger.info(f"✅ Usuario {username} ({user_id}) canjeó código {code}")

        return {
            'success': True,
            'message': f'¡Código canjeado exitosamente! Recibiste {code_data["reward_amount"]} {code_data["reward_type"]}',
            'reward_type': code_data['reward_type'],
            'reward_amount': code_data['reward_amount']
        }

    def get_code_info(self, code: str) -> dict:
        """Obtener información de un código"""
        code = code.upper().strip()
        if code not in self.codes:
            return None

        code_data = self.codes[code].copy()
        code_data['usage_list'] = self.codes_usage.get(code, [])
        return code_data

    def deactivate_code(self, code: str) -> bool:
        """Desactivar un código"""
        code = code.upper().strip()
        if code not in self.codes:
            return False

        self.codes[code]['active'] = False
        self.save_data()
        return True

    def get_user_codes(self, creator_id: str) -> list:
        """Obtener códigos creados por un usuario"""
        user_codes = []
        for code, data in self.codes.items():
            if data['creator_id'] == creator_id:
                code_info = data.copy()
                code_info['usage_count'] = len(self.codes_usage.get(code, []))
                user_codes.append(code_info)

        # Ordenar por fecha de creación (más recientes primero)
        user_codes.sort(key=lambda x: x['created_at'], reverse=True)
        return user_codes

    def cleanup_expired_codes(self):
        """Limpiar códigos expirados"""
        current_time = datetime.now()
        expired_codes = []

        for code, data in self.codes.items():
            expires_at = datetime.fromisoformat(data['expires_at'])
            if current_time > expires_at and data['active']:
                self.codes[code]['active'] = False
                expired_codes.append(code)

        if expired_codes:
            self.save_data()
            logger.info(f"🧹 {len(expired_codes)} códigos expirados desactivados")

        return len(expired_codes)

# Instancia global del sistema de códigos
codes_system = CodesSystem()

def setup_codes_commands(bot):
    """Configurar comandos de códigos"""

    @bot.tree.command(name="canjear", description="Canjear un código promocional")
    async def redeem_command(interaction: discord.Interaction, codigo: str):
        user_id = str(interaction.user.id)
        username = interaction.user.name

        # Verificar verificación
        from main import roblox_verification
        if not roblox_verification.is_user_verified(user_id):
            embed = discord.Embed(
                title="❌ Verificación Requerida",
                description="Debes estar verificado para canjear códigos promocionales.",
                color=0xff0000
            )
            embed.add_field(
                name="💡 ¿Cómo verificarse?",
                value="Usa el comando `/verify` para verificar tu cuenta de Roblox",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Limpiar códigos expirados
        codes_system.cleanup_expired_codes()

        # Intentar canjear código
        result = codes_system.redeem_code(user_id, username, codigo)

        if result['success']:
            # Dar recompensa al usuario
            if result['reward_type'] == 'coins':
                try:
                    from main import coins_system
                    if coins_system:
                        coins_system.add_coins(user_id, result['reward_amount'], f"Código canjeado: {codigo}")
                except Exception as e:
                    logger.error(f"Error agregando monedas por código: {e}")

            # Crear embed de éxito
            embed = discord.Embed(
                title="✅ Código Canjeado",
                description=f"¡Has canjeado exitosamente el código **{codigo}**!",
                color=0x00ff88
            )
            embed.add_field(
                name="🎁 Recompensa",
                value=f"{result['reward_amount']} {result['reward_type']}",
                inline=True
            )
            embed.add_field(
                name="🎫 Código",
                value=codigo.upper(),
                inline=True
            )
            embed.set_footer(text=f"Canjeado por {username}")

            await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            # Error al canjear
            embed = discord.Embed(
                title="❌ Error al Canjear",
                description=result['message'],
                color=0xff0000
            )
            embed.add_field(
                name="🎫 Código Intentado",
                value=codigo.upper(),
                inline=True
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="crear_codigo", description="[OWNER ONLY] Crear un nuevo código promocional")
    async def create_code_command(interaction: discord.Interaction, 
                                 codigo: str = None, 
                                 recompensa: int = 100,
                                 tipo: str = "coins",
                                 usos_maximos: int = 50,
                                 expira_en_horas: int = 168):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede crear códigos promocionales.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Validar parámetros
        if recompensa <= 0:
            embed = discord.Embed(
                title="❌ Recompensa Inválida",
                description="La recompensa debe ser mayor a 0.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if usos_maximos <= 0:
            embed = discord.Embed(
                title="❌ Usos Máximos Inválidos",
                description="Los usos máximos deben ser mayor a 0.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if expira_en_horas <= 0:
            embed = discord.Embed(
                title="❌ Expiración Inválida",
                description="Las horas de expiración deben ser mayor a 0.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Crear código
        created_code = codes_system.create_code(
            creator_id=user_id,
            code=codigo.upper() if codigo else None,
            reward_type=tipo,
            reward_amount=recompensa,
            max_uses=usos_maximos,
            expires_hours=expira_en_horas
        )

        if created_code:
            expires_date = datetime.now() + timedelta(hours=expira_en_horas)

            embed = discord.Embed(
                title="✅ Código Creado",
                description=f"El código promocional **{created_code}** ha sido creado exitosamente.",
                color=0x00ff88
            )
            embed.add_field(name="🎫 Código", value=f"`{created_code}`", inline=True)
            embed.add_field(name="🎁 Recompensa", value=f"{recompensa} {tipo}", inline=True)
            embed.add_field(name="👥 Usos Máximos", value=str(usos_maximos), inline=True)
            embed.add_field(name="⏰ Expira", value=expires_date.strftime("%Y-%m-%d %H:%M"), inline=True)
            embed.add_field(name="👑 Creador", value=interaction.user.mention, inline=True)
            embed.set_footer(text=f"Los usuarios pueden usar /canjear {created_code}")
        else:
            embed = discord.Embed(
                title="❌ Error al Crear Código",
                description="El código ya existe. Intenta con otro nombre.",
                color=0xff0000
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="ver_codigo", description="[OWNER ONLY] Ver información y uso de un código específico")
    async def view_code_command(interaction: discord.Interaction, codigo: str):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede ver información de códigos.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Obtener información del código
        code_info = codes_system.get_code_info(codigo)

        if not code_info:
            embed = discord.Embed(
                title="❌ Código No Encontrado",
                description=f"El código **{codigo.upper()}** no existe.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Información básica del código
        created_date = datetime.fromisoformat(code_info['created_at'])
        expires_date = datetime.fromisoformat(code_info['expires_at'])
        is_expired = datetime.now() > expires_date

        status = "🟢 Activo"
        if not code_info['active']:
            status = "🔴 Desactivado"
        elif is_expired:
            status = "🟡 Expirado"
        elif code_info['current_uses'] >= code_info['max_uses']:
            status = "🟠 Usos Agotados"

        embed = discord.Embed(
            title=f"🎫 Información del Código: {code_info['code']}",
            description=f"Detalles completos del código promocional",
            color=0x3366ff
        )

        embed.add_field(name="📊 Estado", value=status, inline=True)
        embed.add_field(name="🎁 Recompensa", value=f"{code_info['reward_amount']} {code_info['reward_type']}", inline=True)
        embed.add_field(name="👥 Usos", value=f"{code_info['current_uses']}/{code_info['max_uses']}", inline=True)

        embed.add_field(name="📅 Creado", value=created_date.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="⏰ Expira", value=expires_date.strftime("%Y-%m-%d %H:%M"), inline=True)
        embed.add_field(name="👑 Creador", value=f"<@{code_info['creator_id']}>", inline=True)

        # Lista de usuarios que usaron el código
        usage_list = code_info['usage_list']
        if usage_list:
            users_text = []
            for i, usage in enumerate(usage_list[:10]):  # Mostrar máximo 10
                used_date = datetime.fromisoformat(usage['redeemed_at'])
                users_text.append(f"{i+1}. **{usage['username']}** - {used_date.strftime('%Y-%m-%d %H:%M')}")

            embed.add_field(
                name=f"📋 Usuarios que Canjearon ({len(usage_list)} total)",
                value="\n".join(users_text) + (f"\n... y {len(usage_list) - 10} más" if len(usage_list) > 10 else ""),
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Usuarios que Canjearon",
                value="Ningún usuario ha canjeado este código aún.",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="mis_codigos", description="[OWNER ONLY] Ver todos los códigos que has creado")
    async def my_codes_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede ver los códigos creados.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Limpiar códigos expirados
        expired_count = codes_system.cleanup_expired_codes()

        # Obtener códigos del usuario
        user_codes = codes_system.get_user_codes(user_id)

        if not user_codes:
            embed = discord.Embed(
                title="📋 Mis Códigos",
                description="No has creado ningún código promocional aún.",
                color=0xffaa00
            )
            embed.add_field(
                name="💡 Crear Código",
                value="Usa `/crear_codigo` para crear tu primer código promocional",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Mis Códigos Promocionales",
            description=f"Has creado {len(user_codes)} código(s) promocional(es):",
            color=0x3366ff
        )

        active_codes = 0
        total_uses = 0

        for i, code_data in enumerate(user_codes[:10]):  # Mostrar máximo 10
            created_date = datetime.fromisoformat(code_data['created_at'])
            expires_date = datetime.fromisoformat(code_data['expires_at'])
            is_expired = datetime.now() > expires_date

            status = "🟢"
            if not code_data['active']:
                status = "🔴"
            elif is_expired:
                status = "🟡"
            elif code_data['current_uses'] >= code_data['max_uses']:
                status = "🟠"
            else:
                active_codes += 1

            total_uses += code_data['usage_count']

            embed.add_field(
                name=f"{status} {code_data['code']}",
                value=f"**Recompensa:** {code_data['reward_amount']} {code_data['reward_type']}\n**Usos:** {code_data['current_uses']}/{code_data['max_uses']}\n**Creado:** {created_date.strftime('%m/%d %H:%M')}",
                inline=True
            )

        # Estadísticas
        embed.add_field(
            name="📊 Estadísticas",
            value=f"• **Códigos Activos:** {active_codes}\n• **Total de Usos:** {total_uses}\n• **Códigos Expirados:** {expired_count} limpiados",
            inline=False
        )

        if len(user_codes) > 10:
            embed.set_footer(text=f"Mostrando 10 de {len(user_codes)} códigos. Usa /ver_codigo para ver detalles específicos.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="desactivar_codigo", description="[OWNER ONLY] Desactivar un código promocional")
    async def deactivate_code_command(interaction: discord.Interaction, codigo: str):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede desactivar códigos.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Verificar que el código existe
        code_info = codes_system.get_code_info(codigo)
        if not code_info:
            embed = discord.Embed(
                title="❌ Código No Encontrado",
                description=f"El código **{codigo.upper()}** no existe.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Verificar que el código le pertenece al usuario
        if code_info['creator_id'] != user_id:
            embed = discord.Embed(
                title="❌ Sin Permisos",
                description="Solo puedes desactivar códigos que tú creaste.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Desactivar código
        if codes_system.deactivate_code(codigo):
            embed = discord.Embed(
                title="✅ Código Desactivado",
                description=f"El código **{codigo.upper()}** ha sido desactivado exitosamente.",
                color=0x00ff88
            )
            embed.add_field(
                name="📊 Estadísticas Finales",
                value=f"• **Usos:** {code_info['current_uses']}/{code_info['max_uses']}\n• **Usuarios únicos:** {len(code_info['usage_list'])}",
                inline=True
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="No se pudo desactivar el código.",
                color=0xff0000
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="estadisticas_codigos", description="[OWNER ONLY] Ver estadísticas generales del sistema de códigos")
    async def codes_stats_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede ver estadísticas de códigos.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Limpiar códigos expirados
        expired_cleaned = codes_system.cleanup_expired_codes()

        # Calcular estadísticas
        total_codes = len(codes_system.codes)
        active_codes = 0
        expired_codes = 0
        exhausted_codes = 0
        total_uses = 0
        total_users = set()

        for code_data in codes_system.codes.values():
            expires_date = datetime.fromisoformat(code_data['expires_at'])
            is_expired = datetime.now() > expires_date

            if not code_data['active']:
                pass  # Desactivado manualmente
            elif is_expired:
                expired_codes += 1
            elif code_data['current_uses'] >= code_data['max_uses']:
                exhausted_codes += 1
            else:
                active_codes += 1

            total_uses += code_data['current_uses']

        # Contar usuarios únicos
        for usage_list in codes_system.codes_usage.values():
            for usage in usage_list:
                total_users.add(usage['user_id'])

        embed = discord.Embed(
            title="📊 Estadísticas del Sistema de Códigos",
            description="Resumen completo del sistema de códigos promocionales:",
            color=0x3366ff
        )

        embed.add_field(
            name="🎫 Códigos Totales",
            value=str(total_codes),
            inline=True
        )

        embed.add_field(
            name="🟢 Códigos Activos",
            value=str(active_codes),
            inline=True
        )

        embed.add_field(
            name="🟡 Códigos Expirados",
            value=str(expired_codes),
            inline=True
        )

        embed.add_field(
            name="🟠 Códigos Agotados",
            value=str(exhausted_codes),
            inline=True
        )

        embed.add_field(
            name="📈 Total de Usos",
            value=str(total_uses),
            inline=True
        )

        embed.add_field(
            name="👥 Usuarios Únicos",
            value=str(len(total_users)),
            inline=True
        )

        # Códigos más populares
        popular_codes = []
        for code, data in codes_system.codes.items():
            if data['current_uses'] > 0:
                popular_codes.append((code, data['current_uses'], data['reward_amount'], data['reward_type']))

        popular_codes.sort(key=lambda x: x[1], reverse=True)

        if popular_codes:
            popular_text = []
            for i, (code, uses, reward, reward_type) in enumerate(popular_codes[:5]):
                popular_text.append(f"{i+1}. **{code}** - {uses} usos ({reward} {reward_type})")

            embed.add_field(
                name="🏆 Códigos Más Populares",
                value="\n".join(popular_text),
                inline=False
            )

        if expired_cleaned > 0:
            embed.add_field(
                name="🧹 Limpieza Automática",
                value=f"{expired_cleaned} códigos expirados fueron desactivados",
                inline=False
            )

        embed.set_footer(text="Sistema de códigos promocionales - RbxServers Bot")

        await interaction.followup.send(embed=embed, ephemeral=True)

    logger.info("🎟️ Comandos de códigos configurados exitosamente")
    return codes_system