
"""
Comandos /sugerencia y /report para el bot RbxServers
Solo funcionan en el servidor específico: https://discord.gg/DtFDSjn2
"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

# ID del servidor donde deben funcionar los comandos
SERVIDOR_PERMITIDO_ID = 1180659749509578773  # ID del servidor de Discord

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    
    @bot.tree.command(name="sugerencia", description="Envía una sugerencia al equipo de staff")
    async def sugerencia_command(interaction: discord.Interaction, sugerencia: str):
        """Comando para enviar sugerencias al canal de staff"""
        try:
            # Verificar que esté en el servidor correcto
            if not interaction.guild or interaction.guild.id != SERVIDOR_PERMITIDO_ID:
                embed = discord.Embed(
                    title="❌ Servidor No Permitido",
                    description="Este comando solo funciona en el servidor oficial de RbxServers.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Buscar el canal "revisar reportes"
            canal_staff = None
            for channel in interaction.guild.channels:
                if channel.name.lower() == "revisar reportes" or "revisar reportes" in channel.name.lower():
                    canal_staff = channel
                    break
            
            if not canal_staff:
                embed = discord.Embed(
                    title="❌ Canal No Encontrado",
                    description="No se pudo encontrar el canal 'revisar reportes'.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Crear embed para la sugerencia
            embed_sugerencia = discord.Embed(
                title="💡 Nueva Sugerencia",
                description=sugerencia,
                color=0x00ff88,
                timestamp=interaction.created_at
            )
            embed_sugerencia.add_field(
                name="👤 Usuario",
                value=f"{interaction.user.mention} ({interaction.user.name}#{interaction.user.discriminator})",
                inline=True
            )
            embed_sugerencia.add_field(
                name="🆔 ID de Usuario",
                value=f"`{interaction.user.id}`",
                inline=True
            )
            embed_sugerencia.add_field(
                name="📅 Fecha",
                value=f"<t:{int(interaction.created_at.timestamp())}:F>",
                inline=True
            )
            embed_sugerencia.set_thumbnail(url=interaction.user.display_avatar.url)
            embed_sugerencia.set_footer(text="Sistema de Sugerencias RbxServers")
            
            # Enviar al canal de staff
            await canal_staff.send(embed=embed_sugerencia)
            
            # Confirmar al usuario
            embed_confirmacion = discord.Embed(
                title="✅ Sugerencia Enviada",
                description="Tu sugerencia ha sido enviada al equipo de staff. ¡Gracias por tu aporte!",
                color=0x00ff88
            )
            embed_confirmacion.add_field(
                name="📝 Tu sugerencia:",
                value=f"```{sugerencia[:900]}{'...' if len(sugerencia) > 900 else ''}```",
                inline=False
            )
            await interaction.response.send_message(embed=embed_confirmacion, ephemeral=True)
            
            logger.info(f"Sugerencia enviada por {interaction.user.name} (ID: {interaction.user.id})")
            
        except Exception as e:
            logger.error(f"Error en comando sugerencia: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al procesar tu sugerencia. Intenta nuevamente.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="report", description="Reporta un problema o usuario al equipo de staff")
    async def report_command(interaction: discord.Interaction, reporte: str, imagen: discord.Attachment = None):
        """Comando para enviar reportes al canal de staff"""
        try:
            # Verificar que esté en el servidor correcto
            if not interaction.guild or interaction.guild.id != SERVIDOR_PERMITIDO_ID:
                embed = discord.Embed(
                    title="❌ Servidor No Permitido",
                    description="Este comando solo funciona en el servidor oficial de RbxServers.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Buscar el canal "revisar reportes"
            canal_staff = None
            for channel in interaction.guild.channels:
                if channel.name.lower() == "revisar reportes" or "revisar reportes" in channel.name.lower():
                    canal_staff = channel
                    break
            
            if not canal_staff:
                embed = discord.Embed(
                    title="❌ Canal No Encontrado",
                    description="No se pudo encontrar el canal 'revisar reportes'.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Crear embed para el reporte
            embed_reporte = discord.Embed(
                title="🚨 Nuevo Reporte",
                description=reporte,
                color=0xff4444,
                timestamp=interaction.created_at
            )
            embed_reporte.add_field(
                name="👤 Reportado por",
                value=f"{interaction.user.mention} ({interaction.user.name}#{interaction.user.discriminator})",
                inline=True
            )
            embed_reporte.add_field(
                name="🆔 ID de Usuario",
                value=f"`{interaction.user.id}`",
                inline=True
            )
            embed_reporte.add_field(
                name="📅 Fecha",
                value=f"<t:{int(interaction.created_at.timestamp())}:F>",
                inline=True
            )
            
            # Si hay imagen adjunta
            if imagen:
                # Validar que sea una imagen
                if imagen.content_type and imagen.content_type.startswith('image/'):
                    embed_reporte.set_image(url=imagen.url)
                    embed_reporte.add_field(
                        name="📎 Imagen Adjunta",
                        value=f"[Ver imagen]({imagen.url})",
                        inline=False
                    )
                else:
                    embed_reporte.add_field(
                        name="⚠️ Archivo Adjunto",
                        value=f"Archivo no válido (no es imagen): {imagen.filename}",
                        inline=False
                    )
            
            embed_reporte.set_thumbnail(url=interaction.user.display_avatar.url)
            embed_reporte.set_footer(text="Sistema de Reportes RbxServers")
            
            # Enviar al canal de staff
            mensaje_staff = await canal_staff.send(embed=embed_reporte)
            
            # Agregar reacciones para que el staff pueda actuar
            await mensaje_staff.add_reaction("✅")  # Reporte revisado
            await mensaje_staff.add_reaction("❌")  # Reporte rechazado
            await mensaje_staff.add_reaction("🔍")  # Reporte en investigación
            
            # Confirmar al usuario
            embed_confirmacion = discord.Embed(
                title="✅ Reporte Enviado",
                description="Tu reporte ha sido enviado al equipo de staff. Será revisado lo antes posible.",
                color=0x00ff88
            )
            embed_confirmacion.add_field(
                name="📝 Tu reporte:",
                value=f"```{reporte[:900]}{'...' if len(reporte) > 900 else ''}```",
                inline=False
            )
            if imagen:
                embed_confirmacion.add_field(
                    name="📎 Imagen:",
                    value="Imagen adjunta correctamente" if imagen.content_type and imagen.content_type.startswith('image/') else "Archivo adjunto (no es imagen válida)",
                    inline=False
                )
            embed_confirmacion.add_field(
                name="⏰ Tiempo estimado de respuesta:",
                value="24-48 horas",
                inline=False
            )
            await interaction.response.send_message(embed=embed_confirmacion, ephemeral=True)
            
            logger.info(f"Reporte enviado por {interaction.user.name} (ID: {interaction.user.id}) con imagen: {imagen is not None}")
            
        except Exception as e:
            logger.error(f"Error en comando report: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al procesar tu reporte. Intenta nuevamente.",
                color=0xff0000
            )
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
    
    logger.info("✅ Comandos de sugerencias y reportes configurados")
    return True

# Función opcional de limpieza cuando se recarga el módulo
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
