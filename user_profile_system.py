import discord
from discord.ext import commands
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class ProfileView(discord.ui.View):
    def __init__(self, user_id: str, target_user: discord.User, profile_data: dict):
        super().__init__(timeout=300)  # 5 minutos
        self.user_id = user_id
        self.target_user = target_user
        self.profile_data = profile_data
        self.current_section = "overview"

    @discord.ui.select(
        placeholder="📊 Selecciona una sección para ver...",
        options=[
            discord.SelectOption(
                label="📊 Resumen General",
                description="Vista general del perfil del usuario",
                value="overview",
                emoji="📊"
            ),
            discord.SelectOption(
                label="🎮 Servidores de Juegos",
                description="Servidores VIP encontrados y favoritos",
                value="servers",
                emoji="🎮"
            ),
            discord.SelectOption(
                label="🔐 Verificación Roblox",
                description="Estado de verificación y cuenta de Roblox",
                value="verification",
                emoji="🔐"
            ),
            discord.SelectOption(
                label="💰 Sistema de Monedas",
                description="Balance, historial de transacciones",
                value="coins",
                emoji="💰"
            ),
            discord.SelectOption(
                label="📈 Estadísticas de Uso",
                description="Actividad en el bot y uso de comandos",
                value="activity",
                emoji="📈"
            ),
            discord.SelectOption(
                label="🛡️ Seguridad",
                description="Información del sistema anti-alt",
                value="security",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="🏆 Logros y Códigos",
                description="Códigos canjeados y logros obtenidos",
                value="achievements",
                emoji="🏆"
            )
        ]
    )
    async def section_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        section = select.values[0]
        self.current_section = section
        await self.update_embed(interaction, section)

    async def update_embed(self, interaction: discord.Interaction, section: str):
        """Actualizar el embed según la sección seleccionada"""
        embed = None

        if section == "overview":
            embed = self.create_overview_embed()
        elif section == "servers":
            embed = self.create_servers_embed()
        elif section == "verification":
            embed = self.create_verification_embed()
        elif section == "coins":
            embed = self.create_coins_embed()
        elif section == "activity":
            embed = self.create_activity_embed()
        elif section == "security":
            embed = self.create_security_embed()
        elif section == "achievements":
            embed = self.create_achievements_embed()

        await interaction.response.edit_message(embed=embed, view=self)

    def create_overview_embed(self):
        """Crear embed de resumen general"""
        embed = discord.Embed(
            title=f"📊 Perfil de {self.target_user.name}",
            description="Resumen general de la actividad en RbxServers",
            color=0x3366ff,
            timestamp=datetime.now()
        )

        # Información básica
        embed.add_field(
            name="👤 Usuario de Discord",
            value=f"**Nombre:** {self.target_user.name}\n**ID:** `{self.target_user.id}`\n**Cuenta creada:** <t:{int(self.target_user.created_at.timestamp())}:R>",
            inline=True
        )

        # Estadísticas rápidas
        profile = self.profile_data
        embed.add_field(
            name="⚡ Estadísticas Rápidas",
            value=f"**🎮 Juegos:** {profile.get('total_games', 0)}\n**🖥️ Servidores:** {profile.get('total_servers', 0)}\n**💰 Monedas:** {profile.get('coins_balance', 0):,}",
            inline=True
        )

        # Estado de verificación
        verification_status = "✅ Verificado" if profile.get('is_verified', False) else "❌ No verificado"
        roblox_name = profile.get('roblox_username', 'No disponible')

        embed.add_field(
            name="🔐 Estado de Verificación",
            value=f"**Estado:** {verification_status}\n**Roblox:** {roblox_name}\n**Última actividad:** <t:{int(profile.get('last_activity', time.time()))}:R>",
            inline=False
        )

        # Nivel de actividad
        activity_level = self.get_activity_level(profile)
        embed.add_field(
            name="📈 Nivel de Actividad",
            value=f"**Nivel:** {activity_level['level']}\n**Comandos usados:** {profile.get('total_commands', 0)}\n**Días activo:** {profile.get('active_days', 0)}",
            inline=True
        )

        # Sistema de seguridad
        security_status = "🟢 Confiable" if profile.get('is_trusted', True) else "🟡 En revisión"
        embed.add_field(
            name="🛡️ Estado de Seguridad",
            value=f"**Estado:** {security_status}\n**Nivel de riesgo:** {profile.get('risk_level', 'bajo').title()}\n**Advertencias:** {profile.get('warnings', 0)}",
            inline=True
        )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Sistema de Perfiles | Usa el menú para navegar • Gracias por la idea kxis3rr")

        return embed

    def create_servers_embed(self):
        """Crear embed de información de servidores"""
        embed = discord.Embed(
            title=f"🎮 Servidores de {self.target_user.name}",
            description="Información detallada sobre servidores VIP y actividad de juegos",
            color=0x00ff88
        )

        profile = self.profile_data

        # Estadísticas de servidores
        user_servers = profile.get('user_servers', [])
        total_servers = len(user_servers)
        total_games = profile.get('total_games', 0)
        favorite_games = len(profile.get('favorite_games', []))

        embed.add_field(
            name="📊 Estadísticas de Servidores",
            value=f"**🖥️ Servidores guardados:** {total_servers}/5\n**🎯 Juegos únicos:** {total_games}\n**⭐ Favoritos:** {favorite_games}",
            inline=True
        )

        # Mostrar los servidores del usuario si los tiene
        if user_servers:
            servers_preview = []
            for i, server in enumerate(user_servers[:3], 1):  # Mostrar solo los primeros 3
                # Extraer información básica del servidor
                if isinstance(server, str):
                    servers_preview.append(f"**{i}.** [Servidor #{i}]({server})")
                elif isinstance(server, dict):
                    server_name = server.get('name', f'Servidor #{i}')
                    server_url = server.get('url', '#')
                    servers_preview.append(f"**{i}.** [{server_name}]({server_url})")
            
            if len(user_servers) > 3:
                servers_preview.append(f"**...y {len(user_servers) - 3} más**")

            embed.add_field(
                name="🔗 Servidores Guardados",
                value="\n".join(servers_preview) if servers_preview else "Sin servidores guardados",
                inline=False
            )

        # Juegos más populares
        popular_games = profile.get('top_games', [])[:3]
        if popular_games:
            games_text = "\n".join([f"• **{game['name']}** ({game['server_count']} servidores)" for game in popular_games])
        else:
            games_text = "No hay datos disponibles"

        embed.add_field(
            name="🔥 Top 3 Juegos",
            value=games_text,
            inline=True
        )

        # Actividad reciente
        recent_activity = profile.get('recent_server_activity', [])[:3]
        if recent_activity:
            activity_text = "\n".join([f"• **{activity['game_name']}** - <t:{int(activity['timestamp'])}:R>" for activity in recent_activity])
        else:
            activity_text = "Sin actividad reciente"

        embed.add_field(
            name="⏰ Actividad Reciente",
            value=activity_text,
            inline=False
        )

        # Categorías más usadas
        categories = profile.get('game_categories', {})
        if categories:
            cat_text = "\n".join([f"• **{cat.title()}:** {count} juegos" for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]])
        else:
            cat_text = "Sin categorías registradas"

        embed.add_field(
            name="📂 Categorías Favoritas",
            value=cat_text,
            inline=True
        )

        # Servidores reservados
        reserved_servers = len(profile.get('reserved_servers', []))
        embed.add_field(
            name="📌 Servidores Reservados",
            value=f"**{reserved_servers}** servidores guardados",
            inline=True
        )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Información de Servidores • Gracias por la idea kxis3rr")

        return embed

    def create_verification_embed(self):
        """Crear embed de información de verificación"""
        embed = discord.Embed(
            title=f"🔐 Verificación de {self.target_user.name}",
            description="Estado de verificación y información de la cuenta de Roblox",
            color=0xff6b35
        )

        profile = self.profile_data

        # Estado de verificación
        is_verified = profile.get('is_verified', False)
        roblox_username = profile.get('roblox_username', 'No disponible')
        verified_at = profile.get('verified_at')

        if is_verified:
            status_text = "✅ **VERIFICADO**"
            status_color = 0x00ff00

            if verified_at:
                verified_date = f"<t:{int(verified_at)}:F>"
            else:
                verified_date = "Fecha no disponible"
        else:
            status_text = "❌ **NO VERIFICADO**"
            status_color = 0xff0000
            verified_date = "N/A"

        embed.color = status_color

        embed.add_field(
            name="🔐 Estado de Verificación",
            value=f"{status_text}\n**Fecha:** {verified_date}",
            inline=False
        )

        if is_verified and roblox_username != 'No disponible':
            embed.add_field(
                name="👤 Cuenta de Roblox",
                value=f"**Usuario:** [{roblox_username}](https://www.roblox.com/users/profile?username={roblox_username})\n**Perfil:** [Ver en Roblox](https://www.roblox.com/users/profile?username={roblox_username})",
                inline=True
            )

            # Información adicional de Roblox
            roblox_info = profile.get('roblox_info', {})
            if roblox_info:
                embed.add_field(
                    name="📊 Información Adicional",
                    value=f"**ID de Roblox:** {roblox_info.get('user_id', 'No disponible')}\n**Último check:** <t:{int(roblox_info.get('last_check', time.time()))}:R>",
                    inline=True
                )

        # Historial de verificación
        verification_attempts = profile.get('verification_attempts', 0)
        failed_attempts = profile.get('failed_verification_attempts', 0)

        embed.add_field(
            name="📈 Historial de Verificación",
            value=f"**Intentos totales:** {verification_attempts}\n**Intentos fallidos:** {failed_attempts}\n**Tasa de éxito:** {((verification_attempts - failed_attempts) / max(verification_attempts, 1) * 100):.1f}%",
            inline=False
        )

        # Tiempo restante de verificación
        if is_verified and verified_at:
            expiry_time = verified_at + (30 * 24 * 60 * 60)  # 30 días
            time_remaining = expiry_time - time.time()

            if time_remaining > 0:
                days_remaining = int(time_remaining / (24 * 60 * 60))
                embed.add_field(
                    name="⏰ Tiempo Restante",
                    value=f"**{days_remaining}** días hasta expiración\n**Expira:** <t:{int(expiry_time)}:R>",
                    inline=True
                )
            else:
                embed.add_field(
                    name="⚠️ Verificación Expirada",
                    value="La verificación ha expirado\nUse `/verify` para renovar",
                    inline=True
                )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Sistema de Verificación • Gracias por la idea kxis3rr")

        return embed

    def create_coins_embed(self):
        """Crear embed de información de monedas"""
        embed = discord.Embed(
            title=f"💰 Monedas de {self.target_user.name}",
            description="Balance, historial y estadísticas del sistema de monedas",
            color=0xffd700
        )

        profile = self.profile_data

        # Balance actual
        balance = profile.get('coins_balance', 0)
        total_earned = profile.get('total_coins_earned', 0)
        total_spent = profile.get('total_coins_spent', 0)

        embed.add_field(
            name="💎 Balance Actual",
            value=f"**{balance:,}** monedas",
            inline=True
        )

        embed.add_field(
            name="📈 Total Ganado",
            value=f"**{total_earned:,}** monedas",
            inline=True
        )

        embed.add_field(
            name="💸 Total Gastado",
            value=f"**{total_spent:,}** monedas",
            inline=True
        )

        # Estadísticas de transacciones
        total_transactions = profile.get('total_transactions', 0)
        avg_transaction = (total_earned + total_spent) / max(total_transactions, 1)

        embed.add_field(
            name="📊 Estadísticas de Transacciones",
            value=f"**Total transacciones:** {total_transactions}\n**Promedio por transacción:** {avg_transaction:.1f} monedas\n**Eficiencia:** {((total_earned - total_spent) / max(total_earned, 1) * 100):.1f}%",
            inline=False
        )

        # Últimas transacciones
        recent_transactions = profile.get('recent_transactions', [])[:3]
        if recent_transactions:
            trans_text = []
            for trans in recent_transactions:
                trans_type = "💰" if trans['type'] == 'earn' else "💸"
                trans_text.append(f"{trans_type} **{trans['amount']:,}** - {trans['reason'][:30]}...")

            embed.add_field(
                name="⏰ Transacciones Recientes",
                value="\n".join(trans_text),
                inline=False
            )
        else:
            embed.add_field(
                name="⏰ Transacciones Recientes",
                value="Sin transacciones recientes",
                inline=False
            )

        # Métodos de ganancia más frecuentes
        earning_methods = profile.get('earning_methods', {})
        if earning_methods:
            method_text = "\n".join([f"• **{method}:** {count} veces" for method, count in sorted(earning_methods.items(), key=lambda x: x[1], reverse=True)[:3]])
        else:
            method_text = "Sin datos de métodos de ganancia"

        embed.add_field(
            name="🎯 Métodos de Ganancia",
            value=method_text,
            inline=True
        )

        # Nivel de riqueza
        wealth_level = self.get_wealth_level(balance)
        embed.add_field(
            name="👑 Nivel de Riqueza",
            value=f"**{wealth_level['title']}**\n{wealth_level['description']}",
            inline=True
        )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Sistema de Monedas • Gracias por la idea kxis3rr")

        return embed

    def create_activity_embed(self):
        """Crear embed de estadísticas de actividad"""
        embed = discord.Embed(
            title=f"📈 Actividad de {self.target_user.name}",
            description="Estadísticas detalladas de uso del bot y actividad",
            color=0x9b59b6
        )

        profile = self.profile_data

        # Estadísticas generales
        total_commands = profile.get('total_commands', 0)
        active_days = profile.get('active_days', 0)
        first_seen = profile.get('first_seen')

        embed.add_field(
            name="📊 Estadísticas Generales",
            value=f"**Comandos usados:** {total_commands:,}\n**Días activo:** {active_days}\n**Miembro desde:** <t:{int(first_seen or time.time())}:R>",
            inline=True
        )

        # Comandos más usados
        top_commands = profile.get('top_commands', [])[:5]
        if top_commands:
            cmd_text = "\n".join([f"• `/{cmd['name']}` - {cmd['count']} veces" for cmd in top_commands])
        else:
            cmd_text = "Sin datos de comandos"

        embed.add_field(
            name="🔥 Comandos Más Usados",
            value=cmd_text,
            inline=True
        )

        # Actividad por día
        daily_activity = profile.get('daily_activity', {})
        if daily_activity:
            today_activity = daily_activity.get(datetime.now().strftime('%Y-%m-%d'), 0)
            week_activity = sum([daily_activity.get((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'), 0) for i in range(7)])
        else:
            today_activity = 0
            week_activity = 0

        embed.add_field(
            name="📅 Actividad Reciente",
            value=f"**Hoy:** {today_activity} comandos\n**Esta semana:** {week_activity} comandos\n**Promedio diario:** {week_activity / 7:.1f} comandos",
            inline=False
        )

        # Racha de actividad
        activity_streak = profile.get('activity_streak', 0)
        longest_streak = profile.get('longest_activity_streak', 0)

        embed.add_field(
            name="🔥 Racha de Actividad",
            value=f"**Racha actual:** {activity_streak} días\n**Racha más larga:** {longest_streak} días",
            inline=True
        )

        # Horarios más activos
        peak_hours = profile.get('peak_activity_hours', [])[:3]
        if peak_hours:
            hours_text = ", ".join([f"{hour}:00" for hour in peak_hours])
        else:
            hours_text = "Sin datos"

        embed.add_field(
            name="⏰ Horarios Más Activos",
            value=f"**Horas pico:** {hours_text}",
            inline=True
        )

        # Nivel de actividad
        activity_level = self.get_activity_level(profile)
        embed.add_field(
            name="🎯 Nivel de Usuario",
            value=f"**{activity_level['level']}**\n{activity_level['description']}\n**Progreso:** {activity_level['progress']}%",
            inline=False
        )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Estadísticas de Actividad • Gracias por la idea kxis3rr")

        return embed

    def create_security_embed(self):
        """Crear embed de información de seguridad"""
        embed = discord.Embed(
            title=f"🛡️ Seguridad de {self.target_user.name}",
            description="Información del sistema anti-alt y estado de seguridad",
            color=0xe74c3c
        )

        profile = self.profile_data

        # Estado de seguridad general
        risk_level = profile.get('risk_level', 'bajo')
        is_trusted = profile.get('is_trusted', True)
        warnings = profile.get('warnings', 0)

        risk_colors = {'bajo': 0x00ff00, 'medio': 0xffaa00, 'alto': 0xff0000}
        embed.color = risk_colors.get(risk_level, 0x00ff00)

        status_text = "🟢 Confiable" if is_trusted else "🟡 En revisión"
        embed.add_field(
            name="🛡️ Estado de Seguridad",
            value=f"**Estado:** {status_text}\n**Nivel de riesgo:** {risk_level.title()}\n**Advertencias:** {warnings}",
            inline=True
        )

        # Información del fingerprint
        fingerprint_data = profile.get('fingerprint_data', {})
        if fingerprint_data:
            account_age_hours = fingerprint_data.get('account_age_hours', 0)
            account_age_days = account_age_hours / 24

            embed.add_field(
                name="👤 Información de Cuenta",
                value=f"**Antigüedad:** {account_age_days:.1f} días\n**Score de confianza:** {fingerprint_data.get('trust_score', 0):.2f}\n**Actividades sospechosas:** {len(fingerprint_data.get('suspicious_activities', []))}",
                inline=True
            )

        # Historial de infracciones
        infractions = profile.get('security_infractions', [])
        if infractions:
            recent_infractions = infractions[-3:]  # Últimas 3
            infraction_text = "\n".join([f"• {inf['reason']} - <t:{int(inf['timestamp'])}:R>" for inf in recent_infractions])
        else:
            infraction_text = "Sin infracciones registradas"

        embed.add_field(
            name="⚠️ Historial de Infracciones",
            value=infraction_text,
            inline=False
        )

        # Análisis de patrones
        pattern_analysis = profile.get('pattern_analysis', {})
        if pattern_analysis:
            embed.add_field(
                name="🔍 Análisis de Patrones",
                value=f"**Similaridad de nombres:** {pattern_analysis.get('username_similarity', 0):.2f}\n**Patrón de uso:** {pattern_analysis.get('usage_pattern', 'Normal')}\n**Score de comportamiento:** {pattern_analysis.get('behavior_score', 100):.1f}%",
                inline=True
            )

        # Reputación del usuario
        reputation = profile.get('user_reputation', {})
        if reputation:
            rep_score = reputation.get('score', 100)
            rep_status = "Excelente" if rep_score >= 90 else "Buena" if rep_score >= 70 else "Regular" if rep_score >= 50 else "Baja"

            embed.add_field(
                name="⭐ Reputación",
                value=f"**Score:** {rep_score:.1f}/100\n**Status:** {rep_status}\n**Reportes:** {reputation.get('reports', 0)}",
                inline=True
            )

        # Recomendaciones de seguridad
        if not is_trusted or warnings > 0:
            recommendations = []
            if warnings > 0:
                recommendations.append("• Evitar actividades sospechosas")
            if risk_level != 'bajo':
                recommendations.append("• Verificar cuenta de Roblox")
                recommendations.append("• Mantener actividad regular")

            if recommendations:
                embed.add_field(
                    name="💡 Recomendaciones",
                    value="\n".join(recommendations),
                    inline=False
                )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Sistema de Seguridad • Gracias por la idea kxis3rr")

        return embed

    def create_achievements_embed(self):
        """Crear embed de logros y códigos"""
        embed = discord.Embed(
            title=f"🏆 Logros de {self.target_user.name}",
            description="Códigos canjeados, logros obtenidos y progreso",
            color=0xf39c12
        )

        profile = self.profile_data

        # Códigos canjeados
        redeemed_codes = profile.get('redeemed_codes', [])
        total_codes = len(redeemed_codes)
        unique_codes = len(set(redeemed_codes))

        embed.add_field(
            name="🎫 Códigos Canjeados",
            value=f"**Total canjeados:** {total_codes}\n**Códigos únicos:** {unique_codes}\n**Tasa de éxito:** {(unique_codes / max(total_codes, 1) * 100):.1f}%",
            inline=True
        )

        # Últimos códigos canjeados
        recent_codes = profile.get('recent_redeemed_codes', [])[:3]
        if recent_codes:
            codes_text = "\n".join([f"• `{code['code']}` - <t:{int(code['timestamp'])}:R>" for code in recent_codes])
        else:
            codes_text = "Sin códigos canjeados recientemente"

        embed.add_field(
            name="⏰ Códigos Recientes",
            value=codes_text,
            inline=True
        )

        # Logros desbloqueados
        achievements = profile.get('achievements', [])
        achievement_count = len(achievements)

        embed.add_field(
            name="🏅 Logros Desbloqueados",
            value=f"**Total logros:** {achievement_count}\n**Progreso:** {(achievement_count / 20 * 100):.1f}% (20 total)",
            inline=False
        )

        # Mostrar algunos logros
        if achievements:
            recent_achievements = achievements[-3:]  # Últimos 3 logros
            achievements_text = "\n".join([f"🏆 **{ach['name']}** - <t:{int(ach['unlocked_at'])}:R>" for ach in recent_achievements])
        else:
            achievements_text = "Sin logros desbloqueados aún"

        embed.add_field(
            name="🆕 Logros Recientes",
            value=achievements_text,
            inline=False
        )

        # Estadísticas de códigos por categoría
        code_stats = profile.get('code_statistics', {})
        if code_stats:
            stats_text = "\n".join([f"• **{category}:** {count} códigos" for category, count in sorted(code_stats.items(), key=lambda x: x[1], reverse=True)[:3]])
        else:
            stats_text = "Sin estadísticas de códigos"

        embed.add_field(
            name="📊 Códigos por Categoría",
            value=stats_text,
            inline=True
        )

        # Racha de códigos
        code_streak = profile.get('code_redemption_streak', 0)
        longest_streak = profile.get('longest_code_streak', 0)

        embed.add_field(
            name="🔥 Racha de Códigos",
            value=f"**Racha actual:** {code_streak} días\n**Racha más larga:** {longest_streak} días",
            inline=True
        )

        # Próximos logros
        next_achievements = [
            {"name": "Primer Código", "condition": "Canjear tu primer código", "progress": min(total_codes, 1)},
            {"name": "Coleccionista", "condition": "Canjear 10 códigos únicos", "progress": min(unique_codes / 10, 1)},
            {"name": "Verificado", "condition": "Verificar cuenta de Roblox", "progress": 1 if profile.get('is_verified') else 0}
        ]

        progress_text = []
        for ach in next_achievements:
            if ach['progress'] < 1:
                progress_text.append(f"• **{ach['name']}** - {ach['progress']*100:.0f}%")

        if progress_text:
            embed.add_field(
                name="🎯 Próximos Logros",
                value="\n".join(progress_text[:3]),
                inline=False
            )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Logros y Códigos • Gracias por la idea kxis3rr")

        return embed

    def get_activity_level(self, profile):
        """Determinar el nivel de actividad del usuario"""
        total_commands = profile.get('total_commands', 0)
        active_days = profile.get('active_days', 0)

        if total_commands >= 100 and active_days >= 30:
            return {"level": "🌟 Usuario Veterano", "description": "Usuario muy activo y experimentado", "progress": 100}
        elif total_commands >= 50 and active_days >= 14:
            return {"level": "⭐ Usuario Activo", "description": "Usuario regular con buena actividad", "progress": 75}
        elif total_commands >= 20 and active_days >= 7:
            return {"level": "📈 Usuario Intermedio", "description": "Usuario con actividad moderada", "progress": 50}
        elif total_commands >= 5:
            return {"level": "🚀 Usuario Nuevo", "description": "Empezando a usar el bot", "progress": 25}
        else:
            return {"level": "👋 Principiante", "description": "Recién llegado al bot", "progress": 10}

    def get_wealth_level(self, balance):
        """Determinar el nivel de riqueza del usuario"""
        if balance >= 10000:
            return {"title": "💎 Magnate Digital", "description": "Elite de usuarios con gran riqueza"}
        elif balance >= 5000:
            return {"title": "🏆 Millonario", "description": "Usuario muy próspero"}
        elif balance >= 2000:
            return {"title": "💰 Rico", "description": "Usuario con buen balance"}
        elif balance >= 1000:
            return {"title": "💳 Ahorrador", "description": "Usuario con finanzas estables"}
        elif balance >= 500:
            return {"title": "🪙 Clase Media", "description": "Usuario con balance moderado"}
        elif balance >= 100:
            return {"title": "💵 Trabajador", "description": "Usuario construyendo su fortuna"}
        else:
            return {"title": "🌱 Emprendedor", "description": "Comenzando su viaje financiero"}

class UserProfileSystem:
    def __init__(self):
        self.profiles_file = "user_profiles.json"
        self.user_profiles = {}
        self.load_profiles_data()

    def load_profiles_data(self):
        """Cargar datos de perfiles desde archivo"""
        try:
            if Path(self.profiles_file).exists():
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_profiles = data.get('user_profiles', {})
                    logger.info(f"✅ Perfiles cargados para {len(self.user_profiles)} usuarios")
            else:
                self.user_profiles = {}
                logger.info("⚠️ Archivo de perfiles no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando perfiles: {e}")
            self.user_profiles = {}

    def save_profiles_data(self):
        """Guardar datos de perfiles a archivo"""
        try:
            data = {
                'user_profiles': self.user_profiles,
                'last_updated': datetime.now().isoformat(),
                'total_profiles': len(self.user_profiles)
            }
            with open(self.profiles_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Perfiles guardados para {len(self.user_profiles)} usuarios")
        except Exception as e:
            logger.error(f"❌ Error guardando perfiles: {e}")

    def update_user_profile(self, user_id: str, **kwargs):
        """Actualizar perfil de usuario con nueva información"""
        user_id = str(user_id)

        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'first_seen': time.time(),
                'last_activity': time.time(),
                'total_commands': 0,
                'active_days': 0,
                'is_verified': False,
                'roblox_username': None,
                'coins_balance': 0,
                'total_games': 0,
                'total_servers': 0,
                'redeemed_codes': [],
                'achievements': [],
                'warnings': 0,
                'risk_level': 'bajo',
                'is_trusted': True
            }

        # Actualizar campos proporcionados
        for key, value in kwargs.items():
            if key in self.user_profiles[user_id]:
                self.user_profiles[user_id][key] = value

        # Actualizar timestamp de última actividad
        self.user_profiles[user_id]['last_activity'] = time.time()

        # Guardar cambios
        self.save_profiles_data()

    def get_user_profile(self, user_id: str) -> dict:
        """Obtener perfil completo de usuario"""
        user_id = str(user_id)

        # Si no existe el perfil, crear uno básico
        if user_id not in self.user_profiles:
            self.update_user_profile(user_id)

        return self.user_profiles.get(user_id, {})

    
    def collect_user_data(self, user_id: str, user_obj=None) -> dict:
        """Recopilar todos los datos de un usuario desde diferentes sistemas"""
        try:
            # Cargar datos de monedas desde user_coins.json
            coins_data = self.load_user_coins_data(user_id)

            # Cargar datos de servidores desde users_servers.json  
            servers_data = self.load_user_servers_data(user_id)

            # Datos básicos
            data = {
                'user_id': user_id,
                'username': user_obj.name if user_obj else 'Usuario Desconocido',
                'discriminator': user_obj.discriminator if user_obj else '0000',
                'avatar_url': str(user_obj.avatar.url) if user_obj and user_obj.avatar else None,
                'created_at': user_obj.created_at.isoformat() if user_obj else None,
                'joined_at': None,  # Se llenará si está en un servidor

                # Verificación (importar desde main.py)
                'is_verified': False,  # Se actualizará si hay acceso al sistema de verificación
                'verification_date': None,
                'roblox_username': None,
                'roblox_id': None,

                # Servidores de juegos (desde user_game_servers.json - estructura simplificada)
                'user_servers': servers_data['servers'],
                'game_servers': servers_data['games'],  # Compatibilidad con estructura antigua
                'total_servers': servers_data['total_servers'],
                'total_games': servers_data['total_games'],

                # Monedas (desde user_coins.json)
                'coins': coins_data,

                # Actividad y seguridad
                'warnings': [],
                'is_banned': False,
                'ban_info': {},

                # Logros y estadísticas
                'achievements': [],
                'total_commands_used': 0,
                'first_command_date': None,
                'last_activity': None
            }
# Guardar en perfiles
            self.user_profiles[user_id] = data
            self.save_profiles_data()

            logger.info(f"📊 Datos recopilados para usuario {user_id}: verificado={data['is_verified']}, juegos={data['total_games']}, servidores={data['total_servers']}")
            return data

        except Exception as e:
            logger.error(f"❌ Error recopilando datos del usuario {user_id}: {e}")
            return {}

    def load_user_coins_data(self, user_id: str) -> dict:
        """Cargar datos de monedas desde user_coins.json"""
        try:
            import json
            from pathlib import Path

            coins_file = Path("user_coins.json")
            if coins_file.exists():
                with open(coins_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    user_coins = data.get('user_coins', {}).get(user_id, {})

                    transactions = user_coins.get('transactions', [])
                    return {
                        'balance': user_coins.get('balance', 0),
                        'total_earned': user_coins.get('total_earned', 0),
                        'total_transactions': len(transactions),
                        'last_activity': transactions[-1]['timestamp'] if transactions else None
                    }

            return {
                'balance': 0,
                'total_earned': 0,
                'total_transactions': 0,
                'last_activity': None
            }
        except Exception as e:
            logger.error(f"❌ Error cargando datos de monedas para {user_id}: {e}")
            return {
                'balance': 0,
                'total_earned': 0,
                'total_transactions': 0,
                'last_activity': None
            }

    def load_user_servers_data(self, user_id: str) -> dict:
        """Cargar datos de servidores desde user_game_servers.json con estructura simplificada"""
        try:
            import json
            from pathlib import Path

            # Intentar cargar desde el nuevo archivo simplificado
            servers_file = Path("user_game_servers.json")
            if servers_file.exists():
                with open(servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    user_servers = data.get('user_servers', {}).get(user_id, [])
                    
                    return {
                        'servers': user_servers,
                        'total_servers': len(user_servers),
                        'games': {},  # Mantener compatibilidad
                        'total_games': 1 if user_servers else 0  # Contar como 1 juego si tiene servidores
                    }

            # Fallback: intentar cargar desde users_servers.json (estructura antigua)
            fallback_file = Path("users_servers.json")
            if fallback_file.exists():
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    user_data = data.get('users', {}).get(user_id, {})
                    games = user_data.get('games', {})

                    total_servers = 0
                    for game_id, game_data in games.items():
                        servers = game_data.get('server_links', [])
                        total_servers += len(servers)

                    return {
                        'games': games,
                        'total_games': len(games),
                        'total_servers': total_servers,
                        'servers': []  # Nuevo campo vacío
                    }

            return {
                'servers': [],
                'games': {},
                'total_games': 0,
                'total_servers': 0
            }
        except Exception as e:
            logger.error(f"❌ Error cargando datos de servidores para {user_id}: {e}")
            return {
                'servers': [],
                'games': {},
                'total_games': 0,
                'total_servers': 0
            }

def save_user_servers_simple(self, user_id: str, servers: list):
        """Guardar servidores de usuario en la estructura simplificada"""
        try:
            import json
            from pathlib import Path
            from datetime import datetime

            servers_file = Path("user_game_servers.json")
            
            # Cargar datos existentes
            if servers_file.exists():
                with open(servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {
                    "user_servers": {},
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat(),
                        "total_users": 0,
                        "total_servers": 0,
                        "description": "Estructura simplificada: user_id -> array de hasta 5 servidores"
                    }
                }

            # Limitar a máximo 5 servidores
            servers = servers[:5] if servers else []
            
            # Actualizar datos del usuario
            data['user_servers'][user_id] = servers
            
            # Actualizar metadata
            data['metadata']['last_updated'] = datetime.now().isoformat()
            data['metadata']['total_users'] = len(data['user_servers'])
            data['metadata']['total_servers'] = sum(len(user_servers) for user_servers in data['user_servers'].values())

            # Guardar archivo
            with open(servers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Servidores guardados para usuario {user_id}: {len(servers)} servidores")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando servidores para {user_id}: {e}")
            return False

    def add_server_to_user_simple(self, user_id: str, server_link: str):
        """Agregar un servidor a la lista del usuario en formato simplificado"""
        try:
            # Cargar servidores actuales
            current_servers = self.load_user_servers_data(user_id)['servers']
            
            # Si el servidor ya existe, no agregarlo
            if server_link in current_servers:
                return False
            
            # Agregar nuevo servidor al inicio de la lista
            current_servers.insert(0, server_link)
            
            # Guardar la lista actualizada
            return self.save_user_servers_simple(user_id, current_servers)
            
        except Exception as e:
            logger.error(f"❌ Error agregando servidor para {user_id}: {e}")
            return False

    def get_all_user_servers(self):
        """Obtener todos los servidores de todos los usuarios desde la estructura simplificada"""
        try:
            import json
            from pathlib import Path

            servers_file = Path("user_game_servers.json")
            if servers_file.exists():
                with open(servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('user_servers', {})
            
            return {}

        except Exception as e:
            logger.error(f"❌ Error obteniendo todos los servidores: {e}")
            return {}

# Instancia global del sistema de perfiles
user_profile_system = UserProfileSystem()

def setup_profile_commands(bot):
    """Configurar comandos de perfiles"""

    @bot.tree.command(name="profile", description="Ver el perfil completo de un usuario con toda su información del bot")
    async def profile_command(interaction: discord.Interaction, usuario: discord.User = None):
        """Comando para ver el perfil de un usuario"""

        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return

        # Si no se especifica usuario, usar el que ejecuta el comando
        target_user = usuario or interaction.user
        user_id = str(target_user.id)

        # Recopilar datos actualizados del usuario
        profile_data = user_profile_system.collect_user_data(user_id)

        # Crear vista con menú desplegable
        view = ProfileView(str(interaction.user.id), target_user, profile_data)

        # Crear embed inicial (overview)
        embed = view.create_overview_embed()

        # Como check_verification ya hizo defer, usar followup en lugar de response
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

        # Log del uso del comando
        requester = f"{interaction.user.name}#{interaction.user.discriminator}"
        target = f"{target_user.name}#{target_user.discriminator}"
        logger.info(f"👤 {requester} vio el perfil de {target}")

    return user_profile_system