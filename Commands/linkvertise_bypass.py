"""
Comando para bypassear enlaces de Linkvertise automáticamente
"""
import discord
from discord.ext import commands
import logging
import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

logger = logging.getLogger(__name__)

def setup_commands(bot):
    """Configurar comando de bypass de Linkvertise"""

    @bot.tree.command(name="linkvertise", description="Bypassear enlaces de Linkvertise automáticamente")
    async def linkvertise_command(
        interaction: discord.Interaction,
        url: str
    ):
        """
        Comando para bypassear Linkvertise

        Args:
            url: URL de Linkvertise a bypassear
        """
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"

        # Importar verificación desde main.py
        from main import check_verification

        # Verificar autenticación
        if not await check_verification(interaction, defer_response=True):
            return

        try:
            # Validar URL
            if not url.startswith('http'):
                url = f'https://{url}'

            if 'linkvertise.com' not in url.lower():
                embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> URL Inválida",
                    description="La URL debe ser de Linkvertise.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Embed inicial
            initial_embed = discord.Embed(
                title="🔗 Linkvertise Bypass",
                description=f"Iniciando bypass automático...",
                color=0x3366ff
            )
            initial_embed.add_field(name="🌐 URL:", value=f"```{url}```", inline=False)
            initial_embed.add_field(name="📊 Estado:", value="Inicializando navegador...", inline=True)
            initial_embed.add_field(name="⏱️ Tiempo:", value="0s", inline=True)

            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            # Ejecutar bypass
            result = await execute_linkvertise_bypass(url, message, username)

            if result['success']:
                # Éxito
                success_embed = discord.Embed(
                    title="<:verify:1396087763388072006> Bypass Completado",
                    description=f"URL final obtenida exitosamente.",
                    color=0x00ff88
                )
                success_embed.add_field(name="🔗 URL Final:", value=f"```{result['final_url']}```", inline=False)
                success_embed.add_field(name="<:1000182657:1396060091366637669> Tiempo total:", value=f"{result['duration']:.1f}s", inline=True)
                success_embed.add_field(name="<:1000182750:1396420537227411587> Pasos completados:", value=f"{result['steps_completed']}", inline=True)

                await message.edit(embed=success_embed)

            else:
                # Error
                error_embed = discord.Embed(
                    title="<:1000182563:1396420770904932372> Error en Bypass",
                    description=result['error'],
                    color=0xff0000
                )
                error_embed.add_field(name="🔍 Detalles:", value=result.get('details', 'Sin detalles adicionales'), inline=False)
                await message.edit(embed=error_embed)

        except Exception as e:
            logger.error(f"Error en comando linkvertise para {username}: {e}")
            embed = discord.Embed(
                title="<:1000182563:1396420770904932372> Error Interno",
                description="Ocurrió un error durante el bypass.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def execute_linkvertise_bypass(url: str, message: discord.WebhookMessage, username: str):
    """Ejecutar el proceso de bypass de Linkvertise"""
    start_time = time.time()
    steps_completed = 0
    driver = None

    try:
        logger.info(f"🔗 Iniciando bypass de Linkvertise para {username}: {url}")

        # Configurar Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Anti-detección
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        # Paso 1: Inicializar navegador
        await update_progress(message, "🌐 Inicializando navegador...", steps_completed, start_time)
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        steps_completed += 1
        await update_progress(message, "📂 Navegando a Linkvertise...", steps_completed, start_time)

        # Paso 2: Navegar a la URL
        driver.get(url)
        await asyncio.sleep(3)  # Esperar carga inicial

        steps_completed += 1
        await update_progress(message, "🔍 Buscando botón 'Free Access'...", steps_completed, start_time)

        # Paso 3: Buscar y hacer clic en "Get link"
        get_link_clicked = await find_and_click_free_access(driver)
        if not get_link_clicked:
            return {
                'success': False,
                'error': 'No se encontró el botón "Get link"',
                'details': 'El botón inicial "Get link" no está disponible o cambió su estructura',
                'duration': time.time() - start_time,
                'steps_completed': steps_completed
            }

        steps_completed += 1
        await update_progress(message, "<:1000182657:1396060091366637669> Esperando timer de anuncios...", steps_completed, start_time)

        # Paso 4: Esperar y buscar el botón Skip circular
        await asyncio.sleep(5)  # Esperar a que aparezcan los anuncios

        steps_completed += 1
        await update_progress(message, "<:1000182750:1396420537227411587> Buscando botón Skip circular...", steps_completed, start_time)

        # Paso 5: Encontrar y hacer clic en el botón Skip circular
        skip_clicked = await find_and_click_real_skip(driver)
        if not skip_clicked:
            return {
                'success': False,
                'error': 'No se encontró el botón Skip circular',
                'details': 'El botón skip circular no apareció o no se habilitó',
                'duration': time.time() - start_time,
                'steps_completed': steps_completed
            }

        steps_completed += 1
        await update_progress(message, "<:1000182657:1396060091366637669> Esperando proceso del sitio...", steps_completed, start_time)

        # Paso 6: Esperar proceso del sitio
        await asyncio.sleep(5)

        steps_completed += 1
        await update_progress(message, "<:1000182750:1396420537227411587> Buscando botón 'Get [nombre]'...", steps_completed, start_time)

        # Paso 7: Buscar y hacer clic en el botón "Get [nombre]"
        get_content_clicked = await find_and_click_get_button(driver)
        if not get_content_clicked:
            return {
                'success': False,
                'error': 'No se encontró el botón "Get [nombre]"',
                'details': 'El botón secundario Get no apareció después del skip',
                'duration': time.time() - start_time,
                'steps_completed': steps_completed
            }

        steps_completed += 1
        await update_progress(message, "<:1000182750:1396420537227411587> Buscando botón 'Open' final...", steps_completed, start_time)

        # Paso 8: Buscar y hacer clic en el botón "Open"
        open_clicked = await find_and_click_open_button(driver)
        if not open_clicked:
            return {
                'success': False,
                'error': 'No se encontró el botón "Open" final',
                'details': 'El botón Open final no apareció después del Get',
                'duration': time.time() - start_time,
                'steps_completed': steps_completed
            }

        steps_completed += 1
        await update_progress(message, "🔗 Obteniendo URL final...", steps_completed, start_time)

        # Paso 9: Obtener URL final
        final_url = driver.current_url

        logger.info(f"✅ URL final obtenida: {final_url}")
        print(f"🔗 URL FINAL: {final_url}")  # Imprimir en consola como se solicitó

        return {
            'success': True,
            'final_url': final_url,
            'duration': time.time() - start_time,
            'steps_completed': steps_completed
        }

    except Exception as e:
        logger.error(f"❌ Error en bypass de Linkvertise: {e}")
        return {
            'success': False,
            'error': f'Error durante el bypass: {str(e)}',
            'details': str(e),
            'duration': time.time() - start_time,
            'steps_completed': steps_completed
        }
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

async def find_and_click_free_access(driver):
    """Encontrar y hacer clic en el botón 'Get link' inicial"""
    try:
        wait = WebDriverWait(driver, 15)

        # Selectores específicos para el botón "Get link" inicial
        get_link_selectors = [
            # Selector específico por ID
            "//button[@id='get-link']",
            
            # Selector por clase y contenido
            "//button[contains(@class, 'btn-primary') and @id='get-link']",
            
            # Selector por atributo data-action
            "//button[@data-action='start-process']",
            
            # Selector por función onclick
            "//button[contains(@onclick, 'startLinkProcess')]",
            
            # Selector por texto "Get link"
            "//button[contains(text(), 'Get link')]",
            "//button[contains(text(), 'Get Link')]",
            
            # Selectores de respaldo
            "//button[contains(@class, 'btn-primary')]",
            "//button[@type='button' and contains(@class, 'btn-primary')]"
        ]

        for selector in get_link_selectors:
            try:
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                driver.execute_script("arguments[0].click();", element)
                logger.info(f"<:verify:1396087763388072006> Clic en 'Get link' exitoso con selector: {selector}")
                return True
            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue

        # Método alternativo: buscar por CSS selector
        try:
            css_selectors = [
                "#get-link",
                "button.btn-primary#get-link",
                "button[data-action='start-process']",
                "button.btn-primary"
            ]
            
            for css_selector in css_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, css_selector)
                    if element.is_displayed() and element.is_enabled():
                        driver.execute_script("arguments[0].click();", element)
                        logger.info(f"<:verify:1396087763388072006> Clic en 'Get link' exitoso con CSS: {css_selector}")
                        return True
                except:
                    continue
        except Exception as e:
            logger.debug(f"Error en método CSS alternativo: {e}")

        logger.warning("<:1000182563:1396420770904932372> No se encontró botón 'Get link'")
        return False

    except Exception as e:
        logger.error(f"Error buscando 'Get link': {e}")
        return False

