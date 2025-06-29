

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
        # Organize links by game_id: {game_id: {links: set(), server_details: dict()}}
        self.links_by_game: Dict[str, Dict] = {}
        self.scraping_stats = {
            'total_scraped': 0,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'last_scrape_time': None,
            'scrape_duration': 0,
            'servers_per_minute': 0
        }
        # User-specific link reservations organized by game_id
        self.user_reserved_links: Dict[str, Dict[int, List[str]]] = {}  # game_id -> user_id -> list of reserved links
        self.available_links: Dict[str, List[str]] = {}  # game_id -> list of available links
        self.load_existing_links()
        
    def load_existing_links(self):
        """Load existing VIP links from JSON file organized by game_id"""
        try:
            if Path(self.vip_links_file).exists():
                with open(self.vip_links_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load new format if available
                    if 'links_by_game' in data:
                        self.links_by_game = data.get('links_by_game', {})
                        # Convert sets back from lists
                        for game_id in self.links_by_game:
                            self.links_by_game[game_id]['links'] = set(self.links_by_game[game_id].get('links', []))
                        
                        self.scraping_stats = data.get('scraping_stats', self.scraping_stats)
                        self.user_reserved_links = data.get('user_reserved_links', {})
                        self.available_links = data.get('available_links', {})
                        
                    else:
                        # Convert old format to new format
                        old_links = set(data.get('links', []))
                        old_details = data.get('server_details', {})
                        
                        # Assume old links are for the default game_id if no game_id info available
                        default_game_id = "109983668079237"
                        self.links_by_game[default_game_id] = {
                            'links': old_links,
                            'server_details': old_details
                        }
                        
                        # Initialize available links
                        self.available_links[default_game_id] = list(old_links)
                        self.user_reserved_links[default_game_id] = {}
                        
                        self.scraping_stats = data.get('scraping_stats', self.scraping_stats)
                    
                    total_links = sum(len(game_data['links']) for game_data in self.links_by_game.values())
                    logger.info(f"Loaded {total_links} existing VIP links across {len(self.links_by_game)} games")
                    
                    for game_id, game_data in self.links_by_game.items():
                        available_count = len(self.available_links.get(game_id, []))
                        logger.info(f"Game {game_id}: {len(game_data['links'])} total, {available_count} available")
                        
        except Exception as e:
            logger.error(f"Error loading existing links: {e}")
    
    def save_links(self):
        """Save VIP links to JSON file organized by game_id"""
        try:
            # Convert sets to lists for JSON serialization
            links_by_game_serializable = {}
            for game_id, game_data in self.links_by_game.items():
                links_by_game_serializable[game_id] = {
                    'links': list(game_data['links']),
                    'server_details': game_data.get('server_details', {})
                }
            
            # Convert integer user IDs to strings for JSON serialization
            user_reserved_serializable = {}
            for game_id, users_dict in self.user_reserved_links.items():
                user_reserved_serializable[game_id] = {str(k): v for k, v in users_dict.items()}
            
            total_links = sum(len(game_data['links']) for game_data in self.links_by_game.values())
            
            data = {
                'links_by_game': links_by_game_serializable,
                'scraping_stats': self.scraping_stats,
                'user_reserved_links': user_reserved_serializable,
                'available_links': self.available_links,
                'last_updated': datetime.now().isoformat(),
                'total_count': total_links
            }
            with open(self.vip_links_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {total_links} VIP links across {len(self.links_by_game)} games to {self.vip_links_file}")
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
    
    def get_server_links(self, driver, game_id="109983668079237", max_retries=3):
        """Get server links with retry mechanism"""
        url = f"https://rbxservers.xyz/games/{game_id}"
        
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
    
    def extract_vip_link(self, driver, server_url, game_id, max_retries=2):
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
                    # Verify the link matches the game_id
                    if f"/games/{game_id}" not in vip_link:
                        logger.debug(f"Link doesn't match game_id {game_id}: {vip_link}")
                        return None
                    
                    # Extract additional server details
                    server_info = self.extract_server_info(driver, server_url)
                    extraction_time = time.time() - start_time
                    
                    # Initialize game_id entry if needed
                    if game_id not in self.links_by_game:
                        self.links_by_game[game_id] = {'links': set(), 'server_details': {}}
                    
                    # Store detailed information
                    self.links_by_game[game_id]['server_details'][vip_link] = {
                        'source_url': server_url,
                        'discovered_at': datetime.now().isoformat(),
                        'extraction_time': round(extraction_time, 2),
                        'server_info': server_info,
                        'game_id': game_id
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
    
    def scrape_vip_links(self, game_id="109983668079237"):
        """Main scraping function with detailed statistics"""
        driver = None
        start_time = time.time()
        new_links_count = 0
        processed_count = 0
        
        try:
            logger.info(f"🚀 Starting VIP server scraping for game ID: {game_id}...")
            driver = self.create_driver()
            server_links = self.get_server_links(driver, game_id)
            
            if not server_links:
                logger.warning("⚠️ No server links found")
                return
            
            # Initialize game_id entry if needed
            if game_id not in self.links_by_game:
                self.links_by_game[game_id] = {'links': set(), 'server_details': {}}
            if game_id not in self.available_links:
                self.available_links[game_id] = []
            if game_id not in self.user_reserved_links:
                self.user_reserved_links[game_id] = {}
            
            # Limit to 5 servers to avoid overloading
            server_links = server_links[:5]
            logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")
            
            for i, server_url in enumerate(server_links):
                try:
                    processed_count += 1
                    vip_link = self.extract_vip_link(driver, server_url, game_id)
                    
                    if vip_link and vip_link not in self.links_by_game[game_id]['links']:
                        self.links_by_game[game_id]['links'].add(vip_link)
                        self.available_links[game_id].append(vip_link)
                        new_links_count += 1
                        logger.info(f"🎉 New VIP link found for game {game_id} ({new_links_count}): {vip_link}")
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
            
            total_links = sum(len(game_data['links']) for game_data in self.links_by_game.values())
            logger.info(f"✅ Scraping completed in {total_time:.1f}s")
            logger.info(f"📈 Found {new_links_count} new VIP links for game {game_id} (Total across all games: {total_links})")
            logger.info(f"⚡ Processing speed: {self.scraping_stats['servers_per_minute']} servers/minute")
            
            self.save_links()
            
        except Exception as e:
            logger.error(f"💥 Scraping failed: {e}")
            raise
        finally:
            if driver:
                driver.quit()
    
    def get_random_link(self, game_id="109983668079237"):
        """Get a random VIP link with its details for a specific game"""
        if game_id not in self.links_by_game or not self.links_by_game[game_id]['links']:
            return None, None
        
        link = random.choice(list(self.links_by_game[game_id]['links']))
        details = self.links_by_game[game_id]['server_details'].get(link, {})
        return link, details
    
    def get_all_links(self, game_id="109983668079237"):
        """Get all VIP links for a specific game"""
        if game_id not in self.links_by_game:
            return []
        return list(self.links_by_game[game_id]['links'])
    
    def reserve_links_for_user(self, user_id: int, game_id: str, count: int = 5) -> List[str]:
        """Reserve a specific number of links for a user for a specific game"""
        # Initialize game_id entries if needed
        if game_id not in self.user_reserved_links:
            self.user_reserved_links[game_id] = {}
        if game_id not in self.available_links:
            self.available_links[game_id] = []
        
        # If user already has reserved links for this game, return them
        if user_id in self.user_reserved_links[game_id] and len(self.user_reserved_links[game_id][user_id]) >= count:
            return self.user_reserved_links[game_id][user_id][:count]
        
        # Get available links for this game
        available_game_links = self.available_links[game_id]
        if len(available_game_links) >= count:
            # Reserve links from available pool
            reserved = available_game_links[:count]
            self.available_links[game_id] = available_game_links[count:]
            self.user_reserved_links[game_id][user_id] = reserved
            logger.info(f"Reserved {count} links for user {user_id} for game {game_id}")
            return reserved
        else:
            # Not enough available links, return what we have
            reserved = available_game_links.copy()
            self.available_links[game_id] = []
            if reserved:
                self.user_reserved_links[game_id][user_id] = reserved
                logger.info(f"Reserved {len(reserved)} links for user {user_id} for game {game_id} (requested {count})")
            return reserved
    
    def get_user_links(self, user_id: int, game_id: str) -> List[str]:
        """Get reserved links for a specific user for a specific game"""
        if game_id not in self.user_reserved_links:
            return []
        return self.user_reserved_links[game_id].get(user_id, [])
    
    def has_enough_links_for_new_user(self, game_id: str, count: int = 5) -> bool:
        """Check if we have enough available links for a new user for a specific game"""
        if game_id not in self.available_links:
            return False
        return len(self.available_links[game_id]) >= count
    
    def get_server_details(self, link: str, game_id: str) -> Dict:
        """Get server details for a specific link and game"""
        if game_id not in self.links_by_game:
            return {}
        return self.links_by_game[game_id]['server_details'].get(link, {})

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Global scraper instance
scraper = VIPServerScraper()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    total_links = sum(len(game_data['links']) for game_data in scraper.links_by_game.values())
    logger.info(f'Bot is ready with {total_links} VIP links loaded')
    
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
            label="Previous",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_index == 0),
            custom_id="prev_server"
        )
        prev_button.callback = self.previous_server
        self.add_item(prev_button)
        
        # Next button  
        next_button = discord.ui.Button(
            label="Next",
            style=discord.ButtonStyle.secondary,
            disabled=(self.current_index >= self.total_servers - 1),
            custom_id="next_server"
        )
        next_button.callback = self.next_server
        self.add_item(next_button)
        
        # Join server button
        current_server = self.servers_list[self.current_index]
        join_button = discord.ui.Button(
            label="Join Server",
            style=discord.ButtonStyle.primary,
            url=current_server
        )
        self.add_item(join_button)
        
        # Follow hesiz button
        follow_button = discord.ui.Button(
            label="Follow hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        self.add_item(follow_button)
    
    async def previous_server(self, interaction: discord.Interaction):
        """Navigate to previous server"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_buttons()
            
            embed, file = self.create_server_embed()
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        else:
            await interaction.response.defer()
    
    async def next_server(self, interaction: discord.Interaction):
        """Navigate to next server"""
        if self.current_index < self.total_servers - 1:
            self.current_index += 1
            self.update_buttons()
            
            embed, file = self.create_server_embed()
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        else:
            await interaction.response.defer()
    
    def create_server_embed(self):
        """Create embed for current server"""
        current_server = self.servers_list[self.current_index]
        
        embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description="Your server has been successfully generated! Keep it secure and do not share it with anyone.",
            color=0x2F3136
        )
        
        # Get server details from any game that has this server
        details = {}
        server_info = {}
        for game_id, game_data in scraper.links_by_game.items():
            if current_server in game_data['server_details']:
                details = game_data['server_details'][current_server]
                server_info = details.get('server_info', {})
                break
        
        # Server ID
        server_id = server_info.get('server_id', 'Unknown')
        embed.add_field(name="Server ID", value=f"```{{{server_id}}}```", inline=True)
        
        # Server Link in code block
        embed.add_field(name="Server Link", value=f"```{current_server}```", inline=False)
        
        # Add Roblox logo
        file = discord.File("roblox_logo.png", filename="roblox_logo.png")
        embed.set_thumbnail(url="attachment://roblox_logo.png")
        
        # Footer with server count
        embed.set_footer(text=f"Server {self.current_index + 1}/{self.total_servers}")
        
        return embed, file

@bot.tree.command(name="servertest", description="Navegar por todos los servidores VIP disponibles")
async def servertest(interaction: discord.Interaction):
    """Browser through all available VIP servers with navigation"""
    await interaction.response.defer()
    
    try:
        # Get servers from any available game (prioritize default game)
        default_game_id = "109983668079237"
        all_servers = []
        
        if default_game_id in scraper.links_by_game:
            all_servers = scraper.get_all_links(default_game_id)
        else:
            # Get from any available game
            for game_id in scraper.links_by_game:
                all_servers = scraper.get_all_links(game_id)
                if all_servers:
                    break
        
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
        embed, file = view.create_server_embed()
        
        await interaction.followup.send(embed=embed, file=file, view=view)
            
    except Exception as e:
        logger.error(f"Error in servertest command: {e}")
        error_embed = discord.Embed(
            title="❌ Error Occurred",
            description="Ocurrió un error al cargar los servidores.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="scrape", description="Start scraping for new VIP server links")
async def scrape_command(interaction: discord.Interaction, game_id: str):
    """Manually trigger scraping with user-specific link reservation"""
    await interaction.response.defer()
    
    user_id = interaction.user.id
    
    try:
        # Check if user already has reserved links for this game
        existing_links = scraper.get_user_links(user_id, game_id)
        if existing_links and len(existing_links) >= 5:
            # User already has reserved links for this game, show them
            embed = discord.Embed(
                title="ROBLOX PRIVATE SERVER LINKS",
                description=f"You already have reserved VIP servers for game ID {game_id}! Here are your personal links.",
                color=0x2F3136
            )
            
            # Show first 5 reserved links
            for i, link in enumerate(existing_links[:5], 1):
                server_details = scraper.get_server_details(link, game_id)
                server_info = server_details.get('server_info', {})
                server_id = server_info.get('server_id', 'Unknown')
                embed.add_field(
                    name=f"Server {i}",
                    value=f"**ID:** ```{{{server_id}}}```\n**Link:** ```{link}```",
                    inline=False
                )
            
            view = discord.ui.View(timeout=None)
            follow_button = discord.ui.Button(
                label="Follow hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            view.add_item(follow_button)
            
            await interaction.followup.send(embed=embed, view=view)
            return
        
        # Check if we need to scrape more links for this game
        if not scraper.has_enough_links_for_new_user(game_id, 5):
            # Initial status embed
            start_embed = discord.Embed(
                title="ROBLOX PRIVATE SERVER LINKS",
                description=f"Server scraping has been successfully initiated! Searching for your personal VIP servers for game ID: {game_id}",
                color=0x2F3136
            )
            start_embed.add_field(name="Game ID", value=f"`{game_id}`", inline=True)
            total_links = sum(len(game_data['links']) for game_data in scraper.links_by_game.values())
            available_for_game = len(scraper.available_links.get(game_id, []))
            start_embed.add_field(name="Current Database", value=f"{total_links} servers", inline=True)
            start_embed.add_field(name="Available for Game", value=f"{available_for_game} servers", inline=True)
            start_embed.add_field(name="Status", value="Searching for new servers...", inline=True)
            start_time = time.time()
            
            # Create view with follow button
            start_view = discord.ui.View(timeout=None)
            follow_button_start = discord.ui.Button(
                label="Follow hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            start_view.add_item(follow_button_start)
            
            # Send initial message
            message = await interaction.followup.send(embed=start_embed, view=start_view)
            
            # Run scraping with real-time updates
            initial_count = sum(len(game_data['links']) for game_data in scraper.links_by_game.values())
            await scrape_with_updates(message, initial_count, start_time, user_id, game_id)
        else:
            # We have enough links for this game, reserve them immediately
            reserved_links = scraper.reserve_links_for_user(user_id, game_id, 5)
            scraper.save_links()
            
            embed = discord.Embed(
                title="ROBLOX PRIVATE SERVER LINKS",
                description=f"Your personal VIP servers for game ID {game_id} have been successfully reserved! Keep them secure and do not share with anyone.",
                color=0x2F3136
            )
            
            # Show reserved links
            for i, link in enumerate(reserved_links, 1):
                server_details = scraper.get_server_details(link, game_id)
                server_info = server_details.get('server_info', {})
                server_id = server_info.get('server_id', 'Unknown')
                embed.add_field(
                    name=f"Server {i}",
                    value=f"**ID:** ```{{{server_id}}}```\n**Link:** ```{link}```",
                    inline=False
                )
                
            embed.add_field(name="Note", value=f"These servers are exclusively yours for game {game_id}!", inline=False)
            
            view = discord.ui.View(timeout=None)
            follow_button = discord.ui.Button(
                label="Follow hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            view.add_item(follow_button)
            
            await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        error_embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description=f"An error occurred during the scraping process for game ID: {game_id}",
            color=0x2F3136
        )
        error_embed.add_field(name="Error Details", value=f"```{str(e)[:200]}```", inline=False)
        error_embed.add_field(name="Retry", value="You can run /scrape again", inline=False)
        
        # Error view with follow button
        error_view = discord.ui.View(timeout=None)
        follow_button_error = discord.ui.Button(
            label="Follow hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        error_view.add_item(follow_button_error)
        
        await interaction.followup.send(embed=error_embed, view=error_view)

async def scrape_with_updates(message, initial_count, start_time, user_id=None, game_id="109983668079237"):
    """Run scraping with real-time Discord message updates"""
    driver = None
    new_links_count = 0
    processed_count = 0
    
    try:
        logger.info(f"🚀 Starting VIP server scraping for game ID: {game_id}...")
        driver = scraper.create_driver()
        server_links = scraper.get_server_links(driver, game_id)
        
        if not server_links:
            logger.warning("⚠️ No server links found")
            return
        
        # Limit to 5 servers to avoid overloading
        server_links = server_links[:5]
        logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")
        
        # Update message with processing status
        processing_embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description=f"Processing {len(server_links)} servers (limited to 5)... Active search for VIP servers for game ID: {game_id}",
            color=0x2F3136
        )
        processing_embed.add_field(name="Servers Found", value=f"**0**", inline=True)
        processing_embed.add_field(name="Progress", value=f"0/{len(server_links)}", inline=True)
        processing_embed.add_field(name="Time", value="0s", inline=True)
        
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
                
                if vip_link and game_id in scraper.links_by_game and vip_link not in scraper.links_by_game[game_id]['links']:
                    # Initialize game_id entry if needed
                    if game_id not in scraper.links_by_game:
                        scraper.links_by_game[game_id] = {'links': set(), 'server_details': {}}
                    if game_id not in scraper.available_links:
                        scraper.available_links[game_id] = []
                    
                    scraper.links_by_game[game_id]['links'].add(vip_link)
                    scraper.available_links[game_id].append(vip_link)
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
                        title="ROBLOX PRIVATE SERVER LINKS",
                        description=f"Processing {len(server_links)} servers found... Active search for VIP servers for game ID: {game_id}",
                        color=0x2F3136
                    )
                    progress_embed.add_field(name="Servers Found", value=f"**{new_links_count}**", inline=True)
                    progress_embed.add_field(name="Progress", value=f"{i + 1}/{len(server_links)}", inline=True)
                    progress_embed.add_field(name="Time", value=f"{elapsed:.0f}s", inline=True)
                    
                    if eta > 0:
                        progress_embed.add_field(name="ETA", value=f"{eta:.0f}s", inline=True)
                    
                    total_in_db = sum(len(game_data['links']) for game_data in scraper.links_by_game.values())
                    progress_embed.add_field(name="Total in DB", value=f"{total_in_db} servers", inline=True)
                    
                    # Progress bar
                    progress_percentage = ((i + 1) / len(server_links)) * 100
                    bar_length = 10
                    filled_length = int(bar_length * (i + 1) // len(server_links))
                    bar = "█" * filled_length + "░" * (bar_length - filled_length)
                    progress_embed.add_field(
                        name="Visual Progress", 
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
        final_count = sum(len(game_data['links']) for game_data in scraper.links_by_game.values())
        
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
        
        # Reserve links for the requesting user if provided
        reserved_links = []
        if user_id and new_links_count > 0:
            reserved_links = scraper.reserve_links_for_user(user_id, game_id, 5)
        
        scraper.save_links()
        
        # Final completion embed
        if user_id and reserved_links:
            # Show user their reserved links
            complete_embed = discord.Embed(
                title="ROBLOX PRIVATE SERVER LINKS",
                description=f"Your personal VIP servers for game ID {game_id} have been successfully found and reserved! Keep them secure and do not share with anyone.",
                color=0x2F3136
            )
            
            # Show reserved links
            for i, link in enumerate(reserved_links[:5], 1):
                server_details = scraper.get_server_details(link, game_id)
                server_info = server_details.get('server_info', {})
                server_id = server_info.get('server_id', 'Unknown')
                complete_embed.add_field(
                    name=f"Your Server {i}",
                    value=f"**ID:** ```{{{server_id}}}```\n**Link:** ```{link}```",
                    inline=False
                )
            
            complete_embed.add_field(name="New Servers Found", value=f"**{new_links_count}**", inline=True)
            complete_embed.add_field(name="Search Duration", value=f"{total_time:.1f}s", inline=True)
            complete_embed.add_field(name="Your Reserved Links", value=f"**{len(reserved_links)}**", inline=True)
            
            complete_embed.add_field(
                name="Note", 
                value="These servers are exclusively yours! Other users will get different servers when they use /scrape.", 
                inline=False
            )
        else:
            # General completion message
            complete_embed = discord.Embed(
                title="ROBLOX PRIVATE SERVER LINKS",
                description=f"VIP server search for game ID {game_id} has been successfully completed! Use /servertest to get a VIP server.",
                color=0x2F3136
            )
            
            complete_embed.add_field(name="New Servers", value=f"**{new_links_count}**", inline=True)
            complete_embed.add_field(name="Total in DB", value=f"**{final_count}** servers", inline=True)
            complete_embed.add_field(name="Duration", value=f"{total_time:.1f}s", inline=True)
            
            complete_embed.add_field(name="Speed", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)
            complete_embed.add_field(name="Success Rate", value=f"{(new_links_count / max(processed_count, 1) * 100):.1f}%", inline=True)
            available_for_game = len(scraper.available_links.get(game_id, []))
            complete_embed.add_field(name="Available for Game", value=f"{available_for_game} servers", inline=True)
            
            if new_links_count > 0:
                complete_embed.add_field(
                    name="Success!", 
                    value=f"Found {new_links_count} new server{'s' if new_links_count != 1 else ''}!", 
                    inline=False
                )
            else:
                complete_embed.add_field(
                    name="No New Servers", 
                    value="All available servers are already in the database.", 
                    inline=False
                )
        
        # Final completion view
        complete_view = discord.ui.View(timeout=None)
        
        follow_button_final = discord.ui.Button(
            label="Follow hesiz",
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
        total_unique_links = sum(len(game_data['links']) for game_data in scraper.links_by_game.values())
        embed.add_field(name="🗃️ Total Unique Links", value=f"**{total_unique_links}**", inline=True)
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
