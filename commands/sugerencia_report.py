
"""
Comandos de sugerencias y reportes para RbxServers
Funciona únicamente en el servidor específico de Discord
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime
import aiohttp
import io

logger = logging.getLogger(__name__)

# ID del servidor autorizado (Discord Guild ID)
AUTHORIZED_GUILD_ID = 1071851768073035859  # Servidor de https://discord.gg/DtFDSjn2

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    
    async def check_authorized_server(interaction: discord.Interaction) -> bool:
        """Verificar que el comando se ejecute en el servidor autorizado"""
        if not interaction.guild or interaction.guild.id != AUTHORIZED_GUILD_ID:
            embed = discord.Embed(
                title="❌ Servidor No Autorizado",
                description="Este comando solo puede ser usado en el servidor oficial de RbxServers.",
                color=0xff0000
            )
            embed.add_field(
                name="🔗 Servidor Oficial",
                value="[Únete aquí](https://discord.gg/DtFDSjn2)",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    
    async def get_review_channel(guild: discord.Guild):
        """Buscar el canal 'revisar reportes'"""
        # Buscar por nombre exacto primero
        channel = discord.utils.get(guild.channels, name="revisar reportes")
        if channel:
            return channel
        
        # Buscar por nombres similares
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                channel_name = channel.name.lower()
                if any(keyword in channel_name for keyword in ["revisar", "report", "reporte"]):
                    return channel
        
        return None
    
    @bot.tree.command(name="sugerencia", description="Enviar una sugerencia para mejorar el bot")
    async def sugerencia_command(interaction: discord.Interaction, sugerencia: str, imagen: discord.Attachment = None):
        """Comando para enviar sugerencias"""
        # Verificar servidor autorizado
        if not await check_authorized_server(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Buscar canal de revisión
            review_channel = await get_review_channel(interaction.guild)
            if not review_channel:
                embed = discord.Embed(
                    title="❌ Canal No Encontrado",
                    description="No se pudo encontrar el canal 'revisar reportes'. Contacta a un administrador.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed para la sugerencia
            embed = discord.Embed(
                title="💡 Nueva Sugerencia",
                description=sugerencia,
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Usuario",
                value=f"{interaction.user.mention} ({interaction.user.id})",
                inline=True
            )
            
            embed.add_field(
                name="📅 Fecha",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="📍 Canal",
                value=f"{interaction.channel.mention}",
                inline=True
            )
            
            embed.set_footer(text="Tipo: Sugerencia • RbxServers")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Preparar archivos si hay imagen
            files = []
            if imagen:
                try:
                    # Descargar la imagen
                    async with aiohttp.ClientSession() as session:
                        async with session.get(imagen.url) as resp:
                            if resp.status == 200:
                                image_data = await resp.read()
                                file = discord.File(io.BytesIO(image_data), filename=imagen.filename)
                                files.append(file)
                                embed.set_image(url=f"attachment://{imagen.filename}")
                except Exception as e:
                    logger.warning(f"Error procesando imagen de sugerencia: {e}")
            
            # Enviar al canal de revisión
            message = await review_channel.send(embed=embed, files=files)
            
            # Agregar reacciones para votación
            await message.add_reaction("👍")  # A favor
            await message.add_reaction("👎")  # En contra
            await message.add_reaction("🤔")  # Neutral/En consideración
            
            # Responder al usuario
            success_embed = discord.Embed(
                title="✅ Sugerencia Enviada",
                description="Tu sugerencia ha sido enviada exitosamente al equipo de moderación.",
                color=0x00ff88
            )
            success_embed.add_field(
                name="📝 Tu sugerencia:",
                value=f"```{sugerencia[:500]}{'...' if len(sugerencia) > 500 else ''}```",
                inline=False
            )
            success_embed.add_field(
                name="⏰ Estado:",
                value="En revisión por el equipo",
                inline=True
            )
            success_embed.add_field(
                name="📍 Enviado a:",
                value=f"{review_channel.mention}",
                inline=True
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
            logger.info(f"Sugerencia enviada por {interaction.user.name} (ID: {interaction.user.id}): {sugerencia[:100]}...")
            
        except Exception as e:
            logger.error(f"Error en comando sugerencia: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al procesar tu sugerencia. Inténtalo nuevamente.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @bot.tree.command(name="report", description="Reportar un problema o comportamiento inapropiado")
    async def report_command(interaction: discord.Interaction, reporte: str, imagen: discord.Attachment = None):
        """Comando para enviar reportes"""
        # Verificar servidor autorizado
        if not await check_authorized_server(interaction):
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Buscar canal de revisión
            review_channel = await get_review_channel(interaction.guild)
            if not review_channel:
                embed = discord.Embed(
                    title="❌ Canal No Encontrado",
                    description="No se pudo encontrar el canal 'revisar reportes'. Contacta a un administrador.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed para el reporte
            embed = discord.Embed(
                title="🚨 Nuevo Reporte",
                description=reporte,
                color=0xff4444,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="👤 Reportado por",
                value=f"{interaction.user.mention} ({interaction.user.id})",
                inline=True
            )
            
            embed.add_field(
                name="📅 Fecha",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            embed.add_field(
                name="📍 Canal",
                value=f"{interaction.channel.mention}",
                inline=True
            )
            
            embed.add_field(
                name="🔍 Estado",
                value="⏳ Pendiente de revisión",
                inline=False
            )
            
            embed.set_footer(text="Tipo: Reporte • RbxServers")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Preparar archivos si hay imagen
            files = []
            if imagen:
                try:
                    # Descargar la imagen
                    async with aiohttp.ClientSession() as session:
                        async with session.get(imagen.url) as resp:
                            if resp.status == 200:
                                image_data = await resp.read()
                                file = discord.File(io.BytesIO(image_data), filename=imagen.filename)
                                files.append(file)
                                embed.set_image(url=f"attachment://{imagen.filename}")
                except Exception as e:
                    logger.warning(f"Error procesando imagen de reporte: {e}")
            
            # Enviar al canal de revisión
            message = await review_channel.send(embed=embed, files=files)
            
            # Agregar reacciones para manejo del reporte
            await message.add_reaction("✅")  # Resuelto
            await message.add_reaction("❌")  # Rechazado
            await message.add_reaction("⚠️")  # En investigación
            await message.add_reaction("📋")  # Requiere más información
            
            # Responder al usuario
            success_embed = discord.Embed(
                title="✅ Reporte Enviado",
                description="Tu reporte ha sido enviado exitosamente al equipo de moderación.",
                color=0x00ff88
            )
            success_embed.add_field(
                name="📝 Tu reporte:",
                value=f"```{reporte[:500]}{'...' if len(reporte) > 500 else ''}```",
                inline=False
            )
            success_embed.add_field(
                name="⏰ Estado:",
                value="En revisión por el equipo",
                inline=True
            )
            success_embed.add_field(
                name="📍 Enviado a:",
                value=f"{review_channel.mention}",
                inline=True
            )
            success_embed.add_field(
                name="💡 Información:",
                value="El equipo revisará tu reporte y tomará las medidas necesarias.",
                inline=False
            )
            
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
            logger.info(f"Reporte enviado por {interaction.user.name} (ID: {interaction.user.id}): {reporte[:100]}...")
            
        except Exception as e:
            logger.error(f"Error en comando report: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al procesar tu reporte. Inténtalo nuevamente.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comandos de sugerencias y reportes configurados")
    return True

# Función opcional de limpieza cuando se recarga el módulo
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
