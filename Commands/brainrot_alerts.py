
"""
Sistema de alertas para detectar modelos de Brainrot God en Steal A Brainrot
Comando owner only para gestionar notificaciones automáticas
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime
from aiohttp import web

logger = logging.getLogger(__name__)

# Owner ID
DISCORD_OWNER_ID = "916070251895091241"

# Canal de alertas por defecto
ALERT_CHANNEL_ID = None

def setup_commands(bot):
    """Función requerida para configurar comandos de alertas Brainrot"""
    
    @bot.tree.command(name="brainrot-setup", description="[OWNER] Configurar canal para alertas de Brainrot God")
    async def brainrot_setup_command(interaction: discord.Interaction, canal: discord.TextChannel):
        """Configurar canal donde se enviarán las alertas de Brainrot"""
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
            
            # Guardar configuración
            global ALERT_CHANNEL_ID
            ALERT_CHANNEL_ID = canal.id
            
            # Guardar en archivo para persistencia
            config = {
                'alert_channel_id': canal.id,
                'guild_id': interaction.guild.id,
                'configured_at': datetime.now().isoformat(),
                'configured_by': user_id
            }
            
            with open('brainrot_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            embed = discord.Embed(
                title="<:verify:1396087763388072006> Canal de Alertas Configurado",
                description=f"Las alertas de **Brainrot God** se enviarán automáticamente a {canal.mention}",
                color=0x2b2d31
            )
            
            embed.add_field(
                name="<:1000182584:1396049547838492672> **Configuración Activa**",
                value=f"• **Canal:** {canal.mention}\n• **Servidor:** {interaction.guild.name}\n• **Webhook:** `/api/brainrot-alert`",
                inline=False
            )
            
            embed.add_field(
                name="<:1000182751:1396420551798558781> **¿Cómo Funciona?**",
                value="• El script de Roblox detecta modelos de Brainrot God\n• Envía automáticamente los datos al webhook\n• El bot notifica inmediatamente en este canal\n• Incluye link directo al servidor encontrado",
                inline=False
            )
            
            embed.set_footer(text="Sistema está ahora activo y monitoreando")
            
            await interaction.followup.send(embed=embed)
            
            # Enviar mensaje de prueba al canal configurado
            test_embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Sistema de Alertas Brainrot Activado",
                description="Este canal ha sido configurado para recibir alertas automáticas cuando se detecten modelos de **Brainrot God** en Steal A Brainrot.",
                color=0x2b2d31
            )
            test_embed.add_field(
                name="<:verify:1396087763388072006> **Estado del Sistema**",
                value="**ACTIVO** - Monitoreando servidores en tiempo real",
                inline=False
            )
            
            await canal.send(embed=test_embed)
            
            logger.info(f"🧠 Canal de alertas Brainrot configurado: {canal.name} (ID: {canal.id})")
            
        except Exception as e:
            logger.error(f"Error configurando canal de alertas Brainrot: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al configurar el canal de alertas.",
                color=0x2b2d31
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

def load_brainrot_config():
    """Cargar configuración de alertas Brainrot"""
    try:
        with open('brainrot_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            global ALERT_CHANNEL_ID
            ALERT_CHANNEL_ID = config.get('alert_channel_id')
            logger.info(f"🧠 Configuración de Brainrot cargada: Canal {ALERT_CHANNEL_ID}")
            return config
    except FileNotFoundError:
        logger.info("🧠 No hay configuración de Brainrot previa")
        return None
    except Exception as e:
        logger.error(f"Error cargando configuración de Brainrot: {e}")
        return None

async def handle_brainrot_alert(request):
    """Manejar alertas del webhook de Brainrot"""
    try:
        # Verificar método
        if request.method != 'POST':
            return web.json_response({'error': 'Method not allowed'}, status=405)
        
        # Leer datos
        data = await request.json()
        logger.info(f"🧠 Alerta de Brainrot recibida: {data}")
        
        # RECARGAR CONFIGURACIÓN CADA VEZ
        config = load_brainrot_config()
        
        # Obtener el bot desde el contexto global
        from main import bot
        
        channel = None
        
        # Si hay configuración, intentar obtener el canal
        if config and config.get('alert_channel_id'):
            channel_id = config.get('alert_channel_id')
            channel = bot.get_channel(channel_id)
            
            if channel:
                logger.info(f"🧠 Canal configurado encontrado: {channel.name} (ID: {channel_id})")
            else:
                logger.warning(f"🧠 Canal configurado no encontrado: {channel_id}")
        
        # Si no hay canal, buscar automáticamente un canal apropiado
        if not channel:
            logger.info("🔍 Buscando canal apropiado automáticamente...")
            logger.info(f"🔍 Servidores conectados: {len(bot.guilds)}")
            
            # Buscar en todos los servidores del bot
            for guild in bot.guilds:
                logger.info(f"📊 Buscando en servidor: {guild.name} ({guild.id})")
                logger.info(f"📊 Canales de texto disponibles: {len(guild.text_channels)}")
                
                for text_channel in guild.text_channels:
                    logger.info(f"🔍 Revisando canal: {text_channel.name} (ID: {text_channel.id})")
                    
                    # Verificar permisos de envío
                    permissions = text_channel.permissions_for(guild.me)
                    can_send = permissions.send_messages
                    logger.info(f"🔐 Permisos en {text_channel.name}: enviar_mensajes={can_send}")
                    
                    if not can_send:
                        logger.info(f"❌ Sin permisos para enviar en: {text_channel.name}")
                        continue
                    
                    # Buscar el canal específico: ︰🧪・test・bot
                    if text_channel.name == "︰🧪・test・bot":
                        channel = text_channel
                        logger.info(f"🎯 Canal TEST-BOT encontrado: {channel.name} en {guild.name}")
                        
                        # Enviar mensaje simple con verify y return
                        await channel.send("<:verify:1396087763388072006>")
                        logger.info(f"✅ Mensaje verify enviado al canal {channel.name}")
                        
                        return web.json_response({
                            'status': 'success',
                            'message': 'Test message sent to specific channel',
                            'channel': channel.name,
                            'guild': guild.name,
                            'action': 'verify_only'
                        })
                    
                    # Buscar canales alternativos si no encuentra el específico
                    channel_name_lower = text_channel.name.lower()
                    logger.info(f"🔍 Nombre del canal en minúsculas: '{channel_name_lower}'")
                    
                    # Prioridad: canales con "brainrot" en el nombre
                    if 'brainrot' in channel_name_lower and not channel:
                        channel = text_channel
                        logger.info(f"🧠 Canal BRAINROT encontrado: {channel.name} en {guild.name}")
                    
                    # Segunda prioridad: canales con "test" y "bot" en el nombre
                    elif 'test' in channel_name_lower and 'bot' in channel_name_lower and not channel:
                        channel = text_channel
                        logger.info(f"🔧 Canal TEST-BOT alternativo encontrado: {channel.name} en {guild.name}")
                    
                    # Tercera prioridad: cualquier canal con permisos válidos
                    elif not channel:
                        channel = text_channel
                        logger.info(f"📝 Canal por defecto seleccionado: {channel.name} en {guild.name}")
                
                # Si encontramos el canal específico, salir del bucle
                if channel and channel.name == "︰🧪・test・bot":
                    logger.info(f"🎯 Canal específico encontrado, saliendo del bucle de búsqueda")
                    break
                
                # Si encontramos algún canal, también salir
                if channel:
                    logger.info(f"📝 Canal alternativo encontrado, saliendo del bucle de búsqueda")
                    break
            
            # Log final del estado de la búsqueda
            if channel:
                logger.info(f"✅ Canal seleccionado finalmente: {channel.name} (ID: {channel.id}) en {channel.guild.name}")
            else:
                logger.error(f"❌ No se encontró ningún canal después de revisar {len(bot.guilds)} servidores")
        
        # Si definitivamente no hay canal disponible
        if not channel:
            logger.error("🚫 No se encontró ningún canal válido para alertas")
            return web.json_response({'error': 'No valid channel found for alerts'}, status=404)
        
        # Actualizar configuración automáticamente si se encontró un canal diferente
        if not config or config.get('alert_channel_id') != channel.id:
            logger.info(f"🔄 Actualizando configuración automáticamente: {channel.name} (ID: {channel.id})")
            
            new_config = {
                'alert_channel_id': channel.id,
                'guild_id': channel.guild.id,
                'configured_at': datetime.now().isoformat(),
                'configured_by': 'auto_system',
                'auto_configured': True,
                'channel_name': channel.name,
                'guild_name': channel.guild.name
            }
            
            with open('brainrot_config.json', 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2)
            
            logger.info(f"✅ Configuración actualizada automáticamente: {channel.name}")
        
        logger.info(f"🎯 Canal final seleccionado: {channel.name} (ID: {channel.id}) en {channel.guild.name}")
        
        # Procesar TODOS los datos del servidor
        place_name = data.get('placeName', 'Desconocido')
        player_count = data.get('playerCount', 0)
        max_players = data.get('maxPlayers', 50)
        place_version = data.get('placeVersion', 'N/A')
        place_id = data.get('placeId', 'Desconocido')
        game_creator = data.get('gameCreator', 'Desconocido')
        executor = data.get('executor', 'Desconocido')
        datetime_detected = data.get('datetime', 'Ahora')
        server_id = data.get('serverId', 'Desconocido')
        local_player_id = data.get('localPlayerId', 'Desconocido')
        model_count = data.get('modelCount', 0)
        local_player = data.get('localPlayer', 'Scout Bot')
        timestamp = data.get('timestamp', 0)
        found_models = data.get('foundModels', [])
        
        # Crear enlace directo al servidor
        if place_id != 'Desconocido' and server_id != 'Desconocido':
            server_link = f"https://www.roblox.com/games/{place_id}?privateServerLinkCode={server_id}"
        else:
            server_link = "Link no disponible"
        
        # Preparar lista de modelos encontrados
        models_text = ""
        for i, model in enumerate(found_models[:8], 1):  # Máximo 8 modelos para no sobrecargar
            model_name = model.get('name', 'Modelo Desconocido')
            model_position = model.get('position', 'Posición desconocida')
            model_class = model.get('className', 'Model')
            models_text += f"**{i}.** `{model_name}`\n"
            models_text += f"     <:1000182750:1396420537227411587> `{model_class}` en `{model_position}`\n"
        
        if len(found_models) > 8:
            models_text += f"*... y {len(found_models) - 8} modelos más*\n"
        
        # Crear embed épico con colores grises
        embed = discord.Embed(
            title="<:1000182751:1396420551798558781> BRAINROT GOD DETECTADO",
            description=f"**¡Un servidor con modelos de Brainrot ha sido encontrado!**\n\n<:verify:1396087763388072006> **¡ÚNETE AHORA MISMO ANTES QUE SE LLENE!**",
            color=0x2b2d31
        )
        
        embed.add_field(
            name="<:1000182584:1396049547838492672> **MODELOS ENCONTRADOS** ({})".format(len(found_models)),
            value=models_text or "`No hay detalles específicos`",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182750:1396420537227411587> **INFORMACIÓN DEL SERVIDOR**",
            value=(
                f"• **Nombre del Lugar:** `{place_name}`\n"
                f"• **ID del Lugar:** `{place_id}`\n"
                f"• **Versión:** `{place_version}`\n"
                f"• **Creador:** `{game_creator}`\n"
                f"• **Servidor ID:** `{server_id}`\n"
                f"• **Jugadores:** `{player_count}/{max_players}`"
            ),
            inline=True
        )
        
        embed.add_field(
            name="<:1000182657:1396060091366637669> **DETALLES DE DETECCIÓN**",
            value=(
                f"• **Ejecutor Usado:** `{executor}`\n"
                f"• **Detectado por:** `{local_player}`\n"
                f"• **Player ID:** `{local_player_id}`\n"
                f"• **Modelos Total:** `{model_count}`\n"
                f"• **Detectado:** `{datetime_detected}`"
            ),
            inline=True
        )
        
        embed.add_field(
            name="<:1000182614:1396049500375875646> **ESTADO DEL SERVIDOR**",
            value=(
                f"• **Jugadores Conectados:** `{player_count}`\n"
                f"• **Capacidad Máxima:** `{max_players}`\n"
                f"• **Espacios Disponibles:** `{max_players - player_count}`\n"
                f"• **Ocupación:** `{round((player_count/max_players)*100, 1)}%`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="<:verify:1396087763388072006> **ACCESO DIRECTO**",
            value=f"[**CLICK AQUÍ PARA UNIRTE AL SERVIDOR**]({server_link})\n\n<:1000182751:1396420551798558781> **¡VE RÁPIDO ANTES QUE SE LLENE!**",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182584:1396049547838492672> **QUÉ HACER**",
            value="• Click en el enlace de arriba\n• Únete al servidor inmediatamente\n• Busca los modelos listados\n• ¡Consigue tu Brainrot God!",
            inline=False
        )
        
        embed.set_footer(
            text=f"Detectado el {datetime.now().strftime('%H:%M:%S')} | Sistema automático RbxServers"
        )
        
        # Verificar si el canal fue configurado automáticamente y notificarlo
        was_auto_configured = config and config.get('auto_configured', False)
        
        if was_auto_configured:
            auto_notice = discord.Embed(
                title="<:1000182751:1396420551798558781> Canal Configurado Automáticamente",
                description=f"El sistema configuró automáticamente este canal ({channel.mention}) para recibir alertas de Brainrot God.",
                color=0x2b2d31
            )
            auto_notice.add_field(
                name="<:verify:1396087763388072006> **Configuración:**",
                value=f"• **Canal:** {channel.mention}\n• **Servidor:** {channel.guild.name}\n• **Configurado:** Automáticamente por el sistema",
                inline=False
            )
            await channel.send(embed=auto_notice)
        
        # Enviar alerta con @everyone
        await channel.send(
            content="@everyone <:1000182563:1396420770904932372> **¡ALERTA MÁXIMA DE BRAINROT GOD!** <:1000182563:1396420770904932372>", 
            embed=embed
        )
        
        logger.info(f"🧠 Alerta de Brainrot enviada exitosamente al canal {channel.name}")
        
        return web.json_response({
            'status': 'success',
            'message': 'Alert sent successfully',
            'channel': channel.name,
            'models_count': len(found_models),
            'player_count': player_count,
            'server_capacity': f"{player_count}/{max_players}"
        })
        
    except Exception as e:
        logger.error(f"🧠 Error procesando alerta de Brainrot: {e}")
        return web.json_response({'error': str(e)}, status=500)

def setup_brainrot_webhook(app):
    """Configurar endpoint del webhook para alertas de Brainrot"""
    app.router.add_post('/api/brainrot-alert', handle_brainrot_alert)
    app.router.add_options('/api/brainrot-alert', lambda r: web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    ))
    logger.info("🧠 Webhook de alertas Brainrot configurado en /api/brainrot-alert")

# Cargar configuración al importar el módulo
load_brainrot_config()
