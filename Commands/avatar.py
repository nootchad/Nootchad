
"""
Comando /avatar para mostrar avatares de Roblox con información de objetos y precios
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="avatar", description="Ver el avatar de Roblox de un usuario y sus objetos")
    async def avatar_command(interaction: discord.Interaction, roblox_username: str):
        """Mostrar avatar de Roblox con información de objetos y precios"""
        try:
            # Verificar autenticación
            from main import check_verification
            if not await check_verification(interaction, defer_response=True):
                return
            
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            user_id = str(interaction.user.id)
            
            logger.info(f"🎭 Usuario {username} (ID: {user_id}) solicitó avatar de: {roblox_username}")
            
            # Obtener información del usuario de Roblox
            user_info = await get_roblox_user_info(roblox_username)
            
            if not user_info:
                embed = discord.Embed(
                    title="❌ Usuario No Encontrado",
                    description=f"No se pudo encontrar el usuario de Roblox: **{roblox_username}**",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="💡 Sugerencia",
                    value="• Verifica que el nombre de usuario esté escrito correctamente\n• Asegúrate de que el usuario existe en Roblox\n• Intenta con el nombre exacto (mayúsculas y minúsculas importan)",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Obtener información del avatar
            avatar_info = await get_avatar_info(user_info['id'])
            
            if not avatar_info:
                embed = discord.Embed(
                    title="❌ Error de Avatar",
                    description=f"No se pudo obtener la información del avatar de **{roblox_username}**",
                    color=0x5c5c5c
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed principal con información del avatar
            embed = discord.Embed(
                title=f"🎭 Avatar de {user_info['displayName']}",
                description=f"**Nombre de usuario:** {user_info['name']}\n**ID de usuario:** {user_info['id']}",
                color=0x6c6c6c
            )
            
            # Establecer la imagen del avatar en la esquina (thumbnail)
            if avatar_info.get('avatar_url'):
                embed.set_thumbnail(url=avatar_info['avatar_url'])
            
            # Información básica del usuario
            embed.add_field(
                name="👤 Información del Usuario",
                value=f"**Nombre:** {user_info['name']}\n**Nombre mostrado:** {user_info['displayName']}\n**Perfil:** [Ver en Roblox](https://www.roblox.com/users/{user_info['id']}/profile)",
                inline=True
            )
            
            # Información de la cuenta
            created_date = user_info.get('created', 'Fecha no disponible')
            if created_date != 'Fecha no disponible':
                try:
                    from datetime import datetime
                    created_dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    created_formatted = created_dt.strftime('%d/%m/%Y')
                except:
                    created_formatted = created_date
            else:
                created_formatted = created_date
            
            embed.add_field(
                name="📅 Información de la Cuenta",
                value=f"**Creada:** {created_formatted}\n**Descripción:** {user_info.get('description', 'Sin descripción')[:100]}{'...' if len(user_info.get('description', '')) > 100 else ''}",
                inline=True
            )
            
            # Objetos del avatar y precios
            avatar_items = avatar_info.get('items', [])
            if avatar_items:
                items_text = []
                total_robux = 0
                
                for item in avatar_items[:8]:  # Limitar a 8 objetos para no sobrecargar
                    item_name = item.get('name', 'Objeto desconocido')
                    item_price = item.get('price', 0)
                    item_type = item.get('type', 'Accesorio')
                    
                    # Emoji según el tipo de objeto
                    type_emoji = {
                        'Hat': '🎩',
                        'Shirt': '👕',
                        'Pants': '👖',
                        'Accessory': '🎭',
                        'Gear': '⚒️',
                        'Face': '😊',
                        'Hair': '💇',
                        'Package': '📦'
                    }.get(item_type, '🎯')
                    
                    if item_price > 0:
                        items_text.append(f"{type_emoji} **{item_name}** - {item_price:,} R$")
                        total_robux += item_price
                    else:
                        items_text.append(f"{type_emoji} **{item_name}** - Gratis")
                
                embed.add_field(
                    name="🎯 Objetos del Avatar",
                    value="\n".join(items_text) if items_text else "No se encontraron objetos",
                    inline=False
                )
                
                # Resumen de precios
                embed.add_field(
                    name="💰 Resumen de Precios",
                    value=f"**Total estimado:** {total_robux:,} Robux\n**Objetos encontrados:** {len(avatar_items)}\n**Objetos de pago:** {len([item for item in avatar_items if item.get('price', 0) > 0])}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🎯 Objetos del Avatar",
                    value="No se pudieron obtener los objetos del avatar",
                    inline=False
                )
            
            # Estadísticas adicionales
            embed.add_field(
                name="📊 Estadísticas del Avatar",
                value=f"**Tipo de avatar:** {avatar_info.get('avatar_type', 'R15')}\n**Escalas:** {avatar_info.get('scales', 'Normales')}\n**Colores del cuerpo:** {avatar_info.get('body_colors', 'Predeterminados')}",
                inline=True
            )
            
            # Footer con información adicional
            embed.set_footer(
                text=f"RbxServers v3.0.0 • Avatar consultado por {interaction.user.name}",
                icon_url="https://rbxservers.xyz/svgs/roblox.svg"
            )
            embed.timestamp = datetime.now()
            
            await interaction.followup.send(embed=embed, ephemeral=False)
            
            # Log del uso exitoso
            logger.info(f"✅ Avatar de {roblox_username} mostrado exitosamente para {username}")
            
            # Agregar monedas por usar el comando
            try:
                from main import coins_system
                if coins_system:
                    coins_system.add_coins(user_id, 5, "Ver avatar de Roblox")
            except Exception as e:
                logger.debug(f"Error agregando monedas: {e}")
                
        except Exception as e:
            logger.error(f"❌ Error en comando /avatar: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al obtener la información del avatar.",
                color=0x5c5c5c
            )
            embed.add_field(
                name="🔧 Posibles causas:",
                value="• Error de conexión con la API de Roblox\n• Usuario no encontrado\n• Problema temporal del servidor\n• Avatar privado o restringido",
                inline=False
            )
            embed.add_field(
                name="💡 Solución:",
                value="Inténtalo nuevamente en unos segundos o verifica el nombre de usuario.",
                inline=False
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    logger.info("✅ Comando /avatar configurado exitosamente")
    return True

async def get_roblox_user_info(username: str):
    """Obtener información básica del usuario de Roblox"""
    try:
        async with aiohttp.ClientSession() as session:
            # Primero obtener ID del usuario
            users_url = "https://users.roblox.com/v1/usernames/users"
            payload = {
                "usernames": [username],
                "excludeBannedUsers": True
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.post(users_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        user_data = data["data"][0]
                        user_id = user_data.get("id")
                        
                        # Obtener información adicional del usuario
                        user_info_url = f"https://users.roblox.com/v1/users/{user_id}"
                        async with session.get(user_info_url, headers=headers) as user_response:
                            if user_response.status == 200:
                                user_info = await user_response.json()
                                return user_info
                            else:
                                return user_data
                    else:
                        return None
                else:
                    return None
    except Exception as e:
        logger.error(f"Error obteniendo información del usuario: {e}")
        return None

async def get_avatar_info(user_id: int):
    """Obtener información del avatar del usuario"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            avatar_info = {}
            
            # Obtener imagen del avatar
            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
            async with session.get(avatar_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        avatar_info['avatar_url'] = data["data"][0].get("imageUrl")
            
            # Obtener información del avatar completo
            avatar_details_url = f"https://avatar.roblox.com/v1/users/{user_id}/avatar"
            async with session.get(avatar_details_url, headers=headers) as response:
                if response.status == 200:
                    avatar_data = await response.json()
                    
                    # Obtener información de los objetos del avatar
                    assets = avatar_data.get("assets", [])
                    avatar_items = []
                    
                    for asset in assets:
                        asset_id = asset.get("id")
                        asset_name = asset.get("name", "Objeto desconocido")
                        asset_type = asset.get("assetType", {}).get("name", "Accesorio")
                        
                        # Obtener precio del objeto
                        item_price = await get_item_price(session, asset_id)
                        
                        avatar_items.append({
                            "name": asset_name,
                            "type": asset_type,
                            "price": item_price,
                            "id": asset_id
                        })
                    
                    avatar_info['items'] = avatar_items
                    avatar_info['avatar_type'] = avatar_data.get("playerAvatarType", "R15")
                    avatar_info['scales'] = "Personalizadas" if avatar_data.get("scales") else "Normales"
                    avatar_info['body_colors'] = "Personalizados" if avatar_data.get("bodyColors") else "Predeterminados"
            
            return avatar_info
            
    except Exception as e:
        logger.error(f"Error obteniendo información del avatar: {e}")
        return None

async def get_item_price(session: aiohttp.ClientSession, asset_id: int):
    """Obtener precio de un objeto específico"""
    try:
        # Intentar obtener precio desde la API de marketplace
        marketplace_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with session.get(marketplace_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                price = data.get("PriceInRobux")
                if price is not None:
                    return price
                else:
                    return 0  # Gratis o no disponible
            else:
                return 0
    except Exception as e:
        logger.debug(f"Error obteniendo precio para asset {asset_id}: {e}")
        return 0

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