async def find_and_click_real_skip(driver):
    """Encontrar y hacer clic en el botón Skip circular"""
    try:
        # Esperar hasta 30 segundos para que aparezca el botón skip y se habilite
        max_wait_time = 30
        start_wait = time.time()

        while time.time() - start_wait < max_wait_time:
            try:
                # Selectores específicos para el botón Skip circular de Linkvertise
                skip_button_selectors = [
                    # Selector específico por ID
                    "//button[@id='skip-ad']",
                    
                    # Selector por clases específicas
                    "//button[contains(@class, 'skip-btn') and contains(@class, 'circular')]",
                    
                    # Selector por atributo data-step
                    "//button[@data-step='1']",
                    
                    # Selector por data-timer
                    "//button[@data-timer='countdown']",
                    
                    # Selector por función onclick
                    "//button[contains(@onclick, 'skipAdvertisement')]",
                    
                    # Selectores CSS equivalentes
                    "#skip-ad",
                    "button.skip-btn.circular",
                    "button[data-step='1']",
                    "button[data-timer='countdown']"
                ]

                # Verificar cada selector XPath
                for selector in skip_button_selectors[:5]:  # Primeros 5 son XPath
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed():
                                # Verificar si el botón está habilitado (no disabled)
                                is_disabled = element.get_attribute("disabled")
                                if not is_disabled:
                                    # Hacer scroll al elemento
                                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                    await asyncio.sleep(1)

                                    # Hacer clic
                                    driver.execute_script("arguments[0].click();", element)
                                    logger.info(f"<:verify:1396087763388072006> Clic en Skip circular exitoso con selector: {selector}")
                                    return True
                                else:
                                    logger.debug(f"Botón Skip encontrado pero está deshabilitado: {selector}")
                    except Exception as e:
                        logger.debug(f"Error con selector XPath {selector}: {e}")
                        continue

                # Verificar selectores CSS
                for css_selector in skip_button_selectors[5:]:  # Últimos son CSS
                    try:
                        element = driver.find_element(By.CSS_SELECTOR, css_selector)
                        if element.is_displayed():
                            is_disabled = element.get_attribute("disabled")
                            if not is_disabled:
                                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                await asyncio.sleep(1)
                                driver.execute_script("arguments[0].click();", element)
                                logger.info(f"<:verify:1396087763388072006> Clic en Skip circular exitoso con CSS: {css_selector}")
                                return True
                            else:
                                logger.debug(f"Botón Skip encontrado pero está deshabilitado: {css_selector}")
                    except Exception as e:
                        logger.debug(f"Error con selector CSS {css_selector}: {e}")
                        continue

                # Si no se encuentra habilitado, esperar un poco más
                await asyncio.sleep(2)

            except Exception as e:
                logger.debug(f"Error en búsqueda de skip: {e}")
                await asyncio.sleep(2)

        logger.warning("<:1000182563:1396420770904932372> No se encontró botón Skip circular habilitado")
        return False

    except Exception as e:
        logger.error(f"Error buscando Skip circular: {e}")
        return False

