
import discord
from discord.ext import commands
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import random

logger = logging.getLogger(__name__)

class CoinsSystem:
    def __init__(self):
        self.coins_file = "user_coins.json"
        self.shop_file = "shop_items.json"
        self.user_coins = {}
        self.shop_items = {}
        self.load_coins_data()
        self.setup_shop()

    def load_coins_data(self):
        """Cargar datos de monedas desde archivo"""
        try:
            if Path(self.coins_file).exists():
                with open(self.coins_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_coins = data.get('user_coins', {})
                    logger.info(f"✅ Datos de monedas cargados para {len(self.user_coins)} usuarios")
            else:
                self.user_coins = {}
                logger.info("⚠️ Archivo de monedas no encontrado, inicializando vacío")
        except Exception as e:
            logger.error(f"❌ Error cargando datos de monedas: {e}")
            self.user_coins = {}

    def save_coins_data(self):
        """Guardar datos de monedas a archivo"""
        try:
            data = {
                'user_coins': self.user_coins,
                'last_updated': datetime.now().isoformat(),
                'total_users': len(self.user_coins)
            }
            with open(self.coins_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"💾 Datos de monedas guardados para {len(self.user_coins)} usuarios")
        except Exception as e:
            logger.error(f"❌ Error guardando datos de monedas: {e}")

    def setup_shop(self):
        """Configurar tienda de recompensas"""
        self.shop_items = {
            "juegos": {
                "blox_fruits": {
                    "name": "🌊 Blox Fruits - Servidor VIP Premium",
                    "cost": 100,
                    "description": "Acceso a servidores VIP especiales de Blox Fruits",
                    "stock": 50
                },
                "pet_simulator": {
                    "name": "🎃 Pet Simulator X - Pack Premium",
                    "cost": 80,
                    "description": "Acceso a servidores exclusivos con mejor rates",
                    "stock": 30
                },
                "anime_fighting": {
                    "name": "🌟 Anime Fighting Simulator - Boost Pack",
                    "cost": 60,
                    "description": "Servidores con XP multiplicado",
                    "stock": 40
                }
            },
            "cuentas": {
                "roblox_premium": {
                    "name": "👑 Cuenta Roblox Premium",
                    "cost": 500,
                    "description": "Cuenta de Roblox con Premium activo",
                    "stock": 5
                },
                "crunchyroll": {
                    "name": "📺 Cuenta Crunchyroll Premium",
                    "cost": 300,
                    "description": "Acceso completo a anime sin anuncios",
                    "stock": 10
                },
                "spotify": {
                    "name": "🎵 Cuenta Spotify Premium",
                    "cost": 250,
                    "description": "Música sin límites ni anuncios",
                    "stock": 15
                },
                "netflix": {
                    "name": "🎬 Cuenta Netflix Premium",
                    "cost": 400,
                    "description": "Acceso completo a Netflix HD",
                    "stock": 8
                }
            },
            "robux": {
                "robux_100": {
                    "name": "💎 100 Robux",
                    "cost": 200,
                    "description": "100 Robux directos a tu cuenta",
                    "stock": 175
                },
                "robux_500": {
                    "name": "💎 500 Robux",
                    "cost": 800,
                    "description": "500 Robux directos a tu cuenta",
                    "stock": 70
                },
                "robux_1000": {
                    "name": "💎 1000 Robux",
                    "cost": 1500,
                    "description": "1000 Robux directos a tu cuenta",
                    "stock": 35
                }
            },
            "premium": {
                "premium_7d": {
                    "name": "⭐ Premium 7 días",
                    "cost": 150,
                    "description": "Acceso premium al bot por 7 días",
                    "stock": 100
                },
                "premium_30d": {
                    "name": "⭐ Premium 30 días",
                    "cost": 500,
                    "description": "Acceso premium al bot por 30 días",
                    "stock": 50
                }
            }
        }

    def get_user_coins(self, user_id: str) -> int:
        """Obtener monedas de un usuario"""
        return self.user_coins.get(user_id, {}).get('balance', 0)

    def add_coins(self, user_id: str, amount: int, reason: str = "Unknown") -> bool:
        """Agregar monedas a un usuario"""
        try:
            if user_id not in self.user_coins:
                self.user_coins[user_id] = {
                    'balance': 0,
                    'total_earned': 0,
                    'transactions': []
                }
            
            self.user_coins[user_id]['balance'] += amount
            self.user_coins[user_id]['total_earned'] += amount
            
            # Registrar transacción
            transaction = {
                'type': 'earn',
                'amount': amount,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'balance_after': self.user_coins[user_id]['balance']
            }
            
            if 'transactions' not in self.user_coins[user_id]:
                self.user_coins[user_id]['transactions'] = []
            
            self.user_coins[user_id]['transactions'].append(transaction)
            
            # Mantener solo las últimas 50 transacciones
            if len(self.user_coins[user_id]['transactions']) > 50:
                self.user_coins[user_id]['transactions'] = self.user_coins[user_id]['transactions'][-50:]
            
            self.save_coins_data()
            logger.info(f"💰 Usuario {user_id} ganó {amount} monedas ({reason})")
            return True
        except Exception as e:
            logger.error(f"❌ Error agregando monedas: {e}")
            return False

    def spend_coins(self, user_id: str, amount: int, reason: str = "Purchase") -> bool:
        """Gastar monedas de un usuario"""
        try:
            current_balance = self.get_user_coins(user_id)
            
            if current_balance < amount:
                return False
            
            if user_id not in self.user_coins:
                return False
            
            self.user_coins[user_id]['balance'] -= amount
            
            # Registrar transacción
            transaction = {
                'type': 'spend',
                'amount': amount,
                'reason': reason,
                'timestamp': datetime.now().isoformat(),
                'balance_after': self.user_coins[user_id]['balance']
            }
            
            if 'transactions' not in self.user_coins[user_id]:
                self.user_coins[user_id]['transactions'] = []
            
            self.user_coins[user_id]['transactions'].append(transaction)
            
            # Mantener solo las últimas 50 transacciones
            if len(self.user_coins[user_id]['transactions']) > 50:
                self.user_coins[user_id]['transactions'] = self.user_coins[user_id]['transactions'][-50:]
            
            self.save_coins_data()
            logger.info(f"💸 Usuario {user_id} gastó {amount} monedas ({reason})")
            return True
        except Exception as e:
            logger.error(f"❌ Error gastando monedas: {e}")
            return False

    def get_user_stats(self, user_id: str) -> dict:
        """Obtener estadísticas de un usuario"""
        if user_id not in self.user_coins:
            return {
                'balance': 0,
                'total_earned': 0,
                'total_transactions': 0,
                'last_activity': None
            }
        
        user_data = self.user_coins[user_id]
        transactions = user_data.get('transactions', [])
        
        return {
            'balance': user_data.get('balance', 0),
            'total_earned': user_data.get('total_earned', 0),
            'total_transactions': len(transactions),
            'last_activity': transactions[-1]['timestamp'] if transactions else None
        }

# Instancia global del sistema de monedas
coins_system = CoinsSystem()

def setup_coins_commands(bot):
    """Configurar comandos de monedas"""
    
    @bot.tree.command(name="balance", description="Ver tu balance de monedas/créditos")
    async def balance_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Verificar verificación (usar la función existente)
        if not await check_verification(interaction, defer_response=False):
            return
        
        stats = coins_system.get_user_stats(user_id)
        balance = stats['balance']
        
        embed = discord.Embed(
            title="💰 Tu Balance",
            description=f"Aquí tienes tu información de monedas/créditos:",
            color=0x00ff88
        )
        
        embed.add_field(
            name="💎 Balance Actual",
            value=f"**{balance:,}** monedas",
            inline=True
        )
        
        embed.add_field(
            name="📈 Total Ganado",
            value=f"{stats['total_earned']:,} monedas",
            inline=True
        )
        
        embed.add_field(
            name="📊 Transacciones",
            value=f"{stats['total_transactions']} total",
            inline=True
        )
        
        if balance >= 1000:
            embed.add_field(
                name="🎯 Estado",
                value="🔥 **¡Gran Ahorrador!**",
                inline=False
            )
        elif balance >= 500:
            embed.add_field(
                name="🎯 Estado",
                value="⭐ **¡Buen Progreso!**",
                inline=False
            )
        elif balance >= 100:
            embed.add_field(
                name="🎯 Estado",
                value="🌟 **¡Comenzando Bien!**",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Estado",
                value="🚀 **¡Empezando tu Aventura!**",
                inline=False
            )
        
        embed.add_field(
            name="💡 ¿Cómo conseguir más monedas?",
            value="• Usa cualquier comando del bot (+5 monedas)\n• Invita el bot a nuevos servidores (+50 monedas)\n• Participa en eventos especiales",
            inline=False
        )
        
        embed.set_footer(text=f"Usuario: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="stock", description="Ver la tienda de recompensas disponibles")
    async def stock_command(interaction: discord.Interaction):
        # Verificar verificación
        if not await check_verification(interaction, defer_response=False):
            return
        
        embed = discord.Embed(
            title="🏪 Tienda de Recompensas",
            description="Selecciona una categoría para ver las recompensas disponibles:",
            color=0x3366ff
        )
        
        categories_info = {
            "🎮 **Juegos**": "Servidores VIP y contenido premium para tus juegos favoritos",
            "👤 **Cuentas**": "Cuentas premium de diferentes plataformas",
            "💎 **Robux**": "Robux directos a tu cuenta de Roblox",
            "⭐ **Premium**": "Acceso premium al bot con beneficios exclusivos"
        }
        
        for category, description in categories_info.items():
            embed.add_field(
                name=category,
                value=description,
                inline=False
            )
        
        embed.add_field(
            name="📝 ¿Cómo usar la tienda?",
            value="Usa `/buy [categoría] [item]` para comprar un artículo específico",
            inline=False
        )
        
        embed.add_field(
            name="💰 Tu Balance",
            value=f"**{coins_system.get_user_coins(str(interaction.user.id)):,}** monedas",
            inline=True
        )
        
        embed.set_footer(text="Usa /buy para realizar compras")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="buy", description="Comprar un artículo de la tienda")
    async def buy_command(interaction: discord.Interaction, categoria: str, item: str):
        user_id = str(interaction.user.id)
        
        # Verificar verificación
        if not await check_verification(interaction, defer_response=False):
            return
        
        # Buscar el artículo en la tienda
        item_found = None
        item_key = None
        category_key = None
        
        for cat_key, category_items in coins_system.shop_items.items():
            if categoria.lower() in cat_key.lower():
                for item_k, item_data in category_items.items():
                    if item.lower() in item_data['name'].lower() or item.lower() in item_k.lower():
                        item_found = item_data
                        item_key = item_k
                        category_key = cat_key
                        break
                if item_found:
                    break
        
        if not item_found:
            embed = discord.Embed(
                title="❌ Artículo No Encontrado",
                description=f"No se encontró el artículo '{item}' en la categoría '{categoria}'.",
                color=0xff0000
            )
            embed.add_field(
                name="💡 Sugerencia",
                value="Usa `/stock` para ver todos los artículos disponibles",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Verificar balance
        user_balance = coins_system.get_user_coins(user_id)
        item_cost = item_found['cost']
        
        if user_balance < item_cost:
            embed = discord.Embed(
                title="💸 Saldo Insuficiente",
                description=f"Necesitas **{item_cost:,}** monedas pero solo tienes **{user_balance:,}**.",
                color=0xff9900
            )
            embed.add_field(
                name="💰 Te faltan",
                value=f"**{item_cost - user_balance:,}** monedas",
                inline=True
            )
            embed.add_field(
                name="💡 ¿Cómo conseguir más?",
                value="Usa comandos del bot para ganar monedas",
                inline=True
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Verificar stock
        if item_found['stock'] <= 0:
            embed = discord.Embed(
                title="📦 Sin Stock",
                description=f"**{item_found['name']}** está temporalmente agotado.",
                color=0xff0000
            )
            embed.add_field(
                name="🔄 Restock",
                value="El stock se reabastece diariamente",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Realizar la compra
        if coins_system.spend_coins(user_id, item_cost, f"Compra: {item_found['name']}"):
            # Reducir stock
            coins_system.shop_items[category_key][item_key]['stock'] -= 1
            
            # Embed de confirmación
            embed = discord.Embed(
                title="✅ ¡Compra Exitosa!",
                description=f"Has comprado **{item_found['name']}** exitosamente.",
                color=0x00ff88
            )
            
            embed.add_field(
                name="💸 Costo",
                value=f"{item_cost:,} monedas",
                inline=True
            )
            
            embed.add_field(
                name="💰 Balance Restante",
                value=f"{coins_system.get_user_coins(user_id):,} monedas",
                inline=True
            )
            
            embed.add_field(
                name="📦 Descripción",
                value=item_found['description'],
                inline=False
            )
            
            embed.add_field(
                name="📞 Entrega",
                value="El artículo será entregado dentro de las próximas 24 horas. Contacta al administrador si hay demoras.",
                inline=False
            )
            
            embed.set_footer(text=f"Gracias por tu compra, {interaction.user.name}!")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log de la compra
            logger.info(f"💰 Usuario {interaction.user.name} ({user_id}) compró {item_found['name']} por {item_cost} monedas")
        else:
            embed = discord.Embed(
                title="❌ Error en la Compra",
                description="Ocurrió un error procesando tu compra. Intenta nuevamente.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    return coins_system
