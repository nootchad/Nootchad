import discord
from discord.ext import commands
from anti_alt_system import anti_alt_system
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def setup_anti_alt_commands(bot):
    """Configurar comandos del sistema anti-alt"""

    @bot.tree.command(name="blacklist", description="[OWNER ONLY] Gestionar lista negra de usuarios")
    async def blacklist_command(interaction: discord.Interaction, 
                               accion: str, 
                               usuario: discord.User = None, 
                               razon: str = "No especificada"):
        """Comando para gestionar blacklist"""
        user_id = str(interaction.user.id)

        # Verificar permisos de owner
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede gestionar la lista negra.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            if accion.lower() == "add" and usuario:
                target_id = str(usuario.id)
                anti_alt_system.add_to_blacklist(target_id, razon)

                embed = discord.Embed(
                    title="🚫 Usuario Agregado a Lista Negra",
                    description=f"**{usuario.mention}** ha sido agregado a la lista negra.",
                    color=0xff0000
                )
                embed.add_field(name="👤 Usuario", value=f"{usuario.name}#{usuario.discriminator}", inline=True)
                embed.add_field(name="🆔 ID", value=target_id, inline=True)
                embed.add_field(name="📝 Razón", value=razon, inline=False)

            elif accion.lower() == "remove" and usuario:
                target_id = str(usuario.id)
                removed = anti_alt_system.remove_from_blacklist(target_id)

                if removed:
                    embed = discord.Embed(
                        title="✅ Usuario Removido de Lista Negra",
                        description=f"**{usuario.mention}** ha sido removido de la lista negra.",
                        color=0x00ff88
                    )
                else:
                    embed = discord.Embed(
                        title="⚠️ Usuario No Encontrado",
                        description=f"**{usuario.mention}** no estaba en la lista negra.",
                        color=0xffaa00
                    )

            elif accion.lower() == "list":
                blacklisted_users = list(anti_alt_system.blacklist)

                embed = discord.Embed(
                    title="📋 Lista Negra de Usuarios",
                    description=f"Total de usuarios en lista negra: **{len(blacklisted_users)}**",
                    color=0xff0000
                )

                if blacklisted_users:
                    user_list = []
                    for i, blacklisted_id in enumerate(blacklisted_users[:10]):
                        try:
                            user = bot.get_user(int(blacklisted_id))
                            if user:
                                user_list.append(f"{i+1}. {user.name}#{user.discriminator} (`{blacklisted_id}`)")
                            else:
                                user_list.append(f"{i+1}. Usuario desconocido (`{blacklisted_id}`)")
                        except:
                            user_list.append(f"{i+1}. ID inválido (`{blacklisted_id}`)")

                    embed.add_field(
                        name="👥 Usuarios (mostrando 10 de " + str(len(blacklisted_users)) + ")",
                        value="\n".join(user_list) if user_list else "Ninguno",
                        inline=False
                    )

                    if len(blacklisted_users) > 10:
                        embed.add_field(
                            name="📊 Información",
                            value=f"Y {len(blacklisted_users) - 10} usuarios más...",
                            inline=False
                        )
                else:
                    embed.add_field(name="📊 Estado", value="La lista negra está vacía", inline=False)

            else:
                embed = discord.Embed(
                    title="❌ Uso Incorrecto",
                    description="Uso: `/blacklist <add|remove|list> [usuario] [razón]`",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Ejemplos:",
                    value="• `/blacklist add @usuario Múltiples cuentas alt`\n• `/blacklist remove @usuario`\n• `/blacklist list`",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando blacklist: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error procesando el comando.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="whitelist", description="[OWNER ONLY] Gestionar lista blanca de usuarios confiables")
    async def whitelist_command(interaction: discord.Interaction, 
                               accion: str, 
                               usuario: discord.User = None, 
                               razon: str = "Usuario confiable"):
        """Comando para gestionar whitelist"""
        user_id = str(interaction.user.id)

        # Verificar permisos de owner
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede gestionar la lista blanca.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            if accion.lower() == "add" and usuario:
                target_id = str(usuario.id)
                anti_alt_system.add_to_whitelist(target_id, razon)

                embed = discord.Embed(
                    title="✅ Usuario Agregado a Lista Blanca",
                    description=f"**{usuario.mention}** ha sido agregado a la lista blanca.",
                    color=0x00ff88
                )
                embed.add_field(name="👤 Usuario", value=f"{usuario.name}#{usuario.discriminator}", inline=True)
                embed.add_field(name="🆔 ID", value=target_id, inline=True)
                embed.add_field(name="📝 Razón", value=razon, inline=False)
                embed.add_field(name="🎁 Beneficios", value="• Sin cooldowns\n• Sin límites diarios\n• Mayor confianza", inline=False)

            elif accion.lower() == "remove" and usuario:
                target_id = str(usuario.id)
                removed = anti_alt_system.remove_from_whitelist(target_id)

                if removed:
                    embed = discord.Embed(
                        title="⚠️ Usuario Removido de Lista Blanca",
                        description=f"**{usuario.mention}** ha sido removido de la lista blanca.",
                        color=0xffaa00
                    )
                else:
                    embed = discord.Embed(
                        title="⚠️ Usuario No Encontrado",
                        description=f"**{usuario.mention}** no estaba en la lista blanca.",
                        color=0xffaa00
                    )

            elif accion.lower() == "list":
                whitelisted_users = list(anti_alt_system.whitelist)

                embed = discord.Embed(
                    title="🤍 Lista Blanca de Usuarios",
                    description=f"Total de usuarios confiables: **{len(whitelisted_users)}**",
                    color=0x00ff88
                )

                if whitelisted_users:
                    user_list = []
                    for i, whitelisted_id in enumerate(whitelisted_users[:10]):
                        try:
                            user = bot.get_user(int(whitelisted_id))
                            if user:
                                user_list.append(f"{i+1}. {user.name}#{user.discriminator} (`{whitelisted_id}`)")
                            else:
                                user_list.append(f"{i+1}. Usuario desconocido (`{whitelisted_id}`)")
                        except:
                            user_list.append(f"{i+1}. ID inválido (`{whitelisted_id}`)")

                    embed.add_field(
                        name="👥 Usuarios Confiables (mostrando 10 de " + str(len(whitelisted_users)) + ")",
                        value="\n".join(user_list) if user_list else "Ninguno",
                        inline=False
                    )

                    if len(whitelisted_users) > 10:
                        embed.add_field(
                            name="📊 Información",
                            value=f"Y {len(whitelisted_users) - 10} usuarios más...",
                            inline=False
                        )
                else:
                    embed.add_field(name="📊 Estado", value="La lista blanca está vacía", inline=False)

            else:
                embed = discord.Embed(
                    title="❌ Uso Incorrecto",
                    description="Uso: `/whitelist <add|remove|list> [usuario] [razón]`",
                    color=0xff0000
                )
                embed.add_field(
                    name="📝 Ejemplos:",
                    value="• `/whitelist add @usuario Usuario muy activo y confiable`\n• `/whitelist remove @usuario`\n• `/whitelist list`",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando whitelist: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error procesando el comando.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="userstats", description="[OWNER ONLY] Ver estadísticas detalladas de un usuario")
    async def userstats_command(interaction: discord.Interaction, usuario: discord.User):
        """Ver estadísticas de usuario del sistema anti-alt"""
        user_id = str(interaction.user.id)

        # Verificar permisos de owner
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede ver estadísticas de usuarios.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            target_id = str(usuario.id)

            # Actualizar información de cuenta antes de obtener estadísticas
            anti_alt_system.update_account_info(target_id, usuario)

            stats = anti_alt_system.get_user_stats(target_id)

            if not stats:
                embed = discord.Embed(
                    title="❌ Usuario No Encontrado",
                    description=f"No hay datos registrados para **{usuario.mention}**.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Determinar color basado en nivel de riesgo
            risk_colors = {
                'low': 0x00ff88,
                'medium': 0xffaa00,
                'high': 0xff6600,
                'banned': 0xff0000
            }
            color = risk_colors.get(stats['risk_level'], 0x3366ff)

            embed = discord.Embed(
                title=f"📊 Estadísticas de Usuario",
                description=f"Información detallada de **{usuario.mention}**",
                color=color
            )

            embed.set_thumbnail(url=usuario.avatar.url if usuario.avatar else None)

            # Información básica
            roblox_info = ""
            if stats.get('roblox_username'):
                roblox_info = f"\n**Roblox:** {stats['roblox_username']}"
            else:
                roblox_info = "\n**Roblox:** No verificado"

            embed.add_field(
                name="👤 Información Básica",
                value=f"**Usuario:** {usuario.name}#{usuario.discriminator}\n**ID:** `{target_id}`{roblox_info}\n**Nivel de Riesgo:** {stats['risk_level'].upper()}",
                inline=False
            )

            # Estadísticas de actividad anti-alt
            embed.add_field(
                name="🛡️ Sistema Anti-Alt",
                value=f"**Puntuación de Confianza:** {stats['trust_score']}/100\n**Canjes Exitosos:** {stats['total_redemptions']}\n**Intentos Fallidos:** {stats['failed_attempts']}\n**Actividades Sospechosas:** {stats['suspicious_activities_count']}",
                inline=True
            )

            # Estado de listas
            status_list = []
            if stats['is_whitelisted']:
                status_list.append("✅ En Whitelist")
            if stats['is_blacklisted']:
                status_list.append("🚫 En Blacklist")
            if stats['on_cooldown']:
                status_list.append(f"⏰ Cooldown ({stats['cooldown_remaining_seconds']}s)")

            if not status_list:
                status_list.append("📊 Usuario Normal")

            embed.add_field(
                name="🏷️ Estado",
                value="\n".join(status_list),
                inline=True
            )

            # Información de cuenta de Discord
            account_info = []
            if stats.get('account_created_at'):
                try:
                    created_at = datetime.fromisoformat(stats['account_created_at'].replace('Z', '+00:00'))
                    account_info.append(f"**Creada:** <t:{int(created_at.timestamp())}:D>")

                    if stats.get('account_age_hours'):
                        age_days = int(stats['account_age_hours'] / 24)
                        account_info.append(f"**Antigüedad:** {age_days} días")
                except Exception as e:
                    logger.debug(f"Error procesando fecha de creación: {e}")
                    account_info.append("**Creada:** Información no disponible")
            else:
                account_info.append("**Creada:** Información no disponible")

            if account_info:
                embed.add_field(
                    name="📅 Cuenta de Discord",
                    value="\n".join(account_info),
                    inline=False
                )

            # Códigos canjeados (obtener del sistema de códigos)
            codes_canjeados = []
            try:
                from codes_system import codes_system

                # Buscar en todos los códigos canjeados
                for code_name, usage_list in codes_system.codes_usage.items():
                    for usage in usage_list:
                        if usage.get('user_id') == target_id:
                            timestamp = usage.get('redeemed_at', 'Fecha no disponible')
                            try:
                                if timestamp != 'Fecha no disponible':
                                    dt = datetime.fromisoformat(timestamp)
                                    fecha_formateada = f"<t:{int(dt.timestamp())}:d>"
                                else:
                                    fecha_formateada = timestamp
                            except:
                                fecha_formateada = timestamp

                            codes_canjeados.append(f"• **{code_name}** - {fecha_formateada}")

                if codes_canjeados:
                    # Mostrar máximo 10 códigos
                    codes_text = "\n".join(codes_canjeados[:10])
                    if len(codes_canjeados) > 10:
                        codes_text += f"\n... y {len(codes_canjeados) - 10} más"

                    embed.add_field(
                        name=f"🎫 Códigos Canjeados ({len(codes_canjeados)})",
                        value=codes_text,
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🎫 Códigos Canjeados",
                        value="Ningún código canjeado",
                        inline=False
                    )

            except Exception as e:
                logger.error(f"Error obteniendo códigos canjeados: {e}")
                embed.add_field(
                    name="🎫 Códigos Canjeados",
                    value="Error obteniendo información de códigos",
                    inline=False
                )

            # Flags y actividades sospechosas
            if stats.get('flags') and len(stats['flags']) > 0:
                flags_text = "\n".join([f"• {flag}" for flag in stats['flags'][:5]])
                if len(stats['flags']) > 5:
                    flags_text += f"\n... y {len(stats['flags']) - 5} más"

                embed.add_field(
                    name="🚩 Flags de Seguridad",
                    value=flags_text,
                    inline=False
                )

            # Fechas importantes
            dates_info = []
            if stats.get('first_seen'):
                try:
                    first_seen = datetime.fromisoformat(stats['first_seen'])
                    dates_info.append(f"**Primera vez visto:** <t:{int(first_seen.timestamp())}:F>")
                except:
                    dates_info.append(f"**Primera vez visto:** {stats['first_seen']}")

            if stats.get('last_activity'):
                try:
                    last_activity = datetime.fromisoformat(stats['last_activity'])
                    dates_info.append(f"**Última actividad:** <t:{int(last_activity.timestamp())}:R>")
                except:
                    dates_info.append(f"**Última actividad:** {stats['last_activity']}")

            if dates_info:
                embed.add_field(
                    name="⏰ Actividad",
                    value="\n".join(dates_info),
                    inline=False
                )

            embed.set_footer(text=f"Sistema Anti-Alt • Consultado por {interaction.user.name}")
            embed.timestamp = datetime.now()

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando userstats: {e}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")

            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error obteniendo las estadísticas del usuario.",
                color=0xff0000
            )
            embed.add_field(
                name="🐛 Error técnico:",
                value=f"```{str(e)[:200]}```",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="systemstats", description="[OWNER ONLY] Ver estadísticas generales del sistema anti-alt")
    async def systemstats_command(interaction: discord.Interaction):
        """Ver estadísticas generales del sistema anti-alt"""
        user_id = str(interaction.user.id)

        # Verificar permisos de owner
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede ver estadísticas del sistema.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            stats = anti_alt_system.get_system_stats()

            embed = discord.Embed(
                title="📊 Estadísticas del Sistema Anti-Alt",
                description="Resumen completo del sistema de prevención de cuentas múltiples",
                color=0x3366ff
            )

            # Usuarios totales
            embed.add_field(
                name="👥 Usuarios Totales",
                value=f"**{stats['total_users']}** registrados",
                inline=True
            )

            # Listas
            embed.add_field(
                name="🚫 Lista Negra",
                value=f"**{stats['blacklisted_users']}** usuarios",
                inline=True
            )

            embed.add_field(
                name="✅ Lista Blanca",
                value=f"**{stats['whitelisted_users']}** usuarios",
                inline=True
            )

            # Distribución de riesgo
            risk_dist = stats['risk_distribution']
            risk_text = f"🟢 Bajo: **{risk_dist['low']}**\n🟡 Medio: **{risk_dist['medium']}**\n🔴 Alto: **{risk_dist['high']}**\n🚫 Baneados: **{risk_dist['banned']}**"

            embed.add_field(
                name="⚠️ Distribución de Riesgo",
                value=risk_text,
                inline=True
            )

            # Puntuaciones de confianza
            embed.add_field(
                name="🎯 Confianza Promedio",
                value=f"**{stats['average_trust_score']}/100**\n(Mediana: {stats['median_trust_score']})",
                inline=True
            )

            # Actividades recientes
            embed.add_field(
                name="🚨 Actividades Sospechosas (24h)",
                value=f"**{stats['recent_suspicious_activities']}** registradas",
                inline=True
            )

            # Cooldowns activos
            embed.add_field(
                name="⏳ Cooldowns Activos",
                value=f"**{stats['cooldowns_active']}** usuarios",
                inline=True
            )

            # Configuración del sistema
            config = stats['system_config']
            config_text = f"• **Edad mínima:** {config['min_account_age_hours']}h\n• **Similitud username:** {config['username_similarity_threshold']*100}%\n• **Códigos por día:** {config['max_codes_per_day']}\n• **Cooldown base:** {config['cooldown_base_minutes']}min"

            embed.add_field(
                name="⚙️ Configuración",
                value=config_text,
                inline=False
            )

            embed.set_footer(text=f"Última actualización: {stats['last_updated'][:19]}")
            embed.timestamp = datetime.now()

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando systemstats: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error obteniendo las estadísticas del sistema.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="cleanup", description="[OWNER ONLY] Limpiar datos antiguos del sistema anti-alt")
    async def cleanup_command(interaction: discord.Interaction, dias: int = 30):
        """Limpiar datos antiguos del sistema"""
        user_id = str(interaction.user.id)

        # Verificar permisos de owner
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Solo el owner del bot puede ejecutar limpieza del sistema.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if dias < 1 or dias > 365:
            embed = discord.Embed(
                title="❌ Parámetro Inválido",
                description="Los días deben estar entre 1 y 365.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # Realizar limpieza
            anti_alt_system.cleanup_old_data(dias)

            embed = discord.Embed(
                title="🧹 Limpieza Completada",
                description=f"Se han eliminado registros antiguos de más de **{dias} días**.",
                color=0x00ff88
            )
            embed.add_field(
                name="📊 Acciones Realizadas",
                value="• Actividades sospechosas antiguas eliminadas\n• Cooldowns expirados removidos\n• Datos optimizados",
                inline=False
            )
            embed.add_field(
                name="💡 Recomendación",
                value="Ejecuta este comando mensualmente para mantener el sistema optimizado.",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en comando cleanup: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error durante la limpieza del sistema.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    logger.info("🛡️ Comandos del sistema anti-alt configurados exitosamente")
    return anti_alt_system