def is_real_skip_button(element, driver):
    """Verificar si un botón skip es real (no falso)"""
    try:
        # Obtener información del elemento
        location = element.location
        size = element.size

        # Los botones skip reales típicamente:
        # 1. Están en la parte superior de la página (Y < 200)
        # 2. No están en banners grandes
        # 3. No tienen backgrounds oscuros/negros
        # 4. Tienen tamaño razonable (no muy grandes)

        # Verificar posición Y (arriba de la página)
        if location['y'] > 300:  # Si está muy abajo, probablemente es falso
            return False

        # Verificar tamaño (los botones falsos suelen ser muy grandes)
        if size['width'] > 400 or size['height'] > 100:
            return False

        # Verificar que no esté en un contenedor de anuncio
        parent_classes = driver.execute_script("""
            var element = arguments[0];
            var parent = element.parentElement;
            var classes = [];
            while (parent && classes.length < 5) {
                if (parent.className) {
                    classes.push(parent.className.toLowerCase());
                }
                parent = parent.parentElement;
            }
            return classes.join(' ');
        """, element)

        # Palabras que indican que es un anuncio falso
        false_indicators = ['ad', 'banner', 'popup', 'overlay', 'modal', 'fake']
        for indicator in false_indicators:
            if indicator in parent_classes.lower():
                return False

        # Verificar el texto del elemento
        element_text = element.text.strip().lower()
        if len(element_text) > 20:  # Texto muy largo, probablemente falso
            return False

        # Verificar color de fondo (evitar botones negros grandes)
        bg_color = driver.execute_script("""
            var style = window.getComputedStyle(arguments[0]);
            return style.backgroundColor;
        """, element)

        if 'rgb(0, 0, 0)' in bg_color or 'black' in bg_color.lower():
            return False

        logger.info(f"✅ Botón skip validado como real: posición Y={location['y']}, tamaño={size}, texto='{element_text}'")
        return True

    except Exception as e:
        logger.debug(f"Error validando botón skip: {e}")
        return True  # Si hay error en validación, intentar hacer clic de todos modos

