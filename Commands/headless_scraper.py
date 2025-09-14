"""
Comando de scraping headless optimizado para hosting web
Alternativa a /scrape que funciona sin VNC usando solo modo headless
"""
import discord
from discord.ext import commands
import logging
import asyncio
import time
from datetime import datetime
import json
from pathlib import Path
import random

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Configurar comando de scraping headless"""

    @bot.tree.command(name="headscrape", description="Obtener servidores VIP usando scraping headless (sin VNC)")
    async def headscrape_command(
        interaction: discord.Interaction,
        juego: str,
        cantidad: int = 3
    ):
        """
        Comando de scraping headless optimizado para hosting web

        Args:
            juego: Nombre o ID del juego de Roblox
            cantidad: Cantidad de servidores a obtener (1-5, default: 3)
        """
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        # Defer la respuesta inmediatamente para evitar timeouts
        await interaction.response.defer(ephemeral=True)

        # Obtener referencias globales desde el bot
        import main
        scraper = main.scraper
        roblox_verification = main.roblox_verification

        # Verificar si está baneado
        if roblox_verification.is_user_banned(user_id):
            embed = discord.Embed(
                title="🚫 Usuario Baneado",
                description="Estás baneado y no puedes usar comandos del bot.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Verificar si está verificado
        if not roblox_verification.is_user_verified(user_id):
            embed = discord.Embed(
                title="🔒 Verificación Requerida",
                description="Debes verificarte para usar este comando.",
                color=0xffaa00
            )
            embed.add_field(
                name="📝 Cómo verificarse:",
                value="Usa `/verify [tu_nombre_roblox]` para verificarte",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        try:
            # Validar cantidad
            if cantidad < 1 or cantidad > 5:
                embed = discord.Embed(
                    title="❌ Cantidad Inválida",
                    description="La cantidad debe estar entre 1 y 5 servidores.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Verificar cooldown
            cooldown_remaining = scraper.check_cooldown(user_id, cooldown_minutes=2)
            if cooldown_remaining:
                minutes = cooldown_remaining // 60
                seconds = cooldown_remaining % 60

                embed = discord.Embed(
                    title="⏰ Cooldown Activo",
                    description=f"Debes esperar **{minutes}m {seconds}s** antes de usar headless scrape nuevamente.",
                    color=0xffaa00
                )
                embed.add_field(
                    name="💡 Ventajas del Headless Scrape:",
                    value="• Más rápido que scraping normal\n• Optimizado para hosting web\n• No requiere VNC\n• Menor uso de recursos",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Buscar juego
            if juego.isdigit():
                game_id = juego
                game_name = f"Juego ID {game_id}"
            else:
                # Usar la función de búsqueda del scraper
                search_results = await scraper.search_game_by_name(juego)
                if not search_results:
                    embed = discord.Embed(
                        title="❌ Juego No Encontrado",
                        description=f"No se encontró ningún juego con el nombre **{juego}**.",
                        color=0xff0000
                    )
                    embed.add_field(
                        name="💡 Sugerencias:",
                        value="• Usa el ID del juego directamente\n• Prueba con nombres más comunes\n• Verifica la ortografía",
                        inline=False
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return

                best_match = search_results[0]
                game_id = best_match['id']
                game_name = best_match['name']

            # Activar cooldown
            scraper.set_cooldown(user_id)

            # Mensaje inicial
            start_embed = discord.Embed(
                title="🚀 Headless Scrape Iniciado",
                description=f"Iniciando scraping headless para **{game_name}** (ID: {game_id})",
                color=0x00aaff
            )
            start_embed.add_field(name="🎯 Juego", value=f"```{game_name}```", inline=True)
            start_embed.add_field(name="📊 Cantidad", value=f"```{cantidad} servidores```", inline=True)
            start_embed.add_field(name="⚡ Modo", value="```Headless (Sin VNC)```", inline=True)
            start_embed.add_field(
                name="🔧 Optimizaciones:",
                value="• Modo headless forzado\n• Timeouts reducidos\n• Procesamiento rápido\n• Recursos mínimos",
                inline=False
            )
            start_embed.set_footer(text="⏱️ Tiempo estimado: 30-60 segundos")

            message = await interaction.followup.send(embed=start_embed, ephemeral=True)

            # Ejecutar scraping headless
            result = await execute_headless_scraping(
                game_id=game_id,
                game_name=game_name,
                user_id=user_id,
                target_amount=cantidad,
                message=message
            )

            if result['success'] and result['servers']:
                # Mostrar resultados exitosos
                success_embed = discord.Embed(
                    title="✅ Headless Scrape Completado",
                    description=f"Se obtuvieron **{len(result['servers'])}** servidores usando scraping headless.",
                    color=0x00ff88
                )

                # Mostrar servidores encontrados
                servers_text = ""
                for i, server in enumerate(result['servers'][:5], 1):
                    servers_text += f"`{i}.` {server}\n"

                if servers_text:
                    success_embed.add_field(
                        name="🔗 Servidores VIP Obtenidos:",
                        value=servers_text,
                        inline=False
                    )

                success_embed.add_field(name="⏱️ Tiempo total", value=f"{result['duration']:.1f}s", inline=True)
                success_embed.add_field(name="🚀 Método", value="Headless", inline=True)
                success_embed.add_field(name="💾 Guardado", value="Automático", inline=True)
                success_embed.add_field(
                    name="💡 Próximos pasos:",
                    value="• Usa `/servertest` para ver tus servidores\n• Los enlaces están guardados en tu perfil\n• Copia y pega en tu navegador",
                    inline=False
                )

                await message.edit(embed=success_embed)

                # Log exitoso
                logger.info(f"✅ Headless scrape exitoso para {username}: {len(result['servers'])} servidores de {game_name}")

            else:
                # Error o sin resultados
                error_embed = discord.Embed(
                    title="❌ Headless Scrape Sin Resultados",
                    description=result.get('error', 'No se pudieron obtener servidores VIP'),
                    color=0xff9900
                )
                error_embed.add_field(
                    name="🔄 Posibles causas:",
                    value="• No hay servidores VIP activos\n• El juego no tiene servidores disponibles\n• Problema temporal del sitio",
                    inline=False
                )
                error_embed.add_field(
                    name="💡 Alternativas:",
                    value="• Prueba con otro juego\n• Usa `/scrape` tradicional\n• Intenta más tarde",
                    inline=False
                )

                await message.edit(embed=error_embed)

        except Exception as e:
            logger.error(f"❌ Error en comando headscrape para {username}: {e}")

            error_embed = discord.Embed(
                title="❌ Error en Headless Scrape",
                description="Ocurrió un error durante el scraping headless.",
                color=0xff0000
            )
            error_embed.add_field(
                name="🔄 Soluciones:",
                value="• Intenta nuevamente en unos minutos\n• Usa `/scrape` como alternativa\n• Reporta si el problema persiste",
                inline=False
            )

            try:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                pass

async def execute_headless_scraping(game_id: str, game_name: str, user_id: str, target_amount: int, message: discord.WebhookMessage):
    """
    Ejecutar scraping completamente en modo headless
    """
    from main import scraper

    start_time = time.time()

    try:
        logger.info(f"🚀 Iniciando headless scraping para usuario {user_id}: {target_amount} servidores de juego {game_id}")

        # Configurar scraper para usuario actual
        scraper.current_user_id = user_id

        # Actualizar progreso: Obteniendo enlaces de servidores
        progress_embed = discord.Embed(
            title="🔄 Headless Scrape en Progreso",
            description=f"**Paso 1/3:** Obteniendo enlaces de servidores para {game_name}",
            color=0xffaa00
        )
        progress_embed.add_field(name="🎯 Juego", value=f"```{game_name}```", inline=True)
        progress_embed.add_field(name="⚡ Modo", value="```Headless```", inline=True)
        progress_embed.add_field(name="📊 Estado", value="```Buscando servidores...```", inline=True)

        try:
            await message.edit(embed=progress_embed)
        except Exception as edit_error:
            logger.debug(f"Error actualizando mensaje (ignorado): {edit_error}")
            # Continuar sin actualizar mensaje

        # Crear driver completamente headless sin VNC
        driver = create_headless_driver()

        if not driver:
            return {
                'success': False,
                'error': 'No se pudo inicializar el navegador headless',
                'servers': [],
                'duration': time.time() - start_time
            }

        try:
            # Obtener enlaces de servidores con método headless puro
            server_links = get_server_links_headless(driver, game_id)

            if not server_links:
                return {
                    'success': False,
                    'error': f'No se encontraron servidores para el juego {game_name}',
                    'servers': [],
                    'duration': time.time() - start_time
                }

            # Limitar cantidad de servidores a procesar
            server_links = server_links[:min(target_amount + 2, 7)]  # Procesar algunos extra por si fallan

            logger.info(f"📊 Procesando {len(server_links)} enlaces de servidores en modo headless")

            # Actualizar progreso: Extrayendo VIP links
            progress_embed.description = f"**Paso 2/3:** Extrayendo VIP links de {len(server_links)} servidores"
            try:
                await message.edit(embed=progress_embed)
            except Exception as edit_error:
                logger.debug(f"Error actualizando mensaje (ignorado): {edit_error}")
                # Continuar sin actualizar mensaje


            extracted_links = []
            processed_count = 0

            # Procesar enlaces con timeout reducido
            for server_url in server_links:
                if len(extracted_links) >= target_amount:
                    break

                try:
                    # Extracción VIP headless pura
                    vip_link = extract_vip_link_headless(driver, server_url, game_id)

                    if vip_link and vip_link not in extracted_links:
                        extracted_links.append(vip_link)
                        logger.info(f"✅ VIP link extraído: {len(extracted_links)}/{target_amount}")

                    processed_count += 1

                    # Actualizar progreso cada 2 servidores
                    if processed_count % 2 == 0:
                        progress_embed.description = f"**Paso 2/3:** Procesados {processed_count}/{len(server_links)} servidores - Encontrados {len(extracted_links)}"
                        try:
                            await message.edit(embed=progress_embed)
                        except Exception as edit_error:
                            logger.debug(f"Error actualizando mensaje (ignorado): {edit_error}")
                            # Continuar sin actualizar mensaje


                    # Pausa mínima entre requests
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"⚠️ Error procesando servidor {server_url}: {e}")
                    continue

        finally:
            # Cerrar driver
            try:
                driver.quit()
            except:
                pass

        # Actualizar progreso: Guardando resultados
        progress_embed.description = f"**Paso 3/3:** Guardando {len(extracted_links)} servidores VIP"
        progress_embed.set_field_at(2, name="📊 Estado", value="```Guardando...```", inline=True)

        try:
            await message.edit(embed=progress_embed)
        except Exception as edit_error:
            logger.debug(f"Error actualizando mensaje final (ignorado): {edit_error}")
            # Continuar sin actualizar mensaje


        # Guardar servidores si se encontraron
        if extracted_links:
            save_success = scraper.save_servers_directly_to_new_format(user_id, extracted_links)

            if not save_success:
                logger.warning(f"⚠️ No se pudieron guardar los servidores para usuario {user_id}")

        total_duration = time.time() - start_time

        logger.info(f"✅ Headless scraping completado: {len(extracted_links)} servidores en {total_duration:.1f}s")

        return {
            'success': True,
            'servers': extracted_links,
            'duration': total_duration,
            'processed': processed_count
        }

    except Exception as e:
        logger.error(f"❌ Error crítico en headless scraping: {e}")
        return {
            'success': False,
            'error': f'Error durante el scraping headless: {str(e)}',
            'servers': [],
            'duration': time.time() - start_time
        }

def get_server_links_headless(driver, game_id, max_retries=2):
    """Obtener enlaces de servidores en modo headless puro"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    
    url = f"https://rbxservers.xyz/games/{game_id}"
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔍 Obteniendo enlaces de servidores headless (intento {attempt + 1}/{max_retries})")
            
            driver.get(url)
            
            # Wait reducido para hosting web
            wait = WebDriverWait(driver, 10)  # Reducido de 20 a 10
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/servers/']")))
            
            server_elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/servers/']")
            server_links = []
            
            for el in server_elements:
                link = el.get_attribute("href")
                if link and link not in server_links:
                    server_links.append(link)
            
            logger.info(f"✅ Encontrados {len(server_links)} enlaces de servidores (headless)")
            return server_links
            
        except TimeoutException:
            logger.warning(f"⏰ Timeout headless en intento {attempt + 1}")
            if attempt == max_retries - 1:
                logger.error("❌ Todos los intentos headless fallaron")
                return []
            await asyncio.sleep(2)
        except WebDriverException as e:
            logger.error(f"🚫 Error WebDriver headless en intento {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return []
            await asyncio.sleep(2)
    
    return []

def extract_vip_link_headless(driver, server_url, game_id):
    """Extraer VIP link en modo headless puro"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    
    try:
        driver.get(server_url)
        
        # Wait reducido para hosting web
        wait = WebDriverWait(driver, 10)  # Reducido de 15 a 10
        vip_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@type='text' and contains(@value, 'https://')]")
            )
        )
        
        vip_link = vip_input.get_attribute("value")
        if vip_link and vip_link.startswith("https://"):
            logger.debug(f"✅ VIP link extraído headless: {vip_link[:50]}...")
            return vip_link
            
    except TimeoutException:
        logger.debug(f"⏰ No VIP link encontrado headless en {server_url}")
    except Exception as e:
        logger.debug(f"❌ Error extrayendo VIP link headless: {e}")
    
    return None

def create_headless_driver():
    """Crear driver Chrome completamente headless para hosting web sin VNC"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from pathlib import Path
        
        logger.info("🚀 Creando driver Chrome headless puro (sin VNC)")
        
        chrome_options = Options()
        
        # CONFIGURACIÓN HEADLESS FORZADA (sin VNC)
        chrome_options.add_argument("--headless=new")  # Nuevo modo headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--virtual-time-budget=5000")  # Optimización para headless
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # Configuración adicional para hosting web
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-background-networking")
        
        # Deshabilitar imágenes para velocidad
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.cookies": 1,
            "profile.managed_default_content_settings.javascript": 1,
            "profile.managed_default_content_settings.plugins": 2,
            "profile.managed_default_content_settings.popups": 2,
            "profile.managed_default_content_settings.geolocation": 2,
            "profile.managed_default_content_settings.media_stream": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Buscar binario de Chrome para hosting web
        possible_chrome_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser", 
            "/usr/bin/chromium",
            "/snap/bin/chromium",
            "/opt/google/chrome/chrome"
        ]
        
        chrome_binary = None
        for path in possible_chrome_paths:
            if Path(path).exists():
                chrome_binary = path
                break
        
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
            logger.info(f"🔧 Usando Chrome binary: {chrome_binary}")
        
        # Crear driver con configuración mínima y robusta
        try:
            # Intento 1: Driver básico
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("✅ Driver headless creado exitosamente")
        except Exception as e:
            logger.warning(f"⚠️ Intento básico falló: {e}")
            
            # Intento 2: Configuración ultra-mínima
            minimal_options = Options()
            minimal_options.add_argument("--headless=new")
            minimal_options.add_argument("--no-sandbox")
            minimal_options.add_argument("--disable-dev-shm-usage")
            minimal_options.add_argument("--disable-gpu")
            
            driver = webdriver.Chrome(options=minimal_options)
            logger.info("✅ Driver headless creado con configuración mínima")
        
        # Configuración de timeouts optimizada para hosting web
        driver.set_page_load_timeout(20)  # Reducido de 30 a 20
        driver.implicitly_wait(5)  # Reducido de 10 a 5
        
        # Ocultar propiedades de webdriver
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.debug(f"No se pudo ocultar webdriver property: {e}")
        
        logger.info("✅ Driver Chrome headless puro listo (sin VNC)")
        return driver
        
    except Exception as e:
        logger.error(f"❌ Error creando driver headless: {e}")
        raise Exception(f"Falló la creación del driver headless: {e}")

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass