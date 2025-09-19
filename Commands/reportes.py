
"""
Sistema de reportes integral para RbxServers
Permite reportar servidores, usuarios con alts, errores del bot, etc.
"""
import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)

# ID del owner para recibir reportes
OWNER_ID = "916070251895091241"

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    Esta función será llamada automáticamente por el sistema de carga
    """
    
    @bot.tree.command(name="reportes", description="Reportar problemas: servidores, usuarios con alts, errores del bot, etc.")
    async def reportes_command(
        interaction: discord.Interaction,
        tipo: str,
        descripcion: str,
        evidencia: discord.Attachment = None,
        usuario_reportado: discord.User = None,
        servidor_link: str = None
    ):
        """Comando principal de reportes"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        logger.info(f"📋 Reporte enviado por {username} (ID: {user_id}) - Tipo: {tipo}")
        
        await interaction.response.defer()
        
        try:
            
            # Validar longitud de descripción
            if len(descripcion) < 10:
                embed = discord.Embed(
                    title="❌ Descripción Muy Corta",
                    description="La descripción debe tener al menos 10 caracteres.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if len(descripcion) > 1000:
                embed = discord.Embed(
                    title="❌ Descripción Muy Larga",
                    description="La descripción no puede exceder 1000 caracteres.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Generar ID único del reporte
            report_id = f"RPT_{int(datetime.now().timestamp())}_{user_id[:8]}"
            
            # Crear embed del reporte
            reporte_embed = await crear_embed_reporte(
                report_id, tipo, descripcion, interaction.user, 
                usuario_reportado, servidor_link, evidencia, interaction.guild
            )
            
            # Enviar al owner
            owner_sent = await enviar_a_owner(bot, reporte_embed, report_id)
            
            # Enviar confirmación al canal
            confirmacion_embed = discord.Embed(
                title="<a:verify2:1418486831993061497> Reporte Enviado Exitosamente",
                description=f"Tu reporte ha sido enviado y será revisado por el equipo de administración.",
                color=0x00ff88
            )
            confirmacion_embed.add_field(
                name="🆔 ID del Reporte:",
                value=f"`{report_id}`",
                inline=True
            )
            confirmacion_embed.add_field(
                name="📝 Tipo:",
                value=f"`{tipo}`",
                inline=True
            )
            confirmacion_embed.add_field(
                name="⏰ Enviado:",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=True
            )
            confirmacion_embed.add_field(
                name="📋 Descripción:",
                value=f"```{descripcion[:200]}{'...' if len(descripcion) > 200 else ''}```",
                inline=False
            )
            
            if usuario_reportado:
                confirmacion_embed.add_field(
                    name="👤 Usuario Reportado:",
                    value=f"{usuario_reportado.mention} (`{usuario_reportado.id}`)",
                    inline=True
                )
            
            if servidor_link:
                confirmacion_embed.add_field(
                    name="🔗 Servidor Reportado:",
                    value=f"[Link del Servidor]({servidor_link})",
                    inline=True
                )
            
            if evidencia:
                confirmacion_embed.add_field(
                    name="📎 Evidencia:",
                    value=f"[{evidencia.filename}]({evidencia.url})",
                    inline=True
                )
            
            confirmacion_embed.add_field(
                name="📨 Estado del Envío:",
                value="<a:verify2:1418486831993061497> Enviado al owner" if owner_sent else "⚠️ Error enviando al owner",
                inline=False
            )
            
            confirmacion_embed.set_footer(text=f"Reporte ID: {report_id} • RbxServers Reportes")
            
            await interaction.followup.send(embed=confirmacion_embed)
            
            # Log del reporte
            logger.info(f"<a:verify2:1418486831993061497> Reporte {report_id} procesado exitosamente - Usuario: {username}, Tipo: {tipo}")
            
        except Exception as e:
            logger.error(f"❌ Error procesando reporte de {username}: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error Procesando Reporte",
                description="Ocurrió un error al procesar tu reporte. Por favor, intenta nuevamente.",
                color=0xff0000
            )
            error_embed.add_field(
                name="🐛 Error:",
                value=f"```{str(e)[:200]}```",
                inline=False
            )
            error_embed.add_field(
                name="<a:foco:1418492184373755966> Sugerencia:",
                value="Si el problema persiste, contacta directamente al owner del bot.",
                inline=False
            )
            
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    async def crear_embed_reporte(report_id, tipo, descripcion, reporter, usuario_reportado, servidor_link, evidencia, guild):
        """Crear embed detallado del reporte para el owner"""
        
        embed = discord.Embed(
            title="📋 Nuevo Reporte",
            description=f"**Tipo:** `{tipo}`\n**ID:** `{report_id}`",
            color=0x808080,
            timestamp=datetime.now()
        )
        
        # Información del reportero
        embed.add_field(
            name="👤 Reportado por:",
            value=f"{reporter.mention}\n`{reporter.name}#{reporter.discriminator}`\nID: `{reporter.id}`",
            inline=True
        )
        
        # Información del servidor de Discord
        if guild:
            embed.add_field(
                name="🏠 Servidor Discord:",
                value=f"{guild.name}\nID: `{guild.id}`",
                inline=True
            )
        else:
            embed.add_field(
                name="🏠 Servidor Discord:",
                value="DM/Privado",
                inline=True
            )
        
        # Descripción del reporte
        embed.add_field(
            name="📋 Descripción:",
            value=f"```{descripcion}```",
            inline=False
        )
        
        # Usuario reportado (si aplica)
        if usuario_reportado:
            embed.add_field(
                name="🎯 Usuario Reportado:",
                value=f"{usuario_reportado.mention}\n`{usuario_reportado.name}#{usuario_reportado.discriminator}`\nID: `{usuario_reportado.id}`",
                inline=True
            )
        
        # Servidor reportado (si aplica)
        if servidor_link:
            embed.add_field(
                name="🔗 Servidor Reportado:",
                value=f"[Link del Servidor]({servidor_link})\n```{servidor_link}```",
                inline=False
            )
        
        # Evidencia (si aplica)
        if evidencia:
            embed.add_field(
                name="📎 Evidencia:",
                value=f"**Archivo:** [{evidencia.filename}]({evidencia.url})\n**Tamaño:** {evidencia.size} bytes",
                inline=True
            )
            
            # Si es imagen, agregarla al embed
            if evidencia.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                embed.set_image(url=evidencia.url)
        
        embed.set_footer(text=f"Reporte ID: {report_id} • Sistema de Reportes RbxServers")
        
        return embed
    
    async def enviar_a_owner(bot, embed, report_id):
        """Enviar reporte al owner del bot"""
        try:
            owner = bot.get_user(int(OWNER_ID))
            if not owner:
                owner = await bot.fetch_user(int(OWNER_ID))
            
            if owner:
                # Crear botones de acción para el owner
                view = ReporteOwnerView(report_id)
                
                await owner.send(embed=embed, view=view)
                logger.info(f"📨 Reporte {report_id} enviado exitosamente al owner")
                return True
            else:
                logger.error(f"❌ No se pudo encontrar al owner con ID {OWNER_ID}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error enviando reporte {report_id} al owner: {e}")
            return False
    
    class ReporteOwnerView(discord.ui.View):
        """Vista con botones para que el owner gestione reportes"""
        
        def __init__(self, report_id):
            super().__init__(timeout=None)  # Sin timeout para reportes
            self.report_id = report_id
        
        @discord.ui.button(label="<a:verify2:1418486831993061497> Resuelto", style=discord.ButtonStyle.success)
        async def resuelto_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="<a:verify2:1418486831993061497> Reporte Marcado como Resuelto",
                description=f"El reporte `{self.report_id}` ha sido marcado como resuelto.",
                color=0x00ff88,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="🛠️ Acción:",
                value="Marcado como resuelto por el owner",
                inline=True
            )
            embed.add_field(
                name="👤 Resuelto por:",
                value=f"{interaction.user.mention}",
                inline=True
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"<a:verify2:1418486831993061497> Reporte {self.report_id} marcado como resuelto por {interaction.user}")
        
        @discord.ui.button(label="📝 Necesita Info", style=discord.ButtonStyle.secondary)
        async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="📝 Reporte: Necesita Más Información",
                description=f"El reporte `{self.report_id}` necesita más información para ser procesado.",
                color=0xffaa00,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="🔍 Estado:",
                value="Pendiente de más información",
                inline=True
            )
            embed.add_field(
                name="👤 Revisado por:",
                value=f"{interaction.user.mention}",
                inline=True
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"📝 Reporte {self.report_id} marcado como necesita info por {interaction.user}")
        
        @discord.ui.button(label="🚫 Rechazado", style=discord.ButtonStyle.danger)
        async def rechazado_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="🚫 Reporte Rechazado",
                description=f"El reporte `{self.report_id}` ha sido rechazado.",
                color=0xff0000,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="❌ Acción:",
                value="Rechazado por el owner",
                inline=True
            )
            embed.add_field(
                name="👤 Rechazado por:",
                value=f"{interaction.user.mention}",
                inline=True
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            logger.info(f"🚫 Reporte {self.report_id} rechazado por {interaction.user}")
    
    
    
    logger.info("<a:verify2:1418486831993061497> Sistema de reportes configurado exitosamente")
    return True

# Función opcional de limpieza cuando se recarga el módulo
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
