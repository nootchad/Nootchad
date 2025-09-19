
"""
Comando /img2model - Convertir imagen a modelo de Roblox (deshabilitado)
"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="img2model", description="Convierte una imagen en un modelo de Roblox (actualmente deshabilitado)")
    async def img2model_command(interaction: discord.Interaction, image_url: str = None):
        """
        Convertir imagen a modelo de Roblox (función deshabilitada)
        
        Args:
            image_url: URL de la imagen a convertir (opcional)
        """
        from main import check_verification
        
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Comando deshabilitado por ahora
            embed = discord.Embed(
                title="🚧 Función Deshabilitada",
                description="El comando `/img2model` está actualmente deshabilitado mientras trabajamos en mejoras.",
                color=0xffaa00
            )
            
            embed.add_field(
                name="<a:foco:1418492184373755966> ¿Qué hace este comando?",
                value="Este comando convertirá imágenes en modelos 3D de Roblox usando tecnología de IA.",
                inline=False
            )
            
            embed.add_field(
                name="🔧 Estado Actual",
                value="• ⚙️ En desarrollo\n• 🧪 Probando nuevas tecnologías\n• 🎯 Optimizando resultados",
                inline=False
            )
            
            embed.add_field(
                name="📅 Disponibilidad",
                value="Esta función estará disponible en una futura actualización del bot.",
                inline=False
            )
            
            embed.add_field(
                name="<a:loading:1418504453580918856> Alternativas",
                value="• Usa `/asset render` para obtener modelos 3D existentes\n• Explora `/bundle_info` para bundles con modelos",
                inline=False
            )
            
            embed.set_footer(text="RbxServers • Función en Desarrollo")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando img2model: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error con el comando.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("<a:verify2:1418486831993061497> Comando /img2model (deshabilitado) configurado")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
