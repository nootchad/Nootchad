"""
Comando /ownerscrape - Owner only
Comando para hacer scraping y enviar datos a API externa
"""
import discord
from discord.ext import commands
import logging
import asyncio
import aiohttp
import json
import time
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Configurar comando owner scrape"""

    @bot.tree.command(name="ownerscrape", description="[OWNER ONLY] Hacer scraping y enviar datos a API externa")
    async def ownerscrape_command(
        interaction: discord.Interaction,
        cantidad: int,
        game_id: str,
        api_url: str = "https://v0-discord-bot-api-snowy.vercel.app/api/data"
    ):
        """
        Comando owner para scraping y envío a API externa

        Args:
            cantidad: Cantidad de servidores a obtener
            game_id: ID del juego de Roblox
            api_url: URL de la API donde enviar los datos
        """
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        # Importar módulos necesarios
        from main import check_verification, scraper, roblox_verification, DISCORD_OWNER_ID, delegated_owners

        # Verificar que sea owner
        if user_id != DISCORD_OWNER_ID and user_id not in delegated_owners:
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando es solo para owners del bot.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Defer response
        await interaction.response.defer(ephemeral=True)

        try:
            # Validar parámetros
            if cantidad <= 0 or cantidad > 50:
                embed = discord.Embed(
                    title="❌ Cantidad Inválida",
                    description="La cantidad debe estar entre 1 y 50 servidores.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Validar formato de game_id
            if not game_id.isdigit():
                embed = discord.Embed(
                    title="❌ ID de Juego Inválido",
                    description="El ID del juego debe ser un número válido.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Validar URL de API
            if not api_url.startswith(('http://', 'https://')):
                embed = discord.Embed(
                    title="❌ URL de API Inválida",
                    description="La URL debe comenzar con http:// o https://",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Obtener información del juego
            game_info = await get_game_info(game_id)
            game_name = game_info.get('name', f'Juego {game_id}')

            # Información inicial
            initial_embed = discord.Embed(
                title="🔄 Owner Scrape Iniciado",
                description=f"Iniciando scraping de **{cantidad}** servidores para envío a API externa.",
                color=0x3366ff
            )
            initial_embed.add_field(name="🎮 Juego", value=f"```{game_name}```", inline=True)
            initial_embed.add_field(name="🆔 ID", value=f"```{game_id}```", inline=True)
            initial_embed.add_field(name="📊 Cantidad", value=f"```{cantidad}```", inline=True)
            initial_embed.add_field(name="🌐 API URL", value=f"```{api_url[:50]}...```", inline=False)
            initial_embed.add_field(name="⏱️ Estado", value="Iniciando scraping...", inline=False)

            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            # Ejecutar scraping
            scraped_servers = await execute_owner_scrape(game_id, cantidad, interaction, message)

            if not scraped_servers:
                error_embed = discord.Embed(
                    title="❌ Error en Scraping",
                    description="No se pudieron obtener servidores del juego especificado.",
                    color=0xff0000
                )
                await message.edit(embed=error_embed)
                return

            # Preparar datos para API
            api_data = {
                "game_name": game_name,
                "game_id": game_id,
                "total_servers": len(scraped_servers),
                "scraped_at": datetime.now().isoformat(),
                "scraped_by": {
                    "user_id": user_id,
                    "username": username
                },
                "servers": scraped_servers
            }

            # Enviar a API externa
            success, response_data = await send_to_external_api(api_url, api_data)

            if success:
                # Éxito
                success_embed = discord.Embed(
                    title="✅ Owner Scrape Completado",
                    description=f"Se obtuvieron **{len(scraped_servers)}** servidores y se enviaron exitosamente a la API.",
                    color=0x00ff88
                )
                success_embed.add_field(name="🎮 Juego", value=game_name, inline=True)
                success_embed.add_field(name="📊 Servidores", value=str(len(scraped_servers)), inline=True)
                success_embed.add_field(name="🌐 API", value="✅ Enviado", inline=True)
                success_embed.add_field(
                    name="📋 Respuesta API",
                    value=f"```{str(response_data)[:100]}...```",
                    inline=False
                )
                success_embed.add_field(
                    name="🔗 Enlaces de Ejemplo",
                    value=f"```{scraped_servers[0][:50]}...```" if scraped_servers else "Sin servidores",
                    inline=False
                )

                await message.edit(embed=success_embed)

                # Log del owner scrape
                logger.info(f"Owner scrape completado por {username}: {len(scraped_servers)} servidores de {game_name} enviados a {api_url}")

            else:
                # Error enviando a API
                error_embed = discord.Embed(
                    title="⚠️ Scraping Exitoso - Error en API",
                    description=f"Se obtuvieron **{len(scraped_servers)}** servidores pero falló el envío a la API.",
                    color=0xffaa00
                )
                error_embed.add_field(name="🎮 Juego", value=game_name, inline=True)
                error_embed.add_field(name="📊 Servidores", value=str(len(scraped_servers)), inline=True)
                error_embed.add_field(name="🌐 API", value="❌ Error", inline=True)
                error_embed.add_field(
                    name="❌ Error API",
                    value=f"```{str(response_data)[:200]}...```",
                    inline=False
                )

                await message.edit(embed=error_embed)

        except Exception as e:
            logger.error(f"Error en comando ownerscrape: {e}")
            error_embed = discord.Embed(
                title="❌ Error Interno",
                description=f"Ocurrió un error durante el scraping.",
                color=0xff0000
            )
            error_embed.add_field(name="🐛 Error", value=f"```{str(e)[:150]}{'...' if len(str(e)) > 150 else ''}```", inline=False)
            error_embed.add_field(name="💡 Sugerencia", value="Verifica las cookies y la conexión a internet", inline=False)
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("✅ Comando /ownerscrape registrado correctamente")
    return True


async def execute_owner_scrape(game_id: str, cantidad: int, interaction: discord.Interaction, message: discord.WebhookMessage):
    """Ejecutar el scraping para owner"""
    from main import scraper

    try:
        logger.info(f"🔄 Iniciando owner scrape para juego {game_id}: {cantidad} servidores")

        # Actualizar progreso
        progress_embed = discord.Embed(
            title="🔄 Owner Scrape en Progreso",
            description=f"Ejecutando scraping para **{cantidad}** servidores...",
            color=0xffaa00
        )
        progress_embed.add_field(name="📊 Estado", value="Obteniendo enlaces de servidores...", inline=False)

        try:
            await message.edit(embed=progress_embed)
        except:
            pass

        # Usar un user_id temporal para el owner scrape
        temp_user_id = "owner_scrape_temp"
        scraper.current_user_id = temp_user_id

        # Inicializar WebDriver
        driver = scraper.create_driver()

        try:
            # Obtener enlaces de servidores
            server_links = scraper.get_server_links(driver, game_id)

            # Limitar a la cantidad solicitada
            server_links = server_links[:cantidad * 2]  # Obtener más para compensar fallos

            logger.info(f"🎯 Procesando {len(server_links)} enlaces de servidores...")

            # Actualizar progreso
            progress_embed.set_field_at(0, name="📊 Estado", value=f"Procesando {len(server_links)} enlaces...", inline=False)
            try:
                await message.edit(embed=progress_embed)
            except:
                pass

            extracted_servers = []
            processed = 0

            for server_url in server_links:
                if len(extracted_servers) >= cantidad:
                    break

                try:
                    # Extraer enlace VIP
                    vip_link = scraper.extract_vip_link(driver, server_url, game_id)
                    if vip_link:
                        extracted_servers.append(vip_link)
                        processed += 1

                        # Actualizar progreso cada 5 servidores
                        if processed % 5 == 0:
                            progress_embed.set_field_at(
                                0, 
                                name="📊 Estado", 
                                value=f"Obtenidos: {len(extracted_servers)}/{cantidad} servidores...", 
                                inline=False
                            )
                            try:
                                await message.edit(embed=progress_embed)
                            except:
                                pass

                except Exception as e:
                    logger.error(f"❌ Error procesando {server_url}: {e}")
                    continue

        finally:
            # Cerrar WebDriver
            if driver:
                driver.quit()

        # Limpiar datos temporales
        if temp_user_id in scraper.links_by_user:
            del scraper.links_by_user[temp_user_id]

        logger.info(f"✅ Owner scrape completado: {len(extracted_servers)} servidores extraídos")
        return extracted_servers

    except Exception as e:
        logger.error(f"❌ Error crítico en owner scrape: {e}")
        return []

async def send_to_external_api(api_url: str, data: dict):
    """Enviar datos a API externa usando requests"""
    try:
        import requests

        logger.info(f"🌐 Enviando datos a API: {api_url}")

        # Usar la URL por defecto si no se especifica otra
        if api_url == "https://example-api.com/receive-servers":
            api_url = "https://v0-discord-bot-api-snowy.vercel.app/api/data"

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'RbxServers-OwnerScrape/1.0'
        }

        # Ejecutar en un hilo separado para evitar bloquear el loop asyncio
        import asyncio
        import functools

        def sync_request():
            return requests.post(
                api_url,
                json=data,
                headers=headers,
                timeout=30
            )

        # Ejecutar la petición síncrona en un executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, sync_request)

        if response.status_code == 200:
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}

            logger.info(f"✅ API responded successfully: {response.status_code}")
            return True, response_data
        else:
            logger.error(f"❌ API responded with error: {response.status_code} - {response.text}")
            return False, {"error": f"HTTP {response.status_code}", "response": response.text}

    except requests.Timeout:
        logger.error(f"❌ Timeout sending to API: {api_url}")
        return False, {"error": "Timeout", "message": "La API no respondió en 30 segundos"}
    except Exception as e:
        logger.error(f"❌ Error sending to API: {e}")
        return False, {"error": str(e), "type": type(e).__name__}

async def get_game_info(game_id: str):
    """Obtener información del juego desde la API de Roblox"""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://games.roblox.com/v1/games?universeIds={game_id}"

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    games = data.get('data', [])
                    if games:
                        return games[0]
    except Exception as e:
        logger.error(f"Error obtaining game info {game_id}: {e}")

    return {"name": f"Juego {game_id}", "id": game_id}

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass