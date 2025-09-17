
"""
Comando /rs - Obtener información de un asset y sus assets asociados
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="rs", description="Obtiene información de un asset y sus assets asociados")
    async def rs_command(interaction: discord.Interaction, asset_id: str):
        """
        Obtener información detallada de un asset de Roblox
        
        Args:
            asset_id: ID del asset de Roblox
        """
        from main import check_verification
        
        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            # Validar Asset ID
            if not asset_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Asset Inválido",
                    description="El ID del asset debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🔍 Obteniendo Información del Asset...",
                description=f"Consultando asset ID: `{asset_id}`",
                color=0xffaa00
            )
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Obtener información del asset
            asset_info = await get_asset_info(asset_id)
            if not asset_info:
                error_embed = discord.Embed(
                    title="❌ Asset No Encontrado",
                    description=f"No se pudo encontrar información para el asset ID: `{asset_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Obtener assets asociados
            associated_assets = await get_associated_assets(asset_id)
            
            # Crear embed con información completa
            result_embed = discord.Embed(
                title="🎯 Información del Asset",
                description=f"**{asset_info.get('Name', 'Asset desconocido')}**",
                color=0x00ff88
            )
            
            # Información básica del asset
            result_embed.add_field(
                name="📊 Información Básica",
                value=f"**ID:** `{asset_id}`\n**Nombre:** {asset_info.get('Name', 'Desconocido')}\n**Tipo:** {asset_info.get('AssetTypeId', 'N/A')} ({get_asset_type_name(asset_info.get('AssetTypeId', 0))})",
                inline=False
            )
            
            # Información de precio y ventas
            if 'PriceInRobux' in asset_info:
                price = asset_info.get('PriceInRobux', 0)
                if price is None:
                    price_text = "No está en venta"
                elif price == 0:
                    price_text = "Gratis"
                else:
                    price_text = f"{price:,} R$"
                
                result_embed.add_field(
                    name="💰 Información Económica",
                    value=f"**Precio:** {price_text}\n**Ventas:** {asset_info.get('Sales', 'N/A'):,}\n**Favoritos:** {asset_info.get('Favorites', 'N/A'):,}",
                    inline=True
                )
            
            # Información del creador
            creator_info = asset_info.get('Creator', {})
            if creator_info:
                creator_name = creator_info.get('Name', 'Desconocido')
                creator_id = creator_info.get('Id', 'N/A')
                creator_type = "Grupo" if creator_info.get('CreatorType') == 2 else "Usuario"
                
                result_embed.add_field(
                    name="👤 Creador",
                    value=f"**{creator_type}:** {creator_name}\n**ID:** {creator_id}",
                    inline=True
                )
            
            # Fechas importantes
            created_date = asset_info.get('Created', '')
            updated_date = asset_info.get('Updated', '')
            if created_date:
                try:
                    created_dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    created_formatted = f"<t:{int(created_dt.timestamp())}:F>"
                except:
                    created_formatted = created_date
            else:
                created_formatted = "No disponible"
            
            result_embed.add_field(
                name="📅 Fechas",
                value=f"**Creado:** {created_formatted}\n**Actualizado:** {updated_date if updated_date else 'N/A'}",
                inline=False
            )
            
            # Descripción del asset
            description = asset_info.get('Description', '')
            if description:
                if len(description) > 200:
                    description = description[:200] + '...'
                result_embed.add_field(
                    name="📝 Descripción",
                    value=description,
                    inline=False
                )
            
            # Assets asociados
            if associated_assets:
                associated_text = []
                for asset in associated_assets[:5]:  # Mostrar máximo 5
                    asset_name = asset.get('name', 'Asset desconocido')
                    asset_type = get_asset_type_name(asset.get('assetType', {}).get('id', 0))
                    associated_text.append(f"• **{asset_name}** ({asset_type})")
                
                if len(associated_assets) > 5:
                    associated_text.append(f"... y {len(associated_assets) - 5} más")
                
                result_embed.add_field(
                    name="🔗 Assets Asociados",
                    value="\n".join(associated_text) if associated_text else "Sin assets asociados",
                    inline=False
                )
            
            # Enlaces útiles
            result_embed.add_field(
                name="🔗 Enlaces",
                value=f"[Ver en Roblox](https://www.roblox.com/catalog/{asset_id})\n[Thumbnail](https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png)",
                inline=True
            )
            
            # Configurar imagen si está disponible
            try:
                thumbnail_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png&isCircular=false"
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumbnail_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('data') and len(data['data']) > 0:
                                image_url = data['data'][0].get('imageUrl')
                                if image_url:
                                    result_embed.set_image(url=image_url)
            except Exception as e:
                logger.warning(f"Error obteniendo thumbnail: {e}")
            
            result_embed.set_footer(text=f"Asset ID: {asset_id} • RbxServers Marketplace")
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            logger.error(f"Error en comando /rs: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al consultar el asset. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /rs configurado exitosamente")
    return True

async def get_asset_info(asset_id: str):
    """Obtener información del asset desde la API de Roblox"""
    try:
        async with aiohttp.ClientSession() as session:
            # API de detalles del asset
            url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    # Intentar con API alternativa
                    alt_url = f"https://api.roblox.com/marketplace/productinfo?assetId={asset_id}"
                    async with session.get(alt_url, headers=headers) as alt_response:
                        if alt_response.status == 200:
                            return await alt_response.json()
        return None
    except Exception as e:
        logger.error(f"Error obteniendo información del asset {asset_id}: {e}")
        return None

async def get_associated_assets(asset_id: str):
    """Obtener assets asociados al asset principal"""
    try:
        async with aiohttp.ClientSession() as session:
            # Para algunos tipos de assets, pueden tener assets asociados
            url = f"https://catalog.roblox.com/v1/assets/{asset_id}/bundles"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
        return []
    except Exception as e:
        logger.debug(f"Error obteniendo assets asociados para {asset_id}: {e}")
        return []

def get_asset_type_name(asset_type_id: int) -> str:
    """Convertir ID de tipo de asset a nombre legible"""
    asset_types = {
        1: "Imagen",
        2: "T-Shirt",
        3: "Audio",
        4: "Mesh",
        5: "Script Lua",
        8: "Sombrero",
        9: "Lugar",
        10: "Modelo",
        11: "Camisa",
        12: "Pantalón",
        13: "Decal",
        16: "Avatar",
        17: "Cabeza",
        18: "Cara",
        19: "Equipo",
        21: "Insignia",
        24: "Animación",
        25: "Brazos",
        26: "Piernas",
        27: "Torso",
        28: "Paquete",
        29: "Pase de Juego",
        30: "Aplicación",
        32: "Peinado",
        33: "Accesorio de Cara",
        34: "Accesorio de Cuello",
        35: "Accesorio de Hombro",
        36: "Accesorio de Frente",
        37: "Accesorio Trasero",
        38: "Accesorio de Cintura",
        41: "Accesorio de Cabello",
        42: "Accesorio de Ojos",
        43: "Accesorio de Pestañas",
        44: "Accesorio de Ceja",
        45: "Video",
        46: "Bundle de Avatar",
        47: "Emote",
        48: "Badge",
        49: "Pose",
        50: "Climbing Animatio",
        51: "Death Animation",
        52: "Fall Animation",
        53: "Idle Animation",
        54: "Jump Animation",
        55: "Run Animation",
        56: "Swim Animation",
        57: "Walk Animation",
        58: "Dynamic Head",
        59: "Code Review",
        60: "Ad Portal",
        61: "Mood Animation",
        62: "Dynamic Torso",
        63: "Dynamic Left Arm",
        64: "Dynamic Right Arm", 
        65: "Dynamic Left Leg",
        66: "Dynamic Right Leg",
        67: "Eyebrow Accessory",
        68: "Eyelash Accessory"
    }
    return asset_types.get(asset_type_id, f"Tipo {asset_type_id}")

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
