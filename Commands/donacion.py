
"""
Comando /donacion para verificar si un usuario tiene el gamepass de donación
y enviar mensaje de agradecimiento
"""
import discord
from discord.ext import commands
import logging
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

# ID del gamepass de donación
DONATION_GAMEPASS_ID = "1328319614"

def setup_commands(bot):
    """Función requerida para configurar comandos"""
    
    @bot.tree.command(name="donacion", description="Verificar si has donado mediante gamepass y recibir agradecimiento")
    async def donacion_command(interaction: discord.Interaction):
        """Verificar gamepass de donación del usuario"""
        try:
            # Verificar que el usuario esté verificado en Roblox
            from main import roblox_verification
            
            user_id = str(interaction.user.id)
            username = f"{interaction.user.name}#{interaction.user.discriminator}"
            
            logger.info(f"Usuario {username} (ID: {user_id}) usó comando /donacion")
            
            # Defer la respuesta porque puede tomar tiempo verificar la API
            await interaction.response.defer()
            
            # Verificar si el usuario está verificado
            if not roblox_verification.is_user_verified(user_id):
                embed = discord.Embed(
                    title="Verificación Requerida",
                    description="Necesitas estar verificado con tu cuenta de Roblox para usar este comando.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="Como verificarte",
                    value="Usa el comando `/verify nombre_roblox` para verificar tu cuenta",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Obtener información del usuario verificado
            user_data = roblox_verification.verified_users.get(user_id)
            roblox_username = user_data['roblox_username']
            
            logger.info(f"Verificando donación para usuario Roblox: {roblox_username}")
            
            # Obtener el ID de usuario de Roblox
            roblox_user_id = await get_roblox_user_id(roblox_username)
            
            if not roblox_user_id:
                embed = discord.Embed(
                    title="Error de Verificación",
                    description="No se pudo obtener la información de tu cuenta de Roblox. Intenta verificarte nuevamente.",
                    color=0x5c5c5c
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Verificar si tiene el gamepass de donación
            has_gamepass = await check_user_has_gamepass(roblox_user_id, DONATION_GAMEPASS_ID)
            
            if has_gamepass is None:
                # Error al verificar gamepass
                embed = discord.Embed(
                    title="Error de Verificación",
                    description="No se pudo verificar tu estado de donación en este momento. Intenta nuevamente más tarde.",
                    color=0x5c5c5c
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            if has_gamepass:
                # Usuario tiene el gamepass - enviar mensaje de agradecimiento
                embed = discord.Embed(
                    title="Gracias por tu Donación",
                    description=f"Hemos verificado que {roblox_username} ha donado al proyecto mediante gamepass.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="Usuario Roblox",
                    value=roblox_username,
                    inline=True
                )
                embed.add_field(
                    name="Estado de Donación",
                    value="Confirmado",
                    inline=True
                )
                embed.add_field(
                    name="Agradecimiento",
                    value="Tu apoyo es fundamental para mantener y mejorar RbxServers. Gracias por contribuir al desarrollo del bot.",
                    inline=False
                )
                embed.add_field(
                    name="Beneficios",
                    value="Como donador, tu apoyo nos permite seguir proporcionando servidores VIP gratuitos para toda la comunidad.",
                    inline=False
                )
                
                # Enviar mensaje público de agradecimiento
                await interaction.followup.send(embed=embed, ephemeral=False)
                
                # Log del donador
                logger.info(f"DONACIÓN CONFIRMADA: Usuario {username} (Roblox: {roblox_username}) tiene gamepass {DONATION_GAMEPASS_ID}")
                
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
                    title="Donación No Detectada",
                    description=f"No se detectó el gamepass de donación en la cuenta {roblox_username}.",
                    color=0x5c5c5c
                )
                embed.add_field(
                    name="Como Donar",
                    value=f"Puedes donar adquiriendo el gamepass con ID: {DONATION_GAMEPASS_ID}",
                    inline=False
                )
                embed.add_field(
                    name="Información",
                    value="Una vez que adquieras el gamepass, podrás usar este comando nuevamente para recibir el reconocimiento.",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed, ephemeral=True)
                logger.info(f"Usuario {username} (Roblox: {roblox_username}) no tiene gamepass de donación")
        
        except Exception as e:
            logger.error(f"Error en comando /donacion: {e}")
            
            error_embed = discord.Embed(
                title="Error",
                description="Ocurrió un error al verificar tu donación. Intenta nuevamente en unos momentos.",
                color=0x5c5c5c
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
    """Verificar si un usuario tiene un gamepass específico"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://inventory.roblox.com/v1/users/{user_id}/items/GamePass/0"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            params = {
                "limit": 100,  # Obtener hasta 100 gamepasses
                "sortOrder": "Desc"
            }
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    gamepasses = data.get("data", [])
                    
                    # Buscar el gamepass específico
                    for gamepass in gamepasses:
                        asset_id = str(gamepass.get("assetId", ""))
                        if asset_id == gamepass_id:
                            logger.info(f"Usuario {user_id} TIENE gamepass {gamepass_id}")
                            return True
                    
                    logger.info(f"Usuario {user_id} NO tiene gamepass {gamepass_id}")
                    return False
                
                elif response.status == 404:
                    # Usuario no encontrado o sin gamepasses
                    logger.info(f"Usuario {user_id} no encontrado o sin gamepasses")
                    return False
                
                else:
                    logger.warning(f"Error verificando gamepass para usuario {user_id}: status {response.status}")
                    return None
    
    except Exception as e:
        logger.error(f"Error verificando gamepass: {e}")
        return None

logger.info("✅ Comando /donacion configurado exitosamente")
return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    pass
