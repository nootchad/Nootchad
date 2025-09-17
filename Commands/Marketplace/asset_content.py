
"""
Comando /asset content - Similar a /rs pero con funciones adicionales
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
    
    # Crear grupo de comandos para /asset
    asset_group = discord.app_commands.Group(name="asset", description="Comandos relacionados con assets de Roblox")
    
    @asset_group.command(name="content", description="Obtiene información detallada de un asset con funciones adicionales")
    async def asset_content_command(
        interaction: discord.Interaction, 
        asset_id: str,
        include_metadata: bool = True,
        include_creator_info: bool = True,
        include_sales_data: bool = True
    ):
        """
        Obtener información de contenido de un asset con opciones avanzadas
        
        Args:
            asset_id: ID del asset de Roblox
            include_metadata: Incluir metadatos adicionales
            include_creator_info: Incluir información del creador
            include_sales_data: Incluir datos de ventas y estadísticas
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
                title="🔍 Analizando Contenido del Asset...",
                description=f"Realizando análisis completo del asset ID: `{asset_id}`",
                color=0xffaa00
            )
            
            # Mostrar opciones activas
            options = []
            if include_metadata:
                options.append("✅ Metadatos")
            if include_creator_info:
                options.append("✅ Info del Creador")
            if include_sales_data:
                options.append("✅ Datos de Ventas")
            
            if options:
                initial_embed.add_field(name="📊 Análisis Incluido", value=" • ".join(options), inline=False)
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Obtener información completa del asset
            asset_info = await get_comprehensive_asset_info(asset_id, include_metadata, include_creator_info, include_sales_data)
            
            if not asset_info:
                error_embed = discord.Embed(
                    title="❌ Asset No Encontrado",
                    description=f"No se pudo encontrar información para el asset ID: `{asset_id}`",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return
            
            # Crear embed con información completa
            result_embed = discord.Embed(
                title="📋 Análisis de Contenido del Asset",
                description=f"**{asset_info.get('Name', 'Asset desconocido')}**",
                color=0x00ff88
            )
            
            # Información básica (siempre incluida)
            basic_info = f"**ID:** `{asset_id}`\n**Nombre:** {asset_info.get('Name', 'Desconocido')}\n**Tipo:** {get_asset_type_name(asset_info.get('AssetTypeId', 0))}"
            
            # Estado del asset
            is_for_sale = asset_info.get('IsForSale', False)
            is_limited = asset_info.get('IsLimited', False)
            is_limited_unique = asset_info.get('IsLimitedUnique', False)
            
            status_indicators = []
            if is_for_sale:
                status_indicators.append("🟢 En Venta")
            if is_limited:
                status_indicators.append("💎 Limitado")
            if is_limited_unique:
                status_indicators.append("⭐ Único")
            
            if status_indicators:
                basic_info += f"\n**Estado:** {' '.join(status_indicators)}"
            
            result_embed.add_field(
                name="📊 Información Básica",
                value=basic_info,
                inline=False
            )
            
            # Información de ventas (si está habilitada)
            if include_sales_data and 'sales_data' in asset_info:
                sales_data = asset_info['sales_data']
                price = sales_data.get('PriceInRobux', 0)
                
                if price is None:
                    price_text = "No está en venta"
                elif price == 0:
                    price_text = "Gratis"
                else:
                    price_text = f"{price:,} R$"
                
                sales_info = f"**Precio:** {price_text}\n**Ventas:** {sales_data.get('Sales', 0):,}\n**Favoritos:** {sales_data.get('Favorites', 0):,}"
                
                # Información de limitados
                if is_limited or is_limited_unique:
                    remaining = asset_info.get('Remaining')
                    if remaining is not None:
                        sales_info += f"\n**Restantes:** {remaining:,}"
                    
                    min_membership_level = asset_info.get('MinimumMembershipLevel')
                    if min_membership_level:
                        sales_info += f"\n**Membresía Mín.:** {min_membership_level}"
                
                result_embed.add_field(
                    name="💰 Datos de Ventas",
                    value=sales_info,
                    inline=True
                )
            
            # Información del creador (si está habilitada)
            if include_creator_info and 'creator_info' in asset_info:
                creator_data = asset_info['creator_info']
                creator_name = creator_data.get('Name', 'Desconocido')
                creator_id = creator_data.get('Id', 'N/A')
                creator_type = "Grupo" if creator_data.get('CreatorType') == 2 else "Usuario"
                
                creator_info = f"**{creator_type}:** {creator_name}\n**ID:** {creator_id}"
                
                # Si hay información adicional del creador
                if 'additional_creator_info' in creator_data:
                    additional = creator_data['additional_creator_info']
                    if 'memberCount' in additional:
                        creator_info += f"\n**Miembros:** {additional['memberCount']:,}"
                    if 'created' in additional:
                        created_date = additional['created']
                        try:
                            created_dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                            creator_info += f"\n**Creado:** <t:{int(created_dt.timestamp())}:R>"
                        except:
                            pass
                
                result_embed.add_field(
                    name="👤 Información del Creador",
                    value=creator_info,
                    inline=True
                )
            
            # Metadatos (si están habilitados)
            if include_metadata and 'metadata' in asset_info:
                metadata = asset_info['metadata']
                
                # Fechas
                created_date = metadata.get('Created', '')
                updated_date = metadata.get('Updated', '')
                
                if created_date:
                    try:
                        created_dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        created_formatted = f"<t:{int(created_dt.timestamp())}:F>"
                    except:
                        created_formatted = created_date
                else:
                    created_formatted = "No disponible"
                
                metadata_info = f"**Creado:** {created_formatted}\n**Actualizado:** {updated_date if updated_date else 'N/A'}"
                
                # Información técnica
                if 'content_rating' in metadata:
                    metadata_info += f"\n**Rating:** {metadata['content_rating']}"
                
                if 'genre' in metadata:
                    metadata_info += f"\n**Género:** {metadata['genre']}"
                
                result_embed.add_field(
                    name="📅 Metadatos",
                    value=metadata_info,
                    inline=False
                )
            
            # Descripción del asset
            description = asset_info.get('Description', '')
            if description:
                if len(description) > 300:
                    description = description[:300] + '...'
                result_embed.add_field(
                    name="📝 Descripción",
                    value=description,
                    inline=False
                )
            
            # Análisis adicional del contenido
            content_analysis = await analyze_asset_content(asset_id, asset_info)
            if content_analysis:
                result_embed.add_field(
                    name="🔍 Análisis de Contenido",
                    value=content_analysis,
                    inline=False
                )
            
            # Enlaces útiles
            links = f"[Ver en Roblox](https://www.roblox.com/catalog/{asset_id})"
            
            if asset_info.get('AssetTypeId') in [11, 12, 2]:  # Ropa
                links += f"\n[Thumbnail](https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png)"
            
            # Link para descargar si es posible
            if asset_info.get('AssetTypeId') in [1, 3, 4, 13]:  # Imágenes, audio, mesh, decals
                links += f"\n[Descargar](https://assetdelivery.roblox.com/v1/asset/?id={asset_id})"
            
            result_embed.add_field(
                name="🔗 Enlaces",
                value=links,
                inline=True
            )
            
            # Configurar imagen si está disponible
            try:
                await set_asset_thumbnail(result_embed, asset_id, asset_info.get('AssetTypeId', 0))
            except Exception as e:
                logger.warning(f"Error configurando thumbnail: {e}")
            
            result_embed.set_footer(text=f"Asset ID: {asset_id} • RbxServers Marketplace • Análisis Completo")
            
            await message.edit(embed=result_embed)
            
        except Exception as e:
            logger.error(f"Error en comando /asset content: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al analizar el contenido del asset. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    # Registrar el grupo de comandos
    bot.tree.add_command(asset_group)
    
    logger.info("✅ Comando /asset content configurado exitosamente")
    return True

async def get_comprehensive_asset_info(asset_id: str, include_metadata: bool, include_creator_info: bool, include_sales_data: bool):
    """Obtener información completa del asset"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            # Información básica del asset
            basic_url = f"https://api.roblox.com/marketplace/productinfo?assetId={asset_id}"
            async with session.get(basic_url, headers=headers) as response:
                if response.status != 200:
                    return None
                basic_info = await response.json()
            
            result = basic_info.copy()
            
            # Datos de ventas adicionales (si están habilitados)
            if include_sales_data:
                try:
                    sales_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
                    async with session.get(sales_url, headers=headers) as sales_response:
                        if sales_response.status == 200:
                            sales_data = await sales_response.json()
                            result['sales_data'] = sales_data
                except Exception as e:
                    logger.debug(f"Error obteniendo datos de ventas: {e}")
            
            # Información del creador (si está habilitada)
            if include_creator_info:
                try:
                    creator = basic_info.get('Creator', {})
                    creator_id = creator.get('Id')
                    creator_type = creator.get('CreatorType')
                    
                    if creator_id and creator_type:
                        if creator_type == 2:  # Grupo
                            creator_url = f"https://groups.roblox.com/v1/groups/{creator_id}"
                        else:  # Usuario
                            creator_url = f"https://users.roblox.com/v1/users/{creator_id}"
                        
                        async with session.get(creator_url, headers=headers) as creator_response:
                            if creator_response.status == 200:
                                additional_creator_info = await creator_response.json()
                                result['creator_info'] = creator.copy()
                                result['creator_info']['additional_creator_info'] = additional_creator_info
                            else:
                                result['creator_info'] = creator
                except Exception as e:
                    logger.debug(f"Error obteniendo info del creador: {e}")
                    result['creator_info'] = basic_info.get('Creator', {})
            
            # Metadatos adicionales (si están habilitados)
            if include_metadata:
                try:
                    metadata = {
                        'Created': basic_info.get('Created'),
                        'Updated': basic_info.get('Updated'),
                        'content_rating': 'Everyone',  # Default
                        'genre': get_asset_genre(basic_info.get('AssetTypeId', 0))
                    }
                    result['metadata'] = metadata
                except Exception as e:
                    logger.debug(f"Error obteniendo metadatos: {e}")
            
            return result
            
    except Exception as e:
        logger.error(f"Error obteniendo información completa del asset {asset_id}: {e}")
        return None

async def analyze_asset_content(asset_id: str, asset_info: dict) -> str:
    """Analizar el contenido del asset y proporcionar insights"""
    try:
        analysis_points = []
        
        # Análisis basado en tipo de asset
        asset_type_id = asset_info.get('AssetTypeId', 0)
        asset_type_name = get_asset_type_name(asset_type_id)
        
        # Análisis de popularidad
        sales = asset_info.get('sales_data', {}).get('Sales', 0) or asset_info.get('Sales', 0)
        favorites = asset_info.get('sales_data', {}).get('Favorites', 0) or asset_info.get('Favorites', 0)
        
        if sales > 10000:
            analysis_points.append("🔥 Muy popular (10k+ ventas)")
        elif sales > 1000:
            analysis_points.append("⭐ Popular (1k+ ventas)")
        elif sales > 100:
            analysis_points.append("📈 Moderadamente popular")
        
        # Análisis de engagement
        if favorites > 0 and sales > 0:
            fav_ratio = favorites / sales
            if fav_ratio > 0.1:
                analysis_points.append("❤️ Alta tasa de favoritos")
        
        # Análisis de precio
        price = asset_info.get('sales_data', {}).get('PriceInRobux') or asset_info.get('PriceInRobux', 0)
        if price is not None:
            if price == 0:
                analysis_points.append("🆓 Acceso gratuito")
            elif price > 1000:
                analysis_points.append("💎 Precio premium")
        
        # Análisis de tiempo
        created = asset_info.get('Created', '')
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                age_days = (datetime.now(created_dt.tzinfo) - created_dt).days
                
                if age_days > 365 * 5:
                    analysis_points.append("🕰️ Asset clásico (5+ años)")
                elif age_days > 365:
                    analysis_points.append("📅 Asset establecido")
                elif age_days < 30:
                    analysis_points.append("🆕 Asset nuevo")
            except:
                pass
        
        # Análisis específico por tipo
        if asset_type_id in [11, 12]:  # Shirts, Pants
            analysis_points.append("👕 Asset de vestimenta")
        elif asset_type_id == 2:  # T-Shirt
            analysis_points.append("👔 Camiseta personalizada")
        elif asset_type_id in [8, 41]:  # Hat, Hair
            analysis_points.append("🎩 Accesorio de avatar")
        elif asset_type_id == 9:  # Place
            analysis_points.append("🏗️ Lugar/Juego")
        elif asset_type_id in [3]:  # Audio
            analysis_points.append("🎵 Contenido de audio")
        
        return " • ".join(analysis_points[:4])  # Máximo 4 puntos
        
    except Exception as e:
        logger.debug(f"Error analizando contenido del asset: {e}")
        return "📊 Análisis básico completado"

async def set_asset_thumbnail(embed, asset_id: str, asset_type_id: int):
    """Configurar thumbnail del asset en el embed"""
    try:
        async with aiohttp.ClientSession() as session:
            # Diferentes URLs según el tipo de asset
            if asset_type_id in [9]:  # Places
                thumbnail_url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={asset_id}&size=256x256&format=Png"
            else:
                thumbnail_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=420x420&format=Png&isCircular=false"
            
            async with session.get(thumbnail_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('data') and len(data['data']) > 0:
                        image_url = data['data'][0].get('imageUrl')
                        if image_url and 'rbxcdn.com' in image_url:
                            embed.set_image(url=image_url)
    except Exception as e:
        logger.debug(f"Error configurando thumbnail: {e}")

def get_asset_type_name(asset_type_id: int) -> str:
    """Convertir ID de tipo de asset a nombre legible"""
    asset_types = {
        1: "Imagen", 2: "T-Shirt", 3: "Audio", 4: "Mesh", 5: "Script Lua",
        8: "Sombrero", 9: "Lugar", 10: "Modelo", 11: "Camisa", 12: "Pantalón",
        13: "Decal", 16: "Avatar", 17: "Cabeza", 18: "Cara", 19: "Equipo",
        21: "Insignia", 24: "Animación", 25: "Brazos", 26: "Piernas", 27: "Torso",
        28: "Paquete", 29: "Pase de Juego", 30: "Aplicación", 32: "Peinado",
        33: "Accesorio de Cara", 34: "Accesorio de Cuello", 35: "Accesorio de Hombro",
        36: "Accesorio de Frente", 37: "Accesorio Trasero", 38: "Accesorio de Cintura",
        41: "Accesorio de Cabello", 42: "Accesorio de Ojos", 43: "Accesorio de Pestañas",
        44: "Accesorio de Ceja", 45: "Video", 46: "Bundle de Avatar", 47: "Emote",
        48: "Badge", 49: "Pose"
    }
    return asset_types.get(asset_type_id, f"Tipo {asset_type_id}")

def get_asset_genre(asset_type_id: int) -> str:
    """Obtener género/categoría del asset"""
    if asset_type_id in [11, 12, 2]:
        return "Ropa"
    elif asset_type_id in [8, 32, 33, 34, 35, 36, 37, 38, 41, 42, 43, 44]:
        return "Accesorios"
    elif asset_type_id in [3, 45]:
        return "Media"
    elif asset_type_id in [9, 10]:
        return "Construcción"
    elif asset_type_id in [24, 47, 49]:
        return "Animación"
    else:
        return "General"

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
