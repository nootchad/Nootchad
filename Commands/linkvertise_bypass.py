
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
                    title="❌ URL Inválida",
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
                    title="✅ Bypass Completado",
                    description=f"URL final obtenida exitosamente.",
                    color=0x00ff88
                )
                success_embed.add_field(name="🔗 URL Final:", value=f"```{result['final_url']}```", inline=False)
                success_embed.add_field(name="⏱️ Tiempo total:", value=f"{result['duration']:.1f}s", inline=True)
                success_embed.add_field(name="🔄 Pasos completados:", value=f"{result['steps_completed']}", inline=True)

                await message.edit(embed=success_embed)

            else:
                # Error
                error_embed = discord.Embed(
                    title="❌ Error en Bypass",
                    description=result['error'],
                    color=0xff0000
                )
                error_embed.add_field(name="🔍 Detalles:", value=result.get('details', 'Sin detalles adicionales'), inline=False)
                await message.edit(embed=error_embed)

        except Exception as e:
            logger.error(f"Error en comando linkvertise para {username}: {e}")
            embed = discord.Embed(
                title="❌ Error Interno",
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

        # Paso 3: Buscar y hacer clic en "Free Access"
        free_access_clicked = await find_and_click_free_access(driver)
        if not free_access_clicked:
            return {
                'success': False,
                'error': 'No se encontró el botón "Free Access"',
                'details': 'El botón de acceso gratuito no está disponible o cambió su estructura',
                'duration': time.time() - start_time,
                'steps_completed': steps_completed
            }

        steps_completed += 1
        await update_progress(message, "⏳ Esperando anuncios...", steps_completed, start_time)

        # Paso 4: Esperar y buscar el botón Skip verdadero
        await asyncio.sleep(5)  # Esperar a que aparezcan los anuncios

        steps_completed += 1
        await update_progress(message, "🎯 Buscando botón Skip verdadero...", steps_completed, start_time)

        # Paso 5: Encontrar y hacer clic en el botón Skip real
        skip_clicked = await find_and_click_real_skip(driver)
        if not skip_clicked:
            return {
                'success': False,
                'error': 'No se encontró el botón Skip verdadero',
                'details': 'El botón de skip no apareció o cambió su ubicación',
                'duration': time.time() - start_time,
                'steps_completed': steps_completed
            }

        steps_completed += 1
        await update_progress(message, "⏰ Esperando 10 segundos (proceso del sitio)...", steps_completed, start_time)

        # Paso 6: Esperar 10 segundos como hace el sitio
        await asyncio.sleep(10)

        steps_completed += 1
        await update_progress(message, "🔗 Obteniendo URL final...", steps_completed, start_time)

        # Paso 7: Obtener URL final
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
    """Encontrar y hacer clic en el botón Free Access"""
    try:
        wait = WebDriverWait(driver, 15)
        
        # Selectores múltiples para el botón Free Access
        free_access_selectors = [
            "//button[contains(text(), 'Free Access')]",
            "//a[contains(text(), 'Free Access')]",
            "//div[contains(text(), 'Free Access')]",
            "//span[contains(text(), 'Free Access')]",
            "//button[contains(@class, 'free') and contains(@class, 'access')]",
            "//a[contains(@class, 'free-access')]",
            "//button[contains(text(), 'Acceso Gratuito')]",
            "//a[contains(text(), 'Acceso Gratuito')]",
            "//*[contains(text(), 'Continue for free')]",
            "//*[contains(text(), 'Continuar gratis')]"
        ]
        
        for selector in free_access_selectors:
            try:
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                driver.execute_script("arguments[0].click();", element)
                logger.info(f"✅ Clic en Free Access exitoso con selector: {selector}")
                return True
            except TimeoutException:
                continue
            except Exception as e:
                logger.debug(f"Error con selector {selector}: {e}")
                continue
        
        # Método alternativo: buscar por texto parcial
        try:
            elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'ree') and contains(text(), 'ccess')]")
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    driver.execute_script("arguments[0].click();", element)
                    logger.info("✅ Clic en Free Access exitoso (método alternativo)")
                    return True
        except Exception as e:
            logger.debug(f"Error en método alternativo: {e}")
        
        logger.warning("❌ No se encontró botón Free Access")
        return False
        
    except Exception as e:
        logger.error(f"Error buscando Free Access: {e}")
        return False

