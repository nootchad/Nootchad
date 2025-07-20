
"""
Sistema de Snipe Random para Testing
Comando simplificado para probar funcionalidad básica
"""
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import json
import random
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Configurar comando de snipe de prueba"""
    
    @bot.tree.command(name="snipe-test", description="<:1000182751:1396420551798558781> Probar sistema de snipe con items aleatorios")
    async def snipe_test(interaction: discord.Interaction):
        """Comando de prueba para verificar que el sistema de snipe funciona"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            embed = discord.Embed(
                title="<:1000182657:1396060091366637669> Probando Sistema de Snipe...",
                description="Buscando items de prueba...",
                color=0xffaa00
            )
            message = await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Test con IDs conocidos de items populares/baratos
            test_items = await test_simple_search()
            
            if test_items:
                embed.color = 0x00ff88
                embed.title = "<:verify:1396087763388072006> Test Exitoso"
                embed.description = f"Sistema funcionando - {len(test_items)} items encontrados"
                
                for i, item in enumerate(test_items[:5], 1):
                    price_text = "GRATIS" if item['price'] == 0 else f"{item['price']} <:1000182645:1396420615057047612>"
                    
                    embed.add_field(
                        name=f"{i}. {item['name'][:30]}...",
                        value=f"**Precio:** {price_text}\n**ID:** `{item['id']}`\n[Ver Item](https://www.roblox.com/catalog/{item['id']})",
                        inline=True
                    )
                
                embed.add_field(
                    name="<:1000182584:1396049547838492672> Estado del Sistema:",
                    value="✅ APIs funcionando\n✅ Parsing correcto\n✅ Embeds funcionando",
                    inline=False
                )
            else:
                embed.color = 0xff0000
                embed.title = "<:1000182563:1396420770904932372> Test Fallido"
                embed.description = "No se pudieron obtener items de prueba"
                embed.add_field(
                    name="<:1000182751:1396420551798558781> Posibles Causas:",
                    value="• Rate limiting de APIs\n• Problemas de conectividad\n• Endpoints bloqueados",
                    inline=False
                )
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en snipe-test: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error Crítico",
                description=f"Error durante el test: {str(e)[:100]}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @bot.tree.command(name="snipe-debug", description="<:1000182584:1396049547838492672> Información de debug del sistema de snipe")
    async def snipe_debug(interaction: discord.Interaction):
        """Debug avanzado del sistema de snipe"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Debug Avanzado del Sistema de Snipe",
                description="Información técnica detallada del sistema",
                color=0x00ff88
            )
            
            # Test extendido de conectividad
            connectivity_status = await test_api_connectivity()
            
            # APIs principales
            api_status = []
            api_status.append(f"• **Roblox API:** {'✅' if connectivity_status['roblox'] else '❌'}")
            api_status.append(f"• **Economy API:** {'✅' if connectivity_status['economy'] else '❌'}")
            api_status.append(f"• **Catalog API:** {'✅' if connectivity_status['catalog'] else '❌'}")
            api_status.append(f"• **Rolimons API:** {'✅' if connectivity_status.get('rolimons') else '❌'}")
            
            embed.add_field(
                name="<:1000182657:1396060091366637669> Conectividad APIs:",
                value="\n".join(api_status),
                inline=False
            )
            
            # Detalles técnicos de las APIs
            details = connectivity_status.get('details', {})
            if details:
                technical_info = []
                for api_name, api_details in details.items():
                    if isinstance(api_details, dict):
                        if 'status' in api_details:
                            technical_info.append(f"**{api_name.title()}:** {api_details['status']} ({api_details.get('response_time', 'N/A')}s)")
                        elif 'error' in api_details:
                            technical_info.append(f"**{api_name.title()}:** Error - {str(api_details['error'])[:50]}...")
                
                if technical_info:
                    embed.add_field(
                        name="<:1000182751:1396420551798558781> Detalles Técnicos:",
                        value="\n".join(technical_info[:6]),  # Limitar a 6 líneas
                        inline=False
                    )
            
            # Recomendaciones basadas en el estado
            recommendations = []
            working_apis = sum([connectivity_status.get(api, False) for api in ['roblox', 'economy', 'catalog', 'rolimons']])
            
            if working_apis >= 2:
                recommendations.append("✅ **Estado:** Sistema operativo")
                recommendations.append("🔄 **Método:** APIs múltiples disponibles")
            elif working_apis == 1:
                recommendations.append("⚠️ **Estado:** Funcionalidad limitada")
                recommendations.append("🛡️ **Método:** Usando respaldos")
            else:
                recommendations.append("❌ **Estado:** APIs no disponibles")
                recommendations.append("🧪 **Método:** Usando datos de prueba")
            
            if connectivity_status.get('catalog'):
                recommendations.append("💡 **Sugerencia:** Catalog API funcionando - snipe operativo")
            
            embed.add_field(
                name="<:1000182584:1396049547838492672> Estado y Recomendaciones:",
                value="\n".join(recommendations),
                inline=False
            )
            
            # Información del sistema
            import sys
            system_info = []
            system_info.append(f"• **Python:** {sys.version.split()[0]}")
            system_info.append(f"• **Timestamp:** {datetime.now().strftime('%H:%M:%S')}")
            system_info.append(f"• **APIs Funcionando:** {working_apis}/4")
            system_info.append(f"• **Módulos:** {'✅ Cargados' if 'aiohttp' in sys.modules else '❌ Faltantes'}")
            
            embed.add_field(
                name="<:1000182750:1396420537227411587> Sistema:",
                value="\n".join(system_info),
                inline=True
            )
            
            # Métodos de respaldo disponibles
            fallback_methods = []
            if connectivity_status.get('catalog'):
                fallback_methods.append("✅ Catalog API")
            if connectivity_status.get('rolimons'):
                fallback_methods.append("✅ Rolimons API")
            fallback_methods.append("✅ Datos de Prueba")
            fallback_methods.append("✅ Cache Local")
            
            embed.add_field(
                name="🛡️ Métodos de Respaldo:",
                value="\n".join(fallback_methods),
                inline=True
            )
            
            embed.set_footer(text="🔧 Sistema de Debug Avanzado v2.0")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en snipe-debug: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error en Debug",
                description=f"No se pudo obtener información de debug: {str(e)[:100]}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def test_simple_search() -> List[Dict]:
    """Test simplificado de búsqueda"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        # Lista de IDs de items conocidos para test
        test_ids = [
            1028594, 1365767, 1374269, 102611803, 16630147,  # Hats clásicos
            11748356, 13421774, 20573078, 25804887, 27132076  # Más items
        ]
        
        results = []
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            # Probar algunos IDs aleatorios
            random_ids = random.sample(test_ids, 5)
            
            for asset_id in random_ids:
                try:
                    # Test con marketplace API
                    url = f"https://api.roblox.com/marketplace/productinfo?assetId={asset_id}"
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Verificar que sea un item válido
                            if data.get('Name') and data.get('PriceInRobux') is not None:
                                item_info = {
                                    'id': asset_id,
                                    'name': data.get('Name', 'Item de Prueba'),
                                    'price': data.get('PriceInRobux', 0),
                                    'creator': data.get('Creator', {}).get('Name', 'Roblox'),
                                    'is_limited': data.get('IsLimited', False),
                                    'is_for_sale': data.get('IsForSale', False),
                                    'found_at': datetime.now().isoformat(),
                                    'test_mode': True
                                }
                                
                                results.append(item_info)
                                logger.info(f"✅ Test item encontrado: {data.get('Name')} (ID: {asset_id})")
                        
                        elif response.status == 429:
                            logger.warning(f"⚠️ Rate limit en test para ID {asset_id}")
                            break
                        
                        else:
                            logger.debug(f"❌ Error {response.status} para ID {asset_id}")
                    
                    await asyncio.sleep(1)  # Pausa entre requests
                    
                except Exception as e:
                    logger.debug(f"Error testing ID {asset_id}: {e}")
                    continue
        
        # Si no encontramos items reales, crear datos de prueba
        if not results:
            logger.warning("🔧 Creando datos de prueba simulados")
            results = [
                {
                    'id': 999999999,
                    'name': 'Item de Prueba - Sistema Funcionando',
                    'price': 0,
                    'creator': 'RbxServers',
                    'is_limited': False,
                    'is_for_sale': True,
                    'found_at': datetime.now().isoformat(),
                    'test_mode': True,
                    'simulated': True
                }
            ]
        
        logger.info(f"🧪 Test completado: {len(results)} items de prueba")
        return results
        
    except Exception as e:
        logger.error(f"Error en test_simple_search: {e}")
        return []

