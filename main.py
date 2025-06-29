

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
        """Create Firefox driver with Replit-compatible configuration"""
        try:
            # Start Xvfb virtual display for headless environment
            try:
                subprocess.run(['pkill', 'Xvfb'], capture_output=True, timeout=5)
            except:
                pass
            
            # Start virtual display
            xvfb_process = subprocess.Popen([
                'Xvfb', ':99', '-screen', '0', '1920x1080x24', '-ac'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Set display environment variable
            os.environ['DISPLAY'] = ':99'
            
            # Wait a moment for Xvfb to start
            time.sleep(2)
            
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service
            
            firefox_options = FirefoxOptions()
            # Remove --headless since we're using Xvfb
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--disable-gpu")
            firefox_options.add_argument("--disable-extensions")
            firefox_options.add_argument("--disable-web-security")
            firefox_options.add_argument("--disable-logging")
            firefox_options.add_argument("--width=1920")
            firefox_options.add_argument("--height=1080")
            firefox_options.add_argument("--disable-blink-features=AutomationControlled")
            
            # Set Firefox preferences for better compatibility
            firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0")
            firefox_options.set_preference("dom.webdriver.enabled", False)
            firefox_options.set_preference("useAutomationExtension", False)
            firefox_options.set_preference("marionette.logging", "FATAL")
            firefox_options.set_preference("browser.startup.homepage_override.mstone", "ignore")
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
            firefox_options.set_preference("startup.homepage_welcome_url", "about:blank")
            firefox_options.set_preference("startup.homepage_welcome_url.additional", "about:blank")
            
            # Find geckodriver
            result = subprocess.run(['which', 'geckodriver'], capture_output=True, text=True)
            if result.returncode == 0:
                geckodriver_path = result.stdout.strip()
                logger.info(f"Using geckodriver at: {geckodriver_path}")
                service = Service(geckodriver_path)
            else:
                # Fallback to default
                service = Service()
                logger.info("Using default geckodriver service")
            
            # Create driver
            driver = webdriver.Firefox(service=service, options=firefox_options)
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            logger.info("✅ Firefox driver created successfully with Xvfb")
            return driver
            
        except Exception as e:
            logger.error(f"Error creating Firefox driver: {e}")
            # Try fallback with headless mode
            try:
                logger.info("🔄 Trying fallback headless mode...")
                firefox_options = FirefoxOptions()
                firefox_options.add_argument("--headless")
                firefox_options.add_argument("--no-sandbox")
                firefox_options.add_argument("--disable-dev-shm-usage")
                
                driver = webdriver.Firefox(options=firefox_options)
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                logger.info("✅ Firefox driver created with fallback headless mode")
                return driver
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                raise Exception(f"Firefox driver creation failed: {e}")
    
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

@bot.tree.command(name="servertest", description="Get a random VIP server link with detailed information")
async def servertest(interaction: discord.Interaction):
    """Send a random VIP server link with comprehensive details"""
    await interaction.response.defer()
    
    try:
        vip_link, details = scraper.get_random_link()
        
        if vip_link:
            # Create super detailed embed
            embed = discord.Embed(
                title="🎮 Random VIP Server",
                color=0x00ff88,
                timestamp=datetime.now()
            )
            
            # Main server link
            embed.add_field(
                name="🔗 VIP Server Link", 
                value=f"[**Click here to join!**]({vip_link})", 
                inline=False
            )
            
            # Server details if available
            if details:
                server_info = details.get('server_info', {})
                
                # Server identification
                server_id = server_info.get('server_id', 'Unknown')
                embed.add_field(name="🆔 Server ID", value=f"`{server_id}`", inline=True)
                
                # Discovery time
                discovered = details.get('discovered_at', 'Unknown')
                if discovered != 'Unknown':
                    try:
                        disc_time = datetime.fromisoformat(discovered.replace('Z', '+00:00'))
                        time_ago = datetime.now() - disc_time.replace(tzinfo=None)
                        if time_ago.days > 0:
                            time_str = f"{time_ago.days}d {time_ago.seconds//3600}h ago"
                        elif time_ago.seconds > 3600:
                            time_str = f"{time_ago.seconds//3600}h {(time_ago.seconds%3600)//60}m ago"
                        else:
                            time_str = f"{time_ago.seconds//60}m ago"
                        embed.add_field(name="🕐 Discovered", value=time_str, inline=True)
                    except:
                        embed.add_field(name="🕐 Discovered", value="Recently", inline=True)
                
                # Extraction speed
                extraction_time = details.get('extraction_time', 0)
                embed.add_field(name="⚡ Extraction Time", value=f"{extraction_time}s", inline=True)
                
                # Server description
                description = server_info.get('description', 'No description')
                if len(description) > 100:
                    description = description[:97] + "..."
                embed.add_field(name="📝 Description", value=description, inline=False)
            
            # Database statistics
            embed.add_field(name="📊 Database Stats", value=f"**{len(scraper.unique_vip_links)}** total servers", inline=True)
            
            # Last scrape info
            last_scrape = scraper.scraping_stats.get('last_scrape_time')
            if last_scrape:
                try:
                    last_time = datetime.fromisoformat(last_scrape)
                    time_since = datetime.now() - last_time
                    if time_since.days > 0:
                        last_str = f"{time_since.days}d ago"
                    elif time_since.seconds > 3600:
                        last_str = f"{time_since.seconds//3600}h ago"
                    else:
                        last_str = f"{time_since.seconds//60}m ago"
                    embed.add_field(name="🔄 Last Scrape", value=last_str, inline=True)
                except:
                    embed.add_field(name="🔄 Last Scrape", value="Unknown", inline=True)
            
            # Success rate
            total_scraped = scraper.scraping_stats.get('total_scraped', 0)
            successful = scraper.scraping_stats.get('successful_extractions', 0)
            if total_scraped > 0:
                success_rate = (successful / total_scraped) * 100
                embed.add_field(name="📈 Success Rate", value=f"{success_rate:.1f}%", inline=True)
            
            # Footer with additional info
            embed.set_footer(
                text=f"🎯 Enjoy your gaming! • Speed: {scraper.scraping_stats.get('servers_per_minute', 0)} servers/min"
            )
            
            # Add thumbnail (Roblox logo)
            embed.set_thumbnail(url="https://tr.rbxcdn.com/30DAY-AvatarHeadshot-84420265CB769E26FE22025E6E1F77F8-Png/150/150/AvatarHeadshot/Png")
            
            await interaction.followup.send(embed=embed)
            
        else:
            embed = discord.Embed(
                title="❌ No VIP Links Available",
                description="No VIP server links found in database.\n\n**Try running the scraper first with `/scrape`**",
                color=0xff3333
            )
            embed.add_field(name="💡 Tip", value="Use `/scrape` to find new servers!", inline=False)
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error in servertest command: {e}")
        error_embed = discord.Embed(
            title="💥 Error Occurred",
            description="An error occurred while fetching the server link.",
            color=0xff0000
        )
        error_embed.add_field(name="Error Details", value=f"```{str(e)[:100]}```", inline=False)
        await interaction.followup.send(embed=error_embed, ephemeral=True)

@bot.tree.command(name="scrape", description="Start scraping for new VIP server links")
async def scrape_command(interaction: discord.Interaction):
    """Manually trigger scraping with detailed progress tracking"""
    await interaction.response.defer()
    
    try:
        # Initial status embed
        start_embed = discord.Embed(
            title="🔄 Scraping Started",
            description="**Starting VIP server link scraping...**\n\n🔍 Searching for available servers\n⏳ This may take a few minutes",
            color=0xffaa00
        )
        start_embed.add_field(name="Current Database", value=f"{len(scraper.unique_vip_links)} servers", inline=True)
        start_embed.add_field(name="Status", value="🚀 Initializing...", inline=True)
        start_time = time.time()
        
        await interaction.followup.send(embed=start_embed)
        
        # Run scraping in background
        initial_count = len(scraper.unique_vip_links)
        await asyncio.get_event_loop().run_in_executor(None, scraper.scrape_vip_links)
        final_count = len(scraper.unique_vip_links)
        new_found = final_count - initial_count
        total_time = time.time() - start_time
        
        # Completion embed with detailed results
        complete_embed = discord.Embed(
            title="✅ Scraping Completed!",
            description="**Scraping session finished successfully**",
            color=0x00ff88
        )
        
        complete_embed.add_field(name="🆕 New Servers Found", value=f"**{new_found}**", inline=True)
        complete_embed.add_field(name="📊 Total Database", value=f"**{final_count}** servers", inline=True)
        complete_embed.add_field(name="⏱️ Duration", value=f"{total_time:.1f}s", inline=True)
        
        complete_embed.add_field(name="⚡ Speed", value=f"{scraper.scraping_stats.get('servers_per_minute', 0)} servers/min", inline=True)
        complete_embed.add_field(name="📈 Success Rate", value=f"{(scraper.scraping_stats.get('successful_extractions', 0) / max(scraper.scraping_stats.get('total_scraped', 1), 1) * 100):.1f}%", inline=True)
        complete_embed.add_field(name="🎯 Next Step", value="Use `/servertest` for a random server!", inline=True)
        
        if new_found > 0:
            complete_embed.add_field(
                name="🎉 Success!", 
                value=f"Found {new_found} new VIP server{'s' if new_found != 1 else ''}!", 
                inline=False
            )
        else:
            complete_embed.add_field(
                name="ℹ️ No New Servers", 
                value="All available servers are already in the database.", 
                inline=False
            )
        
        complete_embed.set_footer(text=f"Scraping completed at {datetime.now().strftime('%H:%M:%S')}")
        
        await interaction.followup.send(embed=complete_embed)
        
    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        error_embed = discord.Embed(
            title="💥 Scraping Failed",
            description="An error occurred during the scraping process.",
            color=0xff3333
        )
        error_embed.add_field(name="Error Details", value=f"```{str(e)[:200]}```", inline=False)
        error_embed.add_field(name="💡 Try Again", value="You can retry the `/scrape` command", inline=False)
        await interaction.followup.send(embed=error_embed)

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
