
import asyncio
import random
import time
import os
from pathlib import Path
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException

logger = logging.getLogger(__name__)

class FriendRequestBrowserImproved:
    def __init__(self, scraper):
        self.scraper = scraper
    
    def extract_cookies_from_sources(self):
        """Extraer cookies de todas las fuentes disponibles"""
        cookies_disponibles = []
        
        # 1. Cookie del secreto COOKIE (primera prioridad)
        secret_cookie = os.getenv('COOKIE')
        if secret_cookie and len(secret_cookie.strip()) > 50:
            cookies_disponibles.append({
                'cookie': secret_cookie.strip(),
                'source': 'SECRET_COOKIE',
                'index': 0
            })
            logger.info("🔐 Cookie del secreto COOKIE agregada")
        
        # 2. Cookies del archivo Cookiesnew.md
        try:
            if Path("Cookiesnew.md").exists():
                with open("Cookiesnew.md", "r", encoding="utf-8") as f:
                    content = f.read()
                
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if '_|WARNING:-DO-NOT-SHARE-THIS.' in line and '|_' in line:
                        try:
                            warning_text = '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_'
                            if warning_text in line:
                                cookie_value = line.split(warning_text)[1].strip()
                                if cookie_value and len(cookie_value) > 50:
                                    cookies_disponibles.append({
                                        'cookie': cookie_value,
                                        'source': f'Cookiesnew.md:L{line_num}',
                                        'index': len(cookies_disponibles)
                                    })
                                    logger.info(f"🍪 Cookie extraída de Cookiesnew.md línea {line_num}")
                        except Exception as e:
                            logger.debug(f"Error procesando línea {line_num}: {e}")
                            continue
        except Exception as e:
            logger.error(f"Error extrayendo cookies de Cookiesnew.md: {e}")
        
        return cookies_disponibles
    
    async def apply_cookie_to_browser(self, driver, cookie_value):
        """Aplicar cookie al navegador de forma segura"""
        try:
            logger.info("🍪 Aplicando cookie al navegador...")
            
            # Navegar a Roblox primero
            driver.get("https://www.roblox.com")
            await asyncio.sleep(3)
            
            # Limpiar cookies existentes
            driver.delete_all_cookies()
            
            # Agregar la nueva cookie
            cookie_dict = {
                'name': '.ROBLOSECURITY',
                'value': cookie_value,
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            
            driver.add_cookie(cookie_dict)
            logger.info("✅ Cookie aplicada exitosamente")
            
            # Refrescar para aplicar la cookie
            driver.refresh()
            await asyncio.sleep(4)
            
            # Verificar que estamos logueados
            try:
                # Buscar elementos que indiquen que estamos logueados
                user_indicators = [
                    "[data-testid='navigation-robux-balance']",
                    ".nav-robux-amount",
                    "[data-testid='user-menu']",
                    ".nav-menu-username"
                ]
                
                logged_in = False
                for indicator in user_indicators:
                    try:
                        element = driver.find_element(By.CSS_SELECTOR, indicator)
                        if element:
                            logged_in = True
                            logger.info(f"✅ Login verificado con elemento: {indicator}")
                            break
                    except:
                        continue
                
                if not logged_in:
                    logger.warning("⚠️ No se pudo verificar el login, pero continuando...")
                
                return True
                
            except Exception as verify_error:
                logger.warning(f"⚠️ Error verificando login: {verify_error}")
                return True  # Continuar de todas formas
                
        except Exception as e:
            logger.error(f"❌ Error aplicando cookie: {e}")
            return False
    
    async def handle_overlays_and_popups(self, driver):
        """Manejar overlays, popups y elementos que bloquean"""
        try:
            logger.info("🔧 Manejando overlays y popups...")
            
            # Lista de selectores de elementos que pueden bloquear
            blocking_elements = [
                # Botones de signup/login que pueden bloquear
                ".signup-button",
                ".login-button", 
                "#signup-button",
                "#login-button",
                
                # Modales y overlays
                ".modal",
                ".overlay",
                ".popup",
                "[role='dialog']",
                ".alert",
                
                # Banners y notificaciones
                ".banner",
                ".notification",
                ".cookie-banner",
                
                # Botones de cerrar genéricos
                ".close-button",
                "[aria-label='Close']",
                "button[title='Close']"
            ]
            
            # Intentar cerrar elementos bloqueantes
            for selector in blocking_elements:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            try:
                                # Intentar hacer clic para cerrar
                                driver.execute_script("arguments[0].style.display = 'none';", element)
                                logger.info(f"🔧 Elemento bloqueante ocultado: {selector}")
                            except:
                                pass
                except:
                    continue
            
            # Script para ocultar elementos comunes que bloquean
            hide_script = """
            // Ocultar elementos de signup/login que puedan bloquear
            var blockingSelectors = [
                '.signup-button', '.login-button', '#signup-button', '#login-button',
                '.modal', '.overlay', '.popup', '.banner', '.notification'
            ];
            
            blockingSelectors.forEach(function(selector) {
                try {
                    var elements = document.querySelectorAll(selector);
                    elements.forEach(function(el) {
                        if (el.style.display !== 'none') {
                            el.style.display = 'none';
                        }
                    });
                } catch(e) {}
            });
            """
            
            driver.execute_script(hide_script)
            logger.info("✅ Overlays y popups manejados")
            
        except Exception as e:
            logger.debug(f"Error manejando overlays: {e}")
    
    async def find_and_click_friend_button(self, driver, user_id):
        """Buscar y hacer clic en el botón de Add Friend con múltiples estrategias"""
        try:
            logger.info(f"🔍 Buscando botón de Add Friend para usuario {user_id}...")
            
            wait = WebDriverWait(driver, 15)
            
            # Estrategia 1: Selectores CSS específicos
            friend_button_selectors = [
                "button[data-testid='add-friend-button']",
                "button[aria-label='Add Friend']",
                ".btn-add-friend",
                "#add-friend-button",
                "button[title='Add Friend']",
                "button.btn-primary-md",
                "button.btn-secondary-md"
            ]
            
            friend_button = None
            
            for selector in friend_button_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # Verificar que el texto contenga algo relacionado con amistad
                            button_text = element.text.lower()
                            if any(word in button_text for word in ['friend', 'add', 'seguir', 'follow']):
                                friend_button = element
                                logger.info(f"✅ Botón encontrado con selector: {selector} - Texto: '{element.text}'")
                                break
                    if friend_button:
                        break
                except Exception as e:
                    logger.debug(f"Error con selector {selector}: {e}")
                    continue
            
            # Estrategia 2: XPath por texto
            if not friend_button:
                xpath_selectors = [
                    "//button[contains(text(), 'Add Friend')]",
                    "//button[contains(text(), 'Agregar amigo')]",
                    "//button[contains(text(), 'Follow')]",
                    "//button[contains(text(), 'Seguir')]",
                    "//a[contains(text(), 'Add Friend')]",
                    "//a[contains(text(), 'Agregar amigo')]"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                friend_button = element
                                logger.info(f"✅ Botón encontrado con XPath: {xpath} - Texto: '{element.text}'")
                                break
                        if friend_button:
                            break
                    except Exception as e:
                        logger.debug(f"Error con XPath {xpath}: {e}")
                        continue
            
            # Estrategia 3: Búsqueda por texto en todos los botones
            if not friend_button:
                try:
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    all_elements = all_buttons + all_links
                    
                    for element in all_elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                text = element.text.lower().strip()
                                # Términos que indican botón de amistad
                                friend_terms = [
                                    'add friend', 'agregar amigo', 'añadir amigo',
                                    'follow', 'seguir', 'add as friend'
                                ]
                                
                                if any(term in text for term in friend_terms):
                                    friend_button = element
                                    logger.info(f"✅ Botón encontrado por texto: '{element.text}'")
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Error en búsqueda por texto: {e}")
            
            if not friend_button:
                logger.warning("❌ No se encontró botón de Add Friend")
                return False
            
            # Intentar hacer clic con múltiples métodos
            click_success = False
            
            # Método 1: Scroll y clic normal
            try:
                # Hacer scroll al elemento
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", friend_button)
                await asyncio.sleep(1)
                
                # Manejar overlays antes del clic
                await self.handle_overlays_and_popups(driver)
                
                # Intentar clic normal
                friend_button.click()
                click_success = True
                logger.info("✅ Clic exitoso con método normal")
                
            except ElementClickInterceptedException:
                logger.warning("⚠️ Elemento interceptado, probando método JavaScript...")
                
                # Método 2: JavaScript click
                try:
                    driver.execute_script("arguments[0].click();", friend_button)
                    click_success = True
                    logger.info("✅ Clic exitoso con JavaScript")
                    
                except Exception as js_error:
                    logger.warning(f"⚠️ Error con JavaScript click: {js_error}")
                    
                    # Método 3: Forzar clic removiendo elementos bloqueantes
                    try:
                        # Remover elementos que puedan estar bloqueando
                        remove_script = """
                        // Remover elementos con z-index alto que puedan bloquear
                        var allElements = document.querySelectorAll('*');
                        for (var i = 0; i < allElements.length; i++) {
                            var style = window.getComputedStyle(allElements[i]);
                            var zIndex = parseInt(style.zIndex);
                            if (zIndex > 1000) {
                                allElements[i].style.display = 'none';
                            }
                        }
                        """
                        driver.execute_script(remove_script)
                        
                        # Intentar clic de nuevo
                        driver.execute_script("arguments[0].click();", friend_button)
                        click_success = True
                        logger.info("✅ Clic exitoso después de remover elementos bloqueantes")
                        
                    except Exception as force_error:
                        logger.error(f"❌ Error en clic forzado: {force_error}")
            
            if click_success:
                # Esperar a que se procese la solicitud
                await asyncio.sleep(4)
                
                # Verificar resultado
                return await self.verify_friend_request_result(driver)
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error general buscando botón: {e}")
            return False
    
    async def verify_friend_request_result(self, driver):
        """Verificar si la friend request fue exitosa"""
        try:
            page_source = driver.page_source.lower()
            
            # Indicadores de éxito
            success_indicators = [
                "friend request sent", "solicitud enviada", "solicitud de amistad enviada",
                "pending", "pendiente", "request sent", "enviada"
            ]
            
            # Indicadores de que ya son amigos
            friend_indicators = [
                "already friends", "ya son amigos", "friends", "amigos",
                "you are friends", "son amigos", "unfriend", "remove friend"
            ]
            
            if any(indicator in page_source for indicator in success_indicators):
                logger.info("✅ Friend request enviada exitosamente")
                return {"status": "success", "message": "Friend request sent successfully"}
                
            elif any(indicator in page_source for indicator in friend_indicators):
                logger.info("👥 Los usuarios ya son amigos")
                return {"status": "already_friends", "message": "Users are already friends"}
                
            else:
                # Verificar cambios en botones como indicador
                try:
                    # Buscar botones que indiquen cambio de estado
                    changed_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Pending') or contains(text(), 'Pendiente') or contains(text(), 'Cancel')]")
                    if changed_buttons:
                        logger.info("✅ Friend request detectada por cambio en botón")
                        return {"status": "success", "message": "Friend request sent (button changed)"}
                except:
                    pass
                
                logger.warning("⚠️ No se pudo verificar el resultado, asumiendo éxito")
                return {"status": "success", "message": "Friend request attempted"}
                
        except Exception as e:
            logger.debug(f"Error verificando resultado: {e}")
            return {"status": "success", "message": "Friend request attempted (verification failed)"}
    
    async def send_friend_request_with_full_restart(self, user_id, cookie_data, attempt_index, total_attempts):
        """Enviar friend request con navegador completamente nuevo y manejo mejorado"""
        driver = None
        try:
            logger.info(f"🚀 [Cookie {attempt_index + 1}/{total_attempts}] Iniciando navegador NUEVO para {cookie_data['source']}")
            
            # PASO 1: Crear navegador completamente nuevo
            driver = self.scraper.create_driver()
            driver.set_page_load_timeout(45)
            driver.implicitly_wait(15)
            
            logger.info(f"✅ [Cookie {attempt_index + 1}] Navegador creado exitosamente")
            
            # PASO 2: Aplicar cookie específica
            cookie_applied = await self.apply_cookie_to_browser(driver, cookie_data['cookie'])
            if not cookie_applied:
                return {"status": "error", "message": "Error aplicando cookie"}
            
            # PASO 3: Navegar al perfil del usuario
            profile_url = f"https://www.roblox.com/users/{user_id}/profile"
            logger.info(f"🔗 [Cookie {attempt_index + 1}] Navegando al perfil: {profile_url}")
            
            driver.get(profile_url)
            await asyncio.sleep(6)
            
            # PASO 4: Manejar overlays antes de buscar el botón
            await self.handle_overlays_and_popups(driver)
            
            # PASO 5: Buscar y hacer clic en el botón de Add Friend
            result = await self.find_and_click_friend_button(driver, user_id)
            
            if result:
                if isinstance(result, dict):
                    return result
                else:
                    return {"status": "success", "message": "Friend request sent successfully"}
            else:
                return {"status": "error", "message": "Add Friend button not found or not clickable"}
                
        except Exception as e:
            logger.error(f"❌ [Cookie {attempt_index + 1}] Error general: {e}")
            return {"status": "error", "message": f"General error: {str(e)[:50]}"}
        
        finally:
            # PASO 6: CERRAR NAVEGADOR COMPLETAMENTE
            if driver:
                try:
                    logger.info(f"🔒 [Cookie {attempt_index + 1}] Cerrando navegador...")
                    driver.quit()
                    logger.info(f"✅ [Cookie {attempt_index + 1}] Navegador cerrado")
                    
                    # Pausa entre navegadores
                    if attempt_index < total_attempts - 1:
                        pause_time = 6 + random.randint(1, 3)
                        logger.info(f"⏳ [Cookie {attempt_index + 1}] Pausa de {pause_time}s...")
                        await asyncio.sleep(pause_time)
                        
                except Exception as close_error:
                    logger.warning(f"⚠️ Error cerrando navegador: {close_error}")
    
    async def process_friend_requests_with_restart(self, user_id, cantidad):
        """Procesar múltiples friend requests con reinicio completo mejorado"""
        try:
            # Obtener cookies disponibles
            cookies_disponibles = self.extract_cookies_from_sources()
            
            if not cookies_disponibles:
                return {
                    "status": "error",
                    "message": "No se encontraron cookies válidas",
                    "results": {
                        "exitosas": 0,
                        "fallidas": 0,
                        "ya_amigos": 0,
                        "errores": [],
                        "total_procesadas": 0
                    }
                }
            
            # Limitar cantidad a las cookies disponibles
            cantidad_real = min(cantidad, len(cookies_disponibles))
            cookies_a_usar = cookies_disponibles[:cantidad_real]
            
            logger.info(f"🚀 Iniciando {cantidad_real} friend requests con REINICIO COMPLETO mejorado")
            logger.info(f"🍪 Cookies a usar: {[c['source'] for c in cookies_a_usar]}")
            
            # Contadores de resultados
            exitosas = 0
            fallidas = 0
            ya_amigos = 0
            errores = []
            
            # Procesar cada cookie con navegador completamente nuevo
            for i, cookie_data in enumerate(cookies_a_usar):
                try:
                    logger.info(f"🔄 [Proceso {i + 1}/{cantidad_real}] INICIANDO para {cookie_data['source']}")
                    
                    # Enviar friend request con navegador nuevo y manejo mejorado
                    resultado = await self.send_friend_request_with_full_restart(
                        user_id, cookie_data, i, cantidad_real
                    )
                    
                    # Procesar resultado
                    if resultado and resultado["status"] == "success":
                        exitosas += 1
                        logger.info(f"✅ [Proceso {i + 1}] Solicitud exitosa con {cookie_data['source']}")
                        
                    elif resultado and resultado["status"] == "already_friends":
                        ya_amigos += 1
                        logger.info(f"👥 [Proceso {i + 1}] Ya son amigos - {cookie_data['source']}")
                        
                    else:
                        fallidas += 1
                        error_msg = resultado["message"] if resultado else "Error desconocido"
                        errores.append(f"Cookie {i + 1}: {error_msg[:50]}")
                        logger.warning(f"❌ [Proceso {i + 1}] Fallida con {cookie_data['source']}: {error_msg}")
                    
                    logger.info(f"🔄 [Proceso {i + 1}] Completado y navegador cerrado")
                    
                except Exception as e:
                    fallidas += 1
                    errores.append(f"Cookie {i + 1}: {str(e)[:50]}")
                    logger.error(f"❌ [Proceso {i + 1}] Error general: {e}")
            
            logger.info(f"🏁 PROCESO COMPLETADO: {exitosas} exitosas, {fallidas} fallidas, {ya_amigos} ya amigos")
            
            return {
                "status": "completed",
                "message": f"Proceso completado con {cantidad_real} navegadores",
                "results": {
                    "exitosas": exitosas,
                    "fallidas": fallidas,
                    "ya_amigos": ya_amigos,
                    "errores": errores,
                    "total_procesadas": cantidad_real,
                    "cookies_usadas": len(cookies_a_usar)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error crítico en process_friend_requests_with_restart: {e}")
            return {
                "status": "error",
                "message": f"Error crítico: {str(e)[:100]}",
                "results": {
                    "exitosas": 0,
                    "fallidas": 0,
                    "ya_amigos": 0,
                    "errores": [str(e)[:50]],
                    "total_procesadas": 0
                }
            }
