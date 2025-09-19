"""
Comando /clown - Owner only
Permite activar/desactivar reacciones automáticas con emoji clown en un canal
"""
import discord
from discord.ext import commands
import logging
import json
from datetime import datetime
from pathlib import Path
import asyncio # Import asyncio

logger = logging.getLogger(__name__)

# Sistema de gestión de canales con reacciones automáticas
class ClownReactionManager:
    def __init__(self):
        self.config_file = "clown_reactions_config.json"
        self.active_channels = set()
        self.load_config()

    def load_config(self):
        """Cargar configuración de canales activos"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_channels = set(data.get('active_channels', []))
                logger.info(f"✅ Configuración de reacciones clown cargada: {len(self.active_channels)} canales activos")
            else:
                self.active_channels = set()
                logger.info("📁 Archivo de configuración de reacciones clown creado")
        except Exception as e:
            logger.error(f"❌ Error cargando configuración de reacciones clown: {e}")
            self.active_channels = set()

    def save_config(self):
        """Guardar configuración de canales activos"""
        try:
            data = {
                'active_channels': list(self.active_channels),
                'last_updated': datetime.now().isoformat(),
                'total_active_channels': len(self.active_channels)
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("💾 Configuración de reacciones clown guardada exitosamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando configuración de reacciones clown: {e}")
            return False

    def activate_channel(self, channel_id: str) -> bool:
        """Activar reacciones automáticas en un canal"""
        self.active_channels.add(channel_id)
        return self.save_config()

    def deactivate_channel(self, channel_id: str) -> bool:
        """Desactivar reacciones automáticas en un canal"""
        self.active_channels.discard(channel_id)
        return self.save_config()

    def is_channel_active(self, channel_id: str) -> bool:
        """Verificar si un canal tiene reacciones automáticas activas"""
        return channel_id in self.active_channels

    def get_active_channels_count(self) -> int:
        """Obtener número de canales activos"""
        return len(self.active_channels)

# Instancia global del gestor
clown_manager = ClownReactionManager()

def setup_commands(bot):
    """Configurar comando /clown y evento de reacciones automáticas"""

    @bot.tree.command(name="clown", description="[OWNER ONLY] Activar/desactivar reacciones automáticas con emoji clown en este canal")
    async def clown_command(interaction: discord.Interaction, accion: str = "toggle"):
        """
        Comando para gestionar reacciones automáticas con emoji clown

        Args:
            accion: 'on' para activar, 'off' para desactivar, 'toggle' para alternar, 'status' para ver estado
        """
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        channel_id = str(interaction.channel.id)

        # Verificar que solo el owner pueda usar este comando
        from main import DISCORD_OWNER_ID, delegated_owners
        if user_id != DISCORD_OWNER_ID and user_id not in delegated_owners:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Verificar que el bot tenga permisos para reaccionar
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if not permissions.add_reactions or not permissions.read_message_history:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Permisos Insuficientes",
                    description="El bot necesita permisos de **Añadir Reacciones** y **Leer Historial de Mensajes** en este canal.",
                    color=0xff0000
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Permisos Requeridos:",
                    value="• Añadir Reacciones\n• Leer Historial de Mensajes\n• Ver Canal",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            current_status = clown_manager.is_channel_active(channel_id)

            # Procesar acción
            if accion.lower() == "on":
                if current_status:
                    embed = discord.Embed(
                        title="<a:clown:1418508263984463932> Ya Activado",
                        description="Las reacciones automáticas con emoji clown ya están **activadas** en este canal.",
                        color=0xffaa00
                    )
                else:
                    success = clown_manager.activate_channel(channel_id)
                    if success:
                        embed = discord.Embed(
                            title="<a:clown:1418508263984463932> Reacciones Activadas",
                            description="¡Las reacciones automáticas con emoji clown han sido **activadas** en este canal!",
                            color=0x00ff88
                        )
                        embed.add_field(
                            name="<:1000182584:1396049547838492672> ¿Qué pasará ahora?",
                            value="• El bot reaccionará automáticamente a **todos** los mensajes nuevos en este canal\n• Se usará el emoji <a:clown:1418508263984463932>\n• Solo afecta a mensajes enviados después de la activación",
                            inline=False
                        )
                    else:
                        embed = discord.Embed(
                            title="❌ Error de Activación",
                            description="No se pudo activar las reacciones automáticas.",
                            color=0xff0000
                        )

            elif accion.lower() == "off":
                if not current_status:
                    embed = discord.Embed(
                        title="⏹️ Ya Desactivado",
                        description="Las reacciones automáticas con emoji clown ya están **desactivadas** en este canal.",
                        color=0x6c757d
                    )
                else:
                    success = clown_manager.deactivate_channel(channel_id)
                    if success:
                        embed = discord.Embed(
                            title="⏹️ Reacciones Desactivadas",
                            description="Las reacciones automáticas con emoji clown han sido **desactivadas** en este canal.",
                            color=0xff9900
                        )
                        embed.add_field(
                            name="<:1000182584:1396049547838492672> Estado:",
                            value="• El bot ya no reaccionará automáticamente a mensajes nuevos\n• Las reacciones existentes no se eliminan\n• Puedes reactivar usando `/clown on`",
                            inline=False
                        )
                    else:
                        embed = discord.Embed(
                            title="❌ Error de Desactivación",
                            description="No se pudo desactivar las reacciones automáticas.",
                            color=0xff0000
                        )

            elif accion.lower() == "toggle":
                if current_status:
                    # Desactivar
                    success = clown_manager.deactivate_channel(channel_id)
                    if success:
                        embed = discord.Embed(
                            title="⏹️ Reacciones Desactivadas",
                            description="Las reacciones automáticas con emoji clown han sido **desactivadas** en este canal.",
                            color=0xff9900
                        )
                    else:
                        embed = discord.Embed(
                            title="❌ Error",
                            description="No se pudo cambiar el estado de las reacciones.",
                            color=0xff0000
                        )
                else:
                    # Activar
                    success = clown_manager.activate_channel(channel_id)
                    if success:
                        embed = discord.Embed(
                            title="<a:clown:1418508263984463932> Reacciones Activadas",
                            description="¡Las reacciones automáticas con emoji clown han sido **activadas** en este canal!",
                            color=0x00ff88
                        )
                        embed.add_field(
                            name="<:1000182584:1396049547838492672> ¿Qué pasará ahora?",
                            value="• El bot reaccionará automáticamente a **todos** los mensajes nuevos\n• Se usará el emoji <a:clown:1418508263984463932>\n• Solo afecta a mensajes enviados después de la activación",
                            inline=False
                        )
                    else:
                        embed = discord.Embed(
                            title="❌ Error",
                            description="No se pudo cambiar el estado de las reacciones.",
                            color=0xff0000
                        )

            elif accion.lower() == "status":
                # Mostrar estado actual
                status_text = "<a:clown:1418508263984463932> **Activado**" if current_status else "⏹️ **Desactivado**"
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Estado de Reacciones Clown",
                    description=f"Estado actual en este canal: {status_text}",
                    color=0x00ff88 if current_status else 0x6c757d
                )

                embed.add_field(
                    name="<:1000182750:1396420537227411587> Canal Actual:",
                    value=f"{interaction.channel.mention}\n`{interaction.channel.name}`",
                    inline=True
                )

                embed.add_field(
                    name="<:stats:1418490788437823599> Canales Activos Globalmente:",
                    value=f"`{clown_manager.get_active_channels_count()}`",
                    inline=True
                )

                # Verificar permisos en el canal actual
                permissions = interaction.channel.permissions_for(interaction.guild.me)
                perms_status = "✅ Completos" if (permissions.add_reactions and permissions.read_message_history) else "❌ Insuficientes"

                embed.add_field(
                    name="🔐 Permisos del Bot:",
                    value=perms_status,
                    inline=True
                )

                # Verificar disponibilidad del emoji del bot
                emoji_available = False
                try:
                    clown_emoji_check = bot.get_emoji(1418508263984463932)
                    emoji_available = clown_emoji_check is not None
                except:
                    emoji_available = False

                emoji_status = "✅ Disponible en el bot" if emoji_available else "✅ Usando formato directo"

                embed.add_field(
                    name="<a:clown:1418508263984463932> Emoji Clown:",
                    value=emoji_status,
                    inline=True
                )

                # Detalles de permisos
                perm_details = []
                if permissions.add_reactions:
                    perm_details.append("✅ Añadir Reacciones")
                else:
                    perm_details.append("❌ Añadir Reacciones")

                if permissions.read_message_history:
                    perm_details.append("✅ Leer Historial")
                else:
                    perm_details.append("❌ Leer Historial")

                if permissions.view_channel:
                    perm_details.append("✅ Ver Canal")
                else:
                    perm_details.append("❌ Ver Canal")

                embed.add_field(
                    name="🔍 Detalles de Permisos:",
                    value="\n".join(perm_details),
                    inline=True
                )

                embed.add_field(
                    name="<:1000182751:1396420751798558781> Comandos Disponibles:",
                    value="• `/clown on` - Activar reacciones\n• `/clown off` - Desactivar reacciones\n• `/clown toggle` - Alternar estado\n• `/clown status` - Ver este estado\n• `/clown test` - Probar reacción",
                    inline=False
                )

            elif accion.lower() == "test":
                if not current_status:
                    embed = discord.Embed(
                        title="⚠️ Canal Inactivo",
                        description="Este canal no tiene reacciones automáticas activadas. Usa `/clown on` primero.",
                        color=0xff9900
                    )
                else:
                    # Test de reacción inmediata
                    try:
                        # Verificar emoji del bot
                        clown_emoji = None
                        try:
                            clown_emoji = bot.get_emoji(1418508263984463932)
                            if not clown_emoji:
                                # Fallback: usar formato directo
                                clown_emoji = f"<a:clown:1418508263984463932>"
                        except:
                            clown_emoji = f"<a:clown:1418508263984463932>"

                        if not clown_emoji:
                            embed = discord.Embed(
                                title="❌ Emoji No Encontrado",
                                description="El emoji clown personalizado no se pudo obtener del bot. No se puede realizar la prueba.",
                                color=0xff0000
                            )
                        else:
                            # Enviar mensaje de prueba
                            test_message = await interaction.channel.send("🧪 **Mensaje de prueba para reacciones automáticas**")

                            # Esperar un momento para la reacción automática
                            await asyncio.sleep(2)

                            # Verificar si la reacción se añadió
                            fresh_message = await interaction.channel.fetch_message(test_message.id)
                            reaction_found = False

                            for reaction in fresh_message.reactions:
                                if str(reaction.emoji) == str(clown_emoji):
                                    async for user in reaction.users():
                                        if user.id == interaction.guild.me.id:
                                            reaction_found = True
                                            break
                                    break

                            if reaction_found:
                                embed = discord.Embed(
                                    title="✅ Test Exitoso",
                                    description="Las reacciones automáticas funcionan correctamente.",
                                    color=0x00ff88
                                )
                                embed.add_field(
                                    name="<a:clown:1418508263984463932> Resultado:",
                                    value=f"Reacción añadida con emoji: {clown_emoji}",
                                    inline=False
                                )
                            else:
                                embed = discord.Embed(
                                    title="❌ Test Fallido",
                                    description="La reacción automática no funcionó o se eliminó.",
                                    color=0xff0000
                                )
                                embed.add_field(
                                    name="🔍 Posibles causas:",
                                    value="• Rate limiting de Discord\n• Permisos insuficientes\n• Conflicto con otros bots\n• Emoji no disponible",
                                    inline=False
                                )

                            # Limpiar mensaje de prueba
                            try:
                                await test_message.delete()
                            except:
                                pass

                    except discord.Forbidden as e:
                         embed = discord.Embed(
                            title="❌ Permisos Insuficientes para Test",
                            description=f"El bot no tiene permisos para enviar mensajes o reaccionar en este canal. Error: {e}",
                            color=0xff0000
                        )
                    except discord.HTTPException as e:
                        embed = discord.Embed(
                            title="❌ Error HTTP durante el Test",
                            description=f"Ocurrió un error de Discord al intentar la prueba: {str(e)[:200]}",
                            color=0xff0000
                        )
                    except Exception as test_error:
                        embed = discord.Embed(
                            title="❌ Error en Test",
                            description=f"Error durante la prueba: {str(test_error)[:200]}",
                            color=0xff0000
                        )


            else:
                embed = discord.Embed(
                    title="❌ Acción Inválida",
                    description="Acción no reconocida. Usa: `on`, `off`, `toggle`, o `status`",
                    color=0xff0000
                )

            # Agregar información del canal y usuario
            embed.add_field(
                name="<:1000182750:1396420537227411587> Canal:",
                value=f"{interaction.channel.mention}",
                inline=True
            )

            embed.add_field(
                name="<:1000182644:1396049313481625611> Ejecutado por:",
                value=f"{username}",
                inline=True
            )

            embed.add_field(
                name="<:1000182657:1396060091366637669> Hora:",
                value=f"<t:{int(datetime.now().timestamp())}:T>",
                inline=True
            )

            embed.set_footer(text="RbxServers • Sistema de Reacciones Automáticas")

            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Owner {username} ejecutó /clown {accion} en canal {channel_id}")

        except Exception as e:
            logger.error(f"Error en comando /clown: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al procesar el comando de reacciones clown.",
                color=0xff0000
            )
            embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}```", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)

    # Evento para reaccionar automáticamente a mensajes
    @bot.event
    async def on_message(message):
        """Evento para reaccionar automáticamente con emoji clown"""
        try:
            # Ignorar mensajes del bot
            if message.author.bot:
                return

            # Ignorar mensajes en DM
            if not message.guild:
                return

            channel_id = str(message.channel.id)

            # Verificar si el canal tiene reacciones automáticas activadas
            if not clown_manager.is_channel_active(channel_id):
                return

            # Verificar permisos del bot
            permissions = message.channel.permissions_for(message.guild.me)
            if not permissions.add_reactions:
                logger.warning(f"⚠️ Sin permisos para reaccionar en canal {channel_id}")
                return

            # Intentar reaccionar con el emoji clown
            try:
                # Emoji personalizado animado clown - usar directamente por ID
                clown_emoji = None
                
                # Obtener el emoji del bot directamente por ID (emojis internos del bot)
                try:
                    clown_emoji = bot.get_emoji(1418508263984463932)
                    if clown_emoji:
                        logger.debug(f"✅ Emoji clown obtenido del bot: {clown_emoji}")
                    else:
                        logger.debug(f"⚠️ Emoji clown no encontrado en emojis del bot, intentando crear manualmente")
                        # Crear emoji manualmente usando el ID
                        clown_emoji = f"<a:clown:1418508263984463932>"
                except Exception as e:
                    logger.debug(f"Error obteniendo emoji del bot: {e}")
                    # Fallback: usar formato de emoji directo
                    clown_emoji = f"<a:clown:1418508263984463932>"

                if not clown_emoji:
                    logger.warning(f"⚠️ No se pudo obtener emoji clown, saltando reacción")
                    return

                # Añadir reacción con emoji del bot
                reaction = await message.add_reaction(clown_emoji)

                # Verificar que la reacción se mantuvo después de un pequeño delay
                await asyncio.sleep(1)

                # Refrescar el mensaje para verificar reacciones
                try:
                    fresh_message = await message.channel.fetch_message(message.id)
                    bot_reaction_exists = False

                    for reaction in fresh_message.reactions:
                        if str(reaction.emoji) == str(clown_emoji):
                            async for user in reaction.users():
                                if user.id == message.guild.me.id:
                                    bot_reaction_exists = True
                                    break
                            break

                    if bot_reaction_exists:
                        logger.info(f"<a:clown:1418508263984463932> Reacción automática confirmada en mensaje {message.id} canal {channel_id}")
                    else:
                        logger.warning(f"⚠️ Reacción desapareció del mensaje {message.id} en canal {channel_id} - posible rate limit o conflicto")

                        # Intentar reaccionar de nuevo después de una pausa
                        await asyncio.sleep(2)
                        await message.add_reaction(clown_emoji)
                        logger.info(f"🔄 Reintento de reacción realizado en mensaje {message.id}")

                except discord.NotFound:
                    logger.warning(f"⚠️ No se pudo verificar reacción - mensaje {message.id} eliminado")

            except discord.NotFound:
                logger.warning(f"⚠️ Mensaje {message.id} no encontrado para reaccionar")
            except discord.Forbidden as e:
                logger.warning(f"⚠️ Sin permisos para reaccionar al mensaje {message.id} en canal {channel_id}: {e}")

                # Verificar permisos específicos
                perms = message.channel.permissions_for(message.guild.me)
                missing_perms = []
                if not perms.add_reactions:
                    missing_perms.append("Añadir Reacciones")
                if not perms.read_message_history:
                    missing_perms.append("Leer Historial")
                if not perms.view_channel:
                    missing_perms.append("Ver Canal")

                logger.warning(f"⚠️ Permisos faltantes en canal {channel_id}: {', '.join(missing_perms)}")

                # Solo desactivar si faltan permisos críticos
                if not perms.add_reactions:
                    clown_manager.deactivate_channel(channel_id)
                    logger.info(f"⏹️ Canal {channel_id} desactivado automáticamente por falta de permisos de reacción")

            except discord.HTTPException as e:
                if "Unknown Emoji" in str(e):
                    logger.error(f"❌ Emoji clown no disponible en servidor del canal {channel_id}")
                    clown_manager.deactivate_channel(channel_id)
                    logger.info(f"⏹️ Canal {channel_id} desactivado por problemas con emojis")
                elif "reaction blocked" in str(e).lower():
                    logger.warning(f"⚠️ Reacción bloqueada por el servidor en canal {channel_id}")
                elif "rate limited" in str(e).lower():
                    logger.warning(f"⚠️ Rate limited al reaccionar en canal {channel_id} - pausando...")
                    await asyncio.sleep(5)
                else:
                    logger.error(f"❌ Error HTTP reaccionando en canal {channel_id}: {e}")
            except Exception as reaction_error:
                logger.error(f"❌ Error inesperado reaccionando en canal {channel_id}: {reaction_error}")
                import traceback
                logger.debug(f"❌ Traceback: {traceback.format_exc()}")

        except Exception as e:
            logger.error(f"❌ Error crítico en evento on_message para reacciones clown: {e}")

    logger.info("<a:clown:1418508263984463932> Sistema de reacciones automáticas clown configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass