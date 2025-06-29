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
        self.links_by_user: Dict[str, Dict[str, Dict]] = {}  # Store links by user ID, then by game ID
        self.available_links: Dict[str, List[str]] = {}  # Track available links per game
        self.reserved_links: Dict[str, Dict[str, str]] = {}  # User reservations

    def load_existing_links(self):
        """Load existing VIP links from JSON file with user-specific data"""
        try:
            if Path(self.vip_links_file).exists():
                with open(self.vip_links_file, 'r') as f:
                    data = json.load(f)
                    
                    # Load user-specific links if available
                    self.links_by_user = data.get('links_by_user', {})
                    
                    # Migrate old data structure if needed
                    if not self.links_by_user and 'links_by_game' in data:
                        # Create a default user for existing links
                        default_user = "migrated_user"
                        self.links_by_user[default_user] = data.get('links_by_game', {})
                        logger.info(f"Migrated existing links to user: {default_user}")
                    
                    self.scraping_stats = data.get('scraping_stats', self.scraping_stats)
                    
                    # Initialize available_links properly
                    self.available_links = {}
                    total_users = len(self.links_by_user)
                    total_games = 0
                    for user_id, user_games in self.links_by_user.items():
                        total_games += len(user_games)
                    
                    logger.info(f"Loaded links for {total_users} users with {total_games} total games.")
            else:
                # Initialize empty structures if file doesn't exist
                self.available_links = {}
                self.links_by_user = {}
        except Exception as e:
            logger.error(f"Error loading existing links: {e}")
            # Initialize empty structures on error
            self.available_links = {}
            self.links_by_user = {}

    def save_links(self):
        """Save VIP links to JSON file, organizing by user ID and game ID"""
        try:
            total_count = 0
            for user_id, user_games in self.links_by_user.items():
                for game_id, game_data in user_games.items():
                    total_count += len(game_data.get('links', []))
            
            data = {
                'links_by_user': self.links_by_user,
                'scraping_stats': self.scraping_stats,
                'last_updated': datetime.now().isoformat(),
                'total_count': total_count
            }
            with open(self.vip_links_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved VIP links to {self.vip_links_file}")
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

    def get_server_links(self, driver, game_id, max_retries=3):
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
                    # Extract additional server details
                    server_info = self.extract_server_info(driver, server_url)
                    extraction_time = time.time() - start_time

                    # Store detailed information - now stored under user ID and game ID
                    user_id = getattr(self, 'current_user_id', 'unknown_user')
                    
                    if user_id not in self.links_by_user:
                        self.links_by_user[user_id] = {}
                    
                    if game_id not in self.links_by_user[user_id]:
                        self.links_by_user[user_id][game_id] = {'links': [], 'game_name': f'Game {game_id}', 'server_details': {}}
                    
                    if 'server_details' not in self.links_by_user[user_id][game_id]:
                        self.links_by_user[user_id][game_id]['server_details'] = {}

                    self.links_by_user[user_id][game_id]['server_details'][vip_link] = {
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

    def extract_game_info(self, driver, game_id):
        """Extract game information including name and image from rbxservers.xyz"""
        try:
            info = {'game_name': f'Game {game_id}', 'game_image_url': None}
            
            # Navigate to the game page
            url = f"https://rbxservers.xyz/games/{game_id}"
            driver.get(url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 10)
            
            # Try to get game name from title
            try:
                title_element = driver.find_element(By.TAG_NAME, "title")
                page_title = title_element.get_attribute("textContent")
                if page_title and page_title != "Unknown":
                    # Clean up the title (remove "- rbxservers.xyz" if present)
                    game_name = page_title.replace(" - rbxservers.xyz", "").strip()
                    if game_name:
                        info['game_name'] = game_name
            except Exception as e:
                logger.debug(f"Could not extract game name: {e}")
            
            # Try to get game image
            try:
                # Look for common image selectors that might contain the game thumbnail
                image_selectors = [
                    "img[src*='roblox']", 
                    "img[src*='rbxcdn']",
                    ".game-image img",
                    ".thumbnail img",
                    "img[alt*='game']"
                ]
                
                for selector in image_selectors:
                    try:
                        img_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for img in img_elements:
                            src = img.get_attribute("src")
                            if src and ("roblox" in src.lower() or "rbxcdn" in src.lower()):
                                info['game_image_url'] = src
                                logger.info(f"Found game image: {src}")
                                break
                        if info['game_image_url']:
                            break
                    except:
                        continue
                        
            except Exception as e:
                logger.debug(f"Could not extract game image: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error extracting game info: {e}")
            return {'game_name': f'Game {game_id}', 'game_image_url': None}

    def scrape_vip_links(self, game_id="109983668079237", user_id=None):
        """Main scraping function with detailed statistics"""
        driver = None
        start_time = time.time()
        new_links_count = 0
        processed_count = 0

        # Set current user ID for tracking
        self.current_user_id = user_id or 'unknown_user'

        try:
            logger.info(f"🚀 Starting VIP server scraping for game ID: {game_id} (User: {self.current_user_id})...")
            driver = self.create_driver()
            server_links = self.get_server_links(driver, game_id)

            if not server_links:
                logger.warning("⚠️ No server links found")
                return

            # Limit to 5 servers to avoid overloading
            server_links = server_links[:5]
            logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")

            # Initialize user and game data if not exists
            if self.current_user_id not in self.links_by_user:
                self.links_by_user[self.current_user_id] = {}
            
            if game_id not in self.links_by_user[self.current_user_id]:
                # Extract game information first
                game_info = self.extract_game_info(driver, game_id)
                self.links_by_user[self.current_user_id][game_id] = {
                    'links': [],
                    'game_name': game_info['game_name'],
                    'game_image_url': game_info.get('game_image_url'),
                    'server_details': {}
                }

            existing_links = set(self.links_by_user[self.current_user_id][game_id]['links'])

            for i, server_url in enumerate(server_links):
                try:
                    processed_count += 1
                    vip_link = self.extract_vip_link(driver, server_url, game_id)

                    if vip_link and vip_link not in existing_links:
                        self.links_by_user[self.current_user_id][game_id]['links'].append(vip_link)
                        existing_links.add(vip_link)
                        new_links_count += 1
                        logger.info(f"🎉 New VIP link found for user {self.current_user_id}, game {game_id} ({new_links_count}): {vip_link}")
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
            user_game_total = len(self.links_by_user[self.current_user_id][game_id]['links']) if self.current_user_id in self.links_by_user and game_id in self.links_by_user[self.current_user_id] else 0
            logger.info(f"📈 Found {new_links_count} new VIP links (User Total: {user_game_total})")
            logger.info(f"⚡ Processing speed: {self.scraping_stats['servers_per_minute']} servers/minute")

            self.save_links()

        except Exception as e:
            logger.error(f"💥 Scraping failed: {e}")
            raise
        finally:
            if driver:
                driver.quit()

    def get_random_link(self, game_id, user_id):
        """Get a random VIP link for a specific game and user with its details"""
        if (user_id not in self.links_by_user or 
            game_id not in self.links_by_user[user_id] or 
            not self.links_by_user[user_id][game_id]['links']):
            return None, None

        links = self.links_by_user[user_id][game_id]['links']
        link = random.choice(links)
        details = self.links_by_user[user_id][game_id]['server_details'].get(link, {})
        return link, details

    def get_all_links(self, game_id=None, user_id=None):
        """Get all VIP links, optionally for a specific game and user"""
        if user_id and game_id:
            return self.links_by_user.get(user_id, {}).get(game_id, {}).get('links', [])
        elif user_id:
            all_links = []
            user_games = self.links_by_user.get(user_id, {})
            for game_data in user_games.values():
                all_links.extend(game_data.get('links', []))
            return all_links
        else:
            all_links = []
            for user_games in self.links_by_user.values():
                for game_data in user_games.values():
                    all_links.extend(game_data.get('links', []))
            return all_links

# Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Global scraper instance
scraper = VIPServerScraper()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    total_links = sum(len(game_data.get('links', [])) for game_data in scraper.links_by_game.values())
    logger.info(f'Bot is ready with {total_links} VIP links loaded')

    # Sync slash commands after bot is ready
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

# Server browser view with navigation buttons
class ServerBrowserView(discord.ui.View):
    def __init__(self, servers_list, current_index=0, game_info=None):
        super().__init__(timeout=300)
        self.servers_list = servers_list
        self.current_index = current_index
        self.total_servers = len(servers_list)
        self.game_info = game_info or {}

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
            if file:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, attachments=[], view=self)
        else:
            await interaction.response.defer()

    async def next_server(self, interaction: discord.Interaction):
        """Navigate to next server"""
        if self.current_index < self.total_servers - 1:
            self.current_index += 1
            self.update_buttons()

            embed, file = self.create_server_embed()
            if file:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, attachments=[], view=self)
        else:
            await interaction.response.defer()

    def create_server_embed(self):
        """Create embed for current server"""
        current_server = self.servers_list[self.current_index]
        
        # Get game name from game_info
        game_name = self.game_info.get('game_name', 'Unknown Game')
        game_id = self.game_info.get('game_id', 'Unknown')

        embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description=f"Your server for **{game_name}** has been successfully generated! Keep it secure and do not share it with anyone.",
            color=0x2F3136
        )

        # Add game name field
        embed.add_field(name="Game Name", value=f"```{game_name}```", inline=True)
        
        # Add game ID field
        embed.add_field(name="Game ID", value=f"```{game_id}```", inline=True)

        # Get server details from the correct user and game
        server_details = {}
        user_id = self.game_info.get('user_id')
        if user_id and user_id in scraper.links_by_user and game_id in scraper.links_by_user[user_id]:
            server_details = scraper.links_by_user[user_id][game_id].get('server_details', {}).get(current_server, {})
        
        server_info = server_details.get('server_info', {})

        # Server ID
        server_id = server_info.get('server_id', 'Unknown')
        embed.add_field(name="Server ID", value=f"```{{{server_id}}}```", inline=True)

        # Server Link in code block
        embed.add_field(name="Server Link", value=f"```{current_server}```", inline=False)

        # Set game image as thumbnail if available
        game_image_url = self.game_info.get('game_image_url')
        if game_image_url:
            embed.set_thumbnail(url=game_image_url)

        # Footer with server count
        embed.set_footer(text=f"Server {self.current_index + 1}/{self.total_servers}")

        # Always return None for file since we're using URL-based images
        return embed, None

