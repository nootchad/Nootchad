
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
        
        # Cargar configuración del canal
        config = load_brainrot_config()
        alerts_sent = 0
        
        if not config or not config.get('alert_channel_id'):
            logger.warning("🧠 No hay canal configurado para alertas de brainrot")
            return web.json_response({
                'status': 'error',
                'message': 'No brainrot channel configured',
                'suggestion': 'Use /brainrot command to configure a channel first'
            }, status=400)
        
        # Obtener canal configurado
        channel_id = config.get('alert_channel_id')
        channel = bot.get_channel(channel_id)
        
        if not channel:
            logger.error(f"🧠 Canal configurado no encontrado: {channel_id}")
            return web.json_response({
                'status': 'error',
                'message': f'Configured channel {channel_id} not found'
            }, status=404)
        
        # Crear embed de alerta
        embed = discord.Embed(
            title="<:1000182751:1396420551798558781> **Alerta de Brainrot Detectado**",
            description=f"Se ha detectado un **brainrot** en el sistema de monitoreo.",
            color=0x2b2d31,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="<:1000182584:1396049547838492672> **Información del Job**",
            value=f"• **Job ID:** `{data.get('jobid')}`\n• **Jugadores:** {data.get('players')}\n• **Nombre Brainrot:** {data.get('brainrot_name')}",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182657:1396060091366637669> **Información de Detección**",
            value=f"• **Detectado:** {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n• **Canal:** {channel.mention}\n• **Servidor:** {channel.guild.name}",
            inline=False
        )
        
        embed.set_footer(text="Sistema de Brainrot - RbxServers")
        
        # Enviar mensaje
        await channel.send(embed=embed)
        alerts_sent = 1
        logger.info(f"🧠 Alerta enviada al canal {channel.name} en {channel.guild.name}")
        
        # Guardar alerta en datos
        brainrot_data = load_brainrot_data()
        if "alerts" not in brainrot_data:
            brainrot_data["alerts"] = []
        
        alert_record = {
            "jobid": data.get('jobid'),
            "players": data.get('players'),
            "brainrot_name": data.get('brainrot_name'),
            "timestamp": datetime.now().isoformat(),
            "channel_id": channel_id,
            "processed": True
        }
        
        brainrot_data["alerts"].append(alert_record)
        save_brainrot_data(brainrot_data)
        
        return web.json_response({
            'status': 'success',
            'message': 'Brainrot alert processed successfully',
            'jobid': data.get('jobid'),
            'alerts_sent': alerts_sent,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"🧠 Error procesando API de brainrot: {e}")
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
            
            # Guardar configuración del canal
            config = {
                "alert_channel_id": canal.id,
                "guild_id": interaction.guild.id,
                "configured_at": datetime.now().isoformat(),
                "configured_by": user_id
            }
            
            # Guardar configuración
            if save_brainrot_config(config):
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Canal de Brainrot Configurado",
                    description=f"El canal {canal.mention} ha sido configurado para recibir alertas de **brainrot**.",
                    color=0x2b2d31
                )
                
                embed.add_field(
                    name="<:1000182584:1396049547838492672> **Configuración Activa**",
                    value=f"• **Canal:** {canal.mention}\n• **Servidor:** {interaction.guild.name}\n• **API Endpoint:** `/api/brainrot`",
                    inline=False
                )
                
                embed.add_field(
                    name="<:1000182751:1396420551798558781> **Datos Recibidos**",
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