async def find_and_click_get_button(driver):
    """Encontrar y hacer clic en el botón 'Get [nombre]' secundario"""
    try:
        wait = WebDriverWait(driver, 20)

        # Selectores específicos para el botón "Get [nombre]" secundario
        get_content_selectors = [
            # Selector específico por ID
            "//button[@id='get-content']",
            
            # Selector por clase secundaria
            "//button[contains(@class, 'btn-secondary') and @id='get-content']",
            
            # Selector por atributo data-step
            "//button[@data-step='2']",
            
            # Selector por data-content-name
            "//button[@data-content-name]",
            
            # Selector por función onclick
            "//button[contains(@onclick, 'proceedToNext')]",
            
            # Selector por texto que empiece con "Get "
            "//button[starts-with(text(), 'Get ')]",
            
            # Selectores CSS equivalentes
            "#get-content",
            "button.btn-secondary#get-content",
            "button[data-step='2']",
            "button[data-content-name]"
        ]

        # Verificar selectores XPath
        for selector in get_content_selectors[:6]:
            try:
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))

                if element.is_displayed() and element.is_enabled():
                    # Scroll al elemento
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(1)

                    # Hacer clic
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"<:verify:1396087763388072006> Clic en 'Get [nombre]' exitoso con selector: {selector}")
                    await asyncio.sleep(3)
                    return True

            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Error con selector XPath {selector}: {e}")
                continue

        # Verificar selectores CSS
        for css_selector in get_content_selectors[6:]:
            try:
                element = driver.find_element(By.CSS_SELECTOR, css_selector)
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(1)
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"<:verify:1396087763388072006> Clic en 'Get [nombre]' exitoso con CSS: {css_selector}")
                    await asyncio.sleep(3)
                    return True
            except Exception as e:
                logger.debug(f"Error con selector CSS {css_selector}: {e}")
                continue

        # Método alternativo: buscar botón secundario por clase y texto
        try:
            elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-secondary') and contains(text(), 'Get')]")
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(1)
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"<:verify:1396087763388072006> Clic en 'Get [nombre]' exitoso (método alternativo): {element.text}")
                    await asyncio.sleep(3)
                    return True
        except Exception as e:
            logger.debug(f"Error en método alternativo: {e}")

        logger.warning("<:1000182563:1396420770904932372> No se encontró botón 'Get [nombre]'")
        return False

    except Exception as e:
        logger.error(f"Error buscando botón 'Get [nombre]': {e}")
        return False

