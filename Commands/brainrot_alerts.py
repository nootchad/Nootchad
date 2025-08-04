
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
                    title="❌ Acceso Denegado",
                    description="Este comando solo puede ser usado por el owner del bot.",
                    color=0xff0000
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
                color=0x00ff88
            )
            
            embed.add_field(
                name="<:1000182584:1396049547838492672> **Configuración Activa**",
                value=f"• **Canal:** {canal.mention}\n• **Servidor:** {interaction.guild.name}\n• **Webhook:** `https://workspace-paysencharlee.replit.dev/api/brainrot-alert`",
                inline=False
            )
            
            embed.add_field(
                name="<:1000182751:1396420551798558781> **¿Cómo Funciona?**",
                value="• El script de Roblox detecta modelos de Brainrot God\n• Envía automáticamente los datos al webhook\n• El bot notifica inmediatamente en este canal\n• Incluye link directo al servidor encontrado",
                inline=False
            )
            
            embed.set_footer(text="💡 El sistema está ahora activo y monitoreando")
            
            await interaction.followup.send(embed=embed)
            
            # Enviar mensaje de prueba al canal configurado
            test_embed = discord.Embed(
                title="🧠 Sistema de Alertas Brainrot Activado",
                description="Este canal ha sido configurado para recibir alertas automáticas cuando se detecten modelos de **Brainrot God** en Steal A Brainrot.",
                color=0x9932cc
            )
            test_embed.add_field(
                name="⚡ **Estado del Sistema**",
                value="✅ **ACTIVO** - Monitoreando servidores en tiempo real",
                inline=False
            )
            
            await canal.send(embed=test_embed)
            
            logger.info(f"🧠 Canal de alertas Brainrot configurado: {canal.name} (ID: {canal.id})")
            
        except Exception as e:
            logger.error(f"Error configurando canal de alertas Brainrot: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al configurar el canal de alertas.",
                color=0xff0000
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
        
        # Verificar si hay canal configurado
        if not ALERT_CHANNEL_ID:
            logger.warning("🧠 No hay canal configurado para alertas de Brainrot")
            return web.json_response({'error': 'No alert channel configured'}, status=400)
        
        # Obtener el bot desde el contexto global
        from main import bot
        
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        if not channel:
            logger.error(f"🧠 Canal de alertas no encontrado: {ALERT_CHANNEL_ID}")
            return web.json_response({'error': 'Alert channel not found'}, status=404)
        
        # Procesar datos del servidor
        server_id = data.get('serverId', 'Desconocido')
        place_id = data.get('placeId', 'Desconocido')
        player_count = data.get('playerCount', 0)
        found_models = data.get('foundModels', [])
        player_name = data.get('playerName', 'Scout Bot')
        
        # Crear enlace directo al servidor
        server_link = f"https://www.roblox.com/games/{place_id}?privateServerLinkCode={server_id}" if server_id != 'Desconocido' else "Link no disponible"
        
        # Preparar lista de modelos encontrados
        models_text = ""
        for i, model in enumerate(found_models[:10], 1):  # Máximo 10 modelos
            models_text += f"**{i}.** `{model.get('name', 'Modelo Desconocido')}`\n"
        
        if len(found_models) > 10:
            models_text += f"*... y {len(found_models) - 10} modelos más*\n"
        
        # Crear embed épico
        embed = discord.Embed(
            title="🧠💎 ¡BRAINROT GOD DETECTADO! 💎🧠",
            description=f"**¡Un servidor con modelos de Brainrot ha sido encontrado!**\n\n🔥 **¡ÚNETE AHORA MISMO ANTES QUE SE LLENE!** 🔥",
            color=0xff6b35
        )
        
        embed.add_field(
            name="🎯 **MODELOS ENCONTRADOS**",
            value=models_text or "`No hay detalles específicos`",
            inline=False
        )
        
        embed.add_field(
            name="🌐 **INFORMACIÓN DEL SERVIDOR**",
            value=f"• **ID del Servidor:** `{server_id}`\n• **Lugar ID:** `{place_id}`\n• **Jugadores:** `{player_count}/50`\n• **Detectado por:** `{player_name}`",
            inline=True
        )
        
        embed.add_field(
            name="⚡ **ACCESO RÁPIDO**",
            value=f"[🔗 **CLICK AQUÍ PARA UNIRTE**]({server_link})\n\n🚀 **¡VE RÁPIDO!**",
            inline=True
        )
        
        embed.add_field(
            name="🏆 **¿QUÉ HACER?**",
            value="• Click en el enlace de arriba\n• Únete al servidor inmediatamente\n• Busca los modelos listados\n• ¡Consigue tu Brainrot God!",
            inline=False
        )
        
        embed.set_footer(
            text=f"🕐 Detectado el {datetime.now().strftime('%H:%M:%S')} | Sistema automático RbxServers",
            icon_url="https://cdn.discordapp.com/emojis/1396087763388072006.png"
        )
        
        embed.set_thumbnail(url="https://tr.rbxcdn.com/180DAY-7bf01e1bb77441b8a2a99b92e7b3b4e7/768/432/Image/Png/noFilter")
        
        # Enviar alerta con @everyone
        await channel.send(
            content="@everyone 🚨 **¡ALERTA MÁXIMA DE BRAINROT GOD!** 🚨", 
            embed=embed
        )
        
        logger.info(f"🧠 Alerta de Brainrot enviada exitosamente al canal {channel.name}")
        
        return web.json_response({
            'status': 'success',
            'message': 'Alert sent successfully',
            'channel': channel.name,
            'models_count': len(found_models)
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
