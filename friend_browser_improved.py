
import asyncio
import time
import random
import os
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, NoSuchElementException
import logging

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
    
    async def handle_potential_overlay(self, driver):
        """Manejar overlays que pueden bloquear elementos"""
        try:
            # Cerrar posibles modales o overlays
            overlay_selectors = [
                ".modal-overlay",
                ".cookie-banner",
                "#cookie-banner",
                ".notification-banner",
                ".age-verification-modal",
                "[data-testid='close-button']",
                ".close-button",
                "button[aria-label='Close']"
            ]
            
            for selector in overlay_selectors:
                try:
                    overlay = driver.find_element(By.CSS_SELECTOR, selector)
                    if overlay.is_displayed():
                        overlay.click()
                        logger.info(f"🗂️ Overlay cerrado: {selector}")
                        await asyncio.sleep(1)
                except:
                    continue
                    
        except Exception as e:
            logger.debug(f"No hay overlays que cerrar: {e}")
    
    async def scroll_and_click_element(self, driver, element):
        """Hacer scroll y clic en un elemento de manera más robusta"""
        try:
            # Método 1: Scroll directo al elemento
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            await asyncio.sleep(2)
            
            # Método 2: Intentar clic directo
            try:
                element.click()
                logger.info("✅ Clic directo exitoso")
                return True
            except ElementClickInterceptedException:
                logger.warning("⚠️ Clic interceptado, probando alternativas...")
            
            # Método 3: JavaScript click
            try:
                driver.execute_script("arguments[0].click();", element)
                logger.info("✅ Clic por JavaScript exitoso")
                return True
            except Exception as js_error:
                logger.warning(f"⚠️ Clic por JS falló: {js_error}")
            
            # Método 4: Action Chains
            try:
                actions = ActionChains(driver)
                actions.move_to_element(element).click().perform()
                logger.info("✅ Clic por ActionChains exitoso")
                return True
            except Exception as action_error:
                logger.warning(f"⚠️ ActionChains falló: {action_error}")
            
            # Método 5: Clic forzado con coordenadas
            try:
                location = element.location_once_scrolled_into_view
                size = element.size
                x = location['x'] + size['width'] // 2
                y = location['y'] + size['height'] // 2
                
                actions = ActionChains(driver)
                actions.move_by_offset(x, y).click().perform()
                logger.info("✅ Clic por coordenadas exitoso")
                return True
            except Exception as coord_error:
                logger.warning(f"⚠️ Clic por coordenadas falló: {coord_error}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error en scroll_and_click_element: {e}")
            return False
    
    async def find_add_friend_button(self, driver):
        """Buscar el botón de Add Friend con múltiples estrategias"""
        try:
            # Estrategia 1: Selectores CSS específicos
            css_selectors = [
                "button[data-testid='add-friend-button']",
                "button#friend-button",
                ".btn-add-friend",
                "button[aria-label*='Add Friend']",
                "button[aria-label*='Agregar']",
                "button.btn-primary-md",
                "#add-friend-button"
            ]
            
            for selector in css_selectors:
                try:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                    if button and button.is_displayed() and button.is_enabled():
                        logger.info(f"✅ Botón encontrado con CSS: {selector}")
                        return button
                except:
                    continue
            
            # Estrategia 2: Buscar por texto en botones
            text_variations = [
                "Add Friend", "add friend", "ADD FRIEND",
                "Agregar Amigo", "agregar amigo", "AGREGAR AMIGO",
                "Follow", "Seguir", "FOLLOW", "SEGUIR"
            ]
            
            all_buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in all_buttons:
                try:
                    button_text = button.text.strip()
                    if any(text in button_text for text in text_variations):
                        if button.is_displayed() and button.is_enabled():
                            logger.info(f"✅ Botón encontrado por texto: '{button_text}'")
                            return button
                except:
                    continue
            
            # Estrategia 3: XPath más específico
            xpath_selectors = [
                "//button[contains(text(), 'Add Friend')]",
                "//button[contains(text(), 'add friend')]",
                "//button[contains(text(), 'Agregar')]",
                "//button[contains(@aria-label, 'Add Friend')]",
                "//button[contains(@class, 'friend')]",
                "//a[contains(@class, 'btn') and contains(text(), 'Add Friend')]"
            ]
            
            for xpath in xpath_selectors:
                try:
                    button = driver.find_element(By.XPATH, xpath)
                    if button and button.is_displayed() and button.is_enabled():
                        logger.info(f"✅ Botón encontrado con XPath: {xpath}")
                        return button
                except:
                    continue
            
            logger.warning("❌ No se encontró el botón de Add Friend")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error buscando botón de Add Friend: {e}")
            return None
    
    async def send_friend_request_improved(self, user_id, cookie_data, attempt_index, total_attempts):
        """Enviar friend request con manejo mejorado de errores de UI"""
        driver = None
        try:
            logger.info(f"🚀 [Cookie {attempt_index + 1}/{total_attempts}] Iniciando proceso mejorado para {cookie_data['source']}")
            
            # PASO 1: Crear navegador nuevo
            driver = self.scraper.create_driver()
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            logger.info(f"✅ [Cookie {attempt_index + 1}] Navegador creado")
            
            # PASO 2: Aplicar cookie
            logger.info(f"🍪 [Cookie {attempt_index + 1}] Aplicando cookie...")
            
            driver.get("https://www.roblox.com")
            await asyncio.sleep(3)
            
            cookie_dict = {
                'name': '.ROBLOSECURITY',
                'value': cookie_data['cookie'],
                'domain': '.roblox.com',
                'path': '/',
                'secure': True,
                'httpOnly': True
            }
            
            try:
                driver.add_cookie(cookie_dict)
                logger.info(f"✅ [Cookie {attempt_index + 1}] Cookie aplicada")
            except Exception as cookie_error:
                logger.warning(f"⚠️ [Cookie {attempt_index + 1}] Error aplicando cookie: {cookie_error}")
                return {"status": "error", "message": f"Error aplicando cookie: {str(cookie_error)[:50]}"}
            
            driver.refresh()
            await asyncio.sleep(3)
            
            # PASO 3: Navegar al perfil
            profile_url = f"https://www.roblox.com/users/{user_id}/profile"
            logger.info(f"🔗 [Cookie {attempt_index + 1}] Navegando a perfil...")
            
            driver.get(profile_url)
            await asyncio.sleep(5)
            
            # PASO 4: Manejar overlays
            await self.handle_potential_overlay(driver)
            
            # PASO 5: Buscar botón de Add Friend
            logger.info(f"🔍 [Cookie {attempt_index + 1}] Buscando botón de Add Friend...")
            
            friend_button = await self.find_add_friend_button(driver)
            
            if not friend_button:
                # Verificar si ya son amigos
                page_source = driver.page_source.lower()
                if any(phrase in page_source for phrase in ["already friends", "ya son amigos", "friends"]):
                    logger.info(f"👥 [Cookie {attempt_index + 1}] Ya son amigos")
                    return {"status": "already_friends", "message": "Users are already friends"}
                else:
                    logger.warning(f"❌ [Cookie {attempt_index + 1}] Botón de Add Friend no encontrado")
                    return {"status": "error", "message": "Add Friend button not found"}
            
            # PASO 6: Hacer clic en el botón con método mejorado
            logger.info(f"🖱️ [Cookie {attempt_index + 1}] Intentando hacer clic en botón...")
            
            click_success = await self.scroll_and_click_element(driver, friend_button)
            
            if not click_success:
                logger.warning(f"❌ [Cookie {attempt_index + 1}] No se pudo hacer clic en el botón")
                return {"status": "error", "message": "Could not click Add Friend button"}
            
            # PASO 7: Verificar resultado
            await asyncio.sleep(4)
            
            page_source = driver.page_source.lower()
            success_indicators = [
                "friend request sent", "solicitud enviada", "pending", "pendiente",
                "request sent", "solicitud enviada"
            ]
            
            if any(indicator in page_source for indicator in success_indicators):
                logger.info(f"✅ [Cookie {attempt_index + 1}] Friend request enviado exitosamente")
                return {"status": "success", "message": "Friend request sent successfully"}
            
            # Verificar si ya son amigos después del clic
            already_friends_indicators = [
                "already friends", "ya son amigos", "friends", "amigos"
            ]
            
            if any(indicator in page_source for indicator in already_friends_indicators):
                logger.info(f"👥 [Cookie {attempt_index + 1}] Ya son amigos")
                return {"status": "already_friends", "message": "Users are already friends"}
            
            logger.warning(f"⚠️ [Cookie {attempt_index + 1}] Estado del friend request incierto")
            return {"status": "success", "message": "Friend request attempted (status unclear)"}
            
        except Exception as e:
            logger.error(f"❌ [Cookie {attempt_index + 1}] Error general: {e}")
            return {"status": "error", "message": f"General error: {str(e)[:50]}"}
        
        finally:
            # PASO 8: Cerrar navegador
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
                    logger.warning(f"⚠️ [Cookie {attempt_index + 1}] Error cerrando: {close_error}")
    
    async def process_friend_requests_improved(self, user_id, cantidad):
        """Procesar friend requests con sistema mejorado"""
        try:
            cookies_disponibles = self.extract_cookies_from_sources()
            
            if not cookies_disponibles:
                return {
                    "status": "error",
                    "message": "No se encontraron cookies válidas",
                    "results": {
                        "exitosas": 0,
                        "fallidas": 0,
                        "ya_amigos": 0,
                        "errores": []
                    }
                }
            
            cantidad_real = min(cantidad, len(cookies_disponibles))
            cookies_a_usar = cookies_disponibles[:cantidad_real]
            
            logger.info(f"🚀 Iniciando {cantidad_real} friend requests con sistema MEJORADO")
            
            exitosas = 0
            fallidas = 0
            ya_amigos = 0
            errores = []
            
            for i, cookie_data in enumerate(cookies_a_usar):
                try:
                    logger.info(f"🔄 [Proceso {i + 1}/{cantidad_real}] Procesando {cookie_data['source']}")
                    
                    resultado = await self.send_friend_request_improved(
                        user_id, cookie_data, i, cantidad_real
                    )
                    
                    if resultado and resultado["status"] == "success":
                        exitosas += 1
                        logger.info(f"✅ [Proceso {i + 1}] Exitoso")
                        
                    elif resultado and resultado["status"] == "already_friends":
                        ya_amigos += 1
                        logger.info(f"👥 [Proceso {i + 1}] Ya amigos")
                        
                    else:
                        fallidas += 1
                        error_msg = resultado["message"] if resultado else "Error desconocido"
                        errores.append(f"Cookie {i + 1}: {error_msg[:50]}")
                        logger.warning(f"❌ [Proceso {i + 1}] Fallido: {error_msg}")
                    
                except Exception as e:
                    fallidas += 1
                    errores.append(f"Cookie {i + 1}: {str(e)[:50]}")
                    logger.error(f"❌ [Proceso {i + 1}] Error: {e}")
            
            logger.info(f"🏁 PROCESO COMPLETADO: {exitosas} exitosas, {fallidas} fallidas, {ya_amigos} ya amigos")
            
            return {
                "status": "completed",
                "message": f"Proceso completado con sistema mejorado",
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
            logger.error(f"❌ Error crítico en process_friend_requests_improved: {e}")
            return {
                "status": "error",
                "message": f"Error crítico: {str(e)[:100]}",
                "results": {
                    "exitosas": 0,
                    "fallidas": 0,
                    "ya_amigos": 0,
                    "errores": [str(e)[:50]]
                }
            }