async def find_and_click_open_button(driver):
    """Encontrar y hacer clic en el botón 'Open' final"""
    try:
        wait = WebDriverWait(driver, 20)

        # Selectores específicos para el botón "Open" final
        open_link_selectors = [
            # Selector específico por ID
            "//button[@id='open-link']",
            
            # Selector por clase success
            "//button[contains(@class, 'btn-success') and @id='open-link']",
            
            # Selector por atributo data-step final
            "//button[@data-step='final']",
            
            # Selector por data-destination-url
            "//button[@data-destination-url]",
            
            # Selector por función onclick
            "//button[contains(@onclick, 'openFinalLink')]",
            
            # Selector por texto "Open"
            "//button[text()='Open' or text()='OPEN']",
            
            # Selectores CSS equivalentes
            "#open-link",
            "button.btn-success#open-link",
            "button[data-step='final']",
            "button[data-destination-url]"
        ]

        # Verificar selectores XPath
        for selector in open_link_selectors[:6]:
            try:
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))

                if element.is_displayed() and element.is_enabled():
                    # Scroll al elemento
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(1)

                    # Hacer clic
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"<:verify:1396087763388072006> Clic en 'Open' final exitoso con selector: {selector}")
                    await asyncio.sleep(3)  # Esperar redirección
                    return True

            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Error con selector XPath {selector}: {e}")
                continue

        # Verificar selectores CSS
        for css_selector in open_link_selectors[6:]:
            try:
                element = driver.find_element(By.CSS_SELECTOR, css_selector)
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(1)
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"<:verify:1396087763388072006> Clic en 'Open' final exitoso con CSS: {css_selector}")
                    await asyncio.sleep(3)
                    return True
            except Exception as e:
                logger.debug(f"Error con selector CSS {css_selector}: {e}")
                continue

        # Método alternativo: buscar botón success
        try:
            elements = driver.find_elements(By.XPATH, "//button[contains(@class, 'btn-success') and contains(text(), 'Open')]")
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView(true);", element)
                    await asyncio.sleep(1)
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"<:verify:1396087763388072006> Clic en 'Open' final exitoso (método alternativo): {element.text}")
                    await asyncio.sleep(3)
                    return True
        except Exception as e:
            logger.debug(f"Error en método alternativo Open: {e}")

        logger.warning("<:1000182563:1396420770904932372> No se encontró botón 'Open' final")
        return False

    except Exception as e:
        logger.error(f"Error buscando botón 'Open' final: {e}")
        return False

async def update_progress(message, status, steps, start_time):
    """Actualizar el progreso del bypass"""
    try:
        elapsed_time = time.time() - start_time

        embed = discord.Embed(
            title="🔗 Linkvertise Bypass",
            description="Bypass en progreso...",
            color=0xffaa00
        )
        embed.add_field(name="📊 Estado:", value=status, inline=True)
        embed.add_field(name="🔄 Pasos:", value=f"{steps}/10", inline=True)
        embed.add_field(name="⏱️ Tiempo:", value=f"{elapsed_time:.1f}s", inline=True)
        embed.add_field(
            name="💡 Progreso:",
            value=f"{'▰' * steps}{'▱' * (10-steps)} {int((steps/10)*100)}%",
            inline=False
        )

        await message.edit(embed=embed)
    except Exception as e:
        logger.debug(f"Error actualizando progreso: {e}")

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass