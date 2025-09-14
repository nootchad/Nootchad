"""
Comandos para migrar datos desde JSON local a Blob Storage
Sistema simplificado alternativo a Supabase
"""
import discord
from discord.ext import commands
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos de migración a Blob"""

    @bot.tree.command(name="blob_test", description="[OWNER ONLY] Probar conexión con Blob Storage")
    async def blob_test_command(interaction: discord.Interaction):
        """Probar conexión con Blob Storage"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import is_owner_or_delegated, DISCORD_OWNER_ID
        if user_id != DISCORD_OWNER_ID and user_id not in (getattr(__import__('main'), 'delegated_owners', set())):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando es exclusivo para el owner del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            from blob_storage_manager import test_blob_connection

            embed = discord.Embed(
                title="🧪 Probando Blob Storage...",
                description="Verificando conexión y funcionalidades básicas...",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Probar conexión
            success = await test_blob_connection()

            if success:
                embed = discord.Embed(
                    title="✅ Blob Storage - Conexión Exitosa",
                    description="La conexión con Blob Storage está funcionando correctamente.",
                    color=0x00ff00
                )
                embed.add_field(
                    name="✅ Estado",
                    value="Conectado y operativo",
                    inline=True
                )
                embed.add_field(
                    name="🔧 Funcionalidades",
                    value="Upload ✅\nDownload ✅\nDelete ✅",
                    inline=True
                )
                embed.add_field(
                    name="⏰ Fecha",
                    value=f"<t:{int(datetime.now().timestamp())}:F>",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="❌ Blob Storage - Error de Conexión",
                    description="No se pudo conectar con Blob Storage. Verifica el token BLOB_READ_WRITE_TOKEN.",
                    color=0xff0000
                )
                embed.add_field(
                    name="🔍 Posibles Causas",
                    value="• Token inválido o expirado\n• Problemas de red\n• Servicio no disponible",
                    inline=False
                )

            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error en blob_test: {e}")
            embed = discord.Embed(
                title="❌ Error en Prueba",
                description=f"Error interno: {str(e)}",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)

    @bot.tree.command(name="blob_migrate", description="[OWNER ONLY] Migrar datos locales a Blob Storage")
    async def blob_migrate_command(interaction: discord.Interaction):
        """Comando para migrar datos locales a Blob Storage (solo owner)"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            from blob_storage_manager import migrate_to_blob_storage, backup_all_data_to_blob

            embed = discord.Embed(
                title="📦 Iniciando Migración a Blob Storage",
                description="Migrando datos de servidores de usuarios...",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Migrar datos de servidores de usuarios
            migration_results = await migrate_to_blob_storage()

            embed = discord.Embed(
                title="📊 Migración de Servidores Completada",
                color=0x00aa55
            )
            embed.add_field(
                name="👥 Usuarios Migrados",
                value=str(migration_results.get('users_migrated', 0)),
                inline=True
            )
            embed.add_field(
                name="🎮 Servidores Migrados",
                value=str(migration_results.get('servers_migrated', 0)),
                inline=True
            )
            embed.add_field(
                name="❌ Errores",
                value=str(migration_results.get('errors', 0)),
                inline=True
            )

            await interaction.edit_original_response(embed=embed)

            # Hacer backup completo de todos los archivos JSON
            embed.add_field(
                name="📦 Iniciando Backup Completo...",
                value="Respaldando todos los archivos JSON...",
                inline=False
            )
            await interaction.edit_original_response(embed=embed)

            backup_success = await backup_all_data_to_blob()

            if backup_success:
                embed.add_field(
                    name="✅ Backup Completado",
                    value="Todos los archivos JSON han sido respaldados en Blob Storage",
                    inline=False
                )
                embed.color = 0x00ff00
            else:
                embed.add_field(
                    name="⚠️ Backup Parcial",
                    value="Algunos archivos no pudieron ser respaldados",
                    inline=False
                )
                embed.color = 0xffaa00

            embed.add_field(
                name="⏰ Completado",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )

            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error en blob_migrate: {e}")
            embed = discord.Embed(
                title="❌ Error en Migración",
                description=f"Error interno: {str(e)}",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)

    @bot.tree.command(name="blob_status", description="[OWNER ONLY] Ver estado de archivos en Blob Storage")
    async def blob_status_command(interaction: discord.Interaction):
        """Ver estado y archivos en Blob Storage"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            from blob_storage_manager import blob_manager

            # Listar archivos
            files = await blob_manager.list_files()

            embed = discord.Embed(
                title="📋 Estado de Blob Storage",
                description=f"Total de archivos: {len(files)}",
                color=0x0099ff
            )

            if files:
                # Categorizar archivos
                user_servers = [f for f in files if f.startswith('user_servers_')]
                user_verifications = [f for f in files if f.startswith('user_verification_')]
                scam_reports = [f for f in files if f.startswith('scam_report_')]
                backups = [f for f in files if f.startswith('backup_')]
                other_files = [f for f in files if not any(f.startswith(prefix) for prefix in ['user_servers_', 'user_verification_', 'scam_report_', 'backup_'])]

                embed.add_field(
                    name="🎮 Servidores de Usuarios",
                    value=f"{len(user_servers)} archivos",
                    inline=True
                )
                embed.add_field(
                    name="✅ Verificaciones",
                    value=f"{len(user_verifications)} archivos",
                    inline=True
                )
                embed.add_field(
                    name="🚨 Reportes de Scam",
                    value=f"{len(scam_reports)} archivos",
                    inline=True
                )
                embed.add_field(
                    name="📦 Backups",
                    value=f"{len(backups)} archivos",
                    inline=True
                )
                embed.add_field(
                    name="📄 Otros",
                    value=f"{len(other_files)} archivos",
                    inline=True
                )

                # Mostrar algunos archivos recientes
                if len(files) <= 10:
                    file_list = "\n".join([f"• `{f}`" for f in files[:10]])
                else:
                    file_list = "\n".join([f"• `{f}`" for f in files[:10]]) + f"\n... y {len(files) - 10} más"

                embed.add_field(
                    name="📁 Archivos (primeros 10)",
                    value=file_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📭 Sin Archivos",
                    value="No hay archivos almacenados en Blob Storage",
                    inline=False
                )

            embed.add_field(
                name="⏰ Consultado",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error en blob_status: {e}")
            embed = discord.Embed(
                title="❌ Error Consultando Estado",
                description=f"Error interno: {str(e)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


    @bot.tree.command(name="blob_backup", description="[OWNER ONLY] Hacer backup completo a Blob Storage")
    async def blob_backup_command(interaction: discord.Interaction):
        """Comando para hacer backup completo a Blob Storage (solo owner)"""
        user_id = str(interaction.user.id)

        # Verificar que sea owner o delegado
        from main import DISCORD_OWNER_ID, delegated_owners, is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            from blob_storage_manager import backup_all_data_to_blob

            embed = discord.Embed(
                title="📦 Iniciando Backup Completo...",
                description="Respaldando todos los archivos JSON...",
                color=0xffaa00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

            backup_success = await backup_all_data_to_blob()

            if backup_success:
                embed = discord.Embed(
                    title="✅ Backup Completado",
                    description="Todos los archivos JSON han sido respaldados en Blob Storage",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="⚠️ Backup Parcial",
                    description="Algunos archivos no pudieron ser respaldados",
                    color=0xffaa00
                )

            embed.add_field(
                name="⏰ Completado",
                value=f"<t:{int(datetime.now().timestamp())}:F>",
                inline=False
            )

            await interaction.edit_original_response(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error en blob_backup: {e}")
            embed = discord.Embed(
                title="❌ Error en Backup",
                description=f"Error interno: {str(e)}",
                color=0xff0000
            )
            await interaction.edit_original_response(embed=embed)

    logger.info("✅ Comandos de migración a Blob Storage configurados")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass