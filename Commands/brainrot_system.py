#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sistema de brainrot para RbxServers
Maneja la configuración de canales y el procesamiento de alertas de brainrot
"""

import discord
from discord.ext import commands
import json
import logging
from datetime import datetime
import time
from pathlib import Path
from aiohttp import web

# Configuración
logger = logging.getLogger(__name__)
DISCORD_OWNER_ID = "916070251895091241"  # ID del owner

def load_brainrot_data():
    """Cargar datos de brainrot desde archivo JSON"""
    try:
        if Path('brainrot_data.json').exists():
            with open('brainrot_data.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "channels": {},
                "alerts": [],
                "last_updated": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"<:1000182563:1396420770904932372> Error cargando datos de brainrot: {e}")
        return {
            "channels": {},
            "alerts": [],
            "last_updated": datetime.now().isoformat()
        }

def save_brainrot_data(data):
    """Guardar datos de brainrot en archivo JSON"""
    try:
        data["last_updated"] = datetime.now().isoformat()
        with open('brainrot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"<:verify:1396087763388072006> Datos de brainrot guardados exitosamente")
        return True
    except Exception as e:
        logger.error(f"<:1000182563:1396420770904932372> Error guardando datos de brainrot: {e}")
        return False

def load_brainrot_config():
    """Cargar configuración de canal de brainrot"""
    try:
        if Path('brainrot_config.json').exists():
            with open('brainrot_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"<:1000182563:1396420770904932372> Error cargando configuración de brainrot: {e}")
        return None

def save_brainrot_config(config):
    """Guardar configuración de canal de brainrot"""
    try:
        with open('brainrot_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"<:verify:1396087763388072006> Configuración de brainrot guardada")
        return True
    except Exception as e:
        logger.error(f"<:1000182563:1396420770904932372> Error guardando configuración: {e}")
        return False

async def handle_brainrot_api(request):
    """Manejar peticiones de la API de brainrot"""
    try:
        # Verificar método
        if request.method != 'POST':
            return web.json_response({'error': 'Method not allowed'}, status=405)

        # Leer datos
        data = await request.json()
        logger.info(f"🧠 Datos de brainrot recibidos: {data}")

        # Validar datos requeridos
        required_fields = ['jobid', 'players', 'brainrot_name']
        for field in required_fields:
            if field not in data:
                return web.json_response({'error': f'Missing required field: {field}'}, status=400)

        # Obtener el bot desde el contexto global
        from main import bot

        # Cargar configuración de ambos archivos
        brainrot_data = load_brainrot_data()
        brainrot_config = load_brainrot_config()
        
        alerts_sent = 0
        channels_found = []
        all_channel_ids = set()

        # Recopilar IDs de canales de ambas fuentes
        # Desde brainrot_data.json
        if brainrot_data.get('channels'):
            for guild_id, channel_config in brainrot_data["channels"].items():
                channel_id = channel_config.get("channel_id")
                if channel_id:
                    all_channel_ids.add(channel_id)
                    logger.info(f"🧠 Canal encontrado en brainrot_data.json: {channel_id} ({channel_config.get('channel_name', 'Sin nombre')})")

        # Desde brainrot_config.json
        if brainrot_config and brainrot_config.get('alert_channel_id'):
            channel_id = brainrot_config.get('alert_channel_id')
            all_channel_ids.add(channel_id)
            logger.info(f"🧠 Canal encontrado en brainrot_config.json: {channel_id}")

        if not all_channel_ids:
            logger.warning("🧠 No hay canales configurados en ningún archivo")
            return web.json_response({
                'status': 'error',
                'message': 'No brainrot channels configured',
                'suggestion': 'Use /brainrot command to configure a channel first'
            }, status=400)

        # Debug del bot y servidores conectados
        logger.info(f"🔍 Bot conectado: {bot is not None}")
        if bot and hasattr(bot, 'guilds'):
            logger.info(f"🔍 Servidores conectados: {len(bot.guilds)}")
            for guild in bot.guilds:
                logger.info(f"   - {guild.name} (ID: {guild.id}) - Canales: {len(guild.channels)}")
        
        # Si el bot no está en ningún servidor, devolver error específico
        if not bot.guilds:
            logger.error(f"🚫 ERROR CRÍTICO: El bot no está unido a ningún servidor de Discord")
            return web.json_response({
                'status': 'error',
                'message': 'Bot is not connected to any Discord servers',
                'error_type': 'bot_not_in_servers',
                'solution': 'Add the bot to the Discord server where the brainrot channel is located',
                'timestamp': datetime.now().isoformat()
            }, status=500)

        # Intentar enviar a cada canal configurado
        for channel_id in all_channel_ids:
            try:
                # Buscar el canal por ID
                channel = bot.get_channel(channel_id)
                
                if not channel:
                    logger.warning(f"🧠 Canal {channel_id} no encontrado directamente")
                    
                    # Buscar en todos los servidores si no se encuentra directamente
                    found_in_guild = False
                    for guild in bot.guilds:
                        logger.info(f"🔍 Buscando canal {channel_id} en servidor {guild.name} (ID: {guild.id})")
                        for guild_channel in guild.channels:
                            if guild_channel.id == channel_id:
                                channel = guild_channel
                                logger.info(f"✅ Canal {channel_id} encontrado en servidor {guild.name}")
                                found_in_guild = True
                                break
                        if found_in_guild:
                            break
                    
                    if not found_in_guild:
                        logger.error(f"🚫 Canal {channel_id} NO encontrado en ningún servidor donde está el bot")
                        # Listar servidores disponibles para debug
                        available_servers = [f"{g.name} (ID: {g.id})" for g in bot.guilds]
                        logger.error(f"🔍 Servidores disponibles: {available_servers}")

                if not channel:
                    logger.error(f"🧠 Canal {channel_id} no existe o bot no está en ese servidor")
                    continue

                logger.info(f"🧠 Intentando enviar al canal: {channel.name} (ID: {channel_id}) en servidor: {channel.guild.name}")

                # Verificar permisos
                permissions = channel.permissions_for(channel.guild.me)
                logger.info(f"🔐 Permisos en {channel.name}: send_messages={permissions.send_messages}, embed_links={permissions.embed_links}")

                if not permissions.send_messages:
                    logger.error(f"🚫 Bot no tiene permisos para enviar mensajes en {channel.name}")
                    continue

                # Crear embed de alerta
                embed = discord.Embed(
                    title="<:1000182751:1396420551798558781> Alerta de Brainrot Detectado",
                    description=f"**Job ID:** `{data.get('jobid')}`\n**<:1000182614:1396049500375875646> Jugadores:** {data.get('players')}\n**<:1000182584:1396049547838492672> Nombre:** {data.get('brainrot_name')}",
                    color=0xff6b6b,
                    timestamp=datetime.now()
                )

                embed.add_field(
                    name="<:1000182584:1396049547838492672> Información Adicional",
                    value="Se ha detectado actividad de brainrot en el servidor. Alerta generada automáticamente por el sistema.",
                    inline=False
                )

                embed.set_footer(text="RbxServers • Sistema de Alertas Brainrot", icon_url="https://cdn.discordapp.com/emojis/1000182751.png")

                # Intentar enviar mensaje
                try:
                    sent_message = await channel.send(embed=embed)
                    alerts_sent += 1
                    channels_found.append({
                        'channel_name': channel.name,
                        'channel_id': channel.id,
                        'guild_name': channel.guild.name,
                        'guild_id': channel.guild.id,
                        'message_id': sent_message.id
                    })
                    logger.info(f"<:verify:1396087763388072006> Alerta enviada exitosamente al canal {channel.name} en {channel.guild.name}")
                    
                except discord.Forbidden:
                    logger.error(f"🚫 Sin permisos para enviar mensaje en {channel.name}")
                except discord.HTTPException as e:
                    logger.error(f"🌐 Error HTTP enviando mensaje: {e}")
                except Exception as send_error:
                    logger.error(f"💥 Error enviando mensaje: {send_error}")

            except Exception as channel_error:
                logger.error(f"🧠 Error procesando canal {channel_id}: {channel_error}")
                import traceback
                logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                continue

        # Guardar registro de la alerta
        alert_record = {
            "jobid": data.get('jobid'),
            "players": data.get('players'),
            "brainrot_name": data.get('brainrot_name'),
            "timestamp": datetime.now().isoformat(),
            "channels_notified": channels_found,
            "alerts_sent": alerts_sent,
            "processed": True,
            "channels_attempted": list(all_channel_ids)
        }

        brainrot_data["alerts"].append(alert_record)
        save_brainrot_data(brainrot_data)

        if alerts_sent > 0:
            return web.json_response({
                'status': 'success',
                'message': f'Brainrot alert sent to {alerts_sent} channel(s)',
                'jobid': data.get('jobid'),
                'alerts_sent': alerts_sent,
                'channels_notified': channels_found,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return web.json_response({
                'status': 'error',
                'message': 'No alerts could be sent - check bot permissions and channel configuration',
                'jobid': data.get('jobid'),
                'channels_attempted': list(all_channel_ids),
                'alerts_sent': 0,
                'timestamp': datetime.now().isoformat()
            }, status=500)

    except Exception as e:
        logger.error(f"🧠 Error crítico procesando API de brainrot: {e}")
        import traceback
        logger.error(f"🔍 Traceback completo: {traceback.format_exc()}")
        return web.json_response({'error': str(e)}, status=500)

def setup_brainrot_api(app):
    """Configurar endpoint de la API de brainrot"""
    logger.info("🧠 Configurando API de brainrot...")

    # Registrar endpoint POST
    app.router.add_post('/api/brainrot', handle_brainrot_api)

    # Registrar endpoint OPTIONS para CORS
    async def handle_options(request):
        return web.Response(
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )

    app.router.add_options('/api/brainrot', handle_options)

    logger.info("🧠 API de brainrot configurada exitosamente")

def setup_commands(bot):
    """Función requerida para configurar comandos de brainrot"""

    @bot.tree.command(name="brainrot", description="[OWNER] Configurar canal para alertas de brainrot")
    async def brainrot_command(interaction: discord.Interaction, canal: discord.TextChannel):
        """Configurar canal donde se enviarán las alertas de brainrot"""
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

            # Cargar datos existentes de brainrot
            brainrot_data = load_brainrot_data()

            # Agregar/actualizar el canal en brainrot_data.json
            if "channels" not in brainrot_data:
                brainrot_data["channels"] = {}

            guild_id = str(interaction.guild.id)
            brainrot_data["channels"][guild_id] = {
                "channel_id": canal.id,
                "channel_name": canal.name,
                "guild_name": interaction.guild.name,
                "configured_at": datetime.now().isoformat(),
                "configured_by": user_id
            }

            # Guardar en brainrot_data.json
            data_saved = save_brainrot_data(brainrot_data)

            # También mantener la configuración legacy en brainrot_config.json
            config = {
                "alert_channel_id": canal.id,
                "guild_id": interaction.guild.id,
                "configured_at": datetime.now().isoformat(),
                "configured_by": user_id
            }
            config_saved = save_brainrot_config(config)

            # Verificar que ambos se guardaron correctamente
            if data_saved and config_saved:
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Canal de Brainrot Configurado",
                    description=f"El canal {canal.mention} ha sido configurado para recibir alertas de **brainrot**.",
                    color=0x2b2d31
                )

                # Mostrar estadísticas de canales configurados
                total_channels = len(brainrot_data["channels"])

                embed.add_field(
                    name="<:1000182584:1396049547838492672> **Configuración Activa**",
                    value=f"• **Canal:** {canal.mention}\n• **Servidor:** {interaction.guild.name}\n• **API Endpoint:** `/api/brainrot`\n• **Total Canales:** {total_channels}",
                    inline=False
                )

                embed.add_field(
                    name="<:1000182751:1396420770904932372> **Datos Recibidos**",
                    value="• **Job ID:** Identificador del trabajo\n• **Jugadores:** Número total de jugadores\n• **Nombre Brainrot:** Nombre del brainrot encontrado",
                    inline=False
                )

                embed.set_footer(text="Sistema configurado correctamente")

                await interaction.followup.send(embed=embed)

                # Enviar mensaje de confirmación al canal configurado
                test_embed = discord.Embed(
                    title="<:1000182751:1396420551798558781> Canal de Brainrot Activo",
                    description="Este canal ha sido configurado para recibir **alertas de brainrot**.",
                    color=0x2b2d31,
                    timestamp=datetime.now()
                )

                test_embed.add_field(
                    name="<:1000182584:1396049547838492672> **Estado**",
                    value="• **Sistema:** Activo\n• **Configurado por:** <:1000182644:1396049313481625611> Owner\n• **Endpoint:** `/api/brainrot`",
                    inline=False
                )

                test_embed.set_footer(text="Sistema de Brainrot - RbxServers")

                await canal.send(embed=test_embed)

                logger.info(f"<:verify:1396087763388072006> Canal de brainrot configurado: {canal.name} (ID: {canal.id})")

            else:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Error",
                    description="Hubo un error al guardar la configuración del canal.",
                    color=0x2b2d31
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en comando brainrot: {e}")

            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al configurar el canal de brainrot.",
                color=0x2b2d31
            )

            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)