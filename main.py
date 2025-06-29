

import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Dict, Optional
import logging

import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VIPServerScraper:
    def __init__(self):
        self.vip_links_file = "vip_links.json"
        self.unique_vip_links: Set[str] = set()
        self.server_details: Dict[str, Dict] = {}
        self.scraping_stats = {
            'total_scraped': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'last_scrape_time': None,
            'scrape_duration': 0,
            'servers_per_minute': 0
        }
        self.load_existing_links()
        
    def load_existing_links(self):
        """Load existing VIP links from JSON file"""
        try:
            if Path(self.vip_links_file).exists():
                with open(self.vip_links_file, 'r') as f:
                    data = json.load(f)
                    self.unique_vip_links = set(data.get('links', []))
                    self.server_details = data.get('server_details', {})
                    self.scraping_stats = data.get('scraping_stats', self.scraping_stats)
                    logger.info(f"Loaded {len(self.unique_vip_links)} existing VIP links")
        except Exception as e:
            logger.error(f"Error loading existing links: {e}")
    
    def save_links(self):
        """Save VIP links to JSON file"""
        try:
            data = {
                'links': list(self.unique_vip_links),
                'server_details': self.server_details,
                'scraping_stats': self.scraping_stats,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.unique_vip_links)
            }
            with open(self.vip_links_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.unique_vip_links)} VIP links to {self.vip_links_file}")
        except Exception as e:
            logger.error(f"Error saving links: {e}")
    
    def create_driver(self):
        """Create Chrome driver with Replit-compatible configuration"""
        try:
            logger.info("🚀 Creating Chrome driver for Replit...")
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
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
            
            # Disable images and JavaScript for faster loading
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.managed_default_content_settings.cookies": 2,
                "profile.managed_default_content_settings.javascript": 1,
                "profile.managed_default_content_settings.plugins": 2,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.geolocation": 2,
                "profile.managed_default_content_settings.media_stream": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Try to find Chrome/Chromium binary
            possible_chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/chromium-browser", 
                "/usr/bin/chromium",
                "/snap/bin/chromium"
            ]
            
            chrome_binary = None
            for path in possible_chrome_paths:
                if Path(path).exists():
                    chrome_binary = path
                    break
            
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Using Chrome binary at: {chrome_binary}")
            
            # Create driver with Service
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                logger.info("Using ChromeDriverManager")
            except Exception:
                # Fallback to system chromedriver
                service = Service()
                logger.info("Using system chromedriver")
            
            # Create driver
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            # Execute script to hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Chrome driver created successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Error creating Chrome driver: {e}")
            # Try minimal fallback configuration
            try:
                logger.info("🔄 Trying minimal fallback configuration...")
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                logger.info("✅ Chrome driver created with minimal configuration")
                return driver
            except Exception as e2:
                logger.error(f"Minimal fallback also failed: {e2}")
                raise Exception(f"Chrome driver creation failed: {e}")
    
    def get_server_links(self, driver, max_retries=3):
        """Get server links with retry mechanism"""
        url = "https://rbxservers.xyz/games/109983668079237"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 Fetching server links (attempt {attempt + 1}/{max_retries})")
                driver.get(url)
                
                # Wait for server elements to load
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/servers/']")))
                
                server_elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/servers/']")
                server_links = []
                
                for el in server_elements:
                    link = el.get_attribute("href")
                    if link and link not in server_links:
                        server_links.append(link)
                
                logger.info(f"✅ Found {len(server_links)} server links")
                return server_links
                
            except TimeoutException:
                logger.warning(f"⏰ Timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(3)
            except WebDriverException as e:
                logger.error(f"🚫 WebDriver error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(3)
        
        return []
    
    def extract_vip_link(self, driver, server_url, max_retries=2):
        """Extract VIP link from server page with detailed information"""
        start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                driver.get(server_url)
                
                # Wait for VIP input to load
                wait = WebDriverWait(driver, 15)
                vip_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[@type='text' and contains(@value, 'https://')]")
                    )
                )
                
                vip_link = vip_input.get_attribute("value")
                if vip_link and vip_link.startswith("https://"):
                    # Extract additional server details
                    server_info = self.extract_server_info(driver, server_url)
                    extraction_time = time.time() - start_time
                    
                    # Store detailed information
                    self.server_details[vip_link] = {
                        'source_url': server_url,
                        'discovered_at': datetime.now().isoformat(),
                        'extraction_time': round(extraction_time, 2),
                        'server_info': server_info
                    }
                    
                    return vip_link
                    
            except TimeoutException:
                logger.debug(f"⏰ No VIP link found in {server_url} (attempt {attempt + 1})")
            except Exception as e:
                logger.debug(f"❌ Error extracting VIP link from {server_url}: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(2)
        
        return None
    
    def extract_server_info(self, driver, server_url):
        """Extract additional server information"""
        try:
            info = {}
            
            # Try to get server name/title
            try:
                title_element = driver.find_element(By.TAG_NAME, "title")
                info['page_title'] = title_element.get_attribute("textContent")
            except:
                info['page_title'] = "Unknown"
            
            # Try to get server description or other details
            try:
                # Look for common server info elements
                server_elements = driver.find_elements(By.CSS_SELECTOR, ".server-info, .description, .details")
                if server_elements:
                    info['description'] = server_elements[0].text[:200]  # Limit to 200 chars
            except:
                info['description'] = "No description available"
            
            # Extract server ID from URL
            server_id = server_url.split('/')[-1] if '/' in server_url else "unknown"
            info['server_id'] = server_id
            
            return info
            
        except Exception as e:
            logger.debug(f"Could not extract server info: {e}")
            return {'server_id': 'unknown', 'page_title': 'Unknown', 'description': 'No info available'}
    
    def scrape_vip_links(self):
        """Main scraping function with detailed statistics"""
        driver = None
        start_time = time.time()
        new_links_count = 0
        processed_count = 0
        
        try:
            logger.info("🚀 Starting VIP server scraping...")
            driver = self.create_driver()
            server_links = self.get_server_links(driver)
            
            if not server_links:
                logger.warning("⚠️ No server links found")
                return
            
            logger.info(f"🎯 Processing {len(server_links)} server links...")
            
            for i, server_url in enumerate(server_links):
                try:
                    processed_count += 1
                    vip_link = self.extract_vip_link(driver, server_url)
                    
                    if vip_link and vip_link not in self.unique_vip_links:
                        self.unique_vip_links.add(vip_link)
                        new_links_count += 1
                        logger.info(f"🎉 New VIP link found ({new_links_count}): {vip_link}")
                    elif vip_link:
                        logger.debug(f"🔄 Duplicate link skipped: {vip_link}")
                    
                    # Progress indicator with ETA
                    if (i + 1) % 3 == 0:
                        elapsed = time.time() - start_time
                        eta = (elapsed / (i + 1)) * (len(server_links) - i - 1)
                        logger.info(f"📊 Progress: {i + 1}/{len(server_links)} | New: {new_links_count} | ETA: {eta:.1f}s")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {server_url}: {e}")
                    continue
            
            # Update statistics
            total_time = time.time() - start_time
            self.scraping_stats.update({
                'total_scraped': self.scraping_stats['total_scraped'] + processed_count,
                'successful_extractions': self.scraping_stats['successful_extractions'] + new_links_count,
                'failed_extractions': self.scraping_stats['failed_extractions'] + (processed_count - new_links_count),
                'last_scrape_time': datetime.now().isoformat(),
                'scrape_duration': round(total_time, 2),
                'servers_per_minute': round((processed_count / total_time) * 60, 1) if total_time > 0 else 0
            })
            
            logger.info(f"✅ Scraping completed in {total_time:.1f}s")
            logger.info(f"📈 Found {new_links_count} new VIP links (Total: {len(self.unique_vip_links)})")
            logger.info(f"⚡ Processing speed: {self.scraping_stats['servers_per_minute']} servers/minute")
            
            self.save_links()
            
        except Exception as e:
            logger.error(f"💥 Scraping failed: {e}")
            raise
        finally:
            if driver:
                driver.quit()
    
    def get_random_link(self):
        """Get a random VIP link with its details"""
        if not self.unique_vip_links:
            return None, None
        
        link = random.choice(list(self.unique_vip_links))
        details = self.server_details.get(link, {})
        return link, details
    
    def get_all_links(self):
        """Get all VIP links"""
        return list(self.unique_vip_links)

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Global scraper instance
scraper = VIPServerScraper()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is ready with {len(scraper.unique_vip_links)} VIP links loaded')
    
    # Sync slash commands after bot is ready
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.tree.command(name="servertest", description="Get a random VIP server link")
async def servertest(interaction: discord.Interaction):
    """Send a random VIP server link with professional design"""
    await interaction.response.defer()
    
    try:
        vip_link, details = scraper.get_random_link()
        
        if vip_link:
            # Create professional embed similar to the image
            embed = discord.Embed(
                title="Account Generated",
                description="Your account has been successfully generated! Keep it safe and **do not share it with anyone.**",
                color=0x2F3136
            )
            
            # Server details section with more information
            if details:
                server_info = details.get('server_info', {})
                server_id = server_info.get('server_id', 'Unknown')
                discovered_time = details.get('discovered_at', 'Unknown')
                
                # Format discovery time
                if discovered_time != 'Unknown':
                    try:
                        discovery_dt = datetime.fromisoformat(discovered_time)
                        time_ago = datetime.now() - discovery_dt
                        if time_ago.days > 0:
                            time_str = f"{time_ago.days} días"
                        elif time_ago.seconds > 3600:
                            time_str = f"{time_ago.seconds//3600} horas"
                        else:
                            time_str = f"{time_ago.seconds//60} minutos"
                        discovered_time = f"Hace {time_str}"
                    except:
                        discovered_time = "Recientemente"
                
                embed.add_field(name="🆔 Server ID", value=f"`{server_id}`", inline=True)
                embed.add_field(name="⏰ Descubierto", value=discovered_time, inline=True)
                embed.add_field(name="📊 Base de Datos", value=f"{len(scraper.unique_vip_links)} servidores", inline=True)
            
            # Additional stats
            total_scraped = scraper.scraping_stats.get('total_scraped', 0)
            successful = scraper.scraping_stats.get('successful_extractions', 0)
            if total_scraped > 0:
                success_rate = (successful / total_scraped) * 100
                embed.add_field(name="✅ Tasa de Éxito", value=f"{success_rate:.1f}%", inline=True)
            
            # Last scrape info
            last_scrape = scraper.scraping_stats.get('last_scrape_time')
            if last_scrape:
                try:
                    last_dt = datetime.fromisoformat(last_scrape)
                    time_since = datetime.now() - last_dt
                    if time_since.days > 0:
                        last_str = f"Hace {time_since.days} días"
                    elif time_since.seconds > 3600:
                        last_str = f"Hace {time_since.seconds//3600} horas"
                    else:
                        last_str = f"Hace {time_since.seconds//60} minutos"
                    embed.add_field(name="🔄 Último Scrape", value=last_str, inline=True)
                except:
                    pass
            
            # Speed info
            speed = scraper.scraping_stats.get('servers_per_minute', 0)
            if speed > 0:
                embed.add_field(name="⚡ Velocidad", value=f"{speed} serv/min", inline=True)
            
            # Source website
            embed.add_field(name="🌐 Fuente", value="rbxservers.xyz", inline=False)
            
            # Create view with buttons
            view = discord.ui.View(timeout=None)
            
            # VIP Server button
            vip_button = discord.ui.Button(
                label="Acceder al Servidor VIP",
                style=discord.ButtonStyle.secondary,
                url=vip_link
            )
            view.add_item(vip_button)
            
            # Follow hesiz button
            follow_button = discord.ui.Button(
                label="Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            view.add_item(follow_button)
            
            await interaction.followup.send(embed=embed, view=view)
            
        else:
            embed = discord.Embed(
                title="No VIP Links Available",
                description="No se encontraron servidores VIP en la base de datos. Intenta ejecutar `/scrape` primero.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error in servertest command: {e}")
        error_embed = discord.Embed(
            title="Error Occurred",
            description="Ocurrió un error al obtener el servidor.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="scrape", description="Start scraping for new VIP server links")
async def scrape_command(interaction: discord.Interaction):
    """Manually trigger scraping with detailed progress tracking"""
    await interaction.response.defer()
    
    try:
        # Initial status embed
        start_embed = discord.Embed(
            title="Scraping Iniciado",
            description="**Búsqueda de servidores VIP iniciada exitosamente!**\n\nBuscando servidores disponibles en la base de datos...",
            color=0x2F3136
        )
        start_embed.add_field(name="📊 Base de Datos Actual", value=f"{len(scraper.unique_vip_links)} servidores", inline=True)
        start_embed.add_field(name="🔄 Estado", value="Inicializando...", inline=True)
        start_embed.add_field(name="🌐 Fuente", value="rbxservers.xyz", inline=True)
        start_time = time.time()
        
        # Create view with follow button for start message too
        start_view = discord.ui.View(timeout=None)
        follow_button_start = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        start_view.add_item(follow_button_start)
        
        await interaction.followup.send(embed=start_embed, view=start_view)
        
        # Run scraping in background
        initial_count = len(scraper.unique_vip_links)
        await asyncio.get_event_loop().run_in_executor(None, scraper.scrape_vip_links)
        final_count = len(scraper.unique_vip_links)
        new_found = final_count - initial_count
        total_time = time.time() - start_time
        
        # Completion embed with detailed results
        complete_embed = discord.Embed(
            title="Scraping Completado",
            description="**La sesión de scraping ha finalizado exitosamente!** Mantén los datos seguros y **no los compartas con nadie.**",
            color=0x2F3136
        )
        
        complete_embed.add_field(name="🆕 Nuevos Servidores", value=f"**{new_found}**", inline=True)
        complete_embed.add_field(name="📊 Total en BD", value=f"**{final_count}** servidores", inline=True)
        complete_embed.add_field(name="⏱️ Duración", value=f"{total_time:.1f}s", inline=True)
        
        complete_embed.add_field(name="⚡ Velocidad", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)
        complete_embed.add_field(name="✅ Tasa de Éxito", value=f"{(scraper.scraping_stats.get('successful_extractions', 0) / max(scraper.scraping_stats.get('total_scraped', 1), 1) * 100):.1f}%", inline=True)
        complete_embed.add_field(name="🎯 Siguiente Paso", value="Usa `/servertest`", inline=True)
        
        # Processing stats
        total_processed = scraper.scraping_stats.get('total_scraped', 0)
        complete_embed.add_field(name="🔍 Total Procesado", value=f"{total_processed} servidores", inline=True)
        complete_embed.add_field(name="🌐 Fuente", value="rbxservers.xyz", inline=True)
        
        # Time stamp
        current_time = datetime.now().strftime('%H:%M:%S')
        complete_embed.add_field(name="🕐 Completado", value=current_time, inline=True)
        
        if new_found > 0:
            complete_embed.add_field(
                name="🎉 Éxito Total!", 
                value=f"Se encontraron {new_found} nuevo{'s' if new_found != 1 else ''} servidor{'es' if new_found != 1 else ''}!", 
                inline=False
            )
        else:
            complete_embed.add_field(
                name="ℹ️ Sin Nuevos Servidores", 
                value="Todos los servidores disponibles ya están en la base de datos.", 
                inline=False
            )
        
        # Create view with buttons for completion message
        complete_view = discord.ui.View(timeout=None)
        
        # Server test button
        test_button = discord.ui.Button(
            label="Obtener Servidor VIP",
            style=discord.ButtonStyle.secondary,
            disabled=len(scraper.unique_vip_links) == 0
        )
        # Note: We can't make this functional without custom_id, but it shows the intent
        complete_view.add_item(test_button)
        
        # Follow hesiz button
        follow_button = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        complete_view.add_item(follow_button)
        
        await interaction.followup.send(embed=complete_embed, view=complete_view)
        
    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        error_embed = discord.Embed(
            title="Error en Scraping",
            description="Ocurrió un error durante el proceso de scraping.",
            color=0xff3333
        )
        error_embed.add_field(name="Detalles del Error", value=f"```{str(e)[:200]}```", inline=False)
        error_embed.add_field(name="💡 Reintentar", value="Puedes volver a ejecutar `/scrape`", inline=False)
        
        # Error view with follow button
        error_view = discord.ui.View(timeout=None)
        follow_button_error = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        error_view.add_item(follow_button_error)
        
        await interaction.followup.send(embed=error_embed, view=error_view)

@bot.tree.command(name="stats", description="Show comprehensive VIP links statistics")
async def stats(interaction: discord.Interaction):
    """Show detailed statistics about collected VIP links"""
    try:
        embed = discord.Embed(
            title="📊 VIP Server Database Statistics",
            description="**Comprehensive overview of scraped data**",
            color=0x3366ff,
            timestamp=datetime.now()
        )
        
        # Main stats
        embed.add_field(name="🗃️ Total Unique Links", value=f"**{len(scraper.unique_vip_links)}**", inline=True)
        embed.add_field(name="📈 Total Scraped", value=f"**{scraper.scraping_stats.get('total_scraped', 0)}**", inline=True)
        embed.add_field(name="✅ Successful", value=f"**{scraper.scraping_stats.get('successful_extractions', 0)}**", inline=True)
        
        # Performance metrics
        embed.add_field(name="❌ Failed", value=f"{scraper.scraping_stats.get('failed_extractions', 0)}", inline=True)
        embed.add_field(name="⚡ Speed", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} servers/min", inline=True)
        embed.add_field(name="⏱️ Last Duration", value=f"{scraper.scraping_stats.get('scrape_duration', 0)}s", inline=True)
        
        # Success rate calculation
        total_scraped = scraper.scraping_stats.get('total_scraped', 0)
        successful = scraper.scraping_stats.get('successful_extractions', 0)
        if total_scraped > 0:
            success_rate = (successful / total_scraped) * 100
            embed.add_field(name="📊 Success Rate", value=f"{success_rate:.1f}%", inline=True)
        
        # Last update info
        if Path(scraper.vip_links_file).exists():
            with open(scraper.vip_links_file, 'r') as f:
                data = json.load(f)
                last_updated = data.get('last_updated', 'Unknown')
                if last_updated != 'Unknown':
                    try:
                        update_time = datetime.fromisoformat(last_updated)
                        time_diff = datetime.now() - update_time
                        if time_diff.days > 0:
                            time_str = f"{time_diff.days}d {time_diff.seconds//3600}h ago"
                        elif time_diff.seconds > 3600:
                            time_str = f"{time_diff.seconds//3600}h {(time_diff.seconds%3600)//60}m ago"
                        else:
                            time_str = f"{time_diff.seconds//60}m ago"
                        embed.add_field(name="🕐 Last Updated", value=time_str, inline=True)
                    except:
                        embed.add_field(name="🕐 Last Updated", value="Recently", inline=True)
        
        # File size
        try:
            file_size = Path(scraper.vip_links_file).stat().st_size if Path(scraper.vip_links_file).exists() else 0
            size_kb = file_size / 1024
            embed.add_field(name="💾 Database Size", value=f"{size_kb:.1f} KB", inline=True)
        except:
            embed.add_field(name="💾 Database Size", value="Unknown", inline=True)
        
        # Commands info
        embed.add_field(
            name="🎮 Available Commands", 
            value="• `/servertest` - Get random server\n• `/scrape` - Find new servers\n• `/stats` - View statistics", 
            inline=False
        )
        
        embed.set_footer(text="Use /scrape to find more servers • /servertest to get a random link")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/123456789/chart.png")
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching stats.", ephemeral=True)

async def main():
    """Main function to run both scraper and bot"""
    logger.info("🚀 Starting VIP Server Scraper Bot...")
    
    # You can uncomment this to scrape on startup
    # await asyncio.get_event_loop().run_in_executor(None, scraper.scrape_vip_links)
    
    # Start the bot
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN not found in environment variables")
        return
    
    await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())
