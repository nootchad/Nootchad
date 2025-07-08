import discord
from discord.ext import commands
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import random

logger = logging.getLogger(__name__)

class StockView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=300)  # 5 minutos
        self.user_id = user_id

    @discord.ui.select(
        placeholder="Selecciona una categoría...",
        options=[
            discord.SelectOption(
                label="🎮 Juegos",
                description="Servidores VIP y contenido premium",
                value="juegos",
                emoji="🎮"
            ),
            discord.SelectOption(
                label="👤 Cuentas",
                description="Cuentas premium de plataformas",
                value="cuentas",
                emoji="👤"
            ),
            discord.SelectOption(
                label="💎 Robux",
                description="Robux directos a tu cuenta",
                value="robux",
                emoji="💎"
            ),
            discord.SelectOption(
                label="⭐ Premium",
                description="Acceso premium al bot",
                value="premium",
                emoji="⭐"
            )
        ]
    )
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        category = select.values[0]

        embed = discord.Embed(
            title=f"🏪 {select.options[next(i for i, opt in enumerate(select.options) if opt.value == category)].label}",
            description=f"Stock disponible en la categoría {category}:",
            color=0x00ff88
        )

        category_items = coins_system.shop_items.get(category, {})
        user_balance = coins_system.get_user_coins(self.user_id)

        if not category_items:
            embed.add_field(
                name="❌ Sin Stock",
                value="No hay artículos disponibles en esta categoría actualmente.",
                inline=False
            )
        else:
            for item_key, item_data in category_items.items():
                stock_status = "✅ Disponible" if item_data['stock'] > 0 else "❌ Agotado"
                affordability = "💰 Puedes comprarlo" if user_balance >= item_data['cost'] else "💸 Insuficiente"

                embed.add_field(
                    name=f"{item_data['name']}",
                    value=f"**Precio:** {item_data['cost']:,} monedas\n**Stock:** {item_data['stock']} unidades\n**Estado:** {stock_status}\n**Tu balance:** {affordability}\n\n{item_data['description']}",
                    inline=False
                )

        embed.add_field(
            name="💰 Tu Balance Actual",
            value=f"**{user_balance:,}** monedas",
            inline=True
        )

        # Actualizar la vista con el botón de compra rápida
        view = StockView(self.user_id)
        view.add_item(QuickBuyButton(category))

        await interaction.response.edit_message(embed=embed, view=view)

class QuickBuyButton(discord.ui.Button):
    def __init__(self, category: str):
        super().__init__(
            label="🛒 Compra Rápida",
            style=discord.ButtonStyle.success,
            emoji="🛒"
        )
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        modal = QuickBuyModal(self.category)
        await interaction.response.send_modal(modal)

