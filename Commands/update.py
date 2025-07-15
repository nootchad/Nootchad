
"""
Comando /update para mostrar las últimas actualizaciones del bot RbxServers
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="update", description="Ver las últimas actualizaciones del bot RbxServers")
    async def update_command(interaction: discord.Interaction):
        """Mostrar las últimas actualizaciones del bot"""
        try:
            # Crear embed principal de actualizaciones
            embed = discord.Embed(
                title="🚀 RbxServers - Nueva Actualización Disponible",
                description="¡Conoce todas las nuevas funcionalidades que hemos añadido al bot!",
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            # Versión actual
            embed.add_field(
                name="📱 Versión Actual",
                value="**v3.0.0** - Julio 2025",
                inline=True
            )
            
            # Estado del bot
            embed.add_field(
                name="🟢 Estado",
                value="**Estable** - Totalmente operativo",
                inline=True
            )
            
            # Última actualización
            embed.add_field(
                name="📅 Última Actualización",
                value="<t:1737849600:R>",  # Timestamp relativo
                inline=True
            )
            
            # Comando /autoscrape
            embed.add_field(
                name="🔄 Nuevo: Comando `/autoscrape`",
                value="""
                **Auto Scraping Inteligente**
                • Busca automáticamente servidores VIP para ti
                • Especifica hasta 2 juegos simultáneamente
                • Sistema de cooldowns automáticos cada 5 servidores
                • Obtén hasta 20 servidores en una sola ejecución
                • Entrega por mensaje privado para mayor privacidad
                
                **Uso:** `/autoscrape game_id:123456 cantidad:10 game_id2:789012`
                """,
                inline=False
            )
            
            # Comando /music
            embed.add_field(
                name="🎵 Nuevo: Comando `/music`",
                value="""
                **Generador de Música con IA**
                • Crea música única usando RbxServers-v1 Music AI
                • Describe tu música y la IA la generará
                • Duración personalizable (5-300 segundos)
                • **PREMIUM:** Los usuarios premium pueden reproducir la música directamente en Roblox mediante el bot
                • Formato MP3 de alta calidad para descarga
                
                **Uso:** `/music descripcion:"rock épico" duracion:60`
                """,
                inline=False
            )
            
            # Comando /leaderboard
            embed.add_field(
                name="🏆 Nuevo: Comando `/leaderboard`",
                value="""
                **Sistema de Ranking Competitivo**
                • Ranking semanal e histórico de usuarios
                • Basado en servidores VIP acumulados (sin límites)
                • Reinicio automático cada lunes
                • **Recompensas Semanales:**
                  🥇 **1er lugar:** 400 monedas + Cuenta Crunchyroll Premium
                  🥈 **2do lugar:** 250 monedas + Cuenta Crunchyroll Premium  
                  🥉 **3er lugar:** 150 monedas + Cuenta Crunchyroll Premium
                
                **Uso:** `/leaderboard tipo:semanal` o `/leaderboard tipo:historico`
                """,
                inline=False
            )
            
            # Mejoras técnicas
            embed.add_field(
                name="⚙️ Mejoras Técnicas Importantes",
                value="""
                • **Sistema de Comandos Dinámicos** - Carga automática desde carpeta Commands/
                • **Optimización de Scraping** - 60% más rápido con cookies automáticas
                • **API Web Expandida** - Nuevos endpoints para desarrolladores
                • **Sistema Anti-Alt Avanzado** - Detección mejorada de cuentas falsas
                • **Manejo de Errores Robusto** - Menos timeouts y errores inesperados
                • **Base de Datos Simplificada** - Estructura más eficiente en user_game_servers.json
                """,
                inline=False
            )
            
            # Funciones premium
            embed.add_field(
                name="⭐ Funciones Premium Destacadas",
                value="""
                • **Reproducción de Música en Roblox** - Tu música generada directo en el juego
                • **Auto Scraping Ilimitado** - Sin cooldowns ni restricciones
                • **Prioridad en Comandos** - Procesamiento más rápido
                • **Acceso Anticipado** - Nuevas funciones antes que otros usuarios
                • **Soporte Premium** - Atención prioritaria
                """,
                inline=False
            )
            
            # Próximas actualizaciones
            embed.add_field(
                name="🚀 Próximamente en v3.1.0",
                value="""
                • **Sistema de Guilds** - Clanes y grupos de usuarios
                • **Modo Competitivo** - Torneos y eventos especiales
                • **Dashboard Web Completo** - Panel de control total
                • **Sistema de Notificaciones Push** - Alertas en tiempo real
                • **Integración con Spotify** - Exporta tu música generada
                • **Marketplace Expandido** - Intercambio de servidores entre usuarios
                """,
                inline=False
            )
            
            # Enlaces útiles
            embed.add_field(
                name="🔗 Enlaces y Recursos",
                value="""
                • [📚 Documentación API](https://workspace-paysencharlee.replit.dev/api/)
                • [🌐 Dashboard Web](https://workspace-paysencharlee.replit.dev/)
                • [📊 Estado del Servidor](https://workspace-paysencharlee.replit.dev/api/status)
                • [🎯 Reportar Bugs](https://discord.com/) 
                • [💎 Obtener Premium](https://discord.com/)
                """,
                inline=False
            )
            
            # Agradecimientos especiales
            embed.add_field(
                name="🙏 Agradecimientos Especiales",
                value="""
                Gracias a toda la comunidad por su apoyo constante y feedback valioso. 
                Esta actualización incluye muchas de las sugerencias que nos han enviado.
                
                **¡Sigan enviando sus ideas para las próximas actualizaciones!**
                """,
                inline=False
            )
            
            # Footer con información adicional
            embed.set_footer(
                text="RbxServers v3.0.0 • Desarrollado por Hesiz • Powered by Hesiz",
                icon_url="https://rbxservers.xyz/svgs/roblox.svg"
            )
            
            # Thumbnail del bot
            embed.set_thumbnail(url="https://rbxservers.xyz/svgs/roblox.svg")
            
            # Responder con el embed
            await interaction.response.send_message(embed=embed, ephemeral=False)
            
            # Log del uso del comando
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            user_id = str(interaction.user.id)
            logger.info(f"Usuario {username} (ID: {user_id}) usó comando /update")
            
            # Dar monedas por usar el comando (si el sistema está disponible)
            try:
                # Importar el sistema de monedas dinámicamente
                import sys
                if 'coins_system' in sys.modules:
                    coins_system = sys.modules['coins_system']
                    if hasattr(coins_system, 'add_coins'):
                        coins_system.add_coins(user_id, 5, "Ver actualizaciones del bot")
            except Exception as e:
                logger.debug(f"Error agregando monedas automáticas: {e}")
        
        except Exception as e:
            logger.error(f"Error en comando /update: {e}")
            
            # Embed de error
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al cargar las actualizaciones.",
                color=0xff0000
            )
            error_embed.add_field(
                name="🔧 Solución",
                value="Inténtalo nuevamente en unos segundos.",
                inline=False
            )
            
            # Responder con error si no se ha respondido aún
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /update configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