@bot.tree.command(name="servertest", description="Navegar por todos los servidores VIP disponibles")
async def servertest(interaction: discord.Interaction):
    """Browser through all available VIP servers with navigation (user-specific)"""
    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)
        
        # Get all servers from user's games
        all_servers = []
        current_game_info = None
        
        # Find the first game with servers for this user
        user_games = scraper.links_by_user.get(user_id, {})
        for game_id, game_data in user_games.items():
            if game_data.get('links'):
                all_servers = game_data['links']
                current_game_info = {
                    'game_id': game_id,
                    'game_name': game_data.get('game_name', f'Game {game_id}'),
                    'game_image_url': game_data.get('game_image_url'),
                    'user_id': user_id
                }
                break

        if not all_servers:
            embed = discord.Embed(
                title="❌ No VIP Links Available",
                description="No tienes servidores VIP en tu base de datos. Intenta ejecutar `/scrape` primero para generar enlaces.",
                color=0xff3333
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Create browser view starting at index 0
        view = ServerBrowserView(all_servers, 0, current_game_info)
        embed, file = view.create_server_embed()

        if file:
            await interaction.followup.send(embed=embed, file=file, view=view)
        else:
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
async def scrape_command(interaction: discord.Interaction, game_id: str):
    """Manually trigger scraping with real-time progress updates"""
    await interaction.response.defer()

    # Validate game_id (should be numeric)
    if not game_id.isdigit():
        error_embed = discord.Embed(
            title="❌ Invalid Game ID",
            description="El ID del juego debe ser numérico. Por ejemplo: `10449761463`",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)
        return

    try:
        # Initial status embed
        start_embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description=f"Server scraping has been successfully initiated for game ID: **{game_id}**! Keep it secure and do not share it with anyone.",
            color=0x2F3136
        )
        start_embed.add_field(name="Game ID", value=f"```{game_id}```", inline=True)
        # Ensure links_by_game[game_id] exists before accessing it
        initial_count = len(scraper.links_by_game.get(game_id, {}).get('links', []))
        start_embed.add_field(name="Current Database", value=f"{initial_count} servers", inline=True)
        start_embed.add_field(name="Status", value="Initializing...", inline=True)
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
        user_id = str(interaction.user.id)
        await scrape_with_updates(message, start_time, game_id, user_id)

    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        error_embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description="An error occurred during the scraping process.",
            color=0x2F3136
        )
        error_embed.add_field(name="Error Details", value=f"```{str(e)[:200]}```", inline=False)
        error_embed.add_field(name="Retry", value="You can run /scrape again", inline=False)

        # Error view with follow button
        error_view = discord.ui.View(timeout=None)
        follow_button_error = discord.ui.Button(
            label="Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        error_view.add_item(follow_button_error)

        await interaction.followup.send(embed=error_embed, view=error_view)

async def scrape_with_updates(message, start_time, game_id, user_id):
    """Run scraping with real-time Discord message updates"""
    driver = None
    new_links_count = 0
    processed_count = 0

    try:
        logger.info(f"🚀 Starting VIP server scraping for game ID: {game_id} (User: {user_id})...")
        driver = scraper.create_driver()
        server_links = scraper.get_server_links(driver, game_id)

        if not server_links:
            logger.warning("⚠️ No server links found")
            return

        # Limit to 5 servers to avoid overloading
        server_links = server_links[:5]
        logger.info(f"🎯 Processing {len(server_links)} server links (limited to 5)...")

        # Set current user ID for tracking
        scraper.current_user_id = user_id

        # Initialize user and game data if not exists
        if user_id not in scraper.links_by_user:
            scraper.links_by_user[user_id] = {}
        
        if game_id not in scraper.links_by_user[user_id]:
            # Extract game information first
            game_info = scraper.extract_game_info(driver, game_id)
            scraper.links_by_user[user_id][game_id] = {
                'links': [],
                'game_name': game_info['game_name'],
                'game_image_url': game_info.get('game_image_url'),
                'server_details': {}
            }

        existing_links = set(scraper.links_by_user[user_id][game_id]['links'])

        for i, server_url in enumerate(server_links):
            try:
                processed_count += 1
                vip_link = scraper.extract_vip_link(driver, server_url, game_id)

                if vip_link and vip_link not in existing_links:
                    scraper.links_by_user[user_id][game_id]['links'].append(vip_link)
                    existing_links.add(vip_link)
                    new_links_count += 1
                    logger.info(f"🎉 New VIP link found for user {user_id}, game {game_id} ({new_links_count}): {vip_link}")
                elif vip_link:
                    logger.debug(f"🔄 Duplicate link skipped: {vip_link}")

                # Update Discord message every 3 servers or on new find
                if (i + 1) % 3 == 0 or vip_link:
                    elapsed = time.time() - start_time
                    eta = (elapsed / (i + 1)) * (len(server_links) - i - 1) if i > 0 else 0

                    # Update embed with current progress
                    game_name = scraper.links_by_user[user_id][game_id]['game_name']
                    progress_embed = discord.Embed(
                        title="ROBLOX PRIVATE SERVER LINKS",
                        description=f"Processing {len(server_links)} servers found for **{game_name}** (ID: {game_id})... Active search for VIP servers.",
                        color=0x2F3136
                    )
                    
                    # Add game image if available
                    game_image_url = scraper.links_by_user[user_id][game_id].get('game_image_url')
                    if game_image_url:
                        progress_embed.set_thumbnail(url=game_image_url)
                    progress_embed.add_field(name="Servers Found", value=f"**{new_links_count}**", inline=True)
                    progress_embed.add_field(name="Progress", value=f"{i + 1}/{len(server_links)}", inline=True)
                    progress_embed.add_field(name="Time", value=f"{elapsed:.0f}s", inline=True)

                    if eta > 0:
                        progress_embed.add_field(name="ETA", value=f"{eta:.0f}s", inline=True)

                    progress_embed.add_field(name="Your Total", value=f"{len(scraper.links_by_user[user_id][game_id]['links'])} servers", inline=True)

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

                    view = discord.ui.View(timeout=None)
                    follow_button = discord.ui.Button(
                        label="Seguir a hesiz",
                        style=discord.ButtonStyle.secondary,
                        url="https://www.roblox.com/users/11834624/profile"
                    )
                    view.add_item(follow_button)

                    try:
                        await message.edit(embed=progress_embed, view=view)
                    except discord.HTTPException:
                        logger.warning("Failed to update Discord message, continuing...")

            except Exception as e:
                logger.error(f"❌ Error processing {server_url}: {e}")
                continue

        # Final completion update
        total_time = time.time() - start_time
        final_count = len(scraper.links_by_user[user_id][game_id]['links'])

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
        logger.info(f"📈 Found {new_links_count} new VIP links (User Total: {final_count})")
        scraper.save_links()

        # Final completion embed
        game_name = scraper.links_by_user[user_id][game_id]['game_name']
        complete_embed = discord.Embed(
            title="ROBLOX PRIVATE SERVER LINKS",
            description=f"VIP server search has been successfully completed for **{game_name}** (ID: {game_id})! Use /servertest to get a VIP server.",
            color=0x2F3136
        )
        
        # Add game image if available
        game_image_url = scraper.links_by_user[user_id][game_id].get('game_image_url')
        if game_image_url:
            complete_embed.set_thumbnail(url=game_image_url)

        complete_embed.add_field(name="New Servers", value=f"**{new_links_count}**", inline=True)
        complete_embed.add_field(name="Your Total", value=f"**{final_count}** servers", inline=True)
        complete_embed.add_field(name="Duration", value=f"{total_time:.1f}s", inline=True)

        complete_embed.add_field(name="Speed", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)
        complete_embed.add_field(name="Success Rate", value=f"{(new_links_count / max(processed_count, 1) * 100):.1f}%", inline=True)
        complete_embed.add_field(name="Next Step", value="Use /servertest", inline=True)

        complete_embed.add_field(name="Total Processed", value=f"{processed_count} servers", inline=True)

        current_time = datetime.now().strftime('%H:%M:%S')
        complete_embed.add_field(name="Completed", value=current_time, inline=True)

        if new_links_count > 0:
            complete_embed.add_field(
                name="Total Success!", 
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

        test_button = discord.ui.Button(
            label="Obtener Servidor VIP",
            style=discord.ButtonStyle.primary,
            disabled=len(scraper.links_by_game[game_id]['links']) == 0
        )
        
        async def get_vip_server(button_interaction):
            await button_interaction.response.defer()
            try:
                # Get all servers from the user's game
                servers = scraper.links_by_user[user_id][game_id]['links']
                if not servers:
                    error_embed = discord.Embed(
                        title="❌ No VIP Links Available",
                        description="No se encontraron servidores VIP para este juego.",
                        color=0xff3333
                    )
                    await button_interaction.followup.send(embed=error_embed, ephemeral=True)
                    return

                # Create browser view for this specific game
                game_info = {
                    'game_id': game_id,
                    'game_name': scraper.links_by_user[user_id][game_id].get('game_name', f'Game {game_id}'),
                    'game_image_url': scraper.links_by_user[user_id][game_id].get('game_image_url'),
                    'user_id': user_id
                }
                
                view = ServerBrowserView(servers, 0, game_info)
                embed, file = view.create_server_embed()

                if file:
                    await button_interaction.followup.send(embed=embed, file=file, view=view)
                else:
                    await button_interaction.followup.send(embed=embed, view=view)

            except Exception as e:
                logger.error(f"Error in get_vip_server button: {e}")
                error_embed = discord.Embed(
                    title="❌ Error Occurred",
                    description="Ocurrió un error al obtener el servidor VIP.",
                    color=0xff0000
                )
                await button_interaction.followup.send(embed=error_embed, ephemeral=True)
        
        test_button.callback = get_vip_server
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
        user_id = str(interaction.user.id)
        user_links = 0
        total_links = 0
        
        # Calculate user-specific links
        user_games = scraper.links_by_user.get(user_id, {})
        for game_data in user_games.values():
            user_links += len(game_data.get('links', []))
        
        # Calculate total links across all users
        for user_games in scraper.links_by_user.values():
            for game_data in user_games.values():
                total_links += len(game_data.get('links', []))
        
        embed.add_field(name="🗃️ Your Links", value=f"**{user_links}**", inline=True)
        embed.add_field(name="🌐 Total Links", value=f"**{total_links}**", inline=True)
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