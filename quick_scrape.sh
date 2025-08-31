
#!/bin/bash

# Script de ejecución rápida del framework independiente de scraping
# Uso: ./quick_scrape.sh [game_id] [cantidad]

echo "🤖 Framework Independiente RbxServers"
echo "======================================"

# Configuración por defecto
GAME_ID=${1:-"109983668079237"}
AMOUNT=${2:-10}

echo "🎮 Juego: $GAME_ID"
echo "🎯 Cantidad: $AMOUNT servidores"
echo "🌐 API: Vercel"
echo "======================================"

# Verificar que Python3 esté disponible
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 no encontrado"
    exit 1
fi

# Verificar que el archivo del framework exista
if [ ! -f "standalone_scraper.py" ]; then
    echo "❌ Error: standalone_scraper.py no encontrado"
    exit 1
fi

# Ejecutar framework
echo "🚀 Iniciando scraping independiente..."
python3 standalone_scraper.py "$GAME_ID" "$AMOUNT"

# Capturar código de salida
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Framework ejecutado exitosamente"
    echo "📤 Datos enviados a API de Vercel"
else
    echo "❌ Framework falló con código $EXIT_CODE"
fi

echo "======================================"
echo "🔍 Logs disponibles en: standalone_scraper.log"
echo "💾 Resultados guardados en: standalone_results_*.json"

exit $EXIT_CODE
