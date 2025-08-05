
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
        if not config or not config.get('alert_channel_id'):
            logger.warning("🧠 No hay canal configurado para alertas de Brainrot")
            return web.json_response({'error': 'No alert channel configured'}, status=400)
        
        # Obtener el bot desde el contexto global
        from main import bot
        
        channel_id = config.get('alert_channel_id')
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"🧠 Canal de alertas no encontrado: {channel_id}")
            return web.json_response({'error': 'Alert channel not found'}, status=404)
        
        # Procesar TODOS los datos del servidor
        players = data.get('players', [])
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
        
        # Lista de jugadores en el servidor
        players_text = ""
        for i, player in enumerate(players[:10], 1):  # Máximo 10 jugadores
            player_name = player.get('name', 'Desconocido')
            player_display = player.get('displayName', player_name)
            player_id = player.get('userId', 'N/A')
            players_text += f"**{i}.** `{player_display}` (ID: {player_id})\n"
        
        if len(players) > 10:
            players_text += f"*... y {len(players) - 10} jugadores más*\n"
        
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
        
        if players_text:
            embed.add_field(
                name="<:1000182614:1396049500375875646> **JUGADORES EN SERVIDOR** ({})".format(len(players)),
                value=players_text,
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
            'players_count': len(players)
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