async def find_and_click_real_skip(driver):
    """Encontrar y hacer clic en el botón Skip verdadero (no el falso)"""
    try:
        # Esperar hasta 30 segundos para que aparezca el botón skip real
        max_wait_time = 30
        start_wait = time.time()
        
        while time.time() - start_wait < max_wait_time:
            try:
                # Buscar botones skip verdaderos (típicamente están en la parte superior)
                real_skip_selectors = [
                    # Botón skip que típicamente aparece arriba de la página
                    "//button[contains(text(), 'Skip') and not(ancestor::*[contains(@class, 'ad')]) and not(ancestor::*[contains(@class, 'banner')])]",
                    "//a[contains(text(), 'Skip') and not(ancestor::*[contains(@class, 'ad')]) and not(ancestor::*[contains(@class, 'banner')])]",
                    
                    # Botón skip con clases específicas de Linkvertise
                    "//button[contains(@class, 'skip') and not(contains(@class, 'fake')) and not(contains(@class, 'ad'))]",
                    "//a[contains(@class, 'skip') and not(contains(@class, 'fake')) and not(contains(@class, 'ad'))]",
                    
                    # Botón skip en contenedores específicos (no en anuncios)
                    "//div[contains(@class, 'header')]//button[contains(text(), 'Skip')]",
                    "//div[contains(@class, 'top')]//button[contains(text(), 'Skip')]",
                    "//div[contains(@class, 'navigation')]//button[contains(text(), 'Skip')]",
                    
                    # Selectores más específicos para evitar falsas alarmas
                    "//button[text()='Skip' or text()='Skip Ad' or text()='Skip >>']",
                    "//a[text()='Skip' or text()='Skip Ad' or text()='Skip >>']",
                    
                    # Botón skip que no esté en contenedores grandes/negros
                    "//button[contains(text(), 'Skip') and not(ancestor::div[contains(@style, 'background') and contains(@style, 'black')])]",
                    
                    # Específico para Linkvertise 2025
                    "//*[@data-testid='skip-button']",
                    "//*[@id='skip-button']",
                    "//button[contains(@class, 'linkvertise-skip')]"
                ]
                
                # Verificar cada selector
                for selector in real_skip_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if (element.is_displayed() and 
                                element.is_enabled() and 
                                is_real_skip_button(element, driver)):
                                
                                # Hacer scroll al elemento para asegurar que es clickeable
                                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                await asyncio.sleep(1)
                                
                                # Hacer clic
                                driver.execute_script("arguments[0].click();", element)
                                logger.info(f"✅ Clic en Skip real exitoso con selector: {selector}")
                                return True
                    except Exception as e:
                        logger.debug(f"Error con selector skip {selector}: {e}")
                        continue
                
                # Si no se encuentra, esperar un poco más
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Error en búsqueda de skip: {e}")
                await asyncio.sleep(2)
        
        logger.warning("❌ No se encontró botón Skip verdadero")
        return False
        
    except Exception as e:
        logger.error(f"Error buscando Skip real: {e}")
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
        embed.add_field(name="🔄 Pasos:", value=f"{steps}/7", inline=True)
        embed.add_field(name="⏱️ Tiempo:", value=f"{elapsed_time:.1f}s", inline=True)
        embed.add_field(
            name="💡 Progreso:",
            value=f"{'▰' * steps}{'▱' * (7-steps)} {int((steps/7)*100)}%",
            inline=False
        )
        
        await message.edit(embed=embed)
    except Exception as e:
        logger.debug(f"Error actualizando progreso: {e}")

def cleanup_commands(bot):
    """Función de limpieza opcional"""
    pass
