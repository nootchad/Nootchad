
# VIP Server Scraper Discord Bot

A Discord bot that scrapes VIP server links from rbxservers.xyz and provides them through Discord commands.

## Features

- **Improved Scraping**: Faster, more robust scraping with retry mechanisms
- **Error Tolerance**: Network error handling and timeout management
- **Data Persistence**: Saves unique links to JSON file
- **Discord Integration**: Slash commands for easy interaction
- **Optimized Performance**: Headless Chrome with optimized settings

## Setup

1. Install dependencies:
```bash
pip install selenium discord.py
```

2. Get a Discord Bot Token:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application and bot
   - Copy the bot token

3. Update the bot token in `main.py`:
   Replace `'YOUR_BOT_TOKEN'` with your actual token

4. Install Chrome/Chromium for Selenium

## Discord Commands

- `/servertest` - Get a random VIP server link
- `/scrape` - Manually trigger scraping for new links
- `/stats` - Show statistics about collected links

## Running

```bash
python main.py
```

## Files Created

- `vip_links.json` - Stores all unique VIP links with metadata
- Logs are displayed in console for monitoring

## Improvements Made

1. **Speed**: Optimized Chrome options, disabled images/JS
2. **Robustness**: Retry mechanisms, proper error handling
3. **Error Tolerance**: Network timeouts, WebDriver exceptions
4. **Data Management**: JSON storage with unique link tracking
5. **Discord Integration**: Professional slash commands with embeds
