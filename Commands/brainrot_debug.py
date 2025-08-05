#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sistema de debug para brainrot - RbxServers
Comando para verificar canales y configuración
"""

import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
from pathlib import Path

# Configuración
logger = logging.getLogger(__name__)
DISCORD_OWNER_ID = "916070251895091241"  # ID del owner

def load_brainrot_data():
    """Carga los datos del archivo brainrot_data.json"""
    brainrot_data_path = Path('brainrot_data.json')
    if brainrot_data_path.exists():
        try:
            with open(brainrot_data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error("Error decodificando brainrot_data.json. Archivo corrupto.")
            return {}
        except Exception as e:
            logger.error(f"Error leyendo brainrot_data.json: {e}")
            return {}
    return {}

def setup_commands(bot):
    """Función requerida para configurar comandos de debug brainrot"""

    @bot.tree.command(name="brainrot-debug", description="[OWNER] Debug detallado del sistema de brainrot")
    async def brainrot_debug_command(interaction: discord.Interaction):
        """Mostrar información detallada de debug del sistema de brainrot"""
        try:
            user_id = str(interaction.user.id)

            # Verificar que solo el owner pueda usar este comando
            if user_id != DISCORD_OWNER_ID:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Este comando solo puede ser usado por el <:1000182644:1396049313481625611> owner del bot.",
                    color=0x2b2d31
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Leer configuración actual
            config = None
            try:
                if Path('brainrot_config.json').exists():
                    with open('brainrot_config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
            except Exception as e:
                logger.error(f"Error leyendo configuración: {e}")

            # Obtener información detallada de canales
            channel_info = []

            if config:
                channel_id = config.get('alert_channel_id')
                if channel_id:
                    channel = interaction.client.get_channel(channel_id)
                    if channel:
                        permissions = channel.permissions_for(channel.guild.me)
                        channel_info.append({
                            'name': channel.name,
                            'id': channel.id,
                            'guild': channel.guild.name,
                            'send_messages': permissions.send_messages,
                            'embed_links': permissions.embed_links,
                            'view_channel': permissions.view_channel
                        })
                    else:
                        channel_info.append({
                            'name': 'Canal no encontrado',
                            'id': channel_id,
                            'guild': 'Desconocido',
                            'send_messages': False,
                            'embed_links': False,
                            'view_channel': False
                        })

            # Información desde brainrot_data.json
            brainrot_data = load_brainrot_data()
            for guild_id, channel_config in brainrot_data.get('channels', {}).items():
                channel_id = channel_config.get('channel_id')
                if channel_id:
                    channel = interaction.client.get_channel(channel_id)
                    if channel:
                        permissions = channel.permissions_for(channel.guild.me)
                        channel_info.append({
                            'name': channel.name,
                            'id': channel.id,
                            'guild': channel.guild.name,
                            'send_messages': permissions.send_messages,
                            'embed_links': permissions.embed_links,
                            'view_channel': permissions.view_channel
                        })

            embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Debug Sistema Brainrot",
                description="Información detallada del sistema de alertas de brainrot",
                color=0x2b2d31,
                timestamp=datetime.now()
            )

            # Información de archivos de configuración
            config_info = ""
            if config:
                config_info += f"**brainrot_config.json:**\n"
                config_info += f"• Canal ID: {config.get('alert_channel_id', 'No configurado')}\n"
                config_info += f"• Guild ID: {config.get('guild_id', 'No configurado')}\n"
                config_info += f"• Configurado: {config.get('configured_at', 'Desconocido')}\n\n"
            else:
                config_info += "**brainrot_config.json:** ❌ No encontrado\n\n"

            data_channels = brainrot_data.get('channels', {})
            if data_channels:
                config_info += f"**brainrot_data.json:**\n"
                config_info += f"• Canales configurados: {len(data_channels)}\n"
                for guild_id, ch_config in data_channels.items():
                    config_info += f"• Canal: {ch_config.get('channel_name', 'Sin nombre')} (ID: {ch_config.get('channel_id')})\n"
            else:
                config_info += "**brainrot_data.json:** ❌ Sin canales configurados\n"

            embed.add_field(
                name="<:1000182750:1396420537227411587> Configuración de Archivos",
                value=config_info,
                inline=False
            )

            # Información de canales y permisos
            if channel_info:
                perms_info = ""
                for i, ch in enumerate(channel_info, 1):
                    status = "<:verify:1396087763388072006>" if all([ch['send_messages'], ch['embed_links'], ch['view_channel']]) else "<:1000182563:1396420770904932372>"
                    perms_info += f"{status} **{ch['name']}** (ID: {ch['id']})\n"
                    perms_info += f"   └ Servidor: {ch['guild']}\n"
                    perms_info += f"   └ Ver canal: {'✅' if ch['view_channel'] else '❌'}\n"
                    perms_info += f"   └ Enviar mensajes: {'✅' if ch['send_messages'] else '❌'}\n"
                    perms_info += f"   └ Embeds: {'✅' if ch['embed_links'] else '❌'}\n\n"

                embed.add_field(
                    name="<:1000182614:1396049500375875646> Estado de Canales y Permisos",
                    value=perms_info,
                    inline=False
                )
            else:
                embed.add_field(
                    name="<:1000182563:1396420770904932372> Estado de Canales",
                    value="No se encontraron canales configurados o accesibles",
                    inline=False
                )

            # Estado del bot
            bot_info = f"• Conectado: <:verify:1396087763388072006>\n"
            bot_info += f"• Servidores: {len(interaction.client.guilds)}\n"
            bot_info += f"• Canales accesibles: {sum(len(g.channels) for g in interaction.client.guilds)}\n"

            embed.add_field(
                name="<:1000182751:1396420551798558781> Estado del Bot",
                value=bot_info,
                inline=False
            )

            # Alertas recientes
            recent_alerts = brainrot_data.get('alerts', [])[-3:]  # Últimas 3
            if recent_alerts:
                alerts_info = ""
                for alert in recent_alerts:
                    status = "<:verify:1396087763388072006>" if alert.get('alerts_sent', 0) > 0 else "<:1000182563:1396420770904932372>"
                    alerts_info += f"{status} Job ID: `{alert.get('jobid', 'N/A')}`\n"
                    alerts_info += f"   └ Enviadas: {alert.get('alerts_sent', 0)}\n"
                    alerts_info += f"   └ Hora: {alert.get('timestamp', 'N/A')[:19]}\n\n"

                embed.add_field(
                    name="<:1000182657:1396060091366637669> Alertas Recientes",
                    value=alerts_info,
                    inline=False
                )

            embed.set_footer(text="Sistema de Debug • RbxServers")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en comando brainrot-debug: {e}")

            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al obtener información de debug.",
                color=0x2b2d31
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
<line_number>1</line_number>
"""
Debug específico para el sistema de brainrot
Permite verificar la conectividad y configuración del bot
"""

import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
DISCORD_OWNER_ID = "916070251895091241"

def setup_commands(bot):
    """Configurar comandos de debug para brainrot"""
    
    @bot.tree.command(name="brainrot-debug", description="[OWNER] Debug completo del sistema de brainrot")
    async def brainrot_debug_command(interaction: discord.Interaction):
        """Debug completo del sistema de brainrot con información detallada"""
        try:
            user_id = str(interaction.user.id)

            # Verificar que solo el owner pueda usar este comando
            if user_id != DISCORD_OWNER_ID:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Este comando solo puede ser usado por el <:1000182644:1396049313481625611> owner del bot.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)

            # Crear embed principal
            embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Debug Completo de Brainrot",
                description="Información detallada del sistema de alertas de brainrot",
                color=0x00ff88,
                timestamp=datetime.now()
            )

            # 1. Estado de conexión del bot
            bot_status = "🟢 Conectado" if bot.is_ready() else "🔴 Desconectado"
            servers_count = len(bot.guilds) if bot.guilds else 0
            
            embed.add_field(
                name="<:1000182584:1396049547838492672> **Estado del Bot**",
                value=f"• **Estado:** {bot_status}\n• **Servidores:** {servers_count}\n• **Latencia:** {round(bot.latency * 1000)}ms",
                inline=False
            )

            # 2. Listar todos los servidores donde está el bot con detalles
            if bot.guilds:
                servers_info = []
                for guild in bot.guilds:
                    text_channels = len(guild.text_channels)
                    voice_channels = len(guild.voice_channels)
                    total_members = len(guild.members) if guild.members else "N/A"
                    servers_info.append(f"• **{guild.name}** (ID: `{guild.id}`)")
                    servers_info.append(f"  └ Canales de texto: {text_channels}, Voz: {voice_channels}")
                    servers_info.append(f"  └ Miembros: {total_members}")
                
                servers_text = "\n".join(servers_info[:15])  # Mostrar más detalles
                if len(servers_info) > 15:
                    servers_text += f"\n• Y más información disponible..."
                
                embed.add_field(
                    name="<:1000182750:1396420537227411587> **Servidores Conectados**",
                    value=servers_text,
                    inline=False
                )

            # 3. Configuración de canales de brainrot
            try:
                # Cargar desde brainrot_data.json
                brainrot_data = {}
                if Path('brainrot_data.json').exists():
                    with open('brainrot_data.json', 'r', encoding='utf-8') as f:
                        brainrot_data = json.load(f)

                # Cargar desde brainrot_config.json
                brainrot_config = {}
                if Path('brainrot_config.json').exists():
                    with open('brainrot_config.json', 'r', encoding='utf-8') as f:
                        brainrot_config = json.load(f)

                config_info = []
                
                # Información de brainrot_data.json
                if brainrot_data.get('channels'):
                    config_info.append("**📂 brainrot_data.json:**")
                    for guild_id, channel_config in brainrot_data['channels'].items():
                        channel_id = channel_config.get('channel_id')
                        channel_name = channel_config.get('channel_name', 'Sin nombre')
                        guild_name = channel_config.get('guild_name', 'Sin nombre')
                        config_info.append(f"  • Canal: **{channel_name}** (ID: `{channel_id}`)")
                        config_info.append(f"    Servidor: {guild_name}")
                
                # Información de brainrot_config.json
                if brainrot_config.get('alert_channel_id'):
                    config_info.append("**📂 brainrot_config.json:**")
                    config_info.append(f"  • Canal ID: `{brainrot_config['alert_channel_id']}`")
                    config_info.append(f"  • Guild ID: `{brainrot_config.get('guild_id', 'No configurado')}`")

                if config_info:
                    embed.add_field(
                        name="<:1000182584:1396049547838492672> **Configuración de Canales**",
                        value="\n".join(config_info),
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="<:1000182563:1396420770904932372> **Configuración de Canales**",
                        value="❌ No hay canales configurados",
                        inline=False
                    )

            except Exception as config_error:
                embed.add_field(
                    name="<:1000182563:1396420770904932372> **Error de Configuración**",
                    value=f"Error leyendo configuración: {config_error}",
                    inline=False
                )

            # 4. Verificar acceso a canales específicos
            channels_to_check = []
            
            # Recopilar IDs de canales configurados
            if brainrot_data.get('channels'):
                for channel_config in brainrot_data['channels'].values():
                    if channel_config.get('channel_id'):
                        channels_to_check.append(channel_config['channel_id'])
            
            if brainrot_config.get('alert_channel_id'):
                channels_to_check.append(brainrot_config['alert_channel_id'])
            
            # Eliminar duplicados
            channels_to_check = list(set(channels_to_check))
            
            if channels_to_check:
                channel_status = []
                for channel_id in channels_to_check:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        permissions = channel.permissions_for(channel.guild.me)
                        status_icon = "<:verify:1396087763388072006>" if permissions.send_messages else "<:1000182563:1396420770904932372>"
                        channel_status.append(f"{status_icon} **{channel.name}** (ID: `{channel_id}`)")
                        channel_status.append(f"   └ Servidor: {channel.guild.name}")
                        channel_status.append(f"   └ Ver canal: {'✅' if permissions.view_channel else '❌'}")
                        channel_status.append(f"   └ Enviar mensajes: {'✅' if permissions.send_messages else '❌'}")
                        channel_status.append(f"   └ Embeds: {'✅' if permissions.embed_links else '❌'}")
                    else:
                        channel_status.append(f"<:1000182563:1396420770904932372> **Canal no encontrado** (ID: `{channel_id}`)")
                        channel_status.append(f"   └ El bot no está en el servidor del canal")
                
                embed.add_field(
                    name="<:1000182750:1396420537227411587> **Acceso a Canales**",
                    value="\n".join(channel_status),
                    inline=False
                )

            # 5. Estadísticas de alertas recientes
            try:
                if brainrot_data.get('alerts'):
                    recent_alerts = brainrot_data['alerts'][-5:]  # Últimas 5 alertas
                    alerts_info = []
                    
                    for alert in recent_alerts:
                        job_id = alert.get('jobid', 'Sin ID')[:15]
                        timestamp = alert.get('timestamp', 'Sin fecha')[:16]
                        alerts_sent = alert.get('alerts_sent', 0)
                        alerts_info.append(f"• **{job_id}** - {timestamp} - {alerts_sent} enviadas")
                    
                    embed.add_field(
                        name="<:1000182657:1396060091366637669> **Alertas Recientes**",
                        value="\n".join(alerts_info) if alerts_info else "Sin alertas recientes",
                        inline=False
                    )

            except Exception as alerts_error:
                logger.error(f"Error procesando alertas: {alerts_error}")

            # 6. Listado de TODOS los canales de texto disponibles para debug
            all_text_channels = []
            for guild in bot.guilds:
                for text_channel in guild.text_channels:
                    all_text_channels.append(f"• **{text_channel.name}** (ID: `{text_channel.id}`) - {guild.name}")
            
            if all_text_channels:
                channels_text = "\n".join(all_text_channels[:10])  # Primeros 10 canales
                if len(all_text_channels) > 10:
                    channels_text += f"\n• Y {len(all_text_channels) - 10} canales más..."
                
                embed.add_field(
                    name="<:1000182584:1396049547838492672> **Todos los Canales de Texto Disponibles**",
                    value=channels_text,
                    inline=False
                )

            # 7. URL de la API
            embed.add_field(
                name="<:1000182584:1396049547838492672> **API Information**",
                value="• **Endpoint:** `/api/brainrot`\n• **Método:** POST\n• **Estado:** Activo",
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error en brainrot-debug: {e}")
            
            error_embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error en Debug",
                description=f"Ocurrió un error durante el debug: {str(e)}",
                color=0xff0000
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("✅ Comandos de debug de brainrot configurados")
    return True
