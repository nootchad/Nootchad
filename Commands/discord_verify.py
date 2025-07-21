
"""
Sistema de verificación con roles de Discord para RbxServers
Incluye configuración automática y asignación de roles
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos de verificación con roles"""
    
    @bot.tree.command(name="setupverify", description="[OWNER ONLY] Configurar sistema de verificación con roles")
    async def setupverify_command(
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        rol_verificado: discord.Role,
        activar: bool = True
    ):
        """Comando owner para configurar el sistema de verificación con roles"""
        try:
            from main import is_owner_or_delegated
            
            user_id = str(interaction.user.id)
            
            # Verificar que solo el owner pueda usar este comando
            if not is_owner_or_delegated(user_id):
                embed = discord.Embed(
                    title="❌ Acceso Denegado",
                    description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Verificar permisos del bot
            bot_member = interaction.guild.get_member(bot.user.id)
            if not bot_member.guild_permissions.manage_roles:
                embed = discord.Embed(
                    title="❌ Sin Permisos",
                    description="El bot necesita el permiso **'Gestionar Roles'** para asignar roles automáticamente.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar que el rol del bot esté por encima del rol a asignar
            if bot_member.top_role <= rol_verificado:
                embed = discord.Embed(
                    title="❌ Jerarquía de Roles",
                    description=f"El rol del bot debe estar **por encima** del rol {rol_verificado.mention} en la jerarquía para poder asignarlo.",
                    color=0xff0000
                )
                embed.add_field(
                    name="💡 Solución:",
                    value="Mueve el rol del bot por encima del rol de verificado en la configuración del servidor.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar permisos en el canal
            channel_perms = canal.permissions_for(bot_member)
            if not (channel_perms.send_messages and channel_perms.read_messages):
                embed = discord.Embed(
                    title="❌ Sin Permisos en Canal",
                    description=f"El bot necesita permisos de **'Leer Mensajes'** y **'Enviar Mensajes'** en {canal.mention}.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Configurar y guardar datos
            guild_id = str(interaction.guild.id)
            
            config_data = {
                'guild_id': guild_id,
                'guild_name': interaction.guild.name,
                'channel_id': str(canal.id),
                'channel_name': canal.name,
                'role_id': str(rol_verificado.id),
                'role_name': rol_verificado.name,
                'active': activar,
                'setup_by': {
                    'user_id': user_id,
                    'username': str(interaction.user),
                    'setup_at': datetime.now().isoformat()
                },
                'statistics': {
                    'roles_assigned': 0,
                    'last_assignment': None
                }
            }
            
            # Guardar configuración
            if save_verify_config(guild_id, config_data):
                if activar:
                    embed = discord.Embed(
                        title="<:verify:1396087763388072006> Sistema de Verificación Configurado",
                        description="El sistema de verificación con roles ha sido configurado exitosamente.",
                        color=0x00ff88
                    )
                    embed.add_field(
                        name="⚙️ **Configuración:**",
                        value=f"• **Servidor:** {interaction.guild.name}\n• **Canal:** {canal.mention}\n• **Rol:** {rol_verificado.mention}\n• **Estado:** <:verify:1396087763388072006> Activo",
                        inline=False
                    )
                    embed.add_field(
                        name="🔄 **Funcionamiento:**",
                        value="• Los usuarios verificados recibirán el rol automáticamente\n• El comando `/verify` asignará roles en este servidor\n• Solo funciona para usuarios ya verificados con el bot\n• Se enviará confirmación en el canal configurado",
                        inline=False
                    )
                    embed.add_field(
                        name="<:1000182751:1396420551798558781> **Gestión:**",
                        value="• Usa `/setupverify` con `activar: False` para desactivar\n• El sistema funciona 24/7 automáticamente\n• Se guardan estadísticas de asignaciones",
                        inline=False
                    )
                else:
                    embed = discord.Embed(
                        title="⏸️ Sistema de Verificación Desactivado",
                        description="El sistema de verificación con roles ha sido desactivado para este servidor.",
                        color=0xff9900
                    )
                    embed.add_field(
                        name="📊 **Estado:**",
                        value="• Sistema pausado\n• No se asignarán roles automáticamente\n• Configuración guardada para reactivación futura",
                        inline=False
                    )
                
                embed.add_field(
                    name="🎯 **Comando de Usuario:**",
                    value="`/verify` - Los usuarios pueden usar este comando para obtener su rol de verificado",
                    inline=False
                )
                
                embed.set_footer(text=f"Configurado por {interaction.user.name}")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Revisar usuarios ya verificados sin rol si el sistema está activo
                if activar:
                    try:
                        logger.info(f"🔄 Revisando usuarios ya verificados sin rol en {interaction.guild.name}...")
                        roles_assigned = await check_existing_verified_users(bot, guild_id, rol_verificado.id)
                        
                        if roles_assigned > 0:
                            # Enviar actualización con estadísticas
                            update_embed = discord.Embed(
                                title="<:verify:1396087763388072006> Sistema Configurado + Roles Asignados",
                                description=f"Sistema configurado exitosamente y **{roles_assigned} usuarios ya verificados** recibieron automáticamente el rol.",
                                color=0x00ff88
                            )
                            update_embed.add_field(
                                name="⚙️ **Configuración:**",
                                value=f"• **Servidor:** {interaction.guild.name}\n• **Canal:** {canal.mention}\n• **Rol:** {rol_verificado.mention}\n• **Estado:** <:verify:1396087763388072006> Activo",
                                inline=False
                            )
                            update_embed.add_field(
                                name="✅ **Asignación Automática:**",
                                value=f"• **Roles asignados:** {roles_assigned}\n• **Usuarios revisados:** Todos los verificados\n• **Método:** Automático al configurar",
                                inline=False
                            )
                            update_embed.add_field(
                                name="🔄 **Funcionamiento:**",
                                value="• Los usuarios verificados reciben el rol automáticamente\n• El comando `/verify` asigna roles en este servidor\n• Se envía confirmación en el canal configurado",
                                inline=False
                            )
                            update_embed.set_footer(text=f"Configurado por {interaction.user.name}")
                            
                            await interaction.edit_original_response(embed=update_embed)
                            
                    except Exception as check_error:
                        logger.warning(f"⚠️ Error revisando usuarios existentes: {check_error}")
                
                logger.info(f"Owner {interaction.user.name} configuró verificación con roles para servidor {interaction.guild.name} (ID: {guild_id})")
            else:
                embed = discord.Embed(
                    title="❌ Error de Configuración",
                    description="No se pudo guardar la configuración. Inténtalo nuevamente.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error en comando setupverify: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al configurar el sistema de verificación.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="verify", description="Obtener rol de verificado si ya estás verificado con el bot")
    async def verify_role_command(interaction: discord.Interaction):
        """Comando para que usuarios verificados obtengan su rol de Discord"""
        try:
            from main import roblox_verification, check_verification
            
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            guild_id = str(interaction.guild.id)
            
            logger.info(f"Usuario {username} (ID: {user_id}) solicitó rol de verificado en servidor {interaction.guild.name}")
            
            await interaction.response.defer(ephemeral=True)
            
            # Debug adicional
            logger.info(f"🔍 DEBUG: Verificando configuración para servidor {guild_id}")
            logger.info(f"🔍 DEBUG: Usuario verificado: {roblox_verification.is_user_verified(user_id)}")
            if roblox_verification.is_user_verified(user_id):
                user_data = roblox_verification.verified_users.get(user_id, {})
                logger.info(f"🔍 DEBUG: Datos del usuario: {user_data.get('roblox_username', 'N/A')}")
            
            # Verificar que el sistema esté configurado para este servidor
            config = load_verify_config(guild_id)
            if not config:
                embed = discord.Embed(
                    title="⚙️ Sistema No Configurado",
                    description="El sistema de verificación con roles no está configurado en este servidor.",
                    color=0xff9900
                )
                embed.add_field(
                    name="👑 Para Administradores:",
                    value="Un owner del bot debe usar `/setupverify` para configurar el sistema.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar que el sistema esté activo
            if not config.get('active', False):
                embed = discord.Embed(
                    title="⏸️ Sistema Desactivado",
                    description="El sistema de verificación con roles está temporalmente desactivado en este servidor.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar que el usuario esté verificado con el bot
            if not roblox_verification.is_user_verified(user_id):
                # Usuario no verificado - mostrar instrucciones
                embed = discord.Embed(
                    title="🔒 Verificación Requerida",
                    description="**Primero debes verificarte con el bot RbxServers** para obtener el rol de verificado.",
                    color=0xffaa00
                )
                
                embed.add_field(
                    name="📝 **Cómo Verificarse:**",
                    value="**1.** Usa `/verify [tu_nombre_roblox]` (comando de verificación del bot)\n**2.** Copia el código generado a tu descripción de Roblox\n**3.** Haz clic en el botón de confirmación\n**4.** Una vez verificado, vuelve a usar este comando",
                    inline=False
                )
                
                embed.add_field(
                    name="<:1000182563:1396420770904932372> **Importante:**",
                    value="• No uses nombres de usuario falsos\n• La verificación dura 30 días\n• Debes seguir las reglas del bot",
                    inline=False
                )
                
                embed.add_field(
                    name="🎯 **Después de Verificarte:**",
                    value="Regresa aquí y usa `/verify` nuevamente para obtener tu rol de Discord.",
                    inline=False
                )
                
                embed.set_footer(text="RbxServers • Sistema de Verificación")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Usuario verificado - obtener información del usuario
            user_data = roblox_verification.verified_users.get(user_id, {})
            roblox_username = user_data.get('roblox_username', 'Usuario')
            
            # Verificar si ya tiene el rol
            role_id = int(config['role_id'])
            role = interaction.guild.get_role(role_id)
            
            if not role:
                embed = discord.Embed(
                    title="❌ Error de Configuración",
                    description="El rol de verificado ya no existe en este servidor.",
                    color=0xff0000
                )
                embed.add_field(
                    name="👑 Para Administradores:",
                    value="Reconfigura el sistema con `/setupverify` usando un rol existente.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si ya tiene el rol
            if role in interaction.user.roles:
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Ya Tienes el Rol",
                    description=f"Ya tienes el rol {role.mention} asignado.",
                    color=0x00aa55
                )
                embed.add_field(
                    name="<:1000182614:1396049500375875646> **Tu Información:**",
                    value=f"• **Usuario de Roblox:** `{roblox_username}`\n• **Estado:** Verificado ✅\n• **Rol:** {role.mention}",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Asignar el rol
            try:
                await interaction.user.add_roles(role, reason=f"Usuario verificado automáticamente - Roblox: {roblox_username}")
                
                # Actualizar estadísticas
                update_verify_stats(guild_id, user_id, roblox_username)
                
                # Embed de confirmación para el usuario
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Rol Asignado Exitosamente",
                    description=f"¡Felicidades **{roblox_username}**! Has recibido el rol de verificado.",
                    color=0x00ff88
                )
                
                embed.add_field(
                    name="🎉 **Rol Obtenido:**",
                    value=f"{role.mention}",
                    inline=True
                )
                
                embed.add_field(
                    name="<:1000182614:1396049500375875646> **Usuario Roblox:**",
                    value=f"`{roblox_username}`",
                    inline=True
                )
                
                embed.add_field(
                    name="⏰ **Verificado:**",
                    value=f"<t:{int(datetime.now().timestamp())}:R>",
                    inline=True
                )
                
                embed.add_field(
                    name="💡 **Beneficios:**",
                    value="• Acceso a canales exclusivos\n• Comandos premium del bot\n• Confianza en la comunidad",
                    inline=False
                )
                
                embed.set_footer(text="¡Bienvenido a la comunidad verificada!")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                # Enviar notificación al canal configurado (si es posible)
                try:
                    channel = interaction.guild.get_channel(int(config['channel_id']))
                    if channel:
                        notification_embed = discord.Embed(
                            title="<:verify:1396087763388072006> Nuevo Usuario Verificado",
                            description=f"{interaction.user.mention} ha obtenido el rol de verificado.",
                            color=0x00ff88
                        )
                        notification_embed.add_field(
                            name="<:1000182614:1396049500375875646> Usuario:",
                            value=f"**Discord:** {interaction.user.mention}\n**Roblox:** `{roblox_username}`",
                            inline=True
                        )
                        notification_embed.add_field(
                            name="🎯 Rol:",
                            value=f"{role.mention}",
                            inline=True
                        )
                        notification_embed.set_footer(text="Sistema de Verificación Automática")
                        
                        await channel.send(embed=notification_embed)
                except Exception as notif_error:
                    logger.warning(f"No se pudo enviar notificación al canal: {notif_error}")
                
                logger.info(f"Rol de verificado asignado exitosamente a {username} (Roblox: {roblox_username}) en servidor {interaction.guild.name}")
                
            except discord.Forbidden:
                embed = discord.Embed(
                    title="❌ Sin Permisos",
                    description="El bot no tiene permisos para asignar roles en este servidor.",
                    color=0xff0000
                )
                embed.add_field(
                    name="👑 Para Administradores:",
                    value="Asegúrate de que el bot tenga el permiso **'Gestionar Roles'** y que su rol esté por encima del rol de verificado.",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
            except Exception as role_error:
                logger.error(f"Error asignando rol: {role_error}")
                embed = discord.Embed(
                    title="❌ Error Asignando Rol",
                    description="Ocurrió un error al asignar el rol. Inténtalo nuevamente o contacta a un administrador.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error en comando verify (roles) para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error procesando tu solicitud de rol.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

def save_verify_config(guild_id: str, config_data: dict) -> bool:
    """Guardar configuración de verificación con roles instantáneamente"""
    try:
        config_file = Path("discord_verify_config.json")
        
        # Cargar configuraciones existentes
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'guilds': {}, 'metadata': {}}
        
        # Actualizar configuración del servidor
        data['guilds'][guild_id] = config_data
        
        # Actualizar metadata
        data['metadata'] = {
            'total_guilds': len(data['guilds']),
            'last_updated': datetime.now().isoformat(),
            'active_guilds': len([g for g in data['guilds'].values() if g.get('active', False)])
        }
        
        # Guardar archivo
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Configuración de verificación guardada para servidor {guild_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error guardando configuración de verificación: {e}")
        return False

def load_verify_config(guild_id: str) -> dict:
    """Cargar configuración de verificación de un servidor específico"""
    try:
        config_file = Path("discord_verify_config.json")
        if not config_file.exists():
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get('guilds', {}).get(guild_id, {})
        
    except Exception as e:
        logger.error(f"Error cargando configuración de verificación para servidor {guild_id}: {e}")
        return {}

def update_verify_stats(guild_id: str, user_id: str, roblox_username: str):
    """Actualizar estadísticas de asignación de roles"""
    try:
        config_file = Path("discord_verify_config.json")
        if not config_file.exists():
            return
        
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if guild_id in data['guilds']:
            # Actualizar estadísticas
            stats = data['guilds'][guild_id].setdefault('statistics', {})
            stats['roles_assigned'] = stats.get('roles_assigned', 0) + 1
            stats['last_assignment'] = {
                'user_id': user_id,
                'roblox_username': roblox_username,
                'assigned_at': datetime.now().isoformat()
            }
            
            # Guardar cambios
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Estadísticas actualizadas para servidor {guild_id}: rol asignado a {user_id}")
        
    except Exception as e:
        logger.error(f"Error actualizando estadísticas: {e}")

async def check_existing_verified_users(bot, guild_id: str, role_id: str):
    """Revisar usuarios ya verificados sin rol y asignárselo automáticamente"""
    try:
        from main import roblox_verification
        
        guild = bot.get_guild(int(guild_id))
        if not guild:
            logger.warning(f"⚠️ No se pudo encontrar el servidor {guild_id}")
            return 0
        
        role = guild.get_role(int(role_id))
        if not role:
            logger.warning(f"⚠️ No se pudo encontrar el rol {role_id} en servidor {guild.name}")
            return 0
        
        logger.info(f"🔍 Revisando usuarios verificados sin rol en servidor {guild.name}...")
        
        roles_assigned = 0
        checked_users = 0
        
        # Revisar todos los usuarios verificados
        for discord_id, user_data in roblox_verification.verified_users.items():
            try:
                checked_users += 1
                member = guild.get_member(int(discord_id))
                
                if member and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Rol de verificado asignado automáticamente al configurar sistema")
                        
                        roblox_username = user_data.get('roblox_username', 'Usuario desconocido')
                        logger.info(f"✅ Rol asignado automáticamente a {member.name} (Roblox: {roblox_username})")
                        
                        # Actualizar estadísticas
                        update_verify_stats(guild_id, discord_id, roblox_username)
                        roles_assigned += 1
                        
                        # Pausa pequeña para evitar rate limits
                        await asyncio.sleep(0.5)
                        
                    except Exception as role_error:
                        logger.warning(f"⚠️ No se pudo asignar rol a {member.name}: {role_error}")
                        
                elif member and role in member.roles:
                    logger.debug(f"✅ {member.name} ya tiene el rol de verificado")
                    
            except Exception as e:
                logger.debug(f"⚠️ Error revisando usuario {discord_id}: {e}")
                continue
        
        logger.info(f"📊 Revisión completada en {guild.name}: {roles_assigned} roles asignados de {checked_users} usuarios verificados revisados")
        return roles_assigned
        
    except Exception as e:
        logger.error(f"❌ Error revisando usuarios verificados existentes: {e}")
        return 0

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass

logger.info("✅ Sistema de verificación con roles de Discord configurado")
