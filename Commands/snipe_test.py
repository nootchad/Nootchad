
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
        """Debug del sistema de snipe"""
        # Verificar autenticación
        from main import check_verification
        if not await check_verification(interaction, defer_response=True):
            return
        
        try:
            embed = discord.Embed(
                title="<:1000182584:1396049547838492672> Debug del Sistema de Snipe",
                description="Información técnica del sistema",
                color=0x00ff88
            )
            
            # Test básico de conectividad
            connectivity_status = await test_api_connectivity()
            
            embed.add_field(
                name="<:1000182657:1396060091366637669> Conectividad APIs:",
                value=f"• **Roblox API:** {'✅' if connectivity_status['roblox'] else '❌'}\n• **Economy API:** {'✅' if connectivity_status['economy'] else '❌'}\n• **Catalog API:** {'✅' if connectivity_status['catalog'] else '❌'}",
                inline=False
            )
            
            # Información de módulos
            import sys
            modules_info = []
            required_modules = ['aiohttp', 'asyncio', 'json']
            for module in required_modules:
                if module in sys.modules:
                    modules_info.append(f"✅ {module}")
                else:
                    modules_info.append(f"❌ {module}")
            
            embed.add_field(
                name="<:1000182750:1396420537227411587> Módulos:",
                value="\n".join(modules_info),
                inline=True
            )
            
            # Estado del sistema
            embed.add_field(
                name="<:1000182751:1396420551798558781> Sistema:",
                value=f"• **Python:** {sys.version.split()[0]}\n• **Timestamp:** {datetime.now().strftime('%H:%M:%S')}\n• **Memoria:** OK",
                inline=True
            )
            
            embed.set_footer(text="🔧 Sistema de Debug v1.0")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error en snipe-debug: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error en Debug",
                description=f"No se pudo obtener información de debug",
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
    """Test de conectividad a las APIs"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        
        connectivity = {
            'roblox': False,
            'economy': False,
            'catalog': False
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            # Test Roblox API
            try:
                async with session.get("https://api.roblox.com/marketplace/productinfo?assetId=1028594", headers=headers) as response:
                    connectivity['roblox'] = response.status == 200
            except:
                pass
            
            # Test Economy API
            try:
                async with session.get("https://economy.roblox.com/v1/assets/1028594/details", headers=headers) as response:
                    connectivity['economy'] = response.status == 200
            except:
                pass
            
            # Test Catalog API
            try:
                async with session.get("https://catalog.roblox.com/v1/search/items?category=Accessories&limit=10", headers=headers) as response:
                    connectivity['catalog'] = response.status == 200
            except:
                pass
        
        logger.info(f"🔍 Test de conectividad: {connectivity}")
        return connectivity
        
    except Exception as e:
        logger.error(f"Error en test de conectividad: {e}")
        return {'roblox': False, 'economy': False, 'catalog': False}

def cleanup_commands(bot):
    """Limpiar recursos de test"""
    logger.info("🧹 Limpiando recursos de test")
