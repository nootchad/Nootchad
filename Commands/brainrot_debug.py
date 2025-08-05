
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
            
            embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Debug del Sistema Brainrot",
                description="Información detallada del sistema de brainrot y canales disponibles",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            
            # Información de configuración
            if config:
                channel_id = config.get('alert_channel_id')
                embed.add_field(
                    name="<:1000182584:1396049547838492672> **Configuración Actual**",
                    value=f"• **Canal ID:** `{channel_id}`\n• **Guild ID:** `{config.get('guild_id')}`\n• **Configurado:** {config.get('configured_at')}\n• **Por:** <@{config.get('configured_by')}>",
                    inline=False
                )
                
                # Verificar si el canal existe
                configured_channel = bot.get_channel(channel_id)
                if configured_channel:
                    embed.add_field(
                        name="<:verify:1396087763388072006> **Canal Configurado**",
                        value=f"• **Nombre:** {configured_channel.name}\n• **Servidor:** {configured_channel.guild.name}\n• **Estado:** ✅ Activo",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="<:1000182563:1396420770904932372> **Canal Configurado**",
                        value=f"• **ID:** {channel_id}\n• **Estado:** ❌ No encontrado",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="<:1000182563:1396420770904932372> **Sin Configuración**",
                    value="No hay configuración de brainrot guardada",
                    inline=False
                )
            
            # Información de servidores
            servers_info = []
            for guild in bot.guilds:
                text_channels = [ch for ch in guild.channels if hasattr(ch, 'send')]
                servers_info.append(f"• **{guild.name}** (ID: `{guild.id}`)\n  📺 {len(text_channels)} canales de texto")
            
            embed.add_field(
                name="<:1000182750:1396420537227411587> **Servidores Conectados**",
                value="\n".join(servers_info[:5]) + (f"\n... y {len(bot.guilds) - 5} más" if len(bot.guilds) > 5 else ""),
                inline=False
            )
            
            # Canales del servidor actual
            current_guild = interaction.guild
            if current_guild:
                text_channels = [ch for ch in current_guild.channels if hasattr(ch, 'send')]
                channels_info = []
                for ch in text_channels[:10]:  # Mostrar primeros 10
                    channels_info.append(f"• **{ch.name}** (ID: `{ch.id}`)")
                
                embed.add_field(
                    name=f"<:1000182750:1396420537227411587> **Canales en {current_guild.name}**",
                    value="\n".join(channels_info) + (f"\n... y {len(text_channels) - 10} más" if len(text_channels) > 10 else ""),
                    inline=False
                )
            
            embed.set_footer(text="Debug del Sistema Brainrot - RbxServers")
            
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
