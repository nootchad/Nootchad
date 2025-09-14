"""
Comando para generar códigos de acceso temporal para APIs externas
"""
import discord
from discord.ext import commands
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    """
    
    @bot.tree.command(name="access_code", description="Generar código de acceso temporal para APIs externas")
    async def access_code_command(interaction: discord.Interaction):
        """Generar código de acceso para APIs externas"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        logger.info(f"Usuario {username} (ID: {user_id}) solicitó código de acceso")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Importar el sistema de códigos
            from apis import access_code_system
            
            # Generar código para el usuario
            access_code = access_code_system.generate_user_code(user_id)
            
            if access_code:
                # Obtener información del código
                code_info = access_code_system.access_codes.get(access_code, {})
                expires_at = code_info.get('expires_at', time.time() + 24*60*60)
                max_uses = code_info.get('max_uses', 50)
                
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Código de Acceso Generado",
                    description="Tu código de acceso temporal ha sido creado exitosamente",
                    color=0x00ff88
                )
                
                embed.add_field(
                    name="<:verify:1396087763388072006> Tu Código de Acceso:",
                    value=f"```\n{access_code}\n```",
                    inline=False
                )
                
                embed.add_field(
                    name="<:1000182657:1396060091366637669> Información del Código:",
                    value=f"**Expira:** <t:{int(expires_at)}:R>\n**Usos máximos:** {max_uses}\n**Usuario:** {interaction.user.mention}",
                    inline=False
                )
                
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Uso del Código:",
                    value="• Usa este código en aplicaciones externas\n• El código se invalida al generar uno nuevo\n• Máximo 50 usos en 24 horas",
                    inline=False
                )
                
                embed.add_field(
                    name="<:1000182750:1396420537227411587> Endpoints de API:",
                    value="**Verificar código:**\n`POST /api/user-access/verify`\n\n**Obtener información:**\n`GET /api/user-access/info/{access_code}`",
                    inline=False
                )
                
                embed.add_field(
                    name="<:1000182563:1396420770904932372> Importante:",
                    value="• No compartas tu código con nadie\n• Se genera un nuevo código cada vez que uses este comando\n• El código anterior se invalida automáticamente",
                    inline=False
                )
                
                embed.set_footer(text="RbxServers • Sistema de Códigos de Acceso")
                embed.timestamp = datetime.now()
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                logger.info(f"<:verify:1396087763388072006> Código generado exitosamente para {username}: {access_code}")
                
            else:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Error",
                    description="No se pudo generar el código de acceso. Intenta nuevamente.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                logger.error(f"❌ No se pudo generar código para {username}")
        
        except ImportError:
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Sistema No Disponible",
                description="El sistema de códigos de acceso no está disponible.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error en comando access_code para {username}: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error Interno",
                description="Ocurrió un error al generar el código. Contacta al soporte.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="access_info", description="Información sobre el sistema de códigos de acceso")
    async def access_info_command(interaction: discord.Interaction):
        """Mostrar información sobre cómo usar los códigos de acceso"""
        
        embed = discord.Embed(
            title="<:1000182584:1396049547838492672> Sistema de Códigos de Acceso",
            description="Información sobre cómo usar los códigos de acceso temporal",
            color=0x3366ff
        )
        
        embed.add_field(
            name="<:1000182751:1396420551798558781> ¿Qué son los Códigos de Acceso?",
            value="Los códigos de acceso permiten a aplicaciones externas obtener tu información de forma segura sin necesidad de credenciales permanentes.",
            inline=False
        )
        
        embed.add_field(
            name="<:verify:1396087763388072006> Cómo Funciona:",
            value="1. Generas un código con `/access_code`\n2. Usas el código en una aplicación externa\n3. La aplicación obtiene tu información de RbxServers\n4. El código expira en 24 horas o después de 50 usos",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182656:1396059543951118416> Seguridad:",
            value="• Cada código es único para ti\n• Los códigos expiran automáticamente\n• Generar un nuevo código invalida el anterior\n• Límite de usos para prevenir abuso",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182750:1396420537227411587> Información Disponible:",
            value="• Estado de verificación de Roblox\n• Estadísticas de servidores\n• Balance de monedas\n• Actividad en el bot\n• Información de seguridad",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182657:1396060091366637669> Comandos Disponibles:",
            value="`/access_code` - Generar nuevo código\n`/access_info` - Ver esta información",
            inline=False
        )
        
        embed.set_footer(text="RbxServers • Sistema de Códigos de Acceso")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        logger.info(f"Usuario {interaction.user.name} consultó información de códigos de acceso")
    
    logger.info("<:verify:1396087763388072006> Comandos de códigos de acceso configurados")
    return True

# Función opcional de limpieza
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass