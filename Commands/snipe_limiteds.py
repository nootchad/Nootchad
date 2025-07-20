
"""
Sistema de Snipe para Limiteds y UGC Gratis de Roblox
Monitorea el catálogo constantemente para detectar items disponibles
"""
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Base de datos en memoria para items monitoreados
monitored_items = {}
snipe_alerts = {}  # user_id: {channels, filters}
last_check_time = {}
price_alerts = {}  # user_id: {item_id: target_price}

def setup_commands(bot):
    """Configurar comandos de snipe"""
    
    @bot.tree.command(name="snipe-monitor", description="<:1000182656:1396059543951118416> Monitorear limiteds y UGC gratis automáticamente")
    async def snipe_monitor(interaction: discord.Interaction, 
                           item_type: str = "limited", 
                           max_price: int = 0,
                           notify_channel: discord.TextChannel = None):
        """
        Configurar monitoreo automático de items
        
        Args:
            item_type: Tipo de item (limited, ugc, accessory, gear)
            max_price: Precio máximo (0 = solo gratis)
            notify_channel: Canal donde enviar notificaciones
        """
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        user_id = str(interaction.user.id)
        
        try:
            # Validar tipo de item
            valid_types = ["limited", "ugc", "accessory", "gear", "hat", "face", "shirt", "pants", "all"]
            if item_type.lower() not in valid_types:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Tipo Inválido",
                    description=f"Tipos válidos: {', '.join(valid_types)}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Configurar alertas para el usuario
            if user_id not in snipe_alerts:
                snipe_alerts[user_id] = {
                    'channels': [],
                    'filters': [],
                    'active': True,
                    'created_at': datetime.now().isoformat()
                }
            
            # Agregar filtro
            filter_config = {
                'type': item_type.lower(),
                'max_price': max_price,
                'channel_id': notify_channel.id if notify_channel else interaction.channel.id,
                'user_id': user_id,
                'added_at': datetime.now().isoformat()
            }
            
            snipe_alerts[user_id]['filters'].append(filter_config)
            
            embed = discord.Embed(
                title="<:verify:1396087763388072006> Monitor Configurado",
                description="Sistema de snipe configurado exitosamente",
                color=0x00ff88
            )
            embed.add_field(
                name="<:1000182584:1396049547838492672> Configuración:",
                value=f"• **Tipo:** {item_type}\n• **Precio máximo:** {max_price if max_price > 0 else 'Solo gratis'} <:1000182645:1396420615057047612>\n• **Canal:** {notify_channel.mention if notify_channel else 'Este canal'}",
                inline=False
            )
            embed.add_field(
                name="<:1000182657:1396060091366637669> Monitoreo:",
                value="El bot revisará cada 90 segundos automáticamente",
                inline=True
            )
            embed.add_field(
                name="<:1000182751:1396420551798558781> Controles:",
                value="`/snipe-status` - Ver estado\n`/snipe-stop` - Detener monitor",
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Iniciar tarea de monitoreo si no está activa
            if not hasattr(bot, '_snipe_task') or bot._snipe_task.done():
                bot._snipe_task = asyncio.create_task(start_snipe_monitoring(bot))
                logger.info("🎯 Tarea de snipe iniciada")
            
        except Exception as e:
            logger.error(f"Error en snipe-monitor: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error",
                description="Error configurando el monitor",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="snipe-now", description="<:1000182751:1396420551798558781> Buscar limiteds/UGC disponibles ahora mismo")
    async def snipe_now(interaction: discord.Interaction, 
                        item_type: str = "limited",
                        max_price: int = 1000):
        """Buscar items disponibles ahora mismo"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            embed = discord.Embed(
                title="<:1000182657:1396060091366637669> Buscando Items...",
                description=f"Escaneando catálogo de {item_type} con precio máximo {max_price} <:1000182645:1396420615057047612>",
                color=0xffaa00
            )
            message = await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Buscar items
            results = await search_catalog_comprehensive(item_type, max_price)
            
            if results:
                await send_snipe_results(interaction, results, message)
            else:
                embed.color = 0xff9900
                embed.title = "<:1000182563:1396420770904932372> Sin Resultados"
                embed.description = f"No se encontraron items de tipo '{item_type}' con precio ≤ {max_price} <:1000182645:1396420615057047612>"
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Sugerencias:",
                    value="• Prueba aumentar el precio máximo\n• Cambia el tipo de item\n• Usa `/snipe-monitor` para alertas automáticas",
                    inline=False
                )
                await message.edit(embed=embed)
        
        except Exception as e:
            logger.error(f"Error en snipe-now: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error de Búsqueda",
                description="Error durante la búsqueda",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="price-alert", description="<:1000182645:1396420615057047612> Configurar alerta cuando un item llegue a cierto precio")
    async def price_alert(interaction: discord.Interaction, 
                         item_id: str,
                         target_price: int):
        """Configurar alerta de precio para un item específico"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        user_id = str(interaction.user.id)
        
        try:
            # Validar ID del item
            if not item_id.isdigit():
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> ID Inválido",
                    description="El ID del item debe ser solo números",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Obtener información del item
            item_info = await get_item_info(item_id)
            if not item_info:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Item No Encontrado",
                    description=f"No se pudo encontrar el item con ID: {item_id}",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Configurar alerta de precio
            if user_id not in price_alerts:
                price_alerts[user_id] = {}
            
            price_alerts[user_id][item_id] = {
                'target_price': target_price,
                'item_name': item_info.get('name', 'Item Desconocido'),
                'current_price': item_info.get('price', 0),
                'created_at': datetime.now().isoformat(),
                'channel_id': interaction.channel.id
            }
            
            embed = discord.Embed(
                title="<:verify:1396087763388072006> Alerta de Precio Configurada",
                description=f"Te notificaré cuando el precio cambie",
                color=0x00ff88
            )
            embed.add_field(
                name="<:1000182584:1396049547838492672> Item:",
                value=f"**{item_info.get('name', 'Item')}**\nID: `{item_id}`",
                inline=True
            )
            embed.add_field(
                name="<:1000182645:1396420615057047612> Precios:",
                value=f"**Actual:** {item_info.get('price', 0)} <:1000182645:1396420615057047612>\n**Objetivo:** {target_price} <:1000182645:1396420615057047612>",
                inline=True
            )
            embed.add_field(
                name="<:1000182750:1396420537227411587> Link:",
                value=f"[Ver Item](https://www.roblox.com/catalog/{item_id})",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Iniciar monitoreo si no está activo
            if not hasattr(bot, '_price_task') or bot._price_task.done():
                bot._price_task = asyncio.create_task(start_price_monitoring(bot))
                logger.info("💰 Tarea de monitoreo de precios iniciada")
            
        except Exception as e:
            logger.error(f"Error en price-alert: {e}")
    
    @bot.tree.command(name="snipe-status", description="<:1000182584:1396049547838492672> Ver estado del sistema de snipe")
    async def snipe_status(interaction: discord.Interaction):
        """Ver estado del monitoreo"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        user_id = str(interaction.user.id)
        
        try:
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Estado del Snipe",
                color=0x00ff88
            )
            
            # Mostrar filtros de snipe
            if user_id in snipe_alerts and snipe_alerts[user_id].get('filters'):
                filters_text = ""
                for i, filter_config in enumerate(snipe_alerts[user_id]['filters'][-5:], 1):
                    filters_text += f"{i}. **{filter_config['type'].title()}** - Max: {filter_config['max_price']} <:1000182645:1396420615057047612>\n"
                
                embed.add_field(
                    name="<:1000182750:1396420537227411587> Filtros de Snipe:",
                    value=filters_text or "Ninguno",
                    inline=False
                )
            
            # Mostrar alertas de precio
            if user_id in price_alerts and price_alerts[user_id]:
                price_text = ""
                for item_id, alert_info in list(price_alerts[user_id].items())[:3]:
                    price_text += f"• **{alert_info['item_name'][:30]}**\n  Objetivo: {alert_info['target_price']} <:1000182645:1396420615057047612>\n"
                
                embed.add_field(
                    name="<:1000182645:1396420615057047612> Alertas de Precio:",
                    value=price_text or "Ninguna",
                    inline=False
                )
            
            # Estado general del sistema
            embed.add_field(
                name="<:1000182657:1396060091366637669> Última Verificación:",
                value=last_check_time.get('global', 'Nunca'),
                inline=True
            )
            embed.add_field(
                name="<:1000182584:1396049547838492672> Items en Cache:",
                value=str(len(monitored_items)),
                inline=True
            )
            
            if not snipe_alerts.get(user_id) and not price_alerts.get(user_id):
                embed.description = "No tienes configurado ningún sistema de monitoreo"
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Configurar:",
                    value="`/snipe-monitor` - Monitor automático\n`/price-alert` - Alerta de precio",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en snipe-status: {e}")
    
    @bot.tree.command(name="snipe-stop", description="<:1000182563:1396420770904932372> Detener monitoreo de snipe")
    async def snipe_stop(interaction: discord.Interaction):
        """Detener el monitoreo de snipe para el usuario"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        user_id = str(interaction.user.id)
        
        try:
            stopped_items = 0
            
            # Detener alertas de snipe
            if user_id in snipe_alerts:
                snipe_alerts[user_id]['active'] = False
                snipe_alerts[user_id]['stopped_at'] = datetime.now().isoformat()
                stopped_items += len(snipe_alerts[user_id].get('filters', []))
            
            # Detener alertas de precio
            if user_id in price_alerts:
                stopped_items += len(price_alerts[user_id])
                del price_alerts[user_id]
            
            if stopped_items > 0:
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Monitoreo Detenido",
                    description=f"Se detuvieron {stopped_items} alertas",
                    color=0x00ff88
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Reactivar:",
                    value="Usa `/snipe-monitor` o `/price-alert` para volver a activar",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Sin Monitor",
                    description="No tienes ningún monitor activo",
                    color=0xff9900
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en snipe-stop: {e}")

async def search_catalog_comprehensive(item_type: str, max_price: int) -> List[Dict]:
    """Buscar en el catálogo de Roblox usando endpoints optimizados"""
    try:
        results = []
        
        # Headers optimizados para APIs de Roblox
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            # Usar catálogo mejorado con búsqueda por categorías
            search_configs = []
            
            if item_type.lower() in ["limited", "all"]:
                search_configs.extend([
                    {
                        "url": "https://catalog.roblox.com/v1/search/items",
                        "params": {
                            "category": "Accessories",
                            "limit": 120,
                            "maxPrice": max_price if max_price > 0 else None,
                            "salesTypeFilter": 1,  # Limited items
                            "sortType": 4  # Precio (menor a mayor)
                        }
                    }
                ])
            
            if item_type.lower() in ["ugc", "all"]:
                search_configs.extend([
                    {
                        "url": "https://catalog.roblox.com/v1/search/items",
                        "params": {
                            "category": "Accessories", 
                            "limit": 120,
                            "maxPrice": max_price if max_price > 0 else None,
                            "creatorType": "User",
                            "sortType": 4
                        }
                    }
                ])
            
            # Procesar búsquedas principales
            for config in search_configs:
                try:
                    params = {k: v for k, v in config["params"].items() if v is not None}
                    
                    async with session.get(config["url"], params=params, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            items = data.get('data', [])
                            
                            # Obtener detalles específicos para cada item encontrado
                            for item in items[:30]:  # Limitar para evitar rate limits
                                try:
                                    asset_id = item.get('id')
                                    if not asset_id:
                                        continue
                                    
                                    # Obtener información detallada usando los nuevos endpoints
                                    detailed_info = await get_enhanced_asset_info(session, asset_id, headers)
                                    if detailed_info and detailed_info.get('price', 999999) <= max_price:
                                        results.append(detailed_info)
                                    
                                    await asyncio.sleep(0.5)  # Rate limiting
                                    
                                except Exception as e:
                                    logger.debug(f"Error obteniendo detalles del item {asset_id}: {e}")
                                    continue
                        
                        elif response.status == 429:
                            logger.warning(f"Rate limit alcanzado, pausando...")
                            await asyncio.sleep(5)
                        else:
                            logger.warning(f"API response {response.status} for {config['url']}")
                    
                    await asyncio.sleep(2)  # Pausa entre configs
                    
                except Exception as e:
                    logger.error(f"Error en búsqueda: {e}")
                    continue
            
            # Buscar items específicos usando endpoints de detección
            if len(results) < 10:
                logger.info("🔍 Expandiendo búsqueda con endpoints especializados...")
                additional_results = await search_with_marketplace_endpoints(session, headers, item_type, max_price)
                results.extend(additional_results)
        
        # Filtrar duplicados y ordenar
        seen_ids = set()
        unique_results = []
        for item in results:
            if item['id'] not in seen_ids:
                seen_ids.add(item['id'])
                unique_results.append(item)
        
        unique_results.sort(key=lambda x: x.get('price', 0))
        
        logger.info(f"📊 Encontrados {len(unique_results)} items únicos de tipo {item_type} con precio ≤ {max_price}")
        return unique_results[:50]
        
    except Exception as e:
        logger.error(f"Error buscando en catálogo: {e}")
        return []

async def get_enhanced_asset_info(session: aiohttp.ClientSession, asset_id: int, headers: dict) -> Optional[Dict]:
    """Obtener información detallada de un asset usando múltiples endpoints"""
    try:
        asset_info = {}
        
        # 1. Información básica del asset
        marketplace_url = f"https://api.roblox.com/marketplace/productinfo?assetId={asset_id}"
        try:
            async with session.get(marketplace_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    asset_info.update({
                        'id': asset_id,
                        'name': data.get('Name', 'Item Desconocido'),
                        'price': data.get('PriceInRobux', 0),
                        'creator': data.get('Creator', {}).get('Name', 'Roblox'),
                        'is_limited': data.get('IsLimited', False),
                        'is_limited_unique': data.get('IsLimitedUnique', False),
                        'is_for_sale': data.get('IsForSale', False),
                        'remaining': data.get('Remaining'),
                        'asset_type': data.get('AssetTypeId')
                    })
        except Exception as e:
            logger.debug(f"Error marketplace info {asset_id}: {e}")
        
        # 2. Detalles económicos del asset
        economy_url = f"https://economy.roblox.com/v1/assets/{asset_id}/details"
        try:
            async with session.get(economy_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    asset_info.update({
                        'rap': data.get('RecentAveragePrice', 0),
                        'sales': data.get('Sales', 0),
                        'original_price': data.get('OriginalPrice'),
                        'price_robux': data.get('PriceInRobux', asset_info.get('price', 0))
                    })
                    
                    # Actualizar precio si es más preciso
                    if data.get('PriceInRobux') is not None:
                        asset_info['price'] = data.get('PriceInRobux')
        except Exception as e:
            logger.debug(f"Error economy details {asset_id}: {e}")
        
        # 3. Información de revendedores (solo para limiteds)
        if asset_info.get('is_limited') or asset_info.get('is_limited_unique'):
            try:
                resellers_url = f"https://economy.roblox.com/v1/assets/{asset_id}/resellers?limit=10"
                async with session.get(resellers_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        resellers = data.get('data', [])
                        if resellers:
                            lowest_reseller = min(resellers, key=lambda x: x.get('price', 999999))
                            asset_info.update({
                                'lowest_reseller_price': lowest_reseller.get('price'),
                                'resellers_count': len(resellers)
                            })
                            
                            # Si hay revendedores más baratos, usar ese precio
                            reseller_price = lowest_reseller.get('price', 999999)
                            if reseller_price < asset_info.get('price', 999999):
                                asset_info['price'] = reseller_price
                                asset_info['price_source'] = 'reseller'
            except Exception as e:
                logger.debug(f"Error resellers info {asset_id}: {e}")
        
        # Agregar metadatos
        asset_info.update({
            'found_at': datetime.now().isoformat(),
            'search_method': 'enhanced_endpoints'
        })
        
        # Validar que tengamos información mínima
        if asset_info.get('name') and asset_info.get('price') is not None:
            return asset_info
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo info detallada del asset {asset_id}: {e}")
        return None

async def search_with_marketplace_endpoints(session: aiohttp.ClientSession, headers: dict, item_type: str, max_price: int) -> List[Dict]:
    """Buscar usando endpoints especializados de marketplace"""
    try:
        results = []
        
        # Lista de asset IDs populares para escanear (puedes expandir esto)
        scan_ranges = [
            range(1000000000, 1000001000),  # UGCs nuevos
            range(999990000, 1000000000),   # Range de UGCs
            range(1, 100000),               # Limiteds clásicos
        ]
        
        for asset_range in scan_ranges:
            if len(results) >= 20:  # Limitar para evitar rate limits
                break
                
            # Escanear sample de IDs
            sample_ids = list(asset_range)[::100][:50]  # Tomar cada 100 IDs, máximo 50
            
            # Usar endpoint batch para múltiples assets
            batch_url = "https://catalog.roblox.com/v1/catalog/items/details"
            batch_data = {
                "items": [{"itemType": "Asset", "id": asset_id} for asset_id in sample_ids]
            }
            
            try:
                async with session.post(batch_url, json=batch_data, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('data', [])
                        
                        for item in items:
                            try:
                                price = item.get('price', 0)
                                if price <= max_price and item.get('isForSale', False):
                                    
                                    item_data = {
                                        'id': item.get('id'),
                                        'name': item.get('name', 'Item Desconocido'),
                                        'price': price,
                                        'creator': item.get('creatorName', 'Roblox'),
                                        'is_limited': item.get('isLimited', False),
                                        'is_limited_unique': item.get('isLimitedUnique', False),
                                        'is_for_sale': item.get('isForSale', False),
                                        'found_at': datetime.now().isoformat(),
                                        'search_method': 'batch_scan'
                                    }
                                    
                                    results.append(item_data)
                                    
                            except Exception as e:
                                continue
                    
                    elif response.status == 429:
                        logger.warning("Rate limit en batch scan, pausando...")
                        await asyncio.sleep(10)
                        break
                        
            except Exception as e:
                logger.debug(f"Error en batch scan: {e}")
                continue
            
            await asyncio.sleep(3)  # Pausa entre batches
        
        logger.info(f"🔍 Escaneado encontró {len(results)} items adicionales")
        return results
        
    except Exception as e:
        logger.error(f"Error en marketplace scan: {e}")
        return []

async def get_item_info(item_id: str) -> Optional[Dict]:
    """Obtener información de un item específico usando endpoints optimizados"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            # Usar el endpoint más confiable de marketplace
            marketplace_url = f"https://api.roblox.com/marketplace/productinfo?assetId={item_id}"
            
            try:
                async with session.get(marketplace_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        item_info = {
                            'id': int(item_id),
                            'name': data.get('Name', 'Item Desconocido'),
                            'price': data.get('PriceInRobux', 0),
                            'creator': data.get('Creator', {}).get('Name', 'Roblox'),
                            'is_limited': data.get('IsLimited', False),
                            'is_limited_unique': data.get('IsLimitedUnique', False),
                            'is_for_sale': data.get('IsForSale', False),
                            'remaining': data.get('Remaining'),
                            'asset_type': data.get('AssetTypeId')
                        }
                        
                        # Obtener información económica adicional
                        try:
                            economy_url = f"https://economy.roblox.com/v1/assets/{item_id}/details"
                            async with session.get(economy_url, headers=headers) as econ_response:
                                if econ_response.status == 200:
                                    econ_data = await econ_response.json()
                                    item_info.update({
                                        'rap': econ_data.get('RecentAveragePrice', 0),
                                        'sales': econ_data.get('Sales', 0),
                                        'original_price': econ_data.get('OriginalPrice')
                                    })
                                    
                                    # Actualizar precio si es más preciso
                                    if econ_data.get('PriceInRobux') is not None:
                                        item_info['price'] = econ_data.get('PriceInRobux')
                        except:
                            pass
                        
                        # Para limiteds, verificar revendedores
                        if item_info.get('is_limited') or item_info.get('is_limited_unique'):
                            try:
                                resellers_url = f"https://economy.roblox.com/v1/assets/{item_id}/resellers?limit=1"
                                async with session.get(resellers_url, headers=headers) as resell_response:
                                    if resell_response.status == 200:
                                        resell_data = await resell_response.json()
                                        resellers = resell_data.get('data', [])
                                        if resellers:
                                            lowest_price = resellers[0].get('price', item_info['price'])
                                            if lowest_price < item_info['price']:
                                                item_info['price'] = lowest_price
                                                item_info['price_source'] = 'reseller'
                            except:
                                pass
                        
                        return item_info
                        
            except Exception as e:
                logger.debug(f"Error marketplace endpoint: {e}")
            
            # Fallback a endpoints alternativos
            fallback_urls = [
                f"https://economy.roblox.com/v1/assets/{item_id}/details",
                f"https://catalog.roblox.com/v1/catalog/items/{item_id}/details"
            ]
            
            for url in fallback_urls:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            return {
                                'id': int(item_id),
                                'name': data.get('name', data.get('Name', 'Item Desconocido')),
                                'price': data.get('price', data.get('PriceInRobux', 0)),
                                'creator': data.get('creatorName', data.get('Creator', {}).get('Name', 'Roblox')),
                                'is_limited': data.get('isLimited', data.get('IsLimited', False)),
                                'is_for_sale': data.get('isForSale', data.get('IsForSale', False))
                            }
                except:
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo info del item {item_id}: {e}")
        return None

async def start_snipe_monitoring(bot):
    """Tarea principal de monitoreo continuo"""
    logger.info("🎯 Iniciando monitoreo continuo de snipe...")
    
    while True:
        try:
            # Verificar si hay usuarios con monitoreo activo
            active_users = [uid for uid, data in snipe_alerts.items() if data.get('active', False)]
            
            if not active_users:
                await asyncio.sleep(90)  # 90 segundos sin usuarios activos
                continue
            
            logger.info(f"🔍 Verificando catálogo para {len(active_users)} usuarios...")
            
            # Recopilar todos los filtros únicos
            unique_filters = set()
            for user_data in snipe_alerts.values():
                if user_data.get('active', False):
                    for filter_config in user_data.get('filters', []):
                        filter_key = (filter_config['type'], filter_config['max_price'])
                        unique_filters.add(filter_key)
            
            # Procesar cada filtro único
            for item_type, max_price in unique_filters:
                try:
                    results = await search_catalog_comprehensive(item_type, max_price)
                    
                    if results:
                        await process_snipe_results(bot, results, item_type, max_price)
                    
                    # Pausa entre tipos para evitar rate limiting
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error procesando filtro {item_type}/{max_price}: {e}")
                    continue
            
            # Actualizar timestamp
            last_check_time['global'] = datetime.now().strftime('%H:%M:%S')
            
            # Pausa principal (90 segundos)
            await asyncio.sleep(90)
            
        except asyncio.CancelledError:
            logger.info("🛑 Tarea de snipe cancelada")
            break
        except Exception as e:
            logger.error(f"Error crítico en monitoreo de snipe: {e}")
            await asyncio.sleep(60)

async def start_price_monitoring(bot):
    """Tarea de monitoreo de precios"""
    logger.info("💰 Iniciando monitoreo de precios...")
    
    while True:
        try:
            if not price_alerts:
                await asyncio.sleep(300)  # 5 minutos sin alertas
                continue
            
            logger.info(f"💰 Verificando precios para {len(price_alerts)} usuarios...")
            
            # Verificar cada alerta de precio
            for user_id, user_alerts in price_alerts.items():
                for item_id, alert_info in user_alerts.items():
                    try:
                        current_info = await get_item_info(item_id)
                        if current_info:
                            current_price = current_info.get('price', 0)
                            target_price = alert_info['target_price']
                            
                            # Verificar si llegó al precio objetivo
                            if current_price <= target_price:
                                await send_price_alert(bot, user_id, item_id, alert_info, current_info)
                        
                        await asyncio.sleep(1)  # Pausa entre items
                        
                    except Exception as e:
                        logger.error(f"Error verificando precio {item_id}: {e}")
                        continue
            
            # Pausa principal (5 minutos)
            await asyncio.sleep(300)
            
        except asyncio.CancelledError:
            logger.info("🛑 Tarea de monitoreo de precios cancelada")
            break
        except Exception as e:
            logger.error(f"Error crítico en monitoreo de precios: {e}")
            await asyncio.sleep(180)

async def send_price_alert(bot, user_id: str, item_id: str, alert_info: Dict, current_info: Dict):
    """Enviar alerta de precio"""
    try:
        user = bot.get_user(int(user_id))
        if not user:
            user = await bot.fetch_user(int(user_id))
        
        embed = discord.Embed(
            title="🎯 ¡ALERTA DE PRECIO!",
            description=f"El item que monitoreabas llegó al precio objetivo",
            color=0x00ff00
        )
        
        embed.add_field(
            name="<:1000182584:1396049547838492672> Item:",
            value=f"**{current_info['name']}**",
            inline=False
        )
        
        embed.add_field(
            name="<:1000182645:1396420615057047612> Precio Actual:",
            value=f"**{current_info['price']} <:1000182645:1396420615057047612>**",
            inline=True
        )
        
        embed.add_field(
            name="<:1000182657:1396060091366637669> Precio Objetivo:",
            value=f"{alert_info['target_price']} <:1000182645:1396420615057047612>",
            inline=True
        )
        
        embed.add_field(
            name="🔗 Comprar Ahora:",
            value=f"[Ir al Item](https://www.roblox.com/catalog/{item_id})",
            inline=False
        )
        
        embed.set_footer(text="💰 RbxServers Price Alert")
        embed.timestamp = datetime.now()
        
        await user.send(embed=embed)
        logger.info(f"💰 Alerta de precio enviada a {user.name} para item {item_id}")
        
        # Remover alerta después de enviar
        if user_id in price_alerts and item_id in price_alerts[user_id]:
            del price_alerts[user_id][item_id]
        
    except Exception as e:
        logger.error(f"Error enviando alerta de precio: {e}")

async def process_snipe_results(bot, results: List[Dict], item_type: str, max_price: int):
    """Procesar resultados y enviar notificaciones"""
    try:
        # Filtrar items nuevos o cambios de precio
        new_items = []
        current_time = time.time()
        
        for item in results:
            item_id = item['id']
            item_key = f"{item_id}_{item['price']}"
            
            # Si no lo hemos visto o el precio cambió
            if (item_key not in monitored_items or 
                current_time - monitored_items[item_key].get('last_seen', 0) > 1800):  # 30 minutos
                
                monitored_items[item_key] = {
                    'data': item,
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'notified': False
                }
                new_items.append(item)
        
        if not new_items:
            return
        
        logger.info(f"🎯 {len(new_items)} items nuevos/actualizados encontrados para {item_type}")
        
        # Enviar notificaciones a usuarios relevantes
        for user_id, user_data in snipe_alerts.items():
            if not user_data.get('active', False):
                continue
            
            # Verificar si este usuario tiene filtros que coincidan
            matching_items = []
            for filter_config in user_data.get('filters', []):
                if (filter_config['type'] == item_type and 
                    filter_config['max_price'] >= max_price):
                    matching_items.extend(new_items)
            
            if matching_items:
                await send_snipe_notifications(bot, user_id, matching_items, user_data)
    
    except Exception as e:
        logger.error(f"Error procesando resultados de snipe: {e}")

async def send_snipe_notifications(bot, user_id: str, items: List[Dict], user_data: Dict):
    """Enviar notificaciones de snipe al usuario"""
    try:
        user = bot.get_user(int(user_id))
        if not user:
            user = await bot.fetch_user(int(user_id))
        
        items_to_show = items[:5]
        
        embed = discord.Embed(
            title="🎯 ¡SNIPE ALERT!",
            description=f"**{len(items_to_show)}** items encontrados que coinciden con tus filtros",
            color=0xff6b6b
        )
        
        for i, item in enumerate(items_to_show, 1):
            price_text = "GRATIS" if item['price'] == 0 else f"{item['price']} <:1000182645:1396420615057047612>"
            limited_text = " 🔥" if item.get('is_limited') else ""
            
            embed.add_field(
                name=f"{i}. {item['name'][:40]}{'...' if len(item['name']) > 40 else ''}{limited_text}",
                value=f"**Precio:** {price_text}\n**Creador:** {item['creator']}\n**ID:** `{item['id']}`",
                inline=True
            )
        
        # Enlaces rápidos
        quick_links = "\n".join([
            f"[{item['name'][:20]}...](<https://www.roblox.com/catalog/{item['id']}>)"
            for item in items_to_show[:3]
        ])
        
        embed.add_field(
            name="🔗 Enlaces Rápidos:",
            value=quick_links,
            inline=False
        )
        
        embed.set_footer(text="🤖 RbxServers Snipe System")
        embed.timestamp = datetime.now()
        
        await user.send(embed=embed)
        logger.info(f"📨 Notificación de snipe enviada a {user.name}")
        
    except Exception as e:
        logger.error(f"Error enviando notificación de snipe: {e}")

async def send_snipe_results(interaction, results: List[Dict], message):
    """Enviar resultados de búsqueda inmediata"""
    try:
        if not results:
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Sin Resultados",
                description="No se encontraron items disponibles",
                color=0xff9900
            )
            await message.edit(embed=embed)
            return
        
        results_to_show = results[:15]
        
        embed = discord.Embed(
            title="<:verify:1396087763388072006> Items Encontrados",
            description=f"**{len(results_to_show)}** items disponibles ahora mismo",
            color=0x00ff88
        )
        
        for i, item in enumerate(results_to_show, 1):
            price_text = "GRATIS" if item['price'] == 0 else f"{item['price']} <:1000182645:1396420615057047612>"
            limited_text = " 🔥" if item.get('is_limited') else ""
            creator_text = f" • {item.get('creator', 'Roblox')}" if item.get('creator') != 'Roblox' else ""
            
            embed.add_field(
                name=f"{i}. {item['name'][:35]}{'...' if len(item['name']) > 35 else ''}{limited_text}",
                value=f"**{price_text}**{creator_text}\n[Ver Item](https://www.roblox.com/catalog/{item['id']})",
                inline=True
            )
        
        if len(results) > 15:
            embed.add_field(
                name="➕ Más Resultados:",
                value=f"Se encontraron {len(results) - 15} items adicionales",
                inline=False
            )
        
        embed.set_footer(text="🎯 Resultados en tiempo real")
        await message.edit(embed=embed)
        
    except Exception as e:
        logger.error(f"Error mostrando resultados: {e}")

def cleanup_commands(bot):
    """Limpiar recursos al recargar"""
    if hasattr(bot, '_snipe_task') and not bot._snipe_task.done():
        bot._snipe_task.cancel()
    if hasattr(bot, '_price_task') and not bot._price_task.done():
        bot._price_task.cancel()
