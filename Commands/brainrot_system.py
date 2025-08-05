
"""
Sistema de Brainrot - Comando owner only para gestionar información de brainrot
Incluye API para recibir datos externos y comando para configurar canal
"""
import discord
from discord.ext import commands
import logging
import json
import os
from datetime import datetime
from aiohttp import web

logger = logging.getLogger(__name__)

# Owner ID
DISCORD_OWNER_ID = "916070251895091241"

# Archivo para guardar configuración y datos
BRAINROT_CONFIG_FILE = "brainrot_data.json"

def load_brainrot_data():
    """Cargar datos de brainrot desde archivo"""
    try:
        if os.path.exists(BRAINROT_CONFIG_FILE):
            with open(BRAINROT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"channels": {}, "alerts": []}
    except Exception as e:
        logger.error(f"Error cargando datos de brainrot: {e}")
        return {"channels": {}, "alerts": []}

def save_brainrot_data(data):
    """Guardar datos de brainrot en archivo"""
    try:
        with open(BRAINROT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error guardando datos de brainrot: {e}")
        return False

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
            
            # Cargar datos actuales
            brainrot_data = load_brainrot_data()
            
            # Guardar configuración del canal
            server_id = str(interaction.guild.id)
            brainrot_data["channels"][server_id] = {
                "channel_id": canal.id,
                "channel_name": canal.name,
                "guild_name": interaction.guild.name,
                "configured_at": datetime.now().isoformat(),
                "configured_by": user_id
            }
            
            # Guardar datos
            if save_brainrot_data(brainrot_data):
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
                    title="<:1000182751:1396420551798558781> Canal de Brainrot Configurado",
                    description="Este canal ha sido configurado para recibir alertas de **brainrot** a través de la API.",
                    color=0x2b2d31
                )
                test_embed.add_field(
                    name="<:verify:1396087763388072006> **Estado**",
                    value="**ACTIVO** - Esperando datos de la API",
                    inline=False
                )
                
                await canal.send(embed=test_embed)
                
                logger.info(f"🧠 Canal de brainrot configurado: {canal.name} (ID: {canal.id})")
                
            else:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Error",
                    description="No se pudo guardar la configuración del canal.",
                    color=0x2b2d31
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error configurando canal de brainrot: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al configurar el canal de brainrot.",
                color=0x2b2d31
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

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
        
        # Cargar datos de configuración
        brainrot_data = load_brainrot_data()
        
        # Crear registro de alerta
        alert_data = {
            "jobid": data.get('jobid'),
            "players": data.get('players'),
            "brainrot_name": data.get('brainrot_name'),
            "timestamp": datetime.now().isoformat(),
            "processed": False
        }
        
        # Agregar a la lista de alertas
        if "alerts" not in brainrot_data:
            brainrot_data["alerts"] = []
        brainrot_data["alerts"].append(alert_data)
        
        # Guardar datos actualizados
        save_brainrot_data(brainrot_data)
        
        # Enviar alertas a todos los canales configurados
        alerts_sent = 0
        for server_id, config in brainrot_data.get("channels", {}).items():
            try:
                channel_id = config.get("channel_id")
                channel = bot.get_channel(channel_id)
                
                if channel:
                    # Crear embed con la información recibida
                    embed = discord.Embed(
                        title="<:1000182751:1396420551798558781> Nueva Alerta de Brainrot",
                        description="Se ha detectado nueva información de brainrot.",
                        color=0x2b2d31
                    )
                    
                    embed.add_field(
                        name="<:1000182584:1396049547838492672> **Job ID**",
                        value=f"`{alert_data['jobid']}`",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="<:1000182614:1396049500375875646> **Jugadores**",
                        value=f"`{alert_data['players']}`",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="<:1000182751:1396420551798558781> **Nombre Brainrot**",
                        value=f"`{alert_data['brainrot_name']}`",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="<:1000182657:1396060091366637669> **Información**",
                        value=f"• **Detectado:** {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n• **Canal:** {channel.mention}\n• **Servidor:** {channel.guild.name}",
                        inline=False
                    )
                    
                    embed.set_footer(text="Sistema de Brainrot - RbxServers")
                    
                    # Enviar mensaje
                    await channel.send(embed=embed)
                    alerts_sent += 1
                    logger.info(f"🧠 Alerta enviada al canal {channel.name} en {channel.guild.name}")
                    
                else:
                    logger.warning(f"🧠 Canal no encontrado: {channel_id}")
                    
            except Exception as e:
                logger.error(f"🧠 Error enviando alerta al canal {channel_id}: {e}")
        
        # Marcar alerta como procesada
        alert_data["processed"] = True
        save_brainrot_data(brainrot_data)
        
        return web.json_response({
            'status': 'success',
            'message': 'Brainrot alert processed successfully',
            'jobid': alert_data['jobid'],
            'alerts_sent': alerts_sent,
            'timestamp': alert_data['timestamp']
        })
        
    except Exception as e:
        logger.error(f"🧠 Error procesando API de brainrot: {e}")
        return web.json_response({'error': str(e)}, status=500)

def setup_brainrot_api(app):
    """Configurar endpoint de la API de brainrot"""
    app.router.add_post('/api/brainrot', handle_brainrot_api)
    app.router.add_options('/api/brainrot', lambda r: web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    ))
    logger.info("🧠 API de brainrot configurada en /api/brainrot")
