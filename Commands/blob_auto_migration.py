
<old_str>"""
Comando automático para migrar datos a Blob Storage en segundo plano
"""
import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    """
    
    @bot.tree.command(name="auto-migrate", description="[OWNER] Migración automática de datos a Blob Storage")
    async def auto_migrate_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Solo el owner puede usar este comando
        DISCORD_OWNER_ID = "916070251895091241"
        if user_id != DISCORD_OWNER_ID:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Importar el sistema de migración
            from blob_storage_manager import blob_manager
            
            # Migración automática en segundo plano
            embed = discord.Embed(
                title="🔄 Migración Automática Iniciada",
                description="La migración de datos a Blob Storage se está ejecutando en segundo plano...",
                color=0x3366ff
            )
            
            # Crear tarea en segundo plano
            async def background_migration():
                try:
                    # Cargar datos locales
                    import json
                    from pathlib import Path
                    
                    users_migrated = 0
                    errors = 0
                    
                    # Migrar desde user_game_servers.json
                    game_servers_file = Path("user_game_servers.json")
                    if game_servers_file.exists():
                        with open(game_servers_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            user_servers = data.get('user_servers', {})
                        
                        for user_id, servers in user_servers.items():
                            try:
                                success = await blob_manager.save_user_servers(user_id, servers)
                                if success:
                                    users_migrated += 1
                                else:
                                    errors += 1
                            except Exception as e:
                                logger.error(f"Error migrando usuario {user_id}: {e}")
                                errors += 1
                    
                    logger.info(f"🔄 Migración automática completada: {users_migrated} usuarios, {errors} errores")
                    
                except Exception as e:
                    logger.error(f"Error en migración automática: {e}")
            
            # Ejecutar en segundo plano
            asyncio.create_task(background_migration())
            
            embed.add_field(
                name="📋 Estado",
                value="✅ Iniciada correctamente",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Tiempo Estimado",
                value="2-5 minutos",
                inline=True
            )
            
            embed.add_field(
                name="💡 Información",
                value="La migración se ejecuta en segundo plano.\nPuedes usar otros comandos normalmente.",
                inline=False
            )
            
            embed.set_footer(text="RbxServers • Migración Automática")
            embed.timestamp = datetime.now()
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"Owner {interaction.user.name} inició migración automática")
            
        except Exception as e:
            logger.error(f"Error en comando auto-migrate: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Error iniciando migración automática: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    logger.info("✅ Comando de migración automática configurado")
    return True

# Función opcional de limpieza
def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass</old_str>
<new_str># ARCHIVO ELIMINADO - Migración automática ya completada</new_str>
