import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, List
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Modales para formularios
class MiddlemanApplicationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Aplicación para Middleman", timeout=300)
        
        self.roblox_username = discord.ui.TextInput(
            label="Tu nombre de usuario de Roblox",
            placeholder="Escribe tu nombre de Roblox exacto...",
            max_length=50,
            required=True
        )
        
        self.experience = discord.ui.TextInput(
            label="Experiencia en trading/middleman",
            placeholder="Describe tu experiencia con trades, valores, etc...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        
        self.why_middleman = discord.ui.TextInput(
            label="¿Por qué quieres ser middleman?",
            placeholder="Explica tus motivaciones para ser middleman...",
            style=discord.TextStyle.paragraph,
            max_length=800,
            required=True
        )
        
        self.availability = discord.ui.TextInput(
            label="Disponibilidad horaria",
            placeholder="Ej: Lunes a Viernes 4-8 PM, Fines de semana variable...",
            style=discord.TextStyle.paragraph,
            max_length=300,
            required=True
        )
        
        self.additional_info = discord.ui.TextInput(
            label="Información adicional (opcional)",
            placeholder="Referencias, enlaces, información extra...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.add_item(self.roblox_username)
        self.add_item(self.experience)
        self.add_item(self.why_middleman)
        self.add_item(self.availability)
        self.add_item(self.additional_info)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot = interaction.client
            
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible actualmente.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Crear aplicación en la base de datos
            result = bot.middleman_system.create_application(
                discord_user_id=str(interaction.user.id),
                discord_username=interaction.user.display_name,
                roblox_username=self.roblox_username.value,
                experience=self.experience.value,
                why_middleman=self.why_middleman.value,
                availability=self.availability.value,
                additional_info=self.additional_info.value
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="Aplicación Enviada",
                    description=f"Tu aplicación para middleman ha sido enviada exitosamente.\n\n"
                               f"**ID de Aplicación:** {result['application_id']}\n"
                               f"**Estado:** Pendiente de revisión\n\n"
                               f"Los administradores revisarán tu aplicación y te notificarán el resultado.",
                    color=0x808080
                )
                embed.add_field(name="Tiempo Estimado", value="1-3 días hábiles", inline=False)
                
                # Notificar a administradores
                await self.notify_admins_new_application(bot, result['application_id'], interaction.user)
                
            else:
                embed = discord.Embed(
                    title="Error en Aplicación",
                    description=f"No se pudo enviar tu aplicación: {result['error']}",
                    color=0x808080
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en aplicación de middleman: {e}")
            embed = discord.Embed(
                title="Error Interno",
                description="Ocurrió un error al procesar tu aplicación. Intenta nuevamente.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def notify_admins_new_application(self, bot, application_id: int, user: discord.User):
        """Notificar a administradores sobre nueva aplicación usando webhook"""
        try:
            # Usar webhook de Discord desde variables de entorno
            import os
            webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1415669876160462881/F4wOtymuOcKXp3Nc_WXrYqV-OiybtjFQbt3NCmSqmKdu4hk6mIjPAxWrGOogjruYNRYj")
            
            import aiohttp
            from discord import Webhook
            
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhook_url, session=session)
            
            embed = discord.Embed(
                title="Nueva Aplicación de Middleman",
                description=f"**Usuario:** {user.mention} ({user.display_name})\n"
                           f"**ID de Usuario:** {user.id}\n"
                           f"**ID de Aplicación:** {application_id}",
                color=0x808080,
                timestamp=datetime.utcnow()
            )
            
            embed.add_field(
                name="Acciones",
                value=f"Usa `/middleman_review {application_id}` para revisar la aplicación",
                inline=False
            )
            
            await webhook.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error notificando nueva aplicación: {e}")

class RatingModal(discord.ui.Modal):
    def __init__(self, middleman_user: discord.User):
        super().__init__(title=f"Calificar a {middleman_user.display_name}", timeout=300)
        self.middleman_user = middleman_user
        
        self.rating = discord.ui.TextInput(
            label="Calificación (1-5 estrellas)",
            placeholder="Ingresa un número del 1 al 5",
            max_length=1,
            required=True
        )
        
        self.comment = discord.ui.TextInput(
            label="Comentario sobre el servicio",
            placeholder="Describe tu experiencia con este middleman...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        
        self.trade_description = discord.ui.TextInput(
            label="Descripción del trade",
            placeholder="Ej: Trade de Robux por limiteds, 50k robux...",
            max_length=200,
            required=False
        )
        
        self.add_item(self.rating)
        self.add_item(self.comment)
        self.add_item(self.trade_description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validar calificación
            try:
                rating_value = int(self.rating.value)
                if rating_value < 1 or rating_value > 5:
                    raise ValueError("Rating must be between 1 and 5")
            except ValueError:
                embed = discord.Embed(
                    title="Calificación Inválida",
                    description="La calificación debe ser un número del 1 al 5.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            bot = interaction.client
            
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Añadir calificación
            result = bot.middleman_system.add_rating(
                middleman_discord_id=str(self.middleman_user.id),
                rater_discord_id=str(interaction.user.id),
                rater_username=interaction.user.display_name,
                rating=rating_value,
                comment=self.comment.value,
                trade_description=self.trade_description.value
            )
            
            if result["success"]:
                stars = "⭐" * rating_value
                embed = discord.Embed(
                    title="Calificación Enviada",
                    description=f"Has calificado a {self.middleman_user.mention} con {stars} ({rating_value}/5).\n\n"
                               f"Tu calificación ayuda a otros usuarios a tomar mejores decisiones.",
                    color=0x808080
                )
            else:
                embed = discord.Embed(
                    title="Error en Calificación",
                    description=f"No se pudo enviar tu calificación: {result['error']}",
                    color=0x808080
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en calificación: {e}")
            embed = discord.Embed(
                title="Error Interno",
                description="Ocurrió un error al procesar tu calificación.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ReportModal(discord.ui.Modal):
    def __init__(self, middleman_user: discord.User):
        super().__init__(title=f"Reportar a {middleman_user.display_name}", timeout=300)
        self.middleman_user = middleman_user
        
        self.category = discord.ui.TextInput(
            label="Categoría del reporte",
            placeholder="scam, unprofessional, slow_response, failed_trade, harassment, other",
            max_length=20,
            required=True
        )
        
        self.description = discord.ui.TextInput(
            label="Descripción del problema",
            placeholder="Describe detalladamente lo que ocurrió...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        
        self.add_item(self.category)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            bot = interaction.client
            
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Crear reporte
            result = bot.middleman_system.create_report(
                target_discord_id=str(self.middleman_user.id),
                reporter_discord_id=str(interaction.user.id),
                reporter_username=interaction.user.display_name,
                category=self.category.value.lower(),
                description=self.description.value
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="Reporte Enviado",
                    description=f"Tu reporte contra {self.middleman_user.mention} ha sido enviado.\n\n"
                               f"**ID de Reporte:** {result['report_id']}\n"
                               f"**Categoría:** {self.category.value}\n\n"
                               f"Los administradores investigarán tu reporte y tomarán las medidas apropiadas.",
                    color=0x808080
                )
            else:
                embed = discord.Embed(
                    title="Error en Reporte",
                    description=f"No se pudo enviar tu reporte: {result['error']}",
                    color=0x808080
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en reporte: {e}")
            embed = discord.Embed(
                title="Error Interno",
                description="Ocurrió un error al procesar tu reporte.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

def setup_commands(bot):
    """Configurar comandos de middleman"""
    
    @bot.tree.command(name="middleman_apply", description="Aplicar para convertirse en middleman")
    async def middleman_apply(interaction: discord.Interaction):
        """Comando para aplicar como middleman"""
        try:
            modal = MiddlemanApplicationModal()
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_apply: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo abrir el formulario de aplicación.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="middleman_list", description="Ver middlemans activos")
    @app_commands.describe(page="Página de resultados (opcional)")
    async def middleman_list(interaction: discord.Interaction, page: int = 1):
        """Listar middlemans activos"""
        try:
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            middlemans = bot.middleman_system.get_active_middlemans(limit=10)
            
            if not middlemans:
                embed = discord.Embed(
                    title="Sin Middlemans",
                    description="No hay middlemans activos actualmente.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="Middlemans Activos",
                description="Lista de middlemans verificados y activos",
                color=0x808080
            )
            
            for i, middleman in enumerate(middlemans, 1):
                stars = "⭐" * int(middleman.rating_average) if middleman.rating_count > 0 else "Sin calificaciones"
                embed.add_field(
                    name=f"{i}. {middleman.discord_username}",
                    value=f"**Roblox:** {middleman.roblox_username}\n"
                          f"**Rating:** {stars} ({middleman.rating_average:.1f}/5)\n"
                          f"**Trades completados:** {middleman.successful_trades}\n"
                          f"**ID:** <@{middleman.discord_user_id}>",
                    inline=False
                )
            
            embed.set_footer(text=f"Página {page} • Use /middleman rate para calificar")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_list: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo obtener la lista de middlemans.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="middleman_rate", description="Calificar a un middleman")
    @app_commands.describe(middleman="El usuario middleman a calificar")
    async def middleman_rate(interaction: discord.Interaction, middleman: discord.User):
        """Calificar middleman"""
        try:
            if middleman.id == interaction.user.id:
                embed = discord.Embed(
                    title="Acción Inválida",
                    description="No puedes calificarte a ti mismo.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            modal = RatingModal(middleman)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_rate: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo abrir el formulario de calificación.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="middleman_report", description="Reportar a un middleman")
    @app_commands.describe(middleman="El usuario middleman a reportar")
    async def middleman_report(interaction: discord.Interaction, middleman: discord.User):
        """Reportar middleman"""
        try:
            if middleman.id == interaction.user.id:
                embed = discord.Embed(
                    title="Acción Inválida",
                    description="No puedes reportarte a ti mismo.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            modal = ReportModal(middleman)
            await interaction.response.send_modal(modal)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_report: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo abrir el formulario de reporte.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Comandos de administración
    @bot.tree.command(name="middleman_review", description="[ADMIN] Revisar aplicación de middleman")
    @app_commands.describe(application_id="ID de la aplicación a revisar")
    async def middleman_review(interaction: discord.Interaction, application_id: int):
        """Revisar aplicación (solo admins)"""
        try:
            # Verificar permisos de administrador
            if not interaction.user.guild_permissions.administrator:
                embed = discord.Embed(
                    title="Sin Permisos",
                    description="Solo los administradores pueden revisar aplicaciones.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            application = bot.middleman_system.get_application(application_id)
            
            if not application:
                embed = discord.Embed(
                    title="Aplicación No Encontrada",
                    description=f"No se encontró la aplicación con ID {application_id}.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"Aplicación de Middleman #{application_id}",
                description=f"**Usuario:** <@{application.discord_user_id}> ({application.discord_username})\n"
                           f"**Roblox:** {application.roblox_username}\n"
                           f"**Estado:** {application.status}\n"
                           f"**Enviada:** {application.submitted_at.strftime('%d/%m/%Y %H:%M')}",
                color=0x808080
            )
            
            embed.add_field(name="Experiencia", value=application.experience[:500] + "..." if len(application.experience) > 500 else application.experience, inline=False)
            embed.add_field(name="¿Por qué middleman?", value=application.why_middleman[:500] + "..." if len(application.why_middleman) > 500 else application.why_middleman, inline=False)
            embed.add_field(name="Disponibilidad", value=application.availability, inline=False)
            
            if application.additional_info:
                embed.add_field(name="Información adicional", value=application.additional_info[:300] + "..." if len(application.additional_info) > 300 else application.additional_info, inline=False)
            
            embed.set_footer(text="Usa /middleman approve o /middleman reject para procesar")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_review: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo revisar la aplicación.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="middleman_approve", description="[ADMIN] Aprobar aplicación de middleman")
    @app_commands.describe(application_id="ID de la aplicación", notes="Notas del admin (opcional)")
    async def middleman_approve(interaction: discord.Interaction, application_id: int, notes: str = None):
        """Aprobar aplicación (solo admins)"""
        try:
            # Verificar permisos de administrador
            if not interaction.user.guild_permissions.administrator:
                embed = discord.Embed(
                    title="Sin Permisos",
                    description="Solo los administradores pueden aprobar aplicaciones.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            result = bot.middleman_system.approve_application(
                application_id=application_id,
                admin_id=str(interaction.user.id),
                admin_notes=notes
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="Aplicación Aprobada",
                    description=f"La aplicación #{application_id} ha sido aprobada exitosamente.\n\n"
                               f"El usuario ahora es un middleman activo.",
                    color=0x808080
                )
                embed.add_field(name="Aprobado por", value=interaction.user.mention, inline=True)
                if notes:
                    embed.add_field(name="Notas", value=notes, inline=False)
            else:
                embed = discord.Embed(
                    title="Error en Aprobación",
                    description=f"No se pudo aprobar la aplicación: {result['error']}",
                    color=0x808080
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_approve: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo aprobar la aplicación.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="middleman_reject", description="[ADMIN] Rechazar aplicación de middleman")
    @app_commands.describe(application_id="ID de la aplicación", reason="Razón del rechazo")
    async def middleman_reject(interaction: discord.Interaction, application_id: int, reason: str):
        """Rechazar aplicación (solo admins)"""
        try:
            # Verificar permisos de administrador
            if not interaction.user.guild_permissions.administrator:
                embed = discord.Embed(
                    title="Sin Permisos",
                    description="Solo los administradores pueden rechazar aplicaciones.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            if not hasattr(bot, 'middleman_system'):
                embed = discord.Embed(
                    title="Error del Sistema",
                    description="El sistema de middleman no está disponible.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            result = bot.middleman_system.reject_application(
                application_id=application_id,
                admin_id=str(interaction.user.id),
                admin_notes=reason
            )
            
            if result["success"]:
                embed = discord.Embed(
                    title="Aplicación Rechazada",
                    description=f"La aplicación #{application_id} ha sido rechazada.\n\n"
                               f"**Razón:** {reason}",
                    color=0x808080
                )
                embed.add_field(name="Rechazado por", value=interaction.user.mention, inline=True)
            else:
                embed = discord.Embed(
                    title="Error en Rechazo",
                    description=f"No se pudo rechazar la aplicación: {result['error']}",
                    color=0x808080
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en comando middleman_reject: {e}")
            embed = discord.Embed(
                title="Error",
                description="No se pudo rechazar la aplicación.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    logger.info("Comandos de middleman configurados exitosamente")