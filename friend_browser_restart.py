
import asyncio
import random
import time
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class FriendRequestBrowserRestart:
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
    
    async def send_friend_request_with_full_restart(self, user_id, cookie_data, attempt_index, total_attempts):
        """Enviar friend request con navegador completamente nuevo para cada cookie"""
        driver = None
        try:
            logger.info(f"🚀 [Cookie {attempt_index + 1}/{total_attempts}] Iniciando navegador COMPLETAMENTE NUEVO para {cookie_data['source']}")
            
            # PASO 1: Crear navegador completamente nuevo
            driver = self.scraper.create_driver()
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            logger.info(f"✅ [Cookie {attempt_index + 1}] Navegador nuevo creado exitosamente")
            
            # PASO 2: Aplicar cookie específica
            logger.info(f"🍪 [Cookie {attempt_index + 1}] Aplicando cookie {cookie_data['source']}...")
            
            # Navegar a Roblox para aplicar cookies
            driver.get("https://www.roblox.com")
            await asyncio.sleep(3)
            
            # Agregar la cookie
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
                logger.info(f"✅ [Cookie {attempt_index + 1}] Cookie aplicada exitosamente")
            except Exception as cookie_error:
                logger.warning(f"⚠️ [Cookie {attempt_index + 1}] Error aplicando cookie: {cookie_error}")
                return {"status": "error", "message": f"Error aplicando cookie: {str(cookie_error)[:50]}"}
            
            # Refrescar para aplicar la cookie
            driver.refresh()
            await asyncio.sleep(3)
            
            # PASO 3: Navegar al perfil del usuario objetivo
            profile_url = f"https://www.roblox.com/users/{user_id}/profile"
            logger.info(f"🔗 [Cookie {attempt_index + 1}] Navegando al perfil: {profile_url}")
            
            driver.get(profile_url)
            await asyncio.sleep(5)
            
            # PASO 4: Buscar y hacer clic en el botón de Add Friend
            try:
                # Selectores posibles para el botón de agregar amigo
                friend_button_selectors = [
                    "button[data-testid='add-friend-button']",
                    ".btn-add-friend",
                    "button.btn-primary-md",
                    "#add-friend-button"
                ]
                
                friend_button = None
                for selector in friend_button_selectors:
                    try:
                        friend_button = driver.find_element("css selector", selector)
                        if friend_button and friend_button.is_displayed():
                            logger.info(f"✅ [Cookie {attempt_index + 1}] Botón encontrado con selector: {selector}")
                            break
                    except:
                        continue
                
                if not friend_button:
                    # Buscar por texto en todos los botones
                    try:
                        all_buttons = driver.find_elements("tag name", "button")
                        for button in all_buttons:
                            button_text = button.text.lower()
                            if any(phrase in button_text for phrase in ['add friend', 'agregar amigo', 'seguir']):
                                friend_button = button
                                logger.info(f"✅ [Cookie {attempt_index + 1}] Botón encontrado por texto: {button.text}")
                                break
                    except Exception as e:
                        logger.debug(f"Error buscando botones por texto: {e}")
                
                if friend_button:
                    # Hacer scroll al botón si es necesario
                    driver.execute_script("arguments[0].scrollIntoView(true);", friend_button)
                    await asyncio.sleep(1)
                    
                    # Hacer clic en el botón
                    friend_button.click()
                    logger.info(f"✅ [Cookie {attempt_index + 1}] Botón de Add Friend clickeado exitosamente")
                    
                    # Esperar un momento para que se procese la request
                    await asyncio.sleep(4)
                    
                    # Verificar si la solicitud fue exitosa
                    try:
                        success_indicators = [
                            "friend request sent", "solicitud enviada", "pending", "pendiente"
                        ]
                        
                        page_text = driver.page_source.lower()
                        request_sent = any(indicator.lower() in page_text for indicator in success_indicators)
                        
                        if request_sent:
                            logger.info(f"✅ [Cookie {attempt_index + 1}] Friend request enviado exitosamente")
                            return {"status": "success", "message": "Friend request sent successfully"}
                        else:
                            # Verificar si ya son amigos
                            already_friends_indicators = [
                                "already friends", "ya son amigos", "friends", "amigos"
                            ]
                            
                            if any(indicator in page_text for indicator in already_friends_indicators):
                                logger.info(f"👥 [Cookie {attempt_index + 1}] Los usuarios ya son amigos")
                                return {"status": "already_friends", "message": "Users are already friends"}
                            else:
                                logger.warning(f"⚠️ [Cookie {attempt_index + 1}] No se pudo confirmar el envío")
                                return {"status": "success", "message": "Friend request attempted, status unclear"}
                                
                    except Exception as verify_error:
                        logger.debug(f"Error verificando resultado: {verify_error}")
                        return {"status": "success", "message": "Friend request sent (verification failed)"}
                
                else:
                    logger.warning(f"❌ [Cookie {attempt_index + 1}] No se encontró el botón de Add Friend")
                    return {"status": "error", "message": "Add Friend button not found"}
                    
            except Exception as e:
                logger.error(f"❌ [Cookie {attempt_index + 1}] Error interactuando con la página: {e}")
                return {"status": "error", "message": f"Page interaction error: {str(e)[:50]}"}
        
        except Exception as e:
            logger.error(f"❌ [Cookie {attempt_index + 1}] Error general: {e}")
            return {"status": "error", "message": f"General error: {str(e)[:50]}"}
        
        finally:
            # PASO 5: CERRAR NAVEGADOR COMPLETAMENTE (MUY IMPORTANTE)
            if driver:
                try:
                    logger.info(f"🔒 [Cookie {attempt_index + 1}] Cerrando navegador COMPLETAMENTE...")
                    driver.quit()
                    logger.info(f"✅ [Cookie {attempt_index + 1}] Navegador cerrado exitosamente")
                    
                    # Pausa adicional para asegurar que el proceso se cierre completamente
                    if attempt_index < total_attempts - 1:  # No pausar después de la última
                        pause_time = 5 + random.randint(1, 2)  # 6-7 segundos
                        logger.info(f"⏳ [Cookie {attempt_index + 1}] Pausa de {pause_time}s antes del siguiente navegador...")
                        await asyncio.sleep(pause_time)
                        
                except Exception as close_error:
                    logger.warning(f"⚠️ [Cookie {attempt_index + 1}] Error cerrando navegador: {close_error}")
    
    async def process_friend_requests_with_restart(self, user_id, cantidad):
        """Procesar múltiples friend requests con reinicio completo del navegador"""
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
                        "errores": []
                    }
                }
            
            # Limitar cantidad a las cookies disponibles
            cantidad_real = min(cantidad, len(cookies_disponibles))
            cookies_a_usar = cookies_disponibles[:cantidad_real]
            
            logger.info(f"🚀 Iniciando {cantidad_real} friend requests con REINICIO COMPLETO del navegador")
            logger.info(f"🍪 Cookies a usar: {[c['source'] for c in cookies_a_usar]}")
            
            # Contadores de resultados
            exitosas = 0
            fallidas = 0
            ya_amigos = 0
            errores = []
            
            # Procesar cada cookie con navegador completamente nuevo
            for i, cookie_data in enumerate(cookies_a_usar):
                try:
                    logger.info(f"🔄 [Proceso {i + 1}/{cantidad_real}] INICIANDO NUEVO NAVEGADOR para {cookie_data['source']}")
                    
                    # Enviar friend request con navegador nuevo
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
                        logger.warning(f"❌ [Proceso {i + 1}] Solicitud fallida con {cookie_data['source']}: {error_msg}")
                    
                    # El navegador ya se cerró en la función anterior
                    logger.info(f"🔄 [Proceso {i + 1}] Proceso completado. Navegador cerrado.")
                    
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
                    "errores": [str(e)[:50]]
                }
            }
