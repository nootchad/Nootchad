
<old_str>"""
Comando para probar y mostrar información del sistema OAuth2 de Discord
"""
import discord
from discord.ext import commands
import logging
import time

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
                name="<:portapapeles:1418506653279715500> Client ID",
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
                name="<a:latencia:1418504412049182740> Authorize URL",
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
                name="<a:verify2:1418486831993061497> Estado",
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

    @bot.tree.command(name="oauth2-users", description="[OWNER] Ver usuarios que han autorizado OAuth2")
    async def oauth2_users_command(interaction: discord.Interaction):
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
            
            # Obtener usuarios autorizados
            current_time = time.time()
            authorized_users = []
            
            for user_id_oauth, token_info in discord_oauth.user_tokens.items():
                if current_time < token_info.get('expires_at', 0):
                    user_info = token_info.get('user_info', {})
                    authorized_users.append({
                        'user_id': user_id_oauth,
                        'username': user_info.get('username', 'Desconocido'),
                        'display_name': user_info.get('display_name', 'Desconocido'),
                        'email': user_info.get('email', 'No disponible'),
                        'authorized_at': token_info.get('authorized_at', 0),
                        'expires_at': token_info.get('expires_at', 0)
                    })
            
            embed = discord.Embed(
                title="<a:people:1418503543366619247> Usuarios con OAuth2 Autorizado",
                description=f"**{len(authorized_users)}** usuarios han autorizado el acceso OAuth2",
                color=0x00ff88
            )
            
            if authorized_users:
                # Mostrar hasta 10 usuarios más recientes
                recent_users = sorted(authorized_users, key=lambda x: x['authorized_at'], reverse=True)[:10]
                
                for i, user in enumerate(recent_users, 1):
                    hours_remaining = int((user['expires_at'] - current_time) / 3600)
                    embed.add_field(
                        name=f"**{i}.** {user['display_name']}",
                        value=f"**Usuario:** @{user['username']}\n**ID:** `{user['user_id']}`\n**Email:** {user['email']}\n**Expira en:** {hours_remaining}h",
                        inline=True
                    )
                
                if len(authorized_users) > 10:
                    embed.add_field(
                        name="<:stats:1418490788437823599> Información Adicional",
                        value=f"*Mostrando 10 de {len(authorized_users)} usuarios*\nUsa la API `/auth/discord/users` para ver todos",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="📭 Sin Usuarios",
                    value="Ningún usuario ha autorizado OAuth2 aún.",
                    inline=False
                )
            
            embed.set_footer(text="RbxServers • Usuarios OAuth2")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"Owner {interaction.user.name} consultó usuarios OAuth2")
            
        except ImportError:
            embed = discord.Embed(
                title="❌ Sistema OAuth2 No Disponible",
                description="El sistema OAuth2 no está disponible o no se pudo importar.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando oauth2-users: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Ocurrió un error al obtener los usuarios OAuth2: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    logger.info("<a:verify2:1418486831993061497> Comando OAuth2 info configurado")
    return True

# Función opcional de limpieza
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass</old_str>
<new_str># ARCHIVO ELIMINADO - Comandos de prueba OAuth2 ya no necesarios</new_str>
