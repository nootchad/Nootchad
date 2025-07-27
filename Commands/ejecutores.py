
"""
Comando /ejecutores - Sistema disuasorio sobre exploits en Roblox
=================================================================

Este comando muestra un mensaje educativo sobre el uso de exploits
y envía información detallada por DM al usuario.
"""
import discord
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    
    @bot.tree.command(name="ejecutores", description="Información importante sobre exploits y las reglas de Roblox")
    async def ejecutores_command(interaction: discord.Interaction):
        """Comando que muestra mensaje disuasorio sobre exploits"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        logger.info(f"🚫 Usuario {username} (ID: {user_id}) solicitó información sobre ejecutores")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Mensaje público disuasorio
            public_embed = discord.Embed(
                title="🚫 Política sobre Exploits y Ejecutores",
                description="**RbxServers NO apoya ni promueve el uso de exploits, hacks o ejecutores en Roblox.**\n\nEstos programas violan los Términos de Servicio de Roblox y pueden resultar en la suspensión permanente de tu cuenta.",
                color=0xff4444
            )
            
            public_embed.add_field(
                name="⚠️ **IMPORTANTE**",
                value="• El uso de exploits puede resultar en **ban permanente** de Roblox\n• Roblox tiene sistemas anti-cheat muy avanzados\n• Tu cuenta puede ser comprometida por malware\n• Violás los Términos de Servicio oficiales",
                inline=False
            )
            
            public_embed.add_field(
                name="✅ **Alternativas Legales**",
                value="• Usa **Roblox Studio** para crear tus propios juegos\n• Aprende **programación en Lua** oficialmente\n• Participa en **eventos y concursos** de Roblox\n• Únete a **grupos de desarrolladores** legítimos",
                inline=False
            )
            
            public_embed.add_field(
                name="📧 **Información Adicional**",
                value="Se ha enviado información detallada a tu **mensaje privado** con recursos educativos y alternativas seguras.",
                inline=False
            )
            
            public_embed.add_field(
                name="🔗 **Recursos Oficiales**",
                value="• [Términos de Servicio](https://en.help.roblox.com/hc/articles/115004647846)\n• [Reglas de la Comunidad](https://en.help.roblox.com/hc/articles/203313410)\n• [Roblox Developer Hub](https://developer.roblox.com/)",
                inline=False
            )
            
            public_embed.set_footer(text="RbxServers • Promovemos el uso responsable y seguro de Roblox")
            public_embed.timestamp = datetime.now()
            
            await interaction.followup.send(embed=public_embed, ephemeral=True)
            
            # Intentar enviar DM detallado
            try:
                user = interaction.user
                
                dm_embed = discord.Embed(
                    title="🚨 Aviso Importante sobre Exploits en Roblox",
                    description="Hemos recibido tu consulta sobre ejecutores/exploits para Roblox. Como bot oficial, tenemos la responsabilidad de informarte sobre los riesgos y consecuencias de usar estas herramientas.",
                    color=0xff0000
                )
                
                dm_embed.add_field(
                    name="⚖️ **Aspectos Legales y Términos de Servicio**",
                    value="El uso de exploits, hacks, ejecutores o cualquier software de terceros que modifique la experiencia de Roblox constituye una **violación directa** de los Términos de Servicio de Roblox Corporation. Esto incluye pero no se limita a:\n\n• Manipulación de la memoria del juego\n• Inyección de código no autorizado\n• Modificación de archivos del cliente\n• Uso de herramientas de automatización no oficiales\n• Bypassing de sistemas de seguridad",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="🚫 **Consecuencias Reales del Uso de Exploits**",
                    value="**Consecuencias Inmediatas:**\n• Ban permanente e irreversible de tu cuenta de Roblox\n• Pérdida de todos los Robux, items y progreso\n• Pérdida de acceso a juegos premium pagados\n• Restricción IP que puede afectar otras cuentas\n\n**Riesgos de Seguridad:**\n• Malware y virus en ejecutores falsos\n• Robo de credenciales y datos personales\n• Compromiso de tu cuenta de Roblox\n• Posible acceso no autorizado a otras cuentas",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="🔍 **Sistemas Anti-Cheat de Roblox (Hyperion)**",
                    value="Roblox utiliza tecnologías anti-cheat extremadamente avanzadas:\n\n• **Hyperion**: Sistema de detección en tiempo real\n• **Análisis de comportamiento**: Detecta patrones anómalos\n• **Machine Learning**: Aprende constantemente nuevos métodos\n• **Análisis de memoria**: Detecta modificaciones no autorizadas\n• **Reportes automáticos**: Los jugadores pueden reportar fácilmente\n\nEstos sistemas detectan el **99.9% de los exploits** conocidos en cuestión de minutos u horas.",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="💡 **Alternativas Educativas y Legales**",
                    value="**Aprende Desarrollo Oficial:**\n• [Roblox Studio](https://www.roblox.com/create) - Herramienta oficial gratuita\n• [Developer Hub](https://developer.roblox.com/) - Documentación completa\n• [Roblox Education](https://education.roblox.com/) - Cursos oficiales\n• [YouTube Creator Hub](https://www.youtube.com/robloxdev) - Tutoriales oficiales\n\n**Comunidades de Desarrollo:**\n• Roblox Developer Forum\n• DevForum Communities\n• Roblox Discord Servers oficiales\n• Hidden Developers (comunidad hispana)",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="🎯 **¿Por Qué NO Deberías Usar Exploits?**",
                    value="**Impacto en la Comunidad:**\n• Arruinas la experiencia de otros jugadores\n• Causas pérdidas económicas a desarrolladores\n• Contribuyes a la toxicidad en los juegos\n• Reduces la calidad general de la plataforma\n\n**Desarrollo Personal:**\n• No aprendes habilidades reales de programación\n• Dependes de herramientas externas\n• No desarrollas creatividad genuina\n• Pierdes oportunidades de crecimiento profesional",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="🌟 **Oportunidades Reales en Roblox**",
                    value="**Gana Dinero Legalmente:**\n• [DevEx Program](https://developer.roblox.com/devex) - Convierte Robux en dinero real\n• Creación de juegos exitosos (algunos desarrolladores ganan $1M+ anuales)\n• Venta de items en el catálogo oficial\n• Comisiones por desarrollo de juegos\n\n**Builds tu Portafolio:**\n• Roblox Studio es usado por empresas reales\n• Experiencia en Lua es valorada en la industria\n• Portafolio de juegos puede abrir puertas profesionales\n• Networking con otros desarrolladores",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="📞 **Recursos de Ayuda y Soporte**",
                    value="**Si ya usaste exploits:**\n• Deja de usarlos inmediatamente\n• Cambia tu contraseña de Roblox\n• Activa la autenticación de dos factores\n• Escanea tu PC con antivirus actualizado\n\n**Para aprender desarrollo:**\n• [Roblox Scripting Tutorials](https://developer.roblox.com/learn-roblox/)\n• [Lua Learning Resources](https://www.lua.org/start.html)\n• [AlvinBlox YouTube](https://www.youtube.com/channel/UCp1R0TBvgM7gj0rwTYULmSA)\n• Comunidades de Discord de desarrollo",
                    inline=False
                )
                
                dm_embed.add_field(
                    name="🤝 **Nuestro Compromiso como RbxServers**",
                    value="Como bot oficial de la comunidad de Roblox, nuestro compromiso es:\n\n• **Promover el uso ético** y responsable de Roblox\n• **Educar** sobre los riesgos reales del uso de exploits\n• **Apoyar** a desarrolladores legítimos y creativos\n• **Proteger** a nuestra comunidad de amenazas\n• **Fomentar** el aprendizaje y desarrollo de habilidades reales\n\nSi tienes preguntas sobre desarrollo legítimo en Roblox, ¡estamos aquí para ayudarte a encontrar los recursos correctos!",
                    inline=False
                )
                
                dm_embed.set_footer(text="Este mensaje fue enviado para tu seguridad y educación • RbxServers")
                dm_embed.timestamp = datetime.now()
                
                await user.send(embed=dm_embed)
                logger.info(f"✅ DM educativo enviado exitosamente a {username}")
                
            except discord.Forbidden:
                # Si no se puede enviar DM, informar en la respuesta ephemeral
                no_dm_embed = discord.Embed(
                    title="📧 No se pudo enviar DM",
                    description="No pudimos enviarte la información detallada por mensaje privado. Asegúrate de tener los DMs habilitados.",
                    color=0xff9900
                )
                no_dm_embed.add_field(
                    name="💡 Para recibir información completa:",
                    value="1. Ve a **Configuración de Usuario** → **Privacidad y Seguridad**\n2. Habilita **Permitir mensajes directos de miembros del servidor**\n3. Ejecuta el comando nuevamente",
                    inline=False
                )
                await interaction.followup.send(embed=no_dm_embed, ephemeral=True)
                logger.warning(f"⚠️ No se pudo enviar DM a {username} - DMs deshabilitados")
                
            except Exception as dm_error:
                logger.error(f"❌ Error enviando DM a {username}: {dm_error}")
                
                error_embed = discord.Embed(
                    title="❌ Error Enviando Información",
                    description="Ocurrió un error al enviar la información detallada. El mensaje principal contiene los puntos más importantes.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        
        except Exception as e:
            logger.error(f"❌ Error en comando /ejecutores para {username}: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error del Sistema",
                description="Ocurrió un error procesando tu solicitud. Sin embargo, recuerda: **RbxServers NO apoya el uso de exploits en Roblox**.",
                color=0xff0000
            )
            error_embed.add_field(
                name="⚠️ Mensaje Importante",
                value="El uso de exploits puede resultar en la suspensión permanente de tu cuenta de Roblox. Por favor, respeta los Términos de Servicio.",
                inline=False
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /ejecutores configurado correctamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    logger.info("🧹 Limpieza del comando /ejecutores completada")
