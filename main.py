import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Set, Dict, Optional
import logging
import re

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

# Game categories mapping
GAME_CATEGORIES = {
    "rpg": ["roleplay", "adventure", "fantasy", "medieval", "simulator"],
    "simulator": ["simulator", "tycoon", "farming", "business", "idle"],
    "action": ["fighting", "pvp", "combat", "battle", "war", "shooter"],
    "racing": ["racing", "driving", "car", "speed", "vehicle"],
    "horror": ["horror", "scary", "zombie", "survival", "dark"],
    "social": ["hangout", "social", "chat", "dating", "party"],
    "sports": ["sports", "football", "basketball", "soccer", "tennis"],
    "puzzle": ["puzzle", "brain", "logic", "strategy", "quiz"],
    "building": ["building", "creative", "construction", "city", "town"],
    "anime": ["anime", "naruto", "dragon ball", "one piece", "manga"]
}

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
        self.links_by_user: Dict[str, Dict[str, Dict]] = {}
        self.available_links: Dict[str, List[str]] = {}
        self.reserved_links: Dict[str, Dict[str, str]] = {}

        # New features
        self.user_cooldowns: Dict[str, datetime] = {}  # Cooldown tracking
        self.usage_history: Dict[str, List[Dict]] = {}  # Usage history per user
        self.user_favorites: Dict[str, List[str]] = {}  # Favorite games per user
        self.game_categories: Dict[str, str] = {}  # Game ID to category mapping

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
                        default_user = "migrated_user"
                        self.links_by_user[default_user] = data.get('links_by_game', {})
                        logger.info(f"Migrated existing links to user: {default_user}")

                    self.scraping_stats = data.get('scraping_stats', self.scraping_stats)

                    # Load new features
                    self.usage_history = data.get('usage_history', {})
                    self.user_favorites = data.get('user_favorites', {})
                    self.game_categories = data.get('game_categories', {})

                    # Initialize available_links properly
                    self.available_links = {}
                    total_users = len(self.links_by_user)
                    total_games = 0
                    for user_id, user_games in self.links_by_user.items():
                        total_games += len(user_games)

                    logger.info(f"Loaded links for {total_users} users with {total_games} total games.")
            else:
                self.available_links = {}
                self.links_by_user = {}
                self.usage_history = {}
                self.user_favorites = {}
                self.game_categories = {}
        except Exception as e:
            logger.error(f"Error loading existing links: {e}")
            self.available_links = {}
            self.links_by_user = {}
            self.usage_history = {}
            self.user_favorites = {}
            self.game_categories = {}

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
                'usage_history': self.usage_history,
                'user_favorites': self.user_favorites,
                'game_categories': self.game_categories,
                'last_updated': datetime.now().isoformat(),
                'total_count': total_count
            }
            with open(self.vip_links_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved VIP links to {self.vip_links_file}")
        except Exception as e:
            logger.error(f"Error saving links: {e}")

    def check_cooldown(self, user_id: str, cooldown_minutes: int = 5) -> Optional[int]:
        """Check if user is on cooldown. Returns remaining seconds if on cooldown, None otherwise"""
        if user_id in self.user_cooldowns:
            time_diff = datetime.now() - self.user_cooldowns[user_id]
            if time_diff.total_seconds() < cooldown_minutes * 60:
                remaining = cooldown_minutes * 60 - time_diff.total_seconds()
                return int(remaining)
        return None

    def set_cooldown(self, user_id: str):
        """Set cooldown for user"""
        self.user_cooldowns[user_id] = datetime.now()

    def add_usage_history(self, user_id: str, game_id: str, server_link: str, action: str):
        """Add entry to usage history"""
        if user_id not in self.usage_history:
            self.usage_history[user_id] = []

        history_entry = {
            'game_id': game_id,
            'server_link': server_link,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'game_name': self.links_by_user.get(user_id, {}).get(game_id, {}).get('game_name', f'Game {game_id}')
        }

        self.usage_history[user_id].append(history_entry)

        # Keep only last 20 entries per user
        if len(self.usage_history[user_id]) > 20:
            self.usage_history[user_id] = self.usage_history[user_id][-20:]

    def categorize_game(self, game_name: str) -> str:
        """Automatically categorize game based on name"""
        game_name_lower = game_name.lower()

        for category, keywords in GAME_CATEGORIES.items():
            for keyword in keywords:
                if keyword in game_name_lower:
                    return category

        return "other"

    def toggle_favorite(self, user_id: str, game_id: str) -> bool:
        """Toggle favorite status for a game. Returns True if added, False if removed"""
        if user_id not in self.user_favorites:
            self.user_favorites[user_id] = []

        if game_id in self.user_favorites[user_id]:
            self.user_favorites[user_id].remove(game_id)
            return False
        else:
            self.user_favorites[user_id].append(game_id)
            return True

    async def search_game_by_name(self, game_name: str) -> List[Dict]:
        """Search for games by name using expanded database and fuzzy matching"""
        results = []

        # Expanded database of popular Roblox games
        common_games = {
            # Simulators
            "pet simulator": {"id": "6284583030", "name": "🎃 Pet Simulator X", "category": "simulator"},
            "pet sim": {"id": "6284583030", "name": "🎃 Pet Simulator X", "category": "simulator"},
            "mining simulator": {"id": "2724924549", "name": "⛏️ Mining Simulator 2", "category": "simulator"},
            "bee swarm": {"id": "1537690962", "name": "🐝 Bee Swarm Simulator", "category": "simulator"},
            "bee simulator": {"id": "1537690962", "name": "🐝 Bee Swarm Simulator", "category": "simulator"},
            "vehicle simulator": {"id": "171391948", "name": "Vehicle Simulator", "category": "simulator"},
            "car simulator": {"id": "171391948", "name": "Vehicle Simulator", "category": "simulator"},
            "bubble gum": {"id": "2512643572", "name": "🎈 Bubble Gum Simulator", "category": "simulator"},
            "anime fighting": {"id": "2505996599", "name": "🌟 Anime Fighting Simulator", "category": "simulator"},
            "muscle legends": {"id": "3623096087", "name": "💪 Muscle Legends", "category": "simulator"},
            "lifting titans": {"id": "2986677229", "name": "Lifting Titans", "category": "simulator"},
            "magnet simulator": {"id": "1250402770", "name": "🧲 Magnet Simulator", "category": "simulator"},
            "saber simulator": {"id": "3823781113", "name": "⚔️ Saber Simulator", "category": "simulator"},
            "clicking simulator": {"id": "2674698980", "name": "🖱️ Clicking Simulator", "category": "simulator"},
            "shindo life": {"id": "4616652839", "name": "Shindo Life", "category": "rpg"},
            "shinobi life": {"id": "4616652839", "name": "Shindo Life", "category": "rpg"},

            # RPG/Adventure
            "blox fruits": {"id": "2753915549", "name": "🌊 Blox Fruits", "category": "rpg"},
            "one piece": {"id": "2753915549", "name": "🌊 Blox Fruits", "category": "rpg"},
            "anime adventures": {"id": "8304191830", "name": "🎌 Anime Adventures", "category": "rpg"},
            "all star tower defense": {"id": "4646477729", "name": "⭐ All Star Tower Defense", "category": "rpg"},
            "astd": {"id": "4646477729", "name": "⭐ All Star Tower Defense", "category": "rpg"},
            "anime defenders": {"id": "15186202290", "name": "🛡️ Anime Defenders", "category": "rpg"},
            "deepwoken": {"id": "4111023553", "name": "Deepwoken", "category": "rpg"},
            "rogue lineage": {"id": "3016661674", "name": "🗡️ Rogue Lineage", "category": "rpg"},
            "world zero": {"id": "4738545896", "name": "⚔️ World // Zero", "category": "rpg"},
            "dungeon quest": {"id": "2414851778", "name": "⚔️ Dungeon Quest", "category": "rpg"},
            "arcane odyssey": {"id": "3272915504", "name": "🌊 Arcane Odyssey", "category": "rpg"},

            # Popular Games
            "dress to impress": {"id": "15101393044", "name": "[🏖️SUMMER!!] Dress To Impress", "category": "social"},
            "dti": {"id": "15101393044", "name": "[🏖️SUMMER!!] Dress To Impress", "category": "social"},
            "adopt me": {"id": "920587237", "name": "Adopt Me!", "category": "social"},
            "brookhaven": {"id": "4924922222", "name": "🏡 Brookhaven RP", "category": "social"},
            "brookhaven rp": {"id": "4924922222", "name": "🏡 Brookhaven RP", "category": "social"},
            "bloxburg": {"id": "185655149", "name": "Welcome to Bloxburg", "category": "building"},
            "welcome to bloxburg": {"id": "185655149", "name": "Welcome to Bloxburg", "category": "building"},
            "royale high": {"id": "735030788", "name": "👑 Royale High", "category": "social"},
            "rh": {"id": "735030788", "name": "👑 Royale High", "category": "social"},
            "meep city": {"id": "370731277", "name": "MeepCity", "category": "social"},
            "meepcity": {"id": "370731277", "name": "MeepCity", "category": "social"},

            # Action/Fighting
            "jailbreak": {"id": "606849621", "name": "🚓 Jailbreak", "category": "action"},
            "arsenal": {"id": "286090429", "name": "🔫 Arsenal", "category": "action"},
            "phantom forces": {"id": "292439477", "name": "Phantom Forces", "category": "action"},
            "bad business": {"id": "3233893879", "name": "Bad Business", "category": "action"},
            "counter blox": {"id": "301549746", "name": "Counter Blox", "category": "action"},
            "criminality": {"id": "4588604953", "name": "Criminality", "category": "action"},
            "da hood": {"id": "2788229376", "name": "Da Hood", "category": "action"},
            "the hood": {"id": "2788229376", "name": "Da Hood", "category": "action"},
            "prison life": {"id": "155615604", "name": "Prison Life", "category": "action"},
            "mad city": {"id": "1224212277", "name": "Mad City", "category": "action"},

            # Horror
            "piggy": {"id": "4623386862", "name": "🐷 PIGGY", "category": "horror"},
            "doors": {"id": "6516141723", "name": "🚪 DOORS", "category": "horror"},
            "the mimic": {"id": "2377868063", "name": "👻 The Mimic", "category": "horror"},
            "flee the facility": {"id": "893973440", "name": "Flee the Facility", "category": "horror"},
            "dead silence": {"id": "2039118386", "name": "Dead Silence", "category": "horror"},
            "midnight horrors": {"id": "318978013", "name": "Midnight Horrors", "category": "horror"},
            "identity fraud": {"id": "776877586", "name": "Identity Fraud", "category": "horror"},
            "survive the killer": {"id": "1320186298", "name": "Survive the Killer!", "category": "horror"},

            # Puzzle/Strategy
            "murder mystery": {"id": "142823291", "name": "🔍 Murder Mystery 2", "category": "puzzle"},
            "mm2": {"id": "142823291", "name": "🔍 Murder Mystery 2", "category": "puzzle"},
            "murder mystery 2": {"id": "142823291", "name": "🔍 Murder Mystery 2", "category": "puzzle"},
            "tower of hell": {"id": "1962086868", "name": "🏗️ Tower of Hell [CHRISTMAS]", "category": "puzzle"},
            "toh": {"id": "1962086868", "name": "🏗️ Tower of Hell [CHRISTMAS]", "category": "puzzle"},
            "mega fun obby": {"id": "1499593574", "name": "Mega Fun Obby", "category": "puzzle"},
            "escape room": {"id": "4777817887", "name": "Escape Room", "category": "puzzle"},
            "find the markers": {"id": "6029715808", "name": "Find the Markers", "category": "puzzle"},

            # Racing
            "vehicle legends": {"id": "3146619063", "name": "🏁 Vehicle Legends", "category": "racing"},
            "driving simulator": {"id": "3057042787", "name": "🚗 Driving Simulator", "category": "racing"},
            "ultimate driving": {"id": "54865335", "name": "Ultimate Driving", "category": "racing"},
            "ro racing": {"id": "1047802162", "name": "RO-Racing", "category": "racing"},
            "speed run": {"id": "183364845", "name": "Speed Run 4", "category": "racing"},
            "speed run 4": {"id": "183364845", "name": "Speed Run 4", "category": "racing"},

            # Sports
            "football fusion": {"id": "2987410699", "name": "🏈 Football Fusion 2", "category": "sports"},
            "football fusion 2": {"id": "2987410699", "name": "🏈 Football Fusion 2", "category": "sports"},
            "legendary football": {"id": "1045538060", "name": "Legendary Football", "category": "sports"},
            "ro soccer": {"id": "372226183", "name": "RO-Soccer", "category": "sports"},
            "basketball legends": {"id": "1499593574", "name": "Basketball Legends", "category": "sports"},

            # Anime Games
            "anime fighters": {"id": "2505996599", "name": "🌟 Anime Fighting Simulator", "category": "anime"},
            "project slayers": {"id": "3823781113", "name": "Project Slayers", "category": "anime"},
            "demon slayer": {"id": "3823781113", "name": "Project Slayers", "category": "anime"},
            "naruto": {"id": "4616652839", "name": "Shindo Life", "category": "anime"},
            "dragon ball": {"id": "536102540", "name": "Dragon Ball Z Final Stand", "category": "anime"},
            "dbz": {"id": "536102540", "name": "Dragon Ball Z Final Stand", "category": "anime"},
            "one punch man": {"id": "3297964905", "name": "Heroes Online", "category": "anime"},
            "my hero academia": {"id": "3297964905", "name": "Heroes Online", "category": "anime"},
            "mha": {"id": "3297964905", "name": "Heroes Online", "category": "anime"},

            # Tycoon
            "retail tycoon": {"id": "1304578966", "name": "🏪 Retail Tycoon 2", "category": "simulator"},
            "retail tycoon 2": {"id": "1304578966", "name": "🏪 Retail Tycoon 2", "category": "simulator"},
            "theme park tycoon": {"id": "69184822", "name": "🎢 Theme Park Tycoon 2", "category": "simulator"},
            "restaurant tycoon": {"id": "6879537910", "name": "🍕 Restaurant Tycoon 2", "category": "simulator"},
            "lumber tycoon": {"id": "58775777", "name": "🌲 Lumber Tycoon 2", "category": "simulator"},
            "lumber tycoon 2": {"id": "58775777", "name": "🌲 Lumber Tycoon 2", "category": "simulator"},
            "youtuber tycoon": {"id": "1345139196", "name": "📺 YouTuber Tycoon", "category": "simulator"},
            "mega mansion tycoon": {"id": "1060666313", "name": "🏠 Mega Mansion Tycoon", "category": "simulator"},
        }

        search_lower = game_name.lower().strip()

        # Exact match first
        if search_lower in common_games:
            game_info = common_games[search_lower]
            results.append({
                "id": game_info["id"],
                "name": game_info["name"],
                "category": game_info.get("category", "other"),
                "relevance": 1.0
            })

        # Partial matches
        for key, game_info in common_games.items():
            if key != search_lower:  # Skip exact match already added
                # Check if search term is in game key or vice versa
                if (search_lower in key or key in search_lower or 
                    any(word in key for word in search_lower.split()) or
                    any(word in search_lower for word in key.split())):

                    # Calculate relevance based on match quality
                    if search_lower == key:
                        relevance = 1.0
                    elif search_lower in key or key in search_lower:
                        relevance = 0.9
                    elif len(search_lower.split()) > 1 and any(word in key for word in search_lower.split()):
                        relevance = 0.8
                    else:
                        relevance = 0.7

                    # Avoid duplicates
                    if not any(r["id"] == game_info["id"] for r in results):
                        results.append({
                            "id": game_info["id"],
                            "name": game_info["name"],
                            "category": game_info.get("category", "other"),
                            "relevance": relevance
                        })

        # Sort by relevance and then by name
        results.sort(key=lambda x: (-x["relevance"], x["name"]))
        return results[:8]  # Return top 8 results

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
                server_elements = driver.{game_name}```", inline=True)

        # Add game ID field
        embed.add_field(name="🆔 ID del Juego", value=f"```{game_id}```", inline=True)

        # Add category
        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        embed.add_field(
            name="📂 Categoría", 
            value=f"{category_emoji.get(category, '🎮')} {category.title()}", 
            inline=True
        )

        # Get server details from the correct user and game
        server_details = {}
        user_id = self.game_info.get('user_id')
        if user_id and user_id in scraper.links_by_user and game_id in scraper.links_by_user[user_id]:
            server_details = scraper.links_by_user[user_id][game_id].get('server_details', {}).get(current_server, {})

        server_info = server_details.get('server_info', {})

        # Server ID
        server_id = server_info.get('server_id', 'Unknown')
        embed.add_field(name="🔗 ID del Servidor", value=f"```{{{server_id}}}```", inline=True)

        # Check if game is favorite
        is_favorite = (user_id and game_id and 
                      user_id in scraper.user_favorites and 
                      game_id in scraper.user_favorites[user_id])

        fav_status = "⭐ Favorito" if is_favorite else "☆ No Favorito"
        embed.add_field(name="⭐ Estado", value=fav_status, inline=True)

        # Server discovery time
        discovered_at = server_details.get('discovered_at')
        if discovered_at:
            try:
                disc_time = datetime.fromisoformat(discovered_at)
                time_ago = datetime.now() - disc_time
                if time_ago.days > 0:
                    time_str = f"hace {time_ago.days}d"
                elif time_ago.seconds > 3600:
                    time_str = f"hace {time_ago.seconds//3600}h"
                else:
                    time_str = f"hace {time_ago.seconds//60}m"
                embed.add_field(name="🕐 Descubierto", value=time_str, inline=True)
            except:
                pass

        # Server Link in code block
        embed.add_field(name="🔗 Enlace del Servidor", value=f"```{current_server}```", inline=False)

        # Set game image as thumbnail if available
        game_image_url = self.game_info.get('game_image_url')
        if game_image_url:
            embed.set_thumbnail(url=game_image_url)

        # Footer with server count
        embed.set_footer(text=f"Servidor {self.current_index + 1}/{self.total_servers} | Usuario: {self.authorized_user_id}")

        # Always return None for file since we're using URL-based images
        return embed, None

# Game search select menu
class GameSearchSelect(discord.ui.Select):
    def __init__(self, search_results, user_id):
        self.search_results = search_results
        self.user_id = user_id

        options = []
        for result in search_results[:5]:  # Limit to 5 results
            options.append(discord.SelectOption(
                label=result['name'][:100],  # Discord limit
                description=f"ID: {result['id']}",
                value=result['id']
            ))

        super().__init__(placeholder="Selecciona un juego para hacer scraping...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Solo quien ejecutó el comando puede seleccionar.", 
                ephemeral=True
            )
            return

        # Mark as selected
        self._selected = True

        selected_game_id = self.values[0]
        selected_game = next(game for game in self.search_results if game['id'] == selected_game_id)

        # Check cooldown
        cooldown_remaining = scraper.check_cooldown(self.user_id)
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Start scraping for selected game
        await interaction.response.defer()

        # Set cooldown
        scraper.set_cooldown(self.user_id)

        try:
            # Initial status embed
            start_embed = discord.Embed(
                title="🎮 ROBLOX PRIVATE SERVER LINKS",
                description=f"Se ha iniciado la búsqueda de servidores para **{selected_game['name']}** (ID: {selected_game_id})!",
                color=0x2F3136
            )
            start_embed.add_field(name="🎯 Juego", value=f"```{selected_game['name']}```", inline=True)
            start_embed.add_field(name="🆔 ID", value=f"```{selected_game_id}```", inline=True)
            start_embed.add_field(name="📊 Estado", value="Inicializando...", inline=True)

            start_time = time.time()
            message = await interaction.followup.send(embed=start_embed)

            # Run scraping with real-time updates
            await scrape_with_updates(message, start_time, selected_game_id, self.user_id, interaction.user)

        except Exception as e:
            logger.error(f"Error in game search scrape: {e}")
            error_embed = discord.Embed(
                title="❌ Error en Búsqueda",
                description="Ocurrió un error durante la búsqueda de servidores.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

class GameSearchView(discord.ui.View):
    def __init__(self, search_results, user_id):
        super().__init__(timeout=300)
        self.add_item(GameSearchSelect(search_results, user_id))

@bot.tree.command(name="searchgame", description="Buscar un juego por nombre para hacer scraping")
async def search_game_command(interaction: discord.Interaction, nombre: str):
    """Search for games by name"""
    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)

        # Check cooldown for searching
        cooldown_remaining = scraper.check_cooldown(user_id, 2)  # 2 minute cooldown for search
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de buscar nuevamente.",
                color=0xff9900
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Search for games
        search_results = await scraper.search_game_by_name(nombre)

        if not search_results:
            embed = discord.Embed(
                title="❌ No se encontraron resultados",
                description=f"No se encontraron juegos con el nombre **{nombre}**.\n\n**Sugerencias:**\n• Prueba con nombres más comunes\n• Usa abreviaciones (ej: DTI, MM2, TOH)\n• Intenta con `/game` para búsqueda automática\n• Usa `/scrape [id]` si tienes el ID del juego",
                color=0xff3333
            )
            embed.add_field(
                name="💡 Ejemplos de búsqueda:",
                value="• `dress to impress` o `dti`\n• `murder mystery` o `mm2`\n• `tower of hell` o `toh`\n• `blox fruits`\n• `adopt me`",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Create search results embed
        embed = discord.Embed(
            title="🔍 Resultados de Búsqueda",
            description=f"Se encontraron **{len(search_results)}** resultados para **{nombre}**:",
            color=0x00ff88
        )

        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }

        for i, game in enumerate(search_results, 1):
            category = game.get('category', 'other')
            emoji = category_emoji.get(category, '🎮')
            relevance_stars = "⭐" * min(int(game.get('relevance', 0) * 3) + 1, 3)

            embed.add_field(
                name=f"{i}. {emoji} {game['name'][:45]}{'...' if len(game['name']) > 45 else ''}",
                value=f"ID: `{game['id']}` • {relevance_stars} • {category.title()}",
                inline=False
            )

        embed.set_footer(text="Selecciona un juego del menú desplegable para empezar el scraping")

        # Create view with select menu
        view = GameSearchView(search_results, user_id)
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        logger.error(f"Error in search game command: {e}")
        error_embed = discord.Embed(
            title="❌ Error de Búsqueda",
            description="Ocurrió un error al buscar juegos.",
            color=0xff0000
        )
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="game", description="Buscar y hacer scraping automáticamente por nombre de juego")
async def game_command(interaction: discord.Interaction, nombre: str):
    """Search for a game by name and automatically start scraping the best match"""
    await interaction.response.defer()

    try:
        user_id = str(interaction.user.id)

        # Check cooldown
        cooldown_remaining = scraper.check_cooldown(user_id)
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏰ Cooldown Activo",
                description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar game nuevamente.",
                color=0xff9900
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Search for games
        search_results = await scraper.search_game_by_name(nombre)

        if not search_results:
            embed = discord.Embed(
                title="❌ No se encontraron resultados",
                description=f"No se encontraron juegos con el nombre **{nombre}**.",
                color=0xff3333
            )
            embed.add_field(
                name="💡 Sugerencias:",
                value="• Usa `/searchgame` para ver opciones\n• Prueba con nombres más comunes\n• Usa abreviaciones (DTI, MM2, TOH)\n• Verifica la ortografía",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Get the best match (highest relevance)
        best_match = search_results[0]
        game_id = best_match['id']
        game_name = best_match['name']

        # Set cooldown
        scraper.set_cooldown(user_id)

        # If multiple high-relevance results, show selection menu
        if len(search_results) > 1 and search_results[1].get('relevance', 0) >= 0.9:
            embed = discord.Embed(
                title="🎯 Múltiples Coincidencias Encontradas",
                description=f"Se encontraron varios juegos similares a **{nombre}**. Selecciona el correcto:",
                color=0xffaa00
            )

            category_emoji = {
                "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                "building": "🏗️", "anime": "🌸", "other": "🎮"
            }

            for i, game in enumerate(search_results[:5], 1):
                category = game.get('category', 'other')
                emoji = category_emoji.get(category, '🎮')
                relevance_stars = "⭐" * min(int(game.get('relevance', 0) * 3) + 1, 3)

                embed.add_field(
                    name=f"{i}. {emoji} {game['name'][:45]}{'...' if len(game['name']) > 45 else ''}",
                    value=f"ID: `{game['id']}` • {relevance_stars}",
                    inline=False
                )

            embed.set_footer(text="El primer resultado se seleccionará automáticamente en 10 segundos")

            view = GameSearchView(search_results, user_id)
            message = await interaction.followup.send(embed=embed, view=view)

            # Wait 10 seconds, then auto-select first option
            await asyncio.sleep(10)
            try:
                # Check if user hasn't selected anything
                if view.children and not any(getattr(child, '_selected', False) for child in view.children):
                    # Auto-proceed with best match
                    pass  # Continue to scraping below
                else:
                    return  # User made a selection, exit
            except:
                pass  # Continue to scraping

        # Start scraping for best match
        try:
            # Initial status embed
            start_embed = discord.Embed(
                title="ROBLOX PRIVATE SERVER LINKS",
                description=f"Búsqueda automática iniciada para **{game_name}** (ID: {game_id}). Se seleccionó automáticamente la mejor coincidencia para '{nombre}'.",
                color=0x2F3136
            )
            start_embed.add_field(name="Juego Seleccionado", value=f"```{game_name}```", inline=True)
            start_embed.add_field(name="ID", value=f"```{game_id}{game_id}```", inline=True)
            # Get initial count for this user and game
            initial_count = len(scraper.links_by_user.get(user_id, {}).get(game_id, {}).get('links', []))
            start_embed.add_field(name="📊 Base de Datos Actual", value=f"{initial_count} servidores", inline=True)
            start_embed.add_field(name="🔄 Estado", value="Inicializando...", inline=True)
            start_time = time.time()

            # Create view with follow button
            start_view = discord.ui.View(timeout=None)
            follow_button_start = discord.ui.Button(
                label="👤 Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            start_view.add_item(follow_button_start)

            # Send initial message
            message = await interaction.followup.send(embed=start_embed, view=start_view)

            # Run scraping with real-time updates
            await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)

        except Exception as e:
            logger.error(f"Error in scrape command: {e}")
            error_embed = discord.Embed(
                title="🎮 ROBLOX PRIVATE SERVER LINKS",
                description="Ocurrió un error durante el proceso de scraping.",
                color=0x2F3136
            )
            error_embed.add_field(name="📝 Detalles del Error", value=f"```{str(e)[:200]}```", inline=False)
            error_embed.add_field(name="🔄 Reintentar", value="Puedes ejecutar `/scrape` nuevamente", inline=False)

            # Error view with follow button
            error_view = discord.ui.View(timeout=None)
            follow_button_error = discord.ui.Button(
                label="👤 Seguir a hesiz",
                style=discord.ButtonStyle.secondary,
                url="https://www.roblox.com/users/11834624/profile"
            )
            error_view.add_item(follow_button_error)

            await interaction.followup.send(embed=error_embed, view=error_view)

    else:
        # It's a game name, search for it first
        try:
            # Check cooldown for searching
            cooldown_remaining = scraper.check_cooldown(user_id, 2)  # 2 minute cooldown for search
            if cooldown_remaining:
                embed = discord.Embed(
                    title="⏰ Cooldown Activo",
                    description=f"Debes esperar **{cooldown_remaining}** segundos antes de buscar nuevamente.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Search for games
            search_results = await scraper.search_game_by_name(juego)

            if not search_results:
                embed = discord.Embed(
                    title="❌ No se encontraron resultados",
                    description=f"No se encontraron juegos con el nombre **{juego}**.\n\n**Sugerencias:**\n• Prueba con nombres más comunes\n• Usa abreviaciones (ej: DTI, MM2, TOH)\n• Usa el ID del juego directamente si lo tienes",
                    color=0xff3333
                )
                embed.add_field(
                    name="💡 Ejemplos de búsqueda:",
                    value="• `dress to impress` o `dti`\n• `murder mystery` o `mm2`\n• `tower of hell` o `toh`\n• `blox fruits`\n• `adopt me`\n• `10449761463` (ID directo)",
                    inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Get the best match (highest relevance)
            best_match = search_results[0]
            game_id = best_match['id']
            game_name = best_match['name']

            # If multiple high-relevance results, show selection menu
            if len(search_results) > 1 and search_results[1].get('relevance', 0) >= 0.9:
                embed = discord.Embed(
                    title="🎯 Múltiples Coincidencias Encontradas",
                    description=f"Se encontraron varios juegos similares a **{juego}**. Selecciona el correcto:",
                    color=0xffaa00
                )

                category_emoji = {
                    "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                    "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                    "building": "🏗️", "anime": "🌸", "other": "🎮"
                }

                for i, game in enumerate(search_results[:5], 1):
                    category = game.get('category', 'other')
                    emoji = category_emoji.get(category, '🎮')
                    relevance_stars = "⭐" * min(int(game.get('relevance', 0) * 3) + 1, 3)

                    embed.add_field(
                        name=f"{i}. {emoji} {game['name'][:45]}{'...' if len(game['name']) > 45 else ''}",
                        value=f"ID: `{game['id']}` • {relevance_stars}",
                        inline=False
                    )

                embed.set_footer(text="El primer resultado se seleccionará automáticamente en 10 segundos")

                view = GameSearchView(search_results, user_id)
                message = await interaction.followup.send(embed=embed, view=view)

                # Wait 10 seconds, then auto-select first option
                await asyncio.sleep(10)
                try:
                    # Check if user hasn't selected anything
                    if view.children and not any(getattr(child, '_selected', False) for child in view.children):
                        # Auto-proceed with best match
                        pass  # Continue to scraping below
                    else:
                        return  # User made a selection, exit
                except:
                    pass  # Continue to scraping

            # Check cooldown again before scraping
            cooldown_remaining = scraper.check_cooldown(user_id)
            if cooldown_remaining:
                embed = discord.Embed(
                    title="⏰ Cooldown Activo",
                    description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.",
                    color=0xff9900
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Set cooldown
            scraper.set_cooldown(user_id)

            # Start scraping for best match
            try:
                # Initial status embed
                start_embed = discord.Embed(
                    title="ROBLOX PRIVATE SERVER LINKS",
                    description=f"Búsqueda automática iniciada para **{game_name}** (ID: {game_id}). Se seleccionó automáticamente la mejor coincidencia para '{juego}'.",
                    color=0x2F3136
                )
                start_embed.add_field(name="Juego Seleccionado", value=f"```{game_name}```", inline=True)
                start_embed.add_field(name="ID", value=f"```{game_id}```", inline=True)
                start_embed.add_field(name="Estado", value="Inicializando...", inline=True)

                category = best_match.get('category', 'other')
                start_embed.add_field(name="Categoría", value=f"{category.title()}", inline=True)

                relevance_percentage = int(best_match.get('relevance', 0) * 100)
                start_embed.add_field(name="Precisión", value=f"{relevance_percentage}%", inline=True)

                start_time = time.time()

                # Create view with follow button
                start_view = discord.ui.View(timeout=None)
                follow_button_start = discord.ui.Button(
                    label="👤 Seguir a hesiz",
                    style=discord.ButtonStyle.secondary,
                    url="https://www.roblox.com/users/11834624/profile"
                )
                start_view.add_item(follow_button_start)

                # Send initial message or edit existing
                if 'message' in locals():
                    await message.edit(embed=start_embed, view=start_view)
                else:
                    message = await interaction.followup.send(embed=start_embed, view=start_view)

                # Run scraping with real-time updates
                await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)

            except Exception as e:
                logger.error(f"Error in auto scrape: {e}")
                error_embed = discord.Embed(
                    title="❌ Error en Scraping Automático",
                    description="Ocurrió un error durante el scraping automático.",
                    color=0xff0000
                )
                error_embed.add_field(name="🔄 Alternativa", value=f"Usa `/scrape {game_id}` para intentar manualmente", inline=False)
                await interaction.followup.send(embed=error_embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Error in game search: {e}")
            error_embed = discord.Embed(
                title="❌ Error en Búsqueda",
                description="Ocurrió un error al buscar el juego.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    user_id = str(interaction.user.id)

    # Check cooldown
    cooldown_remaining = scraper.check_cooldown(user_id)
    if cooldown_remaining:
        embed = discord.Embed(
            title="⏰ Cooldown Activo",
            description=f"Debes esperar **{cooldown_remaining}** segundos antes de usar scrape nuevamente.\n\n**Razón:** Prevención de spam y sobrecarga del sistema.",
            color=0xff9900
        )
        embed.add_field(name="💡 Mientras esperas:", value="• Usa `/servertest` para ver tus servidores\n• Usa `/favorites` para ver favoritos\n• Usa `/history` para ver historial", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    # Set cooldown
    scraper.set_cooldown(user_id)

    try:
        # Initial status embed
        start_embed = discord.Embed(
            title="🎮 ROBLOX PRIVATE SERVER LINKS",
            description=f"¡Se ha iniciado exitosamente la búsqueda de servidores para el juego ID: **{game_id}**! Manténlo seguro y no lo compartas con nadie.",
            color=0x2F3136
        )
        start_embed.add_field(name="🆔 ID del Juego", value=f"```{game_id}```", inline=True)
        # Get initial count for this user and game
        initial_count = len(scraper.links_by_user.get(user_id, {}).get(game_id, {}).get('links', []))
        start_embed.add_field(name="📊 Base de Datos Actual", value=f"{initial_count} servidores", inline=True)
        start_embed.add_field(name="🔄 Estado", value="Inicializando...", inline=True)
        start_time = time.time()

        # Create view with follow button
        start_view = discord.ui.View(timeout=None)
        follow_button_start = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        start_view.add_item(follow_button_start)

        # Send initial message
        message = await interaction.followup.send(embed=start_embed, view=start_view)

        # Run scraping with real-time updates
        await scrape_with_updates(message, start_time, game_id, user_id, interaction.user)

    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        error_embed = discord.Embed(
            title="🎮 ROBLOX PRIVATE SERVER LINKS",
            description="Ocurrió un error durante el proceso de scraping.",
            color=0x2F3136
        )
        error_embed.add_field(name="📝 Detalles del Error", value=f"```{str(e)[:200]}```", inline=False)
        error_embed.add_field(name="🔄 Reintentar", value="Puedes ejecutar `/scrape` nuevamente", inline=False)

        # Error view with follow button
        error_view = discord.ui.View(timeout=None)
        follow_button_error = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        error_view.add_item(follow_button_error)

        await interaction.followup.send(embed=error_embed, view=error_view)

async def scrape_with_updates(message, start_time, game_id, user_id, discord_user):
    """Run scraping with real-time Discord message updates and user notification"""
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
            game_name = game_info['game_name']
            category = scraper.categorize_game(game_name)
            scraper.game_categories[game_id] = category

            scraper.links_by_user[user_id][game_id] = {
                'links': [],
                'game_name': game_name,
                'game_image_url': game_info.get('game_image_url'),
                'category': category,
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
                    category = scraper.links_by_user[user_id][game_id].get('category', 'other')

                    progress_embed = discord.Embed(
                        title="ROBLOX PRIVATE SERVER LINKS",
                        description=f"Procesando {len(server_links)} servidores encontrados para **{game_name}** (ID: {game_id})... Búsqueda activa de servidores VIP.",
                        color=0x2F3136
                    )

                    # Add game image if available
                    game_image_url = scraper.links_by_user[user_id][game_id].get('game_image_url')
                    if game_image_url:
                        progress_embed.set_thumbnail(url=game_image_url)

                    progress_embed.add_field(name="Servidores Encontrados", value=f"**{new_links_count}**", inline=True)
                    progress_embed.add_field(name="Progreso", value=f"{i + 1}/{len(server_links)}", inline=True)
                    progress_embed.add_field(name="Tiempo", value=f"{elapsed:.0f}s", inline=True)

                    if eta > 0:
                        progress_embed.add_field(name="ETA", value=f"{eta:.0f}s", inline=True)

                    progress_embed.add_field(name="Tu Total", value=f"{len(scraper.links_by_user[user_id][game_id]['links'])} servidores", inline=True)

                    category_emoji = {
                        "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                        "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                        "building": "🏗️", "anime": "🌸", "other": "🎮"
                    }
                    progress_embed.add_field(name="Categoría", value=f"{category_emoji.get(category, '🎮')} {category.title()}", inline=True)

                    # Progress bar
                    progress_percentage = ((i + 1) / len(server_links)) * 100
                    bar_length = 10
                    filled_length = int(bar_length * (i + 1) // len(server_links))
                    bar = "█" * filled_length + "░" * (bar_length - filled_length)
                    progress_embed.add_field(
                        name="Progreso Visual", 
                        value=f"`{bar}` {progress_percentage:.1f}%", 
                        inline=False
                    )

                    view = discord.ui.View(timeout=None)
                    follow_button = discord.ui.Button(
                        label="👤 Seguir a hesiz",
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

        # Add to usage history
        scraper.add_usage_history(user_id, game_id, f"Found {new_links_count} servers", 'scrape_complete')

        logger.info(f"✅ Scraping completed in {total_time:.1f}s")
        logger.info(f"📈 Found {new_links_count} new VIP links (User Total: {final_count})")
        scraper.save_links()

        # Final completion embed
        game_name = scraper.links_by_user[user_id][game_id]['game_name']
        category = scraper.links_by_user[user_id][game_id].get('category', 'other')

        complete_embed = discord.Embed(
            title="✅ BÚSQUEDA COMPLETADA",
            description=f"¡La búsqueda de servidores VIP ha sido completada exitosamente para **{game_name}** (ID: {game_id})! {discord_user.mention}",
            color=0x00ff88
        )

        # Add game image if available
        game_image_url = scraper.links_by_user[user_id][game_id].get('game_image_url')
        if game_image_url:
            complete_embed.set_thumbnail(url=game_image_url)

        complete_embed.add_field(name="🆕 Nuevos Servidores", value=f"**{new_links_count}**", inline=True)
        complete_embed.add_field(name="📊 Tu Total", value=f"**{final_count}** servidores", inline=True)
        complete_embed.add_field(name="⏱️ Duración", value=f"{total_time:.1f}s", inline=True)

        complete_embed.add_field(name="⚡ Velocidad", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)
        complete_embed.add_field(name="✅ Tasa de Éxito", value=f"{(new_links_count / max(processed_count, 1) * 100):.1f}%", inline=True)

        category_emoji = {
            "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
            "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
            "building": "🏗️", "anime": "🌸", "other": "🎮"
        }
        complete_embed.add_field(name="📂 Categoría", value=f"{category_emoji.get(category, '🎮')} {category.title()}", inline=True)

        complete_embed.add_field(name="📈 Total Procesados", value=f"{processed_count} servidores", inline=True)

        current_time = datetime.now().strftime('%H:%M:%S')
        complete_embed.add_field(name="🕐 Completado", value=current_time, inline=True)

        if new_links_count > 0:
            complete_embed.add_field(
                name="🎉 ¡Éxito Total!", 
                value=f"¡Se encontraron {new_links_count} nuevo{'s' if new_links_count != 1 else ''} servidor{'es' if new_links_count != 1 else ''}!", 
                inline=False
            )
        else:
            complete_embed.add_field(
                name="ℹ️ Sin Nuevos Servidores", 
                value="Todos los servidores disponibles ya están en la base de datos.", 
                inline=False
            )

        # Final completion view with user-exclusive buttons
        complete_view = discord.ui.View(timeout=None)

        # VIP server button (user-exclusive)
        class ExclusiveVIPButton(discord.ui.Button):
            def __init__(self, target_user_id, game_id, disabled=False):
                super().__init__(
                    label="🎮 Obtener Servidor VIP",
                    style=discord.ButtonStyle.primary,
                    disabled=disabled
                )
                self.target_user_id = target_user_id
                self.game_id = game_id

            async def callback(self, interaction: discord.Interaction):
                if str(interaction.user.id) != self.target_user_id:
                    await interaction.response.send_message(
                        "❌ Solo quien ejecutó el comando puede usar este botón.", 
                        ephemeral=True
                    )
                    return

                await interaction.response.defer()
                try:
                    # Get all servers from the user's game
                    servers = scraper.links_by_user[self.target_user_id][self.game_id]['links']
                    if not servers:
                        error_embed = discord.Embed(
                            title="❌ No hay Enlaces VIP Disponibles",
                            description="No se encontraron servidores VIP para este juego.",
                            color=0xff3333
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
                        return

                    # Create browser view for this specific game
                    game_info = {
                        'game_id': self.game_id,
                        'game_name': scraper.links_by_user[self.target_user_id][self.game_id].get('game_name', f'Game {self.game_id}'),
                        'game_image_url': scraper.links_by_user[self.target_user_id][self.game_id].get('game_image_url'),
                        'category': scraper.links_by_user[self.target_user_id][self.game_id].get('category', 'other'),
                        'user_id': self.target_user_id
                    }

                    view = ServerBrowserView(servers, 0, game_info, self.target_user_id)
                    embed, file = view.create_server_embed()

                    if file:
                        await interaction.followup.send(embed=embed, file=file, view=view)
                    else:
                        await interaction.followup.send(embed=embed, view=view)

                except Exception as e:
                    logger.error(f"Error in get_vip_server button: {e}")
                    error_embed = discord.Embed(
                        title="❌ Error Occurred",
                        description="Ocurrió un error al obtener el servidor VIP.",
                        color=0xff0000
                    )
                    await interaction.followup.send(embed=error_embed, ephemeral=True)

        vip_button = ExclusiveVIPButton(
            user_id, 
            game_id, 
            disabled=len(scraper.links_by_user.get(user_id, {}).get(game_id, {}).get('links', [])) == 0
        )
        complete_view.add_item(vip_button)

        follow_button_final = discord.ui.Button(
            label="👤 Seguir a hesiz",
            style=discord.ButtonStyle.secondary,
            url="https://www.roblox.com/users/11834624/profile"
        )
        complete_view.add_item(follow_button_final)

        await message.edit(embed=complete_embed, view=complete_view)

        # Send notification ping if new servers were found
        if new_links_count > 0:
            notification_embed = discord.Embed(
                title="🔔 ¡Nuevos Servidores Encontrados!",
                description=f"¡{discord_user.mention}, se encontraron **{new_links_count}** nuevos servidores VIP para **{game_name}**!",
                color=0x00ff88
            )
            notification_embed.add_field(name="🎮 Usa", value="`/servertest`", inline=True)
            notification_embed.add_field(name="⭐ O", value="Haz clic en **Obtener Servidor VIP**", inline=True)

            # Send as a separate message to ensure ping
            await message.channel.send(embed=notification_embed, delete_after=10)

    except Exception as e:
        logger.error(f"💥 Scraping failed: {e}")
        raise
    finally:
        if driver:
            driver.quit()

@bot.tree.command(name="stats", description="Mostrar estadísticas completas de enlaces VIP")
async def stats(interaction: discord.Interaction):
    """Show detailed statistics about collected VIP links"""
    try:
        embed = discord.Embed(
            title="📊 Estadísticas de Base de Datos VIP",
            description="**Vista completa de datos recopilados**",
            color=0x3366ff,
            timestamp=datetime.now()
        )

        # Main stats
        user_id = str(interaction.user.id)
        user_links = 0
        total_links = 0
        user_games_count = 0
        user_favorites_count = len(scraper.user_favorites.get(user_id, []))

        # Calculate user-specific links
        user_games = scraper.links_by_user.get(user_id, {})
        user_games_count = len(user_games)
        for game_data in user_games.values():
            user_links += len(game_data.get('links', []))

        # Calculate total links across all users
        total_users = len(scraper.links_by_user)
        for user_games in scraper.links_by_user.values():
            for game_data in user_games.values():
                total_links += len(game_data.get('links', []))

        embed.add_field(name="🗃️ Tus Enlaces", value=f"**{user_links}**", inline=True)
        embed.add_field(name="🎮 Tus Juegos", value=f"**{user_games_count}**", inline=True)
        embed.add_field(name="⭐ Tus Favoritos", value=f"**{user_favorites_count}**", inline=True)

        embed.add_field(name="🌐 Enlaces Totales", value=f"**{total_links}**", inline=True)
        embed.add_field(name="👥 Usuarios Totales", value=f"**{total_users}**", inline=True)
        embed.add_field(name="📈 Total Escaneado", value=f"**{scraper.scraping_stats.get('total_scraped', 0)}**", inline=True)

        # Performance metrics
        embed.add_field(name="✅ Exitosos", value=f"{scraper.scraping_stats.get('successful_extractions', 0)}", inline=True)
        embed.add_field(name="❌ Fallidos", value=f"{scraper.scraping_stats.get('failed_extractions', 0)}", inline=True)
        embed.add_field(name="⚡ Velocidad", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} serv/min", inline=True)

        # Cooldown status
        cooldown_remaining = scraper.check_cooldown(user_id)
        if cooldown_remaining:
            embed.add_field(name="⏰ Cooldown", value=f"{cooldown_remaining}s restantes", inline=True)
        else:
            embed.add_field(name="✅ Disponible", value="Sin cooldown", inline=True)

        # Success rate calculation
        total_scraped = scraper.scraping_stats.get('total_scraped', 0)
        successful = scraper.scraping_stats.get('successful_extractions', 0)
        if total_scraped > 0:
            success_rate = (successful / total_scraped) * 100
            embed.add_field(name="📊 Tasa de Éxito", value=f"{success_rate:.1f}%", inline=True)

        # Category breakdown for user
        user_categories = {}
        for game_data in user_games.values():
            category = game_data.get('category', 'other')
            user_categories[category] = user_categories.get(category, 0) + 1

        if user_categories:
            category_text = ""
            category_emoji = {
                "rpg": "⚔️", "simulator": "🏗️", "action": "💥", "racing": "🏁",
                "horror": "👻", "social": "👥", "sports": "⚽", "puzzle": "🧩",
                "building": "🏗️", "anime": "🌸", "other": "🎮"
            }
            for category, count in sorted(user_categories.items(), key=lambda x: x[1], reverse=True):
                emoji = category_emoji.get(category, '🎮')
                category_text += f"{emoji} {category.title()}: {count}\n"

            embed.add_field(name="📂 Tus Categorías", value=category_text[:1024], inline=True)

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
                            time_str = f"hace {time_diff.days}d {time_diff.seconds//3600}h"
                        elif time_diff.seconds > 3600:
                            time_str = f"hace {time_diff.seconds//3600}h {(time_diff.seconds%3600)//60}m"
                        else:
                            time_str = f"hace {time_diff.seconds//60}m"
                        embed.add_field(name="🕐 Última Actualización", value=time_str, inline=True)
                    except:
                        embed.add_field(name="🕐 Última Actualización", value="Recientemente", inline=True)

        # File size
        try:
            file_size = Path(scraper.vip_links_file).stat().st_size if Path(scraper.vip_links_file).exists() else 0
            size_kb = file_size / 1024
            embed.add_field(name="💾 Tamaño de BD", value=f"{size_kb:.1f} KB", inline=True)
        except:
            embed.add_field(name="💾 Tamaño de BD", value="Desconocido", inline=True)

        # Commands info
        embed.add_field(
            name="🎮 Comandos Disponibles", 
            value="• `/scrape [id_o_nombre]` - 🚀 **ACTUALIZADO** Buscar por ID o nombre automáticamente\n• `/servertest` - Ver servidores\n• `/favorites` - Ver favoritos\n• `/history` - Ver historial", 
            inline=False
        )

        embed.set_footer(text="Usa /scrape para encontrar más servidores • /servertest para obtener enlace")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await interaction.response.send_message("❌ Ocurrió un error al obtener estadísticas.", ephemeral=True)

async def main():
    """Main function to run both scraper and bot"""
    logger.info("🚀 Starting VIP Server Scraper Bot...")

    # Start the bot
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN not found in environment variables")
        return

    await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())