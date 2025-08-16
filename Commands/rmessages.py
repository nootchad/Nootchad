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
from selenium.webdriver.common.keys import Keys
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

def find_and_click_friend(driver, friend_name):
    """Buscar y hacer click en un amigo específico en la lista de chat"""
    try:
        logger.info(f"🔍 Buscando amigo: {friend_name}")

        wait = WebDriverWait(driver, 15)

        # Buscar el elemento del amigo por nombre
        friend_selectors = [
            f"//span[@class='small text-title text-overflow font-caption-header chat-friend-name dynamic-ellipsis-item ng-binding read' and contains(text(), '{friend_name}')]",
            f"//span[@class='small text-title text-overflow font-caption-header chat-friend-name dynamic-ellipsis-item ng-binding unread' and contains(text(), '{friend_name}')]",
            f"//span[contains(@class, 'chat-friend-name') and contains(text(), '{friend_name}')]",
            f"//*[contains(@class, 'chat-friend-info') and contains(., '{friend_name}')]"
        ]

        friend_element = None
        for selector in friend_selectors:
            try:
                friend_element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"✅ Amigo {friend_name} encontrado con selector: {selector}")
                break
            except TimeoutException:
                logger.debug(f"No se encontró amigo con selector: {selector}")
                continue

        if not friend_element:
            logger.error(f"❌ No se pudo encontrar al amigo: {friend_name}")
            return False

        # Hacer click en el amigo
        driver.execute_script("arguments[0].scrollIntoView(true);", friend_element)
        time.sleep(1)

        try:
            friend_element.click()
            logger.info(f"✅ Click en amigo {friend_name} exitoso")
        except Exception as e:
            # Si falla, usar JavaScript click
            logger.info(f"Click normal falló ({e}), usando JavaScript click...")
            driver.execute_script("arguments[0].click();", friend_element)
            logger.info(f"✅ JavaScript click en amigo {friend_name} exitoso")

        time.sleep(2)  # Esperar a que se abra la conversación

        return True

    except Exception as e:
        logger.error(f"❌ Error buscando amigo {friend_name}: {e}")
        return False

def send_message_to_friend(driver, message):
    """Enviar mensaje en el chat abierto"""
    try:
        logger.info(f"💬 Enviando mensaje: {message[:50]}...")

        wait = WebDriverWait(driver, 15)

        # Buscar el campo de entrada de mensaje
        message_input_selectors = [
            "textarea#dialog-input",
            "textarea[placeholder='Enviar un mensaje']",
            "textarea.dialog-input",
            "textarea[ng-model='dialogData.messageForSend']",
            "textarea[dialog-input]"
        ]

        message_input = None
        for selector in message_input_selectors:
            try:
                message_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                logger.info(f"✅ Campo de mensaje encontrado con selector: {selector}")
                break
            except TimeoutException:
                logger.debug(f"No se encontró campo con selector: {selector}")
                continue

        if not message_input:
            logger.error("❌ No se pudo encontrar el campo de entrada de mensaje")
            return False

        # Limpiar el campo y escribir el mensaje
        message_input.clear()
        time.sleep(0.5)
        message_input.send_keys(message)
        time.sleep(1)

        # Enviar el mensaje presionando Enter
        from selenium.webdriver.common.keys import Keys
        message_input.send_keys(Keys.RETURN)

        logger.info("✅ Mensaje enviado exitosamente")
        time.sleep(2)  # Esperar confirmación

        return True

    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")
        return False

