# Overview

VIP Server Scraper Discord Bot is a comprehensive Discord bot that scrapes VIP server links from rbxservers.xyz and provides them through Discord commands. The bot features advanced user management systems including promotional codes, user verification, and security features. It uses a hybrid architecture with both JSON file storage and Supabase integration for scalability.

## Recent Changes (September 15, 2025)
- **System Cleanup**: Removed antialt detection, coins system, kxis3rr system, leaderboard, marketplace, and music generation systems to simplify codebase and improve bot startup reliability

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Bot Framework
- **Discord.py**: Primary bot framework for Discord integration
- **Slash Commands**: Modern Discord command system using application commands
- **Event-driven Architecture**: Async/await patterns throughout the codebase
- **Modular Command System**: Commands organized in `/Commands` folder with auto-loading

## Web Scraping System
- **Selenium WebDriver**: Chrome-based headless browser automation for scraping VIP server links
- **StandaloneScraper**: Independent scraping framework that can run without the full bot
- **Cookie Management**: Roblox authentication cookies stored in JSON for persistent sessions
- **Rate Limiting**: Built-in delays and retry mechanisms to avoid detection

## Data Storage Architecture
- **Hybrid Storage**: JSON files for local development, Supabase for production scaling
- **File-based Systems**: Over 30 JSON files managing different data types (users, servers, coins, etc.)
- **Supabase Integration**: PostgreSQL database with migration system from JSON to cloud storage
- **Blob Storage**: Vercel Blob Storage for large file management and backups

## User Management Systems
- **User Verification**: Roblox account linking with verification codes  
- **Role Management**: Automatic Discord role assignment upon verification

## Security & Moderation
- **Blacklist/Whitelist**: User access control with permanent and temporary restrictions
- **Report System**: User reporting for scam detection and community moderation
- **Maintenance Mode**: System-wide maintenance with user notifications
- **Access Control**: Owner/delegated owner permission system

## Economic Systems
- **Promotional Codes**: Redeemable codes with usage tracking and limits

## API Integration
- **Web API**: RESTful endpoints for external integrations
- **OAuth2 System**: Discord OAuth for web authentication
- **Image Generation**: AI image generation using Pollinations API

## Monitoring & Analytics
- **Command Logging**: Comprehensive logging of all bot interactions
- **Usage Statistics**: User activity tracking
- **Web Analytics**: Website visit tracking and user behavior analysis
- **Alert System**: Bot startup notifications and user alerts

## Performance Optimizations
- **Async Operations**: Non-blocking operations throughout the codebase
- **Connection Pooling**: Database connection management for Supabase
- **Caching**: In-memory caching for frequently accessed data
- **Background Tasks**: Automated maintenance and cleanup processes

# External Dependencies

## Core Infrastructure
- **Discord API**: Bot hosting and command processing
- **Selenium**: Web scraping automation with Chrome WebDriver
- **Supabase**: Cloud PostgreSQL database and authentication
- **Vercel**: Web hosting and Blob Storage for file management

## Third-party APIs
- **Roblox API**: User verification and game data retrieval
- **Pollinations AI**: Image generation services

## Python Libraries
- **discord.py**: Discord bot framework
- **selenium**: Web automation and scraping
- **aiohttp**: Async HTTP client/server
- **asyncpg**: PostgreSQL async driver
- **supabase-py**: Supabase Python client
- **python-dotenv**: Environment variable management

## Development Tools
- **Railway**: Cloud deployment platform (environment variable loading)
- **Chrome/Chromium**: Headless browser for scraping operations
- **JSON**: Primary data serialization format for local storage