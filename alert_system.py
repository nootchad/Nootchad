
import json
import discord
import logging
from pathlib import Path
from datetime import datetime
from typing import Set, Dict

logger = logging.getLogger(__name__)

class BotStartupAlertSystem:
    def __init__(self):
        self.alerts_file = "startup_alerts.json"
        self.subscribed_users: Set[str] = set()
        self.load_alerts_data()
    
    def load_alerts_data(self):
        """Cargar usuarios suscritos desde archivo"""
        try:
            if Path(self.alerts_file).exists():
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.subscribed_users = set(data.get('subscribed_users', []))
                    logger.info(f"<a:verify2:1418486831993061497> Alertas de inicio cargadas: {len(self.subscribed_users)} usuarios suscritos")
            else:
                logger.info("⚠️ Archivo de alertas de inicio no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando alertas de inicio: {e}")
            self.subscribed_users = set()
    
    def save_alerts_data(self):
        """Guardar usuarios suscritos a archivo"""
        try:
            data = {
                'subscribed_users': list(self.subscribed_users),
                'last_updated': datetime.now().isoformat(),
                'total_subscribed': len(self.subscribed_users)
            }
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Datos de alertas de inicio guardados: {len(self.subscribed_users)} usuarios")
        except Exception as e:
            logger.error(f"❌ Error guardando alertas de inicio: {e}")
    
    def subscribe_user(self, user_id: str) -> bool:
        """Suscribir usuario a alertas de inicio"""
        if user_id not in self.subscribed_users:
            self.subscribed_users.add(user_id)
            self.save_alerts_data()
            logger.info(f"<a:verify2:1418486831993061497> Usuario {user_id} suscrito a alertas de inicio")
            return True
        return False
    
    def unsubscribe_user(self, user_id: str) -> bool:
        """Desuscribir usuario de alertas de inicio"""
        if user_id in self.subscribed_users:
            self.subscribed_users.remove(user_id)
            self.save_alerts_data()
            logger.info(f"<a:verify2:1418486831993061497> Usuario {user_id} desuscrito de alertas de inicio")
            return True
        return False
    
    def is_subscribed(self, user_id: str) -> bool:
        """Verificar si usuario está suscrito"""
        return user_id in self.subscribed_users
    
    async def send_startup_notifications(self, bot):
        """Enviar notificaciones a todos los usuarios suscritos cuando el bot inicia"""
        if not self.subscribed_users:
            logger.info("📭 No hay usuarios suscritos a alertas de inicio")
            return
        
        logger.info(f"📢 Enviando notificaciones de inicio a {len(self.subscribed_users)} usuarios...")
        
        successful_notifications = 0
        failed_notifications = 0
        
        startup_embed = discord.Embed(
            title="<a:pepebot:1418489370129993728> RbxServers Bot Iniciado",
            description="¡El bot de RbxServers está ahora **en línea** y listo para usar!",
            color=0x00ff88,
            timestamp=datetime.now()
        )
        
        startup_embed.add_field(
            name="<a:verify2:1418486831993061497> Estado",
            value="**Conectado y funcionando**",
            inline=True
        )
        
        startup_embed.add_field(
            name="<a:control:1418490793223651409> Servicios Disponibles",
            value="• Scraping de servidores VIP\n• Búsqueda de juegos\n• Sistema de favoritos\n• Y mucho más...",
            inline=False
        )
        
        startup_embed.add_field(
            name="<a:foco:1418492184373755966> Comandos Principales",
            value="`/scrape` • `/game` • `/servertest` • `/favorites`",
            inline=False
        )
        
        startup_embed.add_field(
            name="<a:notification:1418491712317292646> Alerta Automática",
            value="Puedes desactivar estas notificaciones usando `/alerta` nuevamente",
            inline=False
        )
        
        startup_embed.set_footer(text="RbxServers • Sistema de Alertas de Inicio")
        startup_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/123456789/roblox_logo.png")
        
        for user_id in list(self.subscribed_users):  # Crear copia para evitar modificaciones durante iteración
            try:
                user = bot.get_user(int(user_id))
                if not user:
                    user = await bot.fetch_user(int(user_id))
                
                if user:
                    await user.send(embed=startup_embed)
                    successful_notifications += 1
                    logger.info(f"📨 Notificación de inicio enviada a {user.name} (ID: {user_id})")
                else:
                    logger.warning(f"⚠️ No se pudo encontrar usuario {user_id}")
                    failed_notifications += 1
                
            except discord.Forbidden:
                logger.warning(f"🚫 No se puede enviar DM a usuario {user_id} (DMs bloqueados)")
                failed_notifications += 1
            except discord.NotFound:
                logger.warning(f"👤 Usuario {user_id} no encontrado, removiendo de la lista")
                self.unsubscribe_user(user_id)
                failed_notifications += 1
            except Exception as e:
                logger.error(f"❌ Error enviando notificación a usuario {user_id}: {e}")
                failed_notifications += 1
        
        logger.info(f"<:stats:1418490788437823599> Notificaciones de inicio completadas: {successful_notifications} exitosas, {failed_notifications} fallidas")

def setup_alert_commands(bot):
    """Configurar comandos de alertas de inicio"""
    startup_alert_system = BotStartupAlertSystem()
    
    @bot.tree.command(name="alerta", description="Activar/desactivar notificaciones cuando el bot se inicie")
    async def alerta_command(interaction: discord.Interaction):
        """Comando para suscribirse/desuscribirse a alertas de inicio del bot"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        try:
            # Verificar si ya está suscrito
            if startup_alert_system.is_subscribed(user_id):
                # Desuscribir
                startup_alert_system.unsubscribe_user(user_id)
                
                embed = discord.Embed(
                    title="🔕 Alertas Desactivadas",
                    description="Has sido **desuscrito** de las notificaciones de inicio del bot.",
                    color=0xff9900
                )
                embed.add_field(
                    name="❌ Estado Actual",
                    value="**Alertas desactivadas**",
                    inline=True
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> Para reactivar",
                    value="Usa `/alerta` nuevamente",
                    inline=True
                )
                embed.add_field(
                    name="ℹ️ Información",
                    value="Ya no recibirás DMs cuando el bot se inicie o reconecte",
                    inline=False
                )
                embed.set_footer(text="RbxServers • Sistema de Alertas")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Usuario {username} (ID: {user_id}) desactivó alertas de inicio")
                
            else:
                # Suscribir
                startup_alert_system.subscribe_user(user_id)
                
                embed = discord.Embed(
                    title="<a:notification:1418491712317292646> Alertas Activadas",
                    description="¡Te has **suscrito** exitosamente a las notificaciones de inicio del bot!",
                    color=0x00ff88
                )
                embed.add_field(
                    name="<a:verify2:1418486831993061497> Estado Actual",
                    value="**Alertas activadas**",
                    inline=True
                )
                embed.add_field(
                    name="📱 Recibirás DMs cuando:",
                    value="• El bot se inicie\n• El bot se reconecte\n• Haya actualizaciones importantes",
                    inline=False
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> Para desactivar",
                    value="Usa `/alerta` nuevamente",
                    inline=True
                )
                embed.add_field(
                    name="🔒 Privacidad",
                    value="Solo recibirás mensajes relacionados con el estado del bot",
                    inline=False
                )
                embed.set_footer(text="RbxServers • Sistema de Alertas")
                
                # Enviar confirmación por DM
                try:
                    dm_embed = discord.Embed(
                        title="<a:notification:1418491712317292646> Confirmación de Suscripción",
                        description="Has activado las **alertas de inicio** del bot RbxServers.",
                        color=0x00ff88,
                        timestamp=datetime.now()
                    )
                    dm_embed.add_field(
                        name="<a:verify2:1418486831993061497> Activado Exitosamente",
                        value="Ahora recibirás un mensaje cada vez que el bot se inicie o reconecte",
                        inline=False
                    )
                    dm_embed.add_field(
                        name="<a:control:1418490793223651409> Bot Status",
                        value="El bot está **actualmente en línea** y funcionando correctamente",
                        inline=False
                    )
                    dm_embed.add_field(
                        name="🔕 Para Desactivar",
                        value="Usa el comando `/alerta` en cualquier servidor donde esté el bot",
                        inline=False
                    )
                    dm_embed.set_footer(text="RbxServers • Confirmación de Alertas")
                    
                    await interaction.user.send(embed=dm_embed)
                    
                    # Agregar nota en la respuesta principal
                    embed.add_field(
                        name="📬 Confirmación Enviada",
                        value="Se ha enviado una confirmación a tu DM",
                        inline=False
                    )
                    
                except discord.Forbidden:
                    embed.add_field(
                        name="⚠️ Aviso",
                        value="No se pudo enviar confirmación por DM. Asegúrate de tener los DMs habilitados para recibir las alertas.",
                        inline=False
                    )
                    logger.warning(f"No se pudo enviar DM de confirmación a {username} (ID: {user_id})")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                logger.info(f"Usuario {username} (ID: {user_id}) activó alertas de inicio")
            
        except Exception as e:
            logger.error(f"Error en comando /alerta para usuario {username}: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al procesar tu solicitud de alertas.",
                color=0xff0000
            )
            error_embed.add_field(
                name="<a:foco:1418492184373755966> Sugerencia",
                value="Intenta nuevamente en unos momentos",
                inline=False
            )
            
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    return startup_alert_system
