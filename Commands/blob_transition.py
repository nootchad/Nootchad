
"""
Comandos para hacer la transición completa de JSON local a Blob Storage
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos de transición a Blob"""
    
    @bot.tree.command(name="blob_save_user", description="Guardar tus servidores en Blob Storage")
    async def blob_save_user_command(interaction: discord.Interaction):
        """Permitir a usuarios guardar sus propios servidores en Blob"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            from blob_storage_manager import blob_manager
            
            user_id = str(interaction.user.id)
            
            # Obtener servidores del sistema local primero
            from main import scraper
            user_servers = []
            
            if user_id in scraper.links_by_user:
                for game_id, game_data in scraper.links_by_user[user_id].items():
                    if isinstance(game_data, dict) and 'links' in game_data:
                        user_servers.extend(game_data['links'])
            
            if not user_servers:
                embed = discord.Embed(
                    title="⚠️ Sin Servidores",
                    description="No tienes servidores guardados para migrar a Blob Storage.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Guardar en Blob Storage
            success = await blob_manager.save_user_servers(user_id, user_servers)
            
            if success:
                embed = discord.Embed(
                    title="✅ Servidores Guardados en Blob Storage",
                    description=f"Se han guardado {len(user_servers)} servidores en Blob Storage.",
                    color=0x00ff00
                )
                embed.add_field(
                    name="📊 Estadísticas",
                    value=f"• **Servidores guardados:** {len(user_servers)}\n• **Usuario:** <@{user_id}>\n• **Fecha:** <t:{int(datetime.now().timestamp())}:F>",
                    inline=False
                )
                embed.add_field(
                    name="💡 Información",
                    value="Tus servidores ahora están respaldados de forma segura en Blob Storage.",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Error Guardando Servidores",
                    description="No se pudieron guardar tus servidores en Blob Storage. Inténtalo más tarde.",
                    color=0xff0000
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error en blob_save_user: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al intentar guardar tus servidores.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="blob_load_user", description="Cargar tus servidores desde Blob Storage")
    async def blob_load_user_command(interaction: discord.Interaction):
        """Permitir a usuarios cargar sus propios servidores desde Blob"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            from blob_storage_manager import blob_manager
            
            user_id = str(interaction.user.id)
            
            # Cargar servidores desde Blob Storage
            servers = await blob_manager.get_user_servers(user_id)
            
            if not servers:
                embed = discord.Embed(
                    title="⚠️ Sin Datos en Blob Storage",
                    description="No tienes servidores guardados en Blob Storage.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="💡 Sugerencia",
                    value="Usa `/blob_save_user` para guardar tus servidores actuales en Blob Storage.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="✅ Servidores Cargados desde Blob Storage",
                description=f"Se encontraron {len(servers)} servidores en Blob Storage.",
                color=0x00ff00
            )
            
            # Mostrar algunos servidores como ejemplo
            if servers:
                server_list = "\n".join([f"• {server[:50]}..." for server in servers[:5]])
                if len(servers) > 5:
                    server_list += f"\n... y {len(servers) - 5} más"
                
                embed.add_field(
                    name="🎮 Servidores Encontrados",
                    value=f"```\n{server_list}\n```",
                    inline=False
                )
            
            embed.add_field(
                name="📊 Estadísticas",
                value=f"• **Total de servidores:** {len(servers)}\n• **Usuario:** <@{user_id}>\n• **Consultado:** <t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"❌ Error en blob_load_user: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al intentar cargar tus servidores desde Blob Storage.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    logger.info("✅ Comandos de transición a Blob Storage configurados")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