class QuickBuyModal(discord.ui.Modal):
    def __init__(self, category: str):
        super().__init__(title=f"🛒 Compra Rápida - {category.title()}")
        self.category = category

        self.item_input = discord.ui.TextInput(
            label="Nombre del artículo",
            placeholder="Escribe el nombre del artículo que quieres comprar...",
            style=discord.TextStyle.short,
            max_length=100,
            required=True
        )
        self.add_item(self.item_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        item_name = self.item_input.value.strip()

        # Buscar el artículo
        item_found = None
        item_key = None

        category_items = coins_system.shop_items.get(self.category, {})

        for item_k, item_data in category_items.items():
            if (item_name.lower() in item_data['name'].lower() or 
                item_name.lower() in item_k.lower() or
                any(word in item_data['name'].lower() for word in item_name.lower().split())):
                item_found = item_data
                item_key = item_k
                break

        if not item_found:
            embed = discord.Embed(
                title="❌ Artículo No Encontrado",
                description=f"No se encontró '{item_name}' en la categoría {self.category}.",
                color=0xff0000
            )

            # Mostrar artículos disponibles
            available_items = []
            for item_data in category_items.values():
                if item_data['stock'] > 0:
                    available_items.append(f"• {item_data['name']}")

            if available_items:
                embed.add_field(
                    name="🛍️ Artículos Disponibles:",
                    value="\n".join(available_items[:5]),
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
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verificar stock
        if item_found['stock'] <= 0:
            embed = discord.Embed(
                title="📦 Sin Stock",
                description=f"**{item_found['name']}** está temporalmente agotado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Realizar la compra
        if coins_system.spend_coins(user_id, item_cost, f"Compra rápida: {item_found['name']}"):
            # Reducir stock
            coins_system.shop_items[self.category][item_key]['stock'] -= 1

            # Embed de confirmación
            embed = discord.Embed(
                title="✅ ¡Compra Exitosa!",
                description=f"Has comprado **{item_found['name']}** exitosamente usando la compra rápida.",
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
            logger.info(f"💰 Usuario {interaction.user.name} ({user_id}) compró {item_found['name']} por {item_cost} monedas (compra rápida)")
        else:
            embed = discord.Embed(
                title="❌ Error en la Compra",
                description="Ocurrió un error procesando tu compra. Intenta nuevamente.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# Import check_verification function
async def check_verification(interaction: discord.Interaction, defer_response: bool = True) -> bool:
    """Verificar si el usuario está autenticado - versión simplificada para coins_system"""
    # Esta es una implementación simplificada
    # En un sistema real, aquí verificarías la autenticación del usuario
    return True

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
                # Stock vacío - agregar artículos manualmente
            },
            "cuentas": {
                # Stock vacío - agregar artículos manualmente
            },
            "robux": {
                # Stock vacío - agregar artículos manualmente
            },
            "premium": {
                # Stock vacío - agregar artículos manualmente
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

        user_balance = coins_system.get_user_coins(str(interaction.user.id))

        embed = discord.Embed(
            title="🏪 Tienda de Recompensas",
            description="Selecciona una categoría del menú desplegable para ver las recompensas disponibles:",
            color=0x3366ff
        )

        embed.add_field(
            name="💰 Tu Balance",
            value=f"**{user_balance:,}** monedas",
            inline=True
        )

        embed.add_field(
            name="📝 Instrucciones",
            value="1. Selecciona una categoría\n2. Haz clic en '🛒 Compra Rápida' para comprar",
            inline=True
        )

        embed.set_footer(text="Usa el menú desplegable y el botón de compra para una experiencia más fácil")

        view = StockView(user_id=str(interaction.user.id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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

    @bot.tree.command(name="addstock", description="[OWNER ONLY] Agregar artículo al stock de la tienda")
    async def addstock_command(interaction: discord.Interaction, categoria: str, item_key: str, nombre: str, precio: int, descripcion: str, stock: int = 1):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Validar categoría
        categorias_validas = ["juegos", "cuentas", "robux", "premium"]
        if categoria.lower() not in categorias_validas:
            embed = discord.Embed(
                title="❌ Categoría Inválida",
                description=f"Las categorías válidas son: {', '.join(categorias_validas)}",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Validar precio y stock
        if precio <= 0:
            embed = discord.Embed(
                title="❌ Precio Inválido",
                description="El precio debe ser mayor a 0.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if stock < 0:
            embed = discord.Embed(
                title="❌ Stock Inválido",
                description="El stock debe ser 0 o mayor.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            categoria_key = categoria.lower()

            # Agregar artículo al stock
            coins_system.shop_items[categoria_key][item_key] = {
                "name": nombre,
                "cost": precio,
                "description": descripcion,
                "stock": stock
            }

            # Guardar cambios
            coins_system.save_coins_data()

            embed = discord.Embed(
                title="✅ Artículo Agregado",
                description=f"El artículo ha sido agregado exitosamente a la categoría **{categoria}**.",
                color=0x00ff88
            )

            embed.add_field(name="🆔 ID del Artículo", value=f"`{item_key}`", inline=True)
            embed.add_field(name="📝 Nombre", value=f"`{nombre}`", inline=True)
            embed.add_field(name="💰 Precio", value=f"{precio:,} monedas", inline=True)
            embed.add_field(name="📊 Stock", value=f"{stock} unidades", inline=True)
            embed.add_field(name="📂 Categoría", value=categoria.title(), inline=True)
            embed.add_field(name="📋 Descripción", value=descripcion, inline=False)

            await interaction.followup.send(embed=embed, ephemeral=True)

            logger.info(f"Owner {interaction.user.name} agregó artículo '{item_key}' a categoría '{categoria}'")

        except Exception as e:
            logger.error(f"Error agregando stock: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al agregar el artículo.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="removestock", description="[OWNER ONLY] Remover artículo del stock de la tienda")
    async def removestock_command(interaction: discord.Interaction, categoria: str, item_key: str):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            categoria_key = categoria.lower()

            # Verificar que la categoría existe
            if categoria_key not in coins_system.shop_items:
                embed = discord.Embed(
                    title="❌ Categoría No Encontrada",
                    description=f"La categoría '{categoria}' no existe.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Verificar que el artículo existe
            if item_key not in coins_system.shop_items[categoria_key]:
                embed = discord.Embed(
                    title="❌ Artículo No Encontrado",
                    description=f"El artículo '{item_key}' no existe en la categoría '{categoria}'.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Obtener información del artículo antes de eliminarlo
            item_info = coins_system.shop_items[categoria_key][item_key]

            # Remover artículo
            del coins_system.shop_items[categoria_key][item_key]

            # Guardar cambios
            coins_system.save_coins_data()

            embed = discord.Embed(
                title="✅ Artículo Removido",
                description=f"El artículo **{item_info['name']}** ha sido removido de la categoría **{categoria}**.",
                color=0x00ff88
            )

            embed.add_field(name="🆔 ID Removido", value=f"`{item_key}`", inline=True)
            embed.add_field(name="📝 Nombre", value=f"`{item_info['name']}`", inline=True)
            embed.add_field(name="💰 Precio", value=f"{item_info['cost']:,} monedas", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

            logger.info(f"Owner {interaction.user.name} removió artículo '{item_key}' de categoría '{categoria}'")

        except Exception as e:
            logger.error(f"Error removiendo stock: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al remover el artículo.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="updatestock", description="[OWNER ONLY] Actualizar cantidad de stock de un artículo")
    async def updatestock_command(interaction: discord.Interaction, categoria: str, item_key: str, nuevo_stock: int):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Validar stock
        if nuevo_stock < 0:
            embed = discord.Embed(
                title="❌ Stock Inválido",
                description="El stock debe ser 0 o mayor.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            categoria_key = categoria.lower()

            # Verificar que la categoría existe
            if categoria_key not in coins_system.shop_items:
                embed = discord.Embed(
                    title="❌ Categoría No Encontrada",
                    description=f"La categoría '{categoria}' no existe.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Verificar que el artículo existe
            if item_key not in coins_system.shop_items[categoria_key]:
                embed = discord.Embed(
                    title="❌ Artículo No Encontrado",
                    description=f"El artículo '{item_key}' no existe en la categoría '{categoria}'.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Actualizar stock
            stock_anterior = coins_system.shop_items[categoria_key][item_key]['stock']
            coins_system.shop_items[categoria_key][item_key]['stock'] = nuevo_stock

            # Guardar cambios
            coins_system.save_data()

            item_name = coins_system.shop_items[categoria_key][item_key]['name']

            embed = discord.Embed(
                title="✅ Stock Actualizado",
                description=f"El stock de **{item_name}** ha sido actualizado.",
                color=0x00ff88
            )

            embed.add_field(name="🆔 ID del Artículo", value=f"`{item_key}`", inline=True)
            embed.add_field(name="📝 Nombre", value=f"`{item_name}`", inline=True)
            embed.add_field(name="📂 Categoría", value=categoria.title()", inline=True)
            embed.add_field(name="📊 Stock Anterior", value=f"{stock_anterior} unidades", inline=True)
            embed.add_field(name="📊 Stock Nuevo", value=f"{nuevo_stock} unidades", inline=True)
            embed.add_field(name="🔄 Cambio", value=f"{nuevo_stock - stock_anterior:+d} unidades", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

            logger.info(f"Owner {interaction.user.name} actualizó stock de '{item_key}' de {stock_anterior} a {nuevo_stock}")

        except Exception as e:
            logger.error(f"Error actualizando stock: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al actualizar el stock.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="viewstock", description="[OWNER ONLY] Ver todo el stock disponible en la tienda")
    async def viewstock_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            embed = discord.Embed(
                title="📊 Vista Completa del Stock",
                description="Estado actual de todos los artículos en la tienda:",
                color=0x3366ff
            )

            total_items = 0
            total_stock = 0

            for categoria, items in coins_system.shop_items.items():
                if items:  # Si hay artículos en la categoría
                    items_text = []
                    categoria_stock = 0

                    for item_key, item_data in items.items():
                        stock_status = "✅" if item_data['stock'] > 0 else "❌"
                        items_text.append(f"{stock_status} `{item_key}`: **{item_data['name']}** - {item_data['cost']:,} monedas (Stock: {item_data['stock']})")
                        total_items += 1
                        categoria_stock += item_data['stock']
                        total_stock += item_data['stock']

                    embed.add_field(
                        name=f"📂 {categoria.title()} ({len(items)} artículos, {categoria_stock} total stock)",
                        value="\n".join(items_text) if items_text else "Sin artículos",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=f"📂 {categoria.title()}",
                        value="🔴 **Vacío** - Sin artículos disponibles",
                        inline=False
                    )

            embed.add_field(
                name="📈 Resumen Total",
                value=f"• **{total_items}** artículos únicos\n• **{total_stock}** unidades en stock total\n• **{len(coins_system.shop_items)}** categorías",
                inline=False
            )

            embed.set_footer(text="Usa /addstock para agregar nuevos artículos")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error viendo stock: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al obtener el stock.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    # Adding the addstock command with a modal for easier input

    class AddStockModal(discord.ui.Modal):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.categoria = None

            self.item_key_input = discord.ui.TextInput(
                label="ID del Artículo (item_key)",
                placeholder="Deja vacío para auto-generar",
                style=discord.TextStyle.short,
                required=False
            )
            self.add_item(self.item_key_input)

            self.nombre_input = discord.ui.TextInput(
                label="Nombre del Artículo",
                placeholder="Ej: Juego VIP #1",
                style=discord.TextStyle.short,
                required=False
            )
            self.add_item(self.nombre_input)

            self.precio_input = discord.ui.TextInput(
                label="Precio (en monedas)",
                placeholder="Por defecto: 100 monedas",
                style=discord.TextStyle.short,
                required=False
            )
            self.add_item(self.precio_input)

            self.descripcion_input = discord.ui.TextInput(
                label="Descripción del Artículo",
                placeholder="Por defecto: Sin descripción",
                style=discord.TextStyle.long,
                required=False
            )
            self.add_item(self.descripcion_input)

            self.stock_input = discord.ui.TextInput(
                label="Cantidad en Stock",
                placeholder="Por defecto: 1 unidad",
                style=discord.TextStyle.short,
                required=False
            )
            self.add_item(self.stock_input)

        async def on_submit(self, interaction: discord.Interaction):
            item_key = self.item_key_input.value.strip()
            nombre = self.nombre_input.value.strip()
            
            try:
                precio = int(self.precio_input.value.strip())
                stock = int(self.stock_input.value.strip())
            except ValueError:
                embed = discord.Embed(
                    title="❌ Error",
                    description="El precio y el stock deben ser números enteros válidos.",
                    color=0xff0000
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            descripcion = self.descripcion_input.value.strip()
            categoria_key = self.categoria.lower()

            # Validar precio y stock
            if precio <= 0:
                embed = discord.Embed(
                    title="❌ Precio Inválido",
                    description="El precio debe ser mayor a 0.",
                    color=0xff0000
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            if stock < 0:
                embed = discord.Embed(
                    title="❌ Stock Inválido",
                    description="El stock debe ser 0 o mayor.",
                    color=0xff0000
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            try:
                # Agregar artículo al stock
                coins_system.shop_items[categoria_key][item_key] = {
                    "name": nombre,
                    "cost": precio,
                    "description": descripcion,
                    "stock": stock
                }

                # Guardar cambios
                coins_system.save_coins_data()

                embed = discord.Embed(
                    title="✅ Artículo Agregado",
                    description=f"El artículo ha sido agregado exitosamente a la categoría **{self.categoria}**.",
                    color=0x00ff88
                )

                embed.add_field(name="🆔 ID del Artículo", value=f"`{item_key}`", inline=True)
                embed.add_field(name="📝 Nombre", value=f"`{nombre}`", inline=True)
                embed.add_field(name="💰 Precio", value=f"{precio:,} monedas", inline=True)
                embed.add_field(name="📊 Stock", value=f"{stock} unidades", inline=True)
                embed.add_field(name="📂 Categoría", value=self.categoria.title(), inline=True)
                embed.add_field(name="📋 Descripción", value=descripcion, inline=False)

                await interaction.response.send_message(embed=embed, ephemeral=True)

                logger.info(f"Owner {interaction.user.name} agregó artículo '{item_key}' a categoría '{self.categoria}'")

            except Exception as e:
                logger.error(f"Error agregando stock: {e}")
                embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error al agregar el artículo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

    class CategorySelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="🎮 Juegos",
                    description="Servidores VIP y contenido premium",
                    value="juegos",
                    emoji="🎮"
                ),
                discord.SelectOption(
                    label="👤 Cuentas",
                    description="Cuentas premium de plataformas",
                    value="cuentas",
                    emoji="👤"
                ),
                discord.SelectOption(
                    label="💎 Robux",
                    description="Robux directos a tu cuenta",
                    value="robux",
                    emoji="💎"
                ),
                discord.SelectOption(
                    label="⭐ Premium",
                    description="Acceso premium al bot",
                    value="premium",
                    emoji="⭐"
                )
            ]
            super().__init__(placeholder="Selecciona una categoría...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            modal = AddStockModal(title="Agregar Artículo al Stock")
            modal.categoria = self.values[0]
            await interaction.response.send_modal(modal)

    class AddStockView(discord.ui.View):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.add_item(CategorySelect())

    class StockManagementSelect(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label="➕ Agregar Artículo",
                    description="Agregar un nuevo artículo al stock",
                    value="add_item",
                    emoji="➕"
                ),
                discord.SelectOption(
                    label="➖ Remover Artículo",
                    description="Eliminar un artículo existente del stock",
                    value="remove_item",
                    emoji="➖"
                ),
                discord.SelectOption(
                    label="📊 Actualizar Stock",
                    description="Cambiar la cantidad de stock de un artículo",
                    value="update_stock",
                    emoji="📊"
                ),
                discord.SelectOption(
                    label="💰 Actualizar Precio",
                    description="Cambiar el precio de un artículo",
                    value="update_price",
                    emoji="💰"
                ),
                discord.SelectOption(
                    label="📋 Ver Todo el Stock",
                    description="Ver todos los artículos en todas las categorías",
                    value="view_all",
                    emoji="📋"
                )
            ]
            super().__init__(placeholder="Selecciona una acción para gestionar el stock...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            action = self.values[0]
            
            if action == "add_item":
                # Mostrar selector de categorías para agregar
                view = CategorySelectView("add")
                embed = discord.Embed(
                    title="➕ Agregar Artículo",
                    description="Selecciona la categoría donde quieres agregar el artículo:",
                    color=0x00ff88
                )
                await interaction.response.edit_message(embed=embed, view=view)
                
            elif action == "remove_item":
                view = CategorySelectView("remove")
                embed = discord.Embed(
                    title="➖ Remover Artículo",
                    description="Selecciona la categoría del artículo que quieres remover:",
                    color=0xff4444
                )
                await interaction.response.edit_message(embed=embed, view=view)
                
            elif action == "update_stock":
                view = CategorySelectView("update_stock")
                embed = discord.Embed(
                    title="📊 Actualizar Stock",
                    description="Selecciona la categoría del artículo para actualizar su stock:",
                    color=0x3366ff
                )
                await interaction.response.edit_message(embed=embed, view=view)
                
            elif action == "update_price":
                view = CategorySelectView("update_price")
                embed = discord.Embed(
                    title="💰 Actualizar Precio",
                    description="Selecciona la categoría del artículo para actualizar su precio:",
                    color=0xffaa00
                )
                await interaction.response.edit_message(embed=embed, view=view)
                
            elif action == "view_all":
                await self.show_all_stock(interaction)

        async def show_all_stock(self, interaction: discord.Interaction):
            """Mostrar todo el stock disponible"""
            embed = discord.Embed(
                title="📊 Vista Completa del Stock",
                description="Estado actual de todos los artículos en la tienda:",
                color=0x3366ff
            )

            total_items = 0
            total_stock = 0

            for categoria, items in coins_system.shop_items.items():
                if items:  # Si hay artículos en la categoría
                    items_text = []
                    categoria_stock = 0

                    for item_key, item_data in items.items():
                        stock_status = "✅" if item_data['stock'] > 0 else "❌"
                        items_text.append(f"{stock_status} `{item_key}`: **{item_data['name']}** - {item_data['cost']:,} monedas (Stock: {item_data['stock']})")
                        total_items += 1
                        categoria_stock += item_data['stock']
                        total_stock += item_data['stock']

                    embed.add_field(
                        name=f"📂 {categoria.title()} ({len(items)} artículos, {categoria_stock} total stock)",
                        value="\n".join(items_text) if items_text else "Sin artículos",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=f"📂 {categoria.title()}",
                        value="🔴 **Vacío** - Sin artículos disponibles",
                        inline=False
                    )

            embed.add_field(
                name="📈 Resumen Total",
                value=f"• **{total_items}** artículos únicos\n• **{total_stock}** unidades en stock total\n• **{len(coins_system.shop_items)}** categorías",
                inline=False
            )

            # Botón para volver al menú principal
            view = StockManagementView()
            embed.set_footer(text="Usa el menú para realizar más acciones")
            
            await interaction.response.edit_message(embed=embed, view=view)

    class CategorySelectView(discord.ui.View):
        def __init__(self, action_type):
            super().__init__(timeout=300)
            self.action_type = action_type
            self.add_item(CategorySelectForAction(action_type))
            
            # Botón para volver al menú principal
            back_button = discord.ui.Button(
                label="🔙 Volver al Menú",
                style=discord.ButtonStyle.secondary,
                emoji="🔙"
            )
            back_button.callback = self.back_to_main_menu
            self.add_item(back_button)

        async def back_to_main_menu(self, interaction: discord.Interaction):
            view = StockManagementView()
            embed = discord.Embed(
                title="🏪 Gestión de Stock",
                description="Selecciona una acción para gestionar el stock de la tienda:",
                color=0x3366ff
            )
            embed.add_field(
                name="📋 Acciones Disponibles",
                value="• **➕ Agregar**: Crear nuevos artículos\n• **➖ Remover**: Eliminar artículos existentes\n• **📊 Stock**: Actualizar cantidades\n• **💰 Precio**: Cambiar precios\n• **📋 Ver Todo**: Revisar todo el inventario",
                inline=False
            )
            await interaction.response.edit_message(embed=embed, view=view)

    class CategorySelectForAction(discord.ui.Select):
        def __init__(self, action_type):
            self.action_type = action_type
            options = [
                discord.SelectOption(
                    label="🎮 Juegos",
                    description="Servidores VIP y contenido premium",
                    value="juegos",
                    emoji="🎮"
                ),
                discord.SelectOption(
                    label="👤 Cuentas",
                    description="Cuentas premium de plataformas",
                    value="cuentas",
                    emoji="👤"
                ),
                discord.SelectOption(
                    label="💎 Robux",
                    description="Robux directos a tu cuenta",
                    value="robux",
                    emoji="💎"
                ),
                discord.SelectOption(
                    label="⭐ Premium",
                    description="Acceso premium al bot",
                    value="premium",
                    emoji="⭐"
                )
            ]
            super().__init__(placeholder="Selecciona una categoría...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            categoria = self.values[0]
            
            if self.action_type == "add":
                modal = AddStockModal(title=f"➕ Agregar Artículo - {categoria.title()}")
                modal.categoria = categoria
                await interaction.response.send_modal(modal)
                
            elif self.action_type == "remove":
                await self.show_items_for_removal(interaction, categoria)
                
            elif self.action_type == "update_stock":
                await self.show_items_for_stock_update(interaction, categoria)
                
            elif self.action_type == "update_price":
                await self.show_items_for_price_update(interaction, categoria)

        async def show_items_for_removal(self, interaction: discord.Interaction, categoria: str):
            """Mostrar artículos para remover"""
            category_items = coins_system.shop_items.get(categoria, {})
            
            if not category_items:
                embed = discord.Embed(
                    title="❌ Categoría Vacía",
                    description=f"No hay artículos en la categoría **{categoria}** para remover.",
                    color=0xff0000
                )
                view = CategorySelectView("remove")
                await interaction.response.edit_message(embed=embed, view=view)
                return

            view = ItemSelectView(categoria, "remove", category_items)
            embed = discord.Embed(
                title=f"➖ Remover Artículo - {categoria.title()}",
                description="Selecciona el artículo que quieres remover:",
                color=0xff4444
            )
            
            items_list = []
            for item_key, item_data in category_items.items():
                items_list.append(f"• **{item_data['name']}** (`{item_key}`) - {item_data['cost']:,} monedas (Stock: {item_data['stock']})")
            
            embed.add_field(
                name="📦 Artículos Disponibles",
                value="\n".join(items_list[:10]),  # Mostrar máximo 10
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=view)

        async def show_items_for_stock_update(self, interaction: discord.Interaction, categoria: str):
            """Mostrar artículos para actualizar stock"""
            category_items = coins_system.shop_items.get(categoria, {})
            
            if not category_items:
                embed = discord.Embed(
                    title="❌ Categoría Vacía",
                    description=f"No hay artículos en la categoría **{categoria}** para actualizar.",
                    color=0xff0000
                )
                view = CategorySelectView("update_stock")
                await interaction.response.edit_message(embed=embed, view=view)
                return

            view = ItemSelectView(categoria, "update_stock", category_items)
            embed = discord.Embed(
                title=f"📊 Actualizar Stock - {categoria.title()}",
                description="Selecciona el artículo cuyo stock quieres actualizar:",
                color=0x3366ff
            )
            
            items_list = []
            for item_key, item_data in category_items.items():
                stock_status = "✅ Disponible" if item_data['stock'] > 0 else "❌ Agotado"
                items_list.append(f"• **{item_data['name']}** (`{item_key}`) - Stock actual: {item_data['stock']} ({stock_status})")
            
            embed.add_field(
                name="📦 Artículos Disponibles",
                value="\n".join(items_list[:10]),  # Mostrar máximo 10
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=view)

        async def show_items_for_price_update(self, interaction: discord.Interaction, categoria: str):
            """Mostrar artículos para actualizar precio"""
            category_items = coins_system.shop_items.get(categoria, {})
            
            if not category_items:
                embed = discord.Embed(
                    title="❌ Categoría Vacía",
                    description=f"No hay artículos en la categoría **{categoria}** para actualizar precio.",
                    color=0xff0000
                )
                view = CategorySelectView("update_price")
                await interaction.response.edit_message(embed=embed, view=view)
                return

            view = ItemSelectView(categoria, "update_price", category_items)
            embed = discord.Embed(
                title=f"💰 Actualizar Precio - {categoria.title()}",
                description="Selecciona el artículo cuyo precio quieres actualizar:",
                color=0xffaa00
            )
            
            items_list = []
            for item_key, item_data in category_items.items():
                items_list.append(f"• **{item_data['name']}** (`{item_key}`) - Precio actual: {item_data['cost']:,} monedas")
            
            embed.add_field(
                name="💰 Artículos Disponibles",
                value="\n".join(items_list[:10]),  # Mostrar máximo 10
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=view)

    class ItemSelectView(discord.ui.View):
        def __init__(self, categoria: str, action_type: str, items: dict):
            super().__init__(timeout=300)
            self.categoria = categoria
            self.action_type = action_type
            
            # Crear opciones para el select
            options = []
            for item_key, item_data in list(items.items())[:25]:  # Discord limit de 25 opciones
                options.append(discord.SelectOption(
                    label=item_data['name'][:100],  # Discord limit
                    description=f"ID: {item_key} | Precio: {item_data['cost']:,} | Stock: {item_data['stock']}",
                    value=item_key
                ))
            
            if options:
                self.add_item(ItemSelect(categoria, action_type, options))
            
            # Botón para volver
            back_button = discord.ui.Button(
                label="🔙 Volver a Categorías",
                style=discord.ButtonStyle.secondary,
                emoji="🔙"
            )
            back_button.callback = self.back_to_categories
            self.add_item(back_button)

        async def back_to_categories(self, interaction: discord.Interaction):
            view = CategorySelectView(self.action_type)
            action_names = {
                "remove": "➖ Remover Artículo",
                "update_stock": "📊 Actualizar Stock", 
                "update_price": "💰 Actualizar Precio"
            }
            embed = discord.Embed(
                title=action_names.get(self.action_type, "Gestión de Stock"),
                description="Selecciona la categoría:",
                color=0x3366ff
            )
            await interaction.response.edit_message(embed=embed, view=view)

    class ItemSelect(discord.ui.Select):
        def __init__(self, categoria: str, action_type: str, options: list):
            self.categoria = categoria
            self.action_type = action_type
            super().__init__(placeholder="Selecciona un artículo...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            item_key = self.values[0]
            
            if self.action_type == "remove":
                modal = RemoveItemModal(self.categoria, item_key)
                await interaction.response.send_modal(modal)
                
            elif self.action_type == "update_stock":
                modal = UpdateStockModal(self.categoria, item_key)
                await interaction.response.send_modal(modal)
                
            elif self.action_type == "update_price":
                modal = UpdatePriceModal(self.categoria, item_key)
                await interaction.response.send_modal(modal)

    class RemoveItemModal(discord.ui.Modal):
        def __init__(self, categoria: str, item_key: str):
            super().__init__(title=f"➖ Confirmar Eliminación")
            self.categoria = categoria
            self.item_key = item_key
            
            item_data = coins_system.shop_items[categoria][item_key]
            
            self.confirm_input = discord.ui.TextInput(
                label=f"Escribe 'CONFIRMAR' para eliminar '{item_data['name']}'",
                placeholder="CONFIRMAR",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.confirm_input)

        async def on_submit(self, interaction: discord.Interaction):
            if self.confirm_input.value.strip().upper() != "CONFIRMAR":
                embed = discord.Embed(
                    title="❌ Confirmación Incorrecta",
                    description="Debes escribir 'CONFIRMAR' exactamente para eliminar el artículo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            try:
                item_info = coins_system.shop_items[self.categoria][self.item_key]
                del coins_system.shop_items[self.categoria][self.item_key]
                coins_system.save_coins_data()

                embed = discord.Embed(
                    title="✅ Artículo Eliminado",
                    description=f"**{item_info['name']}** ha sido removido exitosamente.",
                    color=0x00ff88
                )
                embed.add_field(name="🆔 ID Eliminado", value=f"`{self.item_key}`", inline=True)
                embed.add_field(name="📂 Categoría", value=self.categoria.title(), inline=True)
                embed.add_field(name="💰 Precio", value=f"{item_info['cost']:,} monedas", inline=True)

                # Volver al menú principal
                view = StockManagementView()
                await interaction.response.edit_message(embed=embed, view=view)

            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error al eliminar el artículo.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

    class UpdateStockModal(discord.ui.Modal):
        def __init__(self, categoria: str, item_key: str):
            super().__init__(title=f"📊 Actualizar Stock")
            self.categoria = categoria
            self.item_key = item_key
            
            item_data = coins_system.shop_items[categoria][item_key]
            
            self.stock_input = discord.ui.TextInput(
                label=f"Nuevo stock para '{item_data['name']}'",
                placeholder=f"Stock actual: {item_data['stock']}",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.stock_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                nuevo_stock = int(self.stock_input.value.strip())
                if nuevo_stock < 0:
                    raise ValueError("Stock no puede ser negativo")

                stock_anterior = coins_system.shop_items[self.categoria][self.item_key]['stock']
                item_name = coins_system.shop_items[self.categoria][self.item_key]['name']
                
                coins_system.shop_items[self.categoria][self.item_key]['stock'] = nuevo_stock
                coins_system.save_coins_data()

                embed = discord.Embed(
                    title="✅ Stock Actualizado",
                    description=f"Stock de **{item_name}** actualizado exitosamente.",
                    color=0x00ff88
                )
                embed.add_field(name="🆔 Artículo", value=f"`{self.item_key}`", inline=True)
                embed.add_field(name="📂 Categoría", value=self.categoria.title(), inline=True)
                embed.add_field(name="📊 Stock Anterior", value=f"{stock_anterior}", inline=True)
                embed.add_field(name="📊 Stock Nuevo", value=f"{nuevo_stock}", inline=True)
                embed.add_field(name="🔄 Cambio", value=f"{nuevo_stock - stock_anterior:+d}", inline=True)

                # Volver al menú principal
                view = StockManagementView()
                await interaction.response.edit_message(embed=embed, view=view)

            except ValueError:
                embed = discord.Embed(
                    title="❌ Stock Inválido",
                    description="El stock debe ser un número entero válido (0 o mayor).",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error al actualizar el stock.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

    class UpdatePriceModal(discord.ui.Modal):
        def __init__(self, categoria: str, item_key: str):
            super().__init__(title=f"💰 Actualizar Precio")
            self.categoria = categoria
            self.item_key = item_key
            
            item_data = coins_system.shop_items[categoria][item_key]
            
            self.price_input = discord.ui.TextInput(
                label=f"Nuevo precio para '{item_data['name']}'",
                placeholder=f"Precio actual: {item_data['cost']:,} monedas",
                style=discord.TextStyle.short,
                required=True
            )
            self.add_item(self.price_input)

        async def on_submit(self, interaction: discord.Interaction):
            try:
                nuevo_precio = int(self.price_input.value.strip())
                if nuevo_precio <= 0:
                    raise ValueError("Precio debe ser mayor a 0")

                precio_anterior = coins_system.shop_items[self.categoria][self.item_key]['cost']
                item_name = coins_system.shop_items[self.categoria][self.item_key]['name']
                
                coins_system.shop_items[self.categoria][self.item_key]['cost'] = nuevo_precio
                coins_system.save_coins_data()

                embed = discord.Embed(
                    title="✅ Precio Actualizado",
                    description=f"Precio de **{item_name}** actualizado exitosamente.",
                    color=0x00ff88
                )
                embed.add_field(name="🆔 Artículo", value=f"`{self.item_key}`", inline=True)
                embed.add_field(name="📂 Categoría", value=self.categoria.title(), inline=True)
                embed.add_field(name="💰 Precio Anterior", value=f"{precio_anterior:,} monedas", inline=True)
                embed.add_field(name="💰 Precio Nuevo", value=f"{nuevo_precio:,} monedas", inline=True)
                embed.add_field(name="🔄 Cambio", value=f"{nuevo_precio - precio_anterior:+,d} monedas", inline=True)

                # Volver al menú principal
                view = StockManagementView()
                await interaction.response.edit_message(embed=embed, view=view)

            except ValueError as e:
                embed = discord.Embed(
                    title="❌ Precio Inválido",
                    description="El precio debe ser un número entero válido mayor a 0.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except Exception as e:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Ocurrió un error al actualizar el precio.",
                    color=0xff0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

    class StockManagementView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=300)
            self.add_item(StockManagementSelect())

    @bot.tree.command(name="addstock", description="[OWNER ONLY] Gestionar stock de la tienda (agregar, remover, actualizar)")
    async def addstock_command(interaction: discord.Interaction):
        user_id = str(interaction.user.id)

        # Verificar que solo el owner o delegados puedan usar este comando
        from main import is_owner_or_delegated
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        view = StockManagementView()
        embed = discord.Embed(
            title="🏪 Gestión de Stock",
            description="Selecciona una acción para gestionar el stock de la tienda:",
            color=0x3366ff
        )
        embed.add_field(
            name="📋 Acciones Disponibles",
            value="• **➕ Agregar**: Crear nuevos artículos\n• **➖ Remover**: Eliminar artículos existentes\n• **📊 Stock**: Actualizar cantidades\n• **💰 Precio**: Cambiar precios\n• **📋 Ver Todo**: Revisar todo el inventario",
            inline=False
        )
        embed.set_footer(text="Usa el menú desplegable para comenzar")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    

    return coins_system