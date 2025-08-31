
#!/usr/bin/env python3
"""
Script ejecutor simple para el framework independiente de scraping
Ejecuta el scraping sin inicializar el bot completo
"""

import asyncio
import sys
import logging
from standalone_scraper import StandaloneScraper

# Configurar logging simple
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def quick_scrape(game_id: str = "109983668079237", amount: int = 10):
    """Función rápida para scraping independiente"""
    try:
        print(f"🚀 Iniciando scraping rápido...")
        print(f"🎮 Juego: {game_id}")
        print(f"🎯 Cantidad: {amount} servidores")
        print("-" * 40)
        
        # Crear y ejecutar scraper
        scraper = StandaloneScraper(game_id)
        success = await scraper.run_full_scraping(amount)
        
        if success:
            print("✅ Scraping completado exitosamente")
            print(f"📤 Datos enviados a Vercel API")
            return True
        else:
            print("❌ Scraping falló")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en scraping rápido: {e}")
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
            print(f"⚠️ Cantidad inválida: {sys.argv[2]}, usando {AMOUNT}")
    
    # Ejecutar
    success = asyncio.run(quick_scrape(GAME_ID, AMOUNT))
    
    if success:
        print("\n🎉 Framework ejecutado exitosamente")
        sys.exit(0)
    else:
        print("\n❌ Framework falló")
        sys.exit(1)
