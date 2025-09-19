
"""
Comando /donacion para verificar si un usuario tiene el gamepass de donación
y enviar mensaje de agradecimiento
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio
import json
import os

logger = logging.getLogger(__name__)

# ID del gamepass de donación
DONATION_GAMEPASS_ID = "1328319614"

# Archivo para almacenar donadores verificados
DONATORS_FILE = "verified_donators.json"

def load_donators():
    """Cargar lista de donadores verificados"""
    if os.path.exists(DONATORS_FILE):
        try:
            with open(DONATORS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando donadores: {e}")
    return {}

def save_donators(donators):
    """Guardar lista de donadores verificados"""
    try:
        with open(DONATORS_FILE, 'w', encoding='utf-8') as f:
            json.dump(donators, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando donadores: {e}")

def is_user_donator(user_id: str) -> bool:
    """Verificar si un usuario es donador verificado"""
    donators = load_donators()
    return user_id in donators

def add_donator(user_id: str, roblox_username: str, roblox_id: str):
    """Agregar un donador verificado"""
    donators = load_donators()
    donators[user_id] = {
        'roblox_username': roblox_username,
        'roblox_id': roblox_id,
        'verified_at': asyncio.get_event_loop().time()
    }
    save_donators(donators)

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="donacion", description="Verificar si has donado mediante gamepass (sin necesidad de verificación previa)")
    async def donacion_command(interaction: discord.Interaction, roblox_username: str):
        """Verificar gamepass de donación del usuario"""
        try:
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            logger.info(f"Usuario {username} (ID: {user_id}) usó comando /donacion con username: {roblox_username}")
            
            # Defer la respuesta porque puede tomar tiempo verificar la API
            await interaction.response.defer()
            
            # Verificar si ya es donador conocido
            if is_user_donator(user_id):
                donators = load_donators()
                donator_data = donators[user_id]
                embed = discord.Embed(
                    title="<a:verify2:1418486831993061497> Donador Verificado",
                    description=f"Ya tienes el estado de donador verificado con la cuenta **{donator_data['roblox_username']}**.",
                    color=0x00ff00
                )
                embed.add_field(
                    name="🎁 Beneficios Activos",
                    value="• 50 usos diarios en `/publicget`\n• Reconocimiento como donador\n• Apoyas el desarrollo del bot",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            logger.info(f"Verificando donación para usuario Roblox: {roblox_username} (Discord ID: {user_id})")
            
            # Obtener el ID de usuario de Roblox
            roblox_user_id = await get_roblox_user_id(roblox_username)
            
            if not roblox_user_id:
                embed = discord.Embed(
                    title="❌ Usuario No Encontrado",
                    description=f"No se pudo encontrar el usuario **{roblox_username}** en Roblox.",
                    color=0xff0000
                )
                embed.add_field(
                    name="<a:foco:1418492184373755966> Verificaciones",
                    value="• Asegúrate de escribir el username correctamente\n• Verifica que la cuenta no esté baneada\n• Intenta nuevamente en unos momentos",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si tiene el gamepass de donación
            has_gamepass = await check_user_has_gamepass(roblox_user_id, DONATION_GAMEPASS_ID)
            
            if has_gamepass is None:
                # Error al verificar gamepass - proporcionar más información
                embed = discord.Embed(
                    title="⚠️ Error de Verificación",
                    description="No se pudo verificar tu estado de donación debido a problemas con la API de Roblox.",
                    color=0xff9900
                )
                embed.add_field(
                    name="🔍 Información Técnica",
                    value=f"• Usuario Roblox: {roblox_username}\n• ID Usuario: {roblox_user_id}\n• Gamepass ID: {DONATION_GAMEPASS_ID}",
                    inline=False
                )
                embed.add_field(
                    name="<a:loading:1418504453580918856> Posibles Soluciones",
                    value="• Intenta nuevamente en 1-2 minutos\n• Verifica que tu perfil de Roblox no sea privado\n• Contacta soporte si el problema persiste",
                    inline=False
                )
                embed.add_field(
                    name="🛠️ Estado de APIs",
                    value="Las APIs de Roblox pueden estar experimentando problemas temporales",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                logger.warning(f"Error de API verificando donación para usuario {username} (Roblox: {roblox_username}, ID: {roblox_user_id})")
                return
            
            if has_gamepass:
                # Usuario tiene el gamepass - agregarlo a la lista de donadores y enviar mensaje de agradecimiento
                add_donator(user_id, roblox_username, roblox_user_id)
                
                embed = discord.Embed(
                    title="🎉 ¡Gracias por tu Donación!",
                    description=f"¡Hemos verificado que **{roblox_username}** ha donado al proyecto mediante gamepass!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="<:1000182614:1396049500375875646> Usuario Roblox",
                    value=f"[{roblox_username}](https://www.roblox.com/users/{roblox_user_id}/profile)",
                    inline=True
                )
                embed.add_field(
                    name="<a:verify2:1418486831993061497> Estado de Donación",
                    value="**CONFIRMADO**",
                    inline=True
                )
                embed.add_field(
                    name="🆔 ID de Roblox",
                    value=f"`{roblox_user_id}`",
                    inline=True
                )
                embed.add_field(
                    name="🙏 Agradecimiento",
                    value="Tu apoyo es fundamental para mantener y mejorar RbxServers. ¡Gracias por contribuir al desarrollo del bot!",
                    inline=False
                )
                embed.add_field(
                    name="🎁 Beneficios Obtenidos",
                    value="• **50 usos diarios** en `/publicget` (en lugar de 10)\n• Reconocimiento público como donador\n• Apoyas el desarrollo continuo del bot",
                    inline=False
                )
                embed.add_field(
                    name="💰 Bonus de Monedas",
                    value="¡Has recibido **500 monedas** bonus por tu donación!",
                    inline=False
                )
                
                # Enviar mensaje público de agradecimiento
                await interaction.followup.send(embed=embed, ephemeral=False)
                
                # Log del donador
                logger.info(f"DONACIÓN CONFIRMADA: Usuario {username} (Roblox: {roblox_username}, ID: {roblox_user_id}) tiene gamepass {DONATION_GAMEPASS_ID}")
                
                # Dar monedas bonus por donación (si el sistema está disponible)
                try:
                    import sys
                    if 'coins_system' in sys.modules:
                        coins_system = sys.modules['coins_system']
                        if hasattr(coins_system, 'add_coins'):
                            coins_system.add_coins(user_id, 500, "Bonus por donación verificada")
                            logger.info(f"Otorgadas 500 monedas bonus a donador {user_id}")
                except Exception as e:
                    logger.debug(f"Error agregando monedas bonus: {e}")
            
            else:
                # Usuario no tiene el gamepass
                embed = discord.Embed(
                    title="💝 Donación No Detectada",
                    description=f"No se detectó el gamepass de donación en la cuenta **{roblox_username}**.",
                    color=0xffa500
                )
                embed.add_field(
                    name="🎁 Como Donar",
                    value=f"Puedes apoyar el proyecto adquiriendo el gamepass de donación.\n\n**Gamepass ID:** `{DONATION_GAMEPASS_ID}`",
                    inline=False
                )
                embed.add_field(
                    name="🎯 Beneficios de Donar",
                    value="• **50 usos diarios** en `/publicget` (en lugar de 10)\n• Reconocimiento público como donador\n• Bonus de 500 monedas\n• Apoyas el desarrollo continuo del bot",
                    inline=False
                )
                embed.add_field(
                    name="<a:loading:1418504453580918856> Después de Donar",
                    value="Una vez que adquieras el gamepass, usa este comando nuevamente para recibir el reconocimiento y beneficios.",
                    inline=False
                )
                embed.add_field(
                    name="<:1000182614:1396049500375875646> Usuario Verificado",
                    value=f"[{roblox_username}](https://www.roblox.com/users/{roblox_user_id}/profile)",
                    inline=True
                )
                embed.add_field(
                    name="🆔 ID de Roblox",
                    value=f"`{roblox_user_id}`",
                    inline=True
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"Usuario {username} (Roblox: {roblox_username}) no tiene gamepass de donación")
        
        except Exception as e:
            logger.error(f"Error en comando /donacion: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error",
                description="Ocurrió un error al verificar tu donación. Intenta nuevamente en unos momentos.",
                color=0xff0000
            )
            
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

async def get_roblox_user_id(username: str):
    """Obtener ID de usuario de Roblox mediante username"""
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://users.roblox.com/v1/usernames/users"
            payload = {
                "usernames": [username],
                "excludeBannedUsers": True
            }
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        user_id = data["data"][0].get("id")
                        logger.info(f"ID de usuario Roblox para {username}: {user_id}")
                        return str(user_id)
                else:
                    logger.warning(f"Error obteniendo ID de usuario para {username}: status {response.status}")
                return None
    except Exception as e:
        logger.error(f"Error obteniendo ID de usuario Roblox: {e}")
        return None

async def check_user_has_gamepass(user_id: str, gamepass_id: str):
    """Verificar si un usuario tiene un gamepass específico usando múltiples métodos"""
    try:
        async with aiohttp.ClientSession() as session:
            # Método 1: API de catálogo más nueva
            url1 = f"https://catalog.roblox.com/v1/search/items"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            # Primero verificar si el gamepass existe
            params1 = {
                "category": "GamePass",
                "keyword": "",
                "limit": 1
            }
            
            try:
                # Método alternativo: usar API de ownership
                ownership_url = f"https://apis.roblox.com/ownership-api/v1/user/{user_id}/owns-asset?assetType=GamePass&assetId={gamepass_id}"
                
                logger.info(f"Verificando ownership para usuario {user_id} y gamepass {gamepass_id}")
                
                async with session.get(ownership_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        owns = data.get("owns", False)
                        logger.info(f"Usuario {user_id} {'TIENE' if owns else 'NO tiene'} gamepass {gamepass_id} (API ownership)")
                        return owns
                    else:
                        logger.warning(f"API ownership falló con status {response.status}")
            except Exception as ownership_error:
                logger.debug(f"Error con API ownership: {ownership_error}")
            
            # Método 2: API de inventario con mejor manejo
            try:
                inventory_url = f"https://inventory.roblox.com/v1/users/{user_id}/items/GamePass/{gamepass_id}"
                
                async with session.get(inventory_url, headers=headers, timeout=10) as response:
                    logger.info(f"API inventario respuesta: {response.status} para usuario {user_id}")
                    
                    if response.status == 200:
                        data = await response.json()
                        has_gamepass = data.get("data", [])
                        if has_gamepass:
                            logger.info(f"Usuario {user_id} TIENE gamepass {gamepass_id} (API inventario)")
                            return True
                        else:
                            logger.info(f"Usuario {user_id} NO tiene gamepass {gamepass_id} (API inventario)")
                            return False
                    elif response.status == 404:
                        logger.info(f"Usuario {user_id} NO tiene gamepass {gamepass_id} (404)")
                        return False
                    else:
                        logger.warning(f"API inventario falló: {response.status}")
            except Exception as inventory_error:
                logger.debug(f"Error con API inventario: {inventory_error}")
            
            # Método 3: API de collectibles (más genérica)
            try:
                collectibles_url = f"https://inventory.roblox.com/v1/users/{user_id}/items/0/{gamepass_id}"
                
                async with session.get(collectibles_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("data"):
                            logger.info(f"Usuario {user_id} TIENE gamepass {gamepass_id} (API collectibles)")
                            return True
                        else:
                            logger.info(f"Usuario {user_id} NO tiene gamepass {gamepass_id} (API collectibles)")
                            return False
                    elif response.status == 404:
                        return False
            except Exception as collectibles_error:
                logger.debug(f"Error con API collectibles: {collectibles_error}")
            
            # Si todos los métodos fallan, retornar None (error)
            logger.error(f"Todos los métodos de verificación fallaron para usuario {user_id}")
            return None
    
    except Exception as e:
        logger.error(f"Error crítico verificando gamepass: {e}")
        return None

    logger.info("✅ Comando /donacion configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
