"""
Comandos de usuarios de Roblox
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
import json
import zipfile
import io
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""

    # Crear grupo de comandos para /user
    user_group = discord.app_commands.Group(name="user", description="Comandos relacionados con usuarios de Roblox")

    @user_group.command(name="info", description="Muestra información de una cuenta de Roblox")
    async def user_info_command(interaction: discord.Interaction, username: str):
        """Mostrar información de usuario de Roblox"""
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            user_info = await get_user_by_username(username)
            if not user_info:
                embed = discord.Embed(title="❌ Usuario No Encontrado", color=0xff0000)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            user_id = user_info['id']
            detailed_info = await get_user_details(user_id)

            embed = discord.Embed(
                title="👤 Información de Usuario",
                description=f"**{user_info['displayName']} (@{user_info['name']})**",
                color=0x00ff88
            )

            embed.add_field(name="🆔 ID", value=f"`{user_id}`", inline=True)
            embed.add_field(name="📅 Creado", value=f"<t:{int(datetime.fromisoformat(detailed_info.get('created', '2006-01-01T00:00:00').replace('Z', '+00:00')).timestamp())}:F>", inline=True)
            embed.add_field(name="📝 Descripción", value=detailed_info.get('description', 'Sin descripción')[:200], inline=False)

            # Configurar avatar
            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png"
            embed.set_thumbnail(url=avatar_url)
            embed.set_footer(text=f"ID: {user_id} • RbxServers")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en user info: {e}")
            await interaction.followup.send("Error obteniendo información del usuario.", ephemeral=True)

    @user_group.command(name="has_badge", description="Verifica si un usuario tiene una insignia específica")
    async def user_has_badge_command(interaction: discord.Interaction, username: str, badge_id: str):
        """Verificar si usuario tiene badge específico"""
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            user_info = await get_user_by_username(username)
            if not user_info:
                embed = discord.Embed(title="❌ Usuario No Encontrado", color=0xff0000)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            has_badge = await check_user_has_badge(user_info['id'], badge_id)
            badge_info = await get_badge_info(badge_id)

            embed = discord.Embed(
                title="🏆 Verificación de Insignia",
                description=f"**Usuario:** {user_info['displayName']} (@{user_info['name']})",
                color=0x00ff88 if has_badge else 0xff9900
            )

            embed.add_field(
                name="🎖️ Insignia",
                value=f"**{badge_info.get('name', 'Insignia desconocida')}**\n`ID: {badge_id}`",
                inline=False
            )

            embed.add_field(
                name="✅ Resultado" if has_badge else "❌ Resultado",
                value="El usuario **SÍ tiene** esta insignia" if has_badge else "El usuario **NO tiene** esta insignia",
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error verificando badge: {e}")
            await interaction.followup.send("Error verificando insignia.", ephemeral=True)

    @user_group.command(name="avatar", description="Generar imagen del avatar actual de un usuario")
    async def user_avatar_command(interaction: discord.Interaction, username: str):
        """Generar imagen del avatar de usuario"""
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            user_info = await get_user_by_username(username)
            if not user_info:
                embed = discord.Embed(title="❌ Usuario No Encontrado", color=0xff0000)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            user_id = user_info['id']

            embed = discord.Embed(
                title="🖼️ Avatar de Usuario",
                description=f"**{user_info['displayName']} (@{user_info['name']})**",
                color=0x00ff88
            )

            # Configurar imagen del avatar (imagen principal grande)
            try:
                # Obtener la imagen del avatar en alta resolución
                avatar_image_url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=720x720&format=Png&isCircular=false"
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_image_url) as response:
                        if response.status == 200:
                            avatar_data = await response.json()
                            if avatar_data.get('data') and len(avatar_data['data']) > 0:
                                image_url = avatar_data['data'][0].get('imageUrl')
                                if image_url:
                                    embed.set_image(url=image_url)
                                    logger.info(f"✅ Imagen del avatar configurada: {image_url}")

                # Thumbnail más pequeño para la esquina
                thumbnail_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumbnail_url) as response:
                        if response.status == 200:
                            thumb_data = await response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                thumb_url = thumb_data['data'][0].get('imageUrl')
                                if thumb_url:
                                    embed.set_thumbnail(url=thumb_url)
            except Exception as e:
                logger.warning(f"⚠️ Error configurando imagen del avatar: {e}")

            embed.add_field(name="🆔 ID Usuario", value=f"`{user_id}`", inline=True)
            embed.add_field(name="🔗 Perfil", value=f"[Ver en Roblox](https://www.roblox.com/users/{user_id}/profile)", inline=True)

            embed.set_footer(text="RbxServers • Avatar Generator")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error generando avatar: {e}")
            await interaction.followup.send("Error generando imagen del avatar.", ephemeral=True)

    # Registrar el grupo de comandos
    bot.tree.add_command(user_group)

    logger.info("✅ Comandos de usuarios configurados exitosamente")
    return True

async def get_user_by_username(username: str):
    """Obtener información de usuario por nombre"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {"usernames": [username], "excludeBannedUsers": True}
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        return data["data"][0]
        return None
    except Exception as e:
        logger.error(f"Error obteniendo usuario: {e}")
        return None

async def get_user_details(user_id: int):
    """Obtener detalles adicionales del usuario"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://users.roblox.com/v1/users/{user_id}"
            headers = {"User-Agent": "Mozilla/5.0"}

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return {}
    except Exception as e:
        logger.error(f"Error obteniendo detalles: {e}")
        return {}

async def check_user_has_badge(user_id: int, badge_id: str):
    """Verificar si usuario tiene badge específico"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates?badgeIds={badge_id}"
            headers = {"User-Agent": "Mozilla/5.0"}

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return len(data.get("data", [])) > 0
        return False
    except Exception as e:
        logger.error(f"Error verificando badge: {e}")
        return False

async def get_badge_info(badge_id: str):
    """Obtener información del badge"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://badges.roblox.com/v1/badges/{badge_id}"
            headers = {"User-Agent": "Mozilla/5.0"}

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return {}
    except Exception as e:
        logger.error(f"Error obteniendo info del badge: {e}")
        return {}

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass