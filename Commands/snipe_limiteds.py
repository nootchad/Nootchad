
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
            valid_types = ["limited", "ugc", "accessory", "gear", "hat", "face", "shirt", "pants"]
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
                value="El bot revisará cada 2 minutos automáticamente",
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
            results = await search_catalog_now(item_type, max_price)
            
            if results:
                await send_snipe_results(interaction, results, message)
            else:
                embed.color = 0xff9900
                embed.title = "<:1000182563:1396420770904932372> Sin Resultados"
                embed.description = "No se encontraron items disponibles con esos criterios"
                await message.edit(embed=embed)
        
        except Exception as e:
            logger.error(f"Error en snipe-now: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error de Búsqueda",
                description="Error durante la búsqueda",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="snipe-status", description="<:1000182584:1396049547838492672> Ver estado del sistema de snipe")
    async def snipe_status(interaction: discord.Interaction):
        """Ver estado del monitoreo"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        user_id = str(interaction.user.id)
        
        try:
            if user_id not in snipe_alerts:
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Sin Monitoreo",
                    description="No tienes configurado ningún monitor de snipe",
                    color=0xff9900
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Configurar:",
                    value="Usa `/snipe-monitor` para empezar",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            user_alerts = snipe_alerts[user_id]
            
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Estado del Snipe",
                description=f"Monitor {'activo' if user_alerts.get('active', False) else 'inactivo'}",
                color=0x00ff88 if user_alerts.get('active', False) else 0xff9900
            )
            
            # Mostrar filtros configurados
            if user_alerts.get('filters'):
                filters_text = ""
                for i, filter_config in enumerate(user_alerts['filters'][-5:], 1):  # Últimos 5
                    filters_text += f"{i}. **{filter_config['type'].title()}** - Max: {filter_config['max_price']} <:1000182645:1396420615057047612>\n"
                
                embed.add_field(
                    name="<:1000182750:1396420537227411587> Filtros Activos:",
                    value=filters_text or "Ninguno",
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
            if user_id in snipe_alerts:
                snipe_alerts[user_id]['active'] = False
                snipe_alerts[user_id]['stopped_at'] = datetime.now().isoformat()
                
                embed = discord.Embed(
                    title="<:verify:1396087763388072006> Monitor Detenido",
                    description="El monitoreo de snipe ha sido desactivado",
                    color=0x00ff88
                )
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Reactivar:",
                    value="Usa `/snipe-monitor` para volver a activar",
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

async def start_snipe_monitoring(bot):
    """Tarea principal de monitoreo continuo"""
    logger.info("🎯 Iniciando monitoreo continuo de snipe...")
    
    while True:
        try:
            # Verificar si hay usuarios con monitoreo activo
            active_users = [uid for uid, data in snipe_alerts.items() if data.get('active', False)]
            
            if not active_users:
                await asyncio.sleep(120)  # 2 minutos sin usuarios activos
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
                    results = await search_catalog_now(item_type, max_price)
                    
                    if results:
                        await process_snipe_results(bot, results, item_type, max_price)
                    
                    # Pausa entre tipos para evitar rate limiting
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error procesando filtro {item_type}/{max_price}: {e}")
                    continue
            
            # Actualizar timestamp
            last_check_time['global'] = datetime.now().strftime('%H:%M:%S')
            
            # Pausa principal (2 minutos)
            await asyncio.sleep(120)
            
        except asyncio.CancelledError:
            logger.info("🛑 Tarea de snipe cancelada")
            break
        except Exception as e:
            logger.error(f"Error crítico en monitoreo de snipe: {e}")
            await asyncio.sleep(60)  # Pausa en caso de error

async def search_catalog_now(item_type: str, max_price: int) -> List[Dict]:
    """Buscar en el catálogo de Roblox ahora mismo"""
    try:
        # URLs de la API de Roblox para diferentes tipos
        api_urls = {
            "limited": "https://catalog.roblox.com/v1/search/items?category=Accessories&subcategory=All&limit=120&salesTypeFilter=1",  # Limited
            "ugc": "https://catalog.roblox.com/v1/search/items?category=Accessories&subcategory=All&limit=120&creatorType=User",
            "accessory": "https://catalog.roblox.com/v1/search/items?category=Accessories&limit=120",
            "gear": "https://catalog.roblox.com/v1/search/items?category=Gear&limit=120",
            "hat": "https://catalog.roblox.com/v1/search/items?category=Accessories&subcategory=Hats&limit=120",
            "face": "https://catalog.roblox.com/v1/search/items?category=Accessories&subcategory=Faces&limit=120"
        }
        
        base_url = api_urls.get(item_type, api_urls["accessory"])
        
        # Agregar filtro de precio si es necesario
        if max_price > 0:
            base_url += f"&maxPrice={max_price}"
        else:
            base_url += "&maxPrice=0"  # Solo gratis
        
        # También buscar por available items
        base_url += "&salesTypeFilter=1"  # Items en venta
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        results = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('data', [])
                    
                    for item in items:
                        # Filtrar por disponibilidad y precio
                        price = item.get('price', 0)
                        is_for_sale = item.get('isForSale', False)
                        remaining = item.get('unitsAvailableForConsumption', 0)
                        
                        if (is_for_sale and 
                            price <= max_price and 
                            (remaining > 0 or remaining is None)):
                            
                            item_data = {
                                'id': item.get('id'),
                                'name': item.get('name'),
                                'price': price,
                                'remaining': remaining,
                                'creator': item.get('creatorName', 'Roblox'),
                                'item_type': item.get('itemType', 'Asset'),
                                'thumbnail': item.get('thumbnailUrl'),
                                'is_limited': item.get('isLimited', False),
                                'is_limited_unique': item.get('isLimitedUnique', False),
                                'found_at': datetime.now().isoformat()
                            }
                            
                            results.append(item_data)
                
                logger.info(f"📊 Encontrados {len(results)} items de tipo {item_type} con precio ≤ {max_price}")
                return results
        
    except Exception as e:
        logger.error(f"Error buscando en catálogo: {e}")
        return []

async def process_snipe_results(bot, results: List[Dict], item_type: str, max_price: int):
    """Procesar resultados y enviar notificaciones"""
    try:
        # Filtrar items nuevos (no vistos antes)
        new_items = []
        current_time = time.time()
        
        for item in results:
            item_id = item['id']
            item_key = f"{item_id}_{item['price']}"
            
            # Si no lo hemos visto o hace más de 1 hora
            if (item_key not in monitored_items or 
                current_time - monitored_items[item_key].get('last_seen', 0) > 3600):
                
                monitored_items[item_key] = {
                    'data': item,
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'notified': False
                }
                new_items.append(item)
        
        if not new_items:
            return
        
        logger.info(f"🎯 {len(new_items)} items nuevos encontrados para {item_type}")
        
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
        # Obtener usuario de Discord
        try:
            user = bot.get_user(int(user_id))
            if not user:
                user = await bot.fetch_user(int(user_id))
        except:
            logger.warning(f"No se pudo encontrar usuario {user_id}")
            return
        
        # Limitar a 5 items por notificación
        items_to_show = items[:5]
        
        embed = discord.Embed(
            title="🎯 ¡SNIPE ALERT!",
            description=f"**{len(items_to_show)}** items encontrados que coinciden con tus filtros",
            color=0xff6b6b
        )
        
        for i, item in enumerate(items_to_show, 1):
            price_text = "GRATIS" if item['price'] == 0 else f"{item['price']} <:1000182645:1396420615057047612>"
            remaining_text = f"({item['remaining']} restantes)" if item['remaining'] else ""
            
            embed.add_field(
                name=f"{i}. {item['name'][:40]}{'...' if len(item['name']) > 40 else ''}",
                value=f"**Precio:** {price_text}\n**Creador:** {item['creator']}\n**ID:** `{item['id']}` {remaining_text}",
                inline=True
            )
        
        # Agregar enlaces rápidos
        quick_links = "\n".join([
            f"[{item['name'][:20]}...](<https://www.roblox.com/catalog/{item['id']}>)"
            for item in items_to_show[:3]
        ])
        
        embed.add_field(
            name="🔗 Enlaces Rápidos:",
            value=quick_links,
            inline=False
        )
        
        embed.add_field(
            name="⚡ Instrucciones:",
            value="1. Haz clic en los enlaces\n2. Compra/Equipa rápidamente\n3. ¡Los limiteds se agotan rápido!",
            inline=False
        )
        
        embed.set_footer(text="🤖 RbxServers Snipe System")
        embed.timestamp = datetime.now()
        
        # Enviar por DM
        try:
            await user.send(embed=embed)
            logger.info(f"📨 Notificación de snipe enviada a {user.name}")
        except discord.Forbidden:
            logger.warning(f"No se pudo enviar DM a {user.name} - DMs cerrados")
        
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
        
        # Mostrar primeros 10 resultados
        results_to_show = results[:10]
        
        embed = discord.Embed(
            title="<:verify:1396087763388072006> Items Encontrados",
            description=f"**{len(results_to_show)}** items disponibles ahora mismo",
            color=0x00ff88
        )
        
        for i, item in enumerate(results_to_show, 1):
            price_text = "GRATIS" if item['price'] == 0 else f"{item['price']} <:1000182645:1396420615057047612>"
            limited_text = " 🔥" if item.get('is_limited') else ""
            
            embed.add_field(
                name=f"{i}. {item['name'][:35]}{'...' if len(item['name']) > 35 else ''}{limited_text}",
                value=f"**Precio:** {price_text}\n**ID:** `{item['id']}`\n[Ver Item](https://www.roblox.com/catalog/{item['id']})",
                inline=True
            )
        
        if len(results) > 10:
            embed.add_field(
                name="➕ Más Resultados:",
                value=f"Se encontraron {len(results) - 10} items adicionales",
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
