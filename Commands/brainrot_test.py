
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Comando de prueba para brainrot - RbxServers
Prueba directa de envío de mensajes al canal configurado
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
    """Función requerida para configurar comando de prueba de brainrot"""

    @bot.tree.command(name="brainrot-test", description="[OWNER] Probar envío directo de mensaje al canal de brainrot")
    async def brainrot_test_command(interaction: discord.Interaction):
        """Probar envío directo de mensaje al canal de brainrot configurado"""
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

            # Cargar configuración de canales
            brainrot_data = {}
            brainrot_config = {}
            
            try:
                if Path('brainrot_data.json').exists():
                    with open('brainrot_data.json', 'r', encoding='utf-8') as f:
                        brainrot_data = json.load(f)
                
                if Path('brainrot_config.json').exists():
                    with open('brainrot_config.json', 'r', encoding='utf-8') as f:
                        brainrot_config = json.load(f)
            except Exception as e:
                logger.error(f"Error cargando configuración: {e}")

            # Recopilar IDs de canales
            channels_to_test = []
            
            # Desde brainrot_data.json
            if brainrot_data.get('channels'):
                for channel_config in brainrot_data['channels'].values():
                    if channel_config.get('channel_id'):
                        channels_to_test.append(channel_config['channel_id'])
            
            # Desde brainrot_config.json
            if brainrot_config.get('alert_channel_id'):
                channels_to_test.append(brainrot_config['alert_channel_id'])
            
            # Eliminar duplicados
            channels_to_test = list(set(channels_to_test))

            if not channels_to_test:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Sin Canales Configurados",
                    description="No hay canales de brainrot configurados para probar.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed)
                return

            # Probar cada canal
            test_results = []
            successful_sends = 0

            for channel_id in channels_to_test:
                try:
                    logger.info(f"🧪 Probando canal ID: {channel_id}")
                    
                    # Buscar canal
                    channel = bot.get_channel(channel_id)
                    
                    if not channel:
                        # Buscar manualmente
                        for guild in bot.guilds:
                            for text_channel in guild.text_channels:
                                if text_channel.id == channel_id:
                                    channel = text_channel
                                    break
                            if channel:
                                break
                    
                    if channel:
                        # Verificar permisos
                        permissions = channel.permissions_for(channel.guild.me)
                        
                        if permissions.send_messages and permissions.embed_links:
                            # Intentar enviar mensaje de prueba
                            test_embed = discord.Embed(
                                title="<:1000182751:1396420551798558781> Prueba de Brainrot",
                                description="Este es un mensaje de prueba del sistema de brainrot.",
                                color=0x00ff88,
                                timestamp=datetime.now()
                            )
                            
                            test_embed.add_field(
                                name="<:1000182584:1396049547838492672> Estado",
                                value="✅ Conexión exitosa al canal",
                                inline=True
                            )
                            
                            test_embed.add_field(
                                name="<:1000182657:1396060091366637669> Hora de Prueba",
                                value=f"<t:{int(datetime.now().timestamp())}:F>",
                                inline=True
                            )
                            
                            test_embed.set_footer(text="Sistema de Brainrot - RbxServers • PRUEBA")
                            
                            sent_message = await channel.send(embed=test_embed)
                            
                            test_results.append(f"✅ **{channel.name}** (ID: `{channel_id}`)")
                            test_results.append(f"   └ Servidor: {channel.guild.name}")
                            test_results.append(f"   └ Mensaje enviado: {sent_message.id}")
                            successful_sends += 1
                            
                            logger.info(f"✅ Mensaje de prueba enviado exitosamente al canal {channel.name}")
                            
                        else:
                            test_results.append(f"❌ **{channel.name}** (ID: `{channel_id}`)")
                            test_results.append(f"   └ Servidor: {channel.guild.name}")
                            test_results.append(f"   └ Sin permisos: send_messages={permissions.send_messages}, embed_links={permissions.embed_links}")
                    else:
                        test_results.append(f"❌ **Canal no encontrado** (ID: `{channel_id}`)")
                        test_results.append(f"   └ El bot no está en el servidor del canal")
                        
                except Exception as channel_error:
                    test_results.append(f"💥 **Error en canal** (ID: `{channel_id}`)")
                    test_results.append(f"   └ Error: {str(channel_error)}")
                    logger.error(f"Error probando canal {channel_id}: {channel_error}")

            # Crear embed de resultados
            embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Resultados de Prueba de Brainrot",
                description=f"Prueba completada en {len(channels_to_test)} canales configurados.",
                color=0x00ff88 if successful_sends > 0 else 0xff0000,
                timestamp=datetime.now()
            )

            embed.add_field(
                name="<:1000182584:1396049547838492672> **Resumen**",
                value=f"• **Canales probados:** {len(channels_to_test)}\n• **Envíos exitosos:** {successful_sends}\n• **Fallos:** {len(channels_to_test) - successful_sends}",
                inline=False
            )

            if test_results:
                results_text = "\n".join(test_results)
                embed.add_field(
                    name="<:1000182750:1396420537227411587> **Detalles de Prueba**",
                    value=results_text[:1024],  # Límite de Discord
                    inline=False
                )

            embed.set_footer(text="Prueba de Sistema de Brainrot • RbxServers")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Error en brainrot-test: {e}")
            
            error_embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error en Prueba",
                description=f"Ocurrió un error durante la prueba: {str(e)}",
                color=0xff0000
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("✅ Comando de prueba de brainrot configurado")
    return True
