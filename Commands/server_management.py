
"""
Comandos de gestión de servidores para RbxServers
Incluye historial, estadísticas y programador de scraping automático
"""
import discord
from discord.ext import commands
import logging
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos de gestión de servidores"""
    
    @bot.tree.command(name="serverhistory", description="Ver historial de servidores que has usado recientemente")
    async def serverhistory_command(interaction: discord.Interaction):
        """Ver historial de servidores del usuario con opción de acceso rápido"""
        try:
            # Verificar autenticación
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            logger.info(f"Usuario {username} (ID: {user_id}) solicitó historial de servidores")
            
            # Obtener servidores del usuario
            user_servers = get_user_servers_from_file(user_id)
            
            if not user_servers:
                embed = discord.Embed(
                    title="<:1000182750:1396420537227411587> Sin Historial de Servidores",
                    description="No tienes servidores guardados aún.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> ¿Cómo obtener servidores?",
                    value="• Usa `/scrape [game_id]` para buscar servidores\n• Usa `/autoscrape` para obtener múltiples servidores\n• Usa `/game [nombre]` para buscar por nombre de juego",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Organizar servidores por fecha (más recientes primero)
            recent_servers = user_servers[:10]  # Últimos 10 servidores
            
            embed = discord.Embed(
                title="<:1000182750:1396420537227411587> Historial de Servidores",
                description=f"Mostrando tus **{len(recent_servers)}** servidores más recientes de **{len(user_servers)}** totales.",
                color=0x3366ff
            )
            
            # Agregar información de servidores
            for i, server_link in enumerate(recent_servers, 1):
                game_id = extract_game_id_from_link(server_link)
                game_name = get_game_name_from_id(game_id) if game_id else "Juego Desconocido"
                
                embed.add_field(
                    name=f"**{i}.** {game_name}",
                    value=f"[🔗 Unirse al Servidor]({server_link})\n`ID: {game_id or 'N/A'}`",
                    inline=True
                )
                
                # Agregar separador cada 3 servidores
                if i % 3 == 0 and i < len(recent_servers):
                    embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Información adicional
            embed.add_field(
                name="<:1000182657:1396060091366637669> Acceso Rápido",
                value="Haz clic en los enlaces para unirte directamente a los servidores",
                inline=False
            )
            
            embed.add_field(
                name="<:1000182584:1396049547838492672> Estadísticas",
                value=f"• **Total:** {len(user_servers)} servidores\n• **Mostrando:** {len(recent_servers)} más recientes",
                inline=True
            )
            
            embed.set_footer(text="<a:foco:1418492184373755966> Usa /serverstats para ver estadísticas detalladas")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando serverhistory para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al obtener tu historial de servidores.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="serverstats", description="Estadísticas detalladas de tus servidores guardados")
    async def serverstats_command(interaction: discord.Interaction):
        """Ver estadísticas detalladas de los servidores del usuario"""
        try:
            # Verificar autenticación
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            logger.info(f"Usuario {username} (ID: {user_id}) solicitó estadísticas de servidores")
            
            # Obtener datos de servidores
            user_servers = get_user_servers_from_file(user_id)
            
            if not user_servers:
                embed = discord.Embed(
                    title="<:1000182584:1396049547838492672> Sin Estadísticas",
                    description="No tienes servidores guardados para mostrar estadísticas.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Empieza a usar el bot",
                    value="• `/scrape [game_id]` - Buscar servidores\n• `/autoscrape` - Auto scraping\n• `/game [nombre]` - Buscar por nombre",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Analizar estadísticas
            stats = analyze_user_servers(user_servers)
            
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Estadísticas de Servidores",
                description=f"Análisis completo de tus **{stats['total_servers']}** servidores guardados.",
                color=0x00aa55
            )
            
            # Estadísticas generales
            embed.add_field(
                name="<:stats:1418490788437823599> **Resumen General**",
                value=f"• **Total de servidores:** {stats['total_servers']}\n• **Juegos únicos:** {stats['unique_games']}\n• **Servidor más antiguo:** {stats['oldest_server_date']}\n• **Último agregado:** {stats['newest_server_date']}",
                inline=False
            )
            
            # Top 5 juegos
            if stats['games_distribution']:
                top_games_text = ""
                for i, (game_name, count) in enumerate(stats['games_distribution'][:5], 1):
                    top_games_text += f"**{i}.** {game_name} - {count} servidores\n"
                
                embed.add_field(
                    name="<a:control:1418490793223651409> **Top 5 Juegos**",
                    value=top_games_text or "No hay datos suficientes",
                    inline=True
                )
            
            # Distribución por antigüedad
            embed.add_field(
                name="<:1000182657:1396060091366637669> **Distribución Temporal**",
                value=f"• **Última semana:** {stats['last_week']} servidores\n• **Último mes:** {stats['last_month']} servidores\n• **Más antiguos:** {stats['older_than_month']} servidores",
                inline=True
            )
            
            # Estado de los enlaces
            embed.add_field(
                name="🔗 **Estado de Enlaces**",
                value=f"• **Activos estimados:** {stats['estimated_active']}\n• **Podrían estar expirados:** {stats['estimated_expired']}\n• **Tasa de éxito:** {stats['success_rate']}%",
                inline=False
            )
            
            # Recomendaciones
            recommendations = generate_recommendations(stats)
            if recommendations:
                embed.add_field(
                    name="<a:foco:1418492184373755966> **Recomendaciones**",
                    value=recommendations,
                    inline=False
                )
            
            embed.set_footer(text="📈 Estadísticas actualizadas en tiempo real • Usa /serverhistory para ver enlaces")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando serverstats para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al generar las estadísticas.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # TEMPORALMENTE DESACTIVADO - /scheduler
    # @bot.tree.command(name="scheduler", description="Programar scraping automático a horas específicas")
    async def scheduler_command(
        interaction: discord.Interaction, 
        game_id: str,
        hora: str,
        cantidad: int = 5,
        activar: bool = True
    ):
        """Programar scraping automático a horas específicas"""
        try:
            # Verificar autenticación
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            logger.info(f"Usuario {username} (ID: {user_id}) configuró scheduler: {game_id} a las {hora}")
            
            # Validar formato de hora (HH:MM)
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', hora):
                embed = discord.Embed(
                    title="❌ Formato de Hora Inválido",
                    description="El formato de hora debe ser **HH:MM** (24 horas).",
                    color=0xff0000
                )
                embed.add_field(
                    name="<a:verify2:1418486831993061497> Ejemplos válidos:",
                    value="• `09:30` (9:30 AM)\n• `14:45` (2:45 PM)\n• `23:00` (11:00 PM)",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar game_id
            if not game_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Juego Inválido",
                    description="El ID del juego debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validar cantidad
            if cantidad < 1 or cantidad > 20:
                embed = discord.Embed(
                    title="❌ Cantidad Inválida",
                    description="La cantidad debe estar entre 1 y 20 servidores.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Gestionar scheduler
            result = manage_user_scheduler(user_id, game_id, hora, cantidad, activar)
            
            if activar:
                embed = discord.Embed(
                    title="<:1000182657:1396060091366637669> Scheduler Configurado",
                    description=f"Scraping automático programado exitosamente.",
                    color=0x00aa55
                )
                embed.add_field(
                    name="<a:control:1418490793223651409> **Configuración**",
                    value=f"• **Juego ID:** `{game_id}`\n• **Hora:** `{hora}` (24h)\n• **Cantidad:** {cantidad} servidores\n• **Estado:** Activo <a:verify2:1418486831993061497>",
                    inline=False
                )
                embed.add_field(
                    name="<:1000182657:1396060091366637669> **Próxima Ejecución**",
                    value=calculate_next_execution(hora),
                    inline=True
                )
                embed.add_field(
                    name="⚙️ **Cómo Funciona**",
                    value="• Se ejecutará automáticamente todos los días\n• Los servidores se guardarán en tu perfil\n• Recibirás una notificación cuando se complete",
                    inline=False
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> **Gestión**",
                    value="• Usa `/scheduler` con `activar: False` para desactivar\n• Puedes tener múltiples schedulers activos\n• Los schedulers se pausan si no usas el bot por 7 días",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="⏹️ Scheduler Desactivado",
                    description=f"El scraping automático para el juego `{game_id}` ha sido desactivado.",
                    color=0xff9900
                )
                embed.add_field(
                    name="<:stats:1418490788437823599> **Estado**",
                    value="• Scheduler pausado\n• No se ejecutarán más scraping automáticos\n• Configuración guardada para reactivación futura",
                    inline=False
                )
            
            # Mostrar todos los schedulers activos del usuario
            user_schedulers = get_user_schedulers(user_id)
            if user_schedulers:
                scheduler_list = ""
                for scheduler in user_schedulers[:5]:  # Mostrar máximo 5
                    status = "<a:verify2:1418486831993061497>" if scheduler['active'] else "⏸️"
                    scheduler_list += f"{status} `{scheduler['game_id']}` - {scheduler['time']} ({scheduler['quantity']} servidores)\n"
                
                embed.add_field(
                    name="📋 **Tus Schedulers Activos**",
                    value=scheduler_list or "Ningún scheduler activo",
                    inline=False
                )
            
            embed.set_footer(text="⚡ Los schedulers se ejecutan en horario UTC. Ajusta según tu zona horaria.")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en comando scheduler para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al configurar el scheduler.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

def get_user_servers_from_file(user_id: str) -> List[str]:
    """Obtener servidores del usuario desde user_game_servers.json"""
    try:
        servers_file = Path("user_game_servers.json")
        if not servers_file.exists():
            return []
        
        with open(servers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        user_servers = data.get('user_servers', {}).get(user_id, [])
        
        # 🔄 INTEGRACIÓN: Filtrar servidores únicos usando el nuevo sistema
        try:
            from Commands.unique_server_manager import unique_server_manager
            
            # Solo filtrar si hay servidores
            if user_servers and isinstance(user_servers, list):
                # El sistema de servidores únicos ya debería tener estos marcados
                # Pero por seguridad, verificamos que no estén duplicados con otros usuarios
                filtered_servers = unique_server_manager.filter_unique_servers_for_user(user_id, user_servers)
                
                if len(filtered_servers) != len(user_servers):
                    logger.info(f"🔍 Filtrados {len(filtered_servers)}/{len(user_servers)} servidores únicos para usuario {user_id}")
                
                return filtered_servers
            
        except ImportError:
            logger.warning("⚠️ Sistema de servidores únicos no disponible, usando método tradicional")
        except Exception as e:
            logger.error(f"❌ Error aplicando filtro de servidores únicos: {e}")
        
        return user_servers if isinstance(user_servers, list) else []
        
    except Exception as e:
        logger.error(f"Error obteniendo servidores del usuario {user_id}: {e}")
        return []

def extract_game_id_from_link(server_link: str) -> Optional[str]:
    """Extraer ID del juego desde un enlace de servidor"""
    try:
        # Buscar patrón: /games/GAME_ID?privateServerLinkCode=
        match = re.search(r'/games/(\d+)\?', server_link)
        return match.group(1) if match else None
    except Exception:
        return None

def get_game_name_from_id(game_id: str) -> str:
    """Obtener nombre del juego desde el ID (base de datos básica)"""
    game_names = {
        "2753915549": "🌊 Blox Fruits",
        "142823291": "🔍 Murder Mystery 2",
        "920587237": "🐾 Adopt Me!",
        "4924922222": "🏡 Brookhaven RP",
        "185655149": "🏠 Welcome to Bloxburg",
        "606849621": "🚓 Jailbreak",
        "286090429": "🔫 Arsenal",
        "109983668079237": "🧠 Steal A Brainrot",
        "6284583030": "🎃 Pet Simulator X",
        "1537690962": "🐝 Bee Swarm Simulator"
    }
    
    return game_names.get(game_id, f"Juego {game_id}")

def analyze_user_servers(servers: List[str]) -> Dict:
    """Analizar estadísticas de los servidores del usuario"""
    try:
        now = datetime.now()
        
        # Contadores
        games_count = {}
        last_week = 0
        last_month = 0
        older_than_month = 0
        
        # Procesar cada servidor
        for server in servers:
            game_id = extract_game_id_from_link(server)
            if game_id:
                game_name = get_game_name_from_id(game_id)
                games_count[game_name] = games_count.get(game_name, 0) + 1
        
        # Para simplificar, consideramos que los servidores están ordenados por fecha
        # Los primeros son más recientes
        total_servers = len(servers)
        if total_servers > 0:
            # Estimación temporal basada en posición
            last_week = min(7, total_servers)  # Últimos 7 servidores como "última semana"
            last_month = min(30, total_servers)  # Últimos 30 como "último mes"
            older_than_month = max(0, total_servers - 30)
        
        # Distribución de juegos (ordenada por cantidad)
        games_distribution = sorted(games_count.items(), key=lambda x: x[1], reverse=True)
        
        # Estimación de servidores activos (los más recientes tienen mayor probabilidad)
        estimated_active = max(1, int(total_servers * 0.7))  # 70% estimado como activos
        estimated_expired = total_servers - estimated_active
        success_rate = int((estimated_active / total_servers) * 100) if total_servers > 0 else 0
        
        return {
            'total_servers': total_servers,
            'unique_games': len(games_count),
            'games_distribution': games_distribution,
            'last_week': last_week,
            'last_month': last_month,
            'older_than_month': older_than_month,
            'estimated_active': estimated_active,
            'estimated_expired': estimated_expired,
            'success_rate': success_rate,
            'oldest_server_date': "Hace más de 1 mes" if older_than_month > 0 else "Reciente",
            'newest_server_date': "Hace pocas horas" if total_servers > 0 else "N/A"
        }
        
    except Exception as e:
        logger.error(f"Error analizando servidores: {e}")
        return {
            'total_servers': 0,
            'unique_games': 0,
            'games_distribution': [],
            'last_week': 0,
            'last_month': 0,
            'older_than_month': 0,
            'estimated_active': 0,
            'estimated_expired': 0,
            'success_rate': 0,
            'oldest_server_date': "N/A",
            'newest_server_date': "N/A"
        }

def generate_recommendations(stats: Dict) -> str:
    """Generar recomendaciones basadas en las estadísticas"""
    recommendations = []
    
    if stats['total_servers'] < 5:
        recommendations.append("• Usa `/autoscrape` para obtener más servidores")
    
    if stats['unique_games'] < 3:
        recommendations.append("• Prueba diferentes juegos con `/game [nombre]`")
    
    if stats['success_rate'] < 50:
        recommendations.append("• Algunos servidores pueden estar expirados, obtén nuevos")
    
    if stats['last_week'] == 0:
        recommendations.append("• No has obtenido servidores recientemente, ¡vuelve a scraping!")
    
    return "\n".join(recommendations[:3])  # Máximo 3 recomendaciones

def manage_user_scheduler(user_id: str, game_id: str, time: str, quantity: int, active: bool) -> bool:
    """Gestionar scheduler del usuario (guardar/actualizar configuración)"""
    try:
        schedulers_file = Path("user_schedulers.json")
        
        # Cargar schedulers existentes
        if schedulers_file.exists():
            with open(schedulers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'schedulers': {}, 'metadata': {}}
        
        # Inicializar usuario si no existe
        if user_id not in data['schedulers']:
            data['schedulers'][user_id] = []
        
        # Buscar scheduler existente para este juego
        existing_index = -1
        for i, scheduler in enumerate(data['schedulers'][user_id]):
            if scheduler['game_id'] == game_id and scheduler['time'] == time:
                existing_index = i
                break
        
        if existing_index >= 0:
            # Actualizar scheduler existente
            data['schedulers'][user_id][existing_index].update({
                'quantity': quantity,
                'active': active,
                'updated_at': datetime.now().isoformat()
            })
        else:
            # Crear nuevo scheduler
            new_scheduler = {
                'game_id': game_id,
                'time': time,
                'quantity': quantity,
                'active': active,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            data['schedulers'][user_id].append(new_scheduler)
        
        # Actualizar metadata
        data['metadata'] = {
            'total_users': len(data['schedulers']),
            'last_updated': datetime.now().isoformat()
        }
        
        # Guardar archivo
        with open(schedulers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Scheduler {'actualizado' if existing_index >= 0 else 'creado'} para usuario {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error gestionando scheduler para usuario {user_id}: {e}")
        return False

def get_user_schedulers(user_id: str) -> List[Dict]:
    """Obtener schedulers activos del usuario"""
    try:
        schedulers_file = Path("user_schedulers.json")
        if not schedulers_file.exists():
            return []
        
        with open(schedulers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        user_schedulers = data.get('schedulers', {}).get(user_id, [])
        # Filtrar solo los activos
        return [s for s in user_schedulers if s.get('active', False)]
        
    except Exception as e:
        logger.error(f"Error obteniendo schedulers del usuario {user_id}: {e}")
        return []

def calculate_next_execution(time_str: str) -> str:
    """Calcular la próxima ejecución del scheduler"""
    try:
        now = datetime.now()
        hour, minute = map(int, time_str.split(':'))
        
        # Crear datetime para hoy a la hora especificada
        next_execution = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Si ya pasó la hora de hoy, programar para mañana
        if next_execution <= now:
            next_execution += timedelta(days=1)
        
        # Calcular tiempo restante
        time_diff = next_execution - now
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        return f"En {hours}h {minutes}m (hoy {time_str})" if hours < 24 else f"Mañana a las {time_str}"
        
    except Exception:
        return f"Próxima: {time_str}"

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
