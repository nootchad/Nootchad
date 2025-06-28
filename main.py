
import asyncio
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import List, Set
import logging

import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VIPServerScraper:
    def __init__(self):
        self.vip_links_file = "vip_links.json"
        self.unique_vip_links: Set[str] = set()
        self.load_existing_links()
        
    def load_existing_links(self):
        """Load existing VIP links from JSON file"""
        try:
            if Path(self.vip_links_file).exists():
                with open(self.vip_links_file, 'r') as f:
                    data = json.load(f)
                    self.unique_vip_links = set(data.get('links', []))
                    logger.info(f"Loaded {len(self.unique_vip_links)} existing VIP links")
        except Exception as e:
            logger.error(f"Error loading existing links: {e}")
    
    def save_links(self):
        """Save VIP links to JSON file"""
        try:
            data = {
                'links': list(self.unique_vip_links),
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.unique_vip_links)
            }
            with open(self.vip_links_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.unique_vip_links)} VIP links to {self.vip_links_file}")
        except Exception as e:
            logger.error(f"Error saving links: {e}")
    
    def create_driver(self):
        """Create Chrome driver with optimized options"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.error(f"Error creating driver: {e}")
            raise
    
    def get_server_links(self, driver, max_retries=3):
        """Get server links with retry mechanism"""
        url = "https://rbxservers.xyz/games/109983668079237"
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching server links (attempt {attempt + 1})")
                driver.get(url)
                
                # Wait for server elements to load
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='/servers/']")))
                
                server_elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/servers/']")
                server_links = []
                
                for el in server_elements:
                    link = el.get_attribute("href")
                    if link and link not in server_links:
                        server_links.append(link)
                
                logger.info(f"Found {len(server_links)} server links")
                return server_links
                
            except TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)
            except WebDriverException as e:
                logger.error(f"WebDriver error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2)
        
        return []
    
    def extract_vip_link(self, driver, server_url, max_retries=2):
        """Extract VIP link from server page with retry mechanism"""
        for attempt in range(max_retries):
            try:
                driver.get(server_url)
                
                # Wait for VIP input to load
                wait = WebDriverWait(driver, 10)
                vip_input = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//input[@type='text' and contains(@value, 'https://')]")
                    )
                )
                
                vip_link = vip_input.get_attribute("value")
                if vip_link and vip_link.startswith("https://"):
                    return vip_link
                    
            except TimeoutException:
                logger.debug(f"No VIP link found in {server_url} (attempt {attempt + 1})")
            except Exception as e:
                logger.debug(f"Error extracting VIP link from {server_url}: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(1)
        
        return None
    
    def scrape_vip_links(self):
        """Main scraping function"""
        driver = None
        new_links_count = 0
        
        try:
            driver = self.create_driver()
            server_links = self.get_server_links(driver)
            
            if not server_links:
                logger.warning("No server links found")
                return
            
            logger.info(f"Processing {len(server_links)} server links")
            
            for i, server_url in enumerate(server_links):
                try:
                    vip_link = self.extract_vip_link(driver, server_url)
                    
                    if vip_link and vip_link not in self.unique_vip_links:
                        self.unique_vip_links.add(vip_link)
                        new_links_count += 1
                        logger.info(f"New VIP link found: {vip_link}")
                    
                    # Progress indicator
                    if (i + 1) % 5 == 0:
                        logger.info(f"Processed {i + 1}/{len(server_links)} servers")
                        
                except Exception as e:
                    logger.error(f"Error processing {server_url}: {e}")
                    continue
            
            logger.info(f"Scraping completed. Found {new_links_count} new VIP links")
            logger.info(f"Total unique VIP links: {len(self.unique_vip_links)}")
            
            self.save_links()
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
        finally:
            if driver:
                driver.quit()
    
    def get_random_link(self):
        """Get a random VIP link"""
        if not self.unique_vip_links:
            return None
        return random.choice(list(self.unique_vip_links))
    
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
    """Send a random VIP server link"""
    await interaction.response.defer()
    
    try:
        vip_link = scraper.get_random_link()
        
        if vip_link:
            embed = discord.Embed(
                title="🎮 Random VIP Server Link",
                description=f"[Click here to join the server]({vip_link})",
                color=0x00ff00,
                timestamp=datetime.now()
            )
            embed.add_field(name="Link", value=vip_link, inline=False)
            embed.add_field(name="Total Links Available", value=len(scraper.unique_vip_links), inline=True)
            embed.set_footer(text="Enjoy your gaming session!")
            
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ No VIP Links Available",
                description="No VIP server links found. Try running the scraper first.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        logger.error(f"Error in servertest command: {e}")
        await interaction.followup.send("❌ An error occurred while fetching the server link.", ephemeral=True)

@bot.tree.command(name="scrape", description="Start scraping for new VIP server links")
async def scrape_command(interaction: discord.Interaction):
    """Manually trigger scraping"""
    await interaction.response.defer()
    
    try:
        embed = discord.Embed(
            title="🔄 Scraping Started",
            description="Starting to scrape for new VIP server links...",
            color=0xffff00
        )
        await interaction.followup.send(embed=embed)
        
        # Run scraping in background
        await asyncio.get_event_loop().run_in_executor(None, scraper.scrape_vip_links)
        
        embed = discord.Embed(
            title="✅ Scraping Completed",
            description=f"Scraping finished! Total VIP links: {len(scraper.unique_vip_links)}",
            color=0x00ff00
        )
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in scrape command: {e}")
        await interaction.followup.send("❌ An error occurred during scraping.", ephemeral=True)

@bot.tree.command(name="stats", description="Show VIP links statistics")
async def stats(interaction: discord.Interaction):
    """Show statistics about collected VIP links"""
    try:
        embed = discord.Embed(
            title="📊 VIP Links Statistics",
            color=0x0099ff,
            timestamp=datetime.now()
        )
        embed.add_field(name="Total Unique Links", value=len(scraper.unique_vip_links), inline=True)
        
        if Path(scraper.vip_links_file).exists():
            with open(scraper.vip_links_file, 'r') as f:
                data = json.load(f)
                last_updated = data.get('last_updated', 'Unknown')
                embed.add_field(name="Last Updated", value=last_updated[:19], inline=True)
        
        embed.set_footer(text="Use /servertest to get a random link!")
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching stats.", ephemeral=True)

async def main():
    """Main function to run both scraper and bot"""
    # Load existing links on startup
    logger.info("Starting VIP Server Scraper Bot...")
    
    # You can uncomment this to scrape on startup
    # await asyncio.get_event_loop().run_in_executor(None, scraper.scrape_vip_links)
    
    # Start the bot
    # Get Discord token from environment variables (Secrets)
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        logger.error("DISCORD_TOKEN not found in environment variables")
        return
    
    await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())
