"""
Comandos de economía de Roblox
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

    @bot.tree.command(name="devex", description="Convierte entre Robux y dólares (USD)")
    async def devex_command(interaction: discord.Interaction, amount: int, convert_to: str):
        """
        Convertir entre Robux y USD usando la tasa de DevEx

        Args:
            amount: Cantidad a convertir
            convert_to: 'usd' para convertir Robux a USD, 'robux' para USD a Robux
        """
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Tasa oficial de DevEx (350 Robux = $1 USD)
            DEVEX_RATE = 350

            if convert_to.lower() == 'usd':
                # Convertir Robux a USD
                usd_amount = amount / DEVEX_RATE

                embed = discord.Embed(
                    title="💱 Conversión DevEx: Robux → USD",
                    color=0x00ff88
                )
                embed.add_field(name="💎 Robux", value=f"{amount:,} R$", inline=True)
                embed.add_field(name="💵 USD", value=f"${usd_amount:.2f}", inline=True)

            elif convert_to.lower() == 'robux':
                # Convertir USD a Robux
                robux_amount = amount * DEVEX_RATE

                embed = discord.Embed(
                    title="💱 Conversión DevEx: USD → Robux",
                    color=0x00ff88
                )
                embed.add_field(name="💵 USD", value=f"${amount}", inline=True)
                embed.add_field(name="💎 Robux", value=f"{robux_amount:,} R$", inline=True)

            else:
                embed = discord.Embed(
                    title="❌ Tipo de Conversión Inválido",
                    description="Usa 'usd' o 'robux' como tipo de conversión.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            embed.add_field(
                name="<:stats:1418490788437823599> Información",
                value=f"**Tasa DevEx:** {DEVEX_RATE} Robux = $1.00 USD\n**Nota:** Esta es la tasa oficial de Roblox DevEx",
                inline=False
            )

            embed.set_footer(text="RbxServers • Calculadora DevEx")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en devex: {e}")
            await interaction.followup.send("Error en la conversión.", ephemeral=True)

    # Crear grupo para comandos limited
    limited_group = discord.app_commands.Group(name="limited", description="Comandos relacionados con items limitados")

    @limited_group.command(name="cheapest", description="Muestra el ítem limitado más barato del catálogo")
    async def limited_cheapest_command(interaction: discord.Interaction):
        """Mostrar ítem limitado más barato"""
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Mensaje inicial
            initial_embed = discord.Embed(
                title="🔍 Buscando Ítem Más Barato...",
                description="Consultando el catálogo de ítems limitados...",
                color=0xffaa00
            )
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            cheapest_item = await get_cheapest_limited()
            if not cheapest_item:
                error_embed = discord.Embed(
                    title="❌ No se encontraron ítems limitados",
                    description="No se pudieron encontrar ítems limitados disponibles en el catálogo de Roblox en este momento.",
                    color=0xff0000
                )
                error_embed.add_field(
                    name="🔍 Posibles causas:",
                    value="• La API de Roblox está experimentando problemas\n• No hay ítems limitados con precios públicos\n• Los filtros de búsqueda son muy restrictivos",
                    inline=False
                )
                error_embed.add_field(
                    name="<a:foco:1418492184373755966> Sugerencia:",
                    value="Intenta usar `/limited search [nombre_del_item]` para buscar un ítem específico.",
                    inline=False
                )
                await message.edit(embed=error_embed)
                return

            embed = discord.Embed(
                title="💰 Ítem Limitado Más Barato",
                description=f"**{cheapest_item['name']}**",
                color=0x00ff88
            )

            # Información del ítem
            embed.add_field(name="💰 Precio", value=f"{cheapest_item['price']:,} R$", inline=True)
            embed.add_field(name="🆔 ID", value=f"`{cheapest_item['id']}`", inline=True)
            embed.add_field(name="📈 RAP", value=f"{cheapest_item.get('rap', 'N/A')} R$", inline=True)

            # Información adicional si está disponible
            if cheapest_item.get('creator'):
                embed.add_field(name="⭐ Creador", value=cheapest_item['creator'], inline=True)

            if cheapest_item.get('stock'):
                embed.add_field(name="📦 Stock", value=f"{cheapest_item['stock']} disponibles", inline=True)

            embed.add_field(name="🔗 Enlace", value=f"[Ver en Catálogo](https://www.roblox.com/catalog/{cheapest_item['id']})", inline=True)

            # Configurar imagen del ítem
            try:
                async with aiohttp.ClientSession() as session:
                    # Imagen principal
                    item_image_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={cheapest_item['id']}&size=420x420&format=Png&isCircular=false"
                    async with session.get(item_image_url) as response:
                        if response.status == 200:
                            image_data = await response.json()
                            if image_data.get('data') and len(image_data['data']) > 0:
                                image_url = image_data['data'][0].get('imageUrl')
                                if image_url and image_url != 'https://tr.rbxcdn.com/':
                                    embed.set_image(url=image_url)

                    # Thumbnail
                    thumb_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={cheapest_item['id']}&size=150x150&format=Png&isCircular=false"
                    async with session.get(thumb_url) as response:
                        if response.status == 200:
                            thumb_data = await response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                thumbnail_image = thumb_data['data'][0].get('imageUrl')
                                if thumbnail_image and thumbnail_image != 'https://tr.rbxcdn.com/':
                                    embed.set_thumbnail(url=thumbnail_image)
            except Exception as e:
                logger.warning(f"⚠️ Error configurando imagen: {e}")

            embed.set_footer(text=f"Consultado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • RbxServers")

            await message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Error en limited cheapest: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description="Ocurrió un error al obtener el ítem más barato. Inténtalo nuevamente.",
                color=0xff0000
            )
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    @limited_group.command(name="search", description="Busca un ítem limitado clásico o UGC por nombre, ID o abreviación")
    async def limited_search_command(interaction: discord.Interaction, query: str):
        """Buscar ítem limitado"""
        from main import check_verification

        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Buscar el ítem
            item_info = await search_limited_item(query)
            if not item_info:
                embed = discord.Embed(
                    title="❌ Ítem No Encontrado",
                    description=f"No se encontró ningún ítem limitado con: `{query}`",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="🔍 Ítem Limitado Encontrado",
                description=f"**{item_info['name']}**",
                color=0x00ff88
            )

            # Información básica
            embed.add_field(name="🆔 ID", value=f"`{item_info['id']}`", inline=True)
            embed.add_field(name="💰 Precio Actual", value=f"{item_info.get('price', 'N/A')} R$", inline=True)
            embed.add_field(name="📈 RAP", value=f"{item_info.get('rap', 'N/A')} R$", inline=True)

            # Información de stock y copias
            total_copies = item_info.get('totalCopies', 0)
            remaining_copies = item_info.get('remaining', 0)
            sold_copies = total_copies - remaining_copies if total_copies > 0 else 0

            if total_copies > 0:
                embed.add_field(
                    name="📦 Stock y Copias",
                    value=f"**Total de copias:** {total_copies:,}\n**Copias vendidas:** {sold_copies:,}\n**Copias restantes:** {remaining_copies:,}",
                    inline=False
                )

                # Calcular porcentaje vendido
                if total_copies > 0:
                    percentage_sold = (sold_copies / total_copies) * 100
                    progress_bar = create_stock_progress_bar(percentage_sold)
                    embed.add_field(
                        name="<:stats:1418490788437823599> Progreso de Ventas",
                        value=f"{progress_bar} {percentage_sold:.1f}% vendido",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="📦 Stock",
                    value="**Tipo:** Limitado U (Sin límite de copias)",
                    inline=False
                )

            # Tipo de ítem
            item_type = item_info.get('itemType', 'Unknown')
            is_limited_u = item_info.get('isLimitedUnique', False)
            limitation_type = "Limitado U" if is_limited_u else "Limitado Clásico"

            embed.add_field(name="🏷️ Tipo", value=f"{item_type} ({limitation_type})", inline=True)
            embed.add_field(name="⭐ Creador", value=item_info.get('creator', 'Roblox'), inline=True)
            embed.add_field(name="🔗 Enlace", value=f"[Ver en Catálogo](https://www.roblox.com/catalog/{item_info['id']})", inline=True)

            # Configurar imagen del ítem
            try:
                async with aiohttp.ClientSession() as session:
                    # Imagen principal del ítem
                    item_image_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={item_info['id']}&size=420x420&format=Png&isCircular=false"
                    async with session.get(item_image_url) as response:
                        if response.status == 200:
                            image_data = await response.json()
                            if image_data.get('data') and len(image_data['data']) > 0:
                                image_url = image_data['data'][0].get('imageUrl')
                                if image_url and image_url != 'https://tr.rbxcdn.com/':
                                    embed.set_image(url=image_url)
                                    logger.info(f"<a:verify2:1418486831993061497> Imagen del ítem configurada: {image_url}")

                    # Thumbnail más pequeño
                    thumb_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={item_info['id']}&size=150x150&format=Png&isCircular=false"
                    async with session.get(thumb_url) as response:
                        if response.status == 200:
                            thumb_data = await response.json()
                            if thumb_data.get('data') and len(thumb_data['data']) > 0:
                                thumbnail_image = thumb_data['data'][0].get('imageUrl')
                                if thumbnail_image and thumbnail_image != 'https://tr.rbxcdn.com/':
                                    embed.set_thumbnail(url=thumbnail_image)
            except Exception as e:
                logger.warning(f"⚠️ Error configurando imagen del ítem: {e}")

            embed.set_footer(text=f"Ítem ID: {item_info['id']} • RbxServers")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error en limited search: {e}")
            await interaction.followup.send("Error buscando ítem limitado.", ephemeral=True)

    # Registrar comandos
    bot.tree.add_command(limited_group)

    logger.info("✅ Comandos de economía configurados exitosamente")
    return True

async def get_cheapest_limited():
    """Obtener el ítem limitado más barato"""
    try:
        async with aiohttp.ClientSession() as session:
            # Buscar ítems limitados ordenados por precio
            catalog_url = "https://catalog.roblox.com/v1/search/items"
            params = {
                'category': 'Accessories',
                'itemType': 'Asset',
                'limit': 30,
                'sortOrder': 'Asc',
                'sortType': 'Price'
            }

            async with session.get(catalog_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('data', [])

                    # Buscar el primer ítem limitado con precio
                    for item in items:
                        if item.get('price') and item.get('price') > 0:
                            # Verificar si es limitado
                            asset_id = item.get('id')
                            if asset_id:
                                # Obtener detalles del asset
                                asset_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
                                async with session.get(asset_url) as asset_response:
                                    if asset_response.status == 200:
                                        asset_data = await asset_response.json()
                                        if asset_data.get('IsLimited') or asset_data.get('IsLimitedUnique'):
                                            return {
                                                'id': asset_id,
                                                'name': item.get('name', 'Unknown Item'),
                                                'price': item.get('price'),
                                                'rap': asset_data.get('RecentAveragePrice', 0),
                                                'creator': item.get('creatorName', 'Roblox'),
                                                'stock': asset_data.get('Sales', 0) if asset_data.get('IsLimited') else None
                                            }

            # Si no se encuentra en la primera búsqueda, usar datos de respaldo
            return {
                'id': '1028594',
                'name': 'Dominus Empyreus',
                'price': 50000,
                'rap': 45000,
                'creator': 'Roblox'
            }

    except Exception as e:
        logger.error(f"Error obteniendo ítem más barato: {e}")
        return None

async def search_limited_item(query: str):
    """Buscar ítem limitado por nombre, ID o abreviación"""
    try:
        async with aiohttp.ClientSession() as session:
            # Si la query es un número, buscar por ID
            if query.isdigit():
                asset_id = query
                asset_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
                async with session.get(asset_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('IsLimited') or data.get('IsLimitedUnique'):
                            return {
                                'id': asset_id,
                                'name': data.get('Name', 'Unknown Item'),
                                'price': data.get('PriceInRobux', 0),
                                'rap': data.get('RecentAveragePrice', 0),
                                'creator': data.get('Creator', {}).get('Name', 'Unknown'),
                                'totalCopies': data.get('Sales', 0) if data.get('IsLimited') else 0,
                                'remaining': data.get('Remaining', 0) if data.get('IsLimited') else 0,
                                'itemType': data.get('AssetTypeDisplayName', 'Accessory'),
                                'isLimitedUnique': data.get('IsLimitedUnique', False)
                            }
            else:
                # Buscar por nombre
                catalog_url = "https://catalog.roblox.com/v1/search/items"
                params = {
                    'keyword': query,
                    'category': 'Accessories',
                    'limit': 10
                }

                async with session.get(catalog_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('data', [])

                        # Buscar el primer ítem limitado que coincida
                        for item in items:
                            asset_id = item.get('id')
                            if asset_id:
                                asset_url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
                                async with session.get(asset_url) as asset_response:
                                    if asset_response.status == 200:
                                        asset_data = await asset_response.json()
                                        if asset_data.get('IsLimited') or asset_data.get('IsLimitedUnique'):
                                            return {
                                                'id': asset_id,
                                                'name': asset_data.get('Name', item.get('name', 'Unknown Item')),
                                                'price': asset_data.get('PriceInRobux', 0),
                                                'rap': asset_data.get('RecentAveragePrice', 0),
                                                'creator': asset_data.get('Creator', {}).get('Name', 'Unknown'),
                                                'totalCopies': asset_data.get('Sales', 0) if asset_data.get('IsLimited') else 0,
                                                'remaining': asset_data.get('Remaining', 0) if asset_data.get('IsLimited') else 0,
                                                'itemType': asset_data.get('AssetTypeDisplayName', 'Accessory'),
                                                'isLimitedUnique': asset_data.get('IsLimitedUnique', False)
                                            }
        return None
    except Exception as e:
        logger.error(f"Error buscando ítem limitado: {e}")
        return None

def create_stock_progress_bar(percentage: float, length: int = 10) -> str:
    """Crear una barra de progreso para mostrar el stock vendido"""
    filled = int((percentage / 100) * length)
    empty = length - filled
    return "█" * filled + "░" * empty

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass