
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
REPORT_CHANNEL_NAME = "╭📋・revisar・reportes"

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
                if channel.name == REPORT_CHANNEL_NAME:
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
    
    @bot.tree.command(name="reportar", description="Reporta cualquier problema, bug o comportamiento inapropiado")
    async def reportar_command(interaction: discord.Interaction, que_reportas: str, imagen: discord.Attachment = None):
        """Comando para enviar reportes - SOLO se envía al canal, NO se guarda en archivos"""
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
            
            logger.info(f"Reporte de {username} (ID: {user.id}): {que_reportas[:100]}...")
            
            # Buscar el canal de reportes exacto
            report_channel = None
            for channel in interaction.guild.text_channels:
                if channel.name == REPORT_CHANNEL_NAME:
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
            
            # Crear embed de reporte para enviar al canal del staff
            report_embed = discord.Embed(
                title="Nuevo Reporte Recibido",
                description=que_reportas,
                color=0x5c5c5c,
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
                name="Canal de Origen",
                value=f"{interaction.channel.mention}",
                inline=True
            )
            
            report_embed.add_field(
                name="Servidor",
                value=f"{interaction.guild.name}",
                inline=True
            )
            
            report_embed.add_field(
                name="Fecha y Hora",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            
            # Agregar imagen si se proporcionó
            if image_url:
                report_embed.set_image(url=image_url)
                report_embed.add_field(
                    name="Evidencia Adjunta",
                    value="Imagen incluida abajo",
                    inline=False
                )
            
            report_embed.set_thumbnail(url=user.display_avatar.url)
            report_embed.set_footer(text="Sistema de Reportes RbxServers", icon_url=bot.user.display_avatar.url)
            
            # ENVIAR AL CANAL DE REPORTES (STAFF) - NO GUARDAR EN ARCHIVOS
            try:
                # Verificar que el bot tenga permisos para enviar mensajes en el canal
                if not report_channel.permissions_for(interaction.guild.me).send_messages:
                    raise Exception("Sin permisos para enviar mensajes en el canal")
                
                # Enviar el reporte al canal
                await report_channel.send(embed=report_embed)
                logger.info(f"✅ Reporte enviado exitosamente al canal {report_channel.name}")
                
            except Exception as channel_error:
                logger.error(f"❌ Error enviando al canal {report_channel.name}: {channel_error}")
                embed = discord.Embed(
                    title="❌ Error Enviando Reporte",
                    description=f"No se pudo enviar el reporte al canal del staff. Error: {str(channel_error)[:100]}",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Posibles causas:",
                    value="• El canal no existe\n• El bot no tiene permisos\n• Problema de conexión",
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Confirmar al usuario (respuesta privada)
            confirmation_embed = discord.Embed(
                title="✅ Reporte Enviado Exitosamente",
                description=f"Tu reporte ha sido enviado al canal {REPORT_CHANNEL_NAME} para revisión del staff.",
                color=0x00ff88
            )
            confirmation_embed.add_field(
                name="Tu reporte",
                value=f"```{que_reportas[:1000]}{'...' if len(que_reportas) > 1000 else ''}```",
                inline=False
            )
            if imagen:
                confirmation_embed.add_field(
                    name="Imagen",
                    value="✅ Imagen adjunta incluida",
                    inline=True
                )
            confirmation_embed.add_field(
                name="¿Qué sigue?",
                value="El equipo de staff revisará tu reporte y tomará las medidas necesarias.",
                inline=False
            )
            confirmation_embed.add_field(
                name="Canal de Destino",
                value=f"{REPORT_CHANNEL_NAME} (Solo Staff)",
                inline=False
            )
            
            await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error en comando /report: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            error_embed = discord.Embed(
                title="Error Procesando Reporte",
                description="Ocurrió un error al procesar tu reporte. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            except Exception as response_error:
                logger.error(f"❌ Error enviando respuesta de error: {response_error}")
    
    logger.info("✅ Comandos /sugerencia y /reportar configurados")
    return True

def cleanup_commands(bot):
    """Función opcional para limpieza"""
    pass
