
import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class KxisSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="🎬 Creadores de contenido",
                description="Información sobre creadores y colaboradores",
                value="creators",
                emoji="🎬"
            ),
            discord.SelectOption(
                label="🔄 Actualizaciones",
                description="Últimas novedades y cambios del bot",
                value="updates",
                emoji="🔄"
            ),
            discord.SelectOption(
                label="📋 Reglas y sanciones",
                description="Normas de uso y sistema de sanciones",
                value="rules",
                emoji="📋"
            ),
            discord.SelectOption(
                label="🎁 Sistema de recompensas",
                description="Cómo funcionan las recompensas y códigos",
                value="rewards",
                emoji="🎁"
            ),
            discord.SelectOption(
                label="⭐ Premium",
                description="Beneficios y características premium",
                value="premium",
                emoji="⭐"
            ),
            discord.SelectOption(
                label="🏆 Créditos",
                description="Reconocimientos y desarrolladores",
                value="credits",
                emoji="🏆"
            )
        ]
        
        super().__init__(
            placeholder="🔽 Selecciona una sección para ver más información...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Callback cuando el usuario selecciona una opción"""
        try:
            selected_value = self.values[0]
            
            # Crear embed específico para cada sección
            embed = discord.Embed(
                title="🔧 Sección en Desarrollo",
                color=0xffaa00
            )
            
            if selected_value == "creators":
                embed.title = "🎬 Creadores de Contenido"
                embed.description = "Esta sección contendrá información sobre los creadores de contenido asociados con RbxServers."
                embed.add_field(
                    name="🚧 En construcción",
                    value="• Lista de creadores oficiales\n• Colaboraciones especiales\n• Contenido exclusivo\n• Códigos de creadores",
                    inline=False
                )
                embed.add_field(
                    name="💡 Próximamente",
                    value="Se añadirán perfiles de creadores y sus beneficios exclusivos.",
                    inline=False
                )
                
            elif selected_value == "updates":
                embed.title = "🔄 Actualizaciones del Bot"
                embed.description = "Aquí encontrarás todas las novedades y cambios recientes de RbxServers."
                embed.add_field(
                    name="🚧 En construcción",
                    value="• Changelog detallado\n• Nuevas funcionalidades\n• Correcciones de bugs\n• Mejoras de rendimiento",
                    inline=False
                )
                embed.add_field(
                    name="💡 Próximamente",
                    value="Sistema de notificaciones automáticas para actualizaciones importantes.",
                    inline=False
                )
                
            elif selected_value == "rules":
                embed.title = "📋 Reglas y Sanciones"
                embed.description = "Normas de uso del bot y información sobre el sistema de sanciones."
                embed.add_field(
                    name="🚧 En construcción",
                    value="• Reglas de uso del bot\n• Tipos de sanciones\n• Sistema de advertencias\n• Proceso de apelaciones",
                    inline=False
                )
                embed.add_field(
                    name="💡 Próximamente",
                    value="Guía completa de términos de servicio y políticas de uso.",
                    inline=False
                )
                
            elif selected_value == "rewards":
                embed.title = "🎁 Sistema de Recompensas"
                embed.description = "Todo sobre las recompensas, códigos promocionales y beneficios."
                embed.add_field(
                    name="🚧 En construcción",
                    value="• Tipos de recompensas\n• Cómo obtener códigos\n• Sistema de puntos\n• Eventos especiales",
                    inline=False
                )
                embed.add_field(
                    name="💡 Próximamente",
                    value="Programa de fidelidad y recompensas por actividad diaria.",
                    inline=False
                )
                
            elif selected_value == "premium":
                embed.title = "⭐ RbxServers Premium"
                embed.description = "Información sobre los beneficios y características de la membresía premium."
                embed.add_field(
                    name="🚧 En construcción",
                    value="• Beneficios exclusivos\n• Precios y planes\n• Cómo obtener premium\n• Funciones adicionales",
                    inline=False
                )
                embed.add_field(
                    name="💡 Próximamente",
                    value="Sistema completo de membresías premium con beneficios únicos.",
                    inline=False
                )
                
            elif selected_value == "credits":
                embed.title = "🏆 Créditos y Reconocimientos"
                embed.description = "Reconocimiento a todas las personas que han contribuido al desarrollo de RbxServers."
                embed.add_field(
                    name="🚧 En construcción",
                    value="• Equipo de desarrollo\n• Colaboradores\n• Agradecimientos especiales\n• Tecnologías utilizadas",
                    inline=False
                )
                embed.add_field(
                    name="💡 Próximamente",
                    value="Página completa de créditos con perfiles detallados del equipo.",
                    inline=False
                )

            # Añadir mensaje especial
            embed.add_field(
                name="👋 Mensaje especial",
                value="oye kxis3rr",
                inline=False
            )
            
            embed.set_footer(text="RbxServers • Información del Bot")
            embed.timestamp = discord.utils.utcnow()
            
            await interaction.response.edit_message(embed=embed, view=self.view)
            
        except Exception as e:
            logger.error(f"Error en callback del menú kxis3rr: {e}")
            await interaction.response.send_message(
                "❌ Ocurrió un error al procesar tu selección.", 
                ephemeral=True
            )

class KxisView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutos de timeout
        self.add_item(KxisSelectMenu())
    
    async def on_timeout(self):
        """Cuando el view expira"""
        for item in self.children:
            item.disabled = True

def setup_kxis3rr_commands(bot):
    """Configurar el comando /kxis3rr"""
    
    @bot.tree.command(name="kxis3rr", description="Información importante sobre el bot y sus características")
    async def kxis3rr_command(interaction: discord.Interaction):
        """Comando que muestra información del bot con menú desplegable"""
        try:
            # Crear embed principal
            embed = discord.Embed(
                title="📚 Información Importante del Bot",
                description="**¡Bienvenido al centro de información de RbxServers!**\n\nAquí encontrarás toda la información importante sobre el bot. Por favor, abre el menú desplegable de abajo y navega por todas las secciones para obtener información detallada sobre cada aspecto del bot.",
                color=0x3366ff
            )
            
            embed.add_field(
                name="🗂️ Secciones disponibles:",
                value="• **🎬 Creadores de contenido** - Información sobre colaboradores\n• **🔄 Actualizaciones** - Últimas novedades del bot\n• **📋 Reglas y sanciones** - Normas de uso importantes\n• **🎁 Sistema de recompensas** - Cómo obtener beneficios\n• **⭐ Premium** - Funciones y beneficios premium\n• **🏆 Créditos** - Reconocimientos del equipo",
                inline=False
            )
            
            embed.add_field(
                name="💡 Cómo usar:",
                value="Haz clic en el menú desplegable de abajo y selecciona la sección que te interese explorar.",
                inline=False
            )
            
            embed.add_field(
                name="👋 Mensaje especial:",
                value="oye kxis3rr",
                inline=False
            )
            
            # Configurar la imagen desde attached_assets como thumbnail
            try:
                file = discord.File("attached_assets/e8d383bc640daf87be94d8b0821eab67_1752283554405.png", filename="kxis3rr_image.png")
                embed.set_thumbnail(url="attachment://kxis3rr_image.png")
                
                # Crear view con el menú desplegable
                view = KxisView()
                
                await interaction.response.send_message(embed=embed, view=view, file=file, ephemeral=False)
                
                # Log de uso del comando
                user_id = str(interaction.user.id)
                username = f"{interaction.user.name}#{interaction.user.discriminator}"
                logger.info(f"Usuario {username} (ID: {user_id}) usó comando /kxis3rr")
                return
                
            except FileNotFoundError:
                logger.warning("⚠️ Imagen kxis3rr no encontrada en attached_assets, usando avatar del bot")
                embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
            
            embed.set_footer(
                text="RbxServers • Sistema de Información",
                icon_url=bot.user.avatar.url if bot.user.avatar else None
            )
            embed.timestamp = discord.utils.utcnow()
            
            # Crear view con el menú desplegable
            view = KxisView()
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
            
            # Log de uso del comando
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            logger.info(f"Usuario {username} (ID: {user_id}) usó comando /kxis3rr")
            
        except Exception as e:
            logger.error(f"Error en comando /kxis3rr: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al cargar la información del bot.",
                color=0xff0000
            )
            error_embed.add_field(
                name="💡 Sugerencia",
                value="Intenta nuevamente en unos momentos",
                inline=False
            )
            
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    logger.info("Comando /kxis3rr configurado exitosamente")
    return True
