

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
            
            # Limit to 5 servers to avoid overloading
            server_links = server_links[:5]
            logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")
            
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

# Server browser view with navigation buttons
class ServerBrowserView(discord.ui.View):
    def __init__(self, servers_list, current_index=0):
        super().__init__(timeout=300)
        self.servers_list = servers_list
        self.current_index = current_index
        self.total_servers = len(servers_list)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current position"""
        # Clear existing items
        self.clear_items()
        
        # Previous button
        prev_button = discord.ui.Button(
            label="⬅️ Anterior",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_index == 0),
            custom_id="prev_server"
        )
        prev_button.callback = self.previous_server
        self.add_item(prev_button)
        
        # Next button  
        next_button = discord.ui.Button(
            label="Siguiente ➡️",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_index >= self.total_servers - 1),
            custom_id="next_server"
        )
        next_button.callback = self.next_server
        self.add_item(next_button)
        
        # Join server button
        current_server = self.servers_list[self.current_index]
        join_button = discord.ui.Button(
            label="🎮 Unirse al Servidor",
            style=discord.ButtonStyle.primary,
            url=current_server
        )
        self.add_item(join_button)
        
        # Follow hesiz button
        follow_button = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        self.add_item(follow_button)
    
    async def previous_server(self, interaction: discord.Interaction):
        """Navigate to previous server"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_buttons()
            
            embed = self.create_server_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    async def next_server(self, interaction: discord.Interaction):
        """Navigate to next server"""
        if self.current_index < self.total_servers - 1:
            self.current_index += 1
            self.update_buttons()
            
            embed = self.create_server_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    def create_server_embed(self):
        """Create embed for current server"""
        current_server = self.servers_list[self.current_index]
        
        embed = discord.Embed(
            title="🎮 ROBLOX PRIVATE SERVER LINKS",
            description=f"**Servidor {self.current_index + 1} de {self.total_servers}**\n\nPowered by **HESIZ**",
            color=0x2F3136
        )
        
        # Add the Roblox logo image
        embed.set_image(url="https://i.imgur.com/roblox_logo.png")  # Placeholder URL
        
        # Get server details
        details = scraper.server_details.get(current_server, {})
        server_info = details.get('server_info', {})
        
        # Primera fila - Información del servidor
        server_id = server_info.get('server_id', 'Unknown')[:8] + '...' if server_info.get('server_id', 'Unknown') != 'Unknown' else 'Unknown'
        embed.add_field(name="🆔 Server ID", value=f"`{server_id}`", inline=True)
        
        # Discovery time
        discovered_time = details.get('discovered_at', 'Unknown')
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
        
        embed.add_field(name="⏰ Descubierto", value=discovered_time, inline=True)
        embed.add_field(name="📊 Total en BD", value=f"{len(scraper.unique_vip_links)} servidores", inline=True)
        
        # Segunda fila - Estadísticas de rendimiento
        speed = scraper.scraping_stats.get('servers_per_minute', 0)
        embed.add_field(name="⚡ Velocidad", value=f"{speed} serv/min" if speed > 0 else "N/A", inline=True)
        
        # Success rate
        total_scraped = scraper.scraping_stats.get('total_scraped', 0)
        successful = scraper.scraping_stats.get('successful_extractions', 0)
        if total_scraped > 0:
            success_rate = (successful / total_scraped) * 100
            embed.add_field(name="✅ Tasa de Éxito", value=f"{success_rate:.1f}%", inline=True)
        else:
            embed.add_field(name="✅ Tasa de Éxito", value="N/A", inline=True)
        
        # Navigation info
        embed.add_field(name="🧭 Navegación", value=f"Servidor {self.current_index + 1}/{self.total_servers}", inline=True)
        
        # Footer
        embed.set_footer(text="Usa los botones para navegar entre servidores | Powered by HESIZ")
        
        return embed

