#!/usr/bin/env python3
"""
Framework independiente de scraping para RbxServers
Obtiene servidores VIP y los envía directamente a la API de Vercel
Sin necesidad de ejecutar el bot de Discord completo
"""

import asyncio
import json
import logging
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import random
import sys
import os
import threading

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('standalone_scraper.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class StandaloneScraper:
    """Framework independiente de scraping para RbxServers"""

    def __init__(self, game_id: str = "109983668079237"):
        self.game_id = game_id
        self.api_url = "https://v0-discord-bot-api-snowy.vercel.app/api/data"
        self.cookies_file = "roblox_cookies.json"
        self.roblox_cookies = {}
        self.scraped_servers = []

        # User Agents para rotación
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        ]
        self.current_user_agent = self.user_agents[0]
        self.server_count_since_ua_change = 0
        self.server_change_interval = 30 # Cambiar cada 30 servidores

        # Estadísticas de scraping
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_servers_found': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'api_send_success': False,
            'duration': 0
        }

        logger.info(f"🚀 Framework de scraping independiente inicializado para juego {game_id}")
        self.load_roblox_cookies()

    def load_roblox_cookies(self):
        """Cargar cookies de Roblox desde archivo"""
        try:
            if Path(self.cookies_file).exists():
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.roblox_cookies = data.get('cookies', {})
                    logger.info(f"Cargadas cookies de Roblox para {len(self.roblox_cookies)} dominios")
            else:
                logger.warning(f"Archivo de cookies {self.cookies_file} no encontrado")

                # Intentar cargar desde Cookiesnew.md
                self.extract_cookies_from_cookiesnew()
        except Exception as e:
            logger.error(f"Error cargando cookies: {e}")
            self.roblox_cookies = {}

    def extract_cookies_from_cookiesnew(self):
        """Extraer cookies del archivo Cookiesnew.md"""
        try:
            cookiesnew_path = Path("Cookiesnew.md")
            if not cookiesnew_path.exists():
                logger.warning("Archivo Cookiesnew.md no encontrado")
                return 0

            with open(cookiesnew_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Buscar patrones de cookies de Roblox con el patrón correcto
            cookie_pattern = r'_\|WARNING:.*?\|_([A-Z0-9]+\.[A-Za-z0-9\-_]+)'
            import re
            cookie_matches = re.findall(cookie_pattern, content)

            if cookie_matches:
                # Usar la primera cookie encontrada
                roblox_cookie = cookie_matches[0]

                # Inicializar estructura de cookies
                self.roblox_cookies = {
                    'roblox.com': {
                        '.ROBLOSECURITY': {
                            'value': roblox_cookie,
                            'domain': '.roblox.com',
                            'path': '/',
                            'secure': True,
                            'httpOnly': True,
                            'sameSite': 'Lax',
                            'extracted_at': datetime.now().isoformat(),
                            'source': 'Cookiesnew.md',
                            'username': 'extracted_user'
                        }
                    }
                }

                # Guardar cookies extraídas
                self.save_roblox_cookies()
                logger.info("Cookie extraída de Cookiesnew.md y guardada")
                return 1
            else:
                logger.warning("No se encontraron cookies válidas en Cookiesnew.md")
                return 0

        except Exception as e:
            logger.error(f"Error extrayendo cookies de Cookiesnew.md: {e}")
            return 0

    def save_roblox_cookies(self):
        """Guardar cookies a archivo"""
        try:
            cookies_data = {
                'cookies': self.roblox_cookies,
                'last_updated': datetime.now().isoformat(),
                'total_domains': len(self.roblox_cookies)
            }

            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, indent=2)
            logger.info(f"Cookies guardadas en {self.cookies_file}")

        except Exception as e:
            logger.error(f"Error guardando cookies: {e}")

    def update_user_agent(self):
        """Actualiza el User-Agent actual a uno nuevo de la lista"""
        if len(self.user_agents) > 1:
            self.current_user_agent = random.choice(self.user_agents)
            logger.info(f"User-Agent actualizado a: {self.current_user_agent}")
        else:
            logger.warning("Solo hay un User-Agent disponible, no se puede rotar.")

    def create_driver(self, retry_count: int = 0, max_retries: int = 5):
        """Crear driver de Chrome optimizado con manejo robusto de errores de Selenium"""
        driver = None
        try:
            logger.info(f"Creating Chrome driver... (Attempt {retry_count + 1}/{max_retries + 1})")

            # Limpiar procesos Chrome previos si es necesario
            if retry_count > 0:
                try:
                    import subprocess
                    subprocess.run(['pkill', '-f', 'chrome'], capture_output=True, timeout=5)
                    time.sleep(1)
                except:
                    pass

            chrome_options = Options()

            # Configuración headless robusta para hosting
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--disable-crash-reporter")
            chrome_options.add_argument("--disable-in-process-stack-traces")
            chrome_options.add_argument("--disable-system-font-check")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            # Utilizar el User-Agent rotativo
            chrome_options.add_argument(f"--user-agent={self.current_user_agent}")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor,VizServiceDisplay")
            chrome_options.add_argument("--single-process")

            # Argumentos adicionales para estabilidad en entornos de hosting
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI,VizDisplayCompositor")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--disable-component-update")
            chrome_options.add_argument("--disable-background-networking")
            chrome_options.add_argument("--disable-sync")
            chrome_options.add_argument("--metrics-recording-only")
            chrome_options.add_argument("--no-report-upload")

            # Configuración optimizada para velocidad
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.cookies": 1,
                "profile.managed_default_content_settings.javascript": 1,
                "profile.managed_default_content_settings.plugins": 2,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.geolocation": 2,
                "profile.managed_default_content_settings.media_stream": 2
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Crear driver con manejo mejorado de errores
            driver = webdriver.Chrome(options=chrome_options)

            # Configurar timeouts más conservadores
            driver.set_page_load_timeout(45)
            driver.implicitly_wait(15)

            # Probar navegación básica con manejo de errores
            try:
                driver.get("about:blank")
                # Verificar que el driver responde
                _ = driver.title
                logger.info(f"Chrome driver created and tested successfully on attempt {retry_count + 1}")
                return driver
            except Exception as nav_error:
                logger.warning(f"Driver created but navigation test failed: {nav_error}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                raise nav_error

        except (WebDriverException, Exception) as e:
            error_msg = str(e).lower()
            logger.warning(f"Driver creation failed on attempt {retry_count + 1}: {e}")

            # Limpiar driver si se creó parcialmente
            if driver:
                try:
                    driver.quit()
                except:
                    pass

            # Decidir si reintentar basado en el tipo de error
            should_retry = (
                retry_count < max_retries and
                any(keyword in error_msg for keyword in ['chrome', 'selenium', 'webdriver', 'connection', 'timeout'])
            )

            if should_retry:
                wait_time = min(3 * (retry_count + 1), 10)  # Backoff exponencial limitado
                logger.info(f"Selenium error detected, waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                return self.create_driver(retry_count + 1, max_retries)
            else:
                logger.error(f"Failed to create driver after {max_retries + 1} attempts")
                raise Exception(f"Could not create Chrome driver after {max_retries + 1} attempts: {e}")

    def load_cookies_to_driver(self, driver):
        """Cargar cookies de Roblox al driver"""
        try:
            if 'roblox.com' not in self.roblox_cookies or not self.roblox_cookies['roblox.com']:
                logger.warning("No hay cookies de Roblox disponibles")
                return 0

            # Navegar a Roblox primero
            logger.info("Navegando a roblox.com para aplicar cookies...")
            driver.get("https://www.roblox.com")
            time.sleep(2)

            cookies_loaded = 0
            for cookie_name, cookie_data in self.roblox_cookies['roblox.com'].items():
                try:
                    cookie_dict = {
                        'name': cookie_name,
                        'value': cookie_data['value'],
                        'domain': cookie_data.get('domain', '.roblox.com'),
                        'path': cookie_data.get('path', '/'),
                        'secure': cookie_data.get('secure', True),
                        'httpOnly': cookie_data.get('httpOnly', True)
                    }

                    driver.add_cookie(cookie_dict)
                    cookies_loaded += 1
                    logger.info(f"Cookie aplicada: {cookie_name}")

                except Exception as e:
                    logger.warning(f"Error aplicando cookie {cookie_name}: {e}")

            if cookies_loaded > 0:
                logger.info("Refrescando página para aplicar cookies...")
                driver.refresh()
                time.sleep(3)

            logger.info(f"{cookies_loaded} cookies aplicadas exitosamente")
            return cookies_loaded

        except Exception as e:
            logger.error(f"Error cargando cookies al driver: {e}")
            return 0

    def get_server_links(self, driver, max_servers: int = 20) -> List[str]:
        """Obtener enlaces de servidores desde rbxservers.xyz"""
        try:
            url = f"https://rbxservers.xyz/games/{self.game_id}"
            logger.info(f"Obteniendo enlaces de servidores de: {url}")

            driver.get(url)

            # Esperar a que carguen los enlaces
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/servers/']")))

            # Encontrar todos los enlaces de servidores
            server_elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/servers/']")
            server_links = []

            for element in server_elements:
                link = element.get_attribute("href")
                if link and link not in server_links:
                    server_links.append(link)

                if len(server_links) >= max_servers:
                    break

            logger.info(f"Encontrados {len(server_links)} enlaces de servidores")
            return server_links

        except Exception as e:
            logger.error(f"Error obteniendo enlaces de servidores: {e}")
            return []

    def extract_vip_link(self, driver, server_url: str) -> Optional[str]:
        """Extraer link VIP de una página específica de servidor"""
        try:
            logger.debug(f"Extrayendo VIP de: {server_url}")

            driver.get(server_url)

            # Buscar el input con el link VIP
            wait = WebDriverWait(driver, 15)
            vip_input = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//input[@type='text' and contains(@value, 'https://')]")
                )
            )

            vip_link = vip_input.get_attribute("value")

            if vip_link and vip_link.startswith("https://www.roblox.com/games/"):
                logger.debug(f"VIP link extraído: {vip_link[:50]}...")
                return vip_link
            else:
                logger.debug(f"Link inválido encontrado: {vip_link}")
                return None

        except TimeoutException:
            logger.debug(f"Timeout - No se encontró VIP link en {server_url}")
            return None
        except Exception as e:
            logger.error(f"Error extrayendo VIP link de {server_url}: {e}")
            return None

    async def scrape_servers(self, target_amount: int = 10, retry_count: int = 0, max_retries: int = 2) -> List[str]:
        """Ejecutar scraping completo de servidores con reintentos automáticos"""
        try:
            self.stats['start_time'] = time.time()
            logger.info(f"Starting independent scraping for {target_amount} servers of game {self.game_id} (Attempt {retry_count + 1}/{max_retries + 1})")

            # Crear driver con reintentos automáticos
            driver = self.create_driver()

            try:
                # Cargar cookies de Roblox
                cookies_loaded = self.load_cookies_to_driver(driver)
                logger.info(f"{cookies_loaded} cookies de Roblox aplicadas")

                # Obtener enlaces de servidores
                server_links = self.get_server_links(driver, target_amount * 2)  # Obtener extras por si fallan

                if not server_links:
                    logger.error("No se encontraron enlaces de servidores")
                    return []

                self.stats['total_servers_found'] = len(server_links)

                # Extraer VIP links
                extracted_servers = []
                processed = 0

                for server_url in server_links:
                    if len(extracted_servers) >= target_amount:
                        logger.info(f"Meta alcanzada: {target_amount} servidores extraídos")
                        break

                    try:
                        processed += 1
                        logger.info(f"Procesando servidor {processed}/{len(server_links)}")

                        # Intentar extraer VIP link con reintentos robustos para errores de Selenium
                        vip_link = None
                        extraction_attempts = 0
                        max_extraction_attempts = 3

                        while extraction_attempts < max_extraction_attempts and not vip_link:
                            try:
                                vip_link = self.extract_vip_link(driver, server_url)
                                if vip_link:
                                    break
                            except (WebDriverException, TimeoutException) as selenium_error:
                                extraction_attempts += 1
                                error_msg = str(selenium_error).lower()

                                if extraction_attempts < max_extraction_attempts:
                                    wait_time = extraction_attempts  # 1s, 2s, 3s...
                                    logger.warning(f"Selenium error on extraction attempt {extraction_attempts}, waiting {wait_time}s before retry...")

                                    # Si es un error crítico de Chrome, reiniciar driver
                                    if any(keyword in error_msg for keyword in ['chrome', 'session', 'disconnected', 'crashed']):
                                        logger.warning("Critical Chrome error detected, may need driver restart")
                                        try:
                                            # Intentar recuperar el driver
                                            driver.get("about:blank")
                                        except:
                                            logger.error("Driver appears to be broken, cannot continue")
                                            break

                                    time.sleep(wait_time)
                                else:
                                    logger.error(f"Failed to extract after {max_extraction_attempts} attempts: {selenium_error}")
                            except Exception as other_error:
                                logger.error(f"Non-Selenium error during extraction: {other_error}")
                                break

                        if vip_link and vip_link not in extracted_servers:
                            extracted_servers.append(vip_link)
                            self.stats['successful_extractions'] += 1
                            logger.info(f"Server {len(extracted_servers)}/{target_amount} extracted")
                        else:
                            self.stats['failed_extractions'] += 1

                        # Actualizar User-Agent si se alcanza el intervalo
                        self.server_count_since_ua_change += 1
                        if self.server_count_since_ua_change >= self.server_change_interval:
                            self.update_user_agent()
                            self.server_count_since_ua_change = 0 # Reset counter

                        # Pausa entre extracciones
                        time.sleep(random.uniform(1, 3))

                    except Exception as e:
                        self.stats['failed_extractions'] += 1
                        logger.error(f"Error procesando {server_url}: {e}")
                        continue

                # Validar que los servidores sean enlaces válidos de Roblox
                valid_servers = [s for s in extracted_servers if s.startswith("https://www.roblox.com/games/")]
                invalid_count = len(extracted_servers) - len(valid_servers)

                if invalid_count > 0:
                    logger.warning(f"Se encontraron {invalid_count} enlaces inválidos, usando solo {len(valid_servers)} válidos")

                if not valid_servers:
                    logger.error("No se obtuvieron servidores válidos. Terminando proceso.")
                    self.stats['api_send_success'] = False
                    return []

                self.scraped_servers = valid_servers
                logger.info(f"PASO 1 COMPLETADO: {len(valid_servers)} servidores válidos obtenidos")

                return valid_servers

            finally:
                # Cerrar driver
                try:
                    driver.quit()
                    logger.info("Driver cerrado exitosamente")
                except:
                    pass

        except (WebDriverException, Exception) as e:
            logger.error(f"Critical error in scraping attempt {retry_count + 1}: {e}")

            # Si es un error de Selenium y aún tenemos reintentos disponibles
            if retry_count < max_retries and ("selenium" in str(e).lower() or "chrome" in str(e).lower() or "webdriver" in str(e).lower()):
                logger.info(f"Selenium error detected, retrying... ({retry_count + 1}/{max_retries})")
                time.sleep(3)  # Pausa antes del reintento
                return await self.scrape_servers(target_amount, retry_count + 1, max_retries)

            return []
        finally:
            self.stats['end_time'] = time.time()
            if self.stats['start_time']:
                self.stats['duration'] = self.stats['end_time'] - self.stats['start_time']

    async def get_game_info(self) -> Dict:
        """Obtener información del juego desde la API de Roblox"""
        try:
            url = f"https://games.roblox.com/v1/games?universeIds={self.game_id}"
            headers = {
                'User-Agent': self.current_user_agent # Usar el user agent actual
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                games = data.get('data', [])
                if games:
                    game_info = games[0]
                    logger.info(f"Información del juego obtenida: {game_info.get('name', 'Sin nombre')}")
                    return game_info

            logger.warning(f"No se pudo obtener info del juego {self.game_id}")
            return {
                'name': f'Juego {self.game_id}',
                'id': self.game_id,
                'description': 'Información no disponible'
            }

        except Exception as e:
            logger.error(f"Error obteniendo info del juego: {e}")
            return {
                'name': f'Juego {self.game_id}',
                'id': self.game_id,
                'description': 'Error obteniendo información'
            }

    async def send_to_vercel_api(self, servers: List[str]) -> tuple[bool, Dict]:
        """Enviar servidores a la API de Vercel"""
        try:
            logger.info(f"Enviando {len(servers)} servidores a API de Vercel: {self.api_url}")

            # Obtener información del juego
            game_info = await self.get_game_info()

            # Preparar datos para la API
            api_data = {
                "game_name": game_info.get('name', f'Juego {self.game_id}'),
                "game_id": self.game_id,
                "total_servers": len(servers),
                "scraped_at": datetime.now().isoformat(),
                "scraped_by": {
                    "system": "standalone_scraper",
                    "framework_version": "1.0",
                    "source": "independent_framework"
                },
                "servers": servers,
                "scraping_stats": self.stats,
                "metadata": {
                    "framework": "StandaloneScraper",
                    "automated": True,
                    "cookies_used": len(self.roblox_cookies.get('roblox.com', {})),
                    "extraction_success_rate": f"{(self.stats['successful_extractions'] / max(self.stats['total_servers_found'], 1)) * 100:.1f}%"
                }
            }

            # Headers para la petición
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': self.current_user_agent, # Usar el user agent actual
                'X-Framework': 'standalone'
            }

            # Hacer petición a la API
            response = requests.post(
                self.api_url,
                json=api_data,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                try:
                    response_data = response.json()
                except:
                    response_data = {"raw_response": response.text}

                logger.info(f"Datos enviados exitosamente a API de Vercel: {response.status_code}")
                self.stats['api_send_success'] = True
                return True, response_data
            else:
                logger.error(f"API responded with error: {response.status_code} - {response.text}")
                self.stats['api_send_success'] = False # Ensure api_send_success is false on API error
                return False, {"error": f"HTTP {response.status_code}", "response": response.text}

        except requests.Timeout:
            logger.error(f"Timeout enviando a API de Vercel")
            self.stats['api_send_success'] = False
            return False, {"error": "Timeout", "message": "La API no respondió en 30 segundos"}
        except Exception as e:
            logger.error(f"Error enviando a API de Vercel: {e}")
            self.stats['api_send_success'] = False
            return False, {"error": str(e), "type": type(e).__name__}

    def save_results(self, servers: List[str]):
        """Guardar resultados localmente"""
        try:
            results_data = {
                'game_id': self.game_id,
                'scraped_at': datetime.now().isoformat(),
                'total_servers': len(servers),
                'servers': servers,
                'stats': self.stats,
                'framework': 'StandaloneScraper'
            }

            # Crear carpeta Serversdb si no existe
            serversdb_dir = Path("Serversdb")
            serversdb_dir.mkdir(exist_ok=True)

            results_file = serversdb_dir / f"standalone_results_{self.game_id}_{int(time.time())}.json"

            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Resultados guardados en: {results_file}")

        except Exception as e:
            logger.error(f"Error guardando resultados: {e}")

    async def run_full_scraping(self, target_servers: int = 10):
        """Ejecutar proceso completo de scraping y envío a API"""
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO FRAMEWORK INDEPENDIENTE DE SCRAPING")
            logger.info(f"Juego: {self.game_id}")
            logger.info(f"Meta: {target_servers} servidores")
            logger.info(f"API destino: {self.api_url}")
            logger.info(f"Cookies disponibles: {len(self.roblox_cookies.get('roblox.com', {}))}")

            # Verificar si las cookies están vacías
            if not self.roblox_cookies.get('roblox.com'):
                logger.warning("No hay cookies de Roblox cargadas. Intentando extraer de Cookiesnew.md...")
                extracted = self.extract_cookies_from_cookiesnew()
                logger.info(f"Cookies extraídas: {extracted}")

            logger.info("=" * 60)

            # Paso 1: Scraping
            logger.info("Ejecutando scraping de servidores...")
            scraped_servers = await self.scrape_servers(target_servers)

            # El scraping ya valida los servidores y actualiza self.scraped_servers
            # y self.stats['api_send_success']

            if not self.scraped_servers: # Check if scraped_servers is empty after validation
                logger.error("No se obtuvieron servidores válidos para enviar. Terminando proceso.")
                return False

            logger.info(f"PASO 1 COMPLETADO: {len(self.scraped_servers)} servidores válidos obtenidos")

            # Paso 2: Envío a API
            logger.info("Enviando datos a API de Vercel...")
            success, response_data = await self.send_to_vercel_api(self.scraped_servers)

            if success:
                logger.info("PASO 2 COMPLETADO: Datos enviados exitosamente a Vercel")
            else:
                logger.error(f"PASO 2 FALLIDO: Error enviando a API - {response_data}")

            # Paso 3: Guardar resultados localmente
            logger.info("Guardando resultados localmente...")
            self.save_results(self.scraped_servers)
            logger.info("PASO 3 COMPLETADO: Resultados guardados")

            # Resumen final
            logger.info("=" * 60)
            logger.info("RESUMEN FINAL DEL FRAMEWORK INDEPENDIENTE")
            logger.info(f"Juego procesado: {self.game_id}")
            logger.info(f"Duración total: {self.stats['duration']:.1f} segundos")
            logger.info(f"Servidores encontrados: {self.stats['total_servers_found']}")
            logger.info(f"Extracciones exitosas: {self.stats['successful_extractions']}")
            logger.info(f"Extracciones fallidas: {self.stats['failed_extractions']}")
            logger.info(f"Envío a API: {'Exitoso' if self.stats['api_send_success'] else 'Fallido'}")
            # Avoid division by zero if no servers were found
            success_rate = (self.stats['successful_extractions'] / max(1, self.stats['total_servers_found'])) * 100 if self.stats['total_servers_found'] > 0 else 0
            logger.info(f"Tasa de éxito: {success_rate:.1f}%")
            logger.info("=" * 60)

            return success

        except Exception as e:
            logger.error(f"Error crítico en proceso completo: {e}")
            return False

async def main():
    """Función principal del framework independiente"""
    try:
        # Configuración
        GAME_ID = "109983668079237"  # Juego por defecto
        TARGET_SERVERS = 15  # Cantidad de servidores a obtener

        # Permitir configuración por argumentos de línea de comandos
        if len(sys.argv) > 1:
            GAME_ID = sys.argv[1]
        if len(sys.argv) > 2:
            try:
                TARGET_SERVERS = int(sys.argv[2])
            except ValueError:
                logger.warning(f"Cantidad inválida: {sys.argv[2]}, usando {TARGET_SERVERS}")

        # Crear framework
        scraper = StandaloneScraper(GAME_ID)

        # Ejecutar scraping completo
        success = await scraper.run_full_scraping(TARGET_SERVERS)

        if success:
            logger.info("Framework independiente ejecutado exitosamente")
            return 0
        else:
            logger.error("Framework independiente falló")
            return 1

    except KeyboardInterrupt:
        logger.info("Framework detenido por el usuario")
        return 0
    except Exception as e:
        logger.error(f"Error crítico en main: {e}")
        return 1

if __name__ == "__main__":
    print("Framework Independiente de Scraping RbxServers")
    print("=" * 50)
    print("Uso:")
    print("  python3 standalone_scraper.py [game_id] [cantidad]")
    print("Ejemplo:")
    print("  python3 standalone_scraper.py 109983668079237 15")
    print("=" * 50)

    # Ejecutar framework
    exit_code = asyncio.run(main())
    sys.exit(exit_code)