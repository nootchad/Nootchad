
"""
Comandos de sugerencias y reportes para RbxServers
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ID del servidor específico donde funcionan los comandos
ALLOWED_GUILD_ID = 1062854351350132797  # ID del servidor https://discord.gg/DtFDSjn2
REPORT_CHANNEL_NAME = "revisar reportes"

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="sugerencia", description="Envía una sugerencia para mejorar el bot")
    async def sugerencia_command(interaction: discord.Interaction, sugerencia: str):
        """Comando para enviar sugerencias"""
        try:
            # Verificar que el comando se use en el servidor correcto
            if not interaction.guild or interaction.guild.id != ALLOWED_GUILD_ID:
                embed = discord.Embed(
                    title="Servidor Incorrecto",
                    description="Este comando solo funciona en el servidor oficial de RbxServers.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="Servidor oficial",
                    value="https://discord.gg/DtFDSjn2",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            user = interaction.user
            username = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
            
            logger.info(f"Sugerencia de {username} (ID: {user.id}): {sugerencia[:100]}...")
            
            # Buscar el canal de reportes
            report_channel = None
            for channel in interaction.guild.text_channels:
                if channel.name.lower() == REPORT_CHANNEL_NAME.lower():
                    report_channel = channel
                    break
            
            if not report_channel:
                embed = discord.Embed(
                    title="Error de Configuración",
                    description=f"No se encontró el canal '{REPORT_CHANNEL_NAME}' en este servidor.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Crear embed de sugerencia
            suggestion_embed = discord.Embed(
                title="Nueva Sugerencia",
                description=sugerencia,
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            suggestion_embed.add_field(
                name="Usuario",
                value=f"{user.mention} ({username})",
                inline=True
            )
            
            suggestion_embed.add_field(
                name="ID del Usuario",
                value=f"`{user.id}`",
                inline=True
            )
            
            suggestion_embed.add_field(
                name="Canal",
                value=f"{interaction.channel.mention}",
                inline=True
            )
            
            suggestion_embed.set_thumbnail(url=user.display_avatar.url)
            suggestion_embed.set_footer(text="Sistema de Sugerencias RbxServers", icon_url=bot.user.display_avatar.url)
            
            # Enviar al canal de reportes
            await report_channel.send(embed=suggestion_embed)
            
            # Confirmar al usuario
            confirmation_embed = discord.Embed(
                title="Sugerencia Enviada",
                description="Tu sugerencia ha sido enviada al equipo de staff exitosamente.",
                color=0x00ff88
            )
            confirmation_embed.add_field(
                name="Tu sugerencia",
                value=f"```{sugerencia[:1000]}{'...' if len(sugerencia) > 1000 else ''}```",
                inline=False
            )
            confirmation_embed.add_field(
                name="¿Qué pasa ahora?",
                value="El equipo de staff revisará tu sugerencia y la considerará para futuras actualizaciones del bot.",
                inline=False
            )
            
            await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando /sugerencia: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="Ocurrió un error al procesar tu sugerencia. Inténtalo nuevamente.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    @bot.tree.command(name="report", description="Reporta un problema, bug o comportamiento inapropiado")
    async def report_command(interaction: discord.Interaction, reporte: str, imagen: discord.Attachment = None):
        """Comando para enviar reportes con imagen opcional"""
        try:
            # Verificar que el comando se use en el servidor correcto
            if not interaction.guild or interaction.guild.id != ALLOWED_GUILD_ID:
                embed = discord.Embed(
                    title="Servidor Incorrecto",
                    description="Este comando solo funciona en el servidor oficial de RbxServers.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="Servidor oficial",
                    value="https://discord.gg/DtFDSjn2",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            user = interaction.user
            username = f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
            
            logger.info(f"Reporte de {username} (ID: {user.id}): {reporte[:100]}...")
            
            # Buscar el canal de reportes
            report_channel = None
            for channel in interaction.guild.text_channels:
                if channel.name.lower() == REPORT_CHANNEL_NAME.lower():
                    report_channel = channel
                    break
            
            if not report_channel:
                embed = discord.Embed(
                    title="Error de Configuración",
                    description=f"No se encontró el canal '{REPORT_CHANNEL_NAME}' en este servidor.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Validar imagen si se proporciona
            image_url = None
            if imagen:
                # Verificar que sea una imagen
                if imagen.content_type and imagen.content_type.startswith('image/'):
                    # Verificar tamaño (máximo 8MB)
                    if imagen.size <= 8 * 1024 * 1024:
                        image_url = imagen.url
                    else:
                        embed = discord.Embed(
                            title="Imagen Muy Grande",
                            description="La imagen debe ser menor a 8MB.",
                            color=0xff0000
                        )
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                else:
                    embed = discord.Embed(
                        title="Archivo Inválido",
                        description="Solo se permiten archivos de imagen (PNG, JPG, GIF, etc.).",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            
            # Crear embed de reporte
            report_embed = discord.Embed(
                title="Nuevo Reporte",
                description=reporte,
                color=0xff4444,
                timestamp=datetime.now()
            )
            
            report_embed.add_field(
                name="Usuario",
                value=f"{user.mention} ({username})",
                inline=True
            )
            
            report_embed.add_field(
                name="ID del Usuario",
                value=f"`{user.id}`",
                inline=True
            )
            
            report_embed.add_field(
                name="Canal",
                value=f"{interaction.channel.mention}",
                inline=True
            )
            
            # Agregar imagen si se proporcionó
            if image_url:
                report_embed.set_image(url=image_url)
                report_embed.add_field(
                    name="Evidencia",
                    value="Imagen adjunta abajo",
                    inline=False
                )
            
            report_embed.set_thumbnail(url=user.display_avatar.url)
            report_embed.set_footer(text="Sistema de Reportes RbxServers", icon_url=bot.user.display_avatar.url)
            
            # Enviar al canal de reportes
            await report_channel.send(embed=report_embed)
            
            # Confirmar al usuario
            confirmation_embed = discord.Embed(
                title="Reporte Enviado",
                description="Tu reporte ha sido enviado al equipo de staff exitosamente.",
                color=0x00ff88
            )
            confirmation_embed.add_field(
                name="Tu reporte",
                value=f"```{reporte[:1000]}{'...' if len(reporte) > 1000 else ''}```",
                inline=False
            )
            if imagen:
                confirmation_embed.add_field(
                    name="Imagen",
                    value="✅ Imagen adjunta incluida",
                    inline=True
                )
            confirmation_embed.add_field(
                name="¿Qué pasa ahora?",
                value="El equipo de staff revisará tu reporte y tomará las medidas necesarias.",
                inline=False
            )
            
            await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando /report: {e}")
            error_embed = discord.Embed(
                title="Error",
                description="Ocurrió un error al procesar tu reporte. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comandos /sugerencia y /report configurados")
    return True

def cleanup_commands(bot):
    """Función opcional para limpieza"""
    pass
