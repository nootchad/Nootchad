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
        """Crear embed de información de servidores sin límite"""
        embed = discord.Embed(
            title=f"🎮 Servidores de {self.target_user.name}",
            description="Información detallada sobre servidores VIP y actividad de juegos (sin límite)",
            color=0x00ff88
        )

        profile = self.profile_data

        # Estadísticas de servidores desde user_game_servers.json
        servers_data = profile.get('servers_data', {})
        user_servers = servers_data.get('servers', [])
        total_servers = len(user_servers)
        total_games = servers_data.get('total_games', 0)
        servers_by_game = servers_data.get('servers_by_game', {})

        embed.add_field(
            name="📊 Estadísticas de Servidores (Sin Límite)",
            value=f"**🖥️ Total de servidores:** {total_servers:,}\n**🎯 Juegos únicos:** {total_games}\n**📈 Sin límite de servidores**",
            inline=True
        )

        # Mostrar resumen de los servidores del usuario
        if user_servers:
            # Mostrar estadísticas por rangos
            if total_servers <= 5:
                status = "🌱 Colección Inicial"
            elif total_servers <= 20:
                status = "📈 Colección en Crecimiento"
            elif total_servers <= 50:
                status = "⭐ Colección Avanzada"
            elif total_servers <= 100:
                status = "🏆 Colección Experta"
            else:
                status = "💎 Maestro de Servidores"
            
            embed.add_field(
                name="🏅 Estado de Colección",
                value=f"**{status}**\n{total_servers:,} servidores acumulados",
                inline=True
            )

            # Mostrar distribución por juegos
            if servers_by_game:
                top_games = sorted(servers_by_game.items(), key=lambda x: x[1], reverse=True)[:3]
                games_text = []
                for game_id, count in top_games:
                    game_name = self.get_game_name_display(game_id, profile)
                    games_text.append(f"• **{game_name}:** {count:,} servidores")
                
                embed.add_field(
                    name="🔥 Top 3 Juegos por Servidores",
                    value="\n".join(games_text) if games_text else "Sin datos",
                    inline=False
                )

            # Mostrar algunos enlaces de ejemplo
            sample_servers = user_servers[:3]  # Primeros 3 como muestra
            servers_preview = []
            for i, server in enumerate(sample_servers, 1):
                try:
                    # Extraer game ID del enlace para mostrar información
                    if "/games/" in server:
                        game_id = server.split("/games/")[1].split("?")[0]
                        game_name = self.get_game_name_display(game_id, profile)
                        servers_preview.append(f"**{i}.** [{game_name}]({server})")
                    else:
                        servers_preview.append(f"**{i}.** [Servidor #{i}]({server})")
                except:
                    servers_preview.append(f"**{i}.** [Servidor #{i}]({server})")
            
            if total_servers > 3:
                remaining = total_servers - 3
                servers_preview.append(f"**...y {remaining:,} servidores más**")

            embed.add_field(
                name="🔗 Muestra de Servidores Guardados",
                value="\n".join(servers_preview) if servers_preview else "Sin servidores",
                inline=False
            )

        else:
            embed.add_field(
                name="📭 Sin Servidores",
                value="Este usuario aún no ha recopilado servidores.\nUsa `/servertest` para comenzar a acumular servidores sin límite.",
                inline=False
            )

        # Progreso y estadísticas adicionales
        daily_avg = profile.get('daily_server_average', 0)
        total_attempts = profile.get('total_scraping_attempts', 0)
        
        embed.add_field(
            name="📈 Progreso de Recopilación",
            value=f"**Promedio diario:** {daily_avg:.1f} servidores\n**Intentos de scraping:** {total_attempts}\n**Eficiencia:** {((total_servers / max(total_attempts, 1)) * 100):.1f}%",
            inline=True
        )

        # Último servidor agregado
        if user_servers:
            last_server_time = profile.get('last_server_added', time.time())
            embed.add_field(
                name="⏰ Último Servidor Agregado",
                value=f"<t:{int(last_server_time)}:R>",
                inline=True
            )

        embed.add_field(
            name="🚀 Sistema Sin Límite",
            value="• Cada uso de `/servertest` agrega más servidores\n• No hay límite máximo de servidores\n• Los servidores se acumulan automáticamente",
            inline=False
        )

        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        embed.set_footer(text="RbxServers • Servidores Sin Límite • Gracias por la idea kxis3rr")

        return embed
    
    def get_game_name_display(self, game_id: str, profile: dict) -> str:
        """Obtener nombre del juego para mostrar en el embed"""
        # Intentar obtener desde datos del perfil primero
        games_data = profile.get('servers_data', {}).get('games', {})
        if game_id in games_data:
            return games_data[game_id].get('game_name', f'Game {game_id}')
        
        # Fallback a nombres conocidos
        game_names = {
            "2753915549": "🌊 Blox Fruits",
            "6284583030": "🎃 Pet Simulator X",
            "185655149": "🏡 Welcome to Bloxburg",
            "920587237": "🏠 Adopt Me!",
            "4924922222": "🏘️ Brookhaven RP",
            "735030788": "👑 Royale High",
            "606849621": "🚓 Jailbreak",
            "4616652839": "⚔️ Shindo Life",
            "142823291": "🔍 Murder Mystery 2",
            "4646477729": "⭐ All Star Tower Defense"
        }
        return game_names.get(game_id, f"🎮 Game {game_id}")

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
        """Recopilar todos los datos de un usuario desde diferentes sistemas (sin límite de servidores)"""
        try:
            # Cargar datos de monedas desde user_coins.json
            coins_data = self.load_user_coins_data(user_id)

            # Cargar datos de servidores desde user_game_servers.json (sin límite)
            servers_data = self.load_user_servers_data(user_id)

            # Obtener datos de verificación desde el sistema global
            verification_data = self.get_verification_data(user_id)

            # Calcular estadísticas adicionales de servidores
            total_servers = servers_data['total_servers']
            daily_avg = 0
            last_server_added = time.time()
            
            # Estimar progreso basado en cantidad de servidores
            if total_servers > 0:
                # Estimar que el usuario ha estado activo por algunos días
                estimated_days = max(1, total_servers // 5)  # Aproximadamente 5 servidores por día activo
                daily_avg = total_servers / estimated_days

            # Datos básicos
            data = {
                'user_id': user_id,
                'username': user_obj.name if user_obj else 'Usuario Desconocido',
                'discriminator': user_obj.discriminator if user_obj else '0000',
                'avatar_url': str(user_obj.avatar.url) if user_obj and user_obj.avatar else None,
                'created_at': user_obj.created_at.isoformat() if user_obj else None,
                'joined_at': None,  # Se llenará si está en un servidor

                # Verificación (desde sistema global)
                'is_verified': verification_data['is_verified'],
                'verification_date': verification_data.get('verified_at'),
                'roblox_username': verification_data.get('roblox_username'),
                'roblox_id': verification_data.get('roblox_id'),

                # Servidores de juegos (desde user_game_servers.json - SIN LÍMITE)
                'servers_data': servers_data,  # Todos los datos de servidores
                'user_servers': servers_data['servers'],  # Lista completa de servidores
                'game_servers': servers_data['games'],  # Datos organizados por juego
                'total_servers': total_servers,  # Cantidad real sin límite
                'total_games': servers_data['total_games'],
                'main_game': servers_data.get('main_game'),
                'servers_by_game': servers_data.get('servers_by_game', {}),

                # Estadísticas adicionales de servidores
                'daily_server_average': daily_avg,
                'last_server_added': last_server_added,
                'total_scraping_attempts': max(total_servers, 1),  # Estimación

                # Monedas (desde user_coins.json)
                'coins': coins_data,
                'coins_balance': coins_data.get('balance', 0),

                # Actividad y seguridad
                'warnings': verification_data.get('warnings', 0),
                'is_banned': verification_data.get('is_banned', False),
                'ban_info': verification_data.get('ban_info', {}),
                'is_trusted': not verification_data.get('is_banned', False),
                'risk_level': 'bajo' if not verification_data.get('is_banned', False) else 'alto',

                # Estadísticas de actividad
                'total_commands': total_servers,  # Usar servidores como proxy de actividad
                'active_days': max(1, total_servers // 5),  # Estimación
                'first_seen': verification_data.get('verified_at', time.time()),
                'last_activity': time.time(),

                # Logros y estadísticas
                'achievements': [],
                'redeemed_codes': [],
                'total_commands_used': total_servers,
                'first_command_date': verification_data.get('verified_at'),
                'verified_at': verification_data.get('verified_at')
            }

            # Guardar en perfiles
            self.user_profiles[user_id] = data
            self.save_profiles_data()

            logger.info(f"📊 Datos recopilados para usuario {user_id}: verificado={data['is_verified']}, juegos={data['total_games']}, servidores={data['total_servers']:,} (sin límite)")
            return data

        except Exception as e:
            logger.error(f"❌ Error recopilando datos del usuario {user_id}: {e}")
            return {
                'user_id': user_id,
                'servers_data': {'servers': [], 'total_servers': 0, 'total_games': 0, 'games': {}, 'servers_by_game': {}},
                'total_servers': 0,
                'total_games': 0,
                'is_verified': False,
                'coins_balance': 0
            }

    def get_verification_data(self, user_id: str) -> dict:
        """Obtener datos de verificación desde el sistema global"""
        try:
            # Importar aquí para evitar import circular
            from main import roblox_verification
            
            is_verified = roblox_verification.is_user_verified(user_id)
            verification_info = roblox_verification.verified_users.get(user_id, {})
            
            return {
                'is_verified': is_verified,
                'roblox_username': verification_info.get('roblox_username'),
                'verified_at': verification_info.get('verified_at'),
                'verification_code': verification_info.get('verification_code'),
                'warnings': roblox_verification.get_user_warnings(user_id),
                'is_banned': roblox_verification.is_user_banned(user_id),
                'ban_info': {
                    'ban_time': roblox_verification.banned_users.get(user_id),
                    'remaining_time': None  # Se puede calcular si está baneado
                }
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de verificación para {user_id}: {e}")
            return {
                'is_verified': False,
                'roblox_username': None,
                'verified_at': None,
                'warnings': 0,
                'is_banned': False,
                'ban_info': {}
            }

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
        """Cargar datos de servidores desde user_game_servers.json sin límite de servidores"""
        try:
            import json
            from pathlib import Path

            # Cargar desde el archivo simplificado user_game_servers.json
            servers_file = Path("user_game_servers.json")
            if servers_file.exists():
                with open(servers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    user_servers = data.get('user_servers', {}).get(user_id, [])
                    
                    # Detectar juegos únicos desde los enlaces (sin límite)
                    game_ids_found = set()
                    games_data = {}
                    
                    for server_link in user_servers:
                        # Extraer game ID desde el enlace
                        try:
                            if "/games/" in server_link:
                                game_id = server_link.split("/games/")[1].split("?")[0]
                                game_ids_found.add(game_id)
                                
                                if game_id not in games_data:
                                    games_data[game_id] = {
                                        'server_links': [],
                                        'game_name': self.get_game_name_from_id(game_id),
                                        'category': 'rpg' if game_id == "2753915549" else 'other'
                                    }
                                
                                games_data[game_id]['server_links'].append(server_link)
                        except Exception:
                            # Si no se puede extraer el game ID, agrupar en un juego por defecto
                            default_game = "unknown"
                            if default_game not in games_data:
                                games_data[default_game] = {
                                    'server_links': [],
                                    'game_name': 'Juegos Varios',
                                    'category': 'other'
                                }
                            games_data[default_game]['server_links'].append(server_link)
                    
                    # Detectar juego principal (el que más servidores tenga)
                    main_game = None
                    max_servers = 0
                    for game_id, game_data in games_data.items():
                        if len(game_data['server_links']) > max_servers:
                            max_servers = len(game_data['server_links'])
                            main_game = game_id
                    
                    return {
                        'servers': user_servers,  # Lista completa sin límite
                        'total_servers': len(user_servers),  # Cantidad real sin límite
                        'games': games_data,  # Datos organizados por juego
                        'total_games': len(games_data),  # Cantidad de juegos únicos
                        'main_game': main_game,  # Juego principal
                        'servers_by_game': {game_id: len(game_data['server_links']) for game_id, game_data in games_data.items()}
                    }

            # Fallback: intentar cargar desde users_servers.json (estructura antigua)
            fallback_file = Path("users_servers.json")
            if fallback_file.exists():
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    user_data = data.get('users', {}).get(user_id, {})
                    games = user_data.get('games', {})

                    all_servers = []
                    total_servers = 0
                    for game_id, game_data in games.items():
                        servers = game_data.get('server_links', [])
                        all_servers.extend(servers)
                        total_servers += len(servers)

                    return {
                        'servers': all_servers,  # Todos los servidores en una lista
                        'games': games,
                        'total_games': len(games),
                        'total_servers': total_servers,
                        'main_game': list(games.keys())[0] if games else None,
                        'servers_by_game': {game_id: len(game_data.get('server_links', [])) for game_id, game_data in games.items()}
                    }

            return {
                'servers': [],
                'games': {},
                'total_games': 0,
                'total_servers': 0,
                'main_game': None,
                'servers_by_game': {}
            }
        except Exception as e:
            logger.error(f"❌ Error cargando datos de servidores para {user_id}: {e}")
            return {
                'servers': [],
                'games': {},
                'total_games': 0,
                'total_servers': 0,
                'main_game': None,
                'servers_by_game': {}
            }
    
    def get_game_name_from_id(self, game_id: str) -> str:
        """Obtener nombre del juego desde su ID"""
        game_names = {
            "2753915549": "🌊 Blox Fruits",
            "6284583030": "🎃 Pet Simulator X",
            "185655149": "🏡 Welcome to Bloxburg",
            "920587237": "🏠 Adopt Me!",
            "4924922222": "🏘️ Brookhaven RP",
            "735030788": "👑 Royale High",
            "606849621": "🚓 Jailbreak",
            "4616652839": "⚔️ Shindo Life",
            "142823291": "🔍 Murder Mystery 2",
            "4646477729": "⭐ All Star Tower Defense"
        }
        return game_names.get(game_id, f"🎮 Game {game_id}")

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

    @bot.tree.command(name="leaderboard", description="🏆 Ver ranking de usuarios con más servidores VIP")
    async def leaderboard_command(interaction: discord.Interaction):
        """Comando para ver el ranking de usuarios con más servidores VIP"""

        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Cargar datos desde user_game_servers.json
            import json
            from pathlib import Path
            
            servers_file = Path("user_game_servers.json")
            
            if not servers_file.exists():
                embed = discord.Embed(
                    title="❌ No hay datos",
                    description="No se encontró información de servidores.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            with open(servers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_servers_data = data.get('user_servers', {})
            
            if not user_servers_data:
                embed = discord.Embed(
                    title="📭 Sin datos",
                    description="No hay usuarios con servidores registrados aún.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear ranking basado en cantidad de servidores
            ranking = []
            for user_id, servers in user_servers_data.items():
                server_count = len(servers) if isinstance(servers, list) else 0
                if server_count > 0:
                    try:
                        # Intentar obtener el usuario de Discord
                        discord_user = bot.get_user(int(user_id))
                        if not discord_user:
                            discord_user = await bot.fetch_user(int(user_id))
                        
                        username = discord_user.name if discord_user else f"Usuario {user_id[:8]}"
                        
                        ranking.append({
                            'user_id': user_id,
                            'username': username,
                            'server_count': server_count,
                            'discord_user': discord_user
                        })
                    except Exception as e:
                        logger.debug(f"Error obteniendo usuario {user_id}: {e}")
                        ranking.append({
                            'user_id': user_id,
                            'username': f"Usuario {user_id[:8]}",
                            'server_count': server_count,
                            'discord_user': None
                        })
            
            # Ordenar por cantidad de servidores (descendente)
            ranking.sort(key=lambda x: x['server_count'], reverse=True)
            
            # Crear embed del leaderboard
            embed = discord.Embed(
                title="🏆 Leaderboard de Servidores VIP",
                description="Ranking de usuarios con más servidores VIP acumulados",
                color=0xffd700
            )
            
            # Mostrar top 10
            top_users = ranking[:10]
            
            leaderboard_text = []
            for i, user_data in enumerate(top_users, 1):
                # Emojis para posiciones
                if i == 1:
                    position_emoji = "🥇"
                elif i == 2:
                    position_emoji = "🥈"
                elif i == 3:
                    position_emoji = "🥉"
                else:
                    position_emoji = f"{i}."
                
                username = user_data['username']
                server_count = user_data['server_count']
                
                leaderboard_text.append(f"{position_emoji} **{username}** - {server_count:,} servidores")
            
            if leaderboard_text:
                embed.add_field(
                    name="🏆 Top 10 Usuarios",
                    value="\n".join(leaderboard_text),
                    inline=False
                )
            
            # Estadísticas generales
            total_users = len(ranking)
            total_servers = sum(user['server_count'] for user in ranking)
            avg_servers = total_servers / total_users if total_users > 0 else 0
            
            embed.add_field(
                name="📊 Estadísticas Generales",
                value=f"**Usuarios activos:** {total_users:,}\n**Total servidores:** {total_servers:,}\n**Promedio por usuario:** {avg_servers:.1f}",
                inline=True
            )
            
            # Información del usuario que ejecuta el comando
            user_id = str(interaction.user.id)
            user_ranking = next((i + 1 for i, user in enumerate(ranking) if user['user_id'] == user_id), None)
            user_servers = len(user_servers_data.get(user_id, []))
            
            if user_ranking:
                embed.add_field(
                    name="📍 Tu Posición",
                    value=f"**Puesto #{user_ranking}**\n{user_servers:,} servidores",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📍 Tu Posición",
                    value=f"Sin servidores aún\nUsa `/servertest` para empezar",
                    inline=True
                )
            
            embed.add_field(
                name="🚀 Sistema Sin Límite",
                value="• Sin límite máximo de servidores\n• Los servidores se acumulan automáticamente\n• Usa `/servertest` para conseguir más",
                inline=False
            )
            
            embed.set_footer(text="RbxServers • Leaderboard de Servidores • Sistema sin límite")
            embed.timestamp = datetime.now()
            
            await interaction.followup.send(embed=embed, ephemeral=False)
            
            # Log del uso del comando
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            logger.info(f"🏆 {username} (ID: {user_id}) usó comando /leaderboard")
            
        except Exception as e:
            logger.error(f"Error en comando leaderboard: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al generar el leaderboard.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    return user_profile_system