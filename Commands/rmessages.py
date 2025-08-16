
"""
Comando /rmessages para hacer scrape de mensajes en Roblox
Owner only - Usa VNC headless false y hace click en el elemento del chat
"""
import discord
import logging
import asyncio
import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from pathlib import Path

logger = logging.getLogger(__name__)

def is_owner_or_delegated(user_id: str) -> bool:
    """Verificar si un usuario es owner original o tiene acceso delegado"""
    DISCORD_OWNER_ID = "916070251895091241"  # Tu Discord ID
    
    # Cargar owners delegados
    delegated_owners = set()
    try:
        delegated_file = "delegated_owners.json"
        if Path(delegated_file).exists():
            import json
            with open(delegated_file, 'r') as f:
                data = json.load(f)
                delegated_owners = set(data.get('delegated_owners', []))
    except Exception as e:
        logger.debug(f"Error cargando owners delegados: {e}")
    
    return user_id == DISCORD_OWNER_ID or user_id in delegated_owners

def get_roblox_cookie():
    """Obtener cookie de Roblox desde el secreto"""
    try:
        cookie = os.getenv('COOKIE')
        if cookie and len(cookie.strip()) > 50:
            return cookie.strip()
        else:
            logger.warning("⚠️ Cookie del secreto COOKIE no válida")
            return None
    except Exception as e:
        logger.error(f"Error obteniendo cookie: {e}")
        return None

def create_roblox_driver():
    """Crear driver de Chrome para Roblox con VNC headless false"""
    try:
        logger.info("🚀 Creando driver de Chrome para Roblox (VNC headless false)...")

        chrome_options = Options()
        # NO usar headless - queremos que sea visible para VNC
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")

        # Configurar preferencias para permitir cookies
        prefs = {
            "profile.managed_default_content_settings.cookies": 1,  # Permitir cookies
            "profile.managed_default_content_settings.javascript": 1,
            "profile.default_content_setting_values.notifications": 2,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Buscar binario de Chrome
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
            logger.info(f"Usando binario de Chrome en: {chrome_binary}")
        else:
            logger.warning("Binario de Chrome no encontrado, usando por defecto")

        # Crear driver
        try:
            # Intentar con chromedriver del sistema
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.warning(f"Error con chromedriver del sistema: {e}")
            # Fallback con configuración mínima
            minimal_options = Options()
            minimal_options.add_argument("--no-sandbox")
            minimal_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=minimal_options)

        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)

        # Ejecutar script para ocultar propiedades de webdriver
        try:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.warning(f"No se pudo ocultar propiedad webdriver: {e}")

        logger.info("✅ Driver de Chrome creado exitosamente para VNC")
        return driver

    except Exception as e:
        logger.error(f"Error creando driver de Chrome: {e}")
        raise Exception(f"Falló la creación del driver: {e}")

def apply_roblox_cookie(driver, cookie):
    """Aplicar cookie de Roblox al navegador"""
    try:
        logger.info("🍪 Aplicando cookie de Roblox...")
        
        # Navegar a Roblox primero
        driver.get("https://www.roblox.com")
        time.sleep(3)
        
        # Agregar la cookie
        driver.add_cookie({
            'name': '.ROBLOSECURITY',
            'value': cookie,
            'domain': '.roblox.com',
            'path': '/',
            'secure': True,
            'httpOnly': True
        })
        
        # Refrescar la página para aplicar la cookie
        driver.refresh()
        time.sleep(3)
        
        logger.info("✅ Cookie de Roblox aplicada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error aplicando cookie de Roblox: {e}")
        return False

