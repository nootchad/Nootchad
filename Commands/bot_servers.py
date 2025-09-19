
"""
Comando para ver en qué servidores está el bot de Discord
Muestra información detallada sobre cada servidor
"""
import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar el comando de servidores del bot"""
    
    @bot.tree.command(name="botservers", description="Ver en qué servidores está el bot actualmente")
    async def botservers_command(interaction: discord.Interaction):
        """Mostrar información sobre los servidores donde está el bot"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
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
            guilds = bot.guilds
            total_guilds = len(guilds)
            total_members = sum(guild.member_count for guild in guilds if guild.member_count)
            
            # Crear embed principal
            embed = discord.Embed(
                title="<a:pepebot:1418489370129993728> Servidores del Bot RbxServers",
                description=f"El bot está activo en **{total_guilds}** servidores con un total de **{total_members:,}** miembros.",
                color=0x00ff88
            )
            
            # Estadísticas generales
            embed.add_field(
                name="<:stats:1418490788437823599> Estadísticas Generales",
                value=f"• **Total Servidores:** {total_guilds}\n• **Total Miembros:** {total_members:,}\n• **Promedio por Servidor:** {total_members // total_guilds if total_guilds > 0 else 0} miembros",
                inline=False
            )
            
            # Ordenar servidores por cantidad de miembros (más grandes primero)
            sorted_guilds = sorted(guilds, key=lambda g: g.member_count or 0, reverse=True)
            
            # Mostrar top 10 servidores más grandes
            if sorted_guilds:
                top_servers = ""
                for i, guild in enumerate(sorted_guilds[:10], 1):
                    member_count = guild.member_count or 0
                    owner_name = guild.owner.name if guild.owner else "Desconocido"
                    
                    # Emoji basado en tamaño del servidor
                    if member_count > 1000:
                        emoji = "🏰"
                    elif member_count > 500:
                        emoji = "🏢"
                    elif member_count > 100:
                        emoji = "🏠"
                    else:
                        emoji = "🏪"
                    
                    top_servers += f"{emoji} **{guild.name}**\n"
                    top_servers += f"   └ {member_count:,} miembros • Owner: {owner_name}\n"
                    top_servers += f"   └ ID: `{guild.id}`\n\n"
                
                embed.add_field(
                    name="🏆 Top 10 Servidores (Por Miembros)",
                    value=top_servers,
                    inline=False
                )
            
            # Información técnica
            embed.add_field(
                name="⚙️ Información Técnica",
                value=f"• **Bot ID:** `{bot.user.id}`\n• **Bot Tag:** `{bot.user.name}#{bot.user.discriminator}`\n• **Latencia:** {round(bot.latency * 1000)}ms",
                inline=True
            )
            
            # Permisos comunes
            total_admin_servers = sum(1 for guild in guilds if guild.me.guild_permissions.administrator)
            embed.add_field(
                name="🔐 Permisos",
                value=f"• **Admin en:** {total_admin_servers} servidores\n• **Sin Admin:** {total_guilds - total_admin_servers} servidores",
                inline=True
            )
            
            # Fecha de creación del bot
            bot_created = bot.user.created_at
            embed.add_field(
                name="📅 Creación del Bot",
                value=f"<t:{int(bot_created.timestamp())}:F>\n(<t:{int(bot_created.timestamp())}:R>)",
                inline=True
            )
            
            embed.set_footer(text=f"Consultado por {username} • {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            embed.set_thumbnail(url=bot.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Si hay muchos servidores, enviar lista completa en un segundo embed
            if total_guilds > 10:
                all_servers_text = ""
                for guild in sorted_guilds:
                    member_count = guild.member_count or 0
                    all_servers_text += f"• **{guild.name}** ({member_count:,} miembros) - `{guild.id}`\n"
                
                # Dividir en chunks si es muy largo
                if len(all_servers_text) > 4000:
                    chunks = [all_servers_text[i:i+3800] for i in range(0, len(all_servers_text), 3800)]
                    
                    for i, chunk in enumerate(chunks[:3]):  # Máximo 3 chunks
                        chunk_embed = discord.Embed(
                            title=f"📋 Lista Completa de Servidores (Parte {i+1})",
                            description=chunk,
                            color=0x3366ff
                        )
                        await interaction.followup.send(embed=chunk_embed, ephemeral=True)
                        
                        if i == 2 and len(chunks) > 3:
                            remaining_embed = discord.Embed(
                                title="⚠️ Lista Truncada",
                                description=f"Se muestran los primeros {(i+1) * 3800} caracteres. Hay {len(chunks) - 3} partes más.",
                                color=0xff9900
                            )
                            await interaction.followup.send(embed=remaining_embed, ephemeral=True)
                            break
                else:
                    complete_embed = discord.Embed(
                        title="📋 Lista Completa de Servidores",
                        description=all_servers_text,
                        color=0x3366ff
                    )
                    await interaction.followup.send(embed=complete_embed, ephemeral=True)
            
            logger.info(f"Owner {username} consultó información de servidores del bot: {total_guilds} servidores, {total_members} miembros")
            
        except Exception as e:
            logger.error(f"Error en comando botservers: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al obtener la información de los servidores.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @bot.tree.command(name="serverinfo", description="[OWNER ONLY] Ver información detallada de un servidor específico")
    async def serverinfo_command(interaction: discord.Interaction, server_id: str):
        """Ver información detallada de un servidor específico por ID"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
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
            # Validar que el server_id sea un número
            try:
                guild_id = int(server_id)
            except ValueError:
                embed = discord.Embed(
                    title="❌ ID Inválido",
                    description="El ID del servidor debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Buscar el servidor
            guild = bot.get_guild(guild_id)
            if not guild:
                embed = discord.Embed(
                    title="❌ Servidor No Encontrado",
                    description=f"El bot no está en el servidor con ID `{server_id}` o el servidor no existe.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed con información detallada
            embed = discord.Embed(
                title=f"🏰 Información del Servidor: {guild.name}",
                description=f"Información detallada del servidor **{guild.name}**",
                color=0x00aaff
            )
            
            # Información básica
            embed.add_field(
                name="📋 Información Básica",
                value=f"• **Nombre:** {guild.name}\n• **ID:** `{guild.id}`\n• **Miembros:** {guild.member_count:,}\n• **Creado:** <t:{int(guild.created_at.timestamp())}:F>",
                inline=False
            )
            
            # Owner información
            owner_info = "Desconocido"
            if guild.owner:
                owner_info = f"{guild.owner.name}#{guild.owner.discriminator}\nID: `{guild.owner.id}`"
            
            embed.add_field(
                name="👑 Owner",
                value=owner_info,
                inline=True
            )
            
            # Información de canales
            text_channels = len(guild.text_channels)
            voice_channels = len(guild.voice_channels)
            categories = len(guild.categories)
            
            embed.add_field(
                name="📺 Canales",
                value=f"• **Texto:** {text_channels}\n• **Voz:** {voice_channels}\n• **Categorías:** {categories}",
                inline=True
            )
            
            # Roles
            roles_count = len(guild.roles)
            embed.add_field(
                name="🎭 Roles",
                value=f"• **Total:** {roles_count}\n• **Máximo:** {guild.max_members or 'Ilimitado'}",
                inline=True
            )
            
            # Información del bot en el servidor
            bot_member = guild.me
            joined_at = bot_member.joined_at
            permissions = bot_member.guild_permissions
            
            embed.add_field(
                name="<a:pepebot:1418489370129993728> Bot en el Servidor",
                value=f"• **Se unió:** <t:{int(joined_at.timestamp())}:F>\n• **Admin:** {'<a:verify2:1418486831993061497>' if permissions.administrator else '❌'}\n• **Nickname:** {bot_member.display_name}",
                inline=False
            )
            
            # Permisos importantes
            important_perms = []
            if permissions.administrator:
                important_perms.append("<a:verify2:1418486831993061497> Administrador")
            else:
                if permissions.manage_guild:
                    important_perms.append("<a:verify2:1418486831993061497> Gestionar Servidor")
                if permissions.manage_channels:
                    important_perms.append("<a:verify2:1418486831993061497> Gestionar Canales")
                if permissions.manage_roles:
                    important_perms.append("<a:verify2:1418486831993061497> Gestionar Roles")
                if permissions.send_messages:
                    important_perms.append("<a:verify2:1418486831993061497> Enviar Mensajes")
                if permissions.embed_links:
                    important_perms.append("<a:verify2:1418486831993061497> Insertar Enlaces")
                if not permissions.send_messages:
                    important_perms.append("❌ Enviar Mensajes")
                if not permissions.embed_links:
                    important_perms.append("❌ Insertar Enlaces")
            
            if important_perms:
                embed.add_field(
                    name="🔐 Permisos Importantes",
                    value="\n".join(important_perms[:8]),  # Máximo 8 permisos
                    inline=True
                )
            
            # Características del servidor
            features = []
            if guild.premium_tier > 0:
                features.append(f"💎 Boost Nivel {guild.premium_tier}")
            if guild.verification_level != discord.VerificationLevel.none:
                features.append(f"🔒 Verificación: {guild.verification_level.name}")
            if guild.explicit_content_filter != discord.ContentFilter.disabled:
                features.append("🔞 Filtro de Contenido")
            
            if features:
                embed.add_field(
                    name="✨ Características",
                    value="\n".join(features),
                    inline=True
                )
            
            # Establecer imagen del servidor si tiene
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            embed.set_footer(text=f"Consultado por {username}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"Owner {username} consultó información detallada del servidor {guild.name} (ID: {guild.id})")
            
        except Exception as e:
            logger.error(f"Error en comando serverinfo: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al obtener la información del servidor.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:200]}```", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("<a:verify2:1418486831993061497> Comandos de información de servidores configurados")
    return True

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
