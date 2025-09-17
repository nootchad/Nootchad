
"""
Comandos para obtener información de badges de juegos de Roblox
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Configurar comandos de badges de juegos"""
    
    # Crear grupo de comandos para /game
    game_group = discord.app_commands.Group(name="game", description="Comandos relacionados con juegos de Roblox")
    
    # Crear subgrupo para /game badge
    badge_group = discord.app_commands.Group(name="badge", description="Comandos relacionados con badges de juegos", parent=game_group)
    
    @badge_group.command(name="checklist", description="Check how many badges a game has and how many more a user needs")
    async def badge_checklist_command(
        interaction: discord.Interaction,
        id: str,
        user: str = None
    ):
        """
        Verificar badges de un juego y progreso del usuario
        
        Args:
            id: Game ID (requerido)
            user: User Name or User ID (opcional)
        """
        from main import check_verification
        
        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Validar Game ID
            if not id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Juego Inválido",
                    description="El ID del juego debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            game_id = id
            
            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🔍 Obteniendo Información de Badges...",
                description=f"Consultando badges del juego ID: `{game_id}`",
                color=0xffaa00
            )
            if user:
                initial_embed.add_field(name="👤 Usuario", value=f"`{user}`", inline=True)
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Obtener información del juego
            game_info = await get_game_info(game_id)
            if not game_info:
                error_embed = discord.Embed(
                    title="❌ Juego No Encontrado",
                    description=f"No se pudo encontrar información para el juego ID: `{game_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Obtener badges del juego
            badges = await get_game_badges(game_id)
            if not badges:
                no_badges_embed = discord.Embed(
                    title="🏆 Sin Badges",
                    description=f"**{game_info.get('name', 'Juego desconocido')}** no tiene badges disponibles.",
                    color=0xffaa00
                )
                no_badges_embed.add_field(name="🎮 Juego", value=game_info.get('name', 'Desconocido'), inline=True)
                no_badges_embed.add_field(name="🆔 ID", value=f"`{game_id}`", inline=True)
                await message.edit(embed=no_badges_embed)
                return
            
            user_badges = []
            user_info = None
            
            # Si se proporcionó un usuario, obtener sus badges
            if user:
                user_info = await get_user_info(user)
                if user_info:
                    user_badges = await get_user_badges(user_info['id'], [badge['id'] for badge in badges])
                else:
                    # Usuario no encontrado, continuar sin información de usuario
                    pass
            
            # Crear embed con información completa
            result_embed = discord.Embed(
                title="🏆 Checklist de Badges",
                description=f"**{game_info.get('name', 'Juego desconocido')}**",
                color=0x00ff88
            )
            
            # Información del juego
            result_embed.add_field(
                name="🎮 Información del Juego",
                value=f"**Nombre:** {game_info.get('name', 'Desconocido')}\n**ID:** `{game_id}`\n**Total Badges:** {len(badges)}",
                inline=False
            )
            
            # Información del usuario si está disponible
            if user_info and user:
                earned_count = len(user_badges)
                remaining_count = len(badges) - earned_count
                progress_percentage = (earned_count / len(badges)) * 100 if badges else 0
                
                result_embed.add_field(
                    name="👤 Progreso del Usuario",
                    value=f"**Usuario:** {user_info.get('displayName', user_info.get('name', user))}\n**Badges Obtenidos:** {earned_count}/{len(badges)} ({progress_percentage:.1f}%)\n**Badges Restantes:** {remaining_count}",
                    inline=False
                )
                
                # Crear barra de progreso visual
                progress_bar = create_progress_bar(progress_percentage)
                result_embed.add_field(
                    name="📊 Progreso Visual",
                    value=f"{progress_bar} {progress_percentage:.1f}%",
                    inline=False
                )
            elif user:
                result_embed.add_field(
                    name="⚠️ Usuario No Encontrado",
                    value=f"No se pudo encontrar el usuario: `{user}`",
                    inline=False
                )
            
            # Lista de badges (mostrar hasta 10)
            badges_text = ""
            user_badge_ids = [badge['id'] for badge in user_badges] if user_badges else []
            
            for i, badge in enumerate(badges[:10], 1):
                status = "✅" if badge['id'] in user_badge_ids else "❌"
                badge_name = badge.get('name', 'Badge desconocido')
                badges_text += f"{status} **{badge_name}**\n"
                
                # Mostrar descripción solo para badges no obtenidos (si hay espacio)
                if badge['id'] not in user_badge_ids and len(badges_text) < 800:
                    description = badge.get('description', '')
                    if description:
                        badges_text += f"   _{description[:50]}{'...' if len(description) > 50 else ''}_\n"
            
            if len(badges) > 10:
                badges_text += f"\n... y {len(badges) - 10} badges más"
            
            result_embed.add_field(
                name="🏅 Lista de Badges",
                value=badges_text if badges_text else "No hay badges disponibles",
                inline=False
            )
            
            # Agregar thumbnail del juego si está disponible
            if game_info.get('thumbnails'):
                result_embed.set_thumbnail(url=game_info['thumbnails'][0]['imageUrl'])
            
            result_embed.set_footer(text=f"Consultado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            logger.error(f"Error en comando badge checklist: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al consultar los badges. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @badge_group.command(name="image", description="Get the icon of a badge")
    async def badge_image_command(
        interaction: discord.Interaction,
        id: str
    ):
        """
        Obtener la imagen/icono de un badge
        
        Args:
            id: Badge ID (requerido)
        """
        from main import check_verification
        
        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Validar Badge ID
            if not id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Badge Inválido",
                    description="El ID del badge debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            badge_id = id
            
            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🔍 Obteniendo Imagen del Badge...",
                description=f"Consultando badge ID: `{badge_id}`",
                color=0xffaa00
            )
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Obtener información del badge
            badge_info = await get_badge_info(badge_id)
            if not badge_info:
                error_embed = discord.Embed(
                    title="❌ Badge No Encontrado",
                    description=f"No se pudo encontrar información para el badge ID: `{badge_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Crear embed con la imagen del badge
            result_embed = discord.Embed(
                title="🏆 Imagen del Badge",
                description=f"**{badge_info.get('name', 'Badge desconocido')}**",
                color=0x00ff88
            )
            
            # Información del badge
            result_embed.add_field(
                name="🏅 Información",
                value=f"**Nombre:** {badge_info.get('name', 'Desconocido')}\n**ID:** `{badge_id}`\n**Descripción:** {badge_info.get('description', 'Sin descripción')[:100]}{'...' if len(badge_info.get('description', '')) > 100 else ''}",
                inline=False
            )
            
            # Información del juego asociado
            if badge_info.get('awardingUniverse'):
                universe_info = badge_info['awardingUniverse']
                result_embed.add_field(
                    name="🎮 Juego Asociado",
                    value=f"**Nombre:** {universe_info.get('name', 'Desconocido')}\n**ID:** `{universe_info.get('id', 'Desconocido')}`",
                    inline=False
                )
            
            # Estadísticas del badge
            if badge_info.get('statistics'):
                stats = badge_info['statistics']
                result_embed.add_field(
                    name="📊 Estadísticas",
                    value=f"**Otorgados:** {stats.get('awardedCount', 0):,}\n**Porcentaje de Ganancia:** {stats.get('winRatePercentage', 0):.2f}%",
                    inline=True
                )
            
            # Configurar la imagen del badge
            if badge_info.get('iconImageId'):
                # URL de la imagen del badge en alta resolución
                image_url = f"https://thumbnails.roblox.com/v1/badges/icons?badgeIds={badge_id}&size=150x150&format=Png&isCircular=false"
                result_embed.set_image(url=image_url)
            
            # Thumbnail más pequeño
            if badge_info.get('iconImageId'):
                thumbnail_url = f"https://thumbnails.roblox.com/v1/badges/icons?badgeIds={badge_id}&size=50x50&format=Png&isCircular=false"
                result_embed.set_thumbnail(url=thumbnail_url)
            
            result_embed.set_footer(text=f"Badge ID: {badge_id} • Consultado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            logger.error(f"Error en comando badge image: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al consultar la imagen del badge. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    # Registrar los grupos de comandos
    bot.tree.add_command(game_group)
    
    logger.info("✅ Comandos de badges de juegos configurados")
    return True

async def get_game_info(game_id: str) -> dict:
    """Obtener información del juego"""
    try:
        async with aiohttp.ClientSession() as session:
            # Primero obtener el universe ID del place ID
            places_url = f"https://games.roblox.com/v1/games/multiget-place-details"
            places_payload = {"placeIds": [int(game_id)]}
            
            async with session.post(places_url, json=places_payload) as response:
                if response.status == 200:
                    places_data = await response.json()
                    if places_data and len(places_data) > 0:
                        place_info = places_data[0]
                        universe_id = place_info.get('universeId')
                        
                        if universe_id:
                            # Obtener información detallada del universo
                            universe_url = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
                            async with session.get(universe_url) as universe_response:
                                if universe_response.status == 200:
                                    universe_data = await universe_response.json()
                                    if universe_data.get('data') and len(universe_data['data']) > 0:
                                        game_data = universe_data['data'][0]
                                        
                                        # Obtener thumbnails
                                        thumbnails_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={universe_id}&returnPolicy=PlaceHolder&size=256x256&format=Png&isCircular=false"
                                        async with session.get(thumbnails_url) as thumb_response:
                                            thumbnails = []
                                            if thumb_response.status == 200:
                                                thumb_data = await thumb_response.json()
                                                thumbnails = thumb_data.get('data', [])
                                        
                                        return {
                                            'id': universe_id,
                                            'placeId': game_id,
                                            'name': game_data.get('name'),
                                            'description': game_data.get('description'),
                                            'thumbnails': thumbnails
                                        }
        return None
    except Exception as e:
        logger.error(f"Error obteniendo información del juego {game_id}: {e}")
        return None

async def get_game_badges(game_id: str) -> list:
    """Obtener badges de un juego"""
    try:
        async with aiohttp.ClientSession() as session:
            # Primero obtener el universe ID
            places_url = f"https://games.roblox.com/v1/games/multiget-place-details"
            places_payload = {"placeIds": [int(game_id)]}
            
            async with session.post(places_url, json=places_payload) as response:
                if response.status == 200:
                    places_data = await response.json()
                    if places_data and len(places_data) > 0:
                        universe_id = places_data[0].get('universeId')
                        
                        if universe_id:
                            # Obtener badges del universo
                            badges_url = f"https://badges.roblox.com/v1/universes/{universe_id}/badges"
                            params = {
                                'limit': 100,  # Máximo permitido
                                'sortOrder': 'Asc'
                            }
                            
                            all_badges = []
                            cursor = None
                            
                            while True:
                                if cursor:
                                    params['cursor'] = cursor
                                
                                async with session.get(badges_url, params=params) as badges_response:
                                    if badges_response.status == 200:
                                        badges_data = await badges_response.json()
                                        badges = badges_data.get('data', [])
                                        all_badges.extend(badges)
                                        
                                        # Verificar si hay más páginas
                                        cursor = badges_data.get('nextPageCursor')
                                        if not cursor:
                                            break
                                    else:
                                        break
                            
                            return all_badges
        return []
    except Exception as e:
        logger.error(f"Error obteniendo badges del juego {game_id}: {e}")
        return []

async def get_user_info(user_identifier: str) -> dict:
    """Obtener información del usuario por nombre o ID"""
    try:
        async with aiohttp.ClientSession() as session:
            # Intentar primero como ID de usuario
            if user_identifier.isdigit():
                user_url = f"https://users.roblox.com/v1/users/{user_identifier}"
                async with session.get(user_url) as response:
                    if response.status == 200:
                        return await response.json()
            
            # Intentar como nombre de usuario
            users_url = "https://users.roblox.com/v1/usernames/users"
            payload = {
                "usernames": [user_identifier],
                "excludeBannedUsers": True
            }
            
            async with session.post(users_url, json=payload) as response:
                if response.status == 200:
                    users_data = await response.json()
                    if users_data.get('data') and len(users_data['data']) > 0:
                        return users_data['data'][0]
        
        return None
    except Exception as e:
        logger.error(f"Error obteniendo información del usuario {user_identifier}: {e}")
        return None

async def get_user_badges(user_id: int, badge_ids: list) -> list:
    """Obtener badges que el usuario ha obtenido de una lista específica"""
    try:
        if not badge_ids:
            return []
        
        async with aiohttp.ClientSession() as session:
            # Dividir en chunks de 100 badges (límite de la API)
            user_badges = []
            chunk_size = 100
            
            for i in range(0, len(badge_ids), chunk_size):
                chunk = badge_ids[i:i + chunk_size]
                badge_ids_str = ','.join(map(str, chunk))
                
                url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates"
                params = {'badgeIds': badge_ids_str}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_badges.extend(data.get('data', []))
                    
                # Pequeña pausa entre requests
                await asyncio.sleep(0.1)
            
            return user_badges
    except Exception as e:
        logger.error(f"Error obteniendo badges del usuario {user_id}: {e}")
        return []

async def get_badge_info(badge_id: str) -> dict:
    """Obtener información detallada de un badge"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://badges.roblox.com/v1/badges/{badge_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        return None
    except Exception as e:
        logger.error(f"Error obteniendo información del badge {badge_id}: {e}")
        return None

def create_progress_bar(percentage: float, length: int = 10) -> str:
    """Crear una barra de progreso visual"""
    filled = int((percentage / 100) * length)
    empty = length - filled
    return "█" * filled + "░" * empty
