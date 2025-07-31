
"""
Comando para probar y mostrar información del sistema OAuth2 de Discord
"""
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    """
    
    @bot.tree.command(name="oauth2-info", description="[OWNER] Mostrar información del sistema OAuth2 de Discord")
    async def oauth2_info_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Solo el owner puede usar este comando
        DISCORD_OWNER_ID = "916070251895091241"
        if user_id != DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Importar sistema OAuth2
            from discord_oauth import discord_oauth
            
            # Generar URL de ejemplo
            auth_url, state = discord_oauth.generate_oauth_url()
            
            embed = discord.Embed(
                title="🔐 Información del Sistema OAuth2",
                description="Configuración actual del sistema de autenticación OAuth2 con Discord",
                color=0x7289da
            )
            
            embed.add_field(
                name="📋 Client ID",
                value=f"`{discord_oauth.client_id}`",
                inline=True
            )
            
            embed.add_field(
                name="🔗 Redirect URI",
                value=f"`{discord_oauth.redirect_uri}`",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Scopes",
                value=f"`{', '.join(discord_oauth.scopes)}`",
                inline=True
            )
            
            embed.add_field(
                name="🌐 Authorize URL",
                value=f"`{discord_oauth.authorize_url}`",
                inline=False
            )
            
            embed.add_field(
                name="🎫 Token URL",
                value=f"`{discord_oauth.token_url}`",
                inline=False
            )
            
            embed.add_field(
                name="🔗 URL de Prueba Generada",
                value=f"[Hacer clic para autorizar]({auth_url})",
                inline=False
            )
            
            embed.add_field(
                name="🔑 State de Ejemplo",
                value=f"`{state}`",
                inline=True
            )
            
            embed.add_field(
                name="✅ Estado",
                value="Sistema OAuth2 configurado correctamente",
                inline=True
            )
            
            embed.set_footer(text="RbxServers • Sistema OAuth2")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"Owner {interaction.user.name} consultó información OAuth2")
            
        except ImportError:
            embed = discord.Embed(
                title="❌ Sistema OAuth2 No Disponible",
                description="El sistema OAuth2 no está disponible o no se pudo importar.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando oauth2-info: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Ocurrió un error al obtener la información OAuth2: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    logger.info("✅ Comando OAuth2 info configurado")
    return True

# Función opcional de limpieza
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
