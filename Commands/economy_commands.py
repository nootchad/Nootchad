
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
                name="📊 Información",
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
        """Mostrar el item limitado más barato"""
        from main import check_verification
        
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            initial_embed = discord.Embed(
                title="🔍 Buscando Item Limitado Más Barato...",
                description="Consultando catálogo de items limitados...",
                color=0xffaa00
            )
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            cheapest_item = await find_cheapest_limited()
            if not cheapest_item:
                embed = discord.Embed(
                    title="❌ Error",
                    description="No se pudieron encontrar items limitados en este momento.",
                    color=0xff0000
                )
                await message.edit(embed=embed)
                return
            
            embed = discord.Embed(
                title="💎 Item Limitado Más Barato",
                description=f"**{cheapest_item['name']}**",
                color=0x00ff88
            )
            
            embed.add_field(name="💰 Precio", value=f"{cheapest_item['price']:,} R$", inline=True)
            embed.add_field(name="📦 Restantes", value=f"{cheapest_item.get('remaining', 'N/A')}", inline=True)
            embed.add_field(name="🏷️ Tipo", value=cheapest_item.get('itemType', 'Desconocido'), inline=True)
            
            embed.add_field(
                name="🔗 Enlaces",
                value=f"[Ver en Roblox](https://www.roblox.com/catalog/{cheapest_item['id']})",
                inline=False
            )
            
            # Configurar imagen
            try:
                image_url = f"https://thumbnails.roblox.com/v1/assets?assetIds={cheapest_item['id']}&size=420x420&format=Png"
                embed.set_image(url=image_url)
            except:
                pass
            
            embed.set_footer(text="RbxServers • Limited Items")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en limited cheapest: {e}")
            try:
                await message.edit(embed=discord.Embed(title="❌ Error", color=0xff0000))
            except:
                await interaction.followup.send("Error buscando items limitados.", ephemeral=True)
    
    @limited_group.command(name="search", description="Buscar ítem limitado por nombre, ID o abreviación")
    async def limited_search_command(interaction: discord.Interaction, query: str):
        """Buscar item limitado por nombre o ID"""
        from main import check_verification
        
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            initial_embed = discord.Embed(
                title="🔍 Buscando Items Limitados...",
                description=f"Buscando: **{query}**",
                color=0xffaa00
            )
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            results = await search_limited_items(query)
            if not results:
                embed = discord.Embed(
                    title="❌ Sin Resultados",
                    description=f"No se encontraron items limitados para: **{query}**",
                    color=0xff9900
                )
                await message.edit(embed=embed)
                return
            
            embed = discord.Embed(
                title="🔍 Resultados de Búsqueda - Items Limitados",
                description=f"Resultados para: **{query}**",
                color=0x00ff88
            )
            
            for i, item in enumerate(results[:5], 1):  # Mostrar máximo 5 resultados
                price_text = f"{item['price']:,} R$" if item.get('price') else "No disponible"
                embed.add_field(
                    name=f"{i}. {item['name']}",
                    value=f"**Precio:** {price_text}\n**ID:** `{item['id']}`\n[Ver en Roblox](https://www.roblox.com/catalog/{item['id']})",
                    inline=False
                )
            
            if len(results) > 5:
                embed.add_field(
                    name="📊 Más Resultados",
                    value=f"Se encontraron {len(results)} resultados en total. Mostrando los primeros 5.",
                    inline=False
                )
            
            embed.set_footer(text="RbxServers • Limited Search")
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en limited search: {e}")
            try:
                await message.edit(embed=discord.Embed(title="❌ Error", color=0xff0000))
            except:
                await interaction.followup.send("Error buscando items limitados.", ephemeral=True)
    
    # Registrar comandos
    bot.tree.add_command(limited_group)
    
    logger.info("✅ Comandos de economía configurados exitosamente")
    return True

async def find_cheapest_limited():
    """Encontrar el item limitado más barato"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://catalog.roblox.com/v1/search/items/details"
            params = {
                'Category': 'All',
                'Limit': 30,
                'SortType': 'PriceLowToHigh',
                'IncludeNotForSale': 'false'
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('data', [])
                    
                    # Filtrar solo items limitados con precio
                    limited_items = []
                    for item in items:
                        if (item.get('itemRestrictions', []) and 
                            'Limited' in item.get('itemRestrictions', []) and 
                            item.get('price')):
                            limited_items.append({
                                'id': item['id'],
                                'name': item['name'],
                                'price': item['price'],
                                'remaining': item.get('unitsAvailableForConsumption'),
                                'itemType': item.get('itemType')
                            })
                    
                    # Retornar el más barato
                    if limited_items:
                        return min(limited_items, key=lambda x: x['price'])
        return None
    except Exception as e:
        logger.error(f"Error buscando limited más barato: {e}")
        return None

async def search_limited_items(query: str):
    """Buscar items limitados por query"""
    try:
        async with aiohttp.ClientSession() as session:
            # Si es un ID numérico, buscar directamente
            if query.isdigit():
                url = f"https://economy.roblox.com/v2/assets/{query}/details"
                async with session.get(url) as response:
                    if response.status == 200:
                        item = await response.json()
                        if item.get('IsLimited') or item.get('IsLimitedUnique'):
                            return [{
                                'id': item['AssetId'],
                                'name': item['Name'],
                                'price': item.get('PriceInRobux'),
                                'itemType': 'Asset'
                            }]
            else:
                # Buscar por nombre
                url = "https://catalog.roblox.com/v1/search/items/details"
                params = {
                    'Category': 'All',
                    'Keyword': query,
                    'Limit': 30,
                    'SortType': 'Relevance'
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('data', [])
                        
                        # Filtrar solo limitados
                        limited_items = []
                        for item in items:
                            if item.get('itemRestrictions', []) and 'Limited' in item.get('itemRestrictions', []):
                                limited_items.append({
                                    'id': item['id'],
                                    'name': item['name'],
                                    'price': item.get('price'),
                                    'itemType': item.get('itemType')
                                })
                        
                        return limited_items
        return []
    except Exception as e:
        logger.error(f"Error buscando limited items: {e}")
        return []

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
