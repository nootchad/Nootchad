
import discord
from discord.ext import commands
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class MaintenanceSystem:
    def __init__(self, bot):
        self.bot = bot
        self.maintenance_file = "maintenance_data.json"
        self.maintenance_data = {}
        self.load_maintenance_data()

    def load_maintenance_data(self):
        """Cargar datos de mantenimiento desde archivo"""
        try:
            if Path(self.maintenance_file).exists():
                with open(self.maintenance_file, 'r', encoding='utf-8') as f:
                    self.maintenance_data = json.load(f)
                    logger.info(f"✅ Datos de mantenimiento cargados")
            else:
                self.maintenance_data = {
                    'active': False,
                    'message': '',
                    'started_at': None,
                    'started_by': None,
                    'notified_users': []
                }
                logger.info("⚠️ Archivo de mantenimiento no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando datos de mantenimiento: {e}")
            self.maintenance_data = {
                'active': False,
                'message': '',
                'started_at': None,
                'started_by': None,
                'notified_users': []
            }

    def save_maintenance_data(self):
        """Guardar datos de mantenimiento a archivo"""
        try:
            with open(self.maintenance_file, 'w', encoding='utf-8') as f:
                json.dump(self.maintenance_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Datos de mantenimiento guardados")
        except Exception as e:
            logger.error(f"❌ Error guardando datos de mantenimiento: {e}")

    async def get_all_verified_users(self):
        """Obtener todos los usuarios verificados desde el sistema de verificación"""
        try:
            # Importar aquí para evitar imports circulares
            from main import roblox_verification
            return list(roblox_verification.verified_users.keys())
        except Exception as e:
            logger.error(f"Error obteniendo usuarios verificados: {e}")
            return []

    async def send_maintenance_notification(self, message: str, started_by: str, action: str = "start"):
        """Enviar notificación de mantenimiento a todos los usuarios verificados"""
        verified_users = await self.get_all_verified_users()
        
        if not verified_users:
            logger.warning("⚠️ No hay usuarios verificados para notificar")
            return 0, 0
        
        successful_notifications = 0
        failed_notifications = 0
        
        # Determinar título y color según la acción
        if action == "start":
            title = "🔧 Mantenimiento Programado"
            color = 0xff9900
            icon = "🔧"
        else:  # end
            title = "✅ Mantenimiento Completado"
            color = 0x00ff88
            icon = "<a:verify2:1418486831993061497>"
        
        for user_id in verified_users:
            try:
                user = self.bot.get_user(int(user_id))
                if not user:
                    user = await self.bot.fetch_user(int(user_id))
                
                if user:
                    embed = discord.Embed(
                        title=title,
                        description=message,
                        color=color,
                        timestamp=datetime.now()
                    )
                    
                    embed.add_field(
                        name="👤 Iniciado por",
                        value=started_by,
                        inline=True
                    )
                    
                    embed.add_field(
                        name="⏰ Fecha",
                        value=f"<t:{int(datetime.now().timestamp())}:F>",
                        inline=True
                    )
                    
                    if action == "start":
                        embed.add_field(
                            name="<a:foco:1418492184373755966> Durante el mantenimiento",
                            value="• Los comandos del bot pueden estar limitados\n• Algunas funciones pueden no estar disponibles\n• Te notificaremos cuando termine",
                            inline=False
                        )
                    else:
                        embed.add_field(
                            name="🎉 ¡Todo listo!",
                            value="• Todos los comandos están disponibles\n• Las funciones están completamente operativas\n• Gracias por tu paciencia",
                            inline=False
                        )
                    
                    embed.set_footer(
                        text="RbxServers • Sistema de Mantenimiento",
                        icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
                    )
                    
                    await user.send(embed=embed)
                    successful_notifications += 1
                    logger.info(f"📨 Notificación de mantenimiento enviada a {user.name} (ID: {user_id})")
                    
                    # Pequeña pausa para evitar rate limits
                    await asyncio.sleep(0.5)
                
            except discord.errors.Forbidden:
                logger.warning(f"⚠️ No se pudo enviar DM a usuario {user_id} - DMs cerrados")
                failed_notifications += 1
            except discord.errors.NotFound:
                logger.warning(f"⚠️ Usuario {user_id} no encontrado")
                failed_notifications += 1
            except Exception as e:
                logger.error(f"❌ Error enviando notificación a usuario {user_id}: {e}")
                failed_notifications += 1
        
        return successful_notifications, failed_notifications

    def is_owner_or_delegated(self, user_id: str) -> bool:
        """Verificar si un usuario es owner original o tiene acceso delegado"""
        try:
            from main import is_owner_or_delegated
            return is_owner_or_delegated(user_id)
        except Exception as e:
            logger.error(f"Error verificando permisos: {e}")
            # Fallback - solo permitir al owner principal
            return user_id == "916070251895091241"

def setup_maintenance_commands(bot):
    """Configurar comandos de mantenimiento"""
    maintenance_system = MaintenanceSystem(bot)
    
    @bot.tree.command(name="maintenance", description="[OWNER ONLY] Activar/desactivar modo mantenimiento y notificar usuarios")
    async def maintenance_command(interaction: discord.Interaction, action: str, message: str = ""):
        """Comando para gestionar el modo mantenimiento"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Verificar permisos
        if not maintenance_system.is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validar acción
        if action.lower() not in ["start", "end", "status"]:
            embed = discord.Embed(
                title="❌ Acción Inválida",
                description="Las acciones válidas son: `start`, `end`, `status`",
                color=0xff0000
            )
            embed.add_field(
                name="📝 Uso correcto:",
                value="• `/maintenance start [mensaje]` - Iniciar mantenimiento\n• `/maintenance end [mensaje]` - Finalizar mantenimiento\n• `/maintenance status` - Ver estado actual",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if action.lower() == "status":
                # Mostrar estado actual
                if maintenance_system.maintenance_data['active']:
                    embed = discord.Embed(
                        title="🔧 Mantenimiento ACTIVO",
                        description=f"**Mensaje:** {maintenance_system.maintenance_data['message']}",
                        color=0xff9900
                    )
                    embed.add_field(
                        name="⏰ Iniciado",
                        value=f"<t:{int(datetime.fromisoformat(maintenance_system.maintenance_data['started_at']).timestamp())}:F>",
                        inline=True
                    )
                    embed.add_field(
                        name="👤 Por",
                        value=maintenance_system.maintenance_data['started_by'],
                        inline=True
                    )
                else:
                    embed = discord.Embed(
                        title="<a:verify2:1418486831993061497> Sin Mantenimiento",
                        description="El bot está operando normalmente",
                        color=0x00ff88
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            elif action.lower() == "start":
                if maintenance_system.maintenance_data['active']:
                    embed = discord.Embed(
                        title="⚠️ Mantenimiento Ya Activo",
                        description="El modo mantenimiento ya está activado",
                        color=0xff9900
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                if not message:
                    message = "El bot está en mantenimiento. Algunas funciones pueden no estar disponibles temporalmente."
                
                # Activar mantenimiento
                maintenance_system.maintenance_data = {
                    'active': True,
                    'message': message,
                    'started_at': datetime.now().isoformat(),
                    'started_by': username,
                    'notified_users': []
                }
                maintenance_system.save_maintenance_data()
                
                # Mostrar progreso inicial
                progress_embed = discord.Embed(
                    title="🔧 Activando Mantenimiento",
                    description="Enviando notificaciones a usuarios verificados...",
                    color=0xffaa00
                )
                progress_embed.add_field(name="📝 Mensaje", value=message, inline=False)
                progress_embed.add_field(name="⏳ Estado", value="Enviando notificaciones...", inline=False)
                
                message_obj = await interaction.followup.send(embed=progress_embed, ephemeral=True)
                
                # Enviar notificaciones
                successful, failed = await maintenance_system.send_maintenance_notification(message, username, "start")
                
                # Actualizar con resultados
                final_embed = discord.Embed(
                    title="🔧 Mantenimiento Activado",
                    description="El modo mantenimiento ha sido activado exitosamente",
                    color=0xff9900
                )
                final_embed.add_field(name="📝 Mensaje", value=message, inline=False)
                final_embed.add_field(name="<a:verify2:1418486831993061497> Notificaciones Enviadas", value=f"{successful}", inline=True)
                final_embed.add_field(name="❌ Fallos", value=f"{failed}", inline=True)
                final_embed.add_field(name="👤 Activado por", value=username, inline=True)
                
                await message_obj.edit(embed=final_embed)
                
            elif action.lower() == "end":
                if not maintenance_system.maintenance_data['active']:
                    embed = discord.Embed(
                        title="⚠️ Sin Mantenimiento Activo",
                        description="No hay un mantenimiento activo para finalizar",
                        color=0xff9900
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                if not message:
                    message = "El mantenimiento ha sido completado. Todas las funciones del bot están disponibles nuevamente."
                
                # Mostrar progreso inicial
                progress_embed = discord.Embed(
                    title="<a:verify2:1418486831993061497> Finalizando Mantenimiento",
                    description="Enviando notificaciones de finalización...",
                    color=0xffaa00
                )
                progress_embed.add_field(name="📝 Mensaje", value=message, inline=False)
                progress_embed.add_field(name="⏳ Estado", value="Enviando notificaciones...", inline=False)
                
                message_obj = await interaction.followup.send(embed=progress_embed, ephemeral=True)
                
                # Enviar notificaciones de finalización
                successful, failed = await maintenance_system.send_maintenance_notification(message, username, "end")
                
                # Desactivar mantenimiento
                maintenance_system.maintenance_data = {
                    'active': False,
                    'message': '',
                    'started_at': None,
                    'started_by': None,
                    'notified_users': []
                }
                maintenance_system.save_maintenance_data()
                
                # Actualizar con resultados
                final_embed = discord.Embed(
                    title="<a:verify2:1418486831993061497> Mantenimiento Finalizado",
                    description="El modo mantenimiento ha sido desactivado exitosamente",
                    color=0x00ff88
                )
                final_embed.add_field(name="📝 Mensaje", value=message, inline=False)
                final_embed.add_field(name="<a:verify2:1418486831993061497> Notificaciones Enviadas", value=f"{successful}", inline=True)
                final_embed.add_field(name="❌ Fallos", value=f"{failed}", inline=True)
                final_embed.add_field(name="👤 Finalizado por", value=username, inline=True)
                
                await message_obj.edit(embed=final_embed)
            
            logger.info(f"Owner {username} usó comando maintenance: {action} - {message[:50]}")
            
        except Exception as e:
            logger.error(f"Error en comando maintenance: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description=f"Ocurrió un error durante la operación de mantenimiento.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}```", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    return maintenance_system