def click_chat_element(driver):
    """Hacer click en el elemento del chat especificado"""
    try:
        logger.info("🎯 Buscando elemento del chat...")
        
        # Esperar a que el elemento esté presente
        wait = WebDriverWait(driver, 20)
        
        # Buscar el elemento del chat por multiple selectores
        chat_selectors = [
            "div.chat-header-label[ng-click='toggleChatContainer()']",
            ".chat-header-label",
            "div[ng-click='toggleChatContainer()']",
            ".chat-header-title",
            "span.font-caption-header.chat-header-title"
        ]
        
        chat_element = None
        for selector in chat_selectors:
            try:
                chat_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                logger.info(f"✅ Elemento del chat encontrado con selector: {selector}")
                break
            except TimeoutException:
                logger.debug(f"No se encontró elemento con selector: {selector}")
                continue
        
        if not chat_element:
            # Buscar por texto si no se encuentra por selectores
            try:
                chat_element = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]")))
                logger.info("✅ Elemento del chat encontrado por texto")
            except TimeoutException:
                logger.error("❌ No se pudo encontrar el elemento del chat")
                return False
        
        # Hacer click en el elemento
        driver.execute_script("arguments[0].scrollIntoView(true);", chat_element)
        time.sleep(1)
        
        # Intentar click normal primero
        try:
            chat_element.click()
            logger.info("✅ Click normal en elemento del chat exitoso")
        except Exception as e:
            # Si falla, usar JavaScript click
            logger.info(f"Click normal falló ({e}), usando JavaScript click...")
            driver.execute_script("arguments[0].click();", chat_element)
            logger.info("✅ JavaScript click en elemento del chat exitoso")
        
        time.sleep(3)  # Esperar a que se abra el chat
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error haciendo click en elemento del chat: {e}")
        return False

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    """
    
    @bot.tree.command(name="rmessages", description="[OWNER ONLY] Hacer scrape de mensajes en Roblox con VNC visible")
    async def rmessages_command(interaction: discord.Interaction):
        """Comando para hacer scrape de mensajes en Roblox"""
        user_id = str(interaction.user.id)
        username = f"{interaction.user.name}#{interaction.user.discriminator}"
        
        # Verificar que solo el owner o delegados puedan usar este comando
        if not is_owner_or_delegated(user_id):
            embed = discord.Embed(
                title="❌ Acceso Denegado",
                description="Este comando solo puede ser usado por el owner del bot o usuarios con acceso delegado.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        logger.info(f"🤖 Owner {username} (ID: {user_id}) ejecutó comando /rmessages")
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Obtener cookie de Roblox
            cookie = get_roblox_cookie()
            if not cookie:
                embed = discord.Embed(
                    title="❌ Cookie No Disponible",
                    description="No se encontró una cookie válida de Roblox en las variables de entorno.",
                    color=0xff0000
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Crear embed inicial
            initial_embed = discord.Embed(
                title="🤖 Iniciando Scrape de Mensajes de Roblox",
                description="Configurando navegador con VNC visible...",
                color=0xffaa00
            )
            initial_embed.add_field(name="🍪 Cookie", value="✅ Disponible", inline=True)
            initial_embed.add_field(name="🖥️ VNC", value="✅ Headless False", inline=True)
            initial_embed.add_field(name="⏳ Estado", value="Iniciando...", inline=True)
            
            message = await interaction.followup.send(embed=initial_embed, ephemeral=True)
            
            # Crear driver con VNC visible
            progress_embed = discord.Embed(
                title="🤖 Scrape de Mensajes de Roblox",
                description="Creando driver de Chrome...",
                color=0xffaa00
            )
            progress_embed.add_field(name="🖥️ VNC", value="✅ Modo visible activado", inline=True)
            progress_embed.add_field(name="🌐 Navegador", value="🔄 Configurando...", inline=True)
            progress_embed.add_field(name="🍪 Cookie", value="⏳ Pendiente", inline=True)
            
            await message.edit(embed=progress_embed)
            
            driver = None
            try:
                driver = create_roblox_driver()
                
                # Actualizar progreso
                progress_embed.add_field(name="🌐 Navegador", value="✅ Creado", inline=True)
                progress_embed.add_field(name="🍪 Cookie", value="🔄 Aplicando...", inline=True)
                await message.edit(embed=progress_embed)
                
                # Aplicar cookie
                cookie_applied = apply_roblox_cookie(driver, cookie)
                if not cookie_applied:
                    raise Exception("No se pudo aplicar la cookie de Roblox")
                
                # Actualizar progreso
                progress_embed = discord.Embed(
                    title="🤖 Scrape de Mensajes de Roblox",
                    description="Navegando a Roblox y buscando elemento del chat...",
                    color=0xffaa00
                )
                progress_embed.add_field(name="🌐 Navegador", value="✅ Activo", inline=True)
                progress_embed.add_field(name="🍪 Cookie", value="✅ Aplicada", inline=True)
                progress_embed.add_field(name="🎯 Chat", value="🔄 Buscando...", inline=True)
                
                await message.edit(embed=progress_embed)
                
                # Navegar a la página principal de Roblox
                driver.get("https://www.roblox.com/home")
                time.sleep(5)  # Esperar a que cargue completamente
                
                # Hacer click en el elemento del chat
                chat_clicked = click_chat_element(driver)
                
                if chat_clicked:
                    # Éxito
                    success_embed = discord.Embed(
                        title="✅ Scrape de Mensajes Completado",
                        description="Se hizo click exitosamente en el elemento del chat de Roblox.",
                        color=0x00ff88
                    )
                    success_embed.add_field(name="🌐 Navegador", value="✅ Activo y visible", inline=True)
                    success_embed.add_field(name="🍪 Cookie", value="✅ Aplicada correctamente", inline=True)
                    success_embed.add_field(name="🎯 Chat", value="✅ Click exitoso", inline=True)
                    success_embed.add_field(
                        name="💡 Información",
                        value="El navegador sigue activo para que puedas ver la página en VNC. Se cerrará automáticamente en 60 segundos.",
                        inline=False
                    )
                    success_embed.add_field(
                        name="🖥️ VNC",
                        value="Puedes ver la sesión del navegador a través de VNC si está configurado.",
                        inline=False
                    )
                    
                    await message.edit(embed=success_embed)
                    
                    # Esperar 60 segundos antes de cerrar para permitir visualización
                    logger.info("⏳ Manteniendo navegador activo por 60 segundos para VNC...")
                    await asyncio.sleep(60)
                    
                else:
                    # Error en el click
                    error_embed = discord.Embed(
                        title="❌ Error en Click del Chat",
                        description="No se pudo hacer click en el elemento del chat.",
                        color=0xff0000
                    )
                    error_embed.add_field(name="🌐 Navegador", value="✅ Activo", inline=True)
                    error_embed.add_field(name="🍪 Cookie", value="✅ Aplicada", inline=True)
                    error_embed.add_field(name="🎯 Chat", value="❌ No encontrado", inline=True)
                    error_embed.add_field(
                        name="💡 Posibles causas",
                        value="• Elemento del chat no está presente\n• Página no cargó completamente\n• Selectores han cambiado",
                        inline=False
                    )
                    
                    await message.edit(embed=error_embed)
                
            finally:
                # Cerrar driver
                if driver:
                    try:
                        driver.quit()
                        logger.info("🔒 Driver de Chrome cerrado")
                    except Exception as e:
                        logger.warning(f"⚠️ Error cerrando driver: {e}")
            
            logger.info(f"Owner {username} completó comando /rmessages")
            
        except Exception as e:
            logger.error(f"Error en comando /rmessages: {e}")
            
            error_embed = discord.Embed(
                title="❌ Error en Scrape de Mensajes",
                description=f"Ocurrió un error durante el proceso de scraping.",
                color=0xff0000
            )
            error_embed.add_field(
                name="🔍 Detalles del Error",
                value=f"```{str(e)[:200]}```",
                inline=False
            )
            error_embed.add_field(
                name="💡 Recomendaciones",
                value="• Verificar que la cookie de Roblox sea válida\n• Intentar nuevamente en unos minutos\n• Verificar conexión a internet",
                inline=False
            )
            
            try:
                await message.edit(embed=error_embed)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    logger.info("✅ Comando /rmessages configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    logger.info("🧹 Limpieza del comando /rmessages completada")
