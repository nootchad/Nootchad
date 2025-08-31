
#!/usr/bin/env python3
"""
Script ejecutor simple para el framework independiente de scraping
Ejecuta el scraping sin inicializar el bot completo
"""

import asyncio
import sys
import logging
from standalone_scraper import StandaloneScraper

# ASCII Header
print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    ██╗  ██╗███████╗███████╗██╗███████╗    ███████╗██████╗  █████╗ ██████╗    ║
║    ██║  ██║██╔════╝██╔════╝██║╚══███╔╝    ██╔════╝██╔══██╗██╔══██╗██╔══██╗   ║
║    ███████║█████╗  ███████╗██║  ███╔╝     ███████╗██████╔╝███████║██████╔╝   ║
║    ██╔══██║██╔══╝  ╚════██║██║ ███╔╝      ╚════██║██╔══██╗██╔══██║██╔═══╝    ║
║    ██║  ██║███████╗███████║██║███████╗    ███████║██║  ██║██║  ██║██║        ║
║    ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝╚══════╝    ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ║
║                                                                              ║
║           This system was made by hesiz, any similar system is a copy        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

# Configurar logging simple
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def quick_scrape(game_id: str = "109983668079237", amount: int = 10):
    """Función rápida para scraping independiente"""
    try:
        print(f"Starting quick scraping...")
        print(f"Game: {game_id}")
        print(f"Amount: {amount} servers")
        print("-" * 40)
        
        # Crear y ejecutar scraper
        scraper = StandaloneScraper(game_id)
        success = await scraper.run_full_scraping(amount)
        
        if success:
            print("Scraping completed successfully")
            print(f"Data sent to Vercel API")
            return True
        else:
            print("Scraping failed")
            return False
            
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error in quick scraping: {e}")
        
        # Proporcionar información específica sobre errores de Selenium
        if any(keyword in error_msg for keyword in ["selenium", "chrome", "webdriver"]):
            print("=" * 50)
            print("SELENIUM ERROR DETECTED")
            print("=" * 50)
            print("This is a common issue that usually resolves on retry.")
            print("The framework has automatic retry mechanisms:")
            print("• Driver creation: up to 5 attempts")
            print("• Scraping process: up to 3 attempts") 
            print("• Individual extractions: up to 3 attempts")
            print("Simply run the command again - errors often disappear!")
            print("=" * 50)
        
        return False

if __name__ == "__main__":
    # Configuración por defecto
    GAME_ID = "109983668079237"
    AMOUNT = 10
    
    # Leer argumentos
    if len(sys.argv) > 1:
        GAME_ID = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            AMOUNT = int(sys.argv[2])
        except ValueError:
            print(f"Invalid amount: {sys.argv[2]}, using {AMOUNT}")
    
    # Ejecutar
    success = asyncio.run(quick_scrape(GAME_ID, AMOUNT))
    
    if success:
        print("\nFramework executed successfully")
        sys.exit(0)
    else:
        print("\nFramework failed")
        sys.exit(1)
