"""
Sistema de configuración de roles automáticos para usuarios verificados
Owner only - Asigna roles a usuarios verificados del bot en el servidor
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time
import os

logger = logging.getLogger(__name__)

# Variables globales para el sistema de monitoreo
verification_monitor_task = None
last_verification_check = None

def setup_commands(bot):
    """Función requerida para configurar comandos de roles automáticos"""
    global verification_monitor_task
    
    # Iniciar el sistema de monitoreo automático
    if verification_monitor_task is None:
        verification_monitor_task = bot.loop.create_task(monitor_verification_changes(bot))
        logger.info("<a:verify2:1418486831993061497> Sistema de monitoreo de verificaciones iniciado")
        
        # Ejecutar verificación inicial de usuarios ya verificados
        bot.loop.create_task(initial_role_assignment_check(bot))
        logger.info("<a:loading:1418504453580918856> Iniciando verificación inicial de roles para usuarios verificados...")

    @bot.tree.command(name="setuprole", description="[OWNER] Configurar rol automático para usuarios verificados en este servidor")
    async def setuprole_command(
        interaction: discord.Interaction,
        rol: discord.Role,
        activar: bool = True
    ):
        """Configurar rol automático para usuarios verificados"""
        try:
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"

            # Verificar que es owner
            from main import DISCORD_OWNER_ID, is_owner_or_delegated
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Solo el <:1000182644:1396049313481625611> **owner** puede usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer()

            guild_id = str(interaction.guild_id)
            guild_name = interaction.guild.name

            logger.info(f"<:1000182644:1396049313481625611> Owner {username} configurando rol automático en {guild_name}")

            # Verificar permisos del bot para gestionar roles
            bot_member = interaction.guild.get_member(bot.user.id)
            if not bot_member.guild_permissions.manage_roles:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Permisos Insuficientes",
                    description="El bot necesita el permiso **Gestionar Roles** para funcionar.",
                    color=0xff0000
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Solución:",
                    value="• Ve a Configuración del Servidor\n• Roles → RbxServers Bot\n• Activa 'Gestionar Roles'",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Verificar jerarquía de roles
            if rol.position >= bot_member.top_role.position:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Error de Jerarquía",
                    description=f"No puedo asignar el rol **{rol.name}** porque está por encima de mi rol más alto.",
                    color=0xff0000
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Solución:",
                    value="• Mueve el rol del bot por encima del rol objetivo\n• O selecciona un rol más bajo en la jerarquía",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Guardar configuración
            config_saved = save_role_config(guild_id, guild_name, rol.id, rol.name, user_id, activar)

            if not config_saved:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Error de Configuración",
                    description="No se pudo guardar la configuración del rol automático.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if activar:
                # Buscar usuarios verificados en el servidor
                verified_users = get_verified_users_in_guild(interaction.guild)

                if not verified_users:
                    embed = discord.Embed(
                        title="<:1000182584:1396049547838492672> Configuración Guardada",
                        description=f"Rol automático configurado pero no hay usuarios verificados en este servidor actualmente.",
                        color=0xff9900
                    )
                    embed.add_field(
                        name="⚙️ **Configuración**",
                        value=f"• **Servidor:** {guild_name}\n• **Rol:** {rol.mention}\n• **Estado:** Activo <:verify:1396087763388072006>\n• **Configurado por:** <:1000182644:1396049313481625611> {username}",
                        inline=False
                    )
                    embed.add_field(
                        name="<a:foco:1418492184373755966> **Funcionamiento**",
                        value="• Los nuevos usuarios verificados recibirán este rol automáticamente\n• Usa `/assignroles` para asignar roles a usuarios ya verificados",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                # Asignar roles a usuarios verificados
                success_count, failed_count, results = await assign_roles_to_verified_users(
                    interaction.guild, rol, verified_users
                )

                # Embed de resultado
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Configuración y Asignación Completada",
                    description=f"Rol automático configurado y asignado a usuarios verificados.",
                    color=0x00aa55
                )

                embed.add_field(
                    name="⚙️ **Configuración**",
                    value=f"• **Servidor:** {guild_name}\n• **Rol:** {rol.mention}\n• **Estado:** Activo <:verify:1396087763388072006>\n• **Configurado por:** <:1000182644:1396049313481625611> {username}",
                    inline=False
                )

                embed.add_field(
                    name="<:stats:1418490788437823599> **Resultados de Asignación**",
                    value=f"• **Exitosos:** {success_count} usuarios\n• **Fallidos:** {failed_count} usuarios\n• **Total procesados:** {len(verified_users)} usuarios",
                    inline=True
                )

                embed.add_field(
                    name="<:1000182657:1396060091366637669> **Funcionamiento Futuro**",
                    value="Los nuevos usuarios que se verifiquen recibirán este rol automáticamente",
                    inline=True
                )

                # Mostrar algunos resultados si hay fallos
                if failed_count > 0 and results:
                    failed_examples = []
                    for result in results[:3]:  # Mostrar máximo 3 ejemplos
                        if not result['success']:
                            failed_examples.append(f"• {result['username']}: {result['error']}")

                    if failed_examples:
                        embed.add_field(
                            name="<:1000182563:1396420770904932372> **Errores (ejemplos)**",
                            value="\n".join(failed_examples),
                            inline=False
                        )

            else:
                # Desactivar configuración
                embed = discord.Embed(
                    title="⏹️ Configuración Desactivada",
                    description=f"El rol automático para **{rol.name}** ha sido desactivado en este servidor.",
                    color=0xff9900
                )
                embed.add_field(
                    name="<:stats:1418490788437823599> **Estado**",
                    value=f"• **Servidor:** {guild_name}\n• **Rol:** {rol.mention}\n• **Estado:** Desactivado\n• **Modificado por:** <:1000182644:1396049313481625611> {username}",
                    inline=False
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> **Nota**",
                    value="• Los usuarios existentes conservan el rol\n• Los nuevos usuarios verificados no recibirán el rol\n• Puedes reactivarlo usando este comando con `activar: True`",
                    inline=False
                )

            embed.set_footer(text="<a:foco:1418492184373755966> Usa /assignroles para asignar roles manualmente • Configuración guardada automáticamente")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando setuprole para {username}: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al configurar el rol automático.",
                color=0xff0000
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="assignroles", description="[OWNER] Asignar roles manualmente a todos los usuarios verificados en el servidor")
    async def assignroles_command(interaction: discord.Interaction):
        """Asignar roles manualmente a usuarios verificados"""
        try:
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"

            # Verificar que es owner
            from main import DISCORD_OWNER_ID, is_owner_or_delegated
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Solo el <:1000182644:1396049313481625611> **owner** puede usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer()

            guild_id = str(interaction.guild_id)

            # Obtener configuración del servidor
            role_config = get_role_config(guild_id)

            if not role_config or not role_config.get('active', False):
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Sin Configuración",
                    description="No hay configuración de rol automático activa en este servidor.",
                    color=0xff9900
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Solución:",
                    value="• Usa `/setuprole` para configurar un rol automático primero\n• Asegúrate de que esté activado",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Obtener el rol configurado
            role_id = role_config.get('role_id')
            rol = interaction.guild.get_role(role_id)

            if not rol:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Rol No Encontrado",
                    description=f"El rol configurado (ID: {role_id}) ya no existe en el servidor.",
                    color=0xff0000
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Solución:",
                    value="• Configura un nuevo rol con `/setuprole`\n• Verifica que el rol no haya sido eliminado",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Buscar usuarios verificados
            verified_users = await get_verified_users_in_guild(interaction.guild)

            if not verified_users:
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Sin Usuarios",
                    description="No hay usuarios verificados con el bot en este servidor.",
                    color=0xff9900
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> **Información**",
                    value="• Los usuarios deben estar verificados con `/verify`\n• Los usuarios deben estar en este servidor\n• El proceso es automático cuando se configure el rol",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Asignar roles
            success_count, failed_count, results = await assign_roles_to_verified_users(
                interaction.guild, rol, verified_users
            )

            # Embed de resultado
            embed = discord.Embed(
                title="<:verify:1396087763388072006> Asignación Manual Completada",
                description=f"Roles asignados manualmente a usuarios verificados.",
                color=0x00aa55
            )

            embed.add_field(
                name="<:stats:1418490788437823599> **Resultados**",
                value=f"• **Exitosos:** {success_count} usuarios\n• **Fallidos:** {failed_count} usuarios\n• **Total procesados:** {len(verified_users)} usuarios",
                inline=True
            )

            embed.add_field(
                name="⚙️ **Configuración Actual**",
                value=f"• **Rol:** {rol.mention}\n• **Estado:** Activo <:verify:1396087763388072006>\n• **Servidor:** {interaction.guild.name}",
                inline=True
            )

            # Mostrar algunos resultados si hay fallos
            if failed_count > 0 and results:
                failed_examples = []
                success_examples = []

                for result in results:
                    if not result['success'] and len(failed_examples) < 3:
                        failed_examples.append(f"• {result['username']}: {result['error']}")
                    elif result['success'] and len(success_examples) < 3:
                        success_examples.append(f"• {result['username']}: Rol asignado")

                if failed_examples:
                    embed.add_field(
                        name="<:1000182563:1396420770904932372> **Errores (ejemplos)**",
                        value="\n".join(failed_examples),
                        inline=False
                    )

                if success_examples and success_count > 0:
                    embed.add_field(
                        name="<:verify:1396087763388072006> **Exitosos (ejemplos)**",
                        value="\n".join(success_examples),
                        inline=False
                    )

            embed.set_footer(text="<a:foco:1418492184373755966> Los nuevos usuarios verificados recibirán el rol automáticamente")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando assignroles para {username}: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al asignar roles.",
                color=0xff0000
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="roleconfig", description="[OWNER] Ver configuración actual de roles automáticos en el servidor")
    async def roleconfig_command(interaction: discord.Interaction):
        """Ver configuración actual de roles automáticos"""
        try:
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"

            # Verificar que es owner
            from main import DISCORD_OWNER_ID, is_owner_or_delegated
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Solo el <:1000182644:1396049313481625611> **owner** puede usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer()

            guild_id = str(interaction.guild_id)
            role_config = get_role_config(guild_id)

            if not role_config:
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Sin Configuración",
                    description="No hay configuración de rol automático en este servidor.",
                    color=0xff9900
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Configurar:",
                    value="Usa `/setuprole` para configurar un rol automático",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Obtener información del rol
            role_id = role_config.get('role_id')
            rol = interaction.guild.get_role(role_id)
            role_mention = rol.mention if rol else f"Rol eliminado (ID: {role_id})"

            # Estado
            is_active = role_config.get('active', False)
            status_emoji = "<:verify:1396087763388072006>" if is_active else "⏹️"
            status_text = "Activo" if is_active else "Desactivado"

            # Contar usuarios verificados en el servidor
            verified_users = get_verified_users_in_guild(interaction.guild)
            verified_count = len(verified_users)

            embed = discord.Embed(
                title="⚙️ Configuración de Roles Automáticos",
                description=f"Configuración actual para **{interaction.guild.name}**",
                color=0x00aa55 if is_active else 0xff9900
            )

            embed.add_field(
                name="<:stats:1418490788437823599> **Estado General**",
                value=f"• **Estado:** {status_emoji} {status_text}\n• **Rol configurado:** {role_mention}\n• **Servidor:** {interaction.guild.name}",
                inline=False
            )

            embed.add_field(
                name="<:1000182644:1396049313481625611> **Configuración**",
                value=f"• **Configurado por:** <@{role_config.get('configured_by', 'Desconocido')}>\n• **Fecha:** {role_config.get('configured_at', 'Desconocido')}\n• **Última actualización:** {role_config.get('updated_at', 'Desconocido')}",
                inline=False
            )

            embed.add_field(
                name="<:1000182182:1396049500375875646> **Usuarios Verificados**",
                value=f"• **En este servidor:** {verified_count} usuarios\n• **Estado del rol:** {'Se asigna automáticamente' if is_active else 'No se asigna'}\n• **Asignación manual:** Disponible con `/assignroles`",
                inline=False
            )

            if not rol and role_id:
                embed.add_field(
                    name="<:1000182563:1396420770904932372> **Problema Detectado**",
                    value=f"El rol configurado (ID: {role_id}) ya no existe en el servidor. Configura uno nuevo con `/setuprole`.",
                    inline=False
                )

            embed.add_field(
                name="<:1000182751:1396420551798558781> **Comandos Disponibles**",
                value="• `/setuprole` - Configurar o cambiar rol\n• `/assignroles` - Asignar manualmente\n• `/roleconfig` - Ver esta configuración",
                inline=False
            )

            embed.set_footer(text="<a:foco:1418492184373755966> La configuración se guarda automáticamente y persiste al reiniciar el bot")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando roleconfig para {username}: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al obtener la configuración.",
                color=0xff0000
            )
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="testrole", description="[OWNER] Probar asignación automática de roles para un usuario")
    async def testrole_command(interaction: discord.Interaction, usuario: discord.Member):
        """Probar asignación de rol automático"""
        try:
            user_id = str(interaction.user.id)

            # Verificar que es owner
            from main import is_owner_or_delegated
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Solo el <:1000182644:1396049313481625611> **owner** puede usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer()

            # Probar asignación automática
            success = await auto_assign_verification_role(str(usuario.id), interaction.guild, bot)

            if success:
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Test Exitoso",
                    description=f"Rol asignado exitosamente a {usuario.mention}",
                    color=0x00aa55
                )
            else:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Test Fallido",
                    description=f"No se pudo asignar rol a {usuario.mention}. Verifica la configuración.",
                    color=0xff0000
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando testrole: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al probar la asignación.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="monitorstatus", description="[OWNER] Ver estado del sistema de monitoreo automático de roles")
    async def monitorstatus_command(interaction: discord.Interaction):
        """Ver estado del monitoreo automático"""
        try:
            user_id = str(interaction.user.id)

            # Verificar que es owner
            from main import is_owner_or_delegated
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Acceso Denegado",
                    description="Solo el <:1000182644:1396049313481625611> **owner** puede usar este comando.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            global verification_monitor_task, last_verification_check

            # Estado del monitoreo
            is_running = verification_monitor_task is not None and not verification_monitor_task.done()
            status_emoji = "<:verify:1396087763388072006>" if is_running else "<:1000182563:1396420770904932372>"
            status_text = "Activo" if is_running else "Inactivo"

            # Obtener configuraciones activas
            all_configs = get_all_role_configs()
            active_configs = {k: v for k, v in all_configs.items() if v.get('active', False)}

            embed = discord.Embed(
                title="<:1000182751:1396420551798558781> Estado del Monitoreo Automático",
                description="Sistema que detecta nuevas verificaciones y asigna roles automáticamente",
                color=0x00aa55 if is_running else 0xff0000
            )

            embed.add_field(
                name="<:stats:1418490788437823599> **Estado General**",
                value=f"• **Monitor:** {status_emoji} {status_text}\n• **Última verificación:** {last_verification_check or 'Nunca'}\n• **Servidores configurados:** {len(active_configs)}",
                inline=False
            )

            if active_configs:
                server_list = []
                for guild_id, config in list(active_configs.items())[:5]:  # Mostrar máximo 5
                    guild = bot.get_guild(int(guild_id))
                    guild_name = guild.name if guild else config.get('guild_name', 'Servidor no encontrado')
                    role_name = config.get('role_name', 'Rol desconocido')
                    server_list.append(f"• **{guild_name}**: {role_name}")

                if len(active_configs) > 5:
                    server_list.append(f"• ... y {len(active_configs) - 5} más")

                embed.add_field(
                    name="⚙️ **Configuraciones Activas**",
                    value="\n".join(server_list) if server_list else "Ninguna",
                    inline=False
                )

            embed.add_field(
                name="<:1000182657:1396060091366637669> **Funcionamiento**",
                value="• Monitorea `followers.json` cada 10 segundos\n• Detecta nuevas verificaciones automáticamente\n• Asigna roles según configuración del servidor\n• Solo afecta usuarios en servidores configurados",
                inline=False
            )

            if not is_running:
                embed.add_field(
                    name="<:1000182563:1396420770904932372> **Problema**",
                    value="El sistema de monitoreo no está funcionando. Reinicia el bot o usa `/testrole` para pruebas manuales.",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando monitorstatus: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Ocurrió un error al obtener el estado del monitoreo.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    logger.info("<a:verify2:1418486831993061497> Comandos de configuración de roles cargados exitosamente")
    return True

async def get_verified_users_in_guild(guild: discord.Guild) -> List[Dict]:
    """Obtener usuarios verificados que están en el servidor"""
    try:
        from main import roblox_verification

        verified_in_guild = []

        for discord_id, user_data in roblox_verification.verified_users.items():
            try:
                member = guild.get_member(int(discord_id))
                if member:
                    verified_in_guild.append({
                        'discord_id': discord_id,
                        'member': member,
                        'roblox_username': user_data.get('roblox_username', 'Unknown'),
                        'verified_at': user_data.get('verified_at', 0)
                    })
            except Exception as e:
                logger.debug(f"Error procesando usuario verificado {discord_id}: {e}")
                continue

        logger.info(f"Encontrados {len(verified_in_guild)} usuarios verificados en {guild.name}")
        return verified_in_guild

    except Exception as e:
        logger.error(f"Error obteniendo usuarios verificados en {guild.name}: {e}")
        return []

async def assign_roles_to_verified_users(guild: discord.Guild, role: discord.Role, verified_users: List[Dict]) -> tuple:
    """Asignar rol a lista de usuarios verificados"""
    success_count = 0
    failed_count = 0
    results = []

    for user_data in verified_users:
        try:
            member = user_data['member']
            username = f"{member.name}#{member.discriminator}"

            # Verificar si ya tiene el rol
            if role in member.roles:
                results.append({
                    'username': username,
                    'success': True,
                    'error': 'Ya tenía el rol'
                })
                success_count += 1
                continue

            # Asignar el rol
            await member.add_roles(role, reason="Rol automático para usuario verificado del bot")

            results.append({
                'username': username,
                'success': True,
                'error': None
            })
            success_count += 1

            logger.info(f"✅ Rol {role.name} asignado a {username} en {guild.name}")

            # Pequeña pausa para evitar rate limits
            await asyncio.sleep(0.5)

        except discord.Forbidden:
            failed_count += 1
            results.append({
                'username': username,
                'success': False,
                'error': 'Sin permisos'
            })
            logger.warning(f"❌ Sin permisos para asignar rol a {username}")

        except discord.HTTPException as e:
            failed_count += 1
            results.append({
                'username': username,
                'success': False,
                'error': f'Error HTTP: {e.status}'
            })
            logger.error(f"❌ Error HTTP asignando rol a {username}: {e}")

        except Exception as e:
            failed_count += 1
            results.append({
                'username': username,
                'success': False,
                'error': str(e)[:50]
            })
            logger.error(f"❌ Error asignando rol a {username}: {e}")

    logger.info(f"Asignación completada: {success_count} éxitos, {failed_count} fallos")
    return success_count, failed_count, results

def save_role_config(guild_id: str, guild_name: str, role_id: int, role_name: str, configured_by: str, active: bool) -> bool:
    """Guardar configuración de rol automático"""
    try:
        config_file = Path("role_config.json")

        # Cargar configuración existente
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'guilds': {}, 'metadata': {}}

        # Actualizar configuración del servidor
        data['guilds'][guild_id] = {
            'guild_name': guild_name,
            'role_id': role_id,
            'role_name': role_name,
            'active': active,
            'configured_by': configured_by,
            'configured_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # Actualizar metadata
        data['metadata'] = {
            'total_guilds': len(data['guilds']),
            'active_guilds': len([g for g in data['guilds'].values() if g.get('active', False)]),
            'last_updated': datetime.now().isoformat()
        }

        # Guardar archivo
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"✅ Configuración de rol guardada para servidor {guild_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Error guardando configuración de rol: {e}")
        return False

def get_role_config(guild_id: str) -> Optional[Dict]:
    """Obtener configuración de rol para un servidor"""
    try:
        config_file = Path("role_config.json")

        if not config_file.exists():
            return None

        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data.get('guilds', {}).get(guild_id)

    except Exception as e:
        logger.error(f"❌ Error obteniendo configuración de rol para {guild_id}: {e}")
        return None

def get_all_role_configs() -> Dict:
    """Obtener todas las configuraciones de roles (para uso futuro)"""
    try:
        config_file = Path("role_config.json")

        if not config_file.exists():
            return {}

        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return data.get('guilds', {})

    except Exception as e:
        logger.error(f"❌ Error obteniendo todas las configuraciones: {e}")
        return {}

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass

# Utility function to automatically assign roles upon verification
async def auto_assign_verification_role(discord_id: str, guild: discord.Guild, bot: commands.Bot) -> bool:
    """Automatically assigns the configured role to a verified user."""
    try:
        # Get the role configuration for the guild
        role_config = get_role_config(str(guild.id))

        if not role_config or not role_config.get('active', False):
            logger.info(f"No active role configuration found for guild {guild.id}")
            return False

        role_id = role_config.get('role_id')
        role = guild.get_role(role_id)

        if not role:
            logger.error(f"Configured role (ID: {role_id}) not found in guild {guild.id}")
            return False

        # Get the member object
        member = guild.get_member(int(discord_id))
        if not member:
            logger.warning(f"Member with Discord ID {discord_id} not found in guild {guild.id}")
            return False

        # Check if the member already has the role
        if role in member.roles:
            logger.info(f"Member {member.name} already has role {role.name} in guild {guild.id}")
            return True

        # Assign the role
        await member.add_roles(role, reason="Automatic role assignment upon verification")
        logger.info(f"Successfully assigned role {role.name} to {member.name} in guild {guild.id}")
        return True

    except Exception as e:
        logger.error(f"Error assigning role to user {discord_id} in guild {guild.id}: {e}")
        return False

# Listen for verification events and trigger role assignment (assuming this is triggered from main.py)
async def on_user_verified(bot: commands.Bot, discord_id: str, guild_id: str):
    """This function is called when a user is verified."""
    guild = bot.get_guild(int(guild_id))
    if not guild:
        logger.warning(f"Guild with ID {guild_id} not found.")
        return

    await auto_assign_verification_role(discord_id, guild, bot)

# That function (on_user_verified) should be called from main.py

async def monitor_verification_changes(bot: commands.Bot):
    """Monitorea cambios en el archivo de verificaciones y asigna roles automáticamente"""
    global last_verification_check
    
    followers_file = "followers.json"
    known_verified_users = set()
    
    logger.info("🔍 Iniciando monitoreo automático de verificaciones...")
    
    # Cargar usuarios verificados iniciales
    try:
        if Path(followers_file).exists():
            with open(followers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                known_verified_users = set(data.get('verified_users', {}).keys())
                logger.info(f"📊 Cargados {len(known_verified_users)} usuarios verificados conocidos")
    except Exception as e:
        logger.error(f"Error cargando usuarios verificados iniciales: {e}")
    
    while True:
        try:
            # Verificar si el archivo existe
            if not Path(followers_file).exists():
                await asyncio.sleep(10)
                continue
            
            # Leer archivo actual
            with open(followers_file, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
            
            current_verified_users = set(current_data.get('verified_users', {}).keys())
            
            # Detectar nuevos usuarios verificados
            new_users = current_verified_users - known_verified_users
            
            if new_users:
                logger.info(f"🆕 Detectados {len(new_users)} nuevos usuarios verificados")
                last_verification_check = datetime.now().strftime("%H:%M:%S")
                
                # Procesar cada nuevo usuario
                for discord_id in new_users:
                    user_data = current_data['verified_users'].get(discord_id, {})
                    roblox_username = user_data.get('roblox_username', 'Unknown')
                    
                    logger.info(f"🔄 Procesando nuevo usuario verificado: {roblox_username} (ID: {discord_id})")
                    
                    # Buscar en todos los servidores donde está el bot
                    await process_user_verification_in_all_guilds(bot, discord_id, roblox_username)
                
                # Actualizar conjunto de usuarios conocidos
                known_verified_users = current_verified_users
            
            # Esperar antes del siguiente check
            await asyncio.sleep(10)  # Verificar cada 10 segundos
            
        except FileNotFoundError:
            # El archivo no existe, esperar
            await asyncio.sleep(10)
            continue
        except json.JSONDecodeError as e:
            logger.error(f"Error leyendo JSON de verificaciones: {e}")
            await asyncio.sleep(10)
            continue
        except Exception as e:
            logger.error(f"Error en monitoreo de verificaciones: {e}")
            await asyncio.sleep(30)  # Esperar más tiempo si hay error
            continue

async def process_user_verification_in_all_guilds(bot: commands.Bot, discord_id: str, roblox_username: str):
    """Procesa la verificación de un usuario en todos los servidores configurados"""
    try:
        # Obtener todas las configuraciones activas
        all_configs = get_all_role_configs()
        active_configs = {k: v for k, v in all_configs.items() if v.get('active', False)}
        
        if not active_configs:
            logger.debug(f"No hay configuraciones activas para procesar usuario {roblox_username}")
            return
        
        successful_assignments = 0
        total_attempts = 0
        
        # Procesar cada servidor configurado
        for guild_id, config in active_configs.items():
            try:
                guild = bot.get_guild(int(guild_id))
                if not guild:
                    logger.warning(f"Servidor {guild_id} no encontrado para usuario {roblox_username}")
                    continue
                
                # Verificar si el usuario está en este servidor
                member = guild.get_member(int(discord_id))
                if not member:
                    logger.debug(f"Usuario {roblox_username} no está en servidor {guild.name}")
                    continue
                
                total_attempts += 1
                
                # Intentar asignar rol
                success = await auto_assign_verification_role(discord_id, guild, bot)
                
                if success:
                    successful_assignments += 1
                    logger.info(f"✅ Rol asignado automáticamente a {roblox_username} en {guild.name}")
                else:
                    logger.warning(f"❌ No se pudo asignar rol a {roblox_username} en {guild.name}")
                
                # Pequeña pausa entre asignaciones
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error procesando servidor {guild_id} para usuario {roblox_username}: {e}")
                continue
        
        if total_attempts > 0:
            logger.info(f"📊 Usuario {roblox_username}: {successful_assignments}/{total_attempts} asignaciones exitosas")
        else:
            logger.debug(f"Usuario {roblox_username} no está en ningún servidor configurado")
            
    except Exception as e:
        logger.error(f"Error procesando verificación de usuario {discord_id}: {e}")

async def initial_role_assignment_check(bot: commands.Bot):
    """Verificar al inicio del bot si hay usuarios verificados sin el rol configurado"""
    try:
        # Esperar un poco para que el bot termine de inicializar
        await asyncio.sleep(10)
        
        logger.info("🔍 Iniciando verificación inicial de roles para usuarios verificados...")
        
        # Obtener todas las configuraciones activas
        all_configs = get_all_role_configs()
        active_configs = {k: v for k, v in all_configs.items() if v.get('active', False)}
        
        if not active_configs:
            logger.info("⚠️ No hay configuraciones de roles activas, saltando verificación inicial")
            return
        
        total_users_checked = 0
        total_roles_assigned = 0
        
        # Procesar cada servidor configurado
        for guild_id, config in active_configs.items():
            try:
                guild = bot.get_guild(int(guild_id))
                if not guild:
                    logger.warning(f"⚠️ Servidor {guild_id} no encontrado")
                    continue
                
                role_id = config.get('role_id')
                role = guild.get_role(role_id)
                if not role:
                    logger.warning(f"⚠️ Rol {role_id} no encontrado en servidor {guild.name}")
                    continue
                
                logger.info(f"🔍 Verificando servidor: {guild.name} (ID: {guild_id})")
                
                # Importar sistema de verificación
                from main import roblox_verification
                
                verified_users_in_server = 0
                roles_assigned_in_server = 0
                
                # Revisar cada usuario verificado
                for discord_id, user_data in roblox_verification.verified_users.items():
                    try:
                        member = guild.get_member(int(discord_id))
                        if not member:
                            continue  # Usuario no está en este servidor
                        
                        verified_users_in_server += 1
                        total_users_checked += 1
                        
                        # Verificar si ya tiene el rol
                        if role in member.roles:
                            logger.debug(f"✅ Usuario {member.name} ya tiene el rol en {guild.name}")
                            continue
                        
                        # Asignar el rol
                        try:
                            await member.add_roles(role, reason="Asignación automática al inicio del bot - usuario ya verificado")
                            roles_assigned_in_server += 1
                            total_roles_assigned += 1
                            
                            roblox_username = user_data.get('roblox_username', 'Unknown')
                            logger.info(f"✅ Rol asignado automáticamente a {member.name} ({roblox_username}) en {guild.name}")
                            
                            # Pequeña pausa para evitar rate limits
                            await asyncio.sleep(0.5)
                            
                        except discord.Forbidden:
                            logger.warning(f"❌ Sin permisos para asignar rol a {member.name} en {guild.name}")
                        except discord.HTTPException as e:
                            logger.error(f"❌ Error HTTP asignando rol a {member.name} en {guild.name}: {e}")
                        except Exception as e:
                            logger.error(f"❌ Error asignando rol a {member.name} en {guild.name}: {e}")
                    
                    except Exception as e:
                        logger.error(f"❌ Error procesando usuario {discord_id}: {e}")
                        continue
                
                if verified_users_in_server > 0:
                    logger.info(f"📊 Servidor {guild.name}: {roles_assigned_in_server}/{verified_users_in_server} usuarios recibieron el rol")
                else:
                    logger.info(f"📊 Servidor {guild.name}: No hay usuarios verificados en este servidor")
                
            except Exception as e:
                logger.error(f"❌ Error procesando servidor {guild_id}: {e}")
                continue
        
        if total_users_checked > 0:
            logger.info(f"✅ Verificación inicial completada: {total_roles_assigned}/{total_users_checked} roles asignados")
        else:
            logger.info("📊 Verificación inicial completada: No hay usuarios verificados en servidores configurados")
            
    except Exception as e:
        logger.error(f"❌ Error crítico en verificación inicial: {e}")

def cleanup_commands(bot):
    """Función de limpieza - detiene el monitoreo"""
    global verification_monitor_task
    
    if verification_monitor_task and not verification_monitor_task.done():
        verification_monitor_task.cancel()
        logger.info("🛑 Sistema de monitoreo de verificaciones detenido")