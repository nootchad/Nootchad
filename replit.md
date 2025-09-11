# Overview

RbxServers is a Discord bot that automates the discovery and distribution of Roblox VIP servers. The bot scrapes VIP server links from multiple sources and provides them to users through Discord commands. It features a comprehensive verification system, marketplace functionality, code redemption system, and various community features. The project includes both a Discord bot interface and REST API endpoints for external integration.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Components

### Discord Bot Framework
- Built on discord.py 2.5.2+ with slash command support
- Modular command system organized in separate files
- Event-driven architecture with proper error handling and logging
- Integration with aiohttp for web server functionality

### Scraping Engine
- Selenium-based web scraping with Chrome WebDriver
- Headless browser automation for VIP server extraction
- Cookie management system for Roblox authentication
- Retry mechanisms and error tolerance for network issues
- Standalone scraper framework that can operate independently

### Verification System
- Roblox profile-based user verification
- Anti-alt detection with fingerprinting
- Trust scoring and risk assessment
- Cooldown management and ban system
- Username history tracking and similarity detection

### Data Storage
- JSON-based file storage for all persistent data
- Separate files for different data types (users, codes, marketplace, etc.)
- No database dependency - uses file-based persistence
- Automatic data saving and loading with error handling

### API Layer
- REST API endpoints for external integration
- OAuth2 system for Discord authentication
- Webhook support for external applications
- CORS-enabled for web application integration
- Authentication via Bearer tokens

## Key Systems

### Economy and Rewards
- Virtual coin system with daily rewards
- Code redemption system with creator tracking
- Marketplace for server exchanges between users
- Leaderboard system with weekly and all-time rankings
- VIP tier system with premium benefits

### Security and Moderation
- Anti-alt system with user fingerprinting
- Blacklist and whitelist management
- Report system for problematic users/servers
- Maintenance mode functionality
- Automated ban system based on suspicious activity

### Community Features
- Middleman system for secure trades
- Support ticket system
- Announcement system with user notifications
- Suggestion system for community feedback
- Role management and server configuration

### Content Generation
- AI-powered image generation using Pollinations API
- Music generation system with callback handling
- Integration with external AI services
- File handling for generated content

## Design Patterns

### Modular Architecture
- Commands separated into individual modules
- System components as independent classes
- Plugin-like structure for easy feature addition
- Clear separation of concerns between bot logic and data management

### Event-Driven Processing
- Async/await pattern throughout the codebase
- Event handlers for Discord interactions
- Webhook processing for external integrations
- Background task management for automated processes

### Configuration Management
- JSON-based configuration files
- Environment variable support for sensitive data
- Runtime configuration updates
- Centralized settings management

# External Dependencies

## Core Dependencies
- **discord.py**: Discord API interaction and bot framework
- **selenium**: Web scraping and browser automation
- **aiohttp**: HTTP client/server for API functionality
- **webdriver-manager**: Chrome WebDriver management

## External Services
- **Discord API**: Primary platform integration
- **Roblox API**: User verification and game data
- **Pollinations AI**: Image generation service
- **External Music API**: Music generation capabilities
- **Chrome/Chromium**: Browser engine for web scraping

## Optional Integrations
- **Supabase**: Database alternative (configured but not actively used)
- **PostgreSQL**: Database support via psycopg2-binary
- **SQLAlchemy**: ORM for database operations
- **Vercel**: Deployment platform for API endpoints

## Development Tools
- **python-dotenv**: Environment variable management
- **requests**: HTTP client for API calls
- **pathlib**: File system operations
- **logging**: Comprehensive logging system