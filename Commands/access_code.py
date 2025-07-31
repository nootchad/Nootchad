
import discord
from discord.ext import commands
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def setup_access_code_commands(bot):
    """Configurar comandos de códigos de acceso"""

    @bot.tree.command(name="access_code", description="<:1000182584:1396049547838492672> Generar un código de acceso temporal para APIs externas")
    async def access_code_command(interaction: discord.Interaction):
        """Generar código de acceso temporal para el usuario"""
        try:
            await interaction.response.defer(ephemeral=True)
            
            user_id = str(interaction.user.id)
            
            # Importar el sistema de códigos
            from apis import access_code_system
            
            # Generar nuevo código (invalida el anterior automáticamente)
            access_code = access_code_system.generate_user_code(user_id)
            
            # Calcular tiempo de expiración
            expires_at = time.time() + (24 * 60 * 60)  # 24 horas
            expires_date = datetime.fromtimestamp(expires_at)
            
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Código de Acceso Generado",
                description="Tu código de acceso temporal ha sido creado exitosamente",
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="<:verify:1396087763388072006> Tu Código de Acceso",
                value=f"```\n{access_code}\n```",
                inline=False
            )
            
            embed.add_field(
                name="<:1000182657:1396060091366637669> Información del Código",
                value=f"**Expira:** <t:{int(expires_at)}:F>\n**Usos máximos:** 50\n**Usuario:** {interaction.user.mention}",
                inline=True
            )
            
            embed.add_field(
                name="<:1000182751:1396420551798558781> Uso del Código",
                value="• Usa este código en aplicaciones externas\n• El código se invalida al generar uno nuevo\n• Máximo 50 usos en 24 horas",
                inline=True
            )
            
            embed.add_field(
                name="<:1000182750:1396420537227411587> Endpoints de API",
                value="**Verificar código:**\n`POST /api/user-access/verify`\n\n**Obtener información:**\n`GET /api/user-access/info/{código}`",
                inline=False
            )
            
            embed.add_field(
                name="<:1000182563:1396420770904932372> Importante",
                value="• No compartas tu código con nadie\n• Se genera un nuevo código cada vez que uses este comando\n• El código anterior se invalida automáticamente",
                inline=False
            )
            
            embed.set_footer(
                text="RbxServers • Sistema de Códigos de Acceso",
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"<:verify:1396087763388072006> Código de acceso generado para {interaction.user.name} (ID: {user_id})")
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en comando access_code: {e}")
            
            error_embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Hubo un error generando tu código de acceso. Inténtalo de nuevo.",
                color=0xff0000
            )
            
            try:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)

    @bot.tree.command(name="access_info", description="<:1000182584:1396049547838492672> Ver información sobre el sistema de códigos de acceso")
    async def access_info_command(interaction: discord.Interaction):
        """Mostrar información sobre el sistema de códigos de acceso"""
        try:
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Sistema de Códigos de Acceso",
                description="Información sobre cómo usar los códigos de acceso temporal",
                color=0x3366ff,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="<:1000182751:1396420551798558781> ¿Qué son los Códigos de Acceso?",
                value="Los códigos de acceso permiten a aplicaciones externas obtener tu información de forma segura sin necesidad de credenciales permanentes.",
                inline=False
            )
            
            embed.add_field(
                name="<:verify:1396087763388072006> Cómo Funciona",
                value="1. Generas un código con `/access_code`\n2. Usas el código en una aplicación externa\n3. La aplicación obtiene tu información de RbxServers\n4. El código expira en 24 horas o después de 50 usos",
                inline=False
            )
            
            embed.add_field(
                name="<:1000182656:1396059543951118416> Seguridad",
                value="• Cada código es único para ti\n• Los códigos expiran automáticamente\n• Generar un nuevo código invalida el anterior\n• Límite de usos para prevenir abuso",
                inline=True
            )
            
            embed.add_field(
                name="<:1000182750:1396420537227411587> Información Disponible",
                value="• Estado de verificación de Roblox\n• Estadísticas de servidores\n• Balance de monedas\n• Actividad en el bot\n• Información de seguridad",
                inline=True
            )
            
            embed.add_field(
                name="<:1000182657:1396060091366637669> Comandos Disponibles",
                value="`/access_code` - Generar nuevo código\n`/access_info` - Ver esta información",
                inline=False
            )
            
            embed.set_footer(
                text="RbxServers • Códigos de Acceso Seguros",
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"<:1000182563:1396420770904932372> Error en comando access_info: {e}")
            
            error_embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Hubo un error mostrando la información.",
                color=0xff0000
            )
            
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    logger.info("<:1000182584:1396049547838492672> Comandos de códigos de acceso configurados")

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    setup_access_code_commands(bot)
    logger.info("<:verify:1396087763388072006> Comandos de códigos de acceso configurados")
    return True

# Mantener compatibilidad con auto-registro anterior
def _try_auto_register():
    """Intentar registrar automáticamente los comandos"""
    try:
        import sys
        if 'main' in sys.modules:
            main_module = sys.modules['main']
            if hasattr(main_module, 'bot') and main_module.bot:
                setup_access_code_commands(main_module.bot)
                logger.info("<:verify:1396087763388072006> Comandos de acceso auto-registrados exitosamente")
                return True
    except Exception as e:
        logger.debug(f"Auto-registro falló: {e}")
    return False

# Intentar auto-registro inmediato solo si no se usa el sistema de carga dinámico
if not _try_auto_register():
    logger.debug("Auto-registro inmediato falló, se usará el sistema de carga dinámico")
