
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
                
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Comandos Disponibles:",
                    value="• `/clown on` - Activar reacciones\n• `/clown off` - Desactivar reacciones\n• `/clown toggle` - Alternar estado\n• `/clown status` - Ver este estado",
                    inline=False
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
                # Emoji personalizado animado clown
                clown_emoji = "<a:clown:1418508263984463932>"
                await message.add_reaction(clown_emoji)
                
                logger.debug(f"<a:clown:1418508263984463932> Reacción automática añadida al mensaje {message.id} en canal {channel_id}")
                
            except discord.NotFound:
                logger.warning(f"⚠️ Mensaje {message.id} no encontrado para reaccionar")
            except discord.Forbidden:
                logger.warning(f"⚠️ Sin permisos para reaccionar al mensaje {message.id} en canal {channel_id}")
                # Desactivar automáticamente el canal si no hay permisos
                clown_manager.deactivate_channel(channel_id)
                logger.info(f"⏹️ Canal {channel_id} desactivado automáticamente por falta de permisos")
            except discord.HTTPException as e:
                if "Unknown Emoji" in str(e):
                    logger.error(f"❌ Emoji clown no disponible en servidor del canal {channel_id}")
                    # Desactivar el canal si el emoji no está disponible
                    clown_manager.deactivate_channel(channel_id)
                    logger.info(f"⏹️ Canal {channel_id} desactivado automáticamente por emoji no disponible")
                else:
                    logger.error(f"❌ Error HTTP reaccionando en canal {channel_id}: {e}")
            except Exception as reaction_error:
                logger.error(f"❌ Error inesperado reaccionando en canal {channel_id}: {reaction_error}")

        except Exception as e:
            logger.error(f"❌ Error crítico en evento on_message para reacciones clown: {e}")

    logger.info("<a:clown:1418508263984463932> Sistema de reacciones automáticas clown configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
