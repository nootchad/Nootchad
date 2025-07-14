
import discord
from discord.ext import commands
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import asyncio

logger = logging.getLogger(__name__)

class LeaderboardSystem:
    def __init__(self):
        self.leaderboard_file = "leaderboard_data.json"
        self.user_game_servers_file = "user_game_servers.json"
        self.load_leaderboard_data()

    def load_leaderboard_data(self):
        """Cargar datos del leaderboard"""
        try:
            if Path(self.leaderboard_file).exists():
                with open(self.leaderboard_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_week = data.get('current_week', self.get_current_week())
                    self.weekly_data = data.get('weekly_data', {})
                    self.all_time_data = data.get('all_time_data', {})
                    logger.info(f"✅ Datos de leaderboard cargados - Semana: {self.current_week}")
            else:
                logger.info("📊 Inicializando nuevo sistema de leaderboard")
                self.current_week = self.get_current_week()
                self.weekly_data = {}
                self.all_time_data = {}
                self.save_leaderboard_data()
        except Exception as e:
            logger.error(f"❌ Error cargando datos de leaderboard: {e}")
            self.current_week = self.get_current_week()
            self.weekly_data = {}
            self.all_time_data = {}

    def save_leaderboard_data(self):
        """Guardar datos del leaderboard"""
        try:
            data = {
                'current_week': self.current_week,
                'weekly_data': self.weekly_data,
                'all_time_data': self.all_time_data,
                'last_updated': datetime.now().isoformat(),
                'total_users_tracked': len(self.all_time_data)
            }
            with open(self.leaderboard_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Datos de leaderboard guardados exitosamente")
        except Exception as e:
            logger.error(f"❌ Error guardando datos de leaderboard: {e}")

    def get_current_week(self) -> str:
        """Obtener la semana actual en formato YYYY-WW"""
        now = datetime.now()
        year, week, _ = now.isocalendar()
        return f"{year}-W{week:02d}"

    def should_reset_weekly(self) -> bool:
        """Verificar si se debe reiniciar la semana"""
        current_week = self.get_current_week()
        return current_week != self.current_week

    def reset_weekly_data(self):
        """Reiniciar datos de la semana"""
        logger.info(f"🔄 Reiniciando leaderboard semanal - Nueva semana: {self.get_current_week()}")
        self.current_week = self.get_current_week()
        self.weekly_data = {}
        self.save_leaderboard_data()

    def load_user_servers_count(self) -> Dict[str, int]:
        """Cargar conteo de servidores de usuarios desde user_game_servers.json SIN LÍMITE"""
        try:
            if not Path(self.user_game_servers_file).exists():
                logger.warning(f"⚠️ Archivo {self.user_game_servers_file} no encontrado")
                return {}

            with open(self.user_game_servers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            user_servers = data.get('user_servers', {})
            servers_count = {}

            for user_id, servers_list in user_servers.items():
                if isinstance(servers_list, list):
                    # IMPORTANTE: No aplicar límite de 5 servidores aquí
                    servers_count[user_id] = len(servers_list)
                    logger.debug(f"👤 Usuario {user_id}: {len(servers_list)} servidores (sin límite)")
                else:
                    logger.warning(f"⚠️ Formato inválido para usuario {user_id}: {type(servers_list)}")
                    servers_count[user_id] = 0

            logger.info(f"📊 Cargados datos de {len(servers_count)} usuarios desde {self.user_game_servers_file}")
            total_servers = sum(servers_count.values())
            logger.info(f"🖥️ Total de servidores en leaderboard: {total_servers} (sin límites)")
            
            return servers_count

        except Exception as e:
            logger.error(f"❌ Error cargando datos de servidores: {e}")
            return {}

    def update_leaderboard_data(self):
        """Actualizar datos del leaderboard"""
        # Verificar si es una nueva semana
        if self.should_reset_weekly():
            self.reset_weekly_data()

        # Cargar datos actuales de servidores
        current_servers = self.load_user_servers_count()

        # Actualizar datos semanales
        self.weekly_data = current_servers.copy()

        # Actualizar datos all-time (máximo histórico por usuario)
        for user_id, server_count in current_servers.items():
            if user_id not in self.all_time_data:
                self.all_time_data[user_id] = server_count
            else:
                # Mantener el máximo histórico
                self.all_time_data[user_id] = max(self.all_time_data[user_id], server_count)

        self.save_leaderboard_data()
        logger.info(f"🔄 Leaderboard actualizado - Semana: {self.current_week}")

    def get_top_users(self, data_type: str = "weekly", limit: int = 10) -> List[Tuple[str, int]]:
        """Obtener top usuarios ordenados por servidores"""
        if data_type == "weekly":
            data = self.weekly_data
        elif data_type == "all_time":
            data = self.all_time_data
        else:
            data = self.weekly_data

        # Ordenar por número de servidores (descendente) y luego por user_id (para consistencia)
        sorted_users = sorted(data.items(), key=lambda x: (-x[1], x[0]))
        return sorted_users[:limit]

    def get_user_rank(self, user_id: str, data_type: str = "weekly") -> Tuple[int, int]:
        """Obtener rango de un usuario específico"""
        if data_type == "weekly":
            data = self.weekly_data
        elif data_type == "all_time":
            data = self.all_time_data
        else:
            data = self.weekly_data

        if user_id not in data:
            return 0, 0  # No clasificado

        user_servers = data[user_id]
        sorted_users = sorted(data.items(), key=lambda x: (-x[1], x[0]))

        for rank, (uid, servers) in enumerate(sorted_users, 1):
            if uid == user_id:
                return rank, user_servers

        return 0, 0

    def get_week_info(self) -> Dict[str, str]:
        """Obtener información de la semana actual"""
        try:
            year, week_num = self.current_week.split('-W')
            
            # Calcular fechas de inicio y fin de la semana
            year = int(year)
            week_num = int(week_num)
            
            # Primer día de la semana (lunes)
            jan_1 = datetime(year, 1, 1)
            week_start = jan_1 + timedelta(weeks=week_num - 1)
            week_start = week_start - timedelta(days=week_start.weekday())
            
            # Último día de la semana (domingo)
            week_end = week_start + timedelta(days=6)
            
            # Próximo reinicio (lunes siguiente)
            next_reset = week_end + timedelta(days=1)
            
            return {
                'week_number': self.current_week,
                'start_date': week_start.strftime('%d/%m/%Y'),
                'end_date': week_end.strftime('%d/%m/%Y'),
                'next_reset': next_reset.strftime('%d/%m/%Y'),
                'days_remaining': (next_reset - datetime.now()).days
            }
        except Exception as e:
            logger.error(f"Error calculando información de semana: {e}")
            return {
                'week_number': self.current_week,
                'start_date': 'N/A',
                'end_date': 'N/A',
                'next_reset': 'N/A',
                'days_remaining': 0
            }

def setup_leaderboard_commands(bot):
    """Configurar comandos de leaderboard en el bot"""
    
    leaderboard_system = LeaderboardSystem()
    
    @bot.tree.command(name="leaderboard", description="Ver el top 10 de usuarios con más servidores VIP")
    async def leaderboard_command(interaction: discord.Interaction, tipo: str = "semanal"):
        """Mostrar leaderboard de usuarios con más servidores"""
        try:
            # Verificar tipo válido
            valid_types = ["semanal", "historico", "weekly", "all_time"]
            if tipo.lower() not in valid_types:
                embed = discord.Embed(
                    title="❌ Tipo Inválido",
                    description=f"Tipo debe ser: `semanal` o `historico`",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            await interaction.response.defer()

            # Actualizar datos del leaderboard
            leaderboard_system.update_leaderboard_data()

            # Determinar tipo de datos
            data_type = "weekly" if tipo.lower() in ["semanal", "weekly"] else "all_time"
            display_type = "Semanal" if data_type == "weekly" else "Histórico"

            # Obtener top 10
            top_users = leaderboard_system.get_top_users(data_type, 10)

            if not top_users:
                embed = discord.Embed(
                    title="📊 Leaderboard Vacío",
                    description="No hay datos disponibles en el leaderboard.",
                    color=0xffaa00
                )
                await interaction.followup.send(embed=embed)
                return

            # Crear embed principal
            embed = discord.Embed(
                title=f"🏆 Leaderboard {display_type} - Top 10 Servidores",
                description="Ranking de usuarios con más servidores VIP acumulados",
                color=0x00ff88
            )

            # Obtener información del usuario que ejecuta el comando
            user_id = str(interaction.user.id)
            user_rank, user_servers = leaderboard_system.get_user_rank(user_id, data_type)

            # Agregar información de la semana si es semanal
            if data_type == "weekly":
                week_info = leaderboard_system.get_week_info()
                embed.add_field(
                    name="📅 Semana Actual",
                    value=f"**{week_info['week_number']}**\n{week_info['start_date']} - {week_info['end_date']}",
                    inline=True
                )
                embed.add_field(
                    name="🔄 Próximo Reinicio",
                    value=f"**{week_info['next_reset']}**\n({week_info['days_remaining']} días restantes)",
                    inline=True
                )
                embed.add_field(
                    name="📊 Tipo",
                    value="**Semanal**\n(Se reinicia cada lunes)",
                    inline=True
                )

            # Crear ranking
            ranking_text = []
            medal_emojis = ["🥇", "🥈", "🥉"]
            
            for i, (uid, server_count) in enumerate(top_users, 1):
                try:
                    # Intentar obtener el usuario de Discord
                    try:
                        discord_user = bot.get_user(int(uid))
                        if discord_user:
                            username = discord_user.display_name
                        else:
                            discord_user = await bot.fetch_user(int(uid))
                            username = discord_user.display_name if discord_user else f"Usuario {uid[:8]}"
                    except:
                        username = f"Usuario {uid[:8]}"

                    # Emoji de posición
                    if i <= 3:
                        position_emoji = medal_emojis[i-1]
                    else:
                        position_emoji = f"**{i}.**"

                    # Texto del ranking
                    ranking_text.append(f"{position_emoji} **{username}** - {server_count:,} servidores")

                except Exception as e:
                    logger.error(f"Error procesando usuario {uid}: {e}")
                    ranking_text.append(f"**{i}.** Usuario {uid[:8]} - {server_count:,} servidores")

            # Agregar ranking al embed
            embed.add_field(
                name=f"🏆 Top 10 {display_type}",
                value="\n".join(ranking_text),
                inline=False
            )

            # Agregar posición del usuario actual
            if user_rank > 0:
                embed.add_field(
                    name="📍 Tu Posición",
                    value=f"**#{user_rank}** con {user_servers:,} servidores",
                    inline=True
                )
            else:
                embed.add_field(
                    name="📍 Tu Posición",
                    value="No clasificado (0 servidores)",
                    inline=True
                )

            # Estadísticas adicionales
            total_users = len(leaderboard_system.weekly_data if data_type == "weekly" else leaderboard_system.all_time_data)
            total_servers = sum((leaderboard_system.weekly_data if data_type == "weekly" else leaderboard_system.all_time_data).values())
            
            embed.add_field(
                name="📊 Estadísticas Generales",
                value=f"**👥 Usuarios totales:** {total_users:,}\n**🖥️ Servidores totales:** {total_servers:,}",
                inline=True
            )

            # Footer y timestamp
            embed.set_footer(
                text=f"Leaderboard {display_type} • Datos sin límite de servidores • Actualizado automáticamente",
                icon_url="https://cdn.discordapp.com/attachments/123456789/roblox_logo.png"
            )
            embed.timestamp = datetime.now()

            await interaction.followup.send(embed=embed)

            # Log del uso
            logger.info(f"Usuario {interaction.user.name} (ID: {user_id}) usó /leaderboard tipo: {tipo}")

        except Exception as e:
            logger.error(f"Error en comando leaderboard: {e}")
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al generar el leaderboard.",
                color=0xff0000
            )
            error_embed.add_field(
                name="💡 Sugerencia",
                value="Intenta nuevamente en unos momentos",
                inline=False
            )
            
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)

    logger.info("🏆 Sistema de leaderboard configurado exitosamente")
    return leaderboard_system