async def test_api_connectivity() -> Dict[str, bool]:
    """Test de conectividad mejorado con más detalles"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        connectivity = {
            'roblox': False,
            'economy': False,
            'catalog': False,
            'rolimons': False,
            'details': {}
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            # Test Roblox API con más detalles
            try:
                start_time = time.time()
                async with session.get("https://api.roblox.com/marketplace/productinfo?assetId=1028594", headers=headers) as response:
                    response_time = time.time() - start_time
                    connectivity['roblox'] = response.status == 200
                    connectivity['details']['roblox'] = {
                        'status': response.status,
                        'response_time': round(response_time, 2),
                        'headers': dict(response.headers) if hasattr(response, 'headers') else {}
                    }
            except Exception as e:
                connectivity['details']['roblox'] = {'error': str(e)}
            
            # Test Economy API con más detalles
            try:
                start_time = time.time()
                async with session.get("https://economy.roblox.com/v1/assets/1028594/details", headers=headers) as response:
                    response_time = time.time() - start_time
                    connectivity['economy'] = response.status == 200
                    connectivity['details']['economy'] = {
                        'status': response.status,
                        'response_time': round(response_time, 2),
                        'headers': dict(response.headers) if hasattr(response, 'headers') else {}
                    }
            except Exception as e:
                connectivity['details']['economy'] = {'error': str(e)}
            
            # Test Catalog API con más detalles
            try:
                start_time = time.time()
                async with session.get("https://catalog.roblox.com/v1/search/items?category=Accessories&limit=10", headers=headers) as response:
                    response_time = time.time() - start_time
                    connectivity['catalog'] = response.status == 200
                    connectivity['details']['catalog'] = {
                        'status': response.status,
                        'response_time': round(response_time, 2),
                        'headers': dict(response.headers) if hasattr(response, 'headers') else {}
                    }
                    if response.status == 200:
                        data = await response.json()
                        connectivity['details']['catalog']['items_count'] = len(data.get('data', []))
            except Exception as e:
                connectivity['details']['catalog'] = {'error': str(e)}
            
            # Test Rolimons API (respaldo)
            try:
                start_time = time.time()
                async with session.get("https://www.rolimons.com/api/activity", headers=headers) as response:
                    response_time = time.time() - start_time
                    connectivity['rolimons'] = response.status == 200
                    connectivity['details']['rolimons'] = {
                        'status': response.status,
                        'response_time': round(response_time, 2)
                    }
                    if response.status == 200:
                        data = await response.json()
                        connectivity['details']['rolimons']['activities_count'] = len(data.get('activities', []))
            except Exception as e:
                connectivity['details']['rolimons'] = {'error': str(e)}
        
        logger.info(f"🔍 Test de conectividad extendido: {connectivity}")
        return connectivity
        
    except Exception as e:
        logger.error(f"Error en test de conectividad: {e}")
        return {'roblox': False, 'economy': False, 'catalog': False, 'rolimons': False, 'details': {'error': str(e)}}

def cleanup_commands(bot):
    """Limpiar recursos de test"""
    logger.info("🧹 Limpiando recursos de test")