@bot.tree.command(name="servertest", description="Navegar por todos los servidores VIP disponibles")
async def servertest(interaction: discord.Interaction):
    """Browser through all available VIP servers with navigation"""
    await interaction.response.defer()
    
    try:
        all_servers = scraper.get_all_links()
        
        if not all_servers:
            embed = discord.Embed(
                title="❌ No VIP Links Available",
                description="No se encontraron servidores VIP en la base de datos. Intenta ejecutar `/scrape` primero.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create browser view starting at index 0
        view = ServerBrowserView(all_servers, 0)
        embed = view.create_server_embed()
        
        await interaction.followup.send(embed=embed, view=view)
            
    except Exception as e:
        logger.error(f"Error in servertest command: {e}")
        error_embed = discord.Embed(
            title="❌ Error Occurred",
            description="Ocurrió un error al cargar los servidores.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="scrape", description="Start scraping for new VIP server links")
async def scrape_command(interaction: discord.Interaction):
    """Manually trigger scraping with real-time progress updates"""
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
        start_time = time.time()
        
        # Create view with follow button
        start_view = discord.ui.View(timeout=None)
        follow_button_start = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        start_view.add_item(follow_button_start)
        
        # Send initial message
        message = await interaction.followup.send(embed=start_embed, view=start_view)
        
        # Run scraping with real-time updates
        initial_count = len(scraper.unique_vip_links)
        await scrape_with_updates(message, initial_count, start_time)
        
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

async def scrape_with_updates(message, initial_count, start_time):
    """Run scraping with real-time Discord message updates"""
    driver = None
    new_links_count = 0
    processed_count = 0
    
    try:
        logger.info("🚀 Starting VIP server scraping...")
        driver = scraper.create_driver()
        server_links = scraper.get_server_links(driver)
        
        if not server_links:
            logger.warning("⚠️ No server links found")
            return
        
        # Limit to 5 servers to avoid overloading
        server_links = server_links[:5]
        logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")
        
        # Update message with processing status
        processing_embed = discord.Embed(
            title="Scraping en Progreso",
            description=f"**Procesando {len(server_links)} servidores (limitado a 5)...**\n\nBúsqueda activa de servidores VIP.",
            color=0xFFAA00
        )
        processing_embed.add_field(name="📊 Servidores Encontrados", value=f"**0**", inline=True)
        processing_embed.add_field(name="🔄 Progreso", value=f"0/{len(server_links)}", inline=True)
        processing_embed.add_field(name="⏱️ Tiempo", value="0s", inline=True)
        
        view = discord.ui.View(timeout=None)
        follow_button = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        view.add_item(follow_button)
        
        await message.edit(embed=processing_embed, view=view)
        
        for i, server_url in enumerate(server_links):
            try:
                processed_count += 1
                vip_link = scraper.extract_vip_link(driver, server_url)
                
                if vip_link and vip_link not in scraper.unique_vip_links:
                    scraper.unique_vip_links.add(vip_link)
                    new_links_count += 1
                    logger.info(f"🎉 New VIP link found ({new_links_count}): {vip_link}")
                elif vip_link:
                    logger.debug(f"🔄 Duplicate link skipped: {vip_link}")
                
                # Update Discord message every 3 servers or on new find
                if (i + 1) % 3 == 0 or vip_link:
                    elapsed = time.time() - start_time
                    eta = (elapsed / (i + 1)) * (len(server_links) - i - 1) if i > 0 else 0
                    
                    # Update embed with current progress
                    progress_embed = discord.Embed(
                        title="Scraping en Progreso",
                        description=f"**Procesando {len(server_links)} servidores encontrados...**\n\nBúsqueda activa de servidores VIP.",
                        color=0xFFAA00
                    )
                    progress_embed.add_field(name="📊 Servidores Encontrados", value=f"**{new_links_count}**", inline=True)
                    progress_embed.add_field(name="🔄 Progreso", value=f"{i + 1}/{len(server_links)}", inline=True)
                    progress_embed.add_field(name="⏱️ Tiempo", value=f"{elapsed:.0f}s", inline=True)
                    
                    if eta > 0:
                        progress_embed.add_field(name="⏰ ETA", value=f"{eta:.0f}s", inline=True)
                    
                    progress_embed.add_field(name="📈 Total en BD", value=f"{len(scraper.unique_vip_links)} servidores", inline=True)
                    
                    # Progress bar
                    progress_percentage = ((i + 1) / len(server_links)) * 100
                    bar_length = 10
                    filled_length = int(bar_length * (i + 1) // len(server_links))
                    bar = "█" * filled_length + "░" * (bar_length - filled_length)
                    progress_embed.add_field(
                        name="📊 Progreso Visual", 
                        value=f"`{bar}` {progress_percentage:.1f}%", 
                        inline=False
                    )
                    
                    try:
                        await message.edit(embed=progress_embed, view=view)
                    except discord.HTTPException:
                        logger.warning("Failed to update Discord message, continuing...")
                        
            except Exception as e:
                logger.error(f"❌ Error processing {server_url}: {e}")
                continue
        
        # Final completion update
        total_time = time.time() - start_time
        final_count = len(scraper.unique_vip_links)
        
        # Update statistics
        scraper.scraping_stats.update({
            'total_scraped': scraper.scraping_stats['total_scraped'] + processed_count,
            'successful_extractions': scraper.scraping_stats['successful_extractions'] + new_links_count,
            'failed_extractions': scraper.scraping_stats['failed_extractions'] + (processed_count - new_links_count),
            'last_scrape_time': datetime.now().isoformat(),
            'scrape_duration': round(total_time, 2),
            'servers_per_minute': round((processed_count / total_time) * 60, 1) if total_time > 0 else 0
        })
        
        logger.info(f"✅ Scraping completed in {total_time:.1f}s")
        logger.info(f"📈 Found {new_links_count} new VIP links (Total: {final_count})")
        scraper.save_links()
        
        # Final completion embed
        complete_embed = discord.Embed(
            title="Scraping Completado",
            description="**La búsqueda de servidores VIP ha finalizado exitosamente!** Usa `/servertest` para obtener un servidor VIP.",
            color=0x00FF00
        )
        
        complete_embed.add_field(name="🆕 Nuevos Servidores", value=f"**{new_links_count}**", inline=True)
        complete_embed.add_field(name="📊 Total en BD", value=f"**{final_count}** servidores", inline=True)
        complete_embed.add_field(name="⏱️ Duración", value=f"{total_time:.1f}s", inline=True)
        
        complete_embed.add_field(name="⚡ Velocidad", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)
        complete_embed.add_field(name="✅ Tasa de Éxito", value=f"{(new_links_count / max(processed_count, 1) * 100):.1f}%", inline=True)
        complete_embed.add_field(name="🎯 Siguiente Paso", value="Usa `/servertest`", inline=True)
        
        complete_embed.add_field(name="🔍 Total Procesado", value=f"{processed_count} servidores", inline=True)
        
        current_time = datetime.now().strftime('%H:%M:%S')
        complete_embed.add_field(name="🕐 Completado", value=current_time, inline=True)
        
        if new_links_count > 0:
            complete_embed.add_field(
                name="🎉 Éxito Total!", 
                value=f"Se encontraron {new_links_count} nuevo{'s' if new_links_count != 1 else ''} servidor{'es' if new_links_count != 1 else ''}!", 
                inline=False
            )
        else:
            complete_embed.add_field(
                name="ℹ️ Sin Nuevos Servidores", 
                value="Todos los servidores disponibles ya están en la base de datos.", 
                inline=False
            )
        
        # Final completion view
        complete_view = discord.ui.View(timeout=None)
        
        test_button = discord.ui.Button(
            label="Obtener Servidor VIP",
            style=discord.ButtonStyle.secondary,
            disabled=len(scraper.unique_vip_links) == 0
        )
        complete_view.add_item(test_button)
        
        follow_button_final = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        complete_view.add_item(follow_button_final)
        
        await message.edit(embed=complete_embed, view=complete_view)
        
    except Exception as e:
        logger.error(f"💥 Scraping failed: {e}")
        raise
    finally:
        if driver:
            driver.quit()

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
