
"""
Sistema de logging de comandos para RbxServers
Registra todos los comandos usados y los envía a un canal configurado
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class CommandLogger:
    def __init__(self):
        self.config_file = "command_logging_config.json"
        self.load_config()
    
    def load_config(self):
        """Cargar configuración desde archivo JSON"""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info(f"✅ Configuración de logging cargada: {len(self.config.get('servers', {}))} servidores")
            else:
                self.config = {
                    'servers': {},
                    'metadata': {
                        'created_at': datetime.now().isoformat(),
                        'total_servers_configured': 0
                    }
                }
                logger.info("📁 Archivo de configuración de logging creado")
        except Exception as e:
            logger.error(f"❌ Error cargando configuración de logging: {e}")
            self.config = {'servers': {}, 'metadata': {}}
    
    def save_config(self):
        """Guardar configuración instantáneamente"""
        try:
            self.config['metadata']['last_updated'] = datetime.now().isoformat()
            self.config['metadata']['total_servers_configured'] = len(self.config['servers'])
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("💾 Configuración de logging guardada exitosamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando configuración de logging: {e}")
            return False
    
    def setup_server(self, guild_id: str, channel_id: str, setup_by: str) -> bool:
        """Configurar servidor para logging de comandos"""
        try:
            self.config['servers'][guild_id] = {
                'channel_id': channel_id,
                'setup_by': setup_by,
                'setup_at': datetime.now().isoformat(),
                'enabled': True,
                'commands_logged': 0
            }
            return self.save_config()
        except Exception as e:
            logger.error(f"❌ Error configurando servidor {guild_id}: {e}")
            return False
    
    def disable_server(self, guild_id: str) -> bool:
        """Deshabilitar logging para un servidor"""
        try:
            if guild_id in self.config['servers']:
                self.config['servers'][guild_id]['enabled'] = False
                self.config['servers'][guild_id]['disabled_at'] = datetime.now().isoformat()
                return self.save_config()
            return False
        except Exception as e:
            logger.error(f"❌ Error deshabilitando servidor {guild_id}: {e}")
            return False
    
    def get_log_channel(self, guild_id: str) -> Optional[str]:
        """Obtener canal de logging para un servidor"""
        server_config = self.config['servers'].get(guild_id)
        if server_config and server_config.get('enabled', False):
            return server_config.get('channel_id')
        return None
    
    def increment_command_count(self, guild_id: str):
        """Incrementar contador de comandos registrados"""
        if guild_id in self.config['servers']:
            self.config['servers'][guild_id]['commands_logged'] += 1
            # Guardar cada 10 comandos para no sobrecargar
            if self.config['servers'][guild_id]['commands_logged'] % 10 == 0:
                self.save_config()

# Instancia global
command_logger = CommandLogger()

def setup_commands(bot):
    """Función requerida para configurar comandos de logging"""
    
    @bot.tree.command(name="logsetup", description="[OWNER ONLY] Configurar canal para logging de comandos")
    async def logsetup_command(interaction: discord.Interaction, canal: discord.TextChannel = None):
        """Configurar canal donde se enviarán los logs de comandos"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        guild_id = str(interaction.guild.id)
        
        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Si no se especifica canal, usar el canal actual
            target_channel = canal or interaction.channel
            
            # Verificar permisos del bot en el canal
            permissions = target_channel.permissions_for(interaction.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Permisos Insuficientes",
                    description=f"El bot no tiene permisos para enviar mensajes o embeds en {target_channel.mention}.",
                    color=0xff0000
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Permisos Requeridos:",
                    value="• Enviar Mensajes\n• Insertar Enlaces\n• Usar Emojis Externos",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Configurar el servidor
            success = command_logger.setup_server(guild_id, str(target_channel.id), user_id)
            
            if success:
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Logging Configurado",
                    description=f"El sistema de logging de comandos ha sido configurado exitosamente.",
                    color=0x00ff88
                )
                embed.add_field(
                    name="<:1000182750:1396420537227411587> Canal Configurado:",
                    value=f"{target_channel.mention}",
                    inline=True
                )
                embed.add_field(
                    name="<:1000182644:1396049313481625611> Configurado por:",
                    value=f"{username}",
                    inline=True
                )
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Hora:",
                    value=f"<t:{int(datetime.now().timestamp())}:F>",
                    inline=True
                )
                embed.add_field(
                    name="<:1000182584:1396049547838492672> ¿Qué se registrará?",
                    value="• Todos los comandos slash ejecutados\n• Usuario que ejecutó el comando\n• Canal donde se ejecutó\n• Hora exacta de ejecución",
                    inline=False
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Gestión:",
                    value="• Usa `/logdisable` para deshabilitar\n• Usa `/logstats` para ver estadísticas\n• La configuración se guarda automáticamente",
                    inline=False
                )
                
                # Enviar mensaje de prueba al canal configurado
                test_embed = discord.Embed(
                    title="<:verify:1396087763388072006> Sistema de Logging Activado",
                    description="Este canal ahora recibirá logs de todos los comandos ejecutados en el servidor.",
                    color=0x00aa55
                )
                test_embed.add_field(
                    name="<:1000182644:1396049313481625611> Configurado por:",
                    value=f"{username}",
                    inline=True
                )
                test_embed.add_field(
                    name="<:1000182657:1396060091366637669> Fecha:",
                    value=f"<t:{int(datetime.now().timestamp())}:F>",
                    inline=True
                )
                test_embed.set_footer(text="RbxServers • Sistema de Logging de Comandos")
                
                try:
                    await target_channel.send(embed=test_embed)
                    embed.add_field(
                        name="<:verify:1396087763388072006> Prueba Exitosa:",
                        value="Se envió un mensaje de prueba al canal configurado.",
                        inline=False
                    )
                except Exception as test_error:
                    embed.add_field(
                        name="<:1000182563:1396420770904932372> Advertencia:",
                        value=f"La configuración fue exitosa, pero no se pudo enviar el mensaje de prueba: {str(test_error)[:100]}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"Owner {username} configuró logging en servidor {guild_id}, canal {target_channel.id}")
                
            else:
                embed = discord.Embed(
                    title="❌ Error de Configuración",
                    description="No se pudo guardar la configuración del sistema de logging.",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Sugerencia:",
                    value="Intenta nuevamente en unos momentos",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error en comando logsetup: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al configurar el sistema de logging.",
                color=0xff0000
            )
            embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}```", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="logdisable", description="[OWNER ONLY] Deshabilitar logging de comandos")
    async def logdisable_command(interaction: discord.Interaction):
        """Deshabilitar el sistema de logging de comandos"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        guild_id = str(interaction.guild.id)
        
        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            success = command_logger.disable_server(guild_id)
            
            if success:
                embed = discord.Embed(
                    title="⏹️ Logging Deshabilitado",
                    description="El sistema de logging de comandos ha sido deshabilitado para este servidor.",
                    color=0xff9900
                )
                embed.add_field(
                    name="<:1000182584:1396049547838492672> Estado:",
                    value="• Logging deshabilitado\n• No se registrarán más comandos\n• Configuración guardada para reactivación futura",
                    inline=False
                )
                embed.add_field(
                    name="💡 Reactivar:",
                    value="Usa `/logsetup` para reactivar el sistema",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"Owner {username} deshabilitó logging en servidor {guild_id}")
            else:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> No Configurado",
                    description="Este servidor no tiene el sistema de logging configurado.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error en comando logdisable: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al deshabilitar el logging.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="logstats", description="[OWNER ONLY] Ver estadísticas del sistema de logging")
    async def logstats_command(interaction: discord.Interaction):
        """Ver estadísticas del sistema de logging"""
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        
        # Verificar que solo el owner pueda usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            server_config = command_logger.config['servers'].get(guild_id)
            
            if not server_config:
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Sin Configuración",
                    description="Este servidor no tiene el sistema de logging configurado.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Configurar:",
                    value="Usa `/logsetup` para configurar el sistema",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Obtener información del canal
            channel_id = server_config.get('channel_id')
            channel = interaction.guild.get_channel(int(channel_id)) if channel_id else None
            
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Estadísticas de Logging",
                description="Información detallada del sistema de logging de comandos.",
                color=0x3366ff
            )
            
            # Estado actual
            status = "✅ Activo" if server_config.get('enabled', False) else "⏸️ Deshabilitado"
            embed.add_field(
                name="📊 **Estado Actual**",
                value=f"• **Estado:** {status}\n• **Canal:** {channel.mention if channel else 'Canal no encontrado'}\n• **Comandos registrados:** {server_config.get('commands_logged', 0)}",
                inline=False
            )
            
            # Información de configuración
            setup_at = server_config.get('setup_at', 'Desconocido')
            try:
                setup_timestamp = datetime.fromisoformat(setup_at.replace('Z', '+00:00'))
                setup_time = f"<t:{int(setup_timestamp.timestamp())}:F>"
            except:
                setup_time = "Fecha desconocida"
            
            embed.add_field(
                name="<:1000182751:1396420551798558781> **Configuración**",
                value=f"• **Configurado:** {setup_time}\n• **Por usuario ID:** {server_config.get('setup_by', 'Desconocido')}",
                inline=True
            )
            
            # Estadísticas globales
            total_servers = len(command_logger.config['servers'])
            active_servers = sum(1 for s in command_logger.config['servers'].values() if s.get('enabled', False))
            
            embed.add_field(
                name="🌐 **Estadísticas Globales**",
                value=f"• **Servidores configurados:** {total_servers}\n• **Servidores activos:** {active_servers}",
                inline=True
            )
            
            embed.set_footer(text="RbxServers • Sistema de Logging de Comandos")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error en comando logstats: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al obtener las estadísticas.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # Hook para capturar todos los comandos
    @bot.event
    async def on_app_command_completion(interaction: discord.Interaction, command):
        """Evento que se ejecuta cuando un comando se completa exitosamente"""
        try:
            if not interaction.guild:
                return  # Ignorar comandos en DM
            
            guild_id = str(interaction.guild.id)
            log_channel_id = command_logger.get_log_channel(guild_id)
            
            if not log_channel_id:
                return  # No hay logging configurado para este servidor
            
            # Obtener canal de logging
            log_channel = bot.get_channel(int(log_channel_id))
            if not log_channel:
                return
            
            # Incrementar contador
            command_logger.increment_command_count(guild_id)
            
            # Crear embed del log
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Comando Ejecutado",
                color=0x00aa55,
                timestamp=datetime.now()
            )
            
            # Información del comando
            embed.add_field(
                name="<:1000182751:1396420551798558781> Comando:",
                value=f"`/{command.name}`",
                inline=True
            )
            
            # Información del usuario
            embed.add_field(
                name="<:1000182614:1396049500375875646> Usuario:",
                value=f"{interaction.user.mention}\n`{interaction.user.name}#{interaction.user.discriminator}`\nID: `{interaction.user.id}`",
                inline=True
            )
            
            # Información del canal
            embed.add_field(
                name="<:1000182750:1396420537227411587> Canal:",
                value=f"{interaction.channel.mention}\n`#{interaction.channel.name}`",
                inline=True
            )
            
            # Obtener parámetros del comando si los hay
            if hasattr(interaction, 'data') and 'options' in interaction.data:
                options = interaction.data['options']
                if options:
                    params_text = ""
                    for option in options[:3]:  # Máximo 3 parámetros para no sobrecargar
                        params_text += f"• **{option['name']}:** `{str(option['value'])[:50]}{'...' if len(str(option['value'])) > 50 else ''}`\n"
                    
                    embed.add_field(
                        name="Parámetros:",
                        value=params_text,
                        inline=False
                    )
            
            embed.set_footer(
                text="RbxServers • Logging de Comandos",
                icon_url=interaction.user.display_avatar.url
            )
            
            # Enviar log al canal
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en logging de comando: {e}")
            # No mostrar error al usuario, solo registrar internamente
    
    logger.info("✅ Sistema de logging de comandos configurado")
    return True

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