def setup_commands(bot):
    """
    Función requerida para configurar comandos
    """

    @bot.tree.command(name="rmessages", description="[OWNER ONLY] Hacer scrape de mensajes en Roblox con VNC visible")
    async def rmessages_command(interaction: discord.Interaction, friend_name: str = None, text_message: str = None):
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

        discord_message = None  # Inicializar discord_message

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

            if friend_name and text_message:
                initial_embed.add_field(name="👤 Amigo", value=friend_name, inline=True)
                initial_embed.add_field(name="💬 Mensaje", value=f"{text_message[:30]}{'...' if len(text_message) > 30 else ''}", inline=True)
            else:
                initial_embed.add_field(name="🎯 Modo", value="Solo abrir chat", inline=True)

            discord_message = await interaction.followup.send(embed=initial_embed, ephemeral=True)

            # Crear driver con VNC visible
            progress_embed = discord.Embed(
                title="🤖 Scrape de Mensajes de Roblox",
                description="Creando driver de Chrome...",
                color=0xffaa00
            )
            progress_embed.add_field(name="🖥️ VNC", value="✅ Modo visible activado", inline=True)
            progress_embed.add_field(name="🌐 Navegador", value="🔄 Configurando...", inline=True)
            progress_embed.add_field(name="🍪 Cookie", value="⏳ Pendiente", inline=True)

            await discord_message.edit(embed=progress_embed)

            driver = None
            try:
                driver = create_roblox_driver()

                # Actualizar progreso
                progress_embed.add_field(name="🌐 Navegador", value="✅ Creado", inline=True)
                progress_embed.add_field(name="🍪 Cookie", value="🔄 Aplicando...", inline=True)
                await discord_message.edit(embed=progress_embed)

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

                await discord_message.edit(progress_embed)

                # Navegar a la página principal de Roblox
                driver.get("https://www.roblox.com/home")
                time.sleep(5)  # Esperar a que cargue completamente

                # Hacer click en el elemento del chat
                chat_clicked = click_chat_element(driver)

                if chat_clicked:
                    # Si se proporcionó nombre de amigo y mensaje, proceder a enviar
                    if friend_name and text_message:
                        # Actualizar progreso
                        friend_embed = discord.Embed(
                            title="🤖 Scrape de Mensajes de Roblox",
                            description=f"Chat abierto exitosamente. Buscando amigo: **{friend_name}**...",
                            color=0xffaa00
                        )
                        friend_embed.add_field(name="🌐 Navegador", value="✅ Activo", inline=True)
                        friend_embed.add_field(name="🍪 Cookie", value="✅ Aplicada", inline=True)
                        friend_embed.add_field(name="🎯 Chat", value="✅ Abierto", inline=True)
                        friend_embed.add_field(name="👤 Amigo", value="🔍 Buscando...", inline=True)

                        await discord_message.edit(embed=friend_embed)

                        # Buscar y hacer click en el amigo
                        friend_found = find_and_click_friend(driver, friend_name)

                        if friend_found:
                            # Actualizar progreso
                            message_embed = discord.Embed(
                                title="🤖 Scrape de Mensajes de Roblox",
                                description=f"Amigo **{friend_name}** encontrado. Enviando mensaje...",
                                color=0xffaa00
                            )
                            message_embed.add_field(name="👤 Amigo", value="✅ Encontrado", inline=True)
                            message_embed.add_field(name="💬 Mensaje", value="🔄 Enviando...", inline=True)

                            await discord_message.edit(embed=message_embed)

                            # Enviar mensaje
                            message_sent = send_message_to_friend(driver, text_message)

                            if message_sent:
                                # Éxito completo
                                success_embed = discord.Embed(
                                    title="✅ Mensaje Enviado Exitosamente",
                                    description=f"Se envió el mensaje a **{friend_name}** en Roblox.",
                                    color=0x00ff88
                                )
                                success_embed.add_field(name="🌐 Navegador", value="✅ Activo y visible", inline=True)
                                success_embed.add_field(name="🍪 Cookie", value="✅ Aplicada correctamente", inline=True)
                                success_embed.add_field(name="🎯 Chat", value="✅ Abierto", inline=True)
                                success_embed.add_field(name="👤 Amigo", value=f"✅ {friend_name}", inline=True)
                                success_embed.add_field(name="💬 Mensaje", value="✅ Enviado", inline=True)
                                success_embed.add_field(
                                    name="📝 Contenido",
                                    value=f"```{text_message[:100]}{'...' if len(text_message) > 100 else ''}```",
                                    inline=False
                                )

                                await discord_message.edit(embed=success_embed)
                            else:
                                # Error enviando mensaje
                                error_embed = discord.Embed(
                                    title="❌ Error Enviando Mensaje",
                                    description=f"No se pudo enviar el mensaje a **{friend_name}**.",
                                    color=0xff0000
                                )
                                error_embed.add_field(name="👤 Amigo", value="✅ Encontrado", inline=True)
                                error_embed.add_field(name="💬 Mensaje", value="❌ Error al enviar", inline=True)

                                await discord_message.edit(embed=error_embed)
                        else:
                            # Error encontrando amigo
                            error_embed = discord.Embed(
                                title="❌ Amigo No Encontrado",
                                description=f"No se pudo encontrar al amigo: **{friend_name}**",
                                color=0xff0000
                            )
                            error_embed.add_field(name="🎯 Chat", value="✅ Abierto", inline=True)
                            error_embed.add_field(name="👤 Amigo", value="❌ No encontrado", inline=True)
                            error_embed.add_field(
                                name="💡 Posibles causas",
                                value="• El nombre no coincide exactamente\n• El amigo no está en línea\n• No están en la lista de amigos",
                                inline=False
                            )

                            await discord_message.edit(embed=error_embed)

                    else:
                        # Solo abrir chat sin enviar mensaje
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
                            name="🔧 Uso Avanzado",
                            value="Para enviar mensajes usa: `/rmessages friend_name:NombreAmigo message:Tu mensaje`",
                            inline=False
                        )

                        await discord_message.edit(embed=success_embed)

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

                    await discord_message.edit(embed=error_embed)

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
                if discord_message is not None:
                    await discord_message.edit(embed=error_embed)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=error_embed, ephemeral=True)

    logger.info("✅ Comando /rmessages configurado exitosamente")
    return True

def cleanup_commands(bot):
    """Función opcional para limpiar comandos al recargar"""
    logger.info("🧹 Limpieza del comando /rmessages completada")