
"""
Comando para migración automática masiva a Blob Storage
Solo para owner - migra todos los usuarios automáticamente
"""
import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos de migración automática masiva"""
    
    @bot.tree.command(name="blob_auto_migrate", description="[OWNER ONLY] Migración automática masiva de todos los usuarios a Blob Storage")
    async def blob_auto_migrate_command(interaction: discord.Interaction):
        """Migrar automáticamente todos los usuarios a Blob Storage"""
        user_id = str(interaction.user.id)
        
        # Verificar que sea owner
        from main import DISCORD_OWNER_ID
        if user_id != DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando es exclusivo para el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            from blob_storage_manager import blob_manager
            from main import scraper
            
            embed = discord.Embed(
                title="🔄 Iniciando Migración Automática Masiva",
                description="Migrando todos los usuarios de local a Blob Storage...",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            total_users = 0
            successful_migrations = 0
            failed_migrations = 0
            total_servers_migrated = 0
            
            # Migrar cada usuario
            for user_id_iter, user_games in scraper.links_by_user.items():
                try:
                    user_servers = []
                    
                    # Recopilar todos los servidores del usuario
                    for game_data in user_games.values():
                        if isinstance(game_data, dict) and 'links' in game_data:
                            user_servers.extend(game_data['links'])
                    
                    if user_servers:
                        # Guardar en Blob Storage
                        success = await blob_manager.save_user_servers(user_id_iter, user_servers)
                        
                        if success:
                            successful_migrations += 1
                            total_servers_migrated += len(user_servers)
                            logger.info(f"☁️ AUTO-MIGRACIÓN: Usuario {user_id_iter} migrado exitosamente ({len(user_servers)} servidores)")
                        else:
                            failed_migrations += 1
                            logger.error(f"❌ AUTO-MIGRACIÓN: Falló migración para usuario {user_id_iter}")
                    
                    total_users += 1
                    
                    # Pequeña pausa para evitar saturar la API
                    await asyncio.sleep(0.5)
                    
                except Exception as user_error:
                    failed_migrations += 1
                    logger.error(f"❌ Error migrando usuario {user_id_iter}: {user_error}")
                    continue
            
            # Enviar resultado final
            if successful_migrations > 0:
                embed = discord.Embed(
                    title="✅ Migración Automática Masiva Completada",
                    description="La migración masiva a Blob Storage ha finalizado.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Migración Automática Masiva Finalizada",
                    description="La migración masiva terminó con problemas.",
                    color=0xffaa00
                )
            
            embed.add_field(
                name="📊 Estadísticas Finales",
                value=f"• **Total de usuarios procesados:** {total_users}\n• **Migraciones exitosas:** {successful_migrations}\n• **Migraciones fallidas:** {failed_migrations}\n• **Servidores migrados:** {total_servers_migrated}",
                inline=False
            )
            
            embed.add_field(
                name="💾 Resultado",
                value=f"• **Tasa de éxito:** {(successful_migrations/total_users*100):.1f}% ({successful_migrations}/{total_users})\n• **Promedio de servidores por usuario:** {(total_servers_migrated/successful_migrations):.1f}" if successful_migrations > 0 else "No se migraron usuarios",
                inline=False
            )
            
            embed.add_field(
                name="⏰ Completado",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )
            
            await interaction.edit_original_response(embed=embed)
            
        except Exception as e:
            logger.error(f"❌ Error en migración automática masiva: {e}")
            embed = discord.Embed(
                title="❌ Error en Migración Automática",
                description=f"Error interno: {str(e)}",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)
    
    logger.info("✅ Comando de migración automática masiva configurado")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
