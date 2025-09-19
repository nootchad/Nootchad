
"""
Comando /anuncio - Owner only
Permite enviar anuncios a todos los usuarios verificados del bot
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# ID del owner principal
DISCORD_OWNER_ID = "916070251895091241"

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    
    @bot.tree.command(name="anuncio", description="[OWNER ONLY] Enviar anuncio a todos los usuarios verificados")
    @discord.app_commands.describe(
        texto="El texto del anuncio que se enviará a todos los usuarios verificados"
    )
    async def anuncio_command(interaction: discord.Interaction, texto: str):
        # Verificar que solo el owner puede usar este comando
        if str(interaction.user.id) != DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando es solo para el owner del bot.",
                color=0xff4444
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Responder inmediatamente para evitar timeout
            embed_inicial = discord.Embed(
                title="📢 Enviando Anuncio...",
                description="Procesando envío a usuarios verificados...",
                color=0xffaa00
            )
            await interaction.response.send_message(embed=embed_inicial, ephemeral=True)

            # Obtener usuarios verificados
            usuarios_verificados = await obtener_usuarios_verificados()
            
            if not usuarios_verificados:
                embed_error = discord.Embed(
                    title="⚠️ Sin Usuarios",
                    description="No se encontraron usuarios verificados.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed_error, ephemeral=True)
                return

            # Crear embed del anuncio
            embed_anuncio = discord.Embed(
                title="📢 Anuncio Oficial - RbxServers",
                description=texto,
                color=0x7289da,
                timestamp=datetime.now()
            )
            
            embed_anuncio.add_field(
                name="<:1000182614:1396049500375875646> Enviado por",
                value=f"{interaction.user.mention} (Owner)",
                inline=True
            )
            
            embed_anuncio.add_field(
                name="🕐 Fecha",
                value=f"<t:{int(time.time())}:F>",
                inline=True
            )
            
            embed_anuncio.set_footer(
                text="RbxServers Bot • Anuncio Oficial",
                icon_url="https://rbxservers.xyz/svgs/roblox.svg"
            )

            # Enviar a usuarios verificados
            exitosos = 0
            fallidos = 0
            usuarios_procesados = []

            for discord_id, usuario_data in usuarios_verificados.items():
                try:
                    user = bot.get_user(int(discord_id))
                    if not user:
                        user = await bot.fetch_user(int(discord_id))
                    
                    if user:
                        await user.send(embed=embed_anuncio)
                        exitosos += 1
                        usuarios_procesados.append({
                            'discord_id': discord_id,
                            'username': str(user),
                            'roblox_username': usuario_data.get('roblox_username', 'Unknown'),
                            'status': 'enviado'
                        })
                        logger.info(f"📢 Anuncio enviado a {user} (ID: {discord_id})")
                        
                        # Pequeña pausa para evitar rate limits
                        await asyncio.sleep(0.5)
                    else:
                        fallidos += 1
                        usuarios_procesados.append({
                            'discord_id': discord_id,
                            'username': 'Usuario no encontrado',
                            'roblox_username': usuario_data.get('roblox_username', 'Unknown'),
                            'status': 'fallido'
                        })
                        
                except Exception as e:
                    fallidos += 1
                    usuarios_procesados.append({
                        'discord_id': discord_id,
                        'username': f'Error: {str(e)[:50]}',
                        'roblox_username': usuario_data.get('roblox_username', 'Unknown'),
                        'status': 'error'
                    })
                    logger.error(f"❌ Error enviando anuncio a {discord_id}: {e}")

            # Guardar log del anuncio
            await guardar_log_anuncio(interaction.user, texto, usuarios_procesados, exitosos, fallidos)

            # Embed de resultado final
            embed_resultado = discord.Embed(
                title="<a:verify2:1418486831993061497> Anuncio Enviado",
                description="El anuncio ha sido procesado y enviado.",
                color=0x00ff88
            )
            
            embed_resultado.add_field(
                name="<:stats:1418490788437823599> Estadísticas",
                value=f"**Exitosos:** {exitosos}\n**Fallidos:** {fallidos}\n**Total:** {len(usuarios_verificados)}",
                inline=True
            )
            
            embed_resultado.add_field(
                name="📝 Contenido",
                value=f"```{texto[:100]}{'...' if len(texto) > 100 else ''}```",
                inline=False
            )
            
            embed_resultado.add_field(
                name="🕐 Proceso completado",
                value=f"<t:{int(time.time())}:R>",
                inline=True
            )

            await interaction.followup.send(embed=embed_resultado, ephemeral=True)
            
            logger.info(f"📢 Anuncio completado por {interaction.user}: {exitosos} exitosos, {fallidos} fallidos")

        except Exception as e:
            logger.error(f"❌ Error crítico en comando anuncio: {e}")
            
            embed_error = discord.Embed(
                title="❌ Error Crítico",
                description=f"Ocurrió un error procesando el anuncio:\n```{str(e)[:200]}```",
                color=0xff4444
            )
            
            try:
                await interaction.followup.send(embed=embed_error, ephemeral=True)
            except:
                # Si ya no podemos responder al interaction, intentar enviar DM al owner
                try:
                    owner = bot.get_user(int(DISCORD_OWNER_ID))
                    if owner:
                        await owner.send(embed=embed_error)
                except:
                    pass

    # Comando adicional para ver estadísticas de anuncios
    @bot.tree.command(name="anuncios_stats", description="[OWNER ONLY] Ver estadísticas de anuncios enviados")
    async def anuncios_stats_command(interaction: discord.Interaction):
        # Verificar owner
        if str(interaction.user.id) != DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando es solo para el owner del bot.",
                color=0xff4444
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Cargar logs de anuncios
            logs = await cargar_logs_anuncios()
            
            if not logs:
                embed = discord.Embed(
                    title="<:stats:1418490788437823599> Estadísticas de Anuncios",
                    description="No hay anuncios registrados aún.",
                    color=0xff9900
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Calcular estadísticas
            total_anuncios = len(logs)
            total_enviados = sum(log.get('exitosos', 0) for log in logs)
            total_fallidos = sum(log.get('fallidos', 0) for log in logs)
            ultimo_anuncio = logs[-1] if logs else None

            embed = discord.Embed(
                title="<:stats:1418490788437823599> Estadísticas de Anuncios",
                description="Resumen de anuncios enviados por el bot",
                color=0x7289da
            )
            
            embed.add_field(
                name="📈 Totales",
                value=f"**Anuncios enviados:** {total_anuncios}\n**Mensajes exitosos:** {total_enviados}\n**Mensajes fallidos:** {total_fallidos}",
                inline=True
            )
            
            if ultimo_anuncio:
                embed.add_field(
                    name="📅 Último Anuncio",
                    value=f"**Fecha:** {ultimo_anuncio.get('timestamp', 'Unknown')}\n**Exitosos:** {ultimo_anuncio.get('exitosos', 0)}\n**Fallidos:** {ultimo_anuncio.get('fallidos', 0)}",
                    inline=True
                )
                
                embed.add_field(
                    name="📝 Último Contenido",
                    value=f"```{ultimo_anuncio.get('texto', 'No disponible')[:100]}{'...' if len(ultimo_anuncio.get('texto', '')) > 100 else ''}```",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error en anuncios_stats: {e}")
            embed_error = discord.Embed(
                title="❌ Error",
                description=f"Error obteniendo estadísticas: {str(e)}",
                color=0xff4444
            )
            await interaction.response.send_message(embed=embed_error, ephemeral=True)
    
    logger.info("<a:verify2:1418486831993061497> Comandos de anuncios configurados exitosamente")
    return True

async def obtener_usuarios_verificados():
    """Obtener lista de usuarios verificados desde followers.json"""
    try:
        followers_file = Path("followers.json")
        if not followers_file.exists():
            logger.warning("⚠️ Archivo followers.json no encontrado")
            return {}
        
        with open(followers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            usuarios_verificados = data.get('verified_users', {})
            logger.info(f"📊 Cargados {len(usuarios_verificados)} usuarios verificados")
            return usuarios_verificados
            
    except Exception as e:
        logger.error(f"❌ Error cargando usuarios verificados: {e}")
        return {}

async def guardar_log_anuncio(autor, texto, usuarios_procesados, exitosos, fallidos):
    """Guardar log del anuncio enviado"""
    try:
        log_file = Path("anuncios_log.json")
        
        # Cargar logs existentes
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []
        
        # Crear nuevo log
        nuevo_log = {
            'timestamp': datetime.now().isoformat(),
            'autor': {
                'id': str(autor.id),
                'username': str(autor),
                'display_name': autor.display_name
            },
            'texto': texto,
            'estadisticas': {
                'exitosos': exitosos,
                'fallidos': fallidos,
                'total': len(usuarios_procesados)
            },
            'usuarios_procesados': usuarios_procesados[:50]  # Guardar solo los primeros 50 para evitar archivos muy grandes
        }
        
        logs.append(nuevo_log)
        
        # Mantener solo los últimos 20 anuncios
        if len(logs) > 20:
            logs = logs[-20:]
        
        # Guardar archivo
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📝 Log de anuncio guardado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error guardando log de anuncio: {e}")

async def cargar_logs_anuncios():
    """Cargar logs de anuncios"""
    try:
        log_file = Path("anuncios_log.json")
        if not log_file.exists():
            return []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            return logs
            
    except Exception as e:
        logger.error(f"❌ Error cargando logs de anuncios: {e}")
        return []

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    logger.info("🧹 Limpieza de comandos de anuncios completada")